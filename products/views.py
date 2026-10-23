from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Brand, Category, CategoryAttribute, Product, ProductReview

# جداکنندهٔ نام و مقدار یک ویژگی در پارامتر «spec» (مثلاً «حافظه داخلی::۲۵۶ گیگابایت»)
SPEC_SEPARATOR = '::'

# سقف و کف گزینه‌های نمایش‌داده‌شده برای هر ویژگی فیلتر
FACET_MIN_VALUES = 2
FACET_MAX_VALUES = 12

# تعداد کالا در هر صفحه از کاتالوگ (۴ ستون × ۳ ردیف)
CATALOG_PAGE_SIZE = 12

SORT_FIELDS = {
    'newest': '-created_at',
    'cheapest': 'price',
    'expensive': '-price',
    'discount': '-discount_pct',
    'popular': '-views_count',
}

SORT_LABELS = [
    ('newest', 'جدیدترین'),
    ('cheapest', 'ارزان‌ترین'),
    ('expensive', 'گران‌ترین'),
    ('discount', 'بیشترین تخفیف'),
]


# ---------------------------------------------------------------------------
# ابزارهای کمکی
# ---------------------------------------------------------------------------
def _clean_query_params(request, exclude=()):
    """پارامترهای مؤثر فیلتر صفحه به‌صورت لیست (key, value).

    کلیدهای ``sort`` و ``page`` همیشه حذف می‌شوند تا لینک چیپ‌ها و مرتب‌سازی
    به صفحهٔ اول برگردد؛ هر جا لازم باشد خودشان صریحاً اضافه می‌شوند.
    """
    params = []
    skipped = {'sort', 'page', *exclude}
    for key in request.GET:
        if key in skipped:
            continue
        for value in request.GET.getlist(key):
            if value:
                params.append((key, value))
    return params


def _url_with(params):
    query = urlencode(params, doseq=True)
    return f'?{query}' if query else '?'


def _pagination_context(request, paginator, page_obj, extra_params=()):
    """لینک صفحه‌های کاتالوگ/بلاگ با حفظ فیلترها و مرتب‌سازی فعال."""
    page_params = _clean_query_params(request) + list(extra_params)

    links = []
    for number in paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1):
        if number == Paginator.ELLIPSIS:
            links.append({'number': None, 'url': None, 'current': False})
            continue
        links.append({
            'number': number,
            'url': _url_with(page_params + [('page', number)]),
            'current': number == page_obj.number,
        })

    return {
        'links': links,
        'number': page_obj.number,
        'num_pages': paginator.num_pages,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_url': _url_with(page_params + [('page', page_obj.previous_page_number())]) if page_obj.has_previous() else None,
        'next_url': _url_with(page_params + [('page', page_obj.next_page_number())]) if page_obj.has_next() else None,
    }


def _selected_spec_filters(request):
    selected = []
    for raw in request.GET.getlist('spec'):
        if SPEC_SEPARATOR not in raw:
            continue
        name, value = raw.split(SPEC_SEPARATOR, 1)
        name, value = name.strip(), value.strip()
        if name and value:
            selected.append((name, value))
    return selected


def _category_options(selected_category):
    """گزینه‌های فیلتر دسته‌بندی/نوع دستگاه بر اساس دستهٔ فعلی."""
    if selected_category and selected_category.children.exists():
        options = (
            selected_category.children.filter(is_active=True)
            .annotate(num_products=Count('products', filter=Q(products__is_active=True)))
            .order_by('order', 'name')
        )
        return 'نوع دستگاه', [
            {'label': c.name, 'url': c.get_absolute_url(), 'count': c.num_products}
            for c in options
        ]

    options = (
        Category.objects.filter(is_active=True, parent__isnull=True)
        .annotate(num_products=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )
    return 'دسته‌بندی', [
        {
            'label': c.name,
            'url': c.get_absolute_url(),
            'count': c.num_products,
            'active': bool(selected_category and selected_category.pk == c.pk),
        }
        for c in options
    ]


def _brand_field(scope, selected_brands):
    rows = (
        scope.exclude(brand__isnull=True)
        .values('brand__slug', 'brand__name', 'brand__name_en')
        .annotate(num_products=Count('id', distinct=True))
        .order_by('-num_products', 'brand__name')
    )
    values = [
        {
            'value': row['brand__slug'],
            'label': row['brand__name'],
            'meta': row['brand__name_en'],
            'count': row['num_products'],
            'selected': row['brand__slug'] in selected_brands,
        }
        for row in rows
    ]
    if not values:
        return None
    return {
        'key': 'brand',
        'type': 'checkbox',
        'param': 'brand',
        'label': 'برند',
        'hint': 'یک یا چند برند را انتخاب کنید',
        'selected_count': sum(1 for item in values if item['selected']),
        'values': values,
    }


def _spec_fields(scope, selected_specs, attribute_map):
    """فیلترهای ویژگی را از مشخصات فنی محصولات همین محدوده می‌سازد (رویکرد داده‌محور)."""
    rows = list(
        scope.filter(specifications__isnull=False)
        .values('specifications__name', 'specifications__value')
        .annotate(num_products=Count('id', distinct=True))
        .order_by('specifications__name', '-num_products', 'specifications__value')
    )

    grouped = {}
    for row in rows:
        grouped.setdefault(row['specifications__name'], []).append(row)

    fields = []
    for index, (name, items) in enumerate(grouped.items()):
        if len(items) < FACET_MIN_VALUES:
            continue
        attribute = attribute_map.get(name)
        values = [
            {
                'value': f'{name}{SPEC_SEPARATOR}{item["specifications__value"]}',
                'label': item['specifications__value'],
                'count': item['num_products'],
                'selected': (name, item['specifications__value']) in selected_specs,
            }
            for item in items[:FACET_MAX_VALUES]
        ]
        fields.append({
            'key': f'spec-{index}',
            'type': 'checkbox',
            'param': 'spec',
            'label': name,
            'hint': f'واحد: {attribute.unit}' if attribute and attribute.unit else None,
            'selected_count': sum(1 for item in values if item['selected']),
            'values': values,
        })
    return fields


def _facet_attributes(selected_category):
    if selected_category:
        definition = CategoryAttribute.objects.filter(is_active=True).filter(
            Q(category=selected_category) | Q(category__isnull=True)
        )
    else:
        definition = CategoryAttribute.objects.filter(is_active=True, category__isnull=True)
    return {attribute.name: attribute for attribute in definition}


# ---------------------------------------------------------------------------
# کاتالوگ
# ---------------------------------------------------------------------------
def shop_view(request, slug=None, category_slug=None):
    category_slug = slug or category_slug
    base = Product.objects.filter(is_active=True)
    selected_category = None

    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        # دستهٔ والد شامل محصولات زیردسته‌ها هم می‌شود.
        category_ids = [selected_category.pk] + list(
            selected_category.children.values_list('id', flat=True)
        )
        base = base.filter(category_id__in=category_ids)

    q = (request.GET.get('q') or '').strip()
    if q:
        base = base.filter(
            Q(title__icontains=q) |
            Q(title_en__icontains=q) |
            Q(sku__icontains=q) |
            Q(short_description__icontains=q)
        )

    # «scope» مبنای شمارش گزینه‌های فیلتر است؛ پس از اعمال فیلترهای ویژگی/برند ساخته
    # می‌شود تا شمارش‌ها پایدار و معنادار بمانند.
    scope = base

    selected_brands = [item for item in request.GET.getlist('brand') if item]
    selected_specs = _selected_spec_filters(request)

    in_stock = request.GET.get('in_stock') == '1'
    special = request.GET.get('special') == '1'
    min_price_raw = (request.GET.get('min_price') or '').strip()
    max_price_raw = (request.GET.get('max_price') or '').strip()

    products = base.select_related('category', 'brand').prefetch_related('images')

    if selected_brands:
        products = products.filter(brand__slug__in=selected_brands)

    # ویژگی‌های هم‌نام با «یا» و ویژگی‌های متفاوت با «و» ترکیب می‌شوند.
    spec_groups = {}
    for name, value in selected_specs:
        spec_groups.setdefault(name, []).append(value)
    for name, values in spec_groups.items():
        condition = Q()
        for value in values:
            condition |= Q(specifications__name=name, specifications__value=value)
        products = products.filter(condition)

    if in_stock:
        products = products.filter(stock_qty__gt=F('reserved_qty'))
    if special:
        products = products.filter(is_special_offer=True)

    min_price = int(min_price_raw) if min_price_raw.isdigit() else None
    max_price = int(max_price_raw) if max_price_raw.isdigit() else None
    if min_price is not None:
        products = products.filter(price__gte=min_price)
    if max_price is not None:
        products = products.filter(price__lte=max_price)

    if selected_brands or selected_specs:
        products = products.distinct()

    sort = request.GET.get('sort', 'newest')
    products = products.order_by(SORT_FIELDS.get(sort, SORT_FIELDS['newest']))

    # --- ساخت فیلدهای فیلتر (ابتدا فیلد، سپس ردیف‌های همان فیلد) -------------
    category_label, category_rows = _category_options(selected_category)

    filter_fields = [{
        'key': 'category',
        'type': 'link',
        'label': category_label,
        'hint': 'برای تغییر محدودهٔ کالاها یکی را انتخاب کنید',
        'selected_count': 1 if selected_category else 0,
        'values': category_rows,
    }]

    brand_field = _brand_field(scope, selected_brands)
    if brand_field:
        filter_fields.append(brand_field)

    filter_fields.extend(_spec_fields(scope, selected_specs, _facet_attributes(selected_category)))

    filter_fields.append({
        'key': 'price',
        'type': 'price',
        'label': 'محدوده قیمت (تومان)',
        'hint': 'بازهٔ قیمت دلخواه را وارد کنید',
        'selected_count': 1 if (min_price is not None or max_price is not None) else 0,
        'min_value': min_price_raw,
        'max_value': max_price_raw,
    })

    status_values = [
        {
            'param': 'in_stock',
            'value': '1',
            'label': 'فقط کالاهای موجود',
            'count': scope.filter(stock_qty__gt=F('reserved_qty')).count(),
            'selected': in_stock,
        },
        {
            'param': 'special',
            'value': '1',
            'label': 'فقط پیشنهادهای شگفت‌انگیز',
            'count': scope.filter(is_special_offer=True).count(),
            'selected': special,
        },
    ]
    filter_fields.append({
        'key': 'status',
        'type': 'status',
        'label': 'وضعیت کالا',
        'hint': 'موجودی و تخفیف‌ها',
        'selected_count': sum(1 for item in status_values if item['selected']),
        'values': status_values,
    })

    # --- چیپ‌های فیلتر فعال و لینک‌های مرتب‌سازی (با حفظ فیلترها) --------------
    active_filters = []
    if q:
        active_filters.append({'label': f'جستجو: {q}', 'url': _url_with(_clean_query_params(request, exclude={'q'}))})
    if selected_category:
        active_filters.append({
            'label': category_label + ': ' + selected_category.name,
            'url': _url_with(_clean_query_params(request)),
        })
    for slug in selected_brands:
        brand = Brand.objects.filter(slug=slug).first()
        active_filters.append({
            'label': f'برند: {brand.name if brand else slug}',
            'url': _url_with([p for p in _clean_query_params(request) if not (p[0] == 'brand' and p[1] == slug)]),
        })
    for name, value in selected_specs:
        active_filters.append({
            'label': f'{name}: {value}',
            'url': _url_with([
                p for p in _clean_query_params(request)
                if not (p[0] == 'spec' and p[1] == f'{name}{SPEC_SEPARATOR}{value}')
            ]),
        })
    if min_price is not None or max_price is not None:
        price_bits = []
        if min_price is not None:
            price_bits.append(f'از {min_price:,}')
        if max_price is not None:
            price_bits.append(f'تا {max_price:,}')
        active_filters.append({
            'label': 'قیمت ' + ' '.join(price_bits) + ' تومان',
            'url': _url_with(_clean_query_params(request, exclude={'min_price', 'max_price'})),
        })
    if in_stock:
        active_filters.append({'label': 'فقط موجود', 'url': _url_with(_clean_query_params(request, exclude={'in_stock'}))})
    if special:
        active_filters.append({'label': 'فقط شگفت‌انگیز', 'url': _url_with(_clean_query_params(request, exclude={'special'}))})

    current_params = _clean_query_params(request)
    sort_options = [
        {'key': key, 'label': label, 'url': _url_with(current_params + [('sort', key)]), 'active': sort == key}
        for key, label in SORT_LABELS
    ]

    categories = (
        Category.objects.filter(is_active=True, parent__isnull=True)
        .annotate(num_products=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )

    total_count = products.count()
    paginator = Paginator(products, CATALOG_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'products': page_obj.object_list,
        'categories': categories,
        'filter_fields': filter_fields,
        'active_filters': active_filters,
        'sort_options': sort_options,
        'catalog_base_url': selected_category.get_absolute_url() if selected_category else reverse('products:shop'),
        'selected_category': selected_category,
        'category_children': list(selected_category.children.filter(is_active=True)) if selected_category else [],
        'current_sort': sort,
        'total_count': total_count,
        'pagination': _pagination_context(request, paginator, page_obj, extra_params=[('sort', sort)]),
        'range_from': page_obj.start_index() if total_count else 0,
        'range_to': page_obj.end_index() if total_count else 0,
        'search_query': q,
    }

    # HTMX: فقط نوار ابزار و شبکهٔ محصولات دوباره رندر می‌شود.
    if request.htmx:
        return render(request, 'products/partials/product_grid.html', context)

    return render(request, 'products/shop.html', context)


def category_index_view(request):
    """صفحهٔ مشاهدهٔ همهٔ دسته‌بندی‌ها همراه با زیردسته‌ها و تعداد کالا."""
    categories = list(
        Category.objects.filter(is_active=True, parent__isnull=True)
        .annotate(num_products=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )
    children = (
        Category.objects.filter(is_active=True, parent__in=categories)
        .annotate(num_products=Count('products', filter=Q(products__is_active=True)))
        .order_by('order', 'name')
    )
    child_map = {}
    for child in children:
        child_map.setdefault(child.parent_id, []).append(child)

    blocks = []
    for category in categories:
        kids = child_map.get(category.pk, [])
        blocks.append({
            'category': category,
            'children': kids,
            'total_products': category.num_products + sum(kid.num_products for kid in kids),
        })

    brands = (
        Brand.objects.filter(is_active=True)
        .annotate(num_products=Count('products', filter=Q(products__is_active=True)))
        .order_by('-num_products', 'order', 'name')
    )

    return render(request, 'products/categories.html', {
        'category_blocks': blocks,
        'brands': brands,
        'total_categories': len(categories),
    })


# ---------------------------------------------------------------------------
# صفحه محصول و نظرات
# ---------------------------------------------------------------------------
def _user_has_purchased(user, product):
    if not user.is_authenticated:
        return False
    from orders.models import OrderItem  # واردکردن تنبل برای جلوگیری از چرخهٔ import

    return OrderItem.objects.filter(
        order__user=user,
        product=product,
        order__payment_status='successful',
    ).exists()


def _display_name(user):
    full_name = f'{user.first_name} {user.last_name}'.strip()
    return full_name or user.username


def _reviews_context(product, user, errors=None, form_values=None):
    reviews = list(product.approved_reviews.select_related('user'))
    total = len(reviews)

    breakdown_counts = {star: 0 for star in range(1, 6)}
    for review in reviews:
        if review.rating in breakdown_counts:
            breakdown_counts[review.rating] += 1

    average = product.review_average
    user_review = product.reviews.filter(user=user).first() if user.is_authenticated else None

    form_values = form_values or {}
    submitted = (form_values.get('rating') or '').strip()
    if submitted.isdigit():
        current_rating = int(submitted)
    elif user_review:
        current_rating = user_review.rating
    else:
        current_rating = 0

    # مقادیر فرم: اول ورودی همین درخواست، در نبود آن نظر قبلی کاربر.
    form_title = form_values.get('title')
    if form_title is None:
        form_title = user_review.title if user_review else ''
    form_body = form_values.get('body')
    if form_body is None:
        form_body = user_review.body if user_review else ''

    return {
        'product': product,
        'reviews': reviews,
        'reviews_count': total,
        'rating_average': average,
        'rating_pct': round(average / 5 * 100),
        'rating_breakdown': [
            {
                'star': star,
                'count': breakdown_counts[star],
                'pct': round(breakdown_counts[star] * 100 / total) if total else 0,
            }
            for star in range(5, 0, -1)
        ],
        'user_review': user_review,
        'can_review': user.is_authenticated,
        'rating_scale': [1, 2, 3, 4, 5],
        'current_rating': current_rating,
        'form_title': form_title,
        'form_body': form_body,
        'review_errors': errors or [],
        'review_form_values': form_values,
    }


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

    # Check if product is already in user's cart
    from cart.views import _get_or_create_cart
    cart = _get_or_create_cart(request)
    is_in_cart = cart.items.filter(product=product).exists()

    insurance_fee = round(product.price * 0.023)

    context = {
        'product': product,
        'is_in_cart': is_in_cart,
        'related_products': related_products,
        'installment_amount': installment_amount,
        'formatted_installment': f"{installment_amount:,}",
        'insurance_fee': insurance_fee,
        'formatted_insurance_fee': f"{insurance_fee:,}",
        'specifications': specifications,
        'spec_summary': specifications[:6],
        'spec_rest': specifications[6:],
        'savings': savings,
        'formatted_savings': f"{savings:,}",
        'is_long_description': len(description_text) > 220,
    }
    context.update(_reviews_context(product, request.user))
    return render(request, 'products/product_detail.html', context)


@require_POST
@login_required(login_url='accounts:login')
def product_review_view(request, pk):
    """ثبت یا ویرایش نظر کاربر روی محصول (اعتبارسنجی کامل سمت سرور)."""
    product = get_object_or_404(Product, pk=pk, is_active=True)

    rating_raw = (request.POST.get('rating') or '').strip()
    body = (request.POST.get('body') or '').strip()
    title = (request.POST.get('title') or '').strip()
    rating = int(rating_raw) if rating_raw.isdigit() else 0

    errors = []
    if rating not in (1, 2, 3, 4, 5):
        errors.append('امتیاز را بین ۱ تا ۵ ستاره انتخاب کنید.')
    if len(body) < 10:
        errors.append('متن نظر باید حداقل ۱۰ کاراکتر باشد.')
    if len(body) > 2000:
        errors.append('متن نظر نمی‌تواند بیشتر از ۲۰۰۰ کاراکتر باشد.')

    if not errors:
        review, created = ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                'author_name': _display_name(request.user),
                'rating': rating,
                'title': title[:150],
                'body': body,
                'is_verified_purchase': _user_has_purchased(request.user, product),
            },
        )
        messages.success(
            request,
            'نظر شما ثبت شد.' if created else 'نظر شما به‌روزرسانی شد.',
        )
        if request.htmx:
            context = _reviews_context(product, request.user)
            context['review_saved_message'] = 'نظر شما ثبت شد.'
            return render(request, 'products/partials/reviews.html', context)
        return redirect(f'{product.get_absolute_url()}#reviews')

    for error in errors:
        messages.error(request, error)

    if request.htmx:
        context = _reviews_context(
            product,
            request.user,
            errors=errors,
            form_values={'rating': rating_raw, 'body': body, 'title': title},
        )
        return render(request, 'products/partials/reviews.html', context)
    return redirect(f'{product.get_absolute_url()}#reviews')


def live_search_view(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return render(request, 'products/partials/search_results.html', {'products': [], 'categories': []})

    # بررسی دسته‌بندی‌ها در ابتدا (اگر کلمه سرچ شده دسته بندی بود در ردیف اول نمایش داده شود)
    matched_categories = list(
        Category.objects.filter(
            Q(name__icontains=q) | Q(name_en__icontains=q),
            is_active=True
        )[:3]
    )

    products = Product.objects.filter(
        Q(title__icontains=q) |
        Q(title_en__icontains=q) |
        Q(category__name__icontains=q) |
        Q(brand__name__icontains=q)
    ).filter(is_active=True)[:6]

    return render(
        request,
        'products/partials/search_results.html',
        {
            'products': products,
            'categories': matched_categories,
            'query': q,
        }
    )
