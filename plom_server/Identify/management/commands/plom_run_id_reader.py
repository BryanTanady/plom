# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import MultipleObjectsReturned

from Identify.services import IDReaderService
from Rectangles.services import RectangleExtractor
from Papers.services import SpecificationService

from time import sleep


class Command(BaseCommand):
    """Commandline tool for running and managing the results of the ID-reader."""

    def get_the_rectangle(self):
        id_page_number = SpecificationService.get_id_page_number()
        rex = RectangleExtractor(1, id_page_number)
        # note that this rectangle is stated [0,1] coords relative to qr-code positions
        region = None  # we are not specifying a region to search.
        initial_rectangle = rex.get_largest_rectangle_contour(region)
        self.stdout.write(f"Found id box rectangle at = {initial_rectangle}")
        return initial_rectangle

    def run_the_reader(self, user_obj, rectangle):
        try:
            self.stdout.write("Running the ID reader")
            IDReaderService().run_the_id_reader_in_background_via_huey(
                user_obj,
                (
                    rectangle["left_f"],
                    rectangle["top_f"],
                    rectangle["right_f"],
                    rectangle["bottom_f"],
                ),
                recompute_heatmap=True,
            )
        except MultipleObjectsReturned:
            raise CommandError("The ID reader is already running.")

    def delete_ID_predictions(self):
        self.stdout.write("Deleting all MLLAP and MLGreedy ID predictions.")
        IDReaderService().delete_ID_predictions("MLLAP")
        IDReaderService().delete_ID_predictions("MLGreedy")

    def wait_for_reader(self):
        self.stdout.write("Waiting for any ID reader processes to finish")
        while True:
            status = IDReaderService().get_id_reader_background_task_status()
            self.stdout.write(f"Status = {status['status']}: {status['message']}")
            if status["status"] in ["Starting", "Queued", "Running"]:
                self.stdout.write("Waiting....")
                sleep(2)
            else:
                break

    def add_arguments(self, parser):
        parser.add_argument(
            "--rectangle", action="store_true", help="Just get the ID-box rectangle"
        )
        parser.add_argument("--run", action="store_true", help="Run the ID-reader")
        parser.add_argument(
            "--delete", action="store_true", help="Delete any predictions"
        )
        parser.add_argument(
            "--wait", action="store_true", help="Wait for any running ID-reader process"
        )

    def handle(self, *args, **kwargs):
        username = "manager"  # TODO - replace with general option for username
        # Fetch the user object based on the username
        User = get_user_model()
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        if kwargs["rectangle"]:
            the_id_box_rectangle = self.get_the_rectangle()
        elif kwargs["run"]:
            the_id_box_rectangle = self.get_the_rectangle()
            self.run_the_reader(user_obj, the_id_box_rectangle)
        elif kwargs["wait"]:
            self.wait_for_reader()
        elif kwargs["delete"]:
            self.delete_ID_predictions()
        else:
            self.print_help("manage.py", "plom_run_id_reader")
