# پلن مرحله‌ای بعدی — زیترو شاپ

## مرحله ۱: ایمن‌سازی وضعیت فعلی با commit (P0)

- **چرا:** تمام دستاوردهای جلسه قبلی (رفع سه خطای تیکتینگ، ۳۱ تست جدید در ماژول `tickets`، سند `docs/SMS_TICKETING_DESIGN.md`، سه migration) روی دیسک‌اند ولی هیچ‌کدام کامیت نشده‌اند؛ تغییم‌ها در حال حاضر کاور نشده و ممکن است در چک‌اند یا کپیِ ناقص از پروژه از بین بروند. خود `DEVELOPMENT.md` گفت که migrationهای untracked (home/0002، orders/0002، products/0003) باید پیش از merge tracked شوند.
- **چگونه:**
  - `git status --short` را بازبینی کرده و بخش‌ها را به چند commit منطقی تقسیم: (a) پنل + تمپلیت‌ها، (b) اپ تیکتینگ + تست‌ها، (c) migration‌ها، (d) اسناد.
  - کامیت فقط با `git add <فایل>` (نه `git add -A`).
  - پیام توضیحی مستقیم و بدون secret.
  - بدون `git push` (اجرای کامیت و push زمانیکه کاربر رضایت دارد).

## مرحله ۲: تنظیمات production و secretها از environment (P0)

- **چرا:** `SECRET_KEY` در `config/settings.py:6` hardcode است و `DEBUG`/`ALLOWED_HOSTS` بدون کنترل هستند؛ علاوه بر اینکه اینها پایه‌گذار همهٔ کنترل‌های امنیتی و تنظیمات پیامک/ایمیل می‌باشند، فاز ۰ نقشه‌راه هم دقیقاً این‌ها را می‌طلبد.
- **چگونه:**
  - بلوک env-محور در `config/settings.py` با `os.environ` و fallback امن فقط برای `DEBUG`; `ALLOWED_HOSTS` لیست‌دار.
  - `.env` از قبل در `.gitignore` است؛ نمونهٔ `.env.example` بدون مقدار واقعی ساخته شود.
  - `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `USE_X_FORWARDED_HOST` و HSTS را پشت پرچم env قرار دهید.
  - در نهایت `python manage.py check --deploy` را اجرا و خروجی واقعی را بگویید.

## مرحله ۳: Manifest وابستگی و CI (P0)

- **چرا:** `requirements.txt`/`pyproject.toml` وجود ندارد و `Registry` packages از محیط `venv/` به‌طور غیرقابلتکرار نصب شده‌اند؛ بدون CI، ۶۶ تست و `check` فقط دستی اجرا می‌شوند و معیار پذیرش ROADMAP (آزمون‌های regression در CI) رد می‌شود.
- **چگونه:**
  - `pip freeze` یا `pip freeze --all` را به `requirements.txt` بکشید و نسخه‌ها را pin کنید (Django 6.1.1 + پکیج‌های مستقیماً وارد شده).
  - یک workflow ساده در GitHub (یا GitLab) تعریف کنید: `npm ci` + `npm run build:css` → `python manage.py check` → `makemigrations --check` → `python manage.py test`.
