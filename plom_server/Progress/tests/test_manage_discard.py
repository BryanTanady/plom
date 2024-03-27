# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.test import TestCase
from django.contrib.auth.models import User

from model_bakery import baker

from Papers.models import (
    Image,
    FixedPage,
    MobilePage,
    Paper,
    DNMPage,
    IDPage,
    QuestionPage,
    DiscardPage,
)

from Progress.services import ManageDiscardService


class ManageScanTests(TestCase):
    """Tests for Progress.services.ManageScanService"""

    def setUp(self) -> None:
        self.user0: User = baker.make(User, username="user0")
        self.paper1 = baker.make(Paper, paper_number=1)

        return super().setUp()

    def test_discard_idpage(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        id1 = baker.make(IDPage, paper=self.paper1, page_number=1, image=img1)

        mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=False)

    def test_discard_dnm(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        dnm1 = baker.make(DNMPage, paper=self.paper1, page_number=2, image=img1)

        mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=False)

    def test_discard_questionpage(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        qp1 = baker.make(QuestionPage, paper=self.paper1, page_number=3, image=img1)

        mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=False)

    def test_discard_fixedpage_exceptions(self) -> None:
        mds = ManageDiscardService()
        fp1 = baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        fp2 = baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, 17, dry_run=False
        )
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, fp1.pk, dry_run=False
        )
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, fp2.pk, dry_run=False
        )

    def test_discard_mobile_page(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        baker.make(QuestionPage, paper=self.paper1, page_number=2, question_index=1)
        baker.make(QuestionPage, paper=self.paper1, page_number=2, question_index=2)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_index=1, image=img1)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_index=2, image=img1)

        mds.discard_pushed_mobile_page(self.user0, mp1.pk, dry_run=True)
        mds.discard_pushed_mobile_page(self.user0, mp1.pk, dry_run=False)

        self.assertRaises(
            ValueError, mds.discard_pushed_mobile_page, self.user0, 17, dry_run=False
        )

    def test_discard_image_from_pk(self) -> None:
        mds = ManageDiscardService()
        baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        # test when no such image
        self.assertRaises(ValueError, mds.discard_pushed_image_from_pk, self.user0, 17)
        # test when fixed page is not dnm, id or question page
        self.assertRaises(
            ValueError, mds.discard_pushed_image_from_pk, self.user0, img1.pk
        )

        # test when fixed page is an dnm page
        img2 = baker.make(Image)
        baker.make(DNMPage, paper=self.paper1, page_number=3, image=img2)
        mds.discard_pushed_image_from_pk(self.user0, img2.pk)
        # test when mobile page (need an associate question page)
        img3 = baker.make(Image)
        baker.make(QuestionPage, paper=self.paper1, page_number=4, question_index=1)
        baker.make(MobilePage, paper=self.paper1, question_index=1, image=img3)
        mds.discard_pushed_image_from_pk(self.user0, img3.pk)
        # test when discard page (no action required)
        img4 = baker.make(Image)
        baker.make(DiscardPage, image=img4)
        mds.discard_pushed_image_from_pk(self.user0, img4.pk)

    def test_reassign_discard_to_mobile(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        img2 = baker.make(Image)
        baker.make(DiscardPage, image=img1)
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=2,
            question_index=1,
            image=None,
        )
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=3,
            question_index=2,
            image=None,
        )

        self.assertRaises(
            ValueError, mds.assign_discard_image_to_mobile_page, self.user0, 17, 1, 1
        )
        self.assertRaises(
            ValueError,
            mds.assign_discard_image_to_mobile_page,
            self.user0,
            img2.pk,
            1,
            1,
        )
        # cannot test this completely as we don't have a qv-map
        # so this will raise a runtimeerror
        self.assertRaises(
            RuntimeError,
            mds.assign_discard_image_to_mobile_page,
            self.user0,
            img1.pk,
            1,
            [1, 2],
        )

    def test_reassign_discard_to_fixed(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        img2 = baker.make(Image)
        img3 = baker.make(Image)
        img4 = baker.make(Image)
        img5 = baker.make(Image)
        baker.make(DiscardPage, image=img1)
        baker.make(DiscardPage, image=img2)
        baker.make(DiscardPage, image=img3)
        baker.make(DiscardPage, image=img4)

        img0 = baker.make(Image)
        baker.make(
            IDPage,
            paper=self.paper1,
            page_number=1,
            image=None,
        )
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=2,
            question_index=1,
            image=img0,
        )
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=3,
            question_index=2,
            image=None,
        )
        baker.make(
            DNMPage,
            paper=self.paper1,
            page_number=4,
            image=None,
        )
        baker.make(FixedPage, paper=self.paper1, page_number=5, image=None)

        # try with non-existent image pk
        self.assertRaises(
            ValueError, mds.assign_discard_image_to_fixed_page, self.user0, 17, 1, 1
        )
        # try to assign to page which already has an image
        self.assertRaises(
            ValueError,
            mds.assign_discard_image_to_fixed_page,
            self.user0,
            img1.pk,
            1,
            2,
        )
        # now assign to a question page, will cause runtime error since we don't have a qvmap.
        self.assertRaises(
            RuntimeError,
            mds.assign_discard_image_to_fixed_page,
            self.user0,
            img1.pk,
            1,
            3,
        )
        # and an ID-page
        mds.assign_discard_image_to_fixed_page(self.user0, img2.pk, 1, 1)
        # and a DNM-page
        mds.assign_discard_image_to_fixed_page(self.user0, img3.pk, 1, 4)
        # and this should raise an exception since the fixed page is not a Q,ID or DNM-page
        self.assertRaises(
            RuntimeError,
            mds.assign_discard_image_to_fixed_page,
            self.user0,
            img4.pk,
            1,
            5,
        )
        # try to assign an image that is not attached to a discard page
        self.assertRaises(
            ValueError,
            mds.assign_discard_image_to_fixed_page,
            self.user0,
            img5.pk,
            1,
            2,
        )

    def test_some_reassign_exceptions(self) -> None:
        mds = ManageDiscardService()
        # test non-existent discardpage
        self.assertRaises(
            ValueError, mds._assign_discard_to_fixed_page, self.user0, 17, 1, 1
        )
        self.assertRaises(
            ValueError, mds._assign_discard_to_mobile_page, self.user0, 17, 1, 1
        )
        dp1 = baker.make(DiscardPage)
        # test non-existent paper
        self.assertRaises(
            ValueError, mds._assign_discard_to_fixed_page, self.user0, dp1.pk, 101, 1
        )
        self.assertRaises(
            ValueError, mds._assign_discard_to_mobile_page, self.user0, dp1.pk, 101, 1
        )
        # test non-existent fp.
        self.assertRaises(
            ValueError, mds._assign_discard_to_fixed_page, self.user0, dp1.pk, 1, 1
        )
