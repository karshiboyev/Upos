from django.contrib import admin
from .models import *

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# Har bir model uchun faqat ko‘rish rejimida ro‘yxatdan o‘tkazamiz:
@admin.register(User)
class UserAdmin(ReadOnlyAdmin):
    list_display = ('phone_number', 'full_name', 'is_active', 'is_shop', 'balance', 'created_at')

@admin.register(Shop)
class ShopAdmin(ReadOnlyAdmin):
    list_display = ('name', 'user_id', 'location', 'is_active', 'created_at')

@admin.register(Product)
class ProductAdmin(ReadOnlyAdmin):
    list_display = ('name', 'price', 'unit', 'barcode', 'quantity', 'stock', 'shop', 'is_active')

@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'user', 'shop', 'created_at')

@admin.register(Customer)
class CustomerAdmin(ReadOnlyAdmin):
    list_display = ('full_name', 'phone_number', 'total_debt', 'shop', 'created_at')

@admin.register(Transaction)
class TransactionAdmin(ReadOnlyAdmin):
    list_display = ('shop', 'user', 'customer', 'total_price', 'profit', 'payment_type', 'status', 'created_at')

@admin.register(TransactionItem)
class TransactionItemAdmin(ReadOnlyAdmin):
    list_display = ('transaction', 'product', 'quantity', 'price_at_sale', 'discount')

@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ('user', 'amount', 'method', 'payment_status', 'paid_until', 'created_at')
