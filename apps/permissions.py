from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated


class IsActiveUser(IsAuthenticated):
    """Faqat aktiv foydalanuvchilarga ruxsat beradi"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_active