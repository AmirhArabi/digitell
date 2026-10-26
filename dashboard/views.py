"""پنل مدیریت اختصاصی فروشگاه دیجی تل.

تمام نماها فقط برای کاربران is_staff قابل دسترسی هستند و در مسیر /dashboard/ سرو می‌شوند.
"""
import csv
from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import User
from blog.models import BlogCategory, Post
from home.models import Banner, SiteSetting
from orders.models import Coupon, Order, OrderItem
from products.models import Brand, Category, CategoryAttribute, Product, ProductImage, ProductSpecification

from functools import wraps

def staff(view_func):
    """دسترسی فقط برای کاربران staff."""
    # استفاده مستقیم از decorator پیش‌فرض Django برای ادمین‌ها
    return staff_member_required(login_url='accounts:login')(view_func)

FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


# --------------------------------------------------------------------------
# ابزارهای کمکی
# --------------------------------------------------------------------------
def to_int(value, default=0):
    """تبدیل ورودی انسانی (اعداد فارسی، کاما، فاصله) به عدد صحیح."""
    if value in (None, ''):
        return default
    try:
        cleaned = str(value).translate(FA_DIGITS).replace(',', '').replace('٬', '').strip()
        return int(float(cleaned))
    except (TypeError, ValueError):
        return default


def to_bool(request, field):
    return field in request.POST


def unique_slug(model, title, instance=None):
    base = slugify(title, allow_unicode=True)[:200] or 'item'
    slug = base
    counter = 2
    qs = model.objects.all()
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def site_settings():
    return SiteSetting.get_settings()


def date_range_from_request(request, default_days=30):
    """بازه تاریخ از پارامترهای from/to (YYYY-MM-DD) با پیش‌فرض N روز گذشته."""
    parse = datetime.strptime
    try:
        start = parse(request.GET.get('from', ''), '%Y-%m-%d').date()
    except ValueError:
        start = timezone.localdate() - timedelta(days=default_days)
    try:
        end = parse(request.GET.get('to', ''), '%Y-%m-%d').date()
    except ValueError:
        end = timezone.localdate()
    if start > end:
        start, end = end, start
    start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end, datetime.max.time()))
    return start, end, start_dt, end_dt


def csv_response(filename, header, rows):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


def category_tree():
    """لیست دسته‌بندی‌ها به ترتیب درختی همراه با عمق (برای نمایش تودرتو)."""
    categories = list(Category.objects.select_related('parent').all())
    children = defaultdict(list)
    for category in categories:
        children[category.parent_id].append(category)

    ordered = []
    seen = set()

    def walk(parent_id, depth):
        for category in sorted(children.get(parent_id, []), key=lambda c: (c.order, c.name)):
            if category.pk in seen:
                continue
            seen.add(category.pk)
            category.depth = depth
            ordered.append(category)
            walk(category.pk, depth + 1)

    walk(None, 0)
    for category in categories:  # دسته‌های بی‌والد در ساختار شکسته
        if category.pk not in seen:
            category.depth = 0
            ordered.append(category)
    return ordered

from cart.models import Cart, CartItem
from accounts.services import send_sms, normalize_phone
def category_options(exclude=None):
    """گزینه‌های نمایشی دسته‌بندی‌ها با تودرتویی؛ در صورت نیاز زیرشاخه‌های یک دسته حذف می‌شوند."""
    tree = category_tree()
    skip = set()
    if exclude and exclude.pk:
        skip.add(exclude.pk)
        children = defaultdict(list)
        for category in Category.objects.all():
            children[category.parent_id].append(category)
        stack = [exclude.pk]
        while stack:
            current = stack.pop()
            for child in children.get(current, []):
                skip.add(child.pk)
                stack.append(child.pk)

    return [
        {'id': category.pk, 'label': '— ' * category.depth + category.name}
        for category in tree
        if category.pk not in skip
    ]


def _querystring_without_page(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def save_uploaded_images(product, request):
    """ذخیره تصاویر آپلودی محصول و تعیین تصویر اصلی."""
    files = request.FILES.getlist('images')
    if not files:
        return
    primary_index = to_int(request.POST.get('primary_image'), 1)
    start_order = product.images.count()
    created = []
    for index, file in enumerate(files, start=1):
        image = ProductImage.objects.create(
            product=product,
            image=file,
            alt_text=request.POST.get('images_alt', '') or product.title,
            order=start_order + index,
        )
        created.append((index, image))

    has_primary = product.images.filter(is_primary=True).exists()
    for index, image in created:
        if index == primary_index or (not has_primary and index == 1):
            product.images.update(is_primary=False)
            image.is_primary = True
            image.save(update_fields=['is_primary'])


def save_specifications(product, request):
    """بازسازی مشخصات فنی از ردیف‌های فرم."""
    names = request.POST.getlist('spec_name')
    values = request.POST.getlist('spec_value')
    units = request.POST.getlist('spec_unit')
    product.specifications.all().delete()
    order = 0
    for name, value, unit in zip(names, values, units):
        name, value = name.strip(), value.strip()
        if not name or not value:
            continue
        order += 1
        full_value = f"{value} {unit.strip()}".strip()
        ProductSpecification.objects.create(product=product, name=name, value=full_value, order=order)


# --------------------------------------------------------------------------
# admin login view
# --------------------------------------------------------------------------
@staff
def admin_login_view(request):
    """ورود اختصاصی ادمین‌ها با نام کاربری و رمز عبور.
    فقط کاربران دارای وضعیت staff می‌توانند وارد شوند.
    پس از موفقیت به داشبورد می‌روند.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            messages.success(request, 'ورود موفقیت‌آمیز')
            return redirect('dashboard:overview')
        messages.error(request, 'نام کاربری یا رمز عبور اشتباه است')
    return render(request, 'dashboard/admin_login.html')

# --------------------------------------------------------------------------
# Category Attributes API (dynamic technical specifications)
# --------------------------------------------------------------------------
@staff
def category_attributes_api(request, pk):
    """Return active attributes for a given category as JSON.
    Used by the product form to populate spec rows dynamically.
    """
    attrs = CategoryAttribute.objects.filter(category_id=pk, is_active=True)
    data = []
    for a in attrs:
        data.append({
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "unit": a.unit,
            "options": getattr(a, 'options_list', []),
        })
    return JsonResponse(data, safe=False)

# --------------------------------------------------------------------------
# Cart Management & Recovery Views
# --------------------------------------------------------------------------
from cart.models import Cart, CartItem, RecoveryCampaign, RecoveryAttempt
from cart.recovery_services import (
    send_recovery_attempt,
    is_cart_eligible_for_recovery,
    get_abandoned_carts,
    create_recovery_coupon,
)
from django.core.paginator import Paginator


@staff
def cart_list_view(request):
    """فهرست سبدهای خرید با فیلترهای پیشرفته، جستجو و آمار بازیابی."""
    status_filter = request.GET.get('status', '').strip()  # all, abandoned, active, converted, empty
    recovery_filter = request.GET.get('recovery', '').strip()
    customer_filter = (request.GET.get('customer') or request.GET.get('user') or request.GET.get('customer_type') or '').strip()
    search_query = request.GET.get('q', '').strip()

    queryset = (
        Cart.objects.select_related('user', 'converted_order')
        .prefetch_related('items__product', 'recovery_attempts')
        .all()
        .order_by('-updated_at')
    )

    if search_query:
        queryset = queryset.filter(
            Q(id__icontains=search_query)
            | Q(session_key__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__phone_number__icontains=search_query)
        )

    if customer_filter:
        if customer_filter in ('authenticated', 'logged_in', 'registered', 'user'):
            queryset = queryset.filter(user__isnull=False)
        elif customer_filter in ('guest', 'anonymous'):
            queryset = queryset.filter(user__isnull=True)
        elif customer_filter.isdigit():
            queryset = queryset.filter(user_id=int(customer_filter))
        else:
            queryset = queryset.filter(
                Q(user__username__icontains=customer_filter)
                | Q(user__phone_number__icontains=customer_filter)
                | Q(user__first_name__icontains=customer_filter)
                | Q(user__last_name__icontains=customer_filter)
            )

    if recovery_filter:
        queryset = queryset.filter(recovery_status=recovery_filter)

    now = timezone.now()
    abandoned_cutoff = now - timedelta(hours=24)

    if status_filter == 'abandoned':
        queryset = queryset.filter(
            items__isnull=False,
            converted_order__isnull=True,
            updated_at__lte=abandoned_cutoff,
        ).distinct()
    elif status_filter == 'active':
        queryset = queryset.filter(
            items__isnull=False,
            converted_order__isnull=True,
            updated_at__gt=abandoned_cutoff,
        ).distinct()
    elif status_filter == 'converted':
        queryset = queryset.filter(converted_order__isnull=False)
    elif status_filter == 'empty':
        queryset = queryset.filter(items__isnull=True)

    total_carts_count = Cart.objects.count()
    authenticated_count = Cart.objects.filter(user__isnull=False).count()
    guest_count = Cart.objects.filter(user__isnull=True).count()
    abandoned_count = Cart.objects.filter(
        items__isnull=False,
        converted_order__isnull=True,
        updated_at__lte=abandoned_cutoff,
    ).distinct().count()
    recovered_count = Cart.objects.filter(recovery_status='recovered').count()
    contacted_count = Cart.objects.filter(recovery_status='contacted').count()

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    carts_page = paginator.get_page(page_number)

    context = {
        'carts': carts_page,
        'total_count': total_carts_count,
        'authenticated_count': authenticated_count,
        'guest_count': guest_count,
        'abandoned_count': abandoned_count,
        'recovered_count': recovered_count,
        'contacted_count': contacted_count,
        'status_filter': status_filter,
        'recovery_filter': recovery_filter,
        'customer_filter': customer_filter,
        'search_query': search_query,
        'recovery_choices': Cart.RECOVERY_CHOICES,
        'querystring': _querystring_without_page(request),
    }
    return render(request, 'dashboard/cart_list.html', context)


@staff
def cart_detail_view(request, pk):
    """صفحه جزئیات کامل سبد خرید، تاریخچه پیگیری‌ها، اقدامات و ارسال پیامک."""
    cart = get_object_or_404(
        Cart.objects.select_related('user', 'converted_order')
        .prefetch_related('items__product', 'recovery_attempts__coupon', 'recovery_attempts__campaign'),
        pk=pk
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_note':
            cart.admin_note = request.POST.get('admin_note', '').strip()
            new_status = request.POST.get('recovery_status')
            if new_status in dict(Cart.RECOVERY_CHOICES):
                cart.recovery_status = new_status
            cart.save(update_fields=['admin_note', 'recovery_status'])
            messages.success(request, "یادداشت و وضعیت سبد بروزرسانی شد.")
            return redirect('dashboard:cart_detail', pk=cart.pk)

    eligible, eligibility_reason = is_cart_eligible_for_recovery(cart)
    attempts = cart.recovery_attempts.all().order_by('-created_at')
    active_campaign = RecoveryCampaign.objects.filter(is_active=True).first()

    context = {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
        'attempts': attempts,
        'is_eligible': eligible,
        'eligibility_reason': eligibility_reason,
        'active_campaign': active_campaign,
        'recovery_choices': Cart.RECOVERY_CHOICES,
    }
    return render(request, 'dashboard/cart_detail.html', context)


@staff
def cart_send_recovery_sms_view(request, pk):
    """ارسال دستی پیامک بازیابی برای یک سبد خرید مشخص."""
    if request.method != 'POST':
        return redirect('dashboard:cart_detail', pk=pk)

    cart = get_object_or_404(Cart, pk=pk)
    msg_type = request.POST.get('message_type', 'reminder')
    custom_text = request.POST.get('custom_text', '').strip() or None
    include_coupon = (msg_type == 'discount') or ('include_coupon' in request.POST)
    dry_run = 'dry_run' in request.POST

    campaign = RecoveryCampaign.objects.filter(is_active=True).first()
    step = cart.attempts_count + 1

    ok, msg, attempt = send_recovery_attempt(
        cart=cart,
        campaign=campaign,
        step=step,
        message_type=msg_type,
        custom_text=custom_text,
        include_coupon=include_coupon,
        dry_run=dry_run,
    )

    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    return redirect('dashboard:cart_detail', pk=cart.pk)


@staff
def cart_bulk_sms_view(request):
    """ارسال گروهی پیامک برای سبدهای انتخاب‌شده."""
    if request.method == 'POST':
        cart_ids = request.POST.getlist('carts')
        message = request.POST.get('message', '').strip()
        include_coupon = request.POST.get('include_coupon') in ('true', 'on', '1')
        dry_run = request.POST.get('dry_run') in ('true', 'on', '1')

        if not cart_ids:
            messages.warning(request, "هیچ سبد خریدی انتخاب نشده است.")
            return redirect('dashboard:cart_list')

        sent_count = 0
        skipped_count = 0
        failed_count = 0

        campaign = RecoveryCampaign.objects.filter(is_active=True).first()

        for cart in Cart.objects.filter(id__in=cart_ids):
            ok, msg, attempt = send_recovery_attempt(
                cart=cart,
                campaign=campaign,
                step=cart.attempts_count + 1,
                message_type='discount' if include_coupon else 'reminder',
                custom_text=message if message else None,
                include_coupon=include_coupon,
                dry_run=dry_run,
            )
            if ok:
                sent_count += 1
            elif attempt and attempt.status == 'skipped':
                skipped_count += 1
            else:
                failed_count += 1

        messages.success(
            request,
            f"عملیات گروهی تکمیل شد: {sent_count} موفق، {skipped_count} ردشده (عدم صلاحیت)، {failed_count} ناموفق."
        )
        return redirect('dashboard:cart_list')
    return redirect('dashboard:cart_list')


@staff
def cart_recovery_campaign_view(request):
    """مدیریت کمپین‌های خودکار بازیابی سبد خرید."""
    campaign = RecoveryCampaign.objects.first()
    if not campaign:
        campaign = RecoveryCampaign.objects.create(
            name="کمپین هوشمند پیش‌فرض بازیابی",
            is_active=True,
            abandonment_threshold_hours=24,
            step1_delay_hours=24,
            step2_delay_hours=48,
            discount_type='percent',
            discount_value=10,
            discount_validity_hours=48,
            max_attempts_per_cart=2,
            min_cart_value=0,
            created_by=request.user,
        )

    if request.method == 'POST':
        campaign.name = request.POST.get('name', campaign.name).strip()
        campaign.is_active = 'is_active' in request.POST
        campaign.abandonment_threshold_hours = int(request.POST.get('abandonment_threshold_hours', 24) or 24)
        campaign.step1_delay_hours = int(request.POST.get('step1_delay_hours', 24) or 24)
        campaign.step2_delay_hours = int(request.POST.get('step2_delay_hours', 48) or 48)
        campaign.message_template_step1 = request.POST.get('message_template_step1', '').strip()
        campaign.message_template_step2 = request.POST.get('message_template_step2', '').strip()
        campaign.discount_type = request.POST.get('discount_type', 'percent')
        campaign.discount_value = int(request.POST.get('discount_value', 10) or 10)
        max_disc = request.POST.get('discount_max_amount', '').strip()
        campaign.discount_max_amount = int(max_disc) if max_disc else None
        campaign.discount_min_order = int(request.POST.get('discount_min_order', 0) or 0)
        campaign.discount_validity_hours = int(request.POST.get('discount_validity_hours', 48) or 48)
        campaign.max_attempts_per_cart = int(request.POST.get('max_attempts_per_cart', 2) or 2)
        campaign.min_cart_value = int(request.POST.get('min_cart_value', 0) or 0)
        campaign.save()

        messages.success(request, "تنظیمات کمپین بازیابی سبد با موفقیت ذخیره شد.")
        return redirect('dashboard:cart_recovery_campaign')

    total_attempts = RecoveryAttempt.objects.filter(campaign=campaign).count()
    successful_sms = RecoveryAttempt.objects.filter(campaign=campaign, status='sent').count()
    converted_attempts = RecoveryAttempt.objects.filter(campaign=campaign, converted_order__isnull=False).count()
    converted_revenue = RecoveryAttempt.objects.filter(
        campaign=campaign, converted_order__isnull=False
    ).aggregate(s=Sum('converted_order__final_amount'))['s'] or 0

    conversion_rate = round((converted_attempts / successful_sms * 100), 1) if successful_sms else 0

    context = {
        'campaign': campaign,
        'total_attempts': total_attempts,
        'successful_sms': successful_sms,
        'converted_attempts': converted_attempts,
        'converted_revenue': converted_revenue,
        'conversion_rate': conversion_rate,
    }
    return render(request, 'dashboard/cart_campaign.html', context)

# --------------------------------------------------------------------------
# نمای کلی و گزارش‌ها
# --------------------------------------------------------------------------
@staff
def overview_view(request):
    paid_orders = Order.objects.filter(payment_status='successful')
    now = timezone.now()
    today = now.date()

    total_sales = paid_orders.aggregate(s=Sum('final_amount'))['s'] or 0
    sales_today = paid_orders.filter(created_at__date=today).aggregate(s=Sum('final_amount'))['s'] or 0
    sales_week = paid_orders.filter(created_at__gte=now - timedelta(days=7)).aggregate(s=Sum('final_amount'))['s'] or 0

    context = {
        'total_sales': f"{total_sales:,}",
        'sales_today': f"{sales_today:,}",
        'sales_week': f"{sales_week:,}",
        'orders_count': Order.objects.count(),
        'pending_orders_count': Order.objects.filter(status='pending').count(),
        'processing_orders_count': Order.objects.filter(status='paid').count(),
        'products_count': Product.objects.count(),
        'active_products_count': Product.objects.filter(is_active=True).count(),
        'inactive_products_count': Product.objects.filter(is_active=False).count(),
        'customers_count': User.objects.filter(is_staff=False).count(),
        'low_stock_products': Product.objects.filter(is_active=True, stock_qty__lte=F('low_stock_threshold')).order_by('stock_qty')[:6],
        'low_stock_count': Product.objects.filter(is_active=True, stock_qty__lte=F('low_stock_threshold')).count(),
        'out_of_stock_count': Product.objects.filter(stock_qty=0).count(),
        'coupons_count': Coupon.objects.filter(is_active=True).count(),
        'recent_orders': Order.objects.select_related('user').prefetch_related('items')[:7],
        'top_products': (
            OrderItem.objects.filter(order__payment_status='successful')
            .values('product_title')
            .annotate(qty=Sum('quantity'), revenue=Sum('total_price'))
            .order_by('-revenue')[:5]
        ),
        'active_categories_count': Category.objects.filter(is_active=True).count(),
        'attributes_count': CategoryAttribute.objects.filter(is_active=True).count(),
        'banners_count': Banner.objects.filter(is_active=True).count(),
        'posts_count': Post.objects.count(),
    }
    return render(request, 'dashboard/overview.html', context)


def to_fa(value):
    """تبدیل ارقام لاتین به فارسی برای برچسب‌های نمودار."""
    return str(value).translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))


def _pct_change(current, previous):
    """درصد تغییر نسبت به بازه قبل (None یعنی قابل محاسبه نیست)."""
    if not previous:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _period_metrics(orders, paid):
    """شاخص‌های فروش یک بازه زمانی."""
    sums = paid.aggregate(
        revenue=Sum('final_amount'),
        avg=Avg('final_amount'),
        count=Count('id'),
        products=Sum('products_total'),
        discount=Sum('discount_amount'),
        coupon=Sum('coupon_discount'),
        shipping=Sum('shipping_cost'),
    )
    items = OrderItem.objects.filter(order__in=paid).aggregate(qty=Sum('quantity'))['qty'] or 0
    buyers = paid.exclude(user__isnull=True).values('user').distinct().count()
    orders_count = sums['count'] or 0
    return {
        'revenue': sums['revenue'] or 0,
        'orders': orders_count,
        'avg_order': int(sums['avg'] or 0),
        'items': items,
        'buyers': buyers,
        'items_per_order': round(items / orders_count, 2) if orders_count else 0,
        'unpaid': orders.exclude(payment_status='successful').count(),
        'all_orders': orders.count(),
        'coupon_discount': sums['coupon'] or 0,
        'discount': sums['discount'] or 0,
        'shipping': sums['shipping'] or 0,
    }


def _inventory_snapshot():
    """تصویر لحظه‌ای انبار: تعداد، ارزش ریالی و وضعیت موجودی."""
    products = Product.objects.all()
    totals = products.aggregate(units=Sum('stock_qty'), value=Sum(F('stock_qty') * F('price')))
    out_of_stock = products.filter(stock_qty=0).count()
    low_stock = products.filter(stock_qty__gt=0, stock_qty__lte=F('low_stock_threshold')).count()
    healthy = products.filter(stock_qty__gt=F('low_stock_threshold')).count()
    return {
        'products_count': products.count(),
        'units': totals['units'] or 0,
        'value': totals['value'] or 0,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'healthy': healthy,
        'inactive': products.filter(is_active=False).count(),
    }


def _sales_charts(paid, orders, start, end, inv):
    """ساخت داده نمودارهای صفحه گزارشات."""
    daily_rows = (
        paid.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('final_amount'), orders=Count('id'))
        .order_by('day')
    )
    daily = [
        {
            'day': row['day'],
            'label': to_fa(row['day'].strftime('%m/%d')),
            'revenue': row['revenue'] or 0,
            'orders': row['orders'] or 0,
        }
        for row in daily_rows
    ]

    weekday_order = [5, 6, 0, 1, 2, 3, 4]  # شنبه تا جمعه (weekday پایتون: دوشنبه=0)
    weekday_names = {5: 'شنبه', 6: 'یک‌شنبه', 0: 'دوشنبه', 1: 'سه‌شنبه', 2: 'چهارشنبه', 3: 'پنج‌شنبه', 4: 'جمعه'}
    weekday_totals = {key: 0 for key in weekday_order}
    for row in daily:
        weekday_totals[row['day'].weekday()] += row['revenue']

    status_labels = dict(Order.STATUS_CHOICES)
    status_breakdown = list(orders.values('status').annotate(count=Count('id')).order_by('-count'))
    for row in status_breakdown:
        row['label'] = status_labels.get(row['status'], row['status'])

    payment_labels = dict(Order.PAYMENT_STATUS_CHOICES)
    payment_breakdown = list(
        orders.values('payment_status').annotate(count=Count('id')).order_by('-count')
    )
    for row in payment_breakdown:
        row['label'] = payment_labels.get(row['payment_status'], row['payment_status'])

    top_products_chart = list(
        OrderItem.objects.filter(order__in=paid)
        .values('product_title')
        .annotate(revenue=Sum('total_price'), qty=Sum('quantity'))
        .order_by('-revenue')[:8]
    )
    top_categories = list(
        OrderItem.objects.filter(order__in=paid, product__isnull=False)
        .values('product__category__name')
        .annotate(revenue=Sum('total_price'), qty=Sum('quantity'))
        .order_by('-revenue')[:8]
    )
    stock_categories = list(
        Product.objects.values('category__name')
        .annotate(value=Sum(F('stock_qty') * F('price')), units=Sum('stock_qty'))
        .order_by('-value')[:7]
    )

    shipping_labels = dict(Order.SHIPPING_CHOICES)
    shipping_breakdown = list(orders.values('shipping_method').annotate(count=Count('id')).order_by('-count'))
    for row in shipping_breakdown:
        row['label'] = shipping_labels.get(row['shipping_method'], row['shipping_method'])

    charts = {
        'daily': {
            'labels': [row['label'] for row in daily],
            'revenue': [row['revenue'] for row in daily],
            'orders': [row['orders'] for row in daily],
        },
        'weekday': {
            'labels': [weekday_names[key] for key in weekday_order],
            'revenue': [weekday_totals[key] for key in weekday_order],
        },
        'status': {
            'labels': [row['label'] for row in status_breakdown],
            'counts': [row['count'] for row in status_breakdown],
        },
        'payment': {
            'labels': [row['label'] for row in payment_breakdown],
            'counts': [row['count'] for row in payment_breakdown],
        },
        'top_products': {
            'labels': [row['product_title'] for row in top_products_chart],
            'revenue': [row['revenue'] for row in top_products_chart],
            'qty': [row['qty'] for row in top_products_chart],
        },
        'categories': {
            'labels': [row['product__category__name'] or 'بدون دسته' for row in top_categories],
            'revenue': [row['revenue'] for row in top_categories],
        },
        'stock_health': {
            'labels': ['موجودی مناسب', 'کم‌موجود (هشدار)', 'ناموجود'],
            'counts': [inv['healthy'], inv['low_stock'], inv['out_of_stock']],
        },
        'stock_categories': {
            'labels': [row['category__name'] or 'بدون دسته' for row in stock_categories],
            'value': [row['value'] or 0 for row in stock_categories],
            'units': [row['units'] or 0 for row in stock_categories],
        },
    }
    return charts, daily, status_breakdown, payment_breakdown, shipping_breakdown, top_categories


@staff
def reports_view(request):
    start, end, start_dt, end_dt = date_range_from_request(request)
    period_days = (end - start).days + 1

    # بازه قبل (هم‌اندازه) برای محاسبه رشد شاخص‌ها
    prev_end_dt = start_dt - timedelta(microseconds=1)
    prev_start_dt = start_dt - timedelta(days=period_days)

    orders = Order.objects.filter(created_at__range=(start_dt, end_dt))
    paid = orders.filter(payment_status='successful')
    prev_orders = Order.objects.filter(created_at__range=(prev_start_dt, prev_end_dt))
    prev_paid = prev_orders.filter(payment_status='successful')

    current = _period_metrics(orders, paid)
    previous = _period_metrics(prev_orders, prev_paid)
    inv = _inventory_snapshot()
    charts, daily, status_breakdown, payment_breakdown, shipping_breakdown, top_categories = _sales_charts(
        paid, orders, start, end, inv
    )

    new_customers = User.objects.filter(date_joined__range=(start_dt, end_dt)).count()

    kpis = [
        {
            'label': 'فروش موفق بازه',
            'value': f"{current['revenue']:,}",
            'unit': 'تومان',
            'growth': _pct_change(current['revenue'], previous['revenue']),
            'compare': f"{previous['revenue']:,} تومان",
            'tone': 'blue',
        },
        {
            'label': 'سفارش‌های پرداخت‌شده',
            'value': f"{current['orders']:,}",
            'unit': 'سفارش',
            'growth': _pct_change(current['orders'], previous['orders']),
            'compare': f"{previous['orders']:,} سفارش",
            'tone': 'indigo',
        },
        {
            'label': 'میانگین ارزش سفارش',
            'value': f"{current['avg_order']:,}",
            'unit': 'تومان',
            'growth': _pct_change(current['avg_order'], previous['avg_order']),
            'compare': f"{previous['avg_order']:,} تومان",
            'tone': 'violet',
        },
        {
            'label': 'اقلام فروخته‌شده',
            'value': f"{current['items']:,}",
            'unit': 'عدد',
            'growth': _pct_change(current['items'], previous['items']),
            'compare': f"{previous['items']:,} عدد",
            'tone': 'emerald',
        },
        {
            'label': 'خریداران یکتا',
            'value': f"{current['buyers']:,}",
            'unit': 'کاربر',
            'growth': _pct_change(current['buyers'], previous['buyers']),
            'compare': f"{previous['buyers']:,} کاربر",
            'tone': 'sky',
        },
        {
            'label': 'مشتریان جدید',
            'value': f"{new_customers:,}",
            'unit': 'نفر',
            'growth': None,
            'compare': 'ثبت‌نام در این بازه',
            'tone': 'teal',
        },
        {
            'label': 'تخفیف اعطاشده (کد + سود)',
            'value': f"{(current['coupon_discount'] + current['discount']):,}",
            'unit': 'تومان',
            'growth': _pct_change(
                current['coupon_discount'] + current['discount'],
                previous['coupon_discount'] + previous['discount'],
            ),
            'compare': f"{current['coupon_discount']:,} تومان از کد تخفیف",
            'tone': 'amber',
        },
        {
            'label': 'سفارش‌های بدون پرداخت',
            'value': f"{current['unpaid']:,}",
            'unit': 'سفارش',
            'growth': _pct_change(current['unpaid'], previous['unpaid']),
            'compare': f"از {current['all_orders']:,} سفارش ثبت‌شده",
            'tone': 'rose',
            'invert': True,
        },
    ]

    # پرفروش‌ترین محصولات همراه تصویر، سهم از فروش و موجودی فعلی
    top_products_rows = list(
        OrderItem.objects.filter(order__in=paid)
        .values('product_id', 'product_title', 'product_sku')
        .annotate(qty=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')[:10]
    )
    product_map = {
        product.pk: product
        for product in Product.objects.filter(pk__in=[row['product_id'] for row in top_products_rows if row['product_id']])
        .select_related('category')
        .prefetch_related('images')
    }
    for row in top_products_rows:
        row['product'] = product_map.get(row['product_id'])
        row['share'] = round((row['revenue'] / current['revenue']) * 100, 1) if current['revenue'] else 0

    # محصولات فعالی که در این بازه فروشی نداشته‌اند (راکد)
    sold_ids = OrderItem.objects.filter(order__in=paid, product__isnull=False).values('product_id')
    dead_stock = list(
        Product.objects.filter(is_active=True)
        .exclude(pk__in=sold_ids)
        .select_related('category', 'brand')
        .prefetch_related('images')
        .order_by('-stock_qty')[:8]
    )
    dead_stock_rows = [
        {'product': product, 'stock_value': product.stock_qty * product.price}
        for product in dead_stock
    ]

    low_stock_products = list(
        Product.objects.filter(is_active=True, stock_qty__lte=F('low_stock_threshold'))
        .select_related('category')
        .prefetch_related('images')
        .order_by('stock_qty')[:8]
    )

    top_value_products = list(
        Product.objects.annotate(inventory_value=F('stock_qty') * F('price'))
        .select_related('category')
        .prefetch_related('images')
        .order_by('-inventory_value')[:8]
    )

    top_customers = list(
        paid.exclude(user__isnull=True)
        .values('user_id', 'user__username', 'user__first_name', 'user__last_name', 'user__phone_number')
        .annotate(orders=Count('id'), revenue=Sum('final_amount'))
        .order_by('-revenue')[:8]
    )

    repeat_buyers = (
        paid.exclude(user__isnull=True).values('user').annotate(c=Count('id')).filter(c__gt=1).count()
    )

    coupon_stats = list(
        paid.exclude(coupon_code='')
        .values('coupon_code')
        .annotate(orders=Count('id'), discount=Sum('coupon_discount'), revenue=Sum('final_amount'))
        .order_by('-discount')[:6]
    )

    max_revenue = max([row['revenue'] for row in daily] or [0]) or 1

    context = {
        'start': start,
        'end': end,
        'period_days': period_days,
        'prev_start': prev_start_dt.date(),
        'prev_end': prev_end_dt.date(),
        'kpis': kpis,
        'charts': charts,
        'current': current,
        'previous': previous,
        'inventory': inv,
        'inventory_value': f"{inv['value']:,}",
        'inventory_units': f"{inv['units']:,}",
        'daily': daily,
        'max_revenue': max_revenue,
        'status_breakdown': status_breakdown,
        'payment_breakdown': payment_breakdown,
        'shipping_breakdown': shipping_breakdown,
        'top_products': top_products_rows,
        'top_categories': top_categories,
        'dead_stock': dead_stock_rows,
        'low_stock_products': low_stock_products,
        'top_value_products': top_value_products,
        'top_customers': top_customers,
        'repeat_buyers': repeat_buyers,
        'coupons': coupon_stats,
        'revenue': f"{current['revenue']:,}",
        'revenue_raw': current['revenue'],
        'paid_count': current['orders'],
        'avg_order': f"{current['avg_order']:,}",
        'orders_total': current['all_orders'],
        'unpaid_count': current['unpaid'],
        'items_sold': f"{current['items']:,}",
        'preset_seven': (timezone.localdate() - timedelta(days=6)).isoformat(),
        'preset_thirty': (timezone.localdate() - timedelta(days=29)).isoformat(),
        'preset_ninety': (timezone.localdate() - timedelta(days=89)).isoformat(),
        'preset_year': (timezone.localdate() - timedelta(days=364)).isoformat(),
    }
    return render(request, 'dashboard/reports.html', context)


@staff
def reports_products_export_view(request):
    """خروجی CSV فروش به تفکیک محصول در بازه انتخاب‌شده."""
    start, end, start_dt, end_dt = date_range_from_request(request)
    paid = Order.objects.filter(created_at__range=(start_dt, end_dt), payment_status='successful')
    rows = (
        OrderItem.objects.filter(order__in=paid)
        .values('product_title', 'product_sku')
        .annotate(qty=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    stock_map = {
        product.sku: product
        for product in Product.objects.filter(sku__in=[row['product_sku'] for row in rows])
    }
    data = []
    for row in rows:
        product = stock_map.get(row['product_sku'])
        data.append([
            row['product_title'],
            row['product_sku'],
            product.category.name if product and product.category else '-',
            row['qty'],
            row['revenue'],
            product.stock_qty if product else '-',
        ])
    return csv_response(
        f"product-sales-{start}-{end}.csv",
        ['محصول', 'کد کالا', 'دسته‌بندی', 'تعداد فروش', 'درآمد (تومان)', 'موجودی فعلی'],
        data,
    )


@staff
def reports_inventory_export_view(request):
    """خروجی CSV وضعیت و ارزش ریالی انبار."""
    products = (
        Product.objects.select_related('category', 'brand')
        .annotate(inventory_value=F('stock_qty') * F('price'))
        .order_by('-inventory_value')
    )
    rows = []
    for product in products:
        if product.stock_qty == 0:
            status = 'ناموجود'
        elif product.stock_qty <= product.low_stock_threshold:
            status = 'کم‌موجود'
        else:
            status = 'موجود'
        rows.append([
            product.sku,
            product.title,
            product.category.name if product.category else '-',
            product.brand.name if product.brand else '-',
            product.price,
            product.stock_qty,
            product.low_stock_threshold,
            product.inventory_value or 0,
            status,
            'فعال' if product.is_active else 'غیرفعال',
        ])
    return csv_response(
        f"inventory-{timezone.localdate()}.csv",
        ['کد کالا', 'محصول', 'دسته‌بندی', 'برند', 'قیمت (تومان)', 'موجودی',
         'حد هشدار', 'ارزش انبار (تومان)', 'وضعیت موجودی', 'وضعیت نمایش'],
        rows,
    )


@staff
def reports_export_view(request):
    start, end, start_dt, end_dt = date_range_from_request(request)
    rows = (
        Order.objects.filter(created_at__range=(start_dt, end_dt))
        .values('order_number', 'created_at', 'status', 'payment_status', 'recipient_name',
                'recipient_phone', 'products_total', 'discount_amount', 'coupon_discount',
                'shipping_cost', 'final_amount')
        .order_by('-created_at')
    )
    status_labels = dict(Order.STATUS_CHOICES)
    payment_labels = dict(Order.PAYMENT_STATUS_CHOICES)
    data = [
        [
            row['order_number'],
            timezone.localtime(row['created_at']).strftime('%Y-%m-%d %H:%M'),
            status_labels.get(row['status'], row['status']),
            payment_labels.get(row['payment_status'], row['payment_status']),
            row['recipient_name'],
            row['recipient_phone'],
            row['products_total'],
            row['discount_amount'],
            row['coupon_discount'],
            row['shipping_cost'],
            row['final_amount'],
        ]
        for row in rows
    ]
    return csv_response(
        f"sales-{start}-{end}.csv",
        ['شماره سفارش', 'تاریخ', 'وضعیت', 'وضعیت پرداخت', 'خریدار', 'موبایل',
         'جمع کالا', 'تخفیف', 'کد تخفیف', 'ارسال', 'مبلغ نهایی'],
        data,
    )


# --------------------------------------------------------------------------
# محصولات
# --------------------------------------------------------------------------
@staff
def product_list_view(request):
    products = Product.objects.select_related('category', 'brand').prefetch_related('images')
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    status = request.GET.get('status')
    stock = request.GET.get('stock')
    sort = request.GET.get('sort', 'newest')

    if q:
        products = products.filter(Q(title__icontains=q) | Q(title_en__icontains=q) | Q(sku__icontains=q))
    if category_id:
        products = products.filter(category_id=to_int(category_id))
    if brand_id:
        products = products.filter(brand_id=to_int(brand_id))
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    elif status == 'featured':
        products = products.filter(is_featured=True)
    elif status == 'special':
        products = products.filter(is_special_offer=True)

    if stock == 'out':
        products = products.filter(stock_qty=0)
    elif stock == 'low':
        products = products.filter(stock_qty__gt=0, stock_qty__lte=F('low_stock_threshold'))
    elif stock == 'in':
        products = products.filter(stock_qty__gt=0)

    sort_map = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'cheapest': 'price',
        'expensive': '-price',
        'stock': 'stock_qty',
        'title': 'title',
    }
    products = products.order_by(sort_map.get(sort, '-created_at'))

    from django.core.paginator import Paginator
    paginator = Paginator(products, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'products': page_obj.object_list,
        'page_obj': page_obj,
        'search_query': q,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'filters': {
            'category': category_id or '',
            'brand': brand_id or '',
            'status': status or '',
            'stock': stock or '',
            'sort': sort,
        },
        'total_count': paginator.count,
        'querystring': _querystring_without_page(request),
    }
    return render(request, 'dashboard/products.html', context)


@staff
def product_form_view(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    categories = category_options()
    brands = Brand.objects.all()
    attributes = CategoryAttribute.objects.filter(is_active=True).select_related('category')

    def form_context():
        return {
            'product': product, 'category_options': categories,
            'brands': brands, 'attributes': attributes,
        }

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        sku = request.POST.get('sku', '').strip()
        category = Category.objects.filter(pk=to_int(request.POST.get('category'))).first()

        if not title or not sku or not category:
            messages.error(request, "عنوان، کد کالا (SKU) و دسته‌بندی الزامی هستند.")
            return render(request, 'dashboard/product_form.html', form_context())

        if Product.objects.filter(sku=sku).exclude(pk=pk).exists():
            messages.error(request, f"کد کالا «{sku}» قبلاً برای محصول دیگری ثبت شده است.")
            return render(request, 'dashboard/product_form.html', form_context())

        compare_at_price = to_int(request.POST.get('compare_at_price'), 0) or None
        stock_qty = to_int(request.POST.get('stock_qty'), 0)

        if product is None:
            product = Product()

        product.title = title
        product.title_en = request.POST.get('title_en', '').strip()
        product.slug = unique_slug(Product, title, product)
        product.sku = sku
        product.category = category
        product.brand = Brand.objects.filter(pk=to_int(request.POST.get('brand'))).first()
        product.price = to_int(request.POST.get('price'), 0)
        product.compare_at_price = compare_at_price
        product.stock_qty = stock_qty
        product.low_stock_threshold = to_int(request.POST.get('low_stock_threshold'), 5)
        product.short_description = request.POST.get('short_description', '').strip()
        product.description = request.POST.get('description', '').strip()
        product.warranty = request.POST.get('warranty', '').strip()
        product.rating = request.POST.get('rating') or 4.5
        product.is_active = to_bool(request, 'is_active')
        product.is_featured = to_bool(request, 'is_featured')
        product.is_special_offer = to_bool(request, 'is_special_offer')
        product.save()

        save_uploaded_images(product, request)
        save_specifications(product, request)

        messages.success(request, f"محصول «{product.title}» با موفقیت ذخیره شد.")
        return redirect('dashboard:products')

    return render(request, 'dashboard/product_form.html', form_context())


@staff
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        title = product.title
        product.delete()
        messages.success(request, f"محصول «{title}» حذف شد.")
    return redirect('dashboard:products')


@staff
@require_POST
def product_bulk_view(request):
    action = request.POST.get('action')
    ids = [to_int(value) for value in request.POST.getlist('ids')]
    products = Product.objects.filter(pk__in=ids)
    count = products.count()

    if not count:
        messages.warning(request, "هیچ محصولی انتخاب نشده بود.")
    elif action == 'activate':
        products.update(is_active=True)
        messages.success(request, f"{count} محصول فعال شد.")
    elif action == 'deactivate':
        products.update(is_active=False)
        messages.success(request, f"{count} محصول غیرفعال شد.")
    elif action == 'feature':
        products.update(is_featured=True)
        messages.success(request, f"{count} محصول به برگزیده‌ها اضافه شد.")
    elif action == 'unfeature':
        products.update(is_featured=False)
        messages.success(request, f"{count} محصول از برگزیده‌ها حذف شد.")
    elif action == 'special':
        products.update(is_special_offer=True)
        messages.success(request, f"{count} محصول به پیشنهادهای شگفت‌انگیز اضافه شد.")
    elif action == 'unspecial':
        products.update(is_special_offer=False)
        messages.success(request, f"{count} محصول از پیشنهادهای شگفت‌انگیز حذف شد.")
    elif action == 'delete':
        products.delete()
        messages.success(request, f"{count} محصول حذف شد.")
    else:
        messages.error(request, "عملیات انتخاب‌شده معتبر نیست.")

    return redirect(request.POST.get('next') or 'dashboard:products')


@staff
@require_POST
def product_toggle_view(request, pk, field):
    allowed = {'active': 'is_active', 'featured': 'is_featured', 'special': 'is_special_offer'}
    if field not in allowed:
        messages.error(request, "فیلد نامعتبر است.")
        return redirect('dashboard:products')
    product = get_object_or_404(Product, pk=pk)
    setattr(product, allowed[field], not getattr(product, allowed[field]))
    product.save(update_fields=[allowed[field]])
    messages.success(request, f"وضعیت «{product.title}» به‌روزرسانی شد.")
    return redirect(request.POST.get('next') or 'dashboard:products')


@staff
@require_POST
def product_image_delete_view(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    product = image.product
    was_primary = image.is_primary
    image.delete()
    if was_primary:
        fallback = product.images.first()
        if fallback:
            fallback.is_primary = True
            fallback.save(update_fields=['is_primary'])
    messages.success(request, "تصویر محصول حذف شد.")
    return redirect('dashboard:product_edit', pk=product.pk)


@staff
@require_POST
def product_image_primary_view(request, pk):
    image = get_object_or_404(ProductImage, pk=pk)
    image.product.images.update(is_primary=False)
    image.is_primary = True
    image.save(update_fields=['is_primary'])
    messages.success(request, "تصویر اصلی محصول تغییر کرد.")
    return redirect('dashboard:product_edit', pk=image.product_id)


@staff
def inventory_view(request):
    products = Product.objects.select_related('category', 'brand')

    if request.method == 'POST':
        updated = 0
        for product in products:
            key = f"stock_{product.pk}"
            if key in request.POST:
                new_qty = to_int(request.POST.get(key), product.stock_qty)
                threshold_key = f"threshold_{product.pk}"
                threshold = to_int(request.POST.get(threshold_key), product.low_stock_threshold)
                if new_qty != product.stock_qty or threshold != product.low_stock_threshold:
                    product.stock_qty = max(new_qty, 0)
                    product.low_stock_threshold = max(threshold, 0)
                    product.save()
                    updated += 1
        if updated:
            messages.success(request, f"موجودی {updated} کالا به‌روزرسانی شد.")
        else:
            messages.warning(request, "تغییری در موجودی کالاها ثبت نشد.")
        return redirect('dashboard:inventory')

    stock = request.GET.get('stock')
    category_id = request.GET.get('category')
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(Q(title__icontains=q) | Q(sku__icontains=q))
    if category_id:
        products = products.filter(category_id=to_int(category_id))
    if stock == 'out':
        products = products.filter(stock_qty=0)
    elif stock == 'low':
        products = products.filter(stock_qty__gt=0, stock_qty__lte=F('low_stock_threshold'))

    totals = products.aggregate(
        items=Count('id'),
        stock_units=Sum('stock_qty'),
        inventory_value=Sum(F('price') * F('stock_qty')),
    )
    context = {
        'products': products.order_by('stock_qty')[:200],
        'categories': Category.objects.all(),
        'stock_filter': stock or '',
        'category_filter': category_id or '',
        'search_query': q,
        'total_items': totals['items'] or 0,
        'stock_units': totals['stock_units'] or 0,
        'inventory_value': f"{(totals['inventory_value'] or 0):,}",
    }
    return render(request, 'dashboard/inventory.html', context)


# --------------------------------------------------------------------------
# دسته‌بندی‌ها
# --------------------------------------------------------------------------
@staff
def category_list_view(request):
    query = request.GET.get('q', '').strip()
    categories = category_tree()
    if query:
        categories = [c for c in categories if query in c.name or query in (c.name_en or '')]
    context = {
        'categories': categories,
        'search_query': query,
        'products_count': Product.objects.count(),
        'without_product_count': Category.objects.filter(products__isnull=True).count(),
    }
    return render(request, 'dashboard/categories.html', context)


@staff
def category_form_view(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None

    def form_context():
        return {'category': category, 'category_options': category_options(category)}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "نام دسته‌بندی الزامی است.")
            return render(request, 'dashboard/category_form.html', form_context())

        parent_id = to_int(request.POST.get('parent'), 0)
        if category and parent_id == category.pk:
            messages.error(request, "یک دسته‌بندی نمی‌تواند والد خودش باشد.")
            return render(request, 'dashboard/category_form.html', form_context())

        if category is None:
            category = Category()

        category.name = name
        category.name_en = request.POST.get('name_en', '').strip()
        category.slug = unique_slug(Category, category.name_en or name, category)
        category.parent = Category.objects.filter(pk=parent_id).exclude(pk=category.pk if category.pk else 0).first()
        category.icon_svg = request.POST.get('icon_svg', '').strip()
        category.order = to_int(request.POST.get('order'), 0)
        category.is_active = to_bool(request, 'is_active')
        if request.FILES.get('image'):
            category.image = request.FILES['image']
        category.save()

        messages.success(request, f"دسته‌بندی «{category.name}» ذخیره شد.")
        return redirect('dashboard:categories')

    return render(request, 'dashboard/category_form.html', form_context())


@staff
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        products_count = category.products.count()
        children_count = category.children.count()
        if products_count:
            messages.error(request, f"این دسته {products_count} محصول دارد؛ ابتدا محصولات را منتقل یا حذف کنید.")
        elif children_count:
            messages.error(request, f"این دسته {children_count} زیردسته دارد؛ ابتدا زیردسته‌ها را حذف کنید.")
        else:
            name = category.name
            category.delete()
            messages.success(request, f"دسته‌بندی «{name}» حذف شد.")
    return redirect('dashboard:categories')


@staff
@require_POST
def category_toggle_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=['is_active'])
    messages.success(request, f"وضعیت «{category.name}» به‌روزرسانی شد.")
    return redirect('dashboard:categories')


# --------------------------------------------------------------------------
# برندها
# --------------------------------------------------------------------------
@staff
def brand_list_view(request):
    query = request.GET.get('q', '').strip()
    brands = Brand.objects.annotate(products_count=Count('products'))
    if query:
        brands = brands.filter(Q(name__icontains=query) | Q(name_en__icontains=query))
    return render(request, 'dashboard/brands.html', {
        'brands': brands,
        'search_query': query,
    })


@staff
def brand_form_view(request, pk=None):
    brand = get_object_or_404(Brand, pk=pk) if pk else None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "نام برند الزامی است.")
            return render(request, 'dashboard/brand_form.html', {'brand': brand})

        if brand is None:
            brand = Brand()
        brand.name = name
        brand.name_en = request.POST.get('name_en', '').strip()
        brand.slug = unique_slug(Brand, brand.name_en or name, brand)
        brand.order = to_int(request.POST.get('order'), 0)
        brand.is_active = to_bool(request, 'is_active')
        if request.FILES.get('logo'):
            brand.logo = request.FILES['logo']
        brand.save()

        messages.success(request, f"برند «{brand.name}» ذخیره شد.")
        return redirect('dashboard:brands')

    return render(request, 'dashboard/brand_form.html', {'brand': brand})


@staff
def brand_delete_view(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        name = brand.name
        brand.delete()  # محصولات با SET_NULL بدون برند می‌شوند
        messages.success(request, f"برند «{name}» حذف شد.")
    return redirect('dashboard:brands')


# --------------------------------------------------------------------------
# ویژگی‌ها (Attributes)
# --------------------------------------------------------------------------
@staff
def attribute_list_view(request):
    attributes = CategoryAttribute.objects.select_related('category')
    category_id = request.GET.get('category')
    if category_id == 'general':
        attributes = attributes.filter(category__isnull=True)
    elif category_id:
        attributes = attributes.filter(category_id=to_int(category_id))

    if request.method == 'POST':  # افزودن سریع از همان صفحه
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "نام ویژگی الزامی است.")
        else:
            CategoryAttribute.objects.create(
                name=name,
                category=Category.objects.filter(pk=to_int(request.POST.get('category'))).first(),
                unit=request.POST.get('unit', '').strip(),
                type=request.POST.get('type', 'text'),
                options=request.POST.get('options', '').strip(),
                order=to_int(request.POST.get('order'), 0),
            )
            messages.success(request, f"ویژگی «{name}» اضافه شد.")
        return redirect('dashboard:attributes')

    return render(request, 'dashboard/attributes.html', {
        'attributes': attributes,
        'categories': category_options(),
        'category_filter': category_id or '',
        'type_choices': CategoryAttribute.TYPE_CHOICES,
    })


@staff
def attribute_form_view(request, pk):
    attribute = get_object_or_404(CategoryAttribute, pk=pk)

    if request.method == 'POST':
        attribute.name = request.POST.get('name', '').strip() or attribute.name
        attribute.category = Category.objects.filter(pk=to_int(request.POST.get('category'))).first()
        attribute.unit = request.POST.get('unit', '').strip()
        attribute.type = request.POST.get('type', 'text')
        attribute.options = request.POST.get('options', '').strip()
        attribute.order = to_int(request.POST.get('order'), 0)
        attribute.is_active = to_bool(request, 'is_active')
        attribute.save()
        messages.success(request, "ویژگی ذخیره شد.")
        return redirect('dashboard:attributes')

    return render(request, 'dashboard/attribute_form.html', {
        'attribute': attribute,
        'categories': category_options(),
        'type_choices': CategoryAttribute.TYPE_CHOICES,
    })


@staff
def attribute_delete_view(request, pk):
    attribute = get_object_or_404(CategoryAttribute, pk=pk)
    if request.method == 'POST':
        attribute.delete()
        messages.success(request, "ویژگی حذف شد.")
    return redirect('dashboard:attributes')


# --------------------------------------------------------------------------
# بنرها
# --------------------------------------------------------------------------
@staff
def banner_list_view(request):
    position = request.GET.get('position') or 'hero'
    banners = Banner.objects.filter(position=position)
    return render(request, 'dashboard/banners.html', {
        'banners': banners,
        'position': position,
        'position_choices': Banner.POSITION_CHOICES,
        'position_counts': {
            key: Banner.objects.filter(position=key).count() for key, _ in Banner.POSITION_CHOICES
        },
    })


@staff
def banner_form_view(request, pk=None):
    banner = get_object_or_404(Banner, pk=pk) if pk else None

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "عنوان بنر الزامی است.")
            return render(request, 'dashboard/banner_form.html', {
                'banner': banner, 'position_choices': Banner.POSITION_CHOICES,
            })

        if banner is None:
            banner = Banner()
        banner.title = title
        banner.subtitle = request.POST.get('subtitle', '').strip()
        banner.link_url = request.POST.get('link_url', '/').strip() or '/'
        banner.button_text = request.POST.get('button_text', '').strip()
        banner.position = request.POST.get('position', 'hero')
        banner.order = to_int(request.POST.get('order'), 0)
        banner.is_active = to_bool(request, 'is_active')
        if request.FILES.get('image'):
            banner.image = request.FILES['image']
        elif banner.pk is None:
            messages.error(request, "انتخاب تصویر بنر الزامی است.")
            return render(request, 'dashboard/banner_form.html', {
                'banner': banner, 'position_choices': Banner.POSITION_CHOICES,
            })
        banner.save()

        messages.success(request, f"بنر «{banner.title}» ذخیره شد.")
        return redirect(f"/dashboard/banners/?position={banner.position}")

    return render(request, 'dashboard/banner_form.html', {
        'banner': banner,
        'position_choices': Banner.POSITION_CHOICES,
    })


@staff
def banner_delete_view(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    if request.method == 'POST':
        banner.delete()
        messages.success(request, "بنر حذف شد.")
    return redirect('dashboard:banners')


@staff
@require_POST
def banner_toggle_view(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save(update_fields=['is_active'])
    messages.success(request, f"وضعیت بنر «{banner.title}» به‌روزرسانی شد.")
    return redirect(f"/dashboard/banners/?position={banner.position}")


@staff
@require_POST
def banner_move_view(request, pk, direction):
    banner = get_object_or_404(Banner, pk=pk)
    siblings = list(Banner.objects.filter(position=banner.position).order_by('order', 'id'))
    index = next((i for i, item in enumerate(siblings) if item.pk == banner.pk), None)
    if index is None:
        return redirect('dashboard:banners')

    if direction == 'up' and index > 0:
        banner.order, siblings[index - 1].order = siblings[index - 1].order, banner.order
    elif direction == 'down' and index < len(siblings) - 1:
        banner.order, siblings[index + 1].order = siblings[index + 1].order, banner.order
    else:  # چرخش به ابتدای لیست/انتهای لیست
        banner.order = (banner.order - 1) if direction == 'up' else (banner.order + 1)
    banner.save(update_fields=['order'])
    return redirect(f"/dashboard/banners/?position={banner.position}")


# --------------------------------------------------------------------------
# سفارش‌ها
# --------------------------------------------------------------------------
def _filtered_orders(request):
    orders = Order.objects.select_related('user', 'coupon').prefetch_related('items')
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    payment = request.GET.get('payment')
    method = request.GET.get('method')
    if q:
        orders = orders.filter(
            Q(order_number__icontains=q) | Q(recipient_phone__icontains=q) |
            Q(recipient_name__icontains=q) | Q(tracking_code__icontains=q)
        )
    if status:
        orders = orders.filter(status=status)
    if payment:
        orders = orders.filter(payment_status=payment)
    if method:
        orders = orders.filter(payment_method=method)
    if request.GET.get('from') or request.GET.get('to'):
        _, _, start_dt, end_dt = date_range_from_request(request)
        orders = orders.filter(created_at__range=(start_dt, end_dt))
    return orders, q


@staff
def order_list_view(request):
    orders, q = _filtered_orders(request)
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
        'status_filter': request.GET.get('status') or '',
        'payment_filter': request.GET.get('payment') or '',
        'method_filter': request.GET.get('method') or '',
        'date_from': request.GET.get('from') or '',
        'date_to': request.GET.get('to') or '',
        'search_query': q,
        'status_choices': Order.STATUS_CHOICES,
        'payment_choices': Order.PAYMENT_STATUS_CHOICES,
        'method_choices': Order.PAYMENT_METHOD_CHOICES,
        'total_count': paginator.count,
        'pending_count': Order.objects.filter(status='pending').count(),
        'paid_count': Order.objects.filter(status='paid').count(),
        'shipped_count': Order.objects.filter(status='shipped').count(),
        'delivered_count': Order.objects.filter(status='delivered').count(),
        'cancelled_count': Order.objects.filter(status='cancelled').count(),
        'querystring': _querystring_without_page(request),
    }
    return render(request, 'dashboard/orders.html', context)


@staff
def order_detail_view(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('user', 'coupon').prefetch_related('items__product'),
        pk=pk,
    )
    return render(request, 'dashboard/order_detail.html', {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
        'payment_choices': Order.PAYMENT_STATUS_CHOICES,
        'shipping_choices': Order.SHIPPING_CHOICES,
    })


@staff
def order_update_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        payment_status = request.POST.get('payment_status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
        if payment_status in dict(Order.PAYMENT_STATUS_CHOICES):
            order.payment_status = payment_status
        if 'tracking_code' in request.POST:
            order.tracking_code = request.POST.get('tracking_code', '').strip()
        if 'shipping_method' in request.POST and request.POST.get('shipping_method') in dict(Order.SHIPPING_CHOICES):
            order.shipping_method = request.POST.get('shipping_method')
        if 'admin_note' in request.POST:
            order.admin_note = request.POST.get('admin_note', '').strip()
        order.save()
        if order.status == 'cancelled':
            order.release_stock()
        messages.success(request, f"سفارش {order.order_number} به‌روزرسانی شد.")
        return redirect('dashboard:order_detail', pk=order.pk)
    return redirect('dashboard:orders')


@staff
@require_POST
def order_status_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        if new_status == 'cancelled' and order.payment_status == 'successful':
            order.payment_status = 'failed'
        order.save()
        if new_status == 'cancelled':
            # موجودی رزروشده آزاد یا کالای فروش‌رفته به انبار برگردانده می‌شود.
            order.release_stock()
        messages.success(request, f"وضعیت سفارش {order.order_number} بروزرسانی شد.")
    else:
        messages.error(request, "وضعیت انتخابی معتبر نیست.")
    return redirect(request.POST.get('next') or 'dashboard:orders')


@staff
def orders_export_view(request):
    orders, _ = _filtered_orders(request)
    status_labels = dict(Order.STATUS_CHOICES)
    payment_labels = dict(Order.PAYMENT_STATUS_CHOICES)
    method_labels = dict(Order.PAYMENT_METHOD_CHOICES)
    rows = [
        [
            order.order_number,
            timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M'),
            order.recipient_name,
            order.recipient_phone,
            f"{order.province} - {order.city}",
            order.shipping_address,
            order.postal_code,
            status_labels.get(order.status, order.status),
            payment_labels.get(order.payment_status, order.payment_status),
            method_labels.get(order.payment_method, order.payment_method),
            order.tracking_code,
            order.products_total,
            order.discount_amount,
            order.coupon_code,
            order.shipping_cost,
            order.final_amount,
        ]
        for order in orders
    ]
    return csv_response(
        f"orders-{timezone.localdate()}.csv",
        ['شماره سفارش', 'تاریخ', 'گیرنده', 'موبایل', 'استان/شهر', 'آدرس', 'کد پستی',
         'وضعیت سفارش', 'وضعیت پرداخت', 'روش پرداخت', 'کد رهگیری',
         'جمع کالا', 'تخفیف', 'کد تخفیف', 'هزینه ارسال', 'مبلغ نهایی'],
        rows,
    )


# --------------------------------------------------------------------------
# مشتریان
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# مشتریان
# --------------------------------------------------------------------------
CUSTOMER_SEGMENTS = {
    'vip': {'label': 'مشتری ویژه', 'tone': 'bg-gradient-to-l from-amber-500 to-yellow-300 text-amber-900'},
    'loyal': {'label': 'وفادار', 'tone': 'bg-indigo-50 text-indigo-700 border border-indigo-100'},
    'active': {'label': 'خریدار فعال', 'tone': 'bg-emerald-50 text-emerald-700 border border-emerald-100'},
    'new': {'label': 'تازه‌وارد', 'tone': 'bg-sky-50 text-sky-700 border border-sky-100'},
    'dormant': {'label': 'راکد', 'tone': 'bg-slate-100 text-slate-500 border border-slate-200'},
    'lead': {'label': 'بدون خرید', 'tone': 'bg-rose-50 text-rose-600 border border-rose-100'},
}


def _customer_segment(customer, vip_threshold, now):
    """تعیین سگمنت مشتری برای نمایش در لیست و پرونده."""
    if customer.is_staff:
        return 'staff'
    if not customer.orders_count:
        return 'lead'
    if (customer.total_spent or 0) >= vip_threshold and customer.paid_orders >= 2:
        return 'vip'
    if customer.paid_orders >= 3:
        return 'loyal'
    if customer.last_order_at and (now - customer.last_order_at).days > 90:
        return 'dormant'
    if customer.date_joined and (now - customer.date_joined).days <= 30:
        return 'new'
    return 'active'


@staff
def customer_list_view(request):
    now = timezone.now()
    customers = User.objects.annotate(
        orders_count=Count('orders', distinct=True),
        paid_orders=Count('orders', filter=Q(orders__payment_status='successful'), distinct=True),
        total_spent=Sum('orders__final_amount', filter=Q(orders__payment_status='successful')),
        last_order_at=Max('orders__created_at'),
    )
    q = request.GET.get('q', '').strip()
    if q:
        customers = customers.filter(
            Q(username__icontains=q) | Q(phone_number__icontains=q) |
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    role = request.GET.get('role')
    if role == 'staff':
        customers = customers.filter(is_staff=True)
    elif role == 'customers':
        customers = customers.filter(is_staff=False)

    segment_filter = request.GET.get('segment', '')
    sort_map = {
        'newest': '-date_joined',
        'spent': '-total_spent',
        'orders': '-orders_count',
        'recent': '-last_order_at',
        'name': 'username',
    }
    sort = request.GET.get('sort', 'spent')
    customers = customers.order_by(sort_map.get(sort, '-date_joined'))

    # آستانه مشتری ویژه: بالاترین ۱۰٪ خریدها یا بیش از ۵۰ میلیون تومان
    spent_values = [
        value for value in User.objects.filter(is_staff=False)
        .filter(orders__payment_status='successful')
        .annotate(spent=Sum('orders__final_amount', filter=Q(orders__payment_status='successful')))
        .values_list('spent', flat=True)
        if value
    ]
    spent_values.sort(reverse=True)
    if spent_values:
        top_index = max(int(len(spent_values) * 0.1) - 1, 0)
        vip_threshold = max(spent_values[top_index], 50000000)
    else:
        vip_threshold = 50000000

    rows = list(customers)
    for customer in rows:
        customer.segment = _customer_segment(customer, vip_threshold, now)
        if customer.segment != 'staff':
            info = CUSTOMER_SEGMENTS.get(customer.segment, CUSTOMER_SEGMENTS['active'])
            customer.segment_label = info['label']
            customer.segment_tone = info['tone']
        else:
            customer.segment_label = 'کاربر پنل'
            customer.segment_tone = 'bg-slate-900 text-white'
        customer.avg_order_value = (
            int((customer.total_spent or 0) / customer.paid_orders) if customer.paid_orders else 0
        )
        customer.is_vip = customer.segment == 'vip'

    if segment_filter:
        rows = [customer for customer in rows if customer.segment == segment_filter]

    try:
        page_number = int(request.GET.get('page', 1))
    except (TypeError, ValueError):
        page_number = 1
    page_size = 20
    total_rows = len(rows)
    total_pages = max((total_rows + page_size - 1) // page_size, 1)
    page_number = min(max(page_number, 1), total_pages)
    start_index = (page_number - 1) * page_size
    page_rows = rows[start_index:start_index + page_size]

    max_spent = max([customer.total_spent or 0 for customer in rows] or [0]) or 1
    for customer in page_rows:
        customer.spend_share = round(((customer.total_spent or 0) / max_spent) * 100)

    successful = Order.objects.filter(payment_status='successful')
    active_buyers = successful.exclude(user__isnull=True).values('user').distinct().count()
    repeat_buyers = (
        successful.exclude(user__isnull=True).values('user').annotate(c=Count('id')).filter(c__gt=1).count()
    )
    revenue_total = successful.aggregate(s=Sum('final_amount'))['s'] or 0

    context = {
        'customers': page_rows,
        'segment_counts': {
            'all': User.objects.count(),
            'customers': User.objects.filter(is_staff=False).count(),
            'staff': User.objects.filter(is_staff=True).count(),
            'buyers': active_buyers,
            'no_order': User.objects.filter(is_staff=False, orders__isnull=True).count(),
        },
        'avg_ltv': f"{int(revenue_total / active_buyers) if active_buyers else 0:,}",
        'repeat_rate': round((repeat_buyers / active_buyers) * 100, 1) if active_buyers else 0,
        'new_last_month': User.objects.filter(is_staff=False, date_joined__gte=now - timedelta(days=30)).count(),
        'vip_threshold': f"{vip_threshold:,}",
        'search_query': q,
        'role_filter': role or '',
        'segment_filter': segment_filter,
        'sort': sort,
        'total_count': total_rows,
        'querystring': _querystring_without_page(request),
        'page_obj': {
            'number': page_number,
            'num_pages': total_pages,
            'has_previous': page_number > 1,
            'has_next': page_number < total_pages,
            'previous_page_number': page_number - 1,
            'next_page_number': page_number + 1,
            'start_index': start_index + 1 if total_rows else 0,
            'end_index': min(start_index + page_size, total_rows),
            'total': total_rows,
        },
    }
    return render(request, 'dashboard/customers.html', context)


@staff
def customer_detail_view(request, pk):
    customer = get_object_or_404(User, pk=pk)
    now = timezone.now()
    orders = customer.orders.prefetch_related('items').order_by('-created_at')
    paid = orders.filter(payment_status='successful')
    totals = paid.aggregate(s=Sum('final_amount'), avg=Avg('final_amount'), c=Count('id'))
    total_spent = totals['s'] or 0

    # روند خرید ۱۲ ماه اخیر
    month_rows = (
        paid.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(revenue=Sum('final_amount'), orders=Count('id'))
        .order_by('month')
    )
    monthly = [
        {'label': to_fa(row['month'].strftime('%Y/%m')), 'revenue': row['revenue'] or 0, 'orders': row['orders']}
        for row in month_rows
    ]

    # محصولات پرتکرار این مشتری
    favourite_products = list(
        OrderItem.objects.filter(order__in=paid)
        .values('product_title', 'product_id')
        .annotate(qty=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-qty')[:5]
    )

    favourite_category = (
        OrderItem.objects.filter(order__in=paid, product__isnull=False)
        .values('product__category__name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')
        .first()
    )

    last_order = orders.first()
    days_since_last = (now - last_order.created_at).days if last_order else None

    context = {
        'customer': customer,
        'orders': orders[:30],
        'orders_count': orders.count(),
        'paid_count': totals['c'] or 0,
        'total_spent': f"{total_spent:,}",
        'total_spent_raw': total_spent,
        'avg_order_value': f"{int(totals['avg'] or 0):,}",
        'items_bought': OrderItem.objects.filter(order__in=paid).aggregate(q=Sum('quantity'))['q'] or 0,
        'addresses': customer.addresses.all(),
        'chart_months': {
            'labels': [row['label'] for row in monthly],
            'revenue': [row['revenue'] for row in monthly],
            'orders': [row['orders'] for row in monthly],
        },
        'favourite_products': favourite_products,
        'favourite_category': favourite_category['product__category__name'] if favourite_category else None,
        'last_order': last_order,
        'days_since_last': days_since_last,
        'canceled_count': orders.filter(status='cancelled').count(),
        'pending_count': orders.filter(payment_status='pending').count(),
        'initial': (customer.get_full_name() or customer.username or '?')[:1].upper(),
    }
    return render(request, 'dashboard/customer_detail.html', context)


@staff
@require_POST
def customer_toggle_staff_view(request, pk):
    if request.user.pk == pk:
        messages.error(request, "نمی‌توانید دسترسی مدیریتی خودتان را تغییر دهید.")
        return redirect('dashboard:customers')
    customer = get_object_or_404(User, pk=pk)
    customer.is_staff = not customer.is_staff
    customer.save(update_fields=['is_staff'])
    messages.success(request, f"دسترسی پنل «{customer}» {'فعال' if customer.is_staff else 'غیرفعال'} شد.")
    return redirect('dashboard:customer_detail', pk=customer.pk)


# --------------------------------------------------------------------------
# کدهای تخفیف
# --------------------------------------------------------------------------
@staff
def coupon_list_view(request):
    coupons = Coupon.objects.annotate(orders_count=Count('orders'))
    return render(request, 'dashboard/coupons.html', {
        'coupons': coupons,
        'active_count': coupons.filter(is_active=True).count(),
        'used_total': Coupon.objects.aggregate(s=Sum('used_count'))['s'] or 0,
    })


@staff
def coupon_form_view(request, pk=None):
    coupon = get_object_or_404(Coupon, pk=pk) if pk else None

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        if not code:
            messages.error(request, "کد تخفیف الزامی است.")
            return render(request, 'dashboard/coupon_form.html', {
                'coupon': coupon, 'type_choices': Coupon.TYPE_CHOICES,
            })
        if Coupon.objects.filter(code=code).exclude(pk=pk).exists():
            messages.error(request, "این کد تخفیف قبلاً ثبت شده است.")
            return render(request, 'dashboard/coupon_form.html', {
                'coupon': coupon, 'type_choices': Coupon.TYPE_CHOICES,
            })

        if coupon is None:
            coupon = Coupon()
        coupon.code = code
        coupon.title = request.POST.get('title', '').strip()
        coupon.discount_type = request.POST.get('discount_type', 'percent')
        coupon.value = to_int(request.POST.get('value'), 0)
        coupon.min_order_amount = to_int(request.POST.get('min_order_amount'), 0)
        coupon.max_discount_amount = to_int(request.POST.get('max_discount_amount'), 0) or None
        coupon.max_uses = to_int(request.POST.get('max_uses'), 0)
        coupon.is_active = to_bool(request, 'is_active')
        coupon.valid_from = _parse_datetime(request.POST.get('valid_from'))
        coupon.valid_until = _parse_datetime(request.POST.get('valid_until'))
        coupon.save()
        messages.success(request, f"کد تخفیف «{coupon.code}» ذخیره شد.")
        return redirect('dashboard:coupons')

    return render(request, 'dashboard/coupon_form.html', {
        'coupon': coupon,
        'type_choices': Coupon.TYPE_CHOICES,
    })


def _parse_datetime(value):
    if not value:
        return None
    try:
        naive = datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        try:
            naive = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


@staff
def coupon_delete_view(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        coupon.delete()
        messages.success(request, "کد تخفیف حذف شد.")
    return redirect('dashboard:coupons')


@staff
@require_POST
def coupon_toggle_view(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    messages.success(request, f"وضعیت کد «{coupon.code}» به‌روزرسانی شد.")
    return redirect('dashboard:coupons')


# --------------------------------------------------------------------------
# مقالات و دسته‌های وبلاگ
# --------------------------------------------------------------------------
@staff
def post_list_view(request):
    posts = Post.objects.select_related('category', 'author')
    q = request.GET.get('q', '').strip()
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(content__icontains=q))
    status = request.GET.get('status')
    if status == 'published':
        posts = posts.filter(is_published=True)
    elif status == 'draft':
        posts = posts.filter(is_published=False)

    return render(request, 'dashboard/posts.html', {
        'posts': posts,
        'search_query': q,
        'status_filter': status or '',
        'categories': BlogCategory.objects.annotate(posts_count=Count('posts')),
        'published_count': Post.objects.filter(is_published=True).count(),
        'draft_count': Post.objects.filter(is_published=False).count(),
    })


@staff
def post_form_view(request, pk=None):
    post = get_object_or_404(Post, pk=pk) if pk else None
    categories = BlogCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if not title or not content:
            messages.error(request, "عنوان و متن مقاله الزامی هستند.")
            return render(request, 'dashboard/post_form.html', {'post': post, 'categories': categories})

        if post is None:
            post = Post(author=request.user)
        post.title = title
        post.slug = unique_slug(Post, title, post)
        post.category = BlogCategory.objects.filter(pk=to_int(request.POST.get('category'))).first()
        post.excerpt = request.POST.get('excerpt', '').strip()
        post.content = content
        post.is_published = to_bool(request, 'is_published')
        if request.FILES.get('cover_image'):
            post.cover_image = request.FILES['cover_image']
        post.save()
        messages.success(request, f"مقاله «{post.title}» ذخیره شد.")
        return redirect('dashboard:posts')

    return render(request, 'dashboard/post_form.html', {'post': post, 'categories': categories})


@staff
def post_delete_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        post.delete()
        messages.success(request, "مقاله حذف شد.")
    return redirect('dashboard:posts')


@staff
@require_POST
def post_toggle_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.is_published = not post.is_published
    post.save(update_fields=['is_published'])
    messages.success(request, f"وضعیت انتشار «{post.title}» تغییر کرد.")
    return redirect('dashboard:posts')


@staff
@require_POST
def blog_category_save_view(request, pk=None):
    category = get_object_or_404(BlogCategory, pk=pk) if pk else BlogCategory()
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, "نام دسته‌بندی مقاله الزامی است.")
        return redirect('dashboard:posts')
    category.name = name
    category.slug = unique_slug(BlogCategory, name, category if category.pk else None)
    category.order = to_int(request.POST.get('order'), 0)
    category.save()
    messages.success(request, f"دسته مقاله «{category.name}» ذخیره شد.")
    return redirect('dashboard:posts')


@staff
@require_POST
def blog_category_delete_view(request, pk):
    category = get_object_or_404(BlogCategory, pk=pk)
    category.delete()
    messages.success(request, "دسته مقاله حذف شد.")
    return redirect('dashboard:posts')


# --------------------------------------------------------------------------
# تنظیمات فروشگاه
# --------------------------------------------------------------------------
@staff
def settings_view(request):
    settings_obj = site_settings()
    if request.method == 'POST':
        settings_obj.store_name = request.POST.get('store_name', settings_obj.store_name)
        settings_obj.slogan = request.POST.get('slogan', '').strip()
        settings_obj.phone = request.POST.get('phone', '').strip()
        settings_obj.email = request.POST.get('email', '').strip()
        settings_obj.address = request.POST.get('address', '').strip()
        settings_obj.working_hours = request.POST.get('working_hours', '').strip()
        settings_obj.telegram = request.POST.get('telegram', '').strip()
        settings_obj.instagram = request.POST.get('instagram', '').strip()
        settings_obj.whatsapp = request.POST.get('whatsapp', '').strip()
        settings_obj.shipping_cost = to_int(request.POST.get('shipping_cost'), settings_obj.shipping_cost)
        settings_obj.free_shipping_threshold = to_int(request.POST.get('free_shipping_threshold'), 0)
        login_method = request.POST.get('login_method', '').strip()
        if login_method in ['otp', 'password']:
            settings_obj.login_method = login_method
        settings_obj.sms_api_key = request.POST.get('sms_api_key', '').strip()
        settings_obj.sms_line_number = request.POST.get('sms_line_number', '').strip()
        settings_obj.sms_otp_template_id = request.POST.get('sms_otp_template_id', '').strip()
        settings_obj.sms_is_active = 'sms_is_active' in request.POST
        settings_obj.about_us = request.POST.get('about_us', '').strip()
        settings_obj.footer_note = request.POST.get('footer_note', '').strip()
        settings_obj.save()
        messages.success(request, "تنظیمات فروشگاه ذخیره شد.")
        return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html', {'settings': settings_obj})


# --------------------------------------------------------------------------
# تیکت‌های پشتیبانی (چت)
# --------------------------------------------------------------------------
from tickets.models import Ticket, TicketMessage  # noqa: E402


@staff
def ticket_list_view(request):
    """فهرست تیکت‌های پشتیبانی با فیلتر وضعیت و جستجو."""
    tickets = Ticket.objects.select_related('user', 'assigned_to').order_by('-last_message_at')

    status_filter = request.GET.get('status', '').strip()
    if status_filter in dict(Ticket.STATUS_CHOICES):
        tickets = tickets.filter(status=status_filter)

    q = request.GET.get('q', '').strip()
    if q:
        tickets = tickets.filter(
            Q(subject__icontains=q) | Q(ticket_number__icontains=q)
            | Q(user__username__icontains=q) | Q(user__phone_number__icontains=q)
            | Q(messages__body__icontains=q)
        ).distinct()

    counts = dict(Ticket.objects.values('status').annotate(n=Count('id')).values_list('status', 'n'))
    status_summary = [(value, label, counts.get(value, 0)) for value, label in Ticket.STATUS_CHOICES]
    context = {
        'tickets': tickets[:200],
        'status_choices': Ticket.STATUS_CHOICES,
        'category_choices': Ticket.CATEGORY_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'status_filter': status_filter,
        'search_query': q,
        'status_summary': status_summary,
        'total_count': Ticket.objects.count(),
        'unread_count': Ticket.objects.filter(staff_unread=True).exclude(status=Ticket.STATUS_CLOSED).count(),
    }
    return render(request, 'dashboard/tickets.html', context)


@staff
def ticket_detail_view(request, pk):
    """گفتگوی تیکت در پنل مدیریت؛ پاسخ و تغییر وضعیت."""
    ticket = get_object_or_404(Ticket.objects.select_related('user', 'assigned_to'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'reply')

        if action == 'reply':
            body = request.POST.get('body', '').strip()
            if not body:
                messages.error(request, "متن پیام خالی است.")
                return redirect('dashboard:ticket_detail', pk=ticket.pk)
            if ticket.is_closed:
                ticket.status = Ticket.STATUS_IN_PROGRESS
                ticket.closed_at = None
            TicketMessage.objects.create(
                ticket=ticket, sender=request.user, body=body, is_staff_message=True
            )
            ticket.last_message_at = timezone.now()
            ticket.customer_unread = True
            ticket.staff_unread = False
            if ticket.assigned_to_id is None:
                ticket.assigned_to = request.user
            if ticket.status in (Ticket.STATUS_NEW, Ticket.STATUS_IN_PROGRESS):
                ticket.status = Ticket.STATUS_ANSWERED
            ticket.save()
            messages.success(request, "پیام ارسال شد.")
            return redirect('dashboard:ticket_detail', pk=ticket.pk)

        if action == 'status':
            new_status = request.POST.get('status', '')
            if new_status in dict(Ticket.STATUS_CHOICES):
                ticket.status = new_status
                if new_status == Ticket.STATUS_CLOSED:
                    ticket.closed_at = timezone.now()
                else:
                    ticket.closed_at = None
                ticket.save(update_fields=['status', 'closed_at', 'updated_at'])
                messages.success(request, "وضعیت تیکت به‌روزرسانی شد.")
            return redirect('dashboard:ticket_detail', pk=ticket.pk)

    if ticket.staff_unread:
        ticket.staff_unread = False
        ticket.save(update_fields=['staff_unread'])

    context = {
        'ticket': ticket,
        'messages_list': ticket.messages.select_related('sender'),
        'status_choices': Ticket.STATUS_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
    }
    return render(request, 'dashboard/ticket_detail.html', context)


@staff
def ticket_messages_partial_view(request, pk):
    """بخش پیام‌های تیکت برای به‌روزرسانی خودکار (polling)."""
    ticket = get_object_or_404(Ticket, pk=pk)
    if ticket.staff_unread:
        ticket.staff_unread = False
        ticket.save(update_fields=['staff_unread'])
    return render(request, 'dashboard/ticket_messages.html', {
        'ticket': ticket,
        'messages_list': ticket.messages.select_related('sender'),
    })


# --------------------------------------------------------------------------
# سامانه پیامک و کمپین‌ها (SMS.ir v2)
# --------------------------------------------------------------------------
from django.urls import reverse
from sms.models import SmsTemplate, SmsLog, SmsCampaign
from sms.services import (
    get_panel_status,
    send_sms as sms_send_service,
    send_pattern_sms,
    send_bulk_campaign_sms,
    normalize_phone,
)


@staff
def sms_dashboard_view(request):
    """داشبورد جامع مدیریت پیامک‌ها، کمپین‌ها، ارسال با پترن و آرشیو لاگ‌ها."""
    active_tab = request.GET.get('tab', 'overview').strip()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'send_single':
            mobile = request.POST.get('mobile', '').strip()
            user_id = request.POST.get('user_id', '').strip()
            if user_id and user_id.isdigit():
                target_user = User.objects.filter(pk=int(user_id)).first()
                if target_user and target_user.phone_number:
                    mobile = target_user.phone_number

            message = request.POST.get('message', '').strip()
            if not mobile or not message:
                messages.error(request, "لطفاً شماره گیرنده و متن پیامک را وارد کنید.")
            else:
                success = sms_send_service(mobile, message, sms_type='single', sender_user=request.user)
                if success:
                    messages.success(request, f"پیامک با موفقیت برای {mobile} ارسال گردید.")
                else:
                    messages.error(request, "خطا در ارسال پیامک. لاگ ارسال را بررسی نمایید.")
            return redirect(f"{reverse('dashboard:sms')}?tab=custom")

        elif action == 'send_pattern':
            mobile = request.POST.get('mobile', '').strip()
            user_id = request.POST.get('user_id', '').strip()
            if user_id and user_id.isdigit():
                target_user = User.objects.filter(pk=int(user_id)).first()
                if target_user and target_user.phone_number:
                    mobile = target_user.phone_number

            template_id_val = request.POST.get('template_id', '').strip()
            template_id = to_int(template_id_val)

            # استخراج پارامترهای پویا
            parameters = {}
            for key, val in request.POST.items():
                if key.startswith('param_name_') and val.strip():
                    idx = key.replace('param_name_', '')
                    param_val = request.POST.get(f'param_value_{idx}', '').strip()
                    if param_val:
                        parameters[val.strip()] = param_val

            if not mobile or not template_id:
                messages.error(request, "شماره موبایل و شناسه الگو (TemplateId) الزامی هستند.")
            else:
                success, msg = send_pattern_sms(mobile, template_id, parameters, sender_user=request.user)
                if success:
                    messages.success(request, f"پیامک الگوی {template_id} با موفقیت ارسال شد.")
                else:
                    messages.error(request, f"خطا در ارسال الگو: {msg}")
            return redirect(f"{reverse('dashboard:sms')}?tab=pattern")

        elif action == 'send_bulk':
            title = request.POST.get('title', 'کمپین پیامکی').strip() or 'کمپین پیامکی'
            audience = request.POST.get('audience', 'all').strip()
            message = request.POST.get('message', '').strip()
            custom_numbers_raw = request.POST.get('custom_numbers', '').strip()

            phone_numbers = []
            if audience == 'all':
                phone_numbers = list(User.objects.filter(phone_number__isnull=False).exclude(phone_number='').values_list('phone_number', flat=True))
            elif audience == 'marketing':
                phone_numbers = list(User.objects.filter(phone_number__isnull=False, sms_marketing_subscribed=True).exclude(phone_number='').values_list('phone_number', flat=True))
            elif audience == 'buyers':
                phone_numbers = list(User.objects.filter(phone_number__isnull=False, orders__status__in=['paid', 'delivered', 'shipped']).distinct().values_list('phone_number', flat=True))
            elif audience == 'abandoned_carts':
                abandoned_cutoff = timezone.now() - timedelta(hours=24)
                phone_numbers = list(Cart.objects.filter(
                    items__isnull=False,
                    converted_order__isnull=True,
                    updated_at__lte=abandoned_cutoff,
                    user__isnull=False,
                    user__phone_number__isnull=False
                ).distinct().values_list('user__phone_number', flat=True))
            elif audience == 'custom':
                import re
                phone_numbers = re.split(r'[\r\n,]+', custom_numbers_raw)

            if not message:
                messages.error(request, "متن پیامک کمپین نمی‌تواند خالی باشد.")
            elif not phone_numbers:
                messages.error(request, "هیچ شماره مخاطبی برای گروه انتخاب‌شده یافت نشد.")
            else:
                res = send_bulk_campaign_sms(phone_numbers, message, title=title, audience=audience, sender_user=request.user)
                if res.get('status') == 1:
                    messages.success(request, f"کمپین با موفقیت ثبت شد و به {res.get('count', 0)} مخاطب ارسال گردید.")
                else:
                    messages.error(request, f"خطا در ثبت کمپین: {res.get('message')}")
            return redirect(f"{reverse('dashboard:sms')}?tab=bulk")

        elif action == 'create_template':
            title = request.POST.get('title', '').strip()
            template_type = request.POST.get('template_type', 'pattern').strip()
            template_id_val = to_int(request.POST.get('template_id', ''))
            text = request.POST.get('text', '').strip()
            parameters_hint = request.POST.get('parameters_hint', '').strip()

            if not title or not text:
                messages.error(request, "عنوان و متن الگو الزامی هستند.")
            else:
                SmsTemplate.objects.create(
                    title=title,
                    template_type=template_type,
                    template_id=template_id_val or None,
                    text=text,
                    parameters_hint=parameters_hint,
                )
                messages.success(request, "الگوی جدید با موفقیت ذخیره شد.")
            return redirect(f"{reverse('dashboard:sms')}?tab=templates")

        elif action == 'delete_template':
            template_pk = to_int(request.POST.get('template_pk', ''))
            SmsTemplate.objects.filter(pk=template_pk).delete()
            messages.success(request, "الگوی پیامک حذف گردید.")
            return redirect(f"{reverse('dashboard:sms')}?tab=templates")

    # آمار کلی و وضعیت پنل
    panel_status = get_panel_status()
    total_count = SmsLog.objects.count()
    sent_count = SmsLog.objects.filter(status='sent').count()
    failed_count = SmsLog.objects.filter(status='failed').count()
    simulated_count = SmsLog.objects.filter(status='simulated').count()
    otp_count = SmsLog.objects.filter(sms_type='otp').count()
    campaigns_count = SmsCampaign.objects.count()

    # اطلاعات مخاطبان
    all_users_count = User.objects.filter(phone_number__isnull=False).exclude(phone_number='').count()
    subscribers_count = User.objects.filter(phone_number__isnull=False, sms_marketing_subscribed=True).exclude(phone_number='').count()
    buyers_count = User.objects.filter(phone_number__isnull=False, orders__status__in=['paid', 'delivered', 'shipped']).distinct().count()
    abandoned_cutoff = timezone.now() - timedelta(hours=24)
    from cart.models import Cart
    abandoned_carts_count = Cart.objects.filter(
        items__isnull=False,
        converted_order__isnull=True,
        updated_at__lte=abandoned_cutoff,
        user__isnull=False,
        user__phone_number__isnull=False
    ).distinct().count()

    # لیست مشتریان برای انتخاب
    customers = (
        User.objects.filter(phone_number__isnull=False)
        .exclude(phone_number='')
        .order_by('-date_joined')[:60]
    )

    # قالب‌ها و کمپین‌ها
    templates_list = SmsTemplate.objects.all().order_by('-created_at')
    campaigns_list = SmsCampaign.objects.all().order_by('-created_at')[:15]

    # لاگ‌ها با فیلتر و جستجو
    logs_qs = SmsLog.objects.select_related('template', 'sender_user').all().order_by('-created_at')
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()
    search_query = request.GET.get('q', '').strip()

    if status_filter:
        logs_qs = logs_qs.filter(status=status_filter)
    if type_filter:
        logs_qs = logs_qs.filter(sms_type=type_filter)
    if search_query:
        logs_qs = logs_qs.filter(
            Q(recipient__icontains=search_query)
            | Q(message__icontains=search_query)
            | Q(error_message__icontains=search_query)
        )

    paginator = Paginator(logs_qs, 20)
    page_number = request.GET.get('page')
    logs_page = paginator.get_page(page_number)

    context = {
        'active_tab': active_tab,
        'panel_status': panel_status,
        'total_count': total_count,
        'sent_count': sent_count,
        'failed_count': failed_count,
        'simulated_count': simulated_count,
        'otp_count': otp_count,
        'campaigns_count': campaigns_count,
        'all_users_count': all_users_count,
        'subscribers_count': subscribers_count,
        'buyers_count': buyers_count,
        'abandoned_carts_count': abandoned_carts_count,
        'customers': customers,
        'templates_list': templates_list,
        'campaigns_list': campaigns_list,
        'logs_page': logs_page,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'search_query': search_query,
        'status_choices': SmsLog.STATUS_CHOICES,
        'sms_type_choices': SmsLog.SMS_TYPE_CHOICES,
        'querystring': _querystring_without_page(request),
    }
    return render(request, 'dashboard/sms.html', context)

