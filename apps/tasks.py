import time

from celery import shared_task

from apps.models import User, Payment


@shared_task
def deduct_daily_fee():
    active_users = User.objects.filter(is_active=True)

    for user in active_users:
        if user.balance >= 1000:
            user.balance -= 1000
            user.save()

            Payment.objects.create(
                user=user,
                amount=-1000,
                payment_status='paid',
                description='Kunlik tolov'
            )
        else:
            user.is_active = False
            user.save()

            Payment.objects.create(
                user=user,
                amount=0,
                payment_status='failed',
                description='Balans yetarli emas'
            )


@shared_task
def start_daily_deduction(user_id):
    user = User.objects.get(id=user_id)
    while user.is_active:
        deduct_daily_fee.delay()
        time.sleep(86400)  # 24 soat kutamiz


import json
import random

import requests
from celery import Celery
from redis import Redis

from root.settings import ESKIZ_EMAIL, ESKIZ_PASSWORD

app = Celery('hello', broker='redis://localhost:6379/0')


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
    return token, token_type


@app.task()
def send_code(user_data: dict, message, pk):
    redis = Redis()
    token, token_type = login_eskiz()
    send_url = "https://notify.eskiz.uz/api/message/sms/send"
    data = {
        "mobile_phone": user_data.get("phone_number"),
        "message": message,
        "from": "7777",
        "callback_url": "http://0000.uz/test.php"
    }
    random_code = random.randrange(10 ** 5, 10 ** 6)
    requests.post(send_url, data, headers={"Authorization": f"{token_type.title()} {token}"})
    redis.mset({pk: json.dumps({"code": random_code, 'data': user_data})})
    return random_code



