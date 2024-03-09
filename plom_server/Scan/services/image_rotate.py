# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer

from __future__ import annotations
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from ..models import StagingBundle, StagingImage
from .util import check_bundle_object_is_neither_locked_nor_pushed
from .util import update_thumbnail_after_rotation


class ImageRotateService:
    @transaction.atomic
    def rotate_image_from_bundle_pk_and_order(
        self,
        bundle_id: int,
        bundle_order: int,
        angle: int,
    ) -> None:
        """A wrapper around rotate_image_cmd.

        Args:
            bundle_id: (int) The pk of the bundle.
            bundle_order: (int) Bundle order of a page.

        Returns:
            None.

        Raises:
            PlomBundleLockedException: when the bundle is pushed or push-locked
            ValueError: when no image at that order in the bundle
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_id)

        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            staging_img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        self._rotate_image(staging_img.pk, angle)

    @transaction.atomic
    def rotate_image_cmd(
        self, username: str, bundle_name: str, bundle_order: int
    ) -> None:
        try:
            User.objects.get(
                username__iexact=username, groups__name__in=["scanner", "manager"]
            )
        except ObjectDoesNotExist:
            raise PermissionError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        check_bundle_object_is_neither_locked_nor_pushed(bundle_obj)

        try:
            staging_img = bundle_obj.stagingimage_set.get(bundle_order=bundle_order)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find an image at order {bundle_order}")

        self._rotate_image(staging_img.pk, angle=-90)

    @transaction.atomic
    def _rotate_image(self, staging_img_pk: int, angle: int, **kwargs: Any) -> None:
        try:
            staging_img = StagingImage.objects.get(pk=staging_img_pk)
        except ObjectDoesNotExist:
            raise ValueError(
                f"Cannot find an image with this pk value {staging_img_pk}"
            )

        # Rotating by 90 = counter-clockwise
        # Rotating by -90 = clockwise
        if staging_img.rotation is None:
            # if rotation has not been set yet,
            # define absolute angle
            staging_img.rotation = angle
        else:
            # otherwise append to existing angle in DB
            staging_img.rotation += angle

        # keep it in [0, 360)
        staging_img.rotation %= 360
        staging_img.save()

        update_thumbnail_after_rotation(staging_img, angle)
