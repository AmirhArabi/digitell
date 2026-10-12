from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User


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
    orders = request.user.orders.prefetch_related('items').all()
    addresses = request.user.addresses.all()

    context = {
        'orders': orders,
        'addresses': addresses,
    }
    return render(request, 'accounts/profile.html', context)
