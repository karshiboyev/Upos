# apps/tasks.py
import json
import random
from django.conf import settings
from django.db import transaction
from django.db.models import F
from celery import shared_task
import requests
from redis import Redis

from apps.models import User
from root.settings import ESKIZ_EMAIL, ESKIZ_PASSWORD







def login_eskiz():
    login_url = "https://notify.eskiz.uz/api/auth/login"
    data = {
        "email": ESKIZ_EMAIL,
        "password": ESKIZ_PASSWORD,
    }
    response = requests.post(login_url, data=data)
    response_data = response.json()
    token = response_data.get("data").get("token")
    token_type = response_data.get("token_type")
    return token , token_type



@shared_task
def send_code(user_data: dict, message: str, pk: str):
    """
    Sends OTP via Eskiz and Telegram, stores it in Redis.
    """
    # Generate OTP
    random_code = random.randint(100000, 999999)
    full_message = f"{message}. Your OTP code is: {random_code}"

    # Send via x
    try:
        token_type, token = login_eskiz()
        send_url = "https://notify.eskiz.uz/api/message/sms/send"
        data = {
            "mobile_phone": user_data.get("phone_number"),
            "message": full_message,
            "from": "4546",
            "callback_url": "http://0000.uz/test.php",
        }
        headers = {"Authorization": f"{token_type} {token}"}
        requests.post(send_url , data , headers={"Authorization": f"{token_type.title()} {token}"})
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
    redis.mset({pk: json.dumps({"code": random_code, 'data': user_data})})

    return random_code

