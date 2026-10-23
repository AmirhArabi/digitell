from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from products.models import Product
from .models import Post, BlogCategory, BlogComment

# تعداد مقاله در هر صفحه (۳ ستون × ۲ ردیف)
BLOG_PAGE_SIZE = 6


def _url_with(params):
    query = urlencode(params, doseq=True)
    return f'?{query}' if query else '?'


def _pagination_context(paginator, page_obj, base_params=()):
    """لینک صفحه‌ها با صریح‌آوردن همهٔ پارامترها تا فیلتر دسته و جستجو حفظ شود."""
    links = []
    for number in paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1):
        if number == Paginator.ELLIPSIS:
            links.append({'number': None, 'url': None, 'current': False})
            continue
        links.append({
            'number': number,
            'url': _url_with(list(base_params) + [('page', number)]),
            'current': number == page_obj.number,
        })

    return {
        'links': links,
        'number': page_obj.number,
        'num_pages': paginator.num_pages,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_url': _url_with(list(base_params) + [('page', page_obj.previous_page_number())]) if page_obj.has_previous() else None,
        'next_url': _url_with(list(base_params) + [('page', page_obj.next_page_number())]) if page_obj.has_next() else None,
    }


def post_list_view(request, category_slug=None):
    posts = Post.objects.filter(is_published=True).select_related('category', 'author')
    categories = BlogCategory.objects.all()
    selected_category = None
    search_query = request.GET.get('q') or request.GET.get('s') or ''
    search_query = search_query.strip()

    if category_slug:
        selected_category = get_object_or_404(BlogCategory, slug=category_slug)
        posts = posts.filter(category=selected_category)

    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    base_params = []
    if search_query:
        base_params.append(('q', search_query))

    paginator = Paginator(posts, BLOG_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # جدیدترین مقالات برای ستون جانبی یا ویجت‌های بالا
    recent_sidebar_posts = Post.objects.filter(is_published=True).order_by('-created_at')[:5]

    context = {
        'posts': page_obj.object_list,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'total_count': paginator.count,
        'pagination': _pagination_context(paginator, page_obj, base_params=base_params),
        'all_posts_url': reverse('blog:post_list'),
        'range_from': page_obj.start_index() if paginator.count else 0,
        'range_to': page_obj.end_index() if paginator.count else 0,
        'recent_sidebar_posts': recent_sidebar_posts,
    }

    # HTMX: فقط شبکهٔ مقالات و صفحه‌بندی دوباره رندر می‌شود.
    if request.htmx:
        return render(request, 'blog/partials/post_grid.html', context)

    return render(request, 'blog/post_list.html', context)


def post_detail_view(request, slug):
    post = get_object_or_404(
        Post.objects.select_related('category', 'author'),
        slug=slug,
        is_published=True
    )
    # افزایش بازدید
    Post.objects.filter(id=post.id).update(views_count=post.views_count + 1)

    # مقاله‌های قبلی و بعدی (بر اساس زمان انتشار)
    previous_post = (
        Post.objects.filter(is_published=True, created_at__lt=post.created_at)
        .order_by('-created_at')
        .first()
    )
    next_post = (
        Post.objects.filter(is_published=True, created_at__gt=post.created_at)
        .order_by('created_at')
        .first()
    )

    # مقالات جدید ستون کناری
    recent_posts = (
        Post.objects.filter(is_published=True)
        .exclude(id=post.id)
        .order_by('-created_at')[:6]
    )

    # مطالب مرتبط (بر اساس دسته‌بندی مشترک یا جدیدترین‌ها)
    related_posts_qs = (
        Post.objects.filter(is_published=True, category=post.category)
        .exclude(id=post.id)
        .order_by('-created_at')[:4]
    )
    related_posts = list(related_posts_qs)
    if len(related_posts) < 4:
        exclude_ids = [post.id] + [p.id for p in related_posts]
        filler_posts = (
            Post.objects.filter(is_published=True)
            .exclude(id__in=exclude_ids)
            .order_by('-created_at')[:4 - len(related_posts)]
        )
        related_posts.extend(list(filler_posts))

    # محصولات مرتبط درون محتوا: در صورت انتساب اختصاصی از همان‌ها استفاده می‌شود،
    # در غیر این صورت از محصولات پرفروش و فعال فروشگاه پر می‌شود
    in_article_products = list(post.related_products.filter(is_active=True))
    if not in_article_products:
        in_article_products = list(
            Product.objects.filter(is_active=True, is_available=True)
            .select_related('category', 'brand')
            .prefetch_related('images')
            .order_by('-views_count', '-created_at')[:3]
        )

    # اسلایدر محصولات انتهای مقاله (مشابه zitro zrp-row)
    bottom_products = list(
        Product.objects.filter(is_active=True, is_available=True)
        .select_related('category', 'brand')
        .prefetch_related('images')
        .order_by('-created_at')[:8]
    )

    # پردازش ثبت دیدگاه
    comment_success = False
    comment_error = None
    if request.method == 'POST':
        author_name = request.POST.get('author', '').strip() or request.POST.get('name', '').strip()
        author_email = request.POST.get('email', '').strip()
        website = request.POST.get('url', '').strip() or request.POST.get('website', '').strip()
        comment_text = request.POST.get('comment', '').strip()

        if author_name and author_email and comment_text:
            BlogComment.objects.create(
                post=post,
                author_name=author_name,
                author_email=author_email,
                website=website,
                content=comment_text,
                is_approved=True
            )
            comment_success = True
        else:
            comment_error = "لطفاً تمامی فیلدهای الزامی (نام، ایمیل و دیدگاه) را تکمیل فرمایید."

    comments = post.comments.filter(is_approved=True).order_by('-created_at')
    categories = BlogCategory.objects.all()

    context = {
        'post': post,
        'previous_post': previous_post,
        'next_post': next_post,
        'recent_posts': recent_posts,
        'related_posts': related_posts,
        'in_article_products': in_article_products,
        'bottom_products': bottom_products,
        'comments': comments,
        'categories': categories,
        'comment_success': comment_success,
        'comment_error': comment_error,
    }

    if request.htmx and request.method == 'POST':
        return render(request, 'blog/partials/comments_section.html', context)

    return render(request, 'blog/post_detail.html', context)
