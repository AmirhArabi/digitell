#!/usr/bin/env bash
# تست مرحله ۱ — «ایمن‌سازی وضعیت فعلی با commit»
# بررسی می‌کند که: همهٔ فایل‌های کلیدی و مهاجرت‌ها در گیت ثبت شده باشند،
# هیچ تغییری بدون کامیت نمانده باشد، مهاجرت‌ها با مدل‌ها هم‌خوان باشند و
# یک کلون تازه از گیت بتواند migrate و کل تست‌ها را با موفقیت اجرا کند.
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

echo "== ۱) ردیابی فایل‌های کلیدی توسط گیت =="
required=(
  "tickets/__init__.py"
  "tickets/apps.py"
  "tickets/admin.py"
  "tickets/models.py"
  "tickets/views.py"
  "tickets/urls.py"
  "tickets/tests.py"
  "tickets/context_processors.py"
  "tickets/migrations/0001_initial.py"
  "home/migrations/0002_banner_button_text_banner_subtitle_and_more.py"
  "orders/migrations/0002_coupon_order_admin_note_order_coupon_code_and_more.py"
  "products/migrations/0003_product_low_stock_threshold_categoryattribute.py"
  "docs/plan_steps.md"
  "docs/PRD.md"
  "docs/SMS_TICKETING_DESIGN.md"
  "templates/dashboard/tickets.html"
  "templates/dashboard/partials/_sidebar_nav.html"
  "templates/tickets/detail.html"
  "static/js/dashboard-charts.js"
  "static/js/dashboard-sidebar.js"
  "static/js/vendor/chart.umd.min.js"
  "static/css/input.css"
  "static/css/output.css"
  "scripts/verify_step1.sh"
)
missing_tracked=0
for path in "${required[@]}"; do
  if ! git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    bad "$path در گیت ثبت نشده است"
    missing_tracked=1
  fi
done
[ "$missing_tracked" -eq 0 ] && pass "همهٔ ${#required[@]} فایل کلیدی ردیابی می‌شوند"

echo "== ۲) هیچ فایل مهاجرت ثبت‌نشده‌ای وجود ندارد =="
untracked_migrations=0
while IFS= read -r m; do
  if ! git ls-files --error-unmatch "$m" >/dev/null 2>&1; then
    bad "مهاجرت ثبت‌نشده: $m"
    untracked_migrations=1
  fi
done < <(find . \( -path ./venv -o -path ./node_modules -o -path ./.git \
  -o -path ./staticfiles -o -path ./media \) -prune -o -type f \
  -name '[0-9]*.py' -path '*/migrations/*' -print | sed 's|^\./||' | sort)
[ "$untracked_migrations" -eq 0 ] && pass "تمام مهاجرت‌های روی دیسک ردیابی می‌شوند"

echo "== ۳) درخت کار تمیز است (بدون تغییر ثبت‌نشده) =="
dirty="$(git status --porcelain)"
if [ -z "$dirty" ]; then
  pass "هیچ تغییر ثبت‌نشده‌ای باقی نمانده است"
else
  bad "تغییرات ثبت‌نشده:"
  printf '%s\n' "$dirty" | sed 's/^/      /'
fi

echo "== ۴) هم‌خوانی مهاجرت‌ها با مدل‌ها (makemigrations --check) =="
if "$PY" manage.py makemigrations --check --dry-run >/tmp/verify1_makemig.log 2>&1; then
  pass "مهاجرت‌ها با مدل‌ها هم‌خوان‌اند"
else
  bad "مهاجرت ناقص است:"
  tail -20 /tmp/verify1_makemig.log | sed 's/^/      /'
fi

echo "== ۵) کلون تازه از گیت: migrate + اجرای کل تست‌ها =="
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp" /tmp/verify1_*.log' EXIT
if ! git archive HEAD | tar -x -C "$tmp"; then
  bad "استخراج HEAD با git archive ناموفق بود"
else
  log=/tmp/verify1_clone.log
  if ( cd "$tmp" && "$PY" manage.py migrate --noinput && "$PY" manage.py test ) >"$log" 2>&1; then
    ran="$(grep -oE 'Ran [0-9]+ tests?' "$log" | grep -oE '[0-9]+' | head -1)"
    if [ -n "${ran:-}" ] && [ "$ran" -ge 66 ]; then
      pass "کلون تازه: migrate موفق و $ran تست با نتیجه OK"
    else
      bad "تعداد تست‌های کلون تازه کمتر از ۶۶ است (اجرا شده: ${ran:-0})"
    fi
  else
    bad "اجرای migrate/test روی کلون تازه شکست خورد:"
    tail -25 "$log" | sed 's/^/      /'
  fi
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "نتیجه مرحله ۱: موفق — همهٔ تغییرات در گیت ثبت شده و مخزن سالم است."
else
  echo "نتیجه مرحله ۱: ناموفق — موارد بالا باید رفع شوند."
fi
exit "$fail"
