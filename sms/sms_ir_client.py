"""کلاینت ارتباطی با وب‌سرویس پیامک SMS.ir (نسخه ۲).

بر اساس پکیج رسمی IPeCompany/SmsPanelV2.Python:
- اندپوینت پایه: https://api.sms.ir
- هدر احراز هویت: X-API-KEY
- متد اعتبارسنجی پترن: /v1/send/verify/
- متد ارسال پیامک متنی/گروهی: /v1/send/bulk/
- متد استعلام اعتبار: /v1/credit/
- متد استعلام خطوط: /v1/line/
"""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SmsIrClient:
    ENDPOINT = "https://api.sms.ir"

    def __init__(self, api_key: str = "", line_number: Optional[str] = None):
        self.api_key = (api_key or "").strip()
        self.line_number = (str(line_number).strip() if line_number else "") or None

    @property
    def is_configured(self) -> bool:
        """بررسی آیا کلید وب‌سرویس تنظیم شده است یا خیر."""
        return bool(self.api_key)

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """ارسال درخواست HTTP استاندارد به API SMS.ir با urllib."""
        if not self.is_configured:
            # حالت شبیه‌سازی / توسعه
            return {
                "status": 1,
                "message": "حالت شبیه‌سازی (کلید API تنظیم نشده است)",
                "data": {"simulated": True, "path": path, "data": data},
                "simulated": True,
            }

        url = self.ENDPOINT + path
        if params:
            cleaned_params = {k: v for k, v in params.items() if v is not None}
            if cleaned_params:
                url += "?" + urllib.parse.urlencode(cleaned_params)

        headers = {
            "X-API-KEY": self.api_key,
            "ACCEPT": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Digitell-SMS-Client/2.0",
        }

        encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            url,
            data=encoded_data,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {"status": 1, "message": "OK"}
        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8") if e.fp else ""
            logger.error("خطای SMS.ir HTTP %s: %s", e.code, raw_err)
            try:
                parsed = json.loads(raw_err)
                return parsed
            except Exception:
                return {
                    "status": 0,
                    "message": f"خطای وب‌سرویس پیامک (کد {e.code})",
                    "error": raw_err,
                }
        except Exception as e:
            logger.error("خطای شبکه در اتصال به SMS.ir: %s", str(e))
            return {
                "status": 0,
                "message": f"خطا در ارتباط با سرور پیامک: {str(e)}",
            }

    def send_verify_code(
        self,
        number: str,
        template_id: int,
        **parameters: str,
    ) -> Dict[str, Any]:
        """ارسال پیامک با الگو/پترن اعتبارسنجی (عبور از بلک‌لیست مخابرات).
        
        نمونه ساختار:
        POST /v1/send/verify/
        {
            "Mobile": "0912...",
            "TemplateId": 123456,
            "Parameters": [{"name": "Code", "value": "1234"}]
        }
        """
        payload = {
            "Mobile": str(number).strip(),
            "TemplateId": int(template_id),
            "Parameters": [
                {"name": str(k), "value": str(v)} for k, v in parameters.items()
            ],
        }
        return self._request("POST", "/v1/send/verify/", data=payload)

    def send_sms(
        self,
        number: str,
        message: str,
        line_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ارسال پیامک متنی به یک شماره مشخص."""
        return self.send_bulk_sms(
            numbers=[number],
            message=message,
            line_number=line_number,
        )

    def send_bulk_sms(
        self,
        numbers: List[str],
        message: str,
        line_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ارسال پیامک به چندین شماره همراه به صورت همزمان."""
        line = line_number or self.line_number
        payload = {
            "lineNumber": int(line) if (line and str(line).isdigit()) else line,
            "MessageText": message,
            "Mobiles": [str(n).strip() for n in numbers if str(n).strip()],
        }
        return self._request("POST", "/v1/send/bulk/", data=payload)

    def send_like_to_like(
        self,
        numbers: List[str],
        messages: List[str],
        line_number: Optional[str] = None,
        send_date_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """ارسال نظیر به نظیر پیام‌های متفاوت به شماره‌های متفاوت."""
        line = line_number or self.line_number
        payload = {
            "lineNumber": int(line) if (line and str(line).isdigit()) else line,
            "MessageTexts": messages,
            "Mobiles": numbers,
            "SendDateTime": send_date_time,
        }
        return self._request("POST", "/v1/send/liketolike/", data=payload)

    def get_credit(self) -> Dict[str, Any]:
        """استعلام موجودی و شارژ حساب پنل پیامک."""
        return self._request("GET", "/v1/credit/")

    def get_line_numbers(self) -> Dict[str, Any]:
        """دریافت لیست شماره‌های خطوط اختصاصی فعال پنل."""
        return self._request("GET", "/v1/line/")

    def report_today(
        self,
        page_size: int = 10,
        page_number: int = 1,
    ) -> Dict[str, Any]:
        """گزارش پیامک‌های ارسالی امروز."""
        return self._request(
            "GET",
            "/v1/send/live/",
            params={"pageSize": page_size, "pageNumber": page_number},
        )

    def report_message(self, message_id: int) -> Dict[str, Any]:
        """استعلام وضعیت تحویل یک پیام با شناسه."""
        return self._request("GET", f"/v1/send/{message_id}/")
