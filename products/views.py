from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category, Brand


def shop_view(request, slug=None, category_slug=None):
    category_slug = slug or category_slug
    products = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        # Include children categories if parent
        cat_ids = [selected_category.id] + list(selected_category.children.values_list('id', flat=True))
        products = products.filter(category_id__in=cat_ids)

    # Filter: search query
    q = request.GET.get('q')
    if q:
        products = products.filter(
            Q(title__icontains=q) |
            Q(title_en__icontains=q) |
            Q(sku__icontains=q) |
            Q(short_description__icontains=q)
        )

    # Filter: brands
    brand_slugs = request.GET.getlist('brand')
    if brand_slugs:
        products = products.filter(brand__slug__in=brand_slugs)

    # Filter: in stock
    if request.GET.get('in_stock') == '1':
        products = products.filter(stock_qty__gt=0)

    # Filter: special offer
    if request.GET.get('special') == '1':
        products = products.filter(is_special_offer=True)

    # Filter: price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and min_price.isdigit():
        products = products.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        products = products.filter(price__lte=int(max_price))

    # Sorting
    sort = request.GET.get('sort', 'newest')
    if sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'cheapest':
        products = products.order_by('price')
    elif sort == 'expensive':
        products = products.order_by('-price')
    elif sort == 'discount':
        products = products.order_by('-discount_pct')
    elif sort == 'popular':
        products = products.order_by('-views_count')

    categories = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related('children')
    brands = Brand.objects.filter(is_active=True)

    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'selected_category': selected_category,
        'current_sort': sort,
        'total_count': products.count(),
        'search_query': q,
    }

    # If request is HTMX, return just the product grid
    if request.htmx:
        return render(request, 'products/partials/product_grid.html', context)

    return render(request, 'products/shop.html', context)


def product_detail_view(request, pk, slug):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('images', 'specifications'),
        pk=pk
    )

    # Increment view count
    Product.objects.filter(pk=pk).update(views_count=product.views_count + 1)

    # Related products from same category (کارت‌ها به تصویر نیاز دارند)
    related_products = list(
        Product.objects.filter(category=product.category, is_active=True)
        .exclude(id=product.id)
        .select_related('category', 'brand')
        .prefetch_related('images')[:10]
    )

    # Calculate 4-installment amount (SnappPay simulation)
    installment_amount = round(product.price / 4)

    specifications = list(product.specifications.all())
    savings = max((product.compare_at_price or product.price) - product.price, 0)
    description_text = f"{product.short_description}\n{product.description}".strip()

    context = {
        'product': product,
        'related_products': related_products,
        'installment_amount': installment_amount,
        'formatted_installment': f"{installment_amount:,}",
        'specifications': specifications,
        'spec_summary': specifications[:6],
        'spec_rest': specifications[6:],
        'savings': savings,
        'formatted_savings': f"{savings:,}",
        'rating_pct': round(float(product.rating or 0) / 5 * 100),
        'is_long_description': len(description_text) > 220,
    }
    return render(request, 'products/product_detail.html', context)


def live_search_view(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return render(request, 'products/partials/search_results.html', {'products': []})

    products = Product.objects.filter(
        Q(title__icontains=q) |
        Q(title_en__icontains=q) |
        Q(category__name__icontains=q) |
        Q(brand__name__icontains=q)
    ).filter(is_active=True)[:6]

    return render(request, 'products/partials/search_results.html', {'products': products, 'query': q})
