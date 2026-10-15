from django.contrib import admin

from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('sender', 'sender_name', 'is_staff_message', 'body', 'created_at')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'user', 'category', 'status', 'priority', 'last_message_at')
    list_filter = ('status', 'category', 'priority')
    search_fields = ('ticket_number', 'subject', 'user__username', 'user__phone_number', 'order_number')
    inlines = (TicketMessageInline,)


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'sender_name', 'is_staff_message', 'created_at')
    list_filter = ('is_staff_message',)
    search_fields = ('body', 'ticket__ticket_number')
