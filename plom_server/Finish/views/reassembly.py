# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.shortcuts import render
from django.http import FileResponse, StreamingHttpResponse
from django.urls import reverse
from django.utils.text import slugify

from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from Papers.services import SpecificationService
from ..services import ReassembleService


class ReassemblePapersView(ManagerRequiredView):
    def get(self, request):
        # Note: uses the symbolic constants defined in HueyTaskTracker
        reas = ReassembleService()
        context = self.build_context()
        all_paper_status = reas.get_all_paper_status_for_reassembly()
        # Compute some counts required for the page
        n_papers = sum([1 for x in all_paper_status if x["scanned"]])
        n_not_ready = sum(
            [
                1
                for x in all_paper_status
                if x["scanned"] and not (x["identified"] and x["marked"])
            ]
        )
        n_ready = sum(
            [
                1
                for x in all_paper_status
                if x["identified"]
                and x["marked"]
                and x["reassembled_status"] == "To Do"
            ]
        )
        n_outdated = sum([1 for x in all_paper_status if x["outdated"]])
        n_queued = sum(
            [
                1
                for x in all_paper_status
                if x["reassembled_status"] in ("Starting", "Queued", "Running")
            ]
        )  # for display purposes started === queued
        n_errors = sum(
            [1 for x in all_paper_status if x["reassembled_status"] == "Error"]
        )
        n_complete = sum(
            [1 for x in all_paper_status if x["reassembled_status"] == "Complete"]
        )

        context.update(
            {
                "papers": all_paper_status,
                "n_papers": n_papers,
                "n_not_ready": n_not_ready,
                "n_ready": n_ready,
                "n_outdated": n_outdated,
                "n_errors": n_errors,
                "n_complete": n_complete,
                "n_queued": n_queued,
            }
        )
        return render(request, "Finish/reassemble_paper_pdfs.html", context=context)


class StartOneReassembly(ManagerRequiredView):
    def post(self, request, paper_number):
        ReassembleService().queue_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def delete(self, request, paper_number):
        ReassembleService().reset_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def get(self, request, paper_number):
        pdf_file = ReassembleService().get_single_reassembled_file(paper_number)
        return FileResponse(pdf_file)

    def put(self, request, paper_number):  # called by "re-reassemble"
        ReassembleService().reset_single_paper_reassembly(paper_number)
        ReassembleService().queue_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))


class StartAllReassembly(ManagerRequiredView):
    def post(self, request):
        ReassembleService().queue_all_paper_reassembly()
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def delete(self, request):
        ReassembleService().reset_all_paper_reassembly()
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def get(self, request):
        # using zipfly python package.  see django example here
        # https://github.com/sandes/zipfly/blob/master/examples/streaming_django.py
        short_name = slugify(SpecificationService.get_shortname())
        zgen = ReassembleService().get_zipfly_generator(short_name)
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = (
            f"attachment; filename={short_name}_reassembled.zip"
        )
        return response


class CancelQueuedReassembly(ManagerRequiredView):
    def delete(self, request):
        ReassembleService().try_to_cancel_all_queued_chores()
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))
