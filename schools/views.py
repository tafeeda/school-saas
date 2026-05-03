from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from core.utils import user_is_super_admin
from accounts.forms import SchoolAdminCreationForm
from core.decorators import super_admin_required
from .forms import SchoolForm, SchoolSubscriptionControlForm, ManualSubscriptionPaymentForm
from .models import School, SchoolSetting, SchoolSubscriptionRecord

import uuid
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from .paystack_utils import initialize_paystack_transaction, verify_paystack_transaction
from django.urls import reverse
from datetime import timedelta
import hmac
import hashlib
import json
from django.http import HttpResponse



User = get_user_model()


def activate_school_subscription_from_payment(*, school, amount, reference, payment_method, note=""):
    existing = SchoolSubscriptionRecord.objects.filter(reference=reference).first()
    if existing:
        return existing, False

    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=30)

    record = SchoolSubscriptionRecord.objects.create(
        school=school,
        amount=amount,
        payment_method=payment_method,
        payment_status="PAID",
        reference=reference,
        paid_at=timezone.now(),
        subscription_start_date=start_date,
        subscription_end_date=end_date,
        note=note,
    )

    school.is_subscription_active = True
    school.is_suspended = False
    school.subscription_start_date = start_date
    school.subscription_end_date = end_date
    school.subscription_amount = amount
    school.payment_method = payment_method
    school.save()

    return record, True


@login_required
@super_admin_required
def school_list(request):
    schools = School.objects.all().order_by("name")
    return render(
        request,
        "schools/school_list.html",
        {
            "page_title": "Schools",
            "schools": schools,
        },
    )


@login_required
@super_admin_required
def school_create(request):
    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES)
        if form.is_valid():
            school = form.save(commit=False)
            school.created_by = request.user
            school.save()
            SchoolSetting.objects.get_or_create(school=school)
            messages.success(request, f"{school.name} was created successfully.")
            return redirect("school_list")
    else:
        form = SchoolForm()

    return render(
        request,
        "schools/school_form.html",
        {
            "page_title": "Create School",
            "form": form,
            "form_mode": "create",
        },
    )


@login_required
@super_admin_required
def school_detail(request, pk):
    school = get_object_or_404(School, pk=pk)
    return render(
        request,
        "schools/school_detail.html",
        {
            "page_title": "School Detail",
            "school": school,
        },
    )


@login_required
@super_admin_required
def school_update(request, pk):
    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, f"{school.name} was updated successfully.")
            return redirect("school_list")
    else:
        form = SchoolForm(instance=school)

    return render(
        request,
        "schools/school_form.html",
        {
            "page_title": "Edit School",
            "form": form,
            "form_mode": "edit",
            "school": school,
        },
    )


@login_required
@super_admin_required
def school_delete(request, pk):
    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        school_name = school.name
        school.delete()
        messages.success(request, f"{school_name} was deleted successfully.")
        return redirect("school_list")

    return render(
        request,
        "includes/confirm_delete.html",
        {
            "object": school,
            "page_title": "Delete School",
            "cancel_url": "/schools/",
        },
    )


@login_required
@super_admin_required
def school_toggle_status(request, pk):
    school = get_object_or_404(School, pk=pk)
    school.is_active = not school.is_active
    school.save(update_fields=["is_active"])

    status_text = "activated" if school.is_active else "deactivated"
    messages.success(request, f"{school.name} has been {status_text}.")
    return redirect("school_list")


@login_required
@super_admin_required
def create_school_admin(request):
    if request.method == "POST":
        form = SchoolAdminCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"School admin account for {user.username} was created successfully.",
            )
            return redirect("school_list")
    else:
        form = SchoolAdminCreationForm()

    return render(
        request,
        "schools/create_school_admin.html",
        {
            "page_title": "Create School Admin",
            "form": form,
        },
    )


@login_required
def school_subscription_control(request, pk):
    if not user_is_super_admin(request.user):
        return redirect("dashboard_redirect")

    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        form = SchoolSubscriptionControlForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School subscription settings updated successfully.")
            return redirect("school_subscription_control", pk=school.pk)
    else:
        form = SchoolSubscriptionControlForm(instance=school)

    records = school.subscription_records.all()

    return render(
        request,
        "schools/school_subscription_control.html",
        {
            "school": school,
            "form": form,
            "records": records,
        },
    )


@login_required
def school_manual_payment_create(request, pk):
    if not user_is_super_admin(request.user):
        return redirect("dashboard_redirect")

    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        form = ManualSubscriptionPaymentForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.school = school
            record.save()

            if record.payment_status == "PAID":
                school.is_subscription_active = True
                school.is_suspended = False
                school.subscription_start_date = record.subscription_start_date
                school.subscription_end_date = record.subscription_end_date
                school.subscription_amount = record.amount
                school.payment_method = record.payment_method
                school.save()

            messages.success(request, "Subscription payment record saved successfully.")
            return redirect("school_subscription_control", pk=school.pk)
    else:
        form = ManualSubscriptionPaymentForm(
            initial={
                "payment_method": school.payment_method,
                "payment_status": "PAID",
            }
        )

    return render(
        request,
        "schools/school_manual_payment_form.html",
        {
            "school": school,
            "form": form,
        },
    )


@login_required
def school_subscription_control(request, pk):
    if not user_is_super_admin(request.user):
        return redirect("dashboard_redirect")

    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        form = SchoolSubscriptionControlForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School subscription settings updated successfully.")
            return redirect("school_subscription_control", pk=school.pk)
    else:
        form = SchoolSubscriptionControlForm(instance=school)

    records = school.subscription_records.all()

    return render(
        request,
        "schools/school_subscription_control.html",
        {
            "school": school,
            "form": form,
            "records": records,
        },
    )


@login_required
def school_manual_payment_create(request, pk):
    if not user_is_super_admin(request.user):
        return redirect("dashboard_redirect")

    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        form = ManualSubscriptionPaymentForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.school = school
            record.save()

            if record.payment_status == "PAID":
                school.is_subscription_active = True
                school.is_suspended = False
                school.subscription_start_date = record.subscription_start_date
                school.subscription_end_date = record.subscription_end_date
                school.subscription_amount = record.amount
                school.payment_method = record.payment_method
                school.save()

            messages.success(request, "Subscription payment record saved successfully.")
            return redirect("school_subscription_control", pk=school.pk)
    else:
        form = ManualSubscriptionPaymentForm(
            initial={
                "payment_method": school.payment_method,
                "payment_status": "PAID",
            }
        )

    return render(
        request,
        "schools/school_manual_payment_form.html",
        {
            "school": school,
            "form": form,
        },
    )


@login_required
def school_paystack_pay(request):
    school = getattr(request.user, "school", None)

    if not school:
        messages.error(request, "No school is attached to your account.")
        return redirect("dashboard_redirect")

    if school.payment_method != "ONLINE" or not school.online_payment_enabled:
        messages.error(request, "Online payment is not enabled for your school.")
        return redirect("dashboard_redirect")

    if not school.subscription_amount or school.subscription_amount <= 0:
        messages.error(request, "Subscription amount is not configured yet.")
        return redirect("dashboard_redirect")

    reference = f"SCHSUB-{school.id}-{uuid.uuid4().hex[:10].upper()}"

    metadata = {
        "school_id": school.id,
        "school_name": school.name,
        "payment_for": "subscription",
    }

    callback_url = request.build_absolute_uri(
        reverse("school_paystack_callback")
    )

    # Paystack expects amount in subunits: NGN 5000 => 500000
    amount_kobo = int(Decimal(school.subscription_amount) * 100)

    email = school.email or request.user.email
    if not email:
        messages.error(request, "No email is configured for this school.")
        return redirect("dashboard_redirect")

    metadata = {
        "school_id": school.id,
        "school_name": school.name,
        "payment_for": "subscription",
    }

    try:
        result = initialize_paystack_transaction(
            email=email,
            amount_kobo=amount_kobo,
            reference=reference,
            callback_url=callback_url,
            metadata=metadata,
        )

        if not result.get("status"):
            messages.error(request, result.get("message", "Unable to initialize payment."))
            return redirect("dashboard_redirect")

        auth_url = result["data"]["authorization_url"]
        return redirect(auth_url)

    except Exception as exc:
        messages.error(request, f"Payment initialization failed: {exc}")
        return redirect("dashboard_redirect")


@login_required
def school_paystack_callback(request):
    reference = request.GET.get("reference")

    if not reference:
        messages.error(request, "Payment reference missing.")
        return redirect("school_payment_failed")

    school = getattr(request.user, "school", None)
    if not school:
        messages.error(request, "No school is attached to your account.")
        return redirect("dashboard_redirect")

    try:
        result = verify_paystack_transaction(reference)

        if not result.get("status"):
            return redirect("school_payment_failed")

        data = result.get("data", {})
        transaction_status = data.get("status")

        if transaction_status != "success":
            return redirect("school_payment_failed")

        amount = Decimal(data.get("amount", 0)) / Decimal("100")

        record, created = activate_school_subscription_from_payment(
            school=school,
            amount=amount,
            reference=reference,
            payment_method="ONLINE",
            note="Paystack callback verification",
        )

        return redirect("school_payment_success")

    except Exception:
        return redirect("school_payment_failed")


@login_required
def school_subscription_status(request):
    school = getattr(request.user, "school", None)

    if not school:
        messages.error(request, "No school is attached to your account.")
        return redirect("dashboard_redirect")

    return render(request, "schools/school_subscription_status.html")



def paystack_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    signature = request.headers.get("x-paystack-signature")
    if not signature:
        return HttpResponse(status=400)

    secret = settings.PAYSTACK_SECRET_KEY
    payload = request.body

    computed_signature = hmac.new(
        secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, signature):
        return HttpResponse(status=400)

    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "charge.success":
        reference = data.get("reference")
        amount = Decimal(data.get("amount", 0)) / Decimal("100")
        metadata = data.get("metadata", {}) or {}
        school_id = metadata.get("school_id")

        if school_id and reference:
            school = School.objects.filter(pk=school_id).first()
            if school:
                activate_school_subscription_from_payment(
                    school=school,
                    amount=amount,
                    reference=reference,
                    payment_method="ONLINE",
                    note="Paystack webhook confirmation",
                )

    return HttpResponse(status=200)


@login_required
def school_payment_success(request):
    return render(request, "schools/payment_success.html")


@login_required
def school_payment_failed(request):
    return render(request, "schools/payment_failed.html")