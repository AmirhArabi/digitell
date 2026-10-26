from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("اطلاعات تکمیلی", {"fields": (
            "phone_number",
            "avatar",
            "is_verified",
            "national_code",
            "birth_date",
            "gender",
            "job_title",
            "sheba_number",
            "card_number",
            "sms_marketing_subscribed",
            "email_marketing_subscribed",
        )}),
    )
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "is_staff",
        "is_active",
    )
    search_fields = (
        "username",
        "email",
        "phone_number",
        "first_name",
        "last_name",
    )



from .models import CustomerProfile, LoyaltyPoint, Reward, CustomerActivityLog

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'birth_date', 'segment')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('user',)

@admin.register(LoyaltyPoint)
class LoyaltyPointAdmin(admin.ModelAdmin):
    list_display = ('profile', 'amount', 'earned_at', 'source')
    list_filter = ('earned_at', 'source')
    search_fields = ('profile__user__username', 'profile__user__email')

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'required_points', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name',)

@admin.register(CustomerActivityLog)
class CustomerActivityLogAdmin(admin.ModelAdmin):
    list_display = ('profile', 'activity_type', 'performed_at')
    list_filter = ('activity_type', 'performed_at')
    search_fields = ('profile__user__username', 'activity_type')

admin.site.register(User, UserAdmin)
