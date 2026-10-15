from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    # نمای کلی و گزارش‌ها
    path('', views.overview_view, name='overview'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/', views.reports_export_view, name='reports_export'),
    path('reports/export/products/', views.reports_products_export_view, name='reports_products_export'),
    path('reports/export/inventory/', views.reports_inventory_export_view, name='reports_inventory_export'),

    # محصولات
    path('products/', views.product_list_view, name='products'),
    path('products/create/', views.product_form_view, name='product_create'),
    path('products/<int:pk>/edit/', views.product_form_view, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete_view, name='product_delete'),
    path('products/<int:pk>/toggle/<str:field>/', views.product_toggle_view, name='product_toggle'),
    path('products/bulk/', views.product_bulk_view, name='product_bulk'),
    path('products/images/<int:pk>/delete/', views.product_image_delete_view, name='product_image_delete'),
    path('products/images/<int:pk>/primary/', views.product_image_primary_view, name='product_image_primary'),

    # انبار
    path('inventory/', views.inventory_view, name='inventory'),

    # دسته‌بندی‌ها
    path('categories/', views.category_list_view, name='categories'),
    path('categories/create/', views.category_form_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_form_view, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),
    path('categories/<int:pk>/toggle/', views.category_toggle_view, name='category_toggle'),

    # برندها
    path('brands/', views.brand_list_view, name='brands'),
    path('brands/create/', views.brand_form_view, name='brand_create'),
    path('brands/<int:pk>/edit/', views.brand_form_view, name='brand_edit'),
    path('brands/<int:pk>/delete/', views.brand_delete_view, name='brand_delete'),

    # ویژگی‌ها
    path('attributes/', views.attribute_list_view, name='attributes'),
    path('attributes/<int:pk>/edit/', views.attribute_form_view, name='attribute_edit'),
    path('attributes/<int:pk>/delete/', views.attribute_delete_view, name='attribute_delete'),

    # بنرها
    path('banners/', views.banner_list_view, name='banners'),
    path('banners/create/', views.banner_form_view, name='banner_create'),
    path('banners/<int:pk>/edit/', views.banner_form_view, name='banner_edit'),
    path('banners/<int:pk>/delete/', views.banner_delete_view, name='banner_delete'),
    path('banners/<int:pk>/toggle/', views.banner_toggle_view, name='banner_toggle'),
    path('banners/<int:pk>/move/<str:direction>/', views.banner_move_view, name='banner_move'),

    # سفارش‌ها
    path('orders/', views.order_list_view, name='orders'),
    path('orders/export/', views.orders_export_view, name='orders_export'),
    path('orders/<int:pk>/', views.order_detail_view, name='order_detail'),
    path('orders/<int:pk>/update/', views.order_update_view, name='order_update'),
    path('orders/<int:pk>/status/', views.order_status_view, name='order_status'),

    # مشتریان
    path('customers/', views.customer_list_view, name='customers'),
    path('customers/<int:pk>/', views.customer_detail_view, name='customer_detail'),
    path('customers/<int:pk>/toggle-staff/', views.customer_toggle_staff_view, name='customer_toggle_staff'),

    # تیکت‌های پشتیبانی
    path('tickets/', views.ticket_list_view, name='tickets'),
    path('tickets/<int:pk>/', views.ticket_detail_view, name='ticket_detail'),
    path('tickets/<int:pk>/messages/', views.ticket_messages_partial_view, name='ticket_messages'),

    # کدهای تخفیف
    path('coupons/', views.coupon_list_view, name='coupons'),
    path('coupons/create/', views.coupon_form_view, name='coupon_create'),
    path('coupons/<int:pk>/edit/', views.coupon_form_view, name='coupon_edit'),
    path('coupons/<int:pk>/delete/', views.coupon_delete_view, name='coupon_delete'),
    path('coupons/<int:pk>/toggle/', views.coupon_toggle_view, name='coupon_toggle'),

    # مقالات
    path('posts/', views.post_list_view, name='posts'),
    path('posts/create/', views.post_form_view, name='post_create'),
    path('posts/<int:pk>/edit/', views.post_form_view, name='post_edit'),
    path('posts/<int:pk>/delete/', views.post_delete_view, name='post_delete'),
    path('posts/<int:pk>/toggle/', views.post_toggle_view, name='post_toggle'),
    path('posts/categories/save/', views.blog_category_save_view, name='blog_category_create'),
    path('posts/categories/<int:pk>/save/', views.blog_category_save_view, name='blog_category_edit'),
    path('posts/categories/<int:pk>/delete/', views.blog_category_delete_view, name='blog_category_delete'),

    # تنظیمات
    path('settings/', views.settings_view, name='settings'),
]
