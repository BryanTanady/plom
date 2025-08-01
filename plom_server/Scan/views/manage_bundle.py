# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Philip D. Loewen

from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404, FileResponse, HttpRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from plom_server.Base.base_group_views import ScannerRequiredView
from plom_server.Papers.services import SpecificationService, PaperInfoService
from ..services import ScanService

from plom.misc_utils import format_int_list_with_runs


class BundleThumbnailsView(ScannerRequiredView):
    """Handles the creation and perhaps some of the interaction with a page of thumbnails of a bundle."""

    def filter_bundle_pages(
        self, page_list: list[dict[str, Any]], filter_kind: str | None
    ) -> list[dict[str, Any]]:
        def is_extra_without_info(page):
            if page["status"] == "extra":
                # is an extra page with page number
                if page["info"]["paper_number"]:
                    return False
                else:  # is an extra page without its info
                    return True
            else:  # is not an extra page
                return False

        if filter_kind is None:
            return page_list
        elif filter_kind in ["known", "unknown", "error", "extra", "discard", "unread"]:
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
        self,
        *,
        bundle_id: int | None = None,
        the_filter: str | None = None,
        pop: int | None = None,
    ) -> dict[str, Any]:
        """Build a context for a particular page of a bundle.

        Keyword Args:
            bundle_id: which bundle.
            the_filter: related to the current filter.
            pop: the index of the page to focus on
        """
        # TODO: not clear if superclass forbids this?
        assert bundle_id is not None, "bundle_id must be specified (?)"

        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_pages = scanner.get_n_images(bundle)
        known_pages = scanner.get_n_known_images(bundle)
        unread_pages = scanner.get_n_unread_images(bundle)
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
        bundle_colliding_images = scanner.get_bundle_colliding_images(bundle)

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
                "is_perfect": scanner.is_bundle_perfect(bundle.pk),
                "slug": bundle.slug,
                "bundle_id": bundle.pk,
                "timestamp": bundle.timestamp,
                "pages": bundle_page_info_list,
                "papers_pages_list": bundle_papers_pages_list,
                "incomplete_papers_list": bundle_incomplete_papers_list,
                "n_incomplete": len(bundle_incomplete_papers_list),
                "colliding_image_orders": bundle_colliding_images,
                "colliding_images_nice_format": format_int_list_with_runs(
                    bundle_colliding_images
                ),
                "n_collisions": len(bundle_colliding_images),
                "total_pages": n_pages,
                "known_pages": known_pages,
                "unread_pages": unread_pages,
                "unknown_pages": unknown_pages,
                "extra_pages": extra_pages,
                "discard_pages": discard_pages,
                "error_pages": error_pages,
                "has_page_images": bundle.has_page_images,
                "finished_reading_qr": bundle.has_qr_codes,
                "the_filter": the_filter,
                "filter_options": filter_options,
            }
        )
        if pop in [pg["order"] for pg in bundle_page_info_list]:
            context.update({"pop": pop})
        else:
            # pop the first image in the list
            if pop and bundle_page_info_list:
                context.update({"pop": bundle_page_info_list[0]["order"]})
            # otherwise don't pop anything.
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
            Note if the url has a pop-query then check if that
            page passes the filter, and if not then pop the first
            page that does pass the filter.
        """
        # to pop up the same image we were just at
        # provided that the image satisfies the current filter.
        pop = request.GET.get("pop", None)
        try:
            context = self.build_context(
                bundle_id=bundle_id, the_filter=the_filter, pop=pop
            )
        except ObjectDoesNotExist as e:
            raise Http404(e)

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
        # note - is a thumbnail - so we don't need the baseimage here.
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
    """Display an error message that a bundle is locked."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug, "bundle_id": bundle_id})
        reasons = [f"{msg}" for msg in messages.get_messages(request)]
        context.update({"reasons": reasons})
        return render(request, "Scan/bundle_is_locked.html", context)


class BundlePushCollisionView(ScannerRequiredView):
    """Display an error message that a collision was detected during push."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug, "bundle_id": bundle_id})
        reasons = [f"{msg}" for msg in messages.get_messages(request)]
        context.update({"reasons": reasons})
        return render(request, "Scan/bundle_push_collision.html", context)


class BundlePushBadErrorView(ScannerRequiredView):
    """Display an error message that something unexpected happened during push."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        context = self.build_context()
        bundle = ScanService().get_bundle_from_pk(bundle_id)
        context.update({"slug": bundle.slug, "bundle_id": bundle_id})
        reasons = [f"{msg}" for msg in messages.get_messages(request)]
        context.update({"reasons": reasons})
        return render(request, "Scan/bundle_push_bad_error.html", context)


class RecentStagedBundleRedirectView(ScannerRequiredView):
    """Handle a redirection, either to the newest unpushed bundle or the overall list."""

    def get(self, request: HttpResponse) -> HttpResponse:
        bundle = ScanService().get_most_recent_unpushed_bundle()
        if bundle is None:
            return redirect(reverse("scan_list_staged"))
        else:
            return redirect(reverse("scan_bundle_thumbnails", args=["all", bundle.pk]))
