# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald

import csv
from io import StringIO

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from .forms import TaskOrderForm, UploadFileForm
from .services.task_ordering_service import TaskOrderService


class TaskOrderPageView(ManagerRequiredView):
    """A page for setting the task marking priorities."""

    def get(self, request: HttpRequest) -> HttpResponse:
        template_name = "TaskOrder/task_order_landing.html"
        tos = TaskOrderService()

        context = self.build_context()
        order_form = TaskOrderForm()
        upload_form = UploadFileForm()

        order_form.fields["order_tasks_by"].initial = request.session.get(
            "order_tasks_by",
        )
        paper_to_priority_dict = tos.get_paper_number_to_priority_list()
        q_labels = SpecificationService.get_question_labels()

        context.update(
            {
                "order_form": order_form,
                "upload_form": upload_form,
                "q_labels": q_labels,
                "paper_to_priority_dict": paper_to_priority_dict,
            }
        )

        return render(request, template_name, context=context)

    @staticmethod
    def upload_task_priorities(request: HttpRequest) -> HttpResponse:
        """Upload the task priorities as a CSV file and update the database."""
        if request.method == "POST":
            tos = TaskOrderService()

            order_by = request.POST.get("order_tasks_by")
            request.session["order_tasks_by"] = order_by

            custom_order = {}
            if order_by == "custom":
                form = UploadFileForm(request.POST, request.FILES)
                if request.FILES:
                    if form.is_valid():
                        file = form.cleaned_data["file"]
                        custom_order = tos.handle_file_upload(file)
                    else:
                        return HttpResponse("Invalid form: " + form.errors.as_text())
                else:
                    return HttpResponse("No file uploaded")

            tos.update_priority_ordering(order_by, custom_order=custom_order)

        return redirect("task_order_landing")

    @staticmethod
    def download_priorities(request: HttpRequest) -> HttpResponse:
        """Download the task priorities."""
        shortname = SpecificationService.get_short_name_slug()
        tos = TaskOrderService()
        keys = tos.get_csv_header()
        priorities = tos.get_task_priorities_download()

        f = StringIO()
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(priorities)
        f.seek(0)

        filename = f"task-order--{shortname}.csv"

        response = HttpResponse(f, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={filename}".format(
            filename=filename
        )

        return response
