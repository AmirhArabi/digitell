#!/usr/bin/env bash
# تست مرحله ۳ — «Manifest وابستگی و CI»
# بررسی می‌کند که: requirements.txt کامل و pin‌شده باشد، با محیط نصب‌شده هم‌خوان باشد،
# workflow درست و با YAML معتبر ساخته شده باشد، و یک محیط مجازی کاملاً تازه فقط با
# همین requirements بتواند check و کل تست‌ها را اجرا کند.
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
TMPVENV="$(mktemp -d)/venv"
cleanup() { rm -f "$LOG" /tmp/verify3_*.log; rm -rf "$(dirname "$TMPVENV")"; }
trap cleanup EXIT

echo "== ۱) ساختار requirements.txt =="
if [ -s requirements.txt ]; then
  pass "requirements.txt موجود و غیرخالی است ($(grep -c . requirements.txt) بستهٔ نصب)"
else
  bad "requirements.txt ساخته نشده یا خالی است"
fi
if grep -q $'\r' requirements.txt; then bad "requirements.txt دارای CRLF است"; else pass "پایان خطوط LF است"; fi
unpinned="$(grep -vE '^[A-Za-z0-9][A-Za-z0-9._+-]*==[^=[:space:]]+$' requirements.txt || true)"
if [ -z "$unpinned" ]; then
  pass "همهٔ خطوط با نسخهٔ دقیق (==) pin شده‌اند"
else
  bad "خطوط غیر pin‌شده:"; printf '%s\n' "$unpinned" | sed 's/^/      /'
fi
missing=""
for pkg in Django asgiref dj-database-url django-htmx gunicorn pillow python-dotenv sqlparse tzdata whitenoise; do
  grep -qiE "^${pkg}==" requirements.txt || missing="$missing $pkg"
done
if [ -z "$missing" ]; then pass "همهٔ بسته‌های موردنیاز پروژه در manifest هستند"; else bad "بسته‌های غایب:$missing"; fi

echo "== ۲) هم‌خوانی requirements با محیط نصب‌شدهٔ فعلی =="
"$PY" -m pip freeze | tr -d '\r' | LC_ALL=C sort > /tmp/verify3_installed.log
if diff -q requirements.txt /tmp/verify3_installed.log >/dev/null; then
  pass "requirements.txt دقیقاً همان محیط فعلی است"
else
  bad "اختلاف میان requirements.txt و محیط نصب‌شده:"
  diff requirements.txt /tmp/verify3_installed.log | sed 's/^/      /'
fi

echo "== ۳) بررسی workflow CI =="
WF=".github/workflows/ci.yml"
if [ -f "$WF" ]; then
  pass "$WF ساخته شده است"
  missing_step=""
  for needle in "npm ci" "npm run build:css" "pip install -r requirements.txt" "manage.py check" "makemigrations --check" "manage.py test"; do
    grep -qF "$needle" "$WF" || missing_step="$missing_step [$needle]"
  done
  if [ -z "$missing_step" ]; then
    pass "همهٔ مراحل موردنیاز در workflow هست"
  else
    bad "مراحل غایب در workflow:$missing_step"
  fi
else
  bad "$WF ساخته نشده است"
fi

echo "== ۴) محیط مجازی کاملاً تازه فقط از روی requirements.txt =="
if "$PY" -m venv "$TMPVENV" >/tmp/verify3_venv.log 2>&1; then
  if [ -x "$TMPVENV/Scripts/python.exe" ]; then FPY="$TMPVENV/Scripts/python.exe"; else FPY="$TMPVENV/bin/python"; fi
  if "$FPY" -m pip install --quiet --disable-pip-version-check -r requirements.txt >/tmp/verify3_install.log 2>&1; then
    pass "نصب وابستگی‌ها در محیط تازه موفق بود"
    if "$FPY" manage.py check >/tmp/verify3_check.log 2>&1; then
      pass "manage.py check با محیط تازه بدون خطا گذشت"
    else
      bad "check با محیط تازه شکست خورد:"; tail -15 /tmp/verify3_check.log | sed 's/^/      /'
    fi
    if "$FPY" manage.py test >/tmp/verify3_test.log 2>&1; then
      ran="$(grep -oE 'Ran [0-9]+ tests?' /tmp/verify3_test.log | grep -oE '[0-9]+' | head -1)"
      if [ -n "${ran:-}" ] && [ "$ran" -ge 66 ]; then
        pass "اجرای کل تست‌ها با محیط تازه: $ran تست OK"
      else
        bad "تعداد تست در محیط تازه کمتر از ۶۶ است (اجرا شده: ${ran:-0})"
      fi
    else
      bad "تست‌ها با محیط تازه شکست خوردند:"; tail -25 /tmp/verify3_test.log | sed 's/^/      /'
    fi
    # اعتبارسنجی نحوی YAML (فقط ابزار تست؛ به requirements اضافه نمی‌شود)
    if "$FPY" -m pip install --quiet --disable-pip-version-check pyyaml >>/tmp/verify3_install.log 2>&1 \
      && "$FPY" -c "import yaml; yaml.safe_load(open('$WF', encoding='utf-8')); print('ok')" >"$LOG" 2>&1 \
      && grep -q ok "$LOG"; then
      pass "YAML فایل workflow معتبر است"
    else
      bad "YAML فایل workflow معتبر نیست:"; tail -10 "$LOG" | sed 's/^/      /'
    fi
  else
    bad "نصب وابستگی‌ها در محیط تازه شکست خورد:"; tail -15 /tmp/verify3_install.log | sed 's/^/      /'
  fi
else
  bad "ساخت محیط مجازی تازه شکست خورد:"; tail -10 /tmp/verify3_venv.log | sed 's/^/      /'
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "نتیجه مرحله ۳: موفق — وابستگی‌ها pin و قابل بازتولید است و CI آمادهٔ اجراست."
else
  echo "نتیجه مرحله ۳: ناموفق — موارد بالا باید رفع شوند."
fi
exit "$fail"
