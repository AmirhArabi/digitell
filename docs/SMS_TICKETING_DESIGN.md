# طراحی ارسال پیامک برای تیکت‌های پشتیبانی — SMS.ir (آی‌پی‌پنل)

وضعیت: **طراحی و مستندسازی (بدون تغییر کد)** — ۲۰۲۶/۰۸/۲۱
تصمیم ثبت‌شده: اجرای عملیاتی هنگام انجام است؛ ارائه‌دهنده انتخابی: **SMS.ir / آی‌پی‌پنل**.

این سند پاسخ به نیاز زیر است:

> هر پیامی که در بخش تیکتینگ ثبت می‌شود یک پیامک بفرستد؛ پیام مدیر/کارشناس → پیامک برای مشتری، پیام مشتری → پیامک برای پشتیبانی.

---

## ۱. دامنه

**داخل دامنه**

- ارسال پیامک هنگام ساخت هر `TicketMessage` در دو مسیر (مشتری و پنل).
- ثبت حسابرسانهٔ هر ارسال در دیتابیس (`SmsLog`) با وضعیت و پاسخ خام پنل.
- غیرفعال بودن پیش‌فرض قابلیت تا زمان تنظیم کلید API و قالب پیامک.
- شکستن پیامک **هرگز** نباید ارسال پیام تیکت یا کار کردن صفحه را مختل کند.

**خارج از دامنه** (فعلاً)

- کمپین/ارسال انبوه، OTP، بازاریابی، ایمیل تراکنشی.
- ارسال هنگام تغییر وضعیت یا بستن تیکت (رویداد پیام نیست؛ قابل افزودن بعداً).
- صف پیشرفته (Celery/Redis) — بخش ۱۰ مسیر ارتقا را توضیح می‌دهد.

---

## ۲. تصمیم‌های کلیدی

| تصمیم | انتخاب | چرا | جایگزین ردشده |
|---|---|---|---|
| محل کد | دو ماژول کوچک درون اپ موجود (`tickets/sms.py` + مدل `SmsLog` در `tickets/models.py`) | کمترین تغییر ساختاری؛ تیکتینگ مدل و تمپلیت خودش را دارد | اپ جدید `sms/` (به `INSTALLED_APPS` و migration جدا نیاز دارد، بی‌جهت) |
| کلاینت HTTP | **`urllib.request` پایتون (stdlib)** | در venv پروژه نه `requests` نه `urllib3` نصب است و اصلاً `requirements.txt` وجود ندارد؛ وابستگی جدید = عمیق‌تر کردن آن خلاصه | `requests` (بدون manifest نسخه‌دار، خلاف ROADMAP فاز ۰) |
| زمان ارسال | `transaction.on_commit` + `try/except` سراسری | شبکه نباید داخل تراکنش باشد؛ خطای پنل نباید رول‌بک یا ۵۰۰ بدهد | ارسال داخل تراکنش (تایماوت، رول‌بک، صفحه ۵۰۰) |
| صف | **سنکرون با تایماوت ۸ ثانیه**، فعلاً | Celery/Redis در پروژه نیست | راه‌اندازی صف برای یک قابلیت (هزینهٔ زیرساخت بیشتر از فایده در این حجم) |
| فعال بودن | `SMS_TICKETING_ENABLED=False` پیش‌فرض | بدون کلید و قالبِ تأییدشده، ارسالِ بی‌هدف فقط اعتبار می‌سوزاند | فعال بودن پیش‌فرض |
| جایگزینی پنل | لایهٔ آداپتر (`SmsSender` interface) | عوض شدن پنل = تغییر یک فایل، نه کل جریان | اتصال مستقیم `urllib` در ویوها (پراکندگی، سختی تعویض) |
| مقصد پشتیبانی | یک یا چند شمارهٔ ثابت از env (mode پیش‌فرض) | پیش‌بینی‌پذیر، هزینه ثابت، از دست‌رفتن اطلاع مشتری به شمارهٔ شخصی کارشناس جلوگیری می‌کند | شمارهٔ کارشناس تیکت به‌عنوان پیش‌فرض (mode اختیاری موجود) |
| جلوگیری از ارسال تکراری | قید یکتای `(message, direction)` روی `SmsLog` | ارسال دوبارهٔ فرم یا replay نباید دو پیامک بدهد | بدون قید یکتایی (پیامک تکراری + هزینهٔ دوباره) |

---

## ۳. معماری پیشنهادی

```
tickets/
├── models.py          # + class SmsLog  (لاگ هر ارسال؛ migration جدید)
├── sms.py             # جدید: آداپتر + سرویس notify_ticket_message()
├── views.py           # خطوط اتصال: ticket_create_view، ticket_reply_view
dashboard/
└── views.py           # خط اتصال: ticket_detail_view (action='reply')
config/
└── settings.py        # + بلوک SMS_TICKETING_* خوانده‌شده از environment
```

جریان داده:

```
TicketMessage.create(...)                       # داخل تراکنشِ نما
   └─ notify_ticket_message(ticket, message)     # فقط تصمیم + ثبت SmsLog(pending)
        └─ transaction.on_commit(_deliver)       # بعد از کامیتِ موفق
             └─ SmsSender.send(to, text)         # urllib → api.sms.ir  (تایماوت ۸s)
                  └─ SmsLog → sent / failed (+ پاسخ خام)
```

نکته: اگر تراکنش رول‌بک شود، `on_commit` اصلاً اجرا نمی‌شود → **پیامک بدون پیامِ تیکت ارسال نمی‌شود** (این خاصیت، دلیل اصلی انتخاب `on_commit` است).

---

## ۴. نقاط اتصال دقیق در کد فعلی

| رویداد | فایل / تابع | جهت پیامک | مقصد |
|---|---|---|---|
| ثبت تیکت جدید (اولین پیام) | `tickets/views.py` → `ticket_create_view` | `to_staff` | شماره‌های پشتیبانی |
| پاسخ مشتری | `tickets/views.py` → `ticket_reply_view` | `to_staff` | شماره‌های پشتیبانی |
| پاسخ کارشناس/مدیر | `dashboard/views.py` → `ticket_detail_view`، شاخهٔ `action == 'reply'` (حدود خط ۱۸۹۵) | `to_customer` | `ticket.user.phone_number` |

جزئیات مهم موجود در کد که طرح باید رعایت کند:

- در پاسخ پنل، اگر `assigned_to_id` خالی باشد، خودِ نما کارشناس را `request.user` می‌کند و **بعد** `ticket.save()` می‌زند؛ بنابراین انتخاب مقصد پشتیبان باید **بعد از** این ذخیره انجام شود.
- اگر تیکت بسته باشد، پاسخ پنل اول `status` را به `in_progress` برمی‌گرداند؛ پیامک همان لحظه ارسال می‌شود (رویداد مقدّم است).
- تیکتِ بسته را مشتری نمی‌تواند پیام بدهد (`ticket_reply_view` جلوی آن را می‌گیرد)، پس حالت «پیامک به مشتریِ تیکتِ بسته» فقط از مسیر پنل ساخته می‌شود که مجاز است.
- **هرگز به فرستندهٔ خود پیامک نزنید**: پیام مشتری فقط به پشتیبانی، پیام پشتیبان فقط به مشتری.

رویدادهایی که فعلاً پیامک ندارند ولی نقطهٔ اتصال آماده دارند: تغییر وضعیت از ستون کناری (`action == 'status'`)، بستن تیکت توسط مشتری (`ticket_close_view`).

---

## ۵. مدل داده: `SmsLog`

در `tickets/models.py` (همان اپ، کمترین جابه‌جایی):

```python
class SmsLog(models.Model):
    DIRECTION_TO_CUSTOMER = 'to_customer'   # پاسخ کارشناس → مشتری
    DIRECTION_TO_STAFF = 'to_staff'         # پیام مشتری → پشتیبانی
    DIRECTION_CHOICES = [(DIRECTION_TO_CUSTOMER, 'به مشتری'), (DIRECTION_TO_STAFF, 'به پشتیبانی')]

    STATUS_PENDING = 'pending'    # ثبت شده، هنوز ارسال نشده (داخل تراکنش)
    STATUS_SENT = 'sent'          # پنل پذیرفت
    STATUS_FAILED = 'failed'      # خطای شبکه/پاسخ ناموفق
    STATUS_SKIPPED = 'skipped'    # شرط نداشتن شماره/قالب/غیرفعالی
    STATUS_CHOICES = [...]

    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='sms_logs')
    message = models.ForeignKey(
        'tickets.TicketMessage', on_delete=models.SET_NULL, null=True, blank=True, related_name='sms_logs'
    )
    direction = models.CharField(max_length=15, choices=DIRECTION_CHOICES)
    receiver = models.CharField(max_length=15)          # شمارهٔ مقصد (mask برای نمایش)
    body = models.TextField()                            # متن دقیقِ ارسال‌شده (Snapshot)
    template_code = models.CharField(max_length=64, blank=True, default='')  # کد الگو در صورت استفاده
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    provider_message_id = models.CharField(max_length=40, blank=True, default='')
    provider_response = models.TextField(blank=True, default='')   # JSON خام (برای دیباگ)
    error = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'پیامک ارسال‌شده'
        verbose_name_plural = 'لاگ پیامک‌های تیکت'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['message', 'direction'], name='uniq_sms_per_message_direction')
        ]
        indexes = [models.Index(fields=['status', '-created_at'])]
```

نکته‌ها

- `message` می‌تواند `SET_NULL` شود (حذف پیام/کاربر) ولی `body` snapshot می‌ماند → حسابرسی از بین نمی‌رود.
- قید یکتای `(message, direction)` مانع پیامک تکراری می‌شود: در صورت تکرار، `get_or_create` برمی‌گرداند و ارسال انجام **نمی‌شود**.
- `receiver` را به‌صورت mask ذخیره کنید (`0912***4567`)؛ شمارهٔ کامل مشتری از قبل در `User.phone_number` هست و نگهداری دوبارهٔ آن در لاگ، ریسک حریم خصوصی است (به ROADMAP «سیاست نگهداری داده» هم مرتبط است).
- migration: `python manage.py makemigrations tickets` (تنها فایل migration جدید در این قابلیت).

---

## ۶. تنظیمات و secretها

از آنجا که `config/settings.py` هنوز `SECRET_KEY` را hardcode دارد و انتقال به environment در فاز ۰ ROADMAP است، بلوک SMS را **همان‌جا env-محور** می‌نویسیم تا اولین قدمِ عملیِ آن فاز هم زده شود. `.env` از قبل در `.gitignore` هست (خطوط ۲۷–۳۱).

| متغیر | نمونه | توضیح |
|---|---|---|
| `SMS_TICKETING_ENABLED` | `0` | کلید اصلی؛ فقط `1/true/yes` روشن می‌کند |
| `SMS_PROVIDER` | `ippanel` | فقط برای شفافیت؛ آداپتر فعلاً یکی است |
| `SMS_API_KEY` | `<کلید وب‌سرویس>` | **secret** — فقط env، هرگز در کد/لاگ/تمپلیت |
| `SMS_FROM` | `1000xxxxxx` | شناسه/خط ارسالِ فعال در پنل شما |
| `SMS_TIMEOUT_SECONDS` | `8` | تایماوت درخواست HTTP |
| `SMS_TEMPLATE_TO_CUSTOMER` | `xxxxx` | کد/شناسهٔ الگوی اطلاع‌رسانی به مشتری؛ خالی = متن آزاد |
| `SMS_TEMPLATE_TO_STAFF` | `xxxxx` | کد/شناسهٔ الگوی اطلاع‌رسانی به پشتیبانی؛ خالی = متن آزاد |
| `SMS_STAFF_NUMBERS` | `09120000000,09350000000` | مقاصد پشتیبانی (جداشده با کاما) |
| `SMS_STAFF_MODE` | `fixed` | `fixed` = فقط شماره‌های بالا؛ `assigned` = شمارهٔ کارشناس تیکت؛ `both` = هر دو |
| `SMS_MAX_PER_TICKET_PER_DAY` | `50` | کفِ ایمن در برابر حلقهٔ پاسخ‌های خودکار/ربات |
| `SMS_BODY_MAX_CHARS` | `160` | حداکثر طول متن ارسالی (یک پیامک) |

نمونهٔ `.env` (بدون مقدار واقعی):

```env
SMS_TICKETING_ENABLED=0
SMS_PROVIDER=ippanel
SMS_API_KEY=
SMS_FROM=
SMS_TIMEOUT_SECONDS=8
SMS_TEMPLATE_TO_CUSTOMER=
SMS_TEMPLATE_TO_STAFF=
SMS_STAFF_NUMBERS=09xxxxxxxxx
SMS_STAFF_MODE=fixed
SMS_MAX_PER_TICKET_PER_DAY=50
SMS_BODY_MAX_CHARS=160
```

نکتهٔ امنیتی: خطاها و `provider_response` هرگز نباید کلید را شامل شوند؛ در ثبت خطا فقط status code و پیام پنل ذخیره شود.

---

## ۷. ساختار آداپتر (نمونهٔ طراحی)

```python
# tickets/sms.py
from __future__ import annotations
import json, urllib.request, urllib.error
from django.conf import settings
from django.db import transaction
from django.utils import timezone

class SmsResult:
    def __init__(self, ok, provider_id='', raw='', error=''): ...

class IppanelSender:
    """آداپتر SMS.ir / آی‌پی‌پنل — تنها نقطهٔ وابسته به مستندات پنل."""
    BASE = 'https://api.sms.ir/v1/'          # ← باید از مستندات رسمی تأیید شود (بخش ۱۴)

    def send(self, to: str, text: str) -> SmsResult:
        payload = {'to': to, 'message': text, 'from': settings.SMS_FROM}
        headers = {'Content-Type': 'application/json',
                   'X-API-KEY': settings.SMS_API_KEY}   # ← نام هدر تأیید نشده (بخش ۱۴)
        # urllib.request با timeout=SMS_TIMEOUT_SECONDS
        # هرگز استثنا بیرون نمی‌دهد: HTTPError / URLError / Timeout → SmsResult(ok=False)

def notify_ticket_message(*, ticket, message) -> None:
    """نقطهٔ اتصال واحد؛ در هر سه نقطهٔ جدول بخش ۴ صدا زده می‌شود."""
    if not settings.SMS_TICKETING_ENABLED:
        return
    direction = 'to_customer' if message.is_staff_message else 'to_staff'
    # 1) مقصد + نرمال‌سازی شماره (ارقام فارسی→لاتین، 09… / +98 → قالب پنل)
    # 2) ساخت متن (بخش ۸) و ثبت SmsLog(pending) با get_or_create روی (message, direction)
    # 3) transaction.on_commit(lambda: _deliver(log_pk))
```

قوانین `_deliver`:

```
اگر log از قبل sent است            → خروج (جلوگیری از ارسال تکراری)
اگر مقصد خالی/نامعتبر              → status=skipped + دلیل، بدون فراخوانی شبکه
اگر سقف روزانهٔ تیکت پر شد          → status=skipped + دلیل
فراخوانی sender.send(...) با try/except سراسری
success → status=sent + provider_message_id + sent_at
failure → status=failed + error (کوتاه، بدون کلید) + provider_response
هر دو شاخه: فقط به‌روزرسانی SmsLog؛ هیچ استثنایی به بالا پرتاب نمی‌شود
```

---

## ۸. متن پیامک‌ها و الگو (قالب)

دو متن پیشنهادی، هر دو **تک‌پیامکی** (≤ ۱۶۰ کاراکتر با شمارش فارسی):

**به مشتری** (پاسخ کارشناس):

```
پاسخ جدید به تیکت {ticket_number} در زیترو:
{subject}
{snippet ۸۰ کاراکتری از متن پاسخ}
مشاهده: {.Absolute_URL صفحهٔ تیکت}
```

**به پشتیبانی** (پیام مشتری):

```
پیام جدید مشتری {نام یا شماره} در تیکت {ticket_number}:
{subject}
{snippet ۸۰ کاراکتری}
```

نکته‌ها:

- `subject` و snippet را با `…` قطع کنید تا از سقف عبور نکنند؛ اعداد در متن فارسی باشند (هم‌خوانی با زبان پنل).
- اگر از **الگو (پترن/قالب)** استفاده شود، متن آزاد معنا ندارد: متغیرها باید دقیقاً با نام‌هایی که در پنل ثبت کرده‌اید بیایند (مثلاً `{#ticket_number}` `{#subject}` `{#snippet}` `{#link}`) و طول هر متغیر سقف دارد. دو قالب جدا ثبت کنید (یکی برای مشتری، یکی برای پشتیبانی) چون متن‌ها متفاوت‌اند.
- متن آزاد در برابر الگو: پیامک تراکنشی به شماره‌های موبایل معمولاً به خط خدماتی/الگوی تأییدشده نیاز دارد (بسته به قوانین و خط فعال شما در پنل). **این را باید از پنل خودتان تأیید کنید** — اگر خط شما متن آزاد می‌پذیرد، `SMS_TEMPLATE_*` را خالی بگذارید و همان متن بخش ۸ ارسال می‌شود؛ در غیر این صورت قالب ثبت و کدش را در همان متغیرها بگذارید. طرح طوری نوشته شده که هر دو حالت فقط با تنظیم env جابه‌جا می‌شوند.

---

## ۹. مرزها و رفتار در خطاها

| شرایط | رفتار |
|---|---|
| `SMS_TICKETING_ENABLED=0` | بدون ثبت لاگ، بدون شبکه؛ صفر هزینه و صرفاً نادیده گرفتن |
| شمارهٔ مشتری خالی/null (`User.phone_number` اختیاری است) | `SmsLog(skipped, 'no_receiver')` |
| شماره با ارقام فارسی یا `+98` ذخیره شده | نرمال‌سازی قبل از ارسال؛ اگر با `09` شروع نشد و اعتبار نگرفت → `skipped` |
| پنل ۵۰۰/تایماوت/بدون اینترنت | پیام تیکت **قبلاً ثبت شده**؛ `SmsLog(failed)`؛ صفحه ۲۰۰، پیام موفقیت نمایش داده می‌شود |
| ارسال دوبارهٔ همان فرم (double submit) | قید یکتایی → فقط یک پیامک |
| کلید نامعتبر/اعتبار صفر | `failed` با پیام کوتاه پنل؛ هیچ اثری روی درخواست کاربر ندارد |
| سقف `SMS_MAX_PER_TICKET_PER_DAY` | `skipped` — جلوی حلقهٔ پاسخ ربات‌گونه را می‌گیرد |
| فرستندهٔ خود پیام | هرگز مقصد پیامک نیست |
| حذف تیکت/پیام بعد از ارسال | `SmsLog.message → SET_NULL`؛ لاگ و snapshot متن می‌ماند |

**هزینه و تجربهٔ کاربر:** هر رفت‌وبرگشت گفتگو ≈ ۲ پیامک؛ یک گفتگوی ۱۰ پیامی ≈ ۸–۱۰ پیامک. سقف روزانهٔ هر تیکت + قطع‌کردن ارسال به فرستنده، دو کنترل اصلی‌اند. اگر حجم روزانه از حدود صدها پیامک گذشت، بخش ۱۰ را اجرا کنید.

**حریم خصوصی:** متن پیام در `SmsLog` ذخیره می‌شود (لازم برای حسابرسی)؛ پاک‌سازی دوره‌ای آن را با سیاست نگهداری دادهٔ ROADMAP هماهنگ کنید.

---

## ۱۰. مسیر ارتقا (اگر حجم زیاد شد)

1. ارسال سنکرون فعلی (تایماوت ۸s → بدترین حالت ۸ ثانیه تأخیر در پاسخ سرور، فقط وقتی پنل down است).
2. ارتقا به صف با Celery/Redis + worker: همان تابع `notify_ticket_message` بدون تغییر امضا؛ فقط جای `on_commit(_deliver)` با `delay(_deliver)`. مسیر این ارتقا از همان ابتدا باز نگه داشته شده (تابع، لاگ و قید یکتایی هیچ‌کدام به سینکرون وابسته نیستند).
3. در صورت نیاز: دریافت status تحویل پیامک از پنل و به‌روزرسانی `SmsLog.status` (نیازمند endpoint وضعیت؛ بخش ۱۴).

---

## ۱۱. تست‌های موردنیاز (پیش از فعال‌سازی)

همه با `unittest.mock.patch` روی آداپتر و `self.captureOnCommitCallbacks(execute=True)` برای `on_commit` — بدون تماس شبکه:

1. غیرفعال بودن → نه `SmsLog` ساخته می‌شود نه فراخوانی شبکه.
2. پاسخ کارشناس → یک `SmsLog(to_customer, sent)` با متنِ حاوی شمارهٔ تیکت.
3. پیام مشتری و ثبت تیکت جدید → `SmsLog(to_staff, sent)`.
4. مقصد خالی (`phone_number=None`) → `skipped` و بدون فراخوانی شبکه.
5. پاسخ ناموفق پنل (HTTP 500/timeout) → پیام تیکت ثبت می‌شود، `SmsLog(failed)`، هیچ exceptionای به نما نمی‌رسد.
6. فراخوانی دوبارهٔ `notify_ticket_message` برای همان پیام → فقط یک ارسال (قید یکتایی).
7. ارسال دوبارهٔ همان POST (double submit) → یک پیامک.
8. نرمال‌سازی شماره (`۰۹۱۲…`، `+98912…`، فاصله).
9. `SMS_STAFF_MODE=assigned` در مقابل `fixed`.
10. سقف روزانه → `skipped`.
11. رول‌بک تراکنش → هیچ پیامک و هیچ لاگی باقی نمی‌ماند.
12. متن فعال/الگو: رندر الگو با متغیرهای ثبت‌شده و قطع snippet در سقف کاراکتر.

(این ۱۲ تست به پوشهٔ `tickets/tests.py` کنار ۳۱ تست فعلی اضافه می‌شوند.)

---

## ۱۲. چک‌لیست سمت پنل شما (پیش از فعال‌سازی)

- [ ] ساخت **کلید وب‌سرویس** در پنل (مسیری شبیه `app.sms.ir/developer` در مستندات قدیمی SMS.ir — در پنل آی‌پی‌پنل معادل آن را پیدا کنید).
- [ ] فعال‌سازی/انتخاب **خط ارسال** و ثبت شناسهٔ آن در `SMS_FROM`.
- [ ] تصمیم دربارهٔ متن آزاد در برابر **الگو**: اگر الگو لازم است، دو قالب (مشتری/پشتیبانی) ثبت و کدها را در `SMS_TEMPLATE_*` بگذارید.
- [ ] شارژ اعتبار و تست اولیه با شمارهٔ خودتان.
- [ ] قرار دادن `SMS_API_KEY` در `.env` (یا secret manager سرور) و روشن کردن `SMS_TICKETING_ENABLED=1`.
- [ ] اجرای کامل تست‌ها و یک گفتگوی واقعی آزمایشی در دو سمت.

---

## ۱۳. ترتیب اجرای پیشنهادی (هنگام شروع کار)

1. بلوک تنظیمات در `config/settings.py` + نمونهٔ `.env`.
2. `SmsLog` در `tickets/models.py` + migration.
3. `tickets/sms.py` (آداپتر + `notify_ticket_message`).
4. اتصال سه نقطهٔ بخش ۴.
5. ۱۲ تست بخش ۱۱ و اجرای کل مجموعه (۶۶ تست فعلی نباید بشکنند).
6. مستندسازی نهایی در `README`/`docs` + بررسی دستی در Preview.
7. فقط پس از تکمیل چک‌لیست بخش ۱۲: فعال‌سازی با یک تیکت آزمایشی.

---

## ۱۴. اطلاعاتی که باید از مستندات رسمی تأیید شود

> **راستی‌آزمایی نشده**: در محیط اجرای این کار، ابزار خواندن صفحات وب به‌دلیل محدودیت DNS (نام دامنه به آدرس خصوصی resolve می‌شود) نتوانست صفحات را باز کند؛ بنابراین موارد زیر از **snippetهای نتایج جست‌وجو** آمده‌اند، نه از خودِ صفحات. پیش از پیاده‌سازی باید دستی در پنل/مستندات خودتان تأیید شوند:

- آدرس پایه و endpoint ارسال تکی — نتایج جست‌وجو به `https://api.sms.ir/v1/send` و `https://api.sms.ir/v1/send/bulk` اشاره می‌کنند.
- نام هدر احراز هویت — نتایج به `X-API-KEY` اشاره می‌کنند (فرمت: کلید وب‌سرویس پس از ساخت در پنل).
- شکل payload پاسخ (فیلدهای id/status/…) و endpoint دریافت وضعیت تحویل.
- endpoint و payload ارسال با **الگو/پترن** در آی‌پی‌پنل، و فرایند ثبت قالب.
- سقف نرخ ارسال و قیمت هر پیامک (برای محاسبهٔ سقف روزانه).

صفحاتی که باید بررسی شوند:

- https://sms.ir/rest-api/
- https://sms.ir/web-service/
- https://ippanelcom.github.io/Edge-Document/docs/
- https://apidoc.ippanel.com/
- https://github.com/ippanel/python-rest-sdk

اگر مستندات را در اختیار بگذارید (متن یا PDF)، بخش‌های نامبرده در آداپتر دقیق می‌شوند.

---

## ۱۵. ارتباط با وضعیت فعلی پروژه

- تیکتینگ همین حالا سالم است: ۶۶ تست پاس، `manage.py check` بدون مشکل (شامل ۳۱ تست ماژول `tickets` که قبلاً صفر تست داشت).
- این سند **هیچ کدی را تغییر نمی‌دهد**؛ صرفاً طرح و چک‌لیست اجراست.
- با پیاده‌سازی، مورد ROADMAP («ایمیل/SMS تراکنشی پس از انتخاب provider») نیمه‌فعال می‌شود: provider انتخاب شده، کار اجرایی باقی می‌ماند.
