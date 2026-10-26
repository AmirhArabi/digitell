from django.contrib import admin
from .models import SmsTemplate, SmsLog, SmsCampaign


@admin.register(SmsTemplate)
class SmsTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'template_type', 'template_id', 'is_active', 'created_at')
    list_filter = ('template_type', 'is_active', 'created_at')
    search_fields = ('title', 'text', 'template_id', 'parameters_hint')


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sms_type', 'status', 'cost', 'message_id', 'created_at')
    list_filter = ('sms_type', 'status', 'created_at')
    search_fields = ('recipient', 'message', 'error_message', 'message_id')
    readonly_fields = ('recipient', 'message', 'sms_type', 'status', 'template', 'pattern_template_id', 'cost', 'message_id', 'pack_id', 'response_data', 'error_message', 'sender_user', 'created_at')


@admin.register(SmsCampaign)
class SmsCampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'total_recipients', 'successful_count', 'status', 'created_at')
    list_filter = ('audience', 'status', 'created_at')
    search_fields = ('title', 'message')
