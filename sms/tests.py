from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from home.models import SiteSetting
from sms.models import SmsTemplate, SmsLog, SmsCampaign
from sms.sms_ir_client import SmsIrClient
from sms.services import (
    normalize_phone,
    send_sms,
    send_otp_sms,
    send_pattern_sms,
    send_bulk_campaign_sms,
    get_panel_status,
)


class SmsModuleTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_superuser(
            username='admin_sms',
            phone_number='09121110000',
            password='adminpassword123',
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            username='customer_sms',
            phone_number='09129998877',
            password='customerpass',
            sms_marketing_subscribed=True,
        )
        self.client = Client()

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone('۰۹۱۲۳۴۵۶۷۸۹'), '09123456789')
        self.assertEqual(normalize_phone('+989123456789'), '09123456789')
        self.assertEqual(normalize_phone('989123456789'), '09123456789')
        self.assertEqual(normalize_phone('0912 345 6789'), '09123456789')

    def test_sms_client_simulated_mode(self):
        client = SmsIrClient(api_key='', line_number='')
        self.assertFalse(client.is_configured)
        res = client.send_sms('09123456789', 'تست پیامک')
        self.assertEqual(res['status'], 1)
        self.assertTrue(res.get('simulated'))

    def test_send_sms_service_creates_log(self):
        success = send_sms('09129998877', 'سلام، پیامک تستی دیجی تل', sender_user=self.staff_user)
        self.assertTrue(success)
        log = SmsLog.objects.filter(recipient='09129998877').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.sms_type, 'single')
        self.assertEqual(log.sender_user, self.staff_user)
        self.assertEqual(log.status, 'simulated')

    def test_send_otp_sms_service(self):
        success, msg = send_otp_sms('09129998877', '123456')
        self.assertTrue(success)
        log = SmsLog.objects.filter(recipient='09129998877', sms_type='otp').first()
        self.assertIsNotNone(log)
        self.assertIn('123456', log.message)

    def test_send_pattern_sms_service(self):
        success, msg = send_pattern_sms('09129998877', 100000, {'Code': '9988'}, sender_user=self.staff_user)
        self.assertTrue(success)
        log = SmsLog.objects.filter(recipient='09129998877', sms_type='pattern').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.pattern_template_id, 100000)

    def test_send_bulk_campaign_sms_service(self):
        res = send_bulk_campaign_sms(['09121111111', '09122222222'], 'متن کمپین', title='تخفیف ویژه')
        self.assertEqual(res['status'], 1)
        self.assertEqual(res['count'], 2)
        campaign = SmsCampaign.objects.filter(title='تخفیف ویژه').first()
        self.assertIsNotNone(campaign)
        self.assertEqual(campaign.total_recipients, 2)
        self.assertEqual(SmsLog.objects.filter(sms_type='campaign').count(), 2)

    def test_panel_status(self):
        status = get_panel_status()
        self.assertIn('is_configured', status)
        self.assertIn('line_number', status)

    def test_dashboard_sms_view_staff_required(self):
        # Anonymous redirect
        url = reverse('dashboard:sms')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # Staff login
        self.client.login(username='admin_sms', password='adminpassword123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'سامانه مدیریت پیامک')
        self.assertContains(response, 'SMS.ir')

    def test_dashboard_sms_send_single_post(self):
        self.client.login(username='admin_sms', password='adminpassword123')
        url = reverse('dashboard:sms')
        response = self.client.post(url, {
            'action': 'send_single',
            'mobile': '09129998877',
            'message': 'پیام تستی پنل مدیریت',
        })
        self.assertEqual(response.status_code, 302)
        log = SmsLog.objects.filter(recipient='09129998877', message='پیام تستی پنل مدیریت').first()
        self.assertIsNotNone(log)

    def test_dashboard_sms_template_crud(self):
        self.client.login(username='admin_sms', password='adminpassword123')
        url = reverse('dashboard:sms')

        # Create
        response = self.client.post(url, {
            'action': 'create_template',
            'title': 'الگوی سفارش جدید',
            'template_type': 'order',
            'template_id': '100200',
            'text': 'سفارش شما با شماره {OrderId} ثبت شد.',
            'parameters_hint': 'OrderId',
        })
        self.assertEqual(response.status_code, 302)
        template = SmsTemplate.objects.filter(title='الگوی سفارش جدید').first()
        self.assertIsNotNone(template)
        self.assertEqual(template.template_id, 100200)

        # Delete
        del_resp = self.client.post(url, {
            'action': 'delete_template',
            'template_pk': template.pk,
        })
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(SmsTemplate.objects.filter(pk=template.pk).exists())

    def test_accounts_generate_otp_uses_sms_service(self):
        from accounts.services import generate_otp
        code, otp_obj = generate_otp('09129998877')
        self.assertEqual(len(code), 6)
        log = SmsLog.objects.filter(recipient='09129998877', sms_type='otp').order_by('-created_at').first()
        self.assertIsNotNone(log)
        self.assertIn(code, log.message)
