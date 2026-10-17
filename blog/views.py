from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Post, BlogCategory

# تعداد مقاله در هر صفحه (۳ ستون × ۲ ردیف)
BLOG_PAGE_SIZE = 6


def _url_with(params):
    query = urlencode(params, doseq=True)
    return f'?{query}' if query else '?'


def _pagination_context(paginator, page_obj, base_params=()):
    """لینک صفحه‌ها با صریح‌آوردن همهٔ پارامترها تا فیلتر دسته حفظ شود."""
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

    if category_slug:
        selected_category = get_object_or_404(BlogCategory, slug=category_slug)
        posts = posts.filter(category=selected_category)

    paginator = Paginator(posts, BLOG_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'posts': page_obj.object_list,
        'categories': categories,
        'selected_category': selected_category,
        'total_count': paginator.count,
        'pagination': _pagination_context(paginator, page_obj),
        # لینک «همه مقالات»/دسته‌ها برای درخواست‌های HTMX
        'all_posts_url': reverse('blog:post_list'),
        'range_from': page_obj.start_index() if paginator.count else 0,
        'range_to': page_obj.end_index() if paginator.count else 0,
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
    # Increment views
    Post.objects.filter(id=post.id).update(views_count=post.views_count + 1)

    recent_posts = Post.objects.filter(is_published=True).exclude(id=post.id)[:4]

    context = {
        'post': post,
        'recent_posts': recent_posts,
    }
    return render(request, 'blog/post_detail.html', context)
