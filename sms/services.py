"""سرویس‌های متمرکز ارسال پیامک، مدیریت OTP، کمپین‌ها و ثبت لاگ."""

import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from django.conf import settings
from .models import SmsLog, SmsTemplate, SmsCampaign
from .sms_ir_client import SmsIrClient

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """تبدیل ارقام فارسی/عربی، حذف فاصله‌ها و یکسان‌سازی شماره تلفن همراه ایران (09xxxxxxxxx)."""
    if not phone:
        return ""
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = str(phone).translate(trans)
    cleaned = ''.join(ch for ch in cleaned if ch.isdigit() or ch == '+')

    if cleaned.startswith('+98'):
        cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('98') and len(cleaned) == 12:
        cleaned = '0' + cleaned[2:]
    elif cleaned.startswith('9') and len(cleaned) == 10:
        cleaned = '0' + cleaned

    return cleaned


def get_sms_client() -> Tuple[SmsIrClient, Any]:
    """دریافت کلاینت پیامک با خواندن مقادیر از SiteSetting یا settings.py."""
    try:
        from home.models import SiteSetting
        site_setting = SiteSetting.get_settings()
    except Exception:
        site_setting = None

    api_key = ""
    line_number = ""

    if site_setting:
        api_key = getattr(site_setting, 'sms_api_key', '') or ''
        line_number = getattr(site_setting, 'sms_line_number', '') or ''

    if not api_key:
        api_key = getattr(settings, 'SMS_IR_API_KEY', '') or ''
    if not line_number:
        line_number = getattr(settings, 'SMS_IR_LINE_NUMBER', '') or ''

    client = SmsIrClient(api_key=api_key, line_number=line_number)
    return client, site_setting


def send_sms(
    phone_number: str,
    message: str,
    sms_type: str = 'single',
    sender_user=None,
    template: Optional[SmsTemplate] = None,
) -> bool:
    """ارسال پیامک متنی به یک شماره همراه، ثبت لاگ و شبیه‌سازی در محیط تست/توسعه."""
    norm_phone = normalize_phone(phone_number)
    if not norm_phone:
        logger.warning("ارسال پیامک لغو شد: شماره تلفن نامعتبر است.")
        return False

    client, site_setting = get_sms_client()
    is_active = getattr(site_setting, 'sms_is_active', True) if site_setting else True

    # اگر کلید وب‌سرویس موجود بود و پنل فعال بود
    if client.is_configured and is_active:
        res = client.send_sms(norm_phone, message)
        status_code = res.get('status', 0)
        is_success = (status_code == 1)

        msg_data = res.get('data') or {}
        message_id = msg_data.get('messageId') if isinstance(msg_data, dict) else None
        cost = msg_data.get('cost', 0) if isinstance(msg_data, dict) else 0

        SmsLog.objects.create(
            recipient=norm_phone,
            message=message,
            sms_type=sms_type,
            status='sent' if is_success else 'failed',
            template=template,
            message_id=message_id,
            cost=cost or 0,
            response_data=json.dumps(res, ensure_ascii=False),
            error_message=res.get('message', '') if not is_success else '',
            sender_user=sender_user,
        )

        log_msg = f"\n{'='*50}\n[SMS SENT VIA SMS.IR TO {norm_phone}]:\n{message}\nResult: {res.get('message')}\n{'='*50}\n"
        logger.info(log_msg)
        print(log_msg)
        return is_success
    else:
        # حالت شبیه‌سازی / توسعه محلی
        SmsLog.objects.create(
            recipient=norm_phone,
            message=message,
            sms_type=sms_type,
            status='simulated',
            template=template,
            response_data=json.dumps({"simulated": True, "reason": "No API Key or inactive"}, ensure_ascii=False),
            sender_user=sender_user,
        )

        log_msg = f"\n{'='*50}\n[SMS SENT TO {norm_phone}]:\n{message}\n{'='*50}\n"
        logger.info(log_msg)
        print(log_msg)
        return True


def send_otp_sms(phone_number: str, code: str) -> Tuple[bool, str]:
    """ارسال کد یکبار مصرف (OTP) با اولویت پترن TemplateId در SMS.ir."""
    norm_phone = normalize_phone(phone_number)
    client, site_setting = get_sms_client()

    template_id = getattr(site_setting, 'sms_otp_template_id', '') if site_setting else ''
    if not template_id:
        template_id = getattr(settings, 'SMS_IR_OTP_TEMPLATE_ID', '')

    default_msg = f"کد تأیید ورود شما به دیجی تل: {code}\nاین کد به مدت ۲ دقیقه معتبر است."

    # اگر قالب پترن و کلید تنظیم شده باشد
    if template_id and client.is_configured:
        try:
            tid = int(template_id)
            res = client.send_verify_code(norm_phone, tid, Code=code)
            is_success = (res.get('status') == 1)

            SmsLog.objects.create(
                recipient=norm_phone,
                message=f"الگوی OTP (شناسه: {tid}) - کد: {code}",
                sms_type='otp',
                status='sent' if is_success else 'failed',
                pattern_template_id=tid,
                response_data=json.dumps(res, ensure_ascii=False),
                error_message=res.get('message', '') if not is_success else '',
            )
            log_msg = f"\n{'='*50}\n[OTP PATTERN SENT TO {norm_phone} (Template: {tid})]:\nCode: {code}\n{'='*50}\n"
            logger.info(log_msg)
            print(log_msg)
            return is_success, res.get('message', 'کد ارسال شد')
        except Exception as e:
            logger.error("خطا در ارسال پترن OTP: %s. بازگشت به پیامک متنی.", str(e))

    # در غیر این صورت پیامک متنی عادی ارسال می‌شود
    success = send_sms(norm_phone, default_msg, sms_type='otp')
    return success, "کد ارسال شد"


def send_pattern_sms(
    phone_number: str,
    template_id: int,
    parameters: Dict[str, str],
    sender_user=None,
    template: Optional[SmsTemplate] = None,
) -> Tuple[bool, str]:
    """ارسال پیامک با یک الگوی تأیید شده (پترن خدماتی SMS.ir)."""
    norm_phone = normalize_phone(phone_number)
    client, site_setting = get_sms_client()

    if client.is_configured:
        res = client.send_verify_code(norm_phone, template_id, **parameters)
        is_success = (res.get('status') == 1)

        summary_msg = f"الگوی {template_id} با پارامترهای: {parameters}"
        SmsLog.objects.create(
            recipient=norm_phone,
            message=summary_msg,
            sms_type='pattern',
            status='sent' if is_success else 'failed',
            template=template,
            pattern_template_id=template_id,
            response_data=json.dumps(res, ensure_ascii=False),
            error_message=res.get('message', '') if not is_success else '',
            sender_user=sender_user,
        )
        return is_success, res.get('message', '')
    else:
        # شبیه‌سازی
        summary_msg = f"[شبیه‌سازی] الگوی {template_id} با پارامترهای: {parameters}"
        SmsLog.objects.create(
            recipient=norm_phone,
            message=summary_msg,
            sms_type='pattern',
            status='simulated',
            template=template,
            pattern_template_id=template_id,
            sender_user=sender_user,
        )
        print(f"\n[SIMULATED PATTERN SMS TO {norm_phone}]: Template {template_id}, Params: {parameters}\n")
        return True, "ارسال در حالت شبیه‌سازی با موفقیت انجام شد."


def send_bulk_campaign_sms(
    phone_numbers: List[str],
    message: str,
    title: str = "کمپین پیامکی",
    audience: str = "custom",
    sender_user=None,
    template: Optional[SmsTemplate] = None,
) -> Dict[str, Any]:
    """ارسال پیامک گروهی و ثبت کمپین پیامکی."""
    cleaned_numbers = list(dict.fromkeys([normalize_phone(p) for p in phone_numbers if normalize_phone(p)]))
    if not cleaned_numbers:
        return {"status": 0, "message": "هیچ شماره معتبری یافت نشد."}

    client, site_setting = get_sms_client()

    campaign = SmsCampaign.objects.create(
        title=title,
        audience=audience,
        message=message,
        template=template,
        total_recipients=len(cleaned_numbers),
        created_by=sender_user,
        status='draft',
    )

    if client.is_configured:
        res = client.send_bulk_sms(cleaned_numbers, message)
        is_success = (res.get('status') == 1)

        msg_data = res.get('data') or {}
        pack_id = msg_data.get('packId') if isinstance(msg_data, dict) else None

        # ایجاد لاگ برای هر شماره
        logs = [
            SmsLog(
                recipient=num,
                message=message,
                sms_type='campaign',
                status='sent' if is_success else 'failed',
                template=template,
                pack_id=pack_id,
                response_data=json.dumps(res, ensure_ascii=False),
                error_message=res.get('message', '') if not is_success else '',
                sender_user=sender_user,
            )
            for num in cleaned_numbers
        ]
        SmsLog.objects.bulk_create(logs)

        campaign.status = 'sent' if is_success else 'failed'
        campaign.successful_count = len(cleaned_numbers) if is_success else 0
        campaign.failed_count = 0 if is_success else len(cleaned_numbers)
        campaign.save(update_fields=['status', 'successful_count', 'failed_count'])

        return {
            "status": 1 if is_success else 0,
            "message": res.get('message', 'کمپین ارسال شد'),
            "campaign_id": campaign.id,
            "count": len(cleaned_numbers),
        }
    else:
        # شبیه‌سازی
        logs = [
            SmsLog(
                recipient=num,
                message=message,
                sms_type='campaign',
                status='simulated',
                template=template,
                sender_user=sender_user,
            )
            for num in cleaned_numbers
        ]
        SmsLog.objects.bulk_create(logs)

        campaign.status = 'sent'
        campaign.successful_count = len(cleaned_numbers)
        campaign.save(update_fields=['status', 'successful_count'])

        print(f"\n[SIMULATED BULK SMS TO {len(cleaned_numbers)} NUMBERS]:\n{message}\n")
        return {
            "status": 1,
            "message": f"ارسال شبیه‌سازی شده برای {len(cleaned_numbers)} شماره ثبت گردید.",
            "campaign_id": campaign.id,
            "count": len(cleaned_numbers),
        }


def get_panel_status() -> Dict[str, Any]:
    """دریافت وضعیت اتصال، میزان شارژ و خطوط اختصاصی پنل پیامک."""
    client, site_setting = get_sms_client()

    data = {
        "is_configured": client.is_configured,
        "api_key_masked": (client.api_key[:6] + "..." + client.api_key[-4:]) if len(client.api_key) > 10 else ("تنظیم شده" if client.api_key else "تنظیم نشده"),
        "line_number": client.line_number or "پیش‌فرض",
        "otp_template_id": getattr(site_setting, 'sms_otp_template_id', '') if site_setting else '',
        "credit": None,
        "lines": [],
        "status_message": "آماده به کار",
    }

    if client.is_configured:
        # استعلام اعتبار
        credit_res = client.get_credit()
        if credit_res.get('status') == 1:
            data['credit'] = credit_res.get('data')

        # استعلام خطوط
        lines_res = client.get_line_numbers()
        if lines_res.get('status') == 1 and isinstance(lines_res.get('data'), list):
            data['lines'] = lines_res.get('data')
    else:
        data['status_message'] = "حالت شبیه‌سازی (کلید API وارد نشده است)"

    return data
