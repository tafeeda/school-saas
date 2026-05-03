from django.shortcuts import redirect
from django.utils import timezone
from django.contrib.auth import logout


class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = request.user

        if user.is_authenticated:

            # Super admin should NEVER be blocked
            if getattr(user, "role", None) == "SUPER_ADMIN":
                return self.get_response(request)

            school = getattr(user, "school", None)

            if school:

                # 1. Check suspension
                if school.is_suspended:
                    logout(request)
                    return redirect("subscription_blocked")

                today = timezone.now().date()

                # 2. Check trial
                if school.trial_end_date and today > school.trial_end_date.date():
                    # trial expired
                    if not school.subscription_end_date:
                        return redirect("subscription_blocked")

                # 3. Check subscription expiry
                if school.subscription_end_date and today > school.subscription_end_date:
                    school.is_subscription_active = False
                    school.save()
                    return redirect("subscription_blocked")

        return self.get_response(request)