# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

import arrow
from collections import defaultdict
from datetime import timedelta
from typing import Dict, Tuple, Union

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum

from Mark.models import Annotation
from Mark.services import MarkingTaskService


class UserInfoServices:
    """Functions for User Info HTML page."""

    @transaction.atomic
    def annotation_exists(self) -> bool:
        """Return True if there are any annotations in the database.

        Returns:
            bool : True if there are annotations or
                False if there aren't any
        """
        return Annotation.objects.exists()

    @transaction.atomic
    def get_total_annotations_based_on_user(self) -> Dict[str, int]:
        """Retrieve annotations based on user.

        Returns:
            Dict[str, int]: A dictionary of all annotations(Value) corresponding with the markers(key).

        Raises:
            Not expected to raise any exceptions.
        """
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

        return annotation_count_dict

    @transaction.atomic
    def get_annotations_based_on_user_and_question_number_version(
        self,
    ) -> Dict[str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]]:
        """Retrieve annotations based on the combination of user, question number, and version.

        Returns a dictionary with users as keys and nested dictionaries as values.
        The nested dictionaries have a tuple (question_number, question_version) as keys
        and the count of annotations and average marking time as values.

        Returns:
            Dict[str, Dict[Tuple[int, int], Dict[str, Union(int, str)]]]: A dictionary with users
                as keys, and nested dictionaries as values containing the count of annotations
                and average marking time for each (question_number, question_version) combination.
        """
        annotations = (
            MarkingTaskService().get_latest_annotations_from_complete_marking_tasks()
        )
        count_data: Dict[str, Dict[Tuple[int, int], int]] = dict()
        total_marking_time_data: Dict[str, Dict[Tuple[int, int], int]] = dict()

        for annotation in annotations:
            key = (annotation.task.question_number, annotation.task.question_version)
            count_data.setdefault(annotation.user.username, {}).setdefault(key, 0)
            count_data[annotation.user.username][key] += 1

            total_marking_time_data.setdefault(annotation.user.username, {}).setdefault(
                key, 0
            )
            total_marking_time_data[annotation.user.username][
                key
            ] += annotation.marking_time

        grouped_annotations: Dict[
            str, Dict[Tuple[int, int], Dict[str, Union[int, str]]]
        ] = dict()
        present = arrow.utcnow()

        for user in count_data:
            grouped_annotations[user] = dict()
            for key in count_data[user]:
                count = count_data[user][key]
                total_marking_time = total_marking_time_data[user][key]

                if total_marking_time is None:
                    total_marking_time = 0

                average_marking_time = total_marking_time / count if count > 0 else 0

                if average_marking_time <= 60:
                    grouped_annotations[user][key] = {
                        "annotations_count": count,
                        "average_marking_time": present.shift(
                            seconds=average_marking_time
                        ).humanize(present, only_distance=True, granularity=["second"]),
                    }
                else:
                    grouped_annotations[user][key] = {
                        "annotations_count": count,
                        "average_marking_time": present.shift(
                            seconds=average_marking_time
                        ).humanize(
                            present,
                            only_distance=True,
                            granularity=["minute", "second"],
                        ),
                    }

        return grouped_annotations
