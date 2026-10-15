"""تست‌های بخش تیکتینگ (گفتگوی مشتری و پشتیبانی).

این فایل پیش از این وجود نداشت؛ بخش تیکتینگ بدون پوشش تست بود و به همین دلیل
خطای رندر صفحه جزئیات تیکت در پنل (تیکت بدون کارشناس) دیده نشده بود.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Ticket, TicketMessage

User = get_user_model()


class TicketBaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="manager", password="pass12345", is_staff=True, is_superuser=True
        )
        self.customer = User.objects.create_user(
            username="buyer", password="pass12345", phone_number="09121112233",
            first_name="رضا", last_name="علوی",
        )
        self.other_customer = User.objects.create_user(
            username="other", password="pass12345", phone_number="09129998877"
        )
        self.ticket = Ticket.objects.create(
            user=self.customer,
            subject="پیگیری سفارش ZT-123",
            category=Ticket.CATEGORY_ORDER,
            priority=Ticket.PRIORITY_NORMAL,
        )
        self.first_message = TicketMessage.objects.create(
            ticket=self.ticket, sender=self.customer, body="سلام، سفارش من ارسال نشده است."
        )

    def login_customer(self):
        self.client.force_login(self.customer)

    def login_staff(self):
        self.client.force_login(self.staff)


class TicketModelTests(TicketBaseTestCase):
    def test_ticket_number_is_generated_and_unique(self):
        other = Ticket.objects.create(user=self.customer, subject="موضوع دوم")
        self.assertTrue(self.ticket.ticket_number.startswith("TK-"))
        self.assertEqual(len(self.ticket.ticket_number), 11)
        self.assertNotEqual(self.ticket.ticket_number, other.ticket_number)

    def test_new_ticket_defaults(self):
        self.assertTrue(self.ticket.staff_unread)
        self.assertTrue(self.ticket.customer_unread)
        self.assertFalse(self.ticket.is_closed)
        self.assertIsNone(self.ticket.assigned_to)
        self.assertEqual(self.ticket.status, Ticket.STATUS_NEW)

    def test_message_snapshots_sender_name(self):
        self.assertEqual(self.first_message.sender_name, "رضا علوی")

    def test_close_sets_status_and_timestamp(self):
        self.ticket.close()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_CLOSED)
        self.assertIsNotNone(self.ticket.closed_at)
        self.assertTrue(self.ticket.is_closed)


class CustomerTicketTests(TicketBaseTestCase):
    def test_ticket_pages_require_login(self):
        for url in [
            reverse("tickets:list"),
            reverse("tickets:create_form"),
            reverse("tickets:detail", args=[self.ticket.pk]),
        ]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response["Location"])

    def test_list_shows_only_own_tickets(self):
        foreign = Ticket.objects.create(user=self.other_customer, subject="تیکت کاربر دیگر")
        self.login_customer()
        response = self.client.get(reverse("tickets:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.ticket_number)
        self.assertNotContains(response, foreign.ticket_number)

    def test_create_ticket_with_first_message(self):
        self.login_customer()
        response = self.client.post(reverse("tickets:create"), {
            "subject": "کالای معیوب",
            "body": "محصول با خطا رسید.",
            "category": Ticket.CATEGORY_PRODUCT,
            "priority": Ticket.PRIORITY_HIGH,
            "order_number": "ZT-10023",
        })
        ticket = Ticket.objects.exclude(pk=self.ticket.pk).get()
        self.assertRedirects(response, reverse("tickets:detail", args=[ticket.pk]))
        self.assertEqual(ticket.user, self.customer)
        self.assertEqual(ticket.priority, Ticket.PRIORITY_HIGH)
        self.assertEqual(ticket.order_number, "ZT-10023")
        self.assertEqual(ticket.messages.count(), 1)
        self.assertTrue(ticket.staff_unread)

    def test_create_requires_subject_and_body(self):
        self.login_customer()
        response = self.client.post(reverse("tickets:create"), {"subject": "", "body": ""})
        self.assertRedirects(response, reverse("tickets:create_form"))
        self.assertEqual(Ticket.objects.count(), 1)

    def test_invalid_category_and_priority_fall_back_to_defaults(self):
        self.login_customer()
        self.client.post(reverse("tickets:create"), {
            "subject": "موضوع", "body": "متن", "category": "hacked", "priority": "hacked",
        })
        ticket = Ticket.objects.exclude(pk=self.ticket.pk).get()
        self.assertEqual(ticket.category, Ticket.CATEGORY_OTHER)
        self.assertEqual(ticket.priority, Ticket.PRIORITY_NORMAL)

    def test_cannot_open_another_customers_ticket(self):
        self.login_customer()
        foreign = Ticket.objects.create(user=self.other_customer, subject="محرمانه")
        self.assertEqual(self.client.get(reverse("tickets:detail", args=[foreign.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("tickets:messages", args=[foreign.pk])).status_code, 404)

    def test_opening_ticket_clears_customer_unread(self):
        self.login_customer()
        self.client.get(reverse("tickets:detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.customer_unread)

    def test_customer_reply_marks_staff_unread_and_reopens_answered(self):
        self.ticket.status = Ticket.STATUS_ANSWERED
        self.ticket.staff_unread = False
        self.ticket.save()
        self.login_customer()
        response = self.client.post(reverse("tickets:reply", args=[self.ticket.pk]), {"body": "لطفاً سریع‌تر"})
        self.assertRedirects(response, reverse("tickets:detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_IN_PROGRESS)
        self.assertTrue(self.ticket.staff_unread)
        self.assertEqual(self.ticket.messages.count(), 2)

    def test_customer_cannot_reply_to_closed_ticket(self):
        self.ticket.close()
        self.login_customer()
        self.client.post(reverse("tickets:reply", args=[self.ticket.pk]), {"body": "ادامه بده"})
        self.assertEqual(self.ticket.messages.count(), 1)

    def test_empty_reply_is_rejected(self):
        self.login_customer()
        self.client.post(reverse("tickets:reply", args=[self.ticket.pk]), {"body": "   "})
        self.assertEqual(self.ticket.messages.count(), 1)

    def test_customer_can_close_own_ticket(self):
        self.login_customer()
        self.client.post(reverse("tickets:close", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_CLOSED)
        self.assertIsNotNone(self.ticket.closed_at)

    def test_status_filter(self):
        closed = Ticket.objects.create(user=self.customer, subject="بسته", status=Ticket.STATUS_CLOSED)
        self.login_customer()
        response = self.client.get(reverse("tickets:list"), {"status": Ticket.STATUS_CLOSED})
        self.assertContains(response, closed.ticket_number)
        self.assertNotContains(response, self.ticket.ticket_number)


class StaffTicketTests(TicketBaseTestCase):
    def test_dashboard_requires_staff(self):
        for url in [reverse("dashboard:tickets"), reverse("dashboard:ticket_detail", args=[self.ticket.pk])]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response["Location"])

        self.login_customer()
        self.assertEqual(self.client.get(reverse("dashboard:tickets")).status_code, 302)

    def test_list_page_renders_and_filters(self):
        self.login_staff()
        response = self.client.get(reverse("dashboard:tickets"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.ticket_number)

        filtered = self.client.get(reverse("dashboard:tickets"), {"status": Ticket.STATUS_ANSWERED})
        self.assertNotContains(filtered, self.ticket.ticket_number)

    def test_list_search_matches_subject_number_customer_and_body(self):
        self.login_staff()
        for query in [self.ticket.ticket_number, "پیگیری سفارش", "buyer", "09121112233", "ارسال نشده"]:
            with self.subTest(query=query):
                response = self.client.get(reverse("dashboard:tickets"), {"q": query})
                self.assertContains(response, self.ticket.ticket_number)

    def test_unassigned_ticket_detail_renders(self):
        """تیکت بدون کارشناس باید رندر شود — رگرسیون خطای VariableDoesNotExist."""
        self.assertIsNone(self.ticket.assigned_to)
        self.login_staff()
        response = self.client.get(reverse("dashboard:ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.ticket_number)
        self.assertContains(response, "اختصاص نیافته")

    def test_assigned_ticket_detail_shows_expert_name(self):
        self.staff.first_name = "سارا"
        self.staff.last_name = "حسینی"
        self.staff.save()
        self.ticket.assigned_to = self.staff
        self.ticket.save()
        self.login_staff()
        response = self.client.get(reverse("dashboard:ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "سارا حسینی")

    def test_staff_detail_clears_staff_unread(self):
        self.login_staff()
        self.client.get(reverse("dashboard:ticket_detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.staff_unread)

    def test_staff_reply_assigns_expert_and_sets_answered(self):
        self.login_staff()
        response = self.client.post(reverse("dashboard:ticket_detail", args=[self.ticket.pk]), {
            "action": "reply", "body": "بررسی شد، ارسال می‌شود.",
        })
        self.assertRedirects(response, reverse("dashboard:ticket_detail", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_ANSWERED)
        self.assertEqual(self.ticket.assigned_to, self.staff)
        self.assertTrue(self.ticket.customer_unread)
        self.assertFalse(self.ticket.staff_unread)
        message = self.ticket.messages.last()
        self.assertTrue(message.is_staff_message)

    def test_staff_reply_to_closed_ticket_reopens_it(self):
        self.ticket.close()
        self.login_staff()
        self.client.post(reverse("dashboard:ticket_detail", args=[self.ticket.pk]),
                         {"action": "reply", "body": "پیگیری مجدد"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_ANSWERED)
        self.assertIsNone(self.ticket.closed_at)

    def test_empty_staff_reply_is_rejected(self):
        self.login_staff()
        self.client.post(reverse("dashboard:ticket_detail", args=[self.ticket.pk]),
                         {"action": "reply", "body": "   "})
        self.assertEqual(self.ticket.messages.count(), 1)

    def test_staff_can_change_status(self):
        self.login_staff()
        for status in [Ticket.STATUS_IN_PROGRESS, Ticket.STATUS_CLOSED, Ticket.STATUS_NEW]:
            with self.subTest(status=status):
                self.client.post(reverse("dashboard:ticket_detail", args=[self.ticket.pk]),
                                 {"action": "status", "status": status})
                self.ticket.refresh_from_db()
                self.assertEqual(self.ticket.status, status)
                self.assertEqual(self.ticket.closed_at is not None, status == Ticket.STATUS_CLOSED)

    def test_invalid_status_is_ignored(self):
        self.login_staff()
        self.client.post(reverse("dashboard:ticket_detail", args=[self.ticket.pk]),
                         {"action": "status", "status": "not-a-status"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_NEW)

    def test_messages_partial_renders_both_sides(self):
        TicketMessage.objects.create(ticket=self.ticket, sender=self.staff,
                                     body="پاسخ پشتیبانی", is_staff_message=True)
        self.login_staff()
        response = self.client.get(reverse("dashboard:ticket_messages", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "پاسخ پشتیبانی")
        self.assertContains(response, "سفارش من ارسال نشده است")

    def test_ticket_without_messages_renders_everywhere(self):
        """تیکت بدون پیام نباید در فهرست‌ها یا صفحه گفتگو خطا بدهد."""
        empty = Ticket.objects.create(user=self.customer, subject="تیکت بدون پیام")
        self.login_staff()
        self.assertEqual(self.client.get(reverse("dashboard:tickets")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("dashboard:ticket_detail", args=[empty.pk])).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("dashboard:ticket_messages", args=[empty.pk])).status_code, 200
        )

        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("tickets:list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tickets:detail", args=[empty.pk])).status_code, 200)

    def test_detail_renders_when_expert_is_not_staff(self):
        """اگر کارشناس تیکت کاربر غیر‌پنلی باشد هم صفحه باید رندر شود."""
        self.ticket.assigned_to = self.other_customer
        self.ticket.save()
        self.login_staff()
        response = self.client.get(reverse("dashboard:ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "other")

    def test_unread_badge_counts_open_tickets(self):
        self.login_staff()
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["open_ticket_count"], 1)
        self.ticket.close()
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.context["open_ticket_count"], 0)
