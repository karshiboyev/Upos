# apps/tasks.py
import json
import random
from django.conf import settings
from django.db import transaction
from django.db.models import F
from celery import shared_task
import requests
from redis import Redis

from apps.models import User, Payment


@shared_task
def deduct_daily_fee():
    """
    Deduct 1000 from all active users.
    If balance < 1000 -> deactivate and record failed payment.
    Use transactions to reduce race conditions.
    """
    fee = 1000

    # Process those who can pay
    payers = User.objects.select_for_update().filter(is_active=True, balance__gte=fee)
    # lock in batches to avoid long locks on SQLite
    CHUNK = 200
    start = 0
    while True:
        batch = list(payers[start:start + CHUNK].values("id"))
        if not batch:
            break
        ids = [row["id"] for row in batch]
        with transaction.atomic():
            # subtract safely in DB
            User.objects.filter(id__in=ids).update(balance=F("balance") - fee)
            for uid in ids:
                Payment.objects.create(
                    user_id=uid,
                    amount=-fee,
                    payment_status="paid",
                    description="Kunlik to‘lov",
                )
        start += CHUNK

    # Deactivate those who cannot pay
    nonpayers = User.objects.select_for_update().filter(is_active=True, balance__lt=fee)
    start = 0
    while True:
        batch = list(nonpayers[start:start + CHUNK].values("id"))
        if not batch:
            break
        ids = [row["id"] for row in batch]
        with transaction.atomic():
            User.objects.filter(id__in=ids).update(is_active=False)
            for uid in ids:
                Payment.objects.create(
                    user_id=uid,
                    amount=0,
                    payment_status="failed",
                    description="Balans yetarli emas",
                )
        start += CHUNK


@shared_task
def start_daily_deduction(user_id):
    """
    DO NOT loop/sleep inside a task. This wrapper simply triggers once.
    If you need a per-user schedule, configure a periodic task or
    use celery beat dynamically. For now, call the global daily task:
    """
    return deduct_daily_fee.delay()


def _eskiz_login():
    url = "https://notify.eskiz.uz/api/auth/login"
    data = {"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD}
    r = requests.post(url, data=data, timeout=10)
    r.raise_for_status()
    j = r.json()
    token = j.get("data", {}).get("token")
    token_type = j.get("token_type", "Bearer")
    if not token:
        raise RuntimeError("Eskiz token not found in response")
    return token_type.title(), token


@shared_task
def send_code(user_data: dict, message: str, pk: str):
    """
    Sends OTP via Eskiz and Telegram, stores it in Redis.
    """
    # Generate OTP
    random_code = random.randint(100000, 999999)
    full_message = f"{message}. Your OTP code is: {random_code}"

    # Send via Eskiz
    try:
        token_type, token = _eskiz_login()
        send_url = "https://notify.eskiz.uz/api/message/sms/send"
        data = {
            "mobile_phone": user_data.get("phone_number"),
            "message": full_message,
            "from": "7777",
            "callback_url": "http://0000.uz/test.php",
        }
        headers = {"Authorization": f"{token_type} {token}"}
        requests.post(send_url, data=data, headers=headers, timeout=10)
    except requests.RequestException:
        # Optionally log or retry
        pass

    # Send via Telegram
    try:
        telegram_bot_token = "8472811004:AAGY9FvLLYKdEHGVwoC6wofpv82YxUGMhvY"
        telegram_chat_id = "5403516004"
        telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        telegram_data = {
            "chat_id": telegram_chat_id,
            "text": full_message
        }
        response = requests.get(telegram_url, params=telegram_data, timeout=10)
        print("Telegram response:", response.status_code, response.text)
    except requests.RequestException as e:
        print("Telegram error:", str(e))

    # Save to Redis
    redis = Redis(host="localhost", port=6379, db=0)
    payload = {"code": random_code, "data": user_data}
    redis.mset({pk: json.dumps(payload)})

    return random_code

