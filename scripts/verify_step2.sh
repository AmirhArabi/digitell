#!/usr/bin/env bash
# تست مرحله ۲ — «تنظیمات production و secretها از environment»
# بررسی می‌کند که: کلید و تنظیمات امنیتی از متغیر محیطی خوانده شوند،
# اجرای محلی بدون تنظیمات کار کند، در حالت تولید نبودِ کلید خطا بدهد،
# مقادیر production درست اعمال شوند، فایل .env خوانده شود و
# check --deploy بدون هشدار بگذرد و کل تست‌ها سبز بمانند.
set -uo pipefail

cd "$(dirname "$0")/.."

if [ -x "venv/Scripts/python.exe" ]; then
  PY="$(pwd)/venv/Scripts/python.exe"
elif [ -x "venv/bin/python" ]; then
  PY="$(pwd)/venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

fail=0
pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad() { printf '  \033[31m✗\033[0m %s\n' "$1"; fail=1; }

LOG="$(mktemp)"
had_env=0
cleanup() {
  rm -f "$LOG" /tmp/verify2_*.log
  if [ "$had_env" -eq 1 ]; then mv -f .env.verify_step2_backup .env; else rm -f .env; fi
}
trap cleanup EXIT

# اگر کاربر .env داشته باشد، موقتاً کنار گذاشته می‌شود تا نتیجهٔ تست‌ها آلوده نشود.
if [ -f .env ]; then mv .env .env.verify_step2_backup; had_env=1; fi

echo "== ۱) بررسی ایستا: کلید hardcode حذف شده و .env.example موجود است =="
if grep -q "django-insecure-zitro-shop-digitell-super-secret-key-fa" config/settings.py; then
  bad "کلید قدیمی هنوز در config/settings.py hardcode است"
else
  pass "کلید hardcode قدیمی حذف شده است"
fi
if grep -q "DJANGO_SECRET_KEY" config/settings.py; then
  pass "کلید از متغیر محیطی DJANGO_SECRET_KEY خوانده می‌شود"
else
  bad "خواندن DJANGO_SECRET_KEY از environment پیدا نشد"
fi
if [ -f .env.example ]; then
  missing=""
  for key in DJANGO_DEBUG DJANGO_SECRET_KEY DJANGO_ALLOWED_HOSTS DJANGO_CSRF_TRUSTED_ORIGINS DJANGO_SECURE; do
    grep -q "$key" .env.example || missing="$missing $key"
  done
  if [ -z "$missing" ]; then pass ".env.example همهٔ کلیدهای لازم را دارد"; else bad ".env.example فاقد:$missing"; fi
else
  bad ".env.example ساخته نشده است"
fi
if git check-ignore -q .env; then pass ".env در .gitignore است"; else bad ".env در .gitignore نیست"; fi
if git check-ignore -q .env.example; then bad ".env.example اشتباهاً ignore شده است"; else pass ".env.example قابل کامیت است"; fi

echo "== ۲) اجرای محلی بدون هیچ متغیر محیطی (fallback امن) =="
if env -u DJANGO_DEBUG -u DJANGO_SECRET_KEY -u DJANGO_ALLOWED_HOSTS \
  "$PY" manage.py shell -c "from django.conf import settings as s; print(s.DEBUG, bool(s.SECRET_KEY), s.ALLOWED_HOSTS, s.SESSION_COOKIE_SECURE, s.SECURE_HSTS_SECONDS)" >"$LOG" 2>&1; then
  if grep -q "True True \['\*'\] False 0" "$LOG"; then
    pass "بدون env: DEBUG=True، کلید موقت موجود، ALLOWED_HOSTS=['*']، بدون اجبار امنیتی"
  else
    bad "مقادیر پیش‌فرض توسعه درست نیستند: $(tail -1 "$LOG")"
  fi
else
  bad "اجرای محلی بدون env شکست خورد:"; tail -15 "$LOG" | sed 's/^/      /'
fi

echo "== ۳) در تولید (DEBUG=false) نبودِ کلید باید خطای صریح بدهد =="
env -u DJANGO_SECRET_KEY DJANGO_DEBUG=0 "$PY" manage.py check >"$LOG" 2>&1
code=$?
if [ "$code" -ne 0 ] && grep -q "DJANGO_SECRET_KEY" "$LOG"; then
  pass "نبود DJANGO_SECRET_KEY در تولید با ImproperlyConfigured رد می‌شود"
else
  bad "در DEBUG=false و نبود کلید، اجرا باید خطا بدهد (exit=$code):"; tail -8 "$LOG" | sed 's/^/      /'
fi

echo "== ۴) اعمال مقادیر production از environment =="
KEY="$(head -c 48 /dev/urandom | od -An -tx1 | tr -d ' \n')"
expected="True True True True True 31536000 True False"
out=$(env DJANGO_SETTINGS_MODULE=config.settings DJANGO_DEBUG=0 DJANGO_SECRET_KEY="$KEY" \
  DJANGO_ALLOWED_HOSTS="shop.example.com,www.shop.example.com" \
  "$PY" -c "import django; django.setup(); from django.conf import settings as s; print(s.SECRET_KEY=='$KEY', s.ALLOWED_HOSTS==['shop.example.com','www.shop.example.com'], s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SECURE_SSL_REDIRECT, s.SECURE_HSTS_SECONDS, s.USE_X_FORWARDED_HOST, s.DEBUG)" 2>"$LOG")
if [ "${out//$'\r'/}" = "$expected" ]; then
  pass "کلید، ALLOWED_HOSTS و پرچم‌های امنیتی از env اعمال شدند"
else
  bad "خروجی production ناهمسان است: «${out//$'\r'/}» به‌جای «$expected»"
  tail -8 "$LOG" | sed 's/^/      /'
fi

echo "== ۵) check --deploy در حالت تولید =="
if env DJANGO_DEBUG=0 DJANGO_SECRET_KEY="$KEY" DJANGO_ALLOWED_HOSTS="shop.example.com" \
  "$PY" manage.py check --deploy >"$LOG" 2>&1; then
  if grep -q "no issues" "$LOG"; then
    pass "check --deploy بدون هیچ هشدار/خطا گذشت"
  else
    bad "check --deploy پیام غیرمنتظره دارد:"; sed 's/^/      /' "$LOG"
  fi
else
  bad "check --deploy شکست خورد:"; sed 's/^/      /' "$LOG"
fi

echo "== ۶) خوانده شدن مقادیر از فایل .env =="
printf 'DJANGO_DEBUG=true\nDJANGO_ALLOWED_HOSTS=from-dotenv.example\n' > .env
out=$(env -u DJANGO_DEBUG -u DJANGO_ALLOWED_HOSTS DJANGO_SETTINGS_MODULE=config.settings "$PY" \
  -c "import django; django.setup(); from django.conf import settings as s; print(s.ALLOWED_HOSTS)" 2>"$LOG")
if [ "${out//$'\r'/}" = "['from-dotenv.example']" ]; then
  pass "فایل .env در محیط توسعه خوانده می‌شود"
else
  bad "مقدار .env اعمال نشد: «${out//$'\r'/}»"
  tail -8 "$LOG" | sed 's/^/      /'
fi
rm -f .env

echo "== ۷) تست‌های رگرسیون پروژه =="
if "$PY" manage.py test >"$LOG" 2>&1; then
  ran="$(grep -oE 'Ran [0-9]+ tests?' "$LOG" | grep -oE '[0-9]+' | head -1)"
  if [ -n "${ran:-}" ] && [ "$ran" -ge 66 ]; then
    pass "کل تست‌ها پس از تغییر تنظیمات: $ran تست OK"
  else
    bad "تعداد تست کمتر از ۶۶ است (اجرا شده: ${ran:-0})"
  fi
else
  bad "اجرای تست‌ها شکست خورد:"; tail -25 "$LOG" | sed 's/^/      /'
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "نتیجه مرحله ۲: موفق — تنظیمات از environment خوانده می‌شود و check --deploy پاک است."
else
  echo "نتیجه مرحله ۲: ناموفق — موارد بالا باید رفع شوند."
fi
exit "$fail"
