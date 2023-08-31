# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

import sys

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

from Base.tests import config_test, ConfigTestCase
from Papers.models import Paper
from Mark.models import MarkingTaskPriority, MarkingTask
from Mark.services import marking_priority, MarkingTaskService
from TaskOrder.services.task_ordering_service import TaskOrderService

from . import config_files


class MarkingTaskPriorityTests(ConfigTestCase):
    """Tests for marking task priority."""

    config_file = resources.files(config_files) / "priority_tests.toml"

    def test_taskorder_update(self):
        """Assert that TaskOrderService.update_priority_ordering() updates MarkingTaskPriority."""

        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

        tos = TaskOrderService()
        tos.update_priority_ordering("shuffle")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.SHUFFLE)

        custom_priority = {(1, 1): 1}
        tos.update_priority_ordering("custom", custom_order=custom_priority)
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.CUSTOM)

        tos.update_priority_ordering("papernum")
        strategy = MarkingTaskPriority.load().strategy
        self.assertEqual(strategy, MarkingTaskPriority.PAPER_NUMBER)

    def test_set_priority_papernum(self):
        """Test that PAPER_NUMBER is the default strategy."""

        n_papers = Paper.objects.count()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)

        marking_priority.set_marking_priority_paper_number()
        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)

        self.assertEqual(
            marking_priority.get_mark_priority_strategy(),
            MarkingTaskPriority.PAPER_NUMBER,
        )

    def test_set_priority_shuffle(self):
        """Test setting priority to SHUFFLE."""

        marking_priority.set_marking_piority_shuffle()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        for task in tasks:
            self.assertTrue(
                task.marking_priority <= 1000 and task.marking_priority >= 0
            )

        self.assertEqual(
            marking_priority.get_mark_priority_strategy(), MarkingTaskPriority.SHUFFLE
        )

    def test_set_priority_custom(self):
        """Test setting priority to CUSTOM."""

        custom_order = {(1, 1): 9, (2, 1): 356, (3, 2): 0}
        marking_priority.set_marking_priority_custom(custom_order)

        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        n_papers = Paper.objects.count()
        for task in tasks:
            task_key = (task.paper.paper_number, task.question_number)
            if task_key in custom_order.keys():
                self.assertEqual(task.marking_priority, custom_order[task_key])
            else:
                self.assertEqual(
                    task.marking_priority, n_papers - task.paper.paper_number
                )

        self.assertEqual(
            marking_priority.get_mark_priority_strategy(), MarkingTaskPriority.CUSTOM
        )

    def test_modify_priority(self):
        """Test modifying the priority of a single task."""
        n_papers = Paper.objects.count()
        mts = MarkingTaskService()
        tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO).prefetch_related(
            "paper"
        )
        first_task = tasks.get(paper__paper_number=1, question_number=1)
        last_task = tasks.get(paper__paper_number=5, question_number=2)

        for task in tasks:
            self.assertEqual(task.marking_priority, n_papers - task.paper.paper_number)
        self.assertEqual(mts.get_first_available_task(), first_task)
        self.assertEqual(
            marking_priority.get_mark_priority_strategy(),
            MarkingTaskPriority.PAPER_NUMBER,
        )
        self.assertFalse(marking_priority.is_priority_modified())

        marking_priority.modify_task_priority(last_task, 1000)
        last_task.refresh_from_db()
        for task in tasks.all():
            if task == last_task:
                self.assertEqual(task.marking_priority, 1000)
            else:
                self.assertEqual(
                    task.marking_priority, n_papers - task.paper.paper_number
                )
        self.assertEqual(mts.get_first_available_task(), last_task)
        self.assertEqual(
            marking_priority.get_mark_priority_strategy(),
            MarkingTaskPriority.PAPER_NUMBER,
        )
        self.assertTrue(marking_priority.is_priority_modified())
