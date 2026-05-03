from django.urls import path

from .views import (
    create_school_admin,
    school_create,
    school_delete,
    school_detail,
    school_list,
    school_toggle_status,
    school_update,
    school_subscription_control,
    school_manual_payment_create,
    school_paystack_pay,
    school_paystack_callback,
    school_subscription_status,
    paystack_webhook,
    school_payment_success,
    school_payment_failed,
)

urlpatterns = [
    path("", school_list, name="school_list"),
    path("create/", school_create, name="school_create"),
    path("create-admin/", create_school_admin, name="create_school_admin"),
    path("<int:pk>/", school_detail, name="school_detail"),
    path("<int:pk>/edit/", school_update, name="school_update"),
    path("<int:pk>/delete/", school_delete, name="school_delete"),
    path("<int:pk>/toggle-status/", school_toggle_status, name="school_toggle_status"),
    path("<int:pk>/subscription/", school_subscription_control, name="school_subscription_control"),
    path("<int:pk>/subscription/manual-payment/", school_manual_payment_create, name="school_manual_payment_create"),
    path("subscription/paystack/pay/", school_paystack_pay, name="school_paystack_pay"),
    path("subscription/paystack/callback/", school_paystack_callback, name="school_paystack_callback"),
    path("subscription/status/", school_subscription_status, name="school_subscription_status"),
    path("paystack/webhook/", paystack_webhook, name="paystack_webhook"),
    path("subscription/payment/success/", school_payment_success, name="school_payment_success"),
    path("subscription/payment/failed/", school_payment_failed, name="school_payment_failed"),
]