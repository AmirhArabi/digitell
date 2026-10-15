from .models import Ticket


def ticket_badge_processor(request):
    """نشان تعداد تیکت‌های باز برای منوی پنل مدیریت."""
    open_ticket_count = 0
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and user.is_staff:
        open_ticket_count = Ticket.objects.exclude(status=Ticket.STATUS_CLOSED).count()
    return {'open_ticket_count': open_ticket_count}
