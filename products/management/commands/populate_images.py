import os
import shutil
import urllib.parse
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from products.models import Category, Product, ProductImage
from home.models import Banner
from blog.models import Post


# ---------------------------------------------------------------------------
# Mapping: product slug -> list of image filenames (from utils/images)
# ---------------------------------------------------------------------------
PRODUCT_IMAGE_MAP = {
    "anker-powerport-iii-a2149-20w": [
        "40374_medium.png",
        "42113_medium.jpg",
        "42480_medium.jpg",
    ],
    "anker-323-charger-33w-a2331": [
        "42405_medium.jpg",
        "43508_medium.jpg",
        "43734_medium.jpg",
    ],
    "xiaomi-redmi-note-15-pro-5g-256gb": [
        "63183_medium.webp",
        "63195_medium.webp",
        "63208_medium.webp",
    ],
    "samsung-galaxy-a57-5g-512gb": [
        "64917_medium.webp",
        "64949_medium.webp",
        "64966_medium.webp",
    ],
    "apple-iphone-18-pro-max-256gb": [
        "77752_small.jpg",
        "36526_medium.webp",
        "48642_medium.webp",
    ],
    "asus-vivobook-x1504va-core5-16gb-1tb": [
        "77759_small.jpg",
        "71526_medium.webp",
        "56534_medium.webp",
    ],
    "sony-ps5-slim-digital-825gb": [
        "77757_small.jpg",
        "61723_medium.webp",
        "68429_medium.webp",
    ],
    "jbl-bar-800-mk2-soundbar": [
        "77756_small.jpg",
        "81978_medium.jpg",
        "81979_medium.jpg",
    ],
    "apple-watch-se-3-44mm": [
        "77755_small.jpg",
        "64974_medium.webp",
        "63266_medium.webp",
    ],
    "anker-soundcore-liberty-buds-d1200": [
        "36526_medium.webp",
        "36802_medium.webp",
        "41588_medium.webp",
    ],
    "silicon-power-ace-a55-1tb-ssd": [
        "50368_medium.jpg",
        "50388_medium.jpg",
        "50395_medium.jpg",
    ],
    "xiaomi-powerbank-20000-pb2020mi": [
        "49217_medium.jpg",
        "49245_medium.jpg",
        "49257_medium.jpg",
    ],
}

HERO_BANNERS = [
    {
        "title": "کلاس شروع شد، تو آماده‌ای؟",
        "file": "84404_Banner%20Header%20-%20C%20School%20-%20H001%20-%20Web%20%20-optimized.webp",
        "link": "/shop/",
        "position": "hero",
        "order": 1,
    },
    {
        "title": "آماده باش برای مدرسه",
        "file": "84406_Banner%20Header%20-%20C%20School%20-%20H002%20-%20Web-optimized.webp",
        "link": "/shop/",
        "position": "hero",
        "order": 2,
    },
    {
        "title": "تجهیزات دیجیتال مدرسه",
        "file": "84409_Banner%20Header%20-%20C%20School%20-%20H006%20-%20Web%20-optimized.webp",
        "link": "/shop/",
        "position": "hero",
        "order": 3,
    },
    {
        "title": "بهترین انتخاب برای کلاس",
        "file": "84411_Banner%20Header%20-%20C%20School%20-%20H003%20-%20Web%20-optimized.webp",
        "link": "/shop/",
        "position": "hero",
        "order": 4,
    },
    {
        "title": "لپ‌تاپ و تبلت برای مدرسه",
        "file": "84412_Banner%20Header%20-%20C%20School%20-%20H004%20-%20Web%20-optimized.webp",
        "link": "/shop/laptops/",
        "position": "hero",
        "order": 5,
    },
]

MID_BANNERS = [
    {
        "title": "خرید گوشی موبایل",
        "file": "86898_Banner%2001.webp",
        "link": "/shop/smartphones/",
        "position": "banner_pair",
        "order": 1,
    },
    {
        "title": "لوازم جانبی موبایل",
        "file": "86899_Banner%2002.webp",
        "link": "/shop/accessories/",
        "position": "banner_pair",
        "order": 2,
    },
    {
        "title": "هدفون و هندزفری",
        "file": "86903_Banner%2003.webp",
        "link": "/shop/headphones/",
        "position": "banner_pair",
        "order": 3,
    },
    {
        "title": "لپ‌تاپ و کامپیوتر",
        "file": "86901_Banner%2004.webp",
        "link": "/shop/laptops/",
        "position": "banner_pair",
        "order": 4,
    },
    {
        "title": "گیمینگ و کنسول بازی",
        "file": "86906_Banner%2005.webp",
        "link": "/shop/gaming/",
        "position": "banner_pair",
        "order": 5,
    },
    {
        "title": "ساعت هوشمند",
        "file": "86908_Banner%2006.webp",
        "link": "/shop/smartwatches/",
        "position": "banner_pair",
        "order": 6,
    },
    {
        "title": "اسپیکر و ساندبار",
        "file": "86924_Banner%2007.webp",
        "link": "/shop/speakers/",
        "position": "banner_pair",
        "order": 7,
    },
    {
        "title": "تجهیزات ذخیره‌سازی",
        "file": "86922_Banner%2008.webp",
        "link": "/shop/storage/",
        "position": "banner_pair",
        "order": 8,
    },
]

WIDE_BANNERS = [
    {
        "title": "صندلی گیمینگ DXRacer",
        "file": "68733_Banner%20Hyper-Chair.webp",
        "link": "/shop/gaming/",
        "position": "banner_wide",
        "order": 1,
    },
    {
        "title": "هدفون حرفه‌ای HyperX",
        "file": "68734_Banner%20Hyper-Headphone.webp",
        "link": "/shop/headphones/",
        "position": "banner_wide",
        "order": 2,
    },
]

CATEGORY_IMAGE_MAP = {
    "smartphones": "77752_small.jpg",
    "tablets": "77753_small.jpg",
    "smartwatches": "77755_small.jpg",
    "speakers": "77756_small.jpg",
    "gaming": "77757_small.jpg",
    "headphones": "77758_small.jpg",
    "laptops": "77759_small.jpg",
}

BLOG_IMAGE_MAP = {
    "which-iphone-to-buy-guide": "77752_small.jpg",
    "zitro-installment-purchase-guide": "86898_Banner%2001.webp",
}


class Command(BaseCommand):
    help = "Populate images from utils/images into media/ and database records"

    def handle(self, *args, **kwargs):
        src_dir = Path(settings.BASE_DIR) / "utils" / "images"
        media_dir = Path(settings.MEDIA_ROOT)

        if not src_dir.exists():
            self.stderr.write(self.style.ERROR(f"Source directory not found: {src_dir}"))
            return

        media_dir.mkdir(parents=True, exist_ok=True)

        self._populate_banners(src_dir, media_dir)
        self._populate_product_images(src_dir, media_dir)
        self._populate_category_images(src_dir, media_dir)
        self._populate_blog_images(src_dir, media_dir)

        self.stdout.write(self.style.SUCCESS("All images imported successfully!"))

    def _copy_image(self, src_dir, media_dir, sub_path, filename):
        src = src_dir / filename
        if not src.exists():
            self.stderr.write(self.style.WARNING(f"  File not found: {filename}"))
            return None

        dest_dir = media_dir / sub_path
        dest_dir.mkdir(parents=True, exist_ok=True)

        clean_name = urllib.parse.unquote(filename)
        dest = dest_dir / clean_name

        if not dest.exists():
            shutil.copy2(src, dest)

        return f"{sub_path}/{clean_name}"

    def _populate_banners(self, src_dir, media_dir):
        self.stdout.write(self.style.NOTICE("\nImporting banners..."))

        all_banners = HERO_BANNERS + MID_BANNERS + WIDE_BANNERS

        for b_data in all_banners:
            rel_path = self._copy_image(src_dir, media_dir, "banners", b_data["file"])
            if not rel_path:
                continue

            banner, created = Banner.objects.get_or_create(
                title=b_data["title"],
                position=b_data["position"],
                defaults={
                    "link_url": b_data["link"],
                    "order": b_data["order"],
                    "is_active": True,
                    "image": rel_path,
                },
            )

            if created:
                self.stdout.write(f"  Created banner: {b_data['title']}")
            else:
                if not banner.image or str(banner.image) != rel_path:
                    banner.image = rel_path
                    banner.save(update_fields=["image"])
                    self.stdout.write(f"  Updated banner: {b_data['title']}")
                else:
                    self.stdout.write(f"  Exists: {b_data['title']}")

    def _populate_product_images(self, src_dir, media_dir):
        self.stdout.write(self.style.NOTICE("\nImporting product images..."))

        for slug, image_files in PRODUCT_IMAGE_MAP.items():
            try:
                product = Product.objects.get(slug=slug)
            except Product.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"  Product not found: {slug}"))
                continue

            if product.images.exists():
                self.stdout.write(f"  Already has images: {product.title[:40]}")
                continue

            count = 0
            for idx, fname in enumerate(image_files):
                rel_path = self._copy_image(src_dir, media_dir, "products", fname)
                if not rel_path:
                    continue

                ProductImage.objects.create(
                    product=product,
                    image=rel_path,
                    alt_text=product.title,
                    is_primary=(idx == 0),
                    order=idx,
                )
                count += 1

            self.stdout.write(f"  Added {count} images for: {product.title[:50]}")

    def _populate_category_images(self, src_dir, media_dir):
        self.stdout.write(self.style.NOTICE("\nImporting category images..."))

        for cat_slug, fname in CATEGORY_IMAGE_MAP.items():
            try:
                category = Category.objects.get(slug=cat_slug)
            except Category.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"  Category not found: {cat_slug}"))
                continue

            if category.image:
                self.stdout.write(f"  Already has image: {cat_slug}")
                continue

            rel_path = self._copy_image(src_dir, media_dir, "categories", fname)
            if rel_path:
                category.image = rel_path
                category.save(update_fields=["image"])
                self.stdout.write(f"  Added image for category: {category.name}")

    def _populate_blog_images(self, src_dir, media_dir):
        self.stdout.write(self.style.NOTICE("\nImporting blog images..."))

        for post_slug, fname in BLOG_IMAGE_MAP.items():
            try:
                post = Post.objects.get(slug=post_slug)
            except Post.DoesNotExist:
                self.stderr.write(self.style.WARNING(f"  Post not found: {post_slug}"))
                continue

            if post.cover_image:
                self.stdout.write(f"  Already has image: {post_slug}")
                continue

            rel_path = self._copy_image(src_dir, media_dir, "blog/2026/10", fname)
            if rel_path:
                post.cover_image = rel_path
                post.save(update_fields=["cover_image"])
                self.stdout.write(f"  Added cover image for: {post.title[:50]}")
