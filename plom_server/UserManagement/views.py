# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Bryan Tanady

import json

from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView

from .services import PermissionChanger

from Authentication.services import AuthenticationServices

from django.shortcuts import get_object_or_404
from django.urls import reverse
from .models import ProbationPeriod
from django.contrib import messages
from .services.probationService import ProbationService
from Progress.services.userinfo_service import UserInfoServices


class UserPage(ManagerRequiredView):
    """Class that handles the views in UserInfo Page.

    This page utilizes extra tags embeddes in messages to display messages in different parts/cards in the page.
    modify_probation: is the tag used when one interacts with "Set Probation" button and "Modify Probation Limit".
    modify_default_limit: when one interacts with "Change Default Limit" button".
    set_probation_confirmation: the tag for the probation confirmation dialog interaction.
    """

    def get(self, request):
        managers = User.objects.filter(groups__name="manager")
        scanners = User.objects.filter(groups__name="scanner").exclude(
            groups__name="manager"
        )
        lead_markers = User.objects.filter(groups__name="lead_marker")
        markers = User.objects.filter(groups__name="marker").prefetch_related(
            "auth_token"
        )
        probation_users = ProbationPeriod.objects.values_list("user_id", flat=True)
        context = {
            "scanners": scanners,
            "markers": markers,
            "lead_markers": lead_markers,
            "managers": managers,
            "probation_users": probation_users,
        }
        return render(request, "UserManagement/users.html", context)

    def post(self, request, username):
        PermissionChanger.toggle_user_active(username)

        return HttpResponseClientRefresh()

    @login_required
    def enableScanners(self):
        PermissionChanger.set_all_scanners_active(True)
        return redirect("/users")

    @login_required
    def disableScanners(self):
        PermissionChanger.set_all_scanners_active(False)
        return redirect("/users")

    @login_required
    def enableMarkers(self):
        PermissionChanger.set_all_markers_active(True)
        return redirect("/users")

    @login_required
    def disableMarkers(self):
        PermissionChanger.set_all_markers_active(False)
        return redirect("/users")

    @login_required
    def toggleLeadMarker(self, username):
        PermissionChanger.toggle_lead_marker_group_membership(username)
        return redirect("/users")


class PasswordResetPage(ManagerRequiredView):
    def get(self, request, username):
        user_obj = User.objects.get(username=username)
        link = AuthenticationServices().generate_link(request, user_obj)

        context = {"username": username, "link": link}
        return render(request, "UserManagement/password_reset_page.html", context)


class HTMXExplodeView(ManagerRequiredView):
    """For debugging, this view causes some sorts of errors non-deterministically."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """For debugging, Getting this randomly fails with 404 or a server 500 error or succeeds."""
        import random

        if random.random() < 0.333:
            1 / 0
        if random.random() < 0.5:
            raise Http404("Should happen 1/3 of the time")
        return HttpResponse("Button pushed", status=200)


class SetProbationView(ManagerRequiredView):
    """View to handle setting a probation period for a user.

    Note: enforce_set_probation is a special flag that enforce a marker to be set to probation
    even though they do not fulfill the probation's limit restriction. The limit will be set
    to their current number of question claimed.
    """

    def post(self, request, username):
        """Handle the POST request to set the probation period for the specified user."""
        user = get_object_or_404(User, username=username)
        next_page = request.POST.get(
            "next", request.META.get("HTTP_REFERER", reverse("users"))
        )

        # Special flag received when user confirms to enforce setting probatiog, ignoring probation limit restriction.
        if "enforce_set_probation" in request.POST:
            complete_and_claimed_tasks = (
                UserInfoServices().get_total_annotated_and_claimed_count_based_on_user()
            )
            complete, claimed = complete_and_claimed_tasks[username]
            probation_period, created = ProbationPeriod.objects.get_or_create(
                user=user, limit=claimed
            )

        # No special flag received, proceed to check whether the marker fulfills the restriction.
        elif ProbationService().can_set_probation(user):
            probation_period, created = ProbationPeriod.objects.get_or_create(
                user=user, limit=ProbationPeriod.default_limit
            )
            if not created:
                probation_period.limit = ProbationPeriod.default_limit
                probation_period.save()

        # Message is specially crafted for confirmation dialog.
        else:
            details = {
                "username": username,
            }
            messages.info(
                request, json.dumps(details), extra_tags="set_probation_confirmation"
            )

        return redirect(next_page)


class UnsetProbationView(ManagerRequiredView):
    """View to handle unsetting a probation period for a user."""

    def post(self, request, username):
        """Handle the POST request to unset the probation period for the specified user."""
        user = get_object_or_404(User, username=username)
        probation_period = ProbationPeriod.objects.filter(user=user)
        probation_period.delete()

        next_page = request.POST.get(
            "next", request.META.get("HTTP_REFERER", reverse("users"))
        )
        return redirect(next_page)


class EditProbationLimitView(ManagerRequiredView):
    """View to handle editing the probation limit for a user."""

    def post(self, request):
        """Handle the POST request to update the probation limit for the specified user."""
        username = request.POST.get("username")
        new_limit = int(request.POST.get("limit"))
        user = get_object_or_404(User, username=username)

        if ProbationService().new_limit_is_valid(new_limit, user):
            probation_period = ProbationPeriod.objects.filter(user=user).first()
            probation_period.limit = new_limit
            probation_period.save()
            messages.success(
                request,
                "Probation limit updated successfully.",
                extra_tags="modify_probation",
            )
        else:
            messages.error(request, "Invalid Limit!", extra_tags="modify_probation")

        previous_url = request.META.get("HTTP_REFERER", reverse("users"))
        return redirect(previous_url)


class ModifyProbationView(ManagerRequiredView):
    """View to handle modifying the probation state or limit for multiple users."""

    def post(self, request):
        """Handle the POST request to update the probation limits for the specified users."""
        user_ids = request.POST.getlist("users")
        new_limit = int(request.POST.get("limit"))
        valid_markers = []
        invalid_markers = []

        if not user_ids:
            messages.error(request, "No users selected.")
            return redirect(reverse("progress_user_info_home"))

        for user_id in user_ids:
            user = get_object_or_404(User, pk=user_id)
            probation_period = ProbationPeriod.objects.get(user=user)
            if not ProbationService().new_limit_is_valid(limit=new_limit, user=user):
                invalid_markers.append(user.username)
            else:
                valid_markers.append(user.username)
                probation_period.limit = new_limit
                probation_period.save()

        if len(invalid_markers) > 0:
            messages.success(
                request,
                f"Probation limit has been successfully updated for: {', '.join(valid_markers)}",
                extra_tags="modify_probation",
            )
            messages.error(
                request,
                f"Invalid limit for: {', '.join(invalid_markers)}",
                extra_tags="modify_probation",
            )
        else:
            messages.success(
                request,
                "All probation limits are updated successfully.",
                extra_tags="modify_probation",
            )
        return redirect(reverse("progress_user_info_home"))


class ModifyDefaultLimitView(ManagerRequiredView):
    """View to handle modifying the default probation limit."""

    def post(self, request):
        """Handle the POST request to change the default probation limit."""
        new_limit = int(request.POST.get("limit"))

        if new_limit > 0:
            ProbationPeriod.set_default_limit(new_limit)
            messages.success(
                request,
                "Default limit updated successfully.",
                extra_tags="modify_default_limit",
            )
        else:
            messages.error(
                request, "Limit is invalid!", extra_tags="modify_default_limit"
            )

        previous_url = request.META.get("HTTP_REFERER", reverse("users"))
        return redirect(previous_url)


class BulkSetProbationView(ManagerRequiredView):
    """View to handle bulk setting probation for all markers."""

    def post(self, request):
        probation_service = ProbationService()
        markers = User.objects.filter(groups__name="marker")
        probation_set_count = 0

        for marker in markers:
            if probation_service.can_set_probation(marker):
                probation_period, created = ProbationPeriod.objects.get_or_create(
                    user=marker,
                    defaults={"limit": ProbationPeriod.default_limit},
                )
                probation_set_count += 1

        messages.success(request, "All markers have been set to probation.")
        return redirect(reverse("progress_user_info_home"))


class BulkUnsetProbationView(ManagerRequiredView):
    """View to handle bulk unsetting probation for all markers."""

    def post(self, request):
        markers = User.objects.filter(groups__name="marker")
        ProbationPeriod.objects.filter(user__in=markers).delete()
        messages.success(request, "Probation unset for all markers.")
        return redirect(reverse("progress_user_info_home"))
