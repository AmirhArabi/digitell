from django.core.management.base import BaseCommand
from django.utils import timezone
from cart.models import RecoveryCampaign
from cart.recovery_services import process_automated_campaign


class Command(BaseCommand):
    help = "پردازش خودکار سبدهای رهاشده و ارسال پیامک‌های یادآوری یا تخفیف طبق کمپین فعال"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='اجرای آزمایشی بدون ارسال پیامک واقعی',
        )
        parser.add_argument(
            '--campaign-id',
            type=int,
            default=None,
            help='شناسه کمپین مشخص برای اجرا',
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='',
            help='دامنه اصلی سایت برای تولید لینک کامل (مانند https://digitell.ir)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        campaign_id = options['campaign_id']
        base_url = options['base_url']

        campaign = None
        if campaign_id:
            campaign = RecoveryCampaign.objects.filter(pk=campaign_id).first()
            if not campaign:
                self.stderr.write(self.style.ERROR(f"کمپین با شناسه {campaign_id} یافت نشد."))
                return

        self.stdout.write(self.style.MIGRATE_HEADING("شروع پردازش سبدهای خرید رهاشده..."))
        if dry_run:
            self.stdout.write(self.style.WARNING("حالت اجرای آزمایشی (Dry Run) فعال است. پیامکی ارسال نخواهد شد."))

        stats = process_automated_campaign(
            campaign=campaign,
            dry_run=dry_run,
            base_url=base_url
        )

        if stats.get('status') == 'error':
            self.stderr.write(self.style.ERROR(stats.get('message')))
            return

        self.stdout.write(self.style.SUCCESS(
            f"پردازش به پایان رسید.\n"
            f"- کل سبدهای بررسی‌شده: {stats['total_examined']}\n"
            f"- پیامک یادآوری (گام ۱): {stats['step1_sent']}\n"
            f"- پیشنهاد تخفیف (گام ۲): {stats['step2_sent']}\n"
            f"- صرف‌نظرشده (عدم صلاحیت): {stats['skipped']}\n"
            f"- ناموفق: {stats['failed']}"
        ))
