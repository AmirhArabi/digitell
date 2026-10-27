from django.shortcuts import render
from django.views.decorators.cache import cache_page

from products.models import Product, Category, Brand
from blog.models import Post
from .models import Banner, SiteSetting
from utils.cache import view_cache, CACHE_TTL_LONG, CACHE_TTL_MEDIUM


@view_cache(timeout=CACHE_TTL_LONG, prefix='home:index', cache_anon_only=False)
def index_view(request):
    banners = Banner.objects.filter(is_active=True).order_by('order')
    hero_banners = Banner.objects.filter(is_active=True, position='hero').order_by('order')

    # Categories for grid
    categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by('order')[:8]

    # Special offers (پیشنهاد شگفت‌انگیز)
    special_offers = Product.objects.filter(
        is_active=True,
        is_special_offer=True
    ).select_related('category', 'brand').prefetch_related('images')[:8]

    # Featured products
    featured_products = Product.objects.filter(
        is_active=True,
        is_featured=True
    ).select_related('category', 'brand').prefetch_related('images')[:6]

    # Smartphones category products
    smartphone_products = Product.objects.filter(
        is_active=True,
        category__slug='smartphones'
    ).select_related('category', 'brand')[:6]

    # Laptops & Gaming
    laptop_gaming_products = Product.objects.filter(
        is_active=True,
        category__slug__in=['laptops', 'gaming']
    ).select_related('category', 'brand')[:6]

    # Latest products (جدیدترین محصولات)
    latest_products = Product.objects.filter(
        is_active=True
    ).select_related('category', 'brand').prefetch_related('images').order_by('-created_at')[:6]

    # Brands for marquee
    brands = Brand.objects.filter(is_active=True).order_by('order')

    # Latest blog posts
    latest_posts = Post.objects.filter(is_published=True).select_related('category')[:3]

    context = {
        'banners': banners,
        'hero_banners': hero_banners,
        'categories': categories,
        'special_offers': special_offers,
        'featured_products': featured_products,
        'latest_products': latest_products,
        'smartphone_products': smartphone_products,
        'laptop_gaming_products': laptop_gaming_products,
        'brands': brands,
        'latest_posts': latest_posts,
    }
    return render(request, 'home/index.html', context)


def faq_view(request):
    return render(request, 'home/faq.html')


def contact_view(request):
    return render(request, 'home/contact.html')


def installment_view(request):
    return render(request, 'home/installment.html')
