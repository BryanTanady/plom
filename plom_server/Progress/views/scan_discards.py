# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect
from django.urls import reverse


from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from Progress.services import ManageScanService, ManageDiscardService


class ScanDiscardView(ManagerRequiredView):
    """View the table of discarded images."""

    def get(self, request: HttpRequest) -> HttpResponse:
        mss = ManageScanService()
        context = self.build_context()
        discards = mss.get_discarded_images()
        context.update(
            {
                "current_page": "discard",
                "number_of_discards": len(discards),
                "discards": discards,
            }
        )
        return render(request, "Progress/scan_discard.html", context)


class ScanReassignView(ManagerRequiredView):
    def get(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        mss = ManageScanService()
        tmp = mss.get_pushed_image(img_pk)
        # MyPy worries tmp can be None
        assert tmp is not None, "Unexpected got None for Image: can this happen?"
        img_angle = -tmp.rotation
        context = self.build_context()
        context.update(
            {"current_page": "reassign", "image_pk": img_pk, "angle": img_angle}
        )

        papers_missing_fixed_pages = mss.get_papers_missing_fixed_pages()
        used_papers = mss.get_all_used_test_papers()
        question_html_labels = SpecificationService.get_question_html_label_triples()

        context.update(
            {
                "papers_missing_fixed_pages": papers_missing_fixed_pages,
                "question_html_labels": question_html_labels,
                "used_papers": used_papers,
            }
        )

        return render(request, "Progress/scan_reassign.html", context)

    def post(self, request: HttpRequest, *, img_pk: int) -> HttpResponse:
        reassignment_data = request.POST
        mds = ManageDiscardService()

        if reassignment_data.get("assignment_type", "fixed") == "fixed":
            try:
                paper_number, page_number = reassignment_data.get(
                    "missingPaperPage", ","
                ).split(",")
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Choose paper/page</div>"""
                )
            try:
                mds.assign_discard_image_to_fixed_page(
                    request.user, img_pk, paper_number, page_number
                )
            except ValueError as e:
                return HttpResponse(
                    f"""<span class="alert alert-danger">Some sort of error: {e}</span>"""
                )
        else:
            paper_number = reassignment_data.get("usedPaper", None)

            try:
                paper_number = int(paper_number)
            except ValueError:
                return HttpResponse(
                    """<div class="alert alert-danger">Invalid paper number</div>"""
                )
            if reassignment_data.get("questionAll", "off") == "all":
                # set all the questions
                to_questions = SpecificationService.get_question_indices()
            else:
                if len(reassignment_data.get("questions", [])):
                    to_questions = [int(q) for q in reassignment_data["questions"]]
                else:
                    return HttpResponse(
                        """<span class="alert alert-danger">At least one question</span>"""
                    )
            try:
                mds.assign_discard_image_to_mobile_page(
                    request.user, img_pk, paper_number, to_questions
                )
            except ValueError as e:
                return HttpResponse(
                    f"""<span class="alert alert-danger">Some sort of error: {e}</span>"""
                )

        return HttpResponseClientRedirect(reverse("progress_scan_discard"))
