import requests
from django.conf import settings


PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/{reference}"


def initialize_paystack_transaction(*, email, amount_kobo, reference, callback_url, metadata=None):
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": email,
        "amount": int(amount_kobo),
        "reference": reference,
        "callback_url": callback_url,
        "currency": settings.PAYSTACK_CURRENCY,
        "metadata": metadata or {},
    }

    response = requests.post(PAYSTACK_INITIALIZE_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def verify_paystack_transaction(reference):
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    url = PAYSTACK_VERIFY_URL.format(reference=reference)
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()