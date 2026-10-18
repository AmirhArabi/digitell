import random
import logging
from datetime import timedelta
from django.utils import timezone
from .models import OTPCode, User

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """تبدیل ارقام فارسی/عربی، حذف فاصله‌ها و یکسان‌سازی شماره تلفن همراه ایران (09xxxxxxxxx)."""
    if not phone:
        return ""
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = str(phone).translate(trans)
    # Remove any non-digit character except optional leading +
    cleaned = ''.join(ch for ch in cleaned if ch.isdigit() or ch == '+')

    if cleaned.startswith('+98'):
        cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('98') and len(cleaned) == 12:
        cleaned = '0' + cleaned[2:]
    elif cleaned.startswith('9') and len(cleaned) == 10:
        cleaned = '0' + cleaned

    return cleaned


def send_sms(phone_number: str, message: str) -> bool:
    """
    ارسال پیامک (در محیط توسعه/شبیه‌سازی در کنسول و لاگ ثبت می‌شود
    و قابلیت اتصال به وب‌سرویس‌هایی مانند کاوه‌نگار، پیامک دات‌کام یا ملی‌پیامک را دارد).
    """
    norm_phone = normalize_phone(phone_number)
    log_msg = f"\n{'='*50}\n[SMS SENT TO {norm_phone}]:\n{message}\n{'='*50}\n"
    logger.info(log_msg)
    print(log_msg)
    return True


def generate_otp(phone_number: str, expiry_minutes: int = 2) -> tuple[str, OTPCode]:
    """تولید کد تأیید ۶ رقمی تصادفی، ذخیره در دیتابیس و ارسال پیامک."""
    norm_phone = normalize_phone(phone_number)
    # Invalidate previous unused codes for this phone
    OTPCode.objects.filter(phone_number=norm_phone, is_used=False).update(is_used=True)

    code = f"{random.randint(100000, 999999)}"
    now = timezone.now()
    expires_at = now + timedelta(minutes=expiry_minutes)

    otp_obj = OTPCode.objects.create(
        phone_number=norm_phone,
        code=code,
        expires_at=expires_at,
        is_used=False,
    )

    msg = f"کد تأیید ورود شما به دیجی تل: {code}\nاین کد به مدت ۲ دقیقه معتبر است."
    send_sms(norm_phone, msg)

    return code, otp_obj


def verify_otp(phone_number: str, code: str) -> bool:
    """بررسی صحت و اعتبار کد OTP ۶ رقمی و ابطال پس از استفاده."""
    norm_phone = normalize_phone(phone_number)
    clean_code = normalize_phone(code).strip()

    now = timezone.now()
    otp_obj = OTPCode.objects.filter(
        phone_number=norm_phone,
        code=clean_code,
        is_used=False,
        expires_at__gte=now,
    ).order_by('-created_at').first()

    if otp_obj:
        otp_obj.is_used = True
        otp_obj.save(update_fields=['is_used'])
        return True
    return False
