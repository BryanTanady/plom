# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.http import HttpResponse, Http404, FileResponse, HttpRequest

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService, PaperInfoService
from ..services import ScanService


class GetBundleImageView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request: HttpResponse, *, bundle_id: int, index: int) -> HttpResponse:
        scanner = ScanService()
        image = scanner.get_image(bundle_id, index)

        return FileResponse(image.image_file)


class BundleThumbnailsView(ScannerRequiredView):
    def filter_bundle_pages(self, page_list, filter_kind):
        def is_extra_without_info(page):
            if page["status"] == "extra":
                # is an extra page with both page number and question list
                if page["info"]["paper_number"] and page["info"]["question_list"]:
                    return False
                else:  # is an extra page without its info
                    return True
            else:  # is not an extra page
                return False

        if filter_kind in ["known", "unknown", "error", "extra", "discard", "unread"]:
            return [pg for pg in page_list if pg["status"] == filter_kind]
        elif filter_kind == "lowqr":
            return [pg for pg in page_list if pg["n_qr_read"] <= 2]
        elif filter_kind == "attn":
            # need unknowns, errors and extras without info
            return [
                pg
                for pg in page_list
                if is_extra_without_info(pg) or pg["status"] in ["unknown", "error"]
            ]
        elif filter_kind == "ex_no_info":
            return [pg for pg in page_list if is_extra_without_info(pg)]
        else:
            return page_list

    def build_context(
        self, *, bundle_id: int | None = None, the_filter: str | None = None
    ) -> dict[str, Any]:
        """Build a context for a particular page of a bundle.

        Keyword Args:
            bundle_id: which bundle.
            the_filter: related to the current filter.
        """
        # TODO: not clear if superclass forbids this?
        assert bundle_id is not None, "bundle_id must be specified (?)"

        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_pages = scanner.get_n_images(bundle)
        known_pages = scanner.get_n_known_images(bundle)
        unknown_pages = scanner.get_n_unknown_images(bundle)
        extra_pages = scanner.get_n_extra_images(bundle)
        discard_pages = scanner.get_n_discard_images(bundle)
        error_pages = scanner.get_n_error_images(bundle)

        # list of dicts of page info, in bundle order
        # filter this according to 'the_filter'
        bundle_page_info_list = self.filter_bundle_pages(
            scanner.get_bundle_pages_info_list(bundle), the_filter
        )
        # and get an ordered list of papers in the bundle and info about the pages for each paper that are in this bundle.
        bundle_papers_pages_list = scanner.get_bundle_papers_pages_list(bundle)
        # get a list of the paper-numbers in bundle that are missing pages
        bundle_incomplete_papers_list = [
            X[0] for X in scanner.get_bundle_missing_paper_page_numbers(bundle)
        ]

        filter_options = [
            {"filter_code": X[0], "filter_name": X[1]}
            for X in [
                ("all", "all"),
                ("attn", "needs your attention"),
                ("known", "known pages"),
                ("extra", "extra pages"),
                ("ex_no_info", "extra pages without information"),
                ("error", "errors"),
                ("lowqr", "few qr codes read"),
                ("discard", "discarded pages"),
                ("unknown", "unknown pages"),
                ("unread", "unread pages"),
            ]
        ]

        context.update(
            {
                "is_pushed": bundle.pushed,
                "slug": bundle.slug,
                "bundle_id": bundle.pk,
                "timestamp": bundle.timestamp,
                "pages": bundle_page_info_list,
                "papers_pages_list": bundle_papers_pages_list,
                "incomplete_papers_list": bundle_incomplete_papers_list,
                "total_pages": n_pages,
                "known_pages": known_pages,
                "unknown_pages": unknown_pages,
                "extra_pages": extra_pages,
                "discard_pages": discard_pages,
                "error_pages": error_pages,
                "finished_reading_qr": bundle.has_qr_codes,
                "the_filter": the_filter,
                "filter_options": filter_options,
            }
        )
        return context

    def get(
        self, request: HttpRequest, *, the_filter: str, bundle_id: int
    ) -> HttpResponse:
        """Get a page of thumbnails with manipulations options for a bundle.

        Args:
            request: incoming request.

        Keyword Args:
            the_filter: which filter to apply to the images.
            bundle_id: which bundle.

        Returns:
            The response returns a template-rendered page.
            If there was no such bundle, return a 404 error page.
        """
        try:
            context = self.build_context(bundle_id=bundle_id, the_filter=the_filter)
        except ObjectDoesNotExist as e:
            raise Http404(e)

        # to pop up the same image we were just at
        context.update({"pop": request.GET.get("pop", None)})
        return render(request, "Scan/bundle_thumbnails.html", context)


class GetBundleThumbnailView(ScannerRequiredView):
    """Return an image from a user-uploaded bundle."""

    def get(self, request: HttpRequest, *, bundle_id: int, index: int) -> HttpResponse:
        """Get a thumbnail view for a particular position in a bundle.

        Args:
            request: incoming request.

        Keyword Args:
            bundle_id: which bundle.
            index: which index within the bundle.

        Returns:
            The response returns the file when everything was successful.
            If there was no such bundle or no such index within the
            bundle, we get a 404 error.
        """
        scanner = ScanService()
        try:
            image = scanner.get_thumbnail_image(bundle_id, index)
        except ObjectDoesNotExist as e:
            raise Http404(e)
        return FileResponse(image.image_file)


class GetBundlePageFragmentView(ScannerRequiredView):
    """Return the image display fragment from a user-uploaded bundle."""

    def get(
        self, request: HttpResponse, *, the_filter: str, bundle_id: int, index: int
    ) -> HttpResponse:
        context = super().build_context()
        scanner = ScanService()
        paper_info = PaperInfoService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_pages = scanner.get_n_images(bundle)

        if index < 0 or index > n_pages:
            raise Http404("Bundle page does not exist.")

        current_page = scanner.get_bundle_single_page_info(bundle, index)
        context.update(
            {
                "is_pushed": bundle.pushed,
                "is_push_locked": bundle.is_push_locked,
                "slug": bundle.slug,
                "bundle_id": bundle.pk,
                "timestamp": bundle.timestamp,
                "index": index,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
                "current_page": current_page,
                "the_filter": the_filter,
            }
        )
        # If page is an extra page then we grab some data for the
        # set-extra-page-info form stuff
        if current_page["status"] == "extra":
            question_labels_html = (
                SpecificationService.get_question_html_label_triples()
            )
            paper_numbers = scanner.get_bundle_paper_numbers(bundle)
            all_paper_numbers = paper_info.which_papers_in_database()
            context.update(
                {
                    "question_labels_html": question_labels_html,
                    "bundle_paper_numbers": paper_numbers,
                    "all_paper_numbers": all_paper_numbers,
                }
            )

        return render(request, "Scan/fragments/bundle_page_view.html", context)


class BundleLockView(ScannerRequiredView):
    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug})
        return render(request, "Scan/bundle_is_locked.html", context)
