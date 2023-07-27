# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import models
from django.contrib.auth.models import User

from Base.models import BaseTask, BaseAction
from Papers.models import Paper


class PaperIDTask(BaseTask):
    """Represents a test-paper that needs to be identified."""

    paper = models.OneToOneField(Paper, on_delete=models.CASCADE)
    latest_action = models.OneToOneField(
        "PaperIDAction", unique=True, null=True, on_delete=models.SET_NULL
    )


class PaperIDAction(BaseAction):
    """Represents an identification of a test-paper."""

    is_valid = models.BooleanField(default=True)
    student_name = models.TextField(default="")
    student_id = models.TextField(default="")


class IDPrediction(models.Model):
    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    student_id = models.CharField(null=True, max_length=255)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    predictor = models.CharField(null=False, max_length=255)
    certainty = models.FloatField(null=False, default=0.0)
