from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from home.models import SiteSetting
from .models import User, Address, Favorite, OTPCode
from .services import normalize_phone, send_sms, generate_otp, verify_otp
from products.models import Product


def to_persian_digits(val):
    if val is None:
        return ""
    trans = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(val).translate(trans)


def check_phone_view(request):
    """بررسی وضعیت ثبت‌نام شماره همراه (برای اعتبارسنجی آنی در لاگین و تسویه حساب)."""
    raw_phone = request.GET.get('phone') or request.POST.get('phone', '')
    phone = normalize_phone(raw_phone)
    if not phone or len(phone) < 10:
        return JsonResponse({'status': 'invalid', 'exists': False, 'message': 'شماره نامعتبر است'})
    user = User.objects.filter(phone_number=phone).first() or User.objects.filter(username=phone).first()
    if user:
        full_name = f"{user.first_name} {user.last_name}".strip() or user.username
        return JsonResponse({
            'status': 'ok',
            'phone': phone,
            'exists': True,
            'name': full_name,
            'full_name': full_name,
        })
    return JsonResponse({'status': 'ok', 'phone': phone, 'exists': False})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home:index')

    site_settings = SiteSetting.get_settings()
    login_method = getattr(site_settings, 'login_method', 'otp')
    next_url = request.GET.get('next') or request.POST.get('next') or 'home:index'

    if request.method == 'POST':
        login_input = (request.POST.get('phone_number') or request.POST.get('login_id') or '').strip()
        norm_phone = normalize_phone(login_input)
        is_phone = bool(norm_phone and norm_phone.startswith('09') and len(norm_phone) == 11)

        # Mode: OTP
        if login_method == 'otp' and is_phone:
            code, _ = generate_otp(norm_phone)
            request.session['pending_auth_phone'] = norm_phone
            request.session['auth_next_url'] = next_url
            messages.success(request, f"کد تأیید ۶ رقمی به شماره {norm_phone} پیامک شد.")
            return redirect('accounts:verify_otp')

        # Mode: Password (or non-phone username fallback e.g. 'admin')
        password = request.POST.get('password', '').strip()

        if is_phone:
            user_obj = User.objects.filter(phone_number=norm_phone).first() or User.objects.filter(username=norm_phone).first()
            if user_obj:
                if not password:
                    messages.error(request, "لطفاً رمز عبور خود را وارد نمایید.")
                    return render(request, 'accounts/login.html', {
                        'login_method': login_method,
                        'phone_number': norm_phone,
                        'user_exists': True,
                        'next_url': next_url,
                    })
                user = authenticate(request, username=user_obj.username, password=password)
                if user:
                    login(request, user)
                    messages.success(request, f"خوش آمدید، {user.first_name or user.username} عزیز!")
                    return redirect(next_url)
                else:
                    messages.error(request, "رمز عبور وارد شده اشتباه است.")
                    return render(request, 'accounts/login.html', {
                        'login_method': login_method,
                        'phone_number': norm_phone,
                        'user_exists': True,
                        'next_url': next_url,
                    })
            else:
                # User not registered yet
                if not password:
                    messages.info(request, "این شماره قبلاً ثبت‌نام نشده است. لطفاً یک رمز عبور برای حساب خود تعیین فرمایید تا ثبت‌نام شما کامل شود.")
                    return render(request, 'accounts/login.html', {
                        'login_method': login_method,
                        'phone_number': norm_phone,
                        'user_exists': False,
                        'is_new_user': True,
                        'next_url': next_url,
                    })
                if len(password) < 4:
                    messages.error(request, "رمز عبور باید حداقل ۴ نویسه (کاراکتر) باشد.")
                    return render(request, 'accounts/login.html', {
                        'login_method': login_method,
                        'phone_number': norm_phone,
                        'user_exists': False,
                        'is_new_user': True,
                        'next_url': next_url,
                    })

                new_user = User.objects.create_user(
                    username=norm_phone,
                    phone_number=norm_phone,
                    password=password,
                    is_verified=True,
                )
                login(request, new_user)
                send_sms(norm_phone, f"به دیجی تل خوش آمدید!\nحساب کاربری شما با شماره {norm_phone} با موفقیت ساخته شد.")
                messages.success(request, "حساب کاربری شما با موفقیت ساخته شد و وارد شدید.")
                return redirect(next_url)
        else:
            # Fallback for standard username e.g. admin
            if not login_input:
                messages.error(request, "لطفاً شماره تلفن همراه معتبر وارد نمایید.")
                return render(request, 'accounts/login.html', {'login_method': login_method, 'next_url': next_url})

            user = authenticate(request, username=login_input, password=password)
            if user:
                login(request, user)
                messages.success(request, f"خوش آمدید، {user.first_name or user.username} عزیز!")
                return redirect(next_url)
            else:
                messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")

    return render(request, 'accounts/login.html', {
        'login_method': login_method,
        'next_url': next_url,
    })


def verify_otp_view(request):
    """صفحه دریافت و اعتبارسنجی خودکار کد یکبار مصرف ۶ رقمی."""
    if request.user.is_authenticated:
        return redirect('home:index')

    phone = request.session.get('pending_auth_phone') or request.GET.get('phone', '')
    phone = normalize_phone(phone)
    if not phone:
        messages.warning(request, "لطفاً ابتدا شماره همراه خود را وارد فرمایید.")
        return redirect('accounts:login')

    next_url = request.session.get('auth_next_url') or request.GET.get('next') or 'home:index'

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code:
            digits = [request.POST.get(f'digit_{i}', '').strip() for i in range(1, 7)]
            code = ''.join(digits)

        code = normalize_phone(code)

        if not code or len(code) != 6:
            messages.error(request, "کد تأیید باید دقیقاً ۶ رقم باشد.")
            return render(request, 'accounts/verify_otp.html', {'phone': phone, 'next_url': next_url})

        if verify_otp(phone, code):
            user = User.objects.filter(phone_number=phone).first() or User.objects.filter(username=phone).first()
            if user:
                login(request, user)
                messages.success(request, f"خوش آمدید، {user.first_name or user.username} عزیز!")
            else:
                user = User.objects.create_user(
                    username=phone,
                    phone_number=phone,
                    is_verified=True,
                )
                login(request, user)
                send_sms(phone, f"به دیجی تل خوش آمدید!\nحساب کاربری شما با شماره {phone} با موفقیت ایجاد شد.")
                messages.success(request, "ثبت‌نام شما با موفقیت انجام شد و به حساب خود وارد شدید.")

            if 'pending_auth_phone' in request.session:
                del request.session['pending_auth_phone']
            if 'auth_next_url' in request.session:
                del request.session['auth_next_url']

            return redirect(next_url)
        else:
            messages.error(request, "کد تأیید وارد شده نامعتبر است یا منقضی شده است.")

    from django.conf import settings
    recent_otp = None
    if settings.DEBUG:
        recent_otp = OTPCode.objects.filter(phone_number=phone, is_used=False).order_by('-created_at').first()

    return render(request, 'accounts/verify_otp.html', {
        'phone': phone,
        'next_url': next_url,
        'dev_code': recent_otp.code if recent_otp else None,
    })


def resend_otp_view(request):
    """ارسال مجدد کد یکبار مصرف به شماره در انتظار."""
    if request.user.is_authenticated:
        return redirect('home:index')

    phone = request.session.get('pending_auth_phone') or request.GET.get('phone') or request.POST.get('phone', '')
    phone = normalize_phone(phone)
    if not phone:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'شماره همراه یافت نشد.'}, status=400)
        messages.error(request, "شماره همراه یافت نشد.")
        return redirect('accounts:login')

    code, _ = generate_otp(phone)
    msg = f"کد تأیید جدید برای شماره {phone} پیامک شد."
    messages.success(request, msg)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'message': msg, 'code': code})

    return redirect('accounts:verify_otp')



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

        elif action == 'update_supplementary':
            user = request.user
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            national_code = request.POST.get('national_code', '').strip()
            birth_date_str = request.POST.get('birth_date', '').strip()
            gender = request.POST.get('gender', '').strip()
            job_title = request.POST.get('job_title', '').strip()
            sheba_number = request.POST.get('sheba_number', '').strip()
            card_number = request.POST.get('card_number', '').strip()
            sms_marketing = request.POST.get('sms_marketing') == 'on'
            email_marketing = request.POST.get('email_marketing') == 'on'

            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name

            # Parse birth date (supports Jalali 1375/05/20 or YYYY-MM-DD)
            parsed_birth_date = None
            if birth_date_str:
                clean_date = birth_date_str.replace('-', '/').strip()
                for fa, en in zip('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'):
                    clean_date = clean_date.replace(fa, en)
                parts = clean_date.split('/')
                if len(parts) == 3:
                    try:
                        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                        if 1250 <= y <= 1450:
                            import jdatetime
                            jd = jdatetime.date(y, m, d)
                            parsed_birth_date = jd.togregorian()
                        elif 1920 <= y <= 2050:
                            import datetime
                            parsed_birth_date = datetime.date(y, m, d)
                    except Exception:
                        pass

            user.national_code = national_code
            if parsed_birth_date:
                user.birth_date = parsed_birth_date
            elif not birth_date_str:
                user.birth_date = None

            if gender in ['male', 'female', 'other']:
                user.gender = gender
            elif not gender:
                user.gender = ''

            user.job_title = job_title

            if sheba_number:
                sheba_clean = sheba_number.upper().replace(' ', '')
                if not sheba_clean.startswith('IR') and sheba_clean.isdigit():
                    sheba_clean = f"IR{sheba_clean}"
                user.sheba_number = sheba_clean[:26]
            else:
                user.sheba_number = ""

            user.card_number = card_number.replace('-', '').replace(' ', '')[:19]
            user.sms_marketing_subscribed = sms_marketing
            user.email_marketing_subscribed = email_marketing
            user.save()

            messages.success(request, "اطلاعات تکمیلی و بازاریابی حساب کاربری شما با موفقیت ذخیره شد.")
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

    # User reviews (نظرات ثبت شده کاربر)
    reviews = (
        request.user.product_reviews
        .select_related('product', 'product__category')
        .prefetch_related('product__images')
        .order_by('-created_at')
        .all()
    )
    reviews_count = reviews.count()

    # User tickets (تیکت‌های پشتیبانی کاربر)
    tickets = (
        request.user.tickets
        .prefetch_related('messages')
        .order_by('-created_at')
        .all()
    )
    tickets_count = tickets.count()

    # Persian dates for reviews and tickets
    try:
        import jdatetime
        for r in reviews:
            rj = jdatetime.datetime.fromgregorian(datetime=r.created_at)
            r.jalali_date = to_persian_digits(rj.strftime("%d %B %Y"))
        for t in tickets:
            tj = jdatetime.datetime.fromgregorian(datetime=t.created_at)
            t.jalali_date = to_persian_digits(tj.strftime("%d %B %Y - %H:%M"))
    except Exception:
        for r in reviews:
            r.jalali_date = r.created_at.strftime("%Y/%m/%d")
        for t in tickets:
            t.jalali_date = t.created_at.strftime("%Y/%m/%d")

    missing_fields = request.user.missing_fields_list
    is_profile_incomplete = len(missing_fields) > 0
    profile_completion_percentage = request.user.profile_completion_percentage

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
        'reviews': reviews,
        'reviews_count': reviews_count,
        'tickets': tickets,
        'tickets_count': tickets_count,
        'persian_date_str': persian_date_str,
        'persian_join_year': persian_join_year,
        'missing_fields': missing_fields,
        'is_profile_incomplete': is_profile_incomplete,
        'profile_completion_percentage': profile_completion_percentage,
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


def deposit_view(request):
    """صفحه و فرم واریز وجه با قابلیت تکمیل خودکار اطلاعات کاربران لاگین‌شده و محاسبه حروف تومان."""
    import random
    is_authenticated = request.user.is_authenticated
    user = request.user if is_authenticated else None

    # استخراج مقادیر پیش‌فرض
    full_name = ""
    phone_number = ""
    if is_authenticated:
        full_name = (f"{user.first_name} {user.last_name}".strip()) or user.username
        phone_number = user.phone_number or getattr(user, 'username', '')

    context = {
        'full_name': full_name,
        'phone_number': phone_number,
        'is_readonly': is_authenticated,
        'success': False,
        'tracking_code': None,
        'deposit_amount': None,
    }

    if request.method == 'POST':
        # دریافت اطلاعات
        if is_authenticated:
            posted_name = full_name
            posted_phone = phone_number
        else:
            posted_name = request.POST.get('full_name', '').strip()
            posted_phone = request.POST.get('phone_number', '').strip()

        amount_raw = request.POST.get('amount', '').strip()

        # تمیزکاری مبلغ: حذف کاما، فاصله و تبدیل ارقام فارسی به انگلیسی
        clean_amount = amount_raw.replace(',', '').replace('،', '').replace(' ', '')
        for fa, en in zip('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'):
            clean_amount = clean_amount.replace(fa, en)

        errors = []
        if not posted_name:
            errors.append('لطفاً نام و نام خانوادگی را وارد فرمایید.')
        if not posted_phone:
            errors.append('لطفاً شماره تماس را وارد فرمایید.')

        try:
            amount_val = int(clean_amount)
            if amount_val < 1000:
                errors.append('حداقل مبلغ واریزی ۱,۰۰۰ تومان می‌باشد.')
        except (ValueError, TypeError):
            errors.append('مبلغ واریزی نامعتبر است.')
            amount_val = None

        if errors:
            for err in errors:
                messages.error(request, err)
            context['full_name'] = posted_name
            context['phone_number'] = posted_phone
            context['amount_value'] = amount_raw
            return render(request, 'accounts/deposit.html', context)

        # ساخت کد رهگیری و نمایش فیدبک موفقیت
        tracking_code = f"DEP-{random.randint(100000, 999999)}"
        context['success'] = True
        context['tracking_code'] = tracking_code
        context['deposit_amount'] = amount_val
        context['full_name'] = posted_name
        context['phone_number'] = posted_phone
        messages.success(request, f'درخواست واریز مبلغ {amount_val:,} تومان با موفقیت ثبت شد.')
        return render(request, 'accounts/deposit.html', context)

    return render(request, 'accounts/deposit.html', context)


