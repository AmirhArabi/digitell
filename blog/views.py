from django.shortcuts import render, get_object_or_404
from .models import Post, BlogCategory


def post_list_view(request, category_slug=None):
    posts = Post.objects.filter(is_published=True).select_related('category', 'author')
    categories = BlogCategory.objects.all()
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(BlogCategory, slug=category_slug)
        posts = posts.filter(category=selected_category)

    context = {
        'posts': posts,
        'categories': categories,
        'selected_category': selected_category,
    }
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
