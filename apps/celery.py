import os
from celery import Celery

# Django settings modulini sozlang
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')

app = Celery('apps')

# Django settings dan konfiguratsiyani olish
app.config_from_object('django.conf:settings', namespace='CELERY')

# Barcha ilovalardan tasks.py fayllarini avto-topish
app.autodiscover_tasks()