# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

import sys

if sys.version_info >= (3, 10):
    # built-in normally ok on 3.9, for some reason fails here
    from importlib import resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

import fitz

from django.core.management.base import BaseCommand, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile

from Papers.services import SpecificationService
from Preparation import useful_files_for_testing as useful_files
from ...services import StagingSpecificationService, ReferencePDFService


class Command(BaseCommand):
    """Push simple demo data to the test specification creator app.

    Also, can clear the current test specification.
    """

    help = "Create a demo test specification."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear an existing test specification.",
        )
        parser.add_argument(
            "--publicCode",
            type=int,
            help="Force the spec to use a pre-determined public code.",
        )

    def handle(self, *args, **options):
        staged_spec_service = StagingSpecificationService()
        valid_spec_service = SpecificationService()
        ref_service = ReferencePDFService()
        if options["clear"]:
            if staged_spec_service.not_empty():
                self.stdout.write("Clearing test specification...")
                staged_spec_service.clear_questions()
                ref_service.delete_pdf()
                staged_spec_service.reset_specification()

                if valid_spec_service.is_there_a_spec():
                    valid_spec_service.remove_spec()
                self.stdout.write("Test specification cleared.")
            else:
                self.stdout.write("No specification uploaded.")
        else:
            if valid_spec_service.is_there_a_spec() or staged_spec_service.not_empty():
                self.stderr.write(
                    "Test specification data already present. Run manage.py plom_demo_spec --clear to clear the current specification."
                )
            else:
                self.stdout.write("Writing test specification...")
                with open(
                    resources.files(useful_files) / "testing_test_spec.toml", "rb"
                ) as f:
                    data = tomllib.load(f)

                # extract page count and upload reference PDF
                with fitz.open(
                    resources.files(useful_files) / "test_version1.pdf"
                ) as doc:
                    n_pdf_pages = doc.page_count
                with open(
                    resources.files(useful_files) / "test_version1.pdf", "rb"
                ) as f:
                    pdf_doc = SimpleUploadedFile("spec_reference.pdf", f.read())
                # TODO: why can't it count the pages itself?
                ref_service.new_pdf(
                    staged_spec_service, "spec_reference.pdf", n_pdf_pages, pdf_doc
                )

                # verify spec, stage + save to DB
                try:
                    staged_spec_service.create_from_dict(data)
                    valid_spec = staged_spec_service.get_valid_spec_dict()

                    if options["publicCode"]:
                        code = options["publicCode"]
                        valid_spec["publicCode"] = code

                    valid_spec_service.store_validated_spec(valid_spec)
                    self.stdout.write("Demo test specification uploaded!")
                    self.stdout.write(str(valid_spec_service.get_the_spec()))
                except ValueError as e:
                    self.stderr.write(e)
                    raise CommandError(e)
