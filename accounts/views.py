from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import User, Address, Favorite
from products.models import Product


def to_persian_digits(val):
    if val is None:
        return ""
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(val).translate(trans)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home:index')

    if request.method == 'POST':
        login_id = request.POST.get('login_id', '').strip()
        password = request.POST.get('password', '')

        # Allow login by username OR phone_number
        user = authenticate(request, username=login_id, password=password)
        if not user:
            # Try phone_number lookup
            try:
                user_obj = User.objects.get(phone_number=login_id)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user:
            login(request, user)
            messages.success(request, f"خوش آمدید، {user.first_name or user.username} عزیز!")
            next_url = request.GET.get('next')
            return redirect(next_url or 'home:index')
        else:
            messages.error(request, "نام کاربری/شماره موبایل یا رمز عبور اشتباه است.")

    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home:index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if password != password_confirm:
            messages.error(request, "رمز عبور و تکرار آن یکسان نیستند.")
            return render(request, 'accounts/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "این نام کاربری قبلاً انتخاب شده است.")
            return render(request, 'accounts/register.html')

        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "این شماره موبایل قبلاً ثبت شده است.")
            return render(request, 'accounts/register.html')

        user = User.objects.create_user(
            username=username,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        login(request, user)
        messages.success(request, "حساب کاربری شما با موفقیت ساخته شد.")
        return redirect('home:index')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    messages.info(request, "با موفقیت از حساب کاربری خارج شدید.")
    return redirect('home:index')


@login_required
def profile_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()

            user = request.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            if phone_number and phone_number != user.phone_number:
                if User.objects.filter(phone_number=phone_number).exclude(pk=user.pk).exists():
                    messages.error(request, "این شماره موبایل قبلاً برای حساب دیگری ثبت شده است.")
                    return redirect('accounts:profile')
                user.phone_number = phone_number
            user.save()
            messages.success(request, "اطلاعات حساب کاربری شما با موفقیت به‌روزرسانی شد.")
            return redirect('accounts:profile')

        elif action == 'save_address':
            title = request.POST.get('title', 'خانه').strip()
            recipient_name = request.POST.get('recipient_name', '').strip()
            recipient_phone = request.POST.get('recipient_phone', '').strip()
            province = request.POST.get('province', '').strip()
            city = request.POST.get('city', '').strip()
            postal_address = request.POST.get('postal_address', '').strip()
            postal_code = request.POST.get('postal_code', '').strip()
            is_default = request.POST.get('is_default') == 'on'

            if is_default:
                request.user.addresses.update(is_default=False)

            Address.objects.create(
                user=request.user,
                title=title or "آدرس",
                recipient_name=recipient_name or request.user.get_full_name() or request.user.username,
                recipient_phone=recipient_phone or request.user.phone_number or "",
                province=province,
                city=city,
                postal_address=postal_address,
                postal_code=postal_code,
                is_default=is_default or not request.user.addresses.exists()
            )
            messages.success(request, "آدرس جدید با موفقیت ثبت شد.")
            return redirect('accounts:profile')

        elif action == 'delete_address':
            addr_id = request.POST.get('address_id')
            if addr_id:
                request.user.addresses.filter(id=addr_id).delete()
                messages.success(request, "آدرس با موفقیت حذف شد.")
            return redirect('accounts:profile')

        elif action == 'set_default_address':
            addr_id = request.POST.get('address_id')
            if addr_id:
                request.user.addresses.update(is_default=False)
                request.user.addresses.filter(id=addr_id).update(is_default=True)
                messages.success(request, "آدرس انتخابی به عنوان پیش‌فرض تنظیم شد.")
            return redirect('accounts:profile')

        elif action == 'remove_favorite':
            fav_id = request.POST.get('favorite_id')
            if fav_id:
                request.user.favorites.filter(id=fav_id).delete()
                messages.success(request, "کالا از لیست علاقه‌مندی‌ها حذف شد.")
            return redirect('accounts:profile')

    orders = request.user.orders.prefetch_related('items', 'items__product', 'items__product__images').all()
    addresses = request.user.addresses.all()
    default_address = addresses.filter(is_default=True).first() or addresses.first()

    total_orders_count = orders.count()
    # Real pending delivery: strictly orders currently in processing or transit (paid or shipped)
    pending_delivery_orders = orders.filter(status__in=['paid', 'shipped']).order_by('-created_at')
    pending_delivery_count = pending_delivery_orders.count()
    delivered_orders_count = orders.filter(status='delivered').count()

    # Active order in transit: only exists if customer has a real active paid/shipped order
    in_transit_order = pending_delivery_orders.first()
    in_transit_item = None
    stepper_step = 0
    if in_transit_order:
        in_transit_item = in_transit_order.items.select_related('product').prefetch_related('product__images').first()
        if in_transit_order.status == 'pending':
            stepper_step = 1
        elif in_transit_order.status == 'paid':
            stepper_step = 2
        elif in_transit_order.status == 'shipped':
            stepper_step = 3
        elif in_transit_order.status == 'delivered':
            stepper_step = 4

    # Real user favorites
    user_favorites = (
        request.user.favorites
        .select_related('product', 'product__category', 'product__brand')
        .prefetch_related('product__images')
        .all()
    )
    wishlist_count = user_favorites.count()
    latest_favorite_item = user_favorites.first()
    latest_favorite = latest_favorite_item.product if latest_favorite_item else None

    # Persian dates
    persian_date_str = ""
    persian_join_year = "۱۴۰۳"
    try:
        import jdatetime
        now_j = jdatetime.datetime.now()
        persian_date_str = to_persian_digits(now_j.strftime("%A، %d %B %Y"))

        if request.user.date_joined:
            user_j = jdatetime.datetime.fromgregorian(datetime=request.user.date_joined)
            persian_join_year = to_persian_digits(user_j.year)

        for o in orders:
            oj = jdatetime.datetime.fromgregorian(datetime=o.created_at)
            o.jalali_date = to_persian_digits(oj.strftime("%d %B %Y"))
    except Exception:
        persian_date_str = timezone.now().strftime("%Y/%m/%d")
        for o in orders:
            o.jalali_date = o.created_at.strftime("%Y/%m/%d")

    recent_orders = orders[:5]

    context = {
        'orders': orders,
        'recent_orders': recent_orders,
        'total_orders_count': total_orders_count,
        'pending_delivery_count': pending_delivery_count,
        'delivered_orders_count': delivered_orders_count,
        'wishlist_count': wishlist_count,
        'user_favorites': user_favorites,
        'in_transit_order': in_transit_order,
        'in_transit_item': in_transit_item,
        'stepper_step': stepper_step,
        'latest_favorite': latest_favorite,
        'addresses': addresses,
        'default_address': default_address,
        'persian_date_str': persian_date_str,
        'persian_join_year': persian_join_year,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def toggle_favorite_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    fav = Favorite.objects.filter(user=request.user, product=product).first()
    if fav:
        fav.delete()
        messages.info(request, f"«{product.title}» از لیست علاقه‌مندی‌ها حذف شد.")
    else:
        Favorite.objects.create(user=request.user, product=product)
        messages.success(request, f"«{product.title}» به لیست علاقه‌مندی‌ها اضافه شد.")

    next_url = request.META.get('HTTP_REFERER') or 'accounts:profile'
    return redirect(next_url)


@login_required
def add_address_ajax_view(request):
    """ثبت آدرس جدید به صورت ایجکس بدون رفرش یا خروج از صفحه تسویه حساب."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'درخواست نامعتبر است.'}, status=405)

    title = request.POST.get('title', 'خانه').strip()
    recipient_name = request.POST.get('recipient_name', '').strip()
    recipient_phone = request.POST.get('recipient_phone', '').strip()
    province = request.POST.get('province', '').strip()
    city = request.POST.get('city', '').strip()
    postal_address = request.POST.get('postal_address', '').strip()
    postal_code = request.POST.get('postal_code', '').strip()
    is_default = request.POST.get('is_default') in ['on', 'true', '1', True]

    if not all([recipient_name, recipient_phone, province, city, postal_address]):
        return JsonResponse({
            'status': 'error',
            'message': 'لطفاً تمام فیلدهای ستاره‌دار آدرس را تکمیل فرمایید.'
        }, status=400)

    # اگر کاربر قبلاً آدرسی نداشته باشد، اولین آدرس اجباراً پیش‌فرض می‌شود
    has_existing = request.user.addresses.exists()
    if is_default or not has_existing:
        request.user.addresses.update(is_default=False)
        is_default = True

    addr = Address.objects.create(
        user=request.user,
        title=title or "آدرس",
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        province=province,
        city=city,
        postal_address=postal_address,
        postal_code=postal_code,
        is_default=is_default,
    )

    return JsonResponse({
        'status': 'ok',
        'message': 'آدرس جدید با موفقیت ثبت شد.',
        'address': {
            'id': addr.id,
            'title': addr.title,
            'recipient_name': addr.recipient_name,
            'recipient_phone': addr.recipient_phone,
            'province': addr.province,
            'city': addr.city,
            'postal_address': addr.postal_address,
            'postal_code': addr.postal_code,
            'is_default': addr.is_default,
        }
    })

