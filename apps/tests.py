import random

def generate_unique_invoice_code():
    from apps.models import User  # avoid circular import
    while True:
        code = str(random.randint(100000, 999999))  # faqat 6 xonali
        if not User.objects.filter(invoice_code=code).exists():
            return code