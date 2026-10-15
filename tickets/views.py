"""نماهای سمت مشتری برای تیکت‌های پشتیبانی (چت)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Ticket, TicketMessage


@login_required
def ticket_list_view(request):
    """فهرست تیکت‌های کاربر جاری."""
    tickets = (
        Ticket.objects.filter(user=request.user)
        .select_related('assigned_to')
        .order_by('-last_message_at')
    )
    status_filter = request.GET.get('status', '').strip()
    if status_filter in dict(Ticket.STATUS_CHOICES):
        tickets = tickets.filter(status=status_filter)

    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'status_choices': Ticket.STATUS_CHOICES,
        'category_choices': Ticket.CATEGORY_CHOICES,
        'open_count': Ticket.objects.filter(user=request.user).exclude(status=Ticket.STATUS_CLOSED).count(),
    }
    return render(request, 'tickets/list.html', context)


@login_required
@require_POST
def ticket_create_view(request):
    """ایجاد تیکت جدید + اولین پیام."""
    subject = request.POST.get('subject', '').strip()
    body = request.POST.get('body', '').strip()
    category = request.POST.get('category', Ticket.CATEGORY_OTHER)
    priority = request.POST.get('priority', Ticket.PRIORITY_NORMAL)
    order_number = request.POST.get('order_number', '').strip()

    if not subject or not body:
        messages.error(request, "عنوان و متن پیام تیکت الزامی است.")
        # بازگشت به فرم ثبت تیکت؛ مسیر tickets:create فقط POST می‌پذیرد و
        # ریدایرکت به آن به خطای 405 منتهی می‌شد.
        return redirect('tickets:create_form')

    if category not in dict(Ticket.CATEGORY_CHOICES):
        category = Ticket.CATEGORY_OTHER
    if priority not in dict(Ticket.PRIORITY_CHOICES):
        priority = Ticket.PRIORITY_NORMAL

    ticket = Ticket.objects.create(
        user=request.user,
        subject=subject[:200],
        category=category,
        priority=priority,
        order_number=order_number[:30],
        last_message_at=timezone.now(),
    )
    TicketMessage.objects.create(ticket=ticket, sender=request.user, body=body)
    messages.success(request, f"تیکت {ticket.ticket_number} ثبت شد؛ پشتیبانی به‌زودی پاسخ می‌دهد.")
    return redirect('tickets:detail', pk=ticket.pk)


@login_required
def ticket_new_view(request):
    """صفحه فرم تیکت جدید."""
    context = {
        'category_choices': Ticket.CATEGORY_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
    }
    return render(request, 'tickets/create.html', context)


@login_required
def ticket_detail_view(request, pk):
    """گفتگوی تیکت (چت) بین مشتری و پشتیبانی."""
    ticket = get_object_or_404(Ticket.objects.select_related('assigned_to'), pk=pk, user=request.user)
    if ticket.customer_unread:
        ticket.customer_unread = False
        ticket.save(update_fields=['customer_unread'])

    context = {
        'ticket': ticket,
        'messages_list': ticket.messages.select_related('sender'),
    }
    return render(request, 'tickets/detail.html', context)


@login_required
def ticket_messages_partial_view(request, pk):
    """بخشی از پیام‌ها برای به‌روزرسانی خودکار (polling) با HTMX."""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    if ticket.customer_unread:
        ticket.customer_unread = False
        ticket.save(update_fields=['customer_unread'])
    return render(request, 'tickets/_messages.html', {
        'ticket': ticket,
        'messages_list': ticket.messages.select_related('sender'),
    })


@login_required
@require_POST
def ticket_reply_view(request, pk):
    """ارسال پیام جدید توسط مشتری."""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    body = request.POST.get('body', '').strip()

    if ticket.is_closed:
        messages.error(request, "این تیکت بسته شده است و امکان ارسال پیام ندارد.")
        return redirect('tickets:detail', pk=ticket.pk)

    if not body:
        messages.error(request, "متن پیام خالی است.")
        return redirect('tickets:detail', pk=ticket.pk)

    TicketMessage.objects.create(ticket=ticket, sender=request.user, body=body)
    ticket.last_message_at = timezone.now()
    ticket.staff_unread = True
    if ticket.status in (Ticket.STATUS_ANSWERED, Ticket.STATUS_CLOSED):
        ticket.status = Ticket.STATUS_IN_PROGRESS
    ticket.save(update_fields=['last_message_at', 'staff_unread', 'status', 'updated_at'])
    return redirect('tickets:detail', pk=ticket.pk)


@login_required
@require_POST
def ticket_close_view(request, pk):
    """بستن تیکت توسط مشتری."""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    if not ticket.is_closed:
        ticket.close()
        messages.success(request, "تیکت بسته شد. در صورت نیاز می‌توانید تیکت جدیدی ثبت کنید.")
    return redirect('tickets:detail', pk=ticket.pk)
