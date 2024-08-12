# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.generic import View

from .base_group_views import ManagerRequiredView
from .forms import CompleteWipeForm
from .services import big_red_button

from Papers.services import SpecificationService
from Scan.services import ScanService

from plom.plom_exceptions import PlomDependencyConflict, PlomDatabaseCreationError


class TroublesAfootGenericErrorView(View):
    def get(self, request: HttpRequest, *, hint: str) -> HttpResponse:
        """Render an unexpected or semi-expected "error page" using kludges.

        We'd probably like to show a real error page, like 404 or 500.
        But for technical reasons we might not know how (yet!).
        Code calling this should be improved if possible.

        Args:
            request: the incoming request.

        Keyword Args:
            hint: a short hint about why this is happening.  Its going
                to be recovered from inside the URL so its probably
                something easy to encode like
                ``"oh-snap-x-can-be-negative"``.

        Returns:
            A rendered HTML page.
        """
        context = {"hint": hint}
        return render(request, "base/troubles_afoot.html", context)


class ResetView(ManagerRequiredView):
    """View class for handling the reset functionality."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles the GET request for the reset functionality.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            An HTTP response object.
        """
        context = self.build_context()
        context.update({"bundles_staged": ScanService().staging_bundles_exist()})
        return render(request, "base/reset.html", context)


class ResetConfirmView(ManagerRequiredView):
    """View class for confirming the reset of a Plom instance."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles the GET request for the reset confirmation view.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: The HTTP response object.
        """
        context = self.build_context()
        form = CompleteWipeForm()
        try:
            reset_phrase = SpecificationService.get_shortname()
        except ObjectDoesNotExist:
            context.update({"no_spec": True})
            return render(request, "base/reset_confirm.html", context=context)
        context.update(
            {
                "no_spec": False,
                "bundles_staged": ScanService().staging_bundles_exist(),
                "wipe_form": form,
                "reset_phrase": reset_phrase,
            }
        )
        return render(request, "base/reset_confirm.html", context=context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles the POST request for the reset confirmation view.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            HttpResponse: The HTTP response object.
        """
        context = self.build_context()
        form = CompleteWipeForm(request.POST)
        reset_phrase = SpecificationService.get_shortname()
        _confirm_field = "confirmation_field"
        if form.is_valid():
            if form.cleaned_data[_confirm_field] == reset_phrase:
                try:
                    big_red_button.reset_assessment_preparation_database()
                except (PlomDependencyConflict, PlomDatabaseCreationError) as err:
                    messages.add_message(request, messages.ERROR, f"{err}")
                    return redirect(reverse("prep_conflict"))

                messages.success(request, "Plom instance successfully wiped.")
                return redirect("home")
            else:
                form.add_error(_confirm_field, "Phrase is incorrect")
                context.update(
                    {
                        "bundles_staged": ScanService().staging_bundles_exist(),
                        "wipe_form": form,
                    }
                )
                return render(request, "base/reset_confirm.html", context=context)
