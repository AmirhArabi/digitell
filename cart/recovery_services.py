import secrets
import string
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from accounts.services import normalize_phone, send_sms
from orders.models import Coupon, Order
from .models import Cart, RecoveryAttempt, RecoveryCampaign


def get_abandoned_carts(threshold_hours=24):
    """
    یافتن سبدهای خریدی که:
    ۱. خالی نیستند
    ۲. حداقل threshold_hours از آخرین بروزرسانی آن‌ها گذشته
    ۳. تبدیل به سفارش نشده‌اند
    ۴. در وضعیت‌های نهایی (recovered یا excluded) قرار ندارند
    """
    cutoff = timezone.now() - timedelta(hours=threshold_hours)
    return (
        Cart.objects.filter(
            items__isnull=False,
            converted_order__isnull=True,
            updated_at__lte=cutoff,
        )
        .exclude(recovery_status__in=['recovered', 'excluded'])
        .distinct()
        .prefetch_related('items__product')
        .select_related('user')
    )


def is_cart_eligible_for_recovery(cart: Cart, campaign: RecoveryCampaign = None):
    """
    اعتبارسنجی صلاحیت سبد خرید برای دریافت پیامک بازیابی:
    - سبد خالی نباشد
    - سفارش ثبت نشده باشد
    - شماره تماس معتبر داشته باشد
    - کاربر انصراف پیامکی نداده باشد (sms_marketing_subscribed)
    - وضعیت سبد excluded یا recovered نباشد
    - سقف تعداد تلاش رعایت شده باشد
    - حداقل ارزش سبد رعایت شده باشد
    """
    if cart.is_empty:
        return False, "سبد خرید خالی است."

    if cart.converted_order_id:
        return False, "سبد قبلاً به سفارش تبدیل شده است."

    phone = cart.customer_phone
    if not phone:
        return False, "شماره موبایلی برای این سبد یافت نشد."

    norm_phone = normalize_phone(phone)
    if not norm_phone or len(norm_phone) != 11 or not norm_phone.startswith('09'):
        return False, f"شماره موبایل نامعتبر است: {phone}"

    # بررسی رضایت پیامکی اگر کاربر لاگین است
    if cart.user and hasattr(cart.user, 'sms_marketing_subscribed'):
        if not cart.user.sms_marketing_subscribed:
            return False, "کاربر از دریافت پیامک‌های بازاریابی انصراف داده است."

    if cart.recovery_status == 'excluded':
        return False, "این سبد توسط مدیر یا سیستم از چرخه پیگیری مستثنا شده است."

    if cart.recovery_status == 'recovered':
        return False, "این سبد قبلاً با موفقیت بازیابی شده است."

    max_attempts = campaign.max_attempts_per_cart if campaign else 3
    if cart.attempts_count >= max_attempts:
        return False, f"سقف دفعات ارسال پیامک ({max_attempts}) تکمیل شده است."

    min_value = campaign.min_cart_value if campaign else 0
    if cart.total_price < min_value:
        return False, f"ارزش سبد کمتر از حداقل تعیین‌شده ({min_value:,} تومان) است."

    return True, "واجد شرایط بازیابی"


def generate_recovery_token(cart: Cart, validity_hours: int = 72) -> str:
    """تولید و ذخیره توکن امن بازگشت به سبد با مهلت انقضا."""
    token = secrets.token_urlsafe(32)
    cart.recovery_token = token
    cart.recovery_token_expires_at = timezone.now() + timedelta(hours=validity_hours)
    cart.save(update_fields=['recovery_token', 'recovery_token_expires_at'])
    return token


def build_recovery_url(cart: Cart, base_url: str = '') -> str:
    """ساخت لینک امن بازیابی سبد خرید."""
    token = cart.recovery_token
    if not token or (cart.recovery_token_expires_at and cart.recovery_token_expires_at < timezone.now()):
        token = generate_recovery_token(cart)

    path = f"/cart/recover/{token}/"
    if base_url:
        return f"{base_url.rstrip('/')}{path}"
    return path


def create_recovery_coupon(
    cart: Cart,
    campaign: RecoveryCampaign = None,
    created_by=None,
    discount_type: str = 'percent',
    discount_value: int = 10,
    validity_hours: int = 48,
    min_order_amount: int = 0,
    max_discount_amount: int = None,
) -> Coupon:
    """ایجاد یک کد تخفیف یکبارمصرف اختصاصی کاربر برای بازیابی سبد خرید."""
    if campaign:
        discount_type = campaign.discount_type
        discount_value = campaign.discount_value
        validity_hours = campaign.discount_validity_hours
        min_order_amount = campaign.discount_min_order
        max_discount_amount = campaign.discount_max_amount

    # تولید کد یکتا مثل RET-A9C3F1
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    code = f"RET-{random_part}"

    now = timezone.now()
    valid_until = now + timedelta(hours=validity_hours)

    title = f"تخفیف بازیابی سبد {cart.id}"
    if campaign:
        title = f"کمپین {campaign.name} - سبد {cart.id}"

    coupon = Coupon.objects.create(
        code=code,
        title=title,
        discount_type=discount_type,
        value=discount_value,
        min_order_amount=min_order_amount,
        max_discount_amount=max_discount_amount,
        max_uses=1,
        used_count=0,
        valid_from=now,
        valid_until=valid_until,
        is_active=True,
        for_user=cart.user,
        source='cart_recovery',
    )
    return coupon


def send_recovery_attempt(
    cart: Cart,
    campaign: RecoveryCampaign = None,
    step: int = 1,
    message_type: str = 'reminder',
    custom_text: str = None,
    include_coupon: bool = False,
    base_url: str = '',
    dry_run: bool = False,
) -> tuple[bool, str, RecoveryAttempt]:
    """
    انجام یک تلاش برای بازیابی سبد:
    ۱. بررسی مجدد صلاحیت درست پیش از ارسال
    ۲. ساخت کلید Idempotency
    ۳. ساخت توکن و لینک بازگشت
    ۴. تولید کد تخفیف اختصاصی در صورت نیاز
    ۵. فرمت متن پیام
    ۶. ثبت لاگ تلاش
    ۷. ارسال پیامک واقعی یا شبیه‌سازی (dry_run)
    ۸. بروزرسانی وضعیت
    """
    eligible, reason = is_cart_eligible_for_recovery(cart, campaign)
    phone = cart.customer_phone

    idempotency_key = f"cart-{cart.id}-step-{step}-{uuid.uuid4().hex[:12]}"

    if not eligible:
        attempt = RecoveryAttempt.objects.create(
            cart=cart,
            campaign=campaign,
            step=step,
            message_type=message_type,
            status='skipped',
            recipient_phone=phone or '',
            skip_reason=reason,
            idempotency_key=idempotency_key,
        )
        return False, f"ارسال لغو شد: {reason}", attempt

    recovery_url = build_recovery_url(cart, base_url=base_url)
    customer_name = cart.customer_display_name

    coupon = None
    coupon_code = ""
    discount_desc = ""

    if include_coupon or message_type == 'discount':
        coupon = create_recovery_coupon(cart, campaign=campaign)
        coupon_code = coupon.code
        if coupon.discount_type == 'percent':
            discount_desc = f"{coupon.value}٪ تخفیف"
        else:
            discount_desc = f"{coupon.value:,} تومان تخفیف"

    if custom_text:
        text = custom_text
        text = text.replace('{name}', customer_name)
        text = text.replace('{cart_url}', recovery_url)
        text = text.replace('{coupon_code}', coupon_code)
        text = text.replace('{discount_desc}', discount_desc)
    elif campaign:
        template = campaign.message_template_step2 if step == 2 else campaign.message_template_step1
        text = template.replace('{name}', customer_name)
        text = text.replace('{cart_url}', recovery_url)
        text = text.replace('{coupon_code}', coupon_code)
        text = text.replace('{discount_desc}', discount_desc)
    else:
        if coupon:
            text = f"سلام {customer_name} عزیز، سبد خرید شما در دیجی تل منتظر شماست. با کد {coupon_code} از {discount_desc} بهره‌مند شوید: {recovery_url}"
        else:
            text = f"سلام {customer_name} عزیز، اقلام منتظر شما در سبد خرید دیجی تل محفوظ است. برای تکمیل خرید کلیک کنید: {recovery_url}"

    norm_phone = normalize_phone(phone)

    attempt = RecoveryAttempt.objects.create(
        cart=cart,
        campaign=campaign,
        step=step,
        message_type=message_type,
        status='processing',
        recipient_phone=norm_phone,
        message_text=text,
        coupon=coupon,
        idempotency_key=idempotency_key,
    )

    if dry_run:
        attempt.status = 'sent'
        attempt.provider_message_id = 'DRY-RUN-SIMULATED'
        attempt.sent_at = timezone.now()
        attempt.save(update_fields=['status', 'provider_message_id', 'sent_at'])

        cart.recovery_status = 'contacted'
        cart.save(update_fields=['recovery_status'])
        return True, "ارسال آزمایشی (Dry-Run) با موفقیت ثبت شد.", attempt

    try:
        success = send_sms(norm_phone, text)
        if success:
            attempt.status = 'sent'
            attempt.provider_message_id = f"MOCK-SMS-{uuid.uuid4().hex[:8]}"
            attempt.sent_at = timezone.now()
            attempt.save(update_fields=['status', 'provider_message_id', 'sent_at'])

            cart.recovery_status = 'contacted'
            cart.save(update_fields=['recovery_status'])
            return True, "پیامک با موفقیت ارسال و ثبت شد.", attempt
        else:
            attempt.status = 'failed'
            attempt.error_detail = "سرویس پیامک پاسخ ناموفق داد."
            attempt.save(update_fields=['status', 'error_detail'])
            return False, "خطا در ارسال پیامک.", attempt
    except Exception as e:
        attempt.status = 'failed'
        attempt.error_detail = str(e)
        attempt.save(update_fields=['status', 'error_detail'])
        return False, f"خطای پیش‌بینی‌نشده در ارسال: {str(e)}", attempt


def process_automated_campaign(campaign: RecoveryCampaign = None, dry_run: bool = False, base_url: str = '') -> dict:
    """
    پردازش دسته‌ای سبدهای رهاشده بر اساس کمپین فعال:
    مرحله ۱ (Step 1): ارسال یادآوری اول پس از آستانه رهاشدگی + step1_delay_hours
    مرحله ۲ (Step 2): ارسال پیشنهاد تخفیف پس از مرحله ۱ + step2_delay_hours
    """
    now = timezone.now()
    if campaign is None:
        campaign = RecoveryCampaign.objects.filter(is_active=True).first()

    if not campaign or not campaign.is_currently_valid:
        return {'status': 'error', 'message': 'کمپین فعالی برای پردازش یافت نشد.'}

    threshold_hours = campaign.abandonment_threshold_hours
    step1_delay = campaign.step1_delay_hours
    step2_delay = campaign.step2_delay_hours

    # یافتن سبدهای بالقوه
    carts = get_abandoned_carts(threshold_hours=threshold_hours)

    stats = {
        'total_examined': carts.count(),
        'step1_sent': 0,
        'step2_sent': 0,
        'skipped': 0,
        'failed': 0,
    }

    for cart in carts:
        attempts = list(cart.recovery_attempts.all().order_by('created_at'))
        num_attempts = len(attempts)

        # مرحله اول
        if num_attempts == 0:
            # زمان بررسی گام اول: حداقل threshold + step1_delay از آخرین بروزرسانی گذشته باشد
            required_time = timedelta(hours=threshold_hours + step1_delay)
            if now - cart.updated_at >= required_time:
                ok, msg, attempt = send_recovery_attempt(
                    cart=cart,
                    campaign=campaign,
                    step=1,
                    message_type='reminder',
                    include_coupon=False,
                    base_url=base_url,
                    dry_run=dry_run,
                )
                if ok:
                    stats['step1_sent'] += 1
                elif attempt.status == 'skipped':
                    stats['skipped'] += 1
                else:
                    stats['failed'] += 1

        # مرحله دوم (تخفیف)
        elif num_attempts == 1:
            first_attempt = attempts[0]
            # آیا تأخیر مرحله دوم از زمان ارسال مرحله ۱ سپری شده است؟
            if first_attempt.sent_at and (now - first_attempt.sent_at >= timedelta(hours=step2_delay)):
                ok, msg, attempt = send_recovery_attempt(
                    cart=cart,
                    campaign=campaign,
                    step=2,
                    message_type='discount',
                    include_coupon=True,
                    base_url=base_url,
                    dry_run=dry_run,
                )
                if ok:
                    stats['step2_sent'] += 1
                elif attempt.status == 'skipped':
                    stats['skipped'] += 1
                else:
                    stats['failed'] += 1

    return stats


def track_order_recovery(order: Order, cart: Cart = None):
    """
    انتساب سفارش موفق یا ایجادشده به سبد خرید و تلاش بازیابی مربوطه.
    اگر کاربر سبد بازیابی‌شده داشت، سفارش به آن منتسب می‌شود.
    """
    if not cart and order.user_id:
        # جستجوی سبد کاربری که به سفارش متصل نشده و در وضعیت بازیابی بوده است
        cart = Cart.objects.filter(
            user=order.user,
            converted_order__isnull=True,
            recovery_status__in=['contacted', 'scheduled']
        ).first()

    if cart:
        cart.converted_order = order
        cart.recovery_status = 'recovered'
        cart.save(update_fields=['converted_order', 'recovery_status'])

        # علامت‌گذاری آخرین تلاش بازیابی
        last_attempt = cart.recovery_attempts.filter(status='sent').order_by('-sent_at').first()
        if last_attempt:
            last_attempt.converted_order = order
            last_attempt.converted_at = timezone.now()
            last_attempt.save(update_fields=['converted_order', 'converted_at'])

        return True
    return False
