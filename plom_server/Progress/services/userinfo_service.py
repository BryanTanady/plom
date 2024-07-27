# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady


from datetime import timedelta
from typing import Dict, Tuple, Union, Any

import arrow

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils import timezone

from Mark.models import Annotation, MarkingTask
from Mark.services import MarkingTaskService, MarkingStatsService

from UserManagement.models import ProbationPeriod


class UserInfoServices:
    """Functions for User Info HTML page."""

    @transaction.atomic
    def get_user_progress(self, username: str) -> Dict[str, Any]:
        """Get marking progress of a user.

        Args:
            username: the user's username.

        Returns:
            A dict whose keys are ["task_claimed", "task_marked", "in_probation", "probation_limit"].
        """
        complete_claimed_task_dict = (
            self.get_total_annotated_and_claimed_count_based_on_user()
        )
        task_marked, task_claimed = complete_claimed_task_dict[username]
        user = User.objects.get(username=username)
        in_probation = ProbationPeriod.objects.filter(user=user).exists()
        if in_probation:
            probation_limit = ProbationPeriod.objects.get(user=user).limit
        else:
            probation_limit = None

        data = {
            "task_claimed": task_claimed,
            "task_marked": task_marked,
            "in_probation": in_probation,
            "probation_limit": probation_limit,
        }
        return data

    @transaction.atomic
    def annotation_exists(self) -> bool:
        """Return True if there are any annotations in the database.

        Returns:
            True if there are annotations or False if there aren't any.
        """
        return Annotation.objects.exists()

    @transaction.atomic
    def get_total_annotated_and_claimed_count_based_on_user(
        self,
    ) -> Dict[str, Tuple[int, int]]:
        """Retrieve count of complete and total claimed tas based on user.

        claimed tasks are those tasks associated with the user with status OUT and Complete.

        Returns:
            A dictionary mapping the marker to a tuple of the count of the complete and claimed tasks.

        Raises:
            Not expected to raise any exceptions.
        """
        result = dict()

        annotations = (
            MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
        )
        markers_and_managers = User.objects.filter(
            groups__name__in=["marker"]
        ).order_by("groups__name", "username")
        annotation_count_dict: Dict[str, int] = {
            user.username: 0 for user in markers_and_managers
        }

        for annotation in annotations:
            if annotation.user.username in annotation_count_dict:
                annotation_count_dict[annotation.user.username] += 1

        for usr in annotation_count_dict:
            complete_task = annotation_count_dict[usr]
            claimed_task = (
                complete_task + self.get_total_claimed_but_unmarked_task_by_a_user(usr)
            )
            result[usr] = (complete_task, claimed_task)

        return result

    @transaction.atomic
    def get_total_claimed_task_for_each_user(self) -> Dict[str, int]:
        """Retrieve the number of tasks claimed by the user."""
        total_complete_annot_dict = self.get_annotations_based_on_user()
        claimed_task_count_dict = dict()

        for usr in total_complete_annot_dict.key():
            claimed_task_count_dict[usr] = total_complete_annot_dict[
                usr
            ] + self.get_total_claimed_but_unmarked_task_by_a_user(usr)

        return claimed_task_count_dict

    @transaction.atomic
    def get_total_claimed_but_unmarked_task_by_a_user(self, username: str) -> int:
        """Retrieve the number of tasks claimed but unmarked by a user.

        These retrieve the tasks claimed by the users that have MarkingTask status of OUT.

        Args:
            username: user's username

        Returns:
            number of tasks claimed by the user whose status is still 'OUT'.
        """
        return len(
            MarkingStatsService().filter_marking_task_annotation_info(
                username=username, status=MarkingTask.OUT
            )
        )

    @transaction.atomic
    def get_annotations_based_on_user(
        self, annotations
    ) -> Dict[str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]]:
        """Retrieve annotations based on the combination of user, question index, and version.

        Returns:
            A dictionary with usernames as keys, and nested dictionaries
            as values containing the count of annotations and average
            marking time for each (question index, question version)
            combination.
        """
        count_data: Dict[str, Dict[Tuple[int, int], int]] = dict()
        total_marking_time_data: Dict[str, Dict[Tuple[int, int], int]] = dict()

        for annotation in annotations:
            key = (annotation.task.question_index, annotation.task.question_version)
            count_data.setdefault(annotation.user.username, {}).setdefault(key, 0)
            count_data[annotation.user.username][key] += 1

            total_marking_time_data.setdefault(annotation.user.username, {}).setdefault(
                key, 0
            )
            total_marking_time_data[annotation.user.username][
                key
            ] += annotation.marking_time

        grouped_by_user: Dict[
            str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]
        ] = dict()

        for user in count_data:
            grouped_by_user[user] = dict()
            for key in count_data[user]:
                count = count_data[user][key]
                total_marking_time = total_marking_time_data[user][key]

                if total_marking_time is None:
                    total_marking_time = 0

                average_marking_time = round(
                    total_marking_time / count if count > 0 else 0
                )

                grouped_by_user[user][key] = {
                    "annotations_count": count,
                    "average_marking_time": self.seconds_to_humanize_time(
                        average_marking_time
                    ),
                    "percentage_marked": int(
                        (
                            count
                            / self._get_marking_task_count_based_on_question_and_version(
                                question=key[0], version=key[1]
                            )
                        )
                        * 100
                    ),
                    "date_format": arrow.utcnow()
                    .shift(seconds=average_marking_time)
                    .format("YYYYMMDDHHmmss"),
                }

        return grouped_by_user

    def get_annotations_based_on_question_and_version(
        self,
        grouped_by_user_annotations: Dict[
            str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]
        ],
    ) -> Dict[Tuple[int, int], Dict[str, list]]:
        """Group annotations by question index and version.

        Args:
            grouped_by_user_annotations: A dictionary with usernames as keys,
                and nested dictionaries as values containing the count
                of annotations and average marking time for each
                (question_index, question_version) combination.

        Returns:
            A dictionary containing annotations grouped by
            question indices and versions, with marker information and
            other data.
        """
        grouped_by_question: Dict[Tuple[int, int], Dict[str, list]] = dict()

        for marker, annotation_data in grouped_by_user_annotations.items():
            for question, question_data in annotation_data.items():
                if question not in grouped_by_question:
                    grouped_by_question[question] = {
                        "annotations": [],
                    }
                grouped_by_question[question]["annotations"].append(
                    {
                        "marker": marker,
                        "annotations_count": question_data["annotations_count"],
                        "average_marking_time": question_data["average_marking_time"],
                        "percentage_marked": question_data["percentage_marked"],
                        "date_format": question_data["date_format"],
                    }
                )

        return grouped_by_question

    def seconds_to_humanize_time(self, seconds: float) -> str:
        """Convert the given number of seconds to a human-readable time string.

        Args:
            seconds: the number of seconds, unsigned so no distinction
                is made between past and future.

        Returns:
            A human-readable time string.
        """
        if seconds > 9:
            return arrow.utcnow().shift(seconds=seconds).humanize(only_distance=True)
        else:
            return (
                arrow.utcnow()
                .shift(seconds=seconds)
                .humanize(only_distance=True, granularity=["second"])
            )

    @transaction.atomic
    def _get_marking_task_count_based_on_question_and_version(
        self, question: int, version: int
    ) -> int:
        """Get the count of MarkingTasks based on the given question index and version.

        Args:
            question: which question by 1-based index.
            version: which question version.

        Returns:
            The count of MarkingTask for the specific question index and version.
        """
        return MarkingTask.objects.filter(
            question_index=question, question_version=version
        ).count()

    @transaction.atomic
    def filter_annotations_by_time_delta_seconds(
        self, time_delta_seconds: int
    ) -> QuerySet[Annotation]:
        """Filter annotations by time in seconds.

        Args:
            time_delta_seconds: (int) Number of seconds.

        Returns:
            QuerySet: Filtered queryset of annotations.
        """
        annotations = (
            MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
        )

        if time_delta_seconds == 0:
            return annotations
        else:
            time_interval_start = timezone.now() - timedelta(seconds=time_delta_seconds)
            return annotations.filter(time_of_last_update__gte=time_interval_start)

    @transaction.atomic
    def get_time_of_latest_updated_annotation(self) -> str:
        """Get the human readable time of the latest updated annotation.

        Returns:
            Human-readable time of the latest updated annotation or
            the string ``"never"`` if there have not been any annotations.
        """
        try:
            annotations = (
                MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
            )
            latest_annotation = annotations.latest("time_of_last_update")
        except ObjectDoesNotExist:
            return "never"
        return arrow.get(latest_annotation.time_of_last_update).humanize()
