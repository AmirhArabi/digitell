import os
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models
from utils.image_optimizer import compress_to_webp


class Command(BaseCommand):
    help = "تبدیل و فشرده‌سازی دسته‌جمعی تمامی تصاویر موجود در دیتابیس به فرمت مدرن WebP"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='بررسی بدون ذخیره‌سازی تغییرات روی دیسک یا پایگاه‌داده',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=82,
            help='کیفیت فشرده‌سازی WebP (پیش‌فرض: 82)',
        )
        parser.add_argument(
            '--keep-originals',
            action='store_true',
            help='نگه‌داشتن فایل‌های اصلی بدون حذف آنها پس از تبدیل',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        quality = options['quality']
        keep_originals = options['keep_originals']

        self.stdout.write(self.style.MIGRATE_HEADING("=== آغاز تبدیل تصاویر سیستم به فرمت WebP ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("[حالت آزمایشی: تغییری در فایل‌ها و دیتابیس اعمال نخواهد شد]"))

        total_checked = 0
        total_converted = 0
        total_skipped = 0
        total_orig_bytes = 0
        total_new_bytes = 0

        for model in apps.get_models():
            image_fields = [f for f in model._meta.fields if isinstance(f, models.ImageField)]
            if not image_fields:
                continue

            model_label = model._meta.label
            for field in image_fields:
                field_name = field.name
                instances = model.objects.exclude(**{field_name: ''}).exclude(**{f"{field_name}__isnull": True})

                for instance in instances.iterator():
                    field_file = getattr(instance, field_name)
                    if not field_file or not field_file.name:
                        continue

                    total_checked += 1
                    raw_path = field_file.name.lower()

                    if raw_path.endswith('.webp'):
                        total_skipped += 1
                        continue

                    if raw_path.endswith('.svg'):
                        total_skipped += 1
                        continue

                    try:
                        if not field_file.storage.exists(field_file.name):
                            self.stdout.write(self.style.NOTICE(f"[موجود نیست] {model_label}#{instance.pk} -> {field_file.name}"))
                            continue

                        orig_size = field_file.size
                        total_orig_bytes += orig_size

                        with field_file.open('rb') as f:
                            compressed_content = compress_to_webp(
                                f,
                                filename=field_file.name,
                                quality=quality,
                                max_dimension=2048
                            )

                        if not compressed_content:
                            self.stdout.write(self.style.ERROR(f"[خطا در انکود] {model_label}#{instance.pk} -> {field_file.name}"))
                            continue

                        new_size = len(compressed_content)
                        total_new_bytes += new_size

                        dir_path = os.path.dirname(field_file.name)
                        base_name, _ = os.path.splitext(os.path.basename(field_file.name))
                        new_rel_path = os.path.join(dir_path, f"{base_name}.webp").replace('\\', '/')

                        old_full_path = field_file.path if hasattr(field_file, 'path') else None

                        if not dry_run:
                            # سیگنال pre_save رو قطع موقت یا با نام جدید فیلد را ذخیره می‌کنیم
                            field_file.save(new_rel_path, compressed_content, save=False)
                            instance.save(update_fields=[field_name])

                            # حذف فایل قدیمی در صورت عدم درخواست نگهداری
                            if not keep_originals and old_full_path and os.path.exists(old_full_path) and old_full_path != getattr(field_file, 'path', ''):
                                try:
                                    os.remove(old_full_path)
                                except OSError:
                                    pass

                        total_converted += 1
                        reduction = ((orig_size - new_size) / orig_size) * 100 if orig_size > 0 else 0
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[تبدیل شد] {model_label}#{instance.pk} ({field_name}): "
                                f"{orig_size / 1024:.1f}KB -> {new_size / 1024:.1f}KB ({reduction:.1f}% کاهش حجم)"
                            )
                        )
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(f"[خطا] {model_label}#{instance.pk}: {exc}"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== گزارش نهایی عملیات ==="))
        self.stdout.write(f"کل تصاویر بررسی شده: {total_checked}")
        self.stdout.write(f"تصاویر تبدیل شده به WebP: {total_converted}")
        self.stdout.write(f"تصاویر رد شده (قبلاً WebP یا وکتور): {total_skipped}")

        if total_orig_bytes > 0:
            saved_bytes = total_orig_bytes - total_new_bytes
            overall_pct = (saved_bytes / total_orig_bytes) * 100
            self.stdout.write(
                self.style.SUCCESS(
                    f"حجم کل اولیه: {total_orig_bytes / 1024 / 1024:.2f} MB | "
                    f"حجم جدید: {total_new_bytes / 1024 / 1024:.2f} MB | "
                    f"صرفه‌جویی کل: {saved_bytes / 1024 / 1024:.2f} MB ({overall_pct:.1f}%)"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("تمامی تصاویر از قبل در فرمت بهینه WebP هستند."))
