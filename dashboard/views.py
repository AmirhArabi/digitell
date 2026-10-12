from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils.text import slugify
from products.models import Product, Category, Brand
from orders.models import Order
from accounts.models import User
from home.models import SiteSetting


@staff_member_required(login_url='accounts:login')
def overview_view(request):
    total_sales = Order.objects.filter(payment_status='successful').aggregate(s=Sum('final_amount'))['s'] or 0
    orders_count = Order.objects.count()
    products_count = Product.objects.count()
    customers_count = User.objects.count()

    recent_orders = Order.objects.select_related('user').prefetch_related('items').all()[:6]
    low_stock_products = Product.objects.filter(stock_qty__lte=5, is_active=True)[:5]

    context = {
        'total_sales': f"{total_sales:,}",
        'orders_count': orders_count,
        'products_count': products_count,
        'customers_count': customers_count,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'dashboard/overview.html', context)


@staff_member_required(login_url='accounts:login')
def product_list_view(request):
    products = Product.objects.select_related('category', 'brand').all().order_by('-created_at')
    q = request.GET.get('q')
    if q:
        products = products.filter(title__icontains=q)

    context = {
        'products': products,
        'search_query': q,
    }
    return render(request, 'dashboard/products.html', context)


@staff_member_required(login_url='accounts:login')
def product_create_view(request):
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        sku = request.POST.get('sku')
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        price = request.POST.get('price')
        compare_at_price = request.POST.get('compare_at_price')
        stock_qty = request.POST.get('stock_qty', 10)
        short_desc = request.POST.get('short_description', '')
        desc = request.POST.get('description', '')
        warranty = request.POST.get('warranty', '۱۸ ماه گارانتی شرکتی')
        is_featured = 'is_featured' in request.POST
        is_special_offer = 'is_special_offer' in request.POST

        category = get_object_or_404(Category, pk=category_id)
        brand = Brand.objects.filter(pk=brand_id).first() if brand_id else None

        slug = slugify(title, allow_unicode=True) or f"prod-{sku}"

        product = Product.objects.create(
            title=title,
            slug=slug,
            sku=sku,
            category=category,
            brand=brand,
            price=int(price),
            compare_at_price=int(compare_at_price) if compare_at_price else None,
            stock_qty=int(stock_qty),
            short_description=short_desc,
            description=desc,
            warranty=warranty,
            is_featured=is_featured,
            is_special_offer=is_special_offer,
        )
        messages.success(request, f"محصول «{product.title}» با موفقیت اضافه شد.")
        return redirect('dashboard:products')

    return render(request, 'dashboard/product_form.html', {
        'categories': categories,
        'brands': brands,
    })


@staff_member_required(login_url='accounts:login')
def product_edit_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    brands = Brand.objects.all()

    if request.method == 'POST':
        product.title = request.POST.get('title')
        product.sku = request.POST.get('sku')
        product.category = get_object_or_404(Category, pk=request.POST.get('category'))
        brand_id = request.POST.get('brand')
        product.brand = Brand.objects.filter(pk=brand_id).first() if brand_id else None
        product.price = int(request.POST.get('price'))
        compare_price = request.POST.get('compare_at_price')
        product.compare_at_price = int(compare_price) if compare_price else None
        product.stock_qty = int(request.POST.get('stock_qty', 10))
        product.short_description = request.POST.get('short_description', '')
        product.description = request.POST.get('description', '')
        product.warranty = request.POST.get('warranty', '')
        product.is_featured = 'is_featured' in request.POST
        product.is_special_offer = 'is_special_offer' in request.POST
        product.save()

        messages.success(request, "تغییرات محصول با موفقیت ذخیره شد.")
        return redirect('dashboard:products')

    return render(request, 'dashboard/product_form.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
    })


@staff_member_required(login_url='accounts:login')
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "محصول با موفقیت حذف شد.")
        return redirect('dashboard:products')
    return redirect('dashboard:products')


@staff_member_required(login_url='accounts:login')
def order_list_view(request):
    orders = Order.objects.select_related('user').all().order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }
    return render(request, 'dashboard/orders.html', context)


@staff_member_required(login_url='accounts:login')
def order_update_status_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f"وضعیت سفارش {order.order_number} بروزرسانی شد.")
    return redirect('dashboard:orders')


@staff_member_required(login_url='accounts:login')
def settings_view(request):
    settings = SiteSetting.get_settings()
    if request.method == 'POST':
        settings.store_name = request.POST.get('store_name')
        settings.slogan = request.POST.get('slogan')
        settings.phone = request.POST.get('phone')
        settings.email = request.POST.get('email')
        settings.address = request.POST.get('address')
        settings.working_hours = request.POST.get('working_hours')
        settings.save()
        messages.success(request, "تنظیمات فروشگاه ذخیره شد.")
        return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html', {'settings': settings})
