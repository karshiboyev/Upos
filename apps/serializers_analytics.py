# apps/serializers_analytics.py
from rest_framework import serializers

class TimePointSerializer(serializers.Serializer):
    ts = serializers.DateTimeField()
    revenue = serializers.FloatField()
    orders = serializers.IntegerField()

class ByHourSerializer(serializers.Serializer):
    hour = serializers.IntegerField(min_value=0, max_value=23)
    revenue = serializers.FloatField()
    orders = serializers.IntegerField()

class PaymentBreakdownSerializer(serializers.Serializer):
    method = serializers.CharField()
    amount = serializers.FloatField()

class ProductPerfSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    qty = serializers.FloatField()      # can be Decimal/Float depending on your units
    revenue = serializers.FloatField()
    category = serializers.CharField(required=False, allow_null=True)

class StaffPerfSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    orders = serializers.IntegerField()
    revenue = serializers.FloatField()

class TopCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    revenue = serializers.FloatField()
    orders = serializers.IntegerField()

class AnalyticsResponseSerializer(serializers.Serializer):
    timeseries = TimePointSerializer(many=True)
    byHour = ByHourSerializer(many=True, required=False)
    payments = PaymentBreakdownSerializer(many=True)
    topProducts = ProductPerfSerializer(many=True)
    topCategories = TopCategorySerializer(many=True)
    staff = StaffPerfSerializer(many=True)
    discounts = serializers.FloatField()
    refunds = serializers.FloatField()
    grossSales = serializers.FloatField()
    netSales = serializers.FloatField()
    orders = serializers.IntegerField()
