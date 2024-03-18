# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService


class SpecUploadView(ManagerRequiredView):
    """Serves an "upload file" page but somewhat strangely doesn't process the form."""

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        context.update({"is_there_a_spec": SpecificationService.is_there_a_spec()})
        return render(request, "SpecCreator/spec_upload.html", context)
