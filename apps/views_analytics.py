# apps/views_analytics.py
from __future__ import annotations

from datetime import date, datetime, timedelta, time as dt_time
from decimal import Decimal
from typing import Literal, List, Dict

from django.db.models import (
    Sum,
    Count,
    F,
    Value as V,
    IntegerField,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import (
    TruncDay,
    TruncWeek,
    TruncMonth,
    TruncHour,
    Coalesce,
)

# Timezone: Asia/Tashkent
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    UZ_TZ = ZoneInfo("Asia/Tashkent")
except Exception:  # pragma: no cover
    import pytz
    UZ_TZ = pytz.timezone("Asia/Tashkent")

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.models import Transaction, TransactionItem, User


# =========================
# Response Serializers (for docs + optional runtime validation)
# =========================
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
    qty = serializers.FloatField()        # can be float if you sell by weight
    revenue = serializers.FloatField()


class AnalyticsResponseSerializer(serializers.Serializer):
    timeseries = TimePointSerializer(many=True)
    byHour = ByHourSerializer(many=True, required=False)
    payments = PaymentBreakdownSerializer(many=True)
    topProducts = ProductPerfSerializer(many=True)
    discounts = serializers.FloatField()
    refunds = serializers.FloatField()
    grossSales = serializers.FloatField()
    netSales = serializers.FloatField()
    orders = serializers.IntegerField()
    # extra fields for business accuracy
    profit = serializers.FloatField()
    costOfGoods = serializers.FloatField()


# =========================
# Helpers & constants
# =========================
GROUPERS: dict[str, type[TruncDay] | type[TruncWeek] | type[TruncMonth]] = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}

DECIMAL_F = DecimalField(max_digits=18, decimal_places=2)
DEC_ZERO = V(Decimal("0.00"), output_field=DECIMAL_F)
INT_ZERO = V(0, output_field=IntegerField())


def local_day_bounds(d: date):
    """Inclusive local-day bounds in Asia/Tashkent."""
    start = datetime.combine(d, dt_time.min).replace(tzinfo=UZ_TZ)
    end = datetime.combine(d, dt_time.max).replace(tzinfo=UZ_TZ)
    return start, end


def iter_day_buckets(start_d: date, end_d: date) -> List[datetime]:
    """Return start-of-day datetimes (TZ-aware) from start to end inclusive."""
    cur = start_d
    out: List[datetime] = []
    while cur <= end_d:
        out.append(datetime.combine(cur, dt_time.min).replace(tzinfo=UZ_TZ))
        cur += timedelta(days=1)
    return out


def iter_week_buckets(start_d: date, end_d: date) -> List[datetime]:
    """Return start-of-week (Monday 00:00) TZ-aware datetimes covering [start_d, end_d]."""
    start_monday = start_d - timedelta(days=start_d.weekday())
    out: List[datetime] = []
    cur = start_monday
    while cur <= end_d:
        out.append(datetime.combine(cur, dt_time.min).replace(tzinfo=UZ_TZ))
        cur += timedelta(days=7)
    return out


def iter_month_buckets(start_d: date, end_d: date) -> List[datetime]:
    """Return first-day-of-month TZ-aware datetimes covering [start_d, end_d]."""
    out: List[datetime] = []
    y, m = start_d.year, start_d.month
    first = date(y, m, 1)
    while first <= end_d:
        out.append(datetime.combine(first, dt_time.min).replace(tzinfo=UZ_TZ))
        # increment month
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
        first = date(y, m, 1)
    return out


def bucket_index(group_by: str, start_d: date, end_d: date) -> List[datetime]:
    if group_by == "day":
        return iter_day_buckets(start_d, end_d)
    if group_by == "week":
        return iter_week_buckets(start_d, end_d)
    return iter_month_buckets(start_d, end_d)


@extend_schema(
    tags=["analytics"],
    parameters=[
        OpenApiParameter(
            name="start", required=False, type=str,
            description="Start date (YYYY-MM-DD) in Asia/Tashkent."
        ),
        OpenApiParameter(
            name="end", required=False, type=str,
            description="End date (YYYY-MM-DD) in Asia/Tashkent (inclusive)."
        ),
        OpenApiParameter(
            name="group_by", required=False, type=str, enum=["day", "week", "month"],
            description="Time bucket for timeseries."
        ),
        OpenApiParameter(
            name="shop_id", required=False, type=str,
            description="Optional shop UUID. Defaults to current user's shop; otherwise falls back to current user."
        ),
    ],
    responses=AnalyticsResponseSerializer,
)
class AnalyticsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ---------- 1) Parse params / range ----------
        start_str = request.query_params.get("start")
        end_str = request.query_params.get("end")
        group_by: Literal["day", "week", "month"] = request.query_params.get("group_by", "day")  # type: ignore
        if group_by not in GROUPERS:
            group_by = "day"

        try:
            if start_str and end_str:
                start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_d = datetime.strptime(end_str, "%Y-%m-%d").date()
            else:
                end_d = date.today()
                start_d = end_d - timedelta(days=6)  # default last 7 days
            start_dt, end_dt = local_day_bounds(start_d)[0], local_day_bounds(end_d)[1]
        except Exception as e:
            return Response({"detail": f"Invalid date(s): {e}"}, status=status.HTTP_400_BAD_REQUEST)

        # ---------- 2) Scope ----------
        user: User = request.user
        req_shop_id = request.query_params.get("shop_id")

        if req_shop_id:
            tx_base = Transaction.objects.filter(shop_id=req_shop_id, created_at__range=(start_dt, end_dt))
        else:
            if getattr(user, "shop_id", None):
                tx_base = Transaction.objects.filter(shop_id=user.shop_id, created_at__range=(start_dt, end_dt))
            else:
                tx_base = Transaction.objects.filter(user=user, created_at__range=(start_dt, end_dt))

        tx_completed = tx_base.filter(status="completed")
        tx_refunded = tx_base.filter(status="refunded")

        # ---------- 3) KPI calculations (authoritative from Transactions) ----------
        # Gross Sales (completed): sum of transaction.total_price
        gross = tx_completed.aggregate(
            total=Coalesce(Sum("total_price"), DEC_ZERO, output_field=DECIMAL_F)
        )["total"] or Decimal(0)

        # Discounts (completed): sum of item-level discounts
        items_completed = TransactionItem.objects.filter(transaction__in=tx_completed)
        discounts = items_completed.aggregate(
            total=Coalesce(Sum("discount"), DEC_ZERO, output_field=DECIMAL_F)
        )["total"] or Decimal(0)

        # Refunds (refunded): subtract full transaction total_price
        refunds = tx_refunded.aggregate(
            total=Coalesce(Sum("total_price"), DEC_ZERO, output_field=DECIMAL_F)
        )["total"] or Decimal(0)

        # Cost of Goods (completed)
        cost_of_goods = tx_completed.aggregate(
            total=Coalesce(Sum("cost_total"), DEC_ZERO, output_field=DECIMAL_F)
        )["total"] or Decimal(0)

        # Profit:
        # 1) Completed profit (your Transaction.profit is authoritative)
        completed_profit = tx_completed.aggregate(
            total=Coalesce(Sum("profit"), DEC_ZERO, output_field=DECIMAL_F)
        )["total"] or Decimal(0)
        # 2) Refunded profit (remove it)
        refunded_profit = tx_refunded.aggregate(
            total=Coalesce(Sum("profit"), DEC_ZERO, output_field=DECIMAL_F)
        )["total"] or Decimal(0)
        # 3) If discounts were not included in Transaction.profit, subtract them
        net_profit = completed_profit - refunded_profit - discounts

        # Net Sales = Gross Sales - Discounts - Refunds
        net_sales = gross - discounts - refunds

        orders = tx_completed.count()

        # ---------- 4) Timeseries (from Transaction.total_price) with zero fill ----------
        Grouper = GROUPERS[group_by]
        ts_rows = (
            tx_completed
            .annotate(bucket=Grouper("created_at", tzinfo=UZ_TZ))
            .values("bucket")
            .annotate(
                revenue=Coalesce(Sum("total_price"), DEC_ZERO, output_field=DECIMAL_F),
                orders=Coalesce(Count("id"), INT_ZERO, output_field=IntegerField()),
            )
            .order_by("bucket")
        )

        # map of bucket ISO -> (revenue, orders)
        raw_map: Dict[str, dict] = {}
        for row in ts_rows:
            key = row["bucket"].astimezone(UZ_TZ).isoformat()
            raw_map[key] = {
                "revenue": float(row["revenue"]),
                "orders": int(row["orders"]),
            }

        # build the complete bucket index and zero-fill
        buckets = bucket_index(group_by, start_d, end_d)
        timeseries = []
        for b in buckets:
            k = b.isoformat()
            item = raw_map.get(k, {"revenue": 0.0, "orders": 0})
            timeseries.append({"ts": k, **item})

        # ---------- 5) ByHour (24 entries, 0..23) ----------
        hour_rows = (
            tx_completed
            .annotate(h=TruncHour("created_at", tzinfo=UZ_TZ))
            .values("h")
            .annotate(
                revenue=Coalesce(Sum("total_price"), DEC_ZERO, output_field=DECIMAL_F),
                orders=Coalesce(Count("id"), INT_ZERO, output_field=IntegerField()),
            )
            .order_by("h")
        )
        hour_map = {row["h"].astimezone(UZ_TZ).hour: row for row in hour_rows}
        by_hour = []
        for hr in range(24):
            row = hour_map.get(hr)
            by_hour.append({
                "hour": hr,
                "revenue": float(row["revenue"]) if row else 0.0,
                "orders": int(row["orders"]) if row else 0,
            })

        # ---------- 6) Payments breakdown ----------
        payment_label = {"card": "Card", "cash": "Cash", "debt": "Debt", "mixed": "Mixed"}
        pay_rows = (
            tx_completed
            .values("payment_type")
            .annotate(amount=Coalesce(Sum("total_price"), DEC_ZERO, output_field=DECIMAL_F))
            .order_by("-amount")
        )
        payments = [
            {"method": payment_label.get(r["payment_type"], r["payment_type"]), "amount": float(r["amount"])}
            for r in pay_rows
        ]

        # ---------- 7) Top products (from items of completed transactions) ----------
        price_times_qty = ExpressionWrapper(F("price_at_sale") * F("quantity"), output_field=DECIMAL_F)
        prod_rows = (
            items_completed
            .select_related("product")
            .values("product_id", "product__name")
            .annotate(
                qty=Coalesce(Sum("quantity"), INT_ZERO, output_field=IntegerField()),
                revenue=Coalesce(Sum(price_times_qty), DEC_ZERO, output_field=DECIMAL_F),
            )
            .order_by("-revenue")[:20]
        )
        top_products = [
            {
                "id": str(r["product_id"]),
                "name": r["product__name"],
                "qty": float(r["qty"]),           # RN expects number
                "revenue": float(r["revenue"]),
            }
            for r in prod_rows
        ]

        # ---------- 8) Build & validate payload ----------
        payload = {
            "timeseries": timeseries,
            "byHour": by_hour,
            "payments": payments,
            "topProducts": top_products,
            "discounts": float(discounts),
            "refunds": float(refunds),
            "grossSales": float(gross),
            "netSales": float(net_sales),
            "orders": int(orders),
            "profit": float(net_profit),
            "costOfGoods": float(cost_of_goods),
        }

        # Optional runtime validation (helps catch mistakes early in development)
        ser = AnalyticsResponseSerializer(data=payload)
        ser.is_valid(raise_exception=True)

        return Response(ser.data, status=status.HTTP_200_OK)
