#!/usr/bin/env bash
# بررسی گام ۳ — پلن ادامهٔ مراحل:
#   ۱) وجود سند پلن و ارجاع‌هایش به فایل‌های واقعی مخزن
#   ۲) پشتوانهٔ کدی برای کارهای «انجام‌شده» که در نقشه‌راه‌ها تیک خورده‌اند
#   ۳) ساختار قابل‌اجرا بودن گام‌ها (تست و معیار پذیرش برای هر گام)
#   ۴) ثبت درست کامیت‌های قبلی به نام نویسندهٔ پروژه

set -uo pipefail

PY="./venv/Scripts/python.exe"
[ -x "$PY" ] || PY="python"
PLAN="docs/PLAN_NEXT_STEPS.md"
FAILED=0

pass() { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAILED=1; }
head() { printf '\n== %s ==\n' "$1"; }

head "۱. سند پلن و ساختار آن"
if [ -f "$PLAN" ]; then
    pass "سند پلن موجود است: $PLAN"
else
    fail "سند پلن پیدا نشد: $PLAN"
fi

STEP_COUNT=$(grep -c '^### گام' "$PLAN" || true)
if [ "$STEP_COUNT" -ge 8 ]; then
    pass "تعداد گام‌های پلن: $STEP_COUNT"
else
    fail "تعداد گام‌های پلن کمتر از حد انتظار است: $STEP_COUNT"
fi

for marker in 'تست گام' 'معیار پذیرش' 'تصمیم‌های مسدودکننده' 'قاعدهٔ اجرای هر گام'; do
    if grep -q "$marker" "$PLAN"; then
        pass "بخش «$marker» در پلن هست"
    else
        fail "بخش «$marker» در پلن نیست"
    fi
done

# هر گام باید هم آزمون و هم معیار پذیرش داشته باشد.
BARE_STEPS=$("$PY" - "$PLAN" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding='utf-8')
steps = re.split(r'^### ', text, flags=re.M)[1:]
bare = []
for block in steps:
    title = block.splitlines()[0].strip()
    if not title.startswith('گام'):
        continue
    if '**تست گام' not in block or '**معیار پذیرش' not in block:
        bare.append(title)
for title in bare:
    print(title)
PY
)
if [ -z "$BARE_STEPS" ]; then
    pass "هر گام هم «تست گام» و هم «معیار پذیرش» دارد"
else
    fail "گام‌های بدون تست یا معیار پذیرش:"
    printf '       %s\n' "$BARE_STEPS"
fi

head "۲. ارجاع‌های پلن به فایل‌های واقعی"
NOT_FOUND=0
for path in \
    "config/settings.py" "requirements.txt" ".github/workflows/ci.yml" \
    "products/models.py" "orders/models.py" "orders/views.py" "cart/views.py" \
    "orders/tests.py" "products/tests.py" "templates/products/product_detail.html" \
    "accounts/models.py" "docs/ROADMAP_STOREFRONT.md" "docs/ROADMAP_ADMIN_PANEL.md" \
    "docs/PRD.md" "docs/TESTING.md" "docs/BUSINESS_RULES.md" "docs/SMS_TICKETING_DESIGN.md" \
    "docs/plan_steps.md"; do
    if [ -e "$path" ]; then
        pass "مسیر موجود: $path"
    else
        fail "مسیر ارجاع‌شده پیدا نشد: $path"
        NOT_FOUND=1
    fi
done

# ارجاع‌های in-code در پلن (نام کلاس‌ها و متدها) باید در کد وجود داشته باشند.
for symbol in "reserve_stock" "release_stock" "commit_stock" "reserved_qty" "stock_state" "available_qty"; do
    if grep -rq "$symbol" products/models.py orders/models.py; then
        pass "نماد کد موجود: $symbol"
    else
        fail "نماد کد در مخزن پیدا نشد: $symbol"
    fi
done

head "۳. پشتوانهٔ کدی برای کارهای تیک‌خورده در نقشه‌راه‌ها"
if grep -q "reserved_qty" products/models.py && grep -q "stock_state" orders/models.py; then
    pass "رزرو موجودی (کامیت c139e41) در کد هست"
else
    fail "ادعای رزرو موجودی در نقشه‌راه با کد هم‌خوان نیست"
fi

if [ -f requirements.txt ] && ! grep -qE '^[A-Za-z0-9_.-]+$' requirements.txt; then
    pass "requirements.txt با نسخهٔ pin‌شده وجود دارد"
else
    fail "requirements.txt وجود ندارد یا نسخه‌ها pin نشده‌اند"
fi

if [ -f .github/workflows/ci.yml ]; then
    pass "workflow CI وجود دارد"
else
    fail "workflow CI پیدا نشد"
fi

if grep -q "DJANGO_SECRET_KEY" config/settings.py; then
    pass "کلید و تنظیمات امنیتی از environment خوانده می‌شود"
else
    fail "تنظیمات env-محور در settings پیدا نشد"
fi

if grep -qE '\[x\]' docs/ROADMAP_STOREFRONT.md docs/ROADMAP_ADMIN_PANEL.md; then
    pass "موارد انجام‌شده در نقشه‌راه‌ها تیک خورده‌اند"
else
    fail "هیچ مورد تیک‌خورده‌ای در نقشه‌راه‌ها نیست"
fi

head "۴. کامیت‌های ارجاع‌شده در پلن"
for sha in 48a7561 6e77c3c c139e41 a5ed2df; do
    if ! git cat-file -e "$sha^{commit}" 2>/dev/null; then
        fail "کامیت در پلن ذکر شده ولی در مخزن نیست: $sha"
        continue
    fi
    AUTHOR_MAIL=$(git log -1 --format='%ae' "$sha")
    SUBJECT=$(git log -1 --format='%s' "$sha")
    BODY_LINES=$(git log -1 --format='%b' "$sha" | grep -c . || true)
    if [ "$AUTHOR_MAIL" = "digitallyboy@gmail.com" ]; then
        pass "$sha — نویسنده درست ($SUBJECT)"
    else
        fail "$sha — نویسندهٔ نادرست: $AUTHOR_MAIL"
    fi
    if [ "$BODY_LINES" -eq 0 ]; then
        pass "$sha — پیام تک‌خطی (بدون بدنهٔ اضافه)"
    else
        fail "$sha — پیام بدنهٔ اضافه دارد ($BODY_LINES خط)"
    fi
done

head "نتیجه"
if [ "$FAILED" -eq 0 ]; then
    printf '\033[32mتمام بررسی‌های گام ۳ سبز است.\033[0m\n'
    exit 0
fi
printf '\033[31mبررسی‌های گام ۳ ناموفق بود.\033[0m\n'
exit 1
