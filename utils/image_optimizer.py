import io
import logging
import os
from PIL import Image, ImageOps
from django.apps import apps
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import pre_save

logger = logging.getLogger(__name__)


def compress_to_webp(file_obj, filename=None, quality=82, max_dimension=2048):
    """
    فشرده‌سازی تصویر و تبدیل خودکار به فرمت مدرن WebP.
    - اصلاح چرخش خودکار بر اساس اطلاعات EXIF (به‌ویژه عکس‌های موبایل).
    - حفظ کانال شفافیت (Alpha Channel) برای تصاویر بدون پس‌زمینه (PNG/WebP).
    - مقیاس‌پذیری نرم برای تصاویر بسیار بزرگ (بزرگتر از max_dimension).
    - فشرده‌سازی بیشینه با الگوریتم method=6 برای سبک‌ترین حجم و بالاترین شفافیت بصری.
    """
    try:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)

        img = Image.open(file_obj)

        # اصلاح چرخش عکس‌های گرفته‌شده با گوشی
        img = ImageOps.exif_transpose(img)

        # تغییر اندازه در صورت بیش از حد بزرگ بودن ابعاد تصویر
        w, h = img.size
        if w > max_dimension or h > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # پشتیبانی کامل از شفافیت (Transparency)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            save_img = img.convert('RGBA')
        else:
            save_img = img.convert('RGB')

        out = io.BytesIO()
        save_img.save(
            out,
            format='WEBP',
            quality=quality,
            optimize=True,
            method=6
        )
        out.seek(0)

        raw_name = filename or getattr(file_obj, 'name', 'image.webp')
        base_name, _ = os.path.splitext(os.path.basename(raw_name))
        new_filename = f"{base_name}.webp"

        return ContentFile(out.getvalue(), name=new_filename)
    except Exception as exc:
        logger.warning("خطا در فشرده‌سازی تصویر به WebP: %s. فایل با فرمت اصلی ذخیره می‌شود.", exc)
        return None


def auto_compress_image_fields(sender, instance, **kwargs):
    """
    سیگنال pre_save خودکار برای مدل‌ها:
    هر تصویر جدیدی که در هر مدلی بارگذاری شود، پیش از ذخیره روی دیسک فشرده و به WebP تبدیل می‌شود.
    """
    for field in instance._meta.fields:
        if isinstance(field, models.ImageField):
            field_file = getattr(instance, field.name, None)
            # اگر فیلد خالی است یا قبلاً ذخیره و commit شده، رد شو
            if not field_file or getattr(field_file, '_committed', True):
                continue
            if not hasattr(field_file, 'file') or not field_file.file:
                continue

            file_name = (field_file.name or '').lower()
            # وکتورهای SVG نیازی به فشرده‌سازی یا تبدیل به WebP ندارند
            if file_name.endswith('.svg'):
                continue

            # فشرده‌سازی و تبدیل به webp
            compressed_content = compress_to_webp(
                field_file.file,
                filename=field_file.name,
                quality=82,
                max_dimension=2048
            )

            if compressed_content:
                # جایگزینی پسوند فایل در مسیر ذخیره‌سازی
                dir_path = os.path.dirname(field_file.name)
                base_name, _ = os.path.splitext(os.path.basename(field_file.name))
                new_path = os.path.join(dir_path, f"{base_name}.webp").replace('\\', '/')
                field_file.save(new_path, compressed_content, save=False)


def register_image_compression_signals():
    """
    اتصال خودکار به تمامی مدل‌هایی که در سیستم دارای ImageField هستند.
    """
    registered_models = []
    for model in apps.get_models():
        image_fields = [f.name for f in model._meta.fields if isinstance(f, models.ImageField)]
        if image_fields:
            pre_save.connect(auto_compress_image_fields, sender=model, weak=False)
            registered_models.append(model._meta.label)
    logger.info("ثبت سیگنال تبدیل خودکار تصاویر به WebP برای مدل‌های: %s", registered_models)
