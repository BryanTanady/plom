# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.contrib.auth.models import User
from django.db import transaction

from Papers.models import Paper
from ..services import IdentifyTaskService


class IDDirectService:
    """Functions for Identify (directly) uploads - typically for homework."""

    @transaction.atomic
    def identify_direct(
        self, user_obj: User, paper_number: int, student_id: str, student_name: str
    ):
        """Identify directly a given paper with as the student id and name.

        Args:
            user_obj: The user doing the identifying
            paper_number: which paper to id
            student_id: the student's id
            student_name: the student's name

        Raises:
            RuntimeError: no such paper, or paper already claimed, or paper already ID'd.
        """
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Cannot find paper with number {paper_number}")

        its = IdentifyTaskService()
        # set any previous id-ing as out of date and create a new task
        its.create_task(paper_obj)
        # then claim it for the user and id it with the provided data
        its.claim_task(user_obj, paper_number)
        its.identify_paper(user_obj, paper_number, student_id, student_name)

    def identify_direct_cmd(
        self, username: str, paper_number: int, student_id: str, student_name: str
    ):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except User.DoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            ) from e

        self.identify_direct(user_obj, paper_number, student_id, student_name)
