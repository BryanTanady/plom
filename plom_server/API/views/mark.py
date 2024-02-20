# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse

from Finish.services import SolnImageService
from Mark.services import mark_task
from Mark.services import MarkingTaskService, PageDataService
from Papers.services import SpecificationService
from Papers.models import Image

from .utils import _error_response


class QuestionMaxMark(APIView):
    """Return the max mark for a given question.

    Returns:
        (200): returns the maximum number of points for a question
        (416): question value out of range
    """

    def get(self, request, *, question):
        try:
            max_mark = SpecificationService.get_question_mark(question)
            return Response(max_mark)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Question {question} out of range: {e}",
                status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            )


class MarkingProgressCount(APIView):
    """Responds with a list of completed/total tasks.

    Returns:
        (200): returns two integers, first the number of marked papers
            for this question/version and the total number of papers for
            this question/version.
        (400): malformed such as non-integers for question/version.
        (416): question values out of range: NOT IMPLEMENTED YET.
            (In legacy, this was thrown by the backend).
    """

    def get(self, request):
        data = request.data
        try:
            question = int(data["q"])
            version = int(data["v"])
        except (ValueError, TypeError):
            return _error_response(
                "question and version must be integers",
                status.HTTP_400_BAD_REQUEST,
            )
        mts = MarkingTaskService()
        progress = mts.get_marking_progress(question, version)
        return Response(progress, status=status.HTTP_200_OK)


class MgetDoneTasks(APIView):
    """Retrieve data for questions which have already been graded by the user.

    Respond with status 200.

    Returns:
        200: list of [group-ids, mark, marking_time, [list_of_tag_texts], integrity_check ] for each paper.
    """

    def get(self, request, *args):
        data = request.data
        question = data["q"]
        version = data["v"]

        mts = MarkingTaskService()
        marks = mts.get_user_mark_results(
            request.user, question=question, version=version
        )

        # TODO: 3rd entry here is marking time: in legacy, we trust the client's
        # previously given value (which the client tracks including revisions)
        # Currently this tries to estimate a value server-side.  Decisions?
        # Previous code was `mark_action.time - mark_action.claim_action.time`
        # which is a `datatime.timedelta`.  Not sure how to convert to seconds
        # so currently using hardcoded value.
        # TODO: legacy marking time is int, but we may decide to change to float.
        rows = map(
            lambda annotation: [
                annotation.task.code,
                annotation.score,
                annotation.marking_time,
                mts.get_tags_for_task(annotation.task.code),
                annotation.task.pk,  # TODO: integrity check is not implemented yet
            ],
            marks,
        )
        return Response(rows, status=status.HTTP_200_OK)


class MgetPageDataQuestionInContext(APIView):
    """Get page metadata for a particular test-paper optionally with a question highlighted.

    APIs backed by this routine return a JSON response with a list of
    dicts, where each dict has keys: `pagename`, `md5`, `included`,
    `order`, `id`, `orientation`, `server_path` as documented below.

    This routine returns all pages, including ID pages, DNM pages and
    various sorts of extra pages.

    A 409 is returned with an explanation if paper number not found.

    The list of dicts (we think of them as rows) have the keys:

    `pagename`
        A string something like `"t2"`.  Reasonable to use
        as a thumbnail label for the image or in other cases where
        a very short string label is required.

    `md5`
        A string of the md5sum of the image.

    `id`
        an integer like 19.  This is the key in the database to
        the image of this page.  It is (I think) possible to have
        two pages pointing to the same image, in which case the md5
        and the id could be repeated.  TODO: determine if this only
        happens b/c of bugs/upload issues or if its a reasonably
        normal state.
        Note this is nothing to do with "the ID page", that is the page
        where assessment writers put their name and other info.

    `order`
        None or an integer specifying the relative ordering of
        pages within a question.  As with `included`,
        this information only reflects the initial (typically
        scan-time) ordering of the images.  If its None, server has
        no info about what order might be appropriate, for example
        because this image is not thought to belong in `question`.

    `orientation`
        relative to the natural orientation of the image.
        This is an integer for the degrees of rotation.  Probably
        only multiples of 90 work and perhaps only [0, 90, 180, 270]
        but could/should (TODO) be generalized for arbitrary
        rotations.  This should be applied *after* any metadata
        rotations from inside the file instead (such as jpeg exif
        orientation).  As with `included` and `order`, this is only
        the initial state.  Clients may rotate images and that
        information belongs their annotation.

    `server_path`
        a string of a path and filename where the server
        might have the file stored, such as
        `"pages/originalPages/t0004p02v1.86784dd1.png"`.
        This is guaranteed unique (such as by the random bit before
        `.png`).  It is *not* guaranteed that the server actually
        stores the file in this location, although the current
        implementation does.

    `included`
        boolean, did the server *originally* have this page
        included in question number `question`?.  Note that clients
        may pull other pages into their annotating; you can only
        rely on this information for initializing a new annotating
        session.  If you're e.g., editing an existing annotation,
        you should rely on the info from that existing annotation
        instead of this.

    Example::

        [
          {'pagename': 't2',
           'md5': 'e4e131f476bfd364052f2e1d866533ea',
           'included': False,
           'order': None,
           'id': 19',
           'orientation': 0
           'server_path': 'pages/originalPages/t0004p02v1.86784dd1.png',
          },
          {'pagename': 't3',
           'md5': 'a896cb05f2616cb101df175a94c2ef95',
           'included': True,
           'order': 1,
           'id': 20,
           'orientation': 270
           'server_path': 'pages/originalPages/t0004p03v2.ef7f9754.png',
          }
        ]
    """

    def get(self, request, paper, question=None):
        service = PageDataService()

        try:
            # we need include_idpage here b/c this APIView Class serves two different
            # API calls: one of which wants all pages.  Its also documented above that
            # callers who don't want to see the ID page (generally b/c Plom does
            # anonymous grading) should filter this out.  This is the current behaviour
            # of the Plom Client UI tool.
            page_metadata = service.get_question_pages_metadata(
                paper, question=question, include_idpage=True, include_dnmpages=True
            )
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Paper {paper} does not exist: {e}", status.HTTP_409_CONFLICT
            )
        return Response(page_metadata, status=status.HTTP_200_OK)


class MgetOneImage(APIView):
    """Get a page image from the server."""

    def get(self, request, pk, hash):
        pds = PageDataService()
        # TODO - replace this fileresponse(open(file)) with fileresponse(filefield)
        # so that we don't have explicit file-path handling.
        try:
            img_path = pds.get_image_path(pk, hash)
            return FileResponse(open(img_path, "rb"), status=status.HTTP_200_OK)
        except Image.DoesNotExist:
            return _error_response("Image does not exist.", status.HTTP_400_BAD_REQUEST)


class MgetAnnotations(APIView):
    """Get the latest annotations for a question.

    TODO: implement "edition"?

    TODO: The legacy server sends 410 for "task deleted", and the client
    messenger is documented as expecting 406/410/416.
    I suspect here we have folded the "task deleted" case into the 404.

    Returns:
        200: the annotation data.
        404: no such task (i.e., no such paper) or no annotations for the
            task if it exists.
        406: the task has been mdified, perhaps even during this call?
            TODO: some atomic operation would prevent this?
    """

    def get(self, request: Request, *, paper: int, question: int) -> Response:
        mts = MarkingTaskService()
        try:
            annotation = mts.get_latest_annotation(paper, question)
        except (ObjectDoesNotExist, ValueError) as e:
            return _error_response(
                f"No annotations for paper {paper} question {question}: {e}",
                status.HTTP_404_NOT_FOUND,
            )
        annotation_task = annotation.task
        annotation_data = annotation.annotation_data

        # TODO is this really needed?
        try:
            latest_task = mark_task.get_latest_task(paper, question)
        except ObjectDoesNotExist as e:
            # Possibly should be 410?  see baseMessenger.py
            return _error_response(e, status.HTTP_404_NOT_FOUND)

        if latest_task != annotation_task:
            return _error_response(
                "Integrity error: task has been modified by server.",
                status.HTTP_406_NOT_ACCEPTABLE,
            )

        annotation_data["user"] = annotation.user.username
        annotation_data["annotation_edition"] = annotation.edition
        annotation_data["annotation_reference"] = annotation.pk

        return Response(annotation_data, status=status.HTTP_200_OK)


class MgetAnnotationImage(APIView):
    """Get an annotation-image.

    TODO: implement "edition".

    TODO: The legacy server sends 410 for "task deleted", and the client
    messenger is documented as expecting 406/410/416 (although the legacy
    server doesn't seem to send 406/416 for annotation image calls).
    I suspect here we have folded the "task deleted" case into the 404.

    Returns:
        200: the image as a file.
        404: no such task (i.e., no such paper) or no annotations for the
            task if it exists.
        406: the task has been modified, perhaps even during this call?
            TODO: some atomic operation would prevent this?
    """

    def get(
        self, request: Request, *, paper: int, question: int, edition: int | None = None
    ) -> Response:
        if edition is not None:
            raise NotImplementedError('"edition" not implemented')
        mts = MarkingTaskService()
        try:
            annotation = mts.get_latest_annotation(paper, question)
        except (ObjectDoesNotExist, ValueError) as e:
            return _error_response(
                f"No annotations for paper {paper} question idx {question}: {e}",
                status.HTTP_404_NOT_FOUND,
            )
        annotation_task = annotation.task
        annotation_image = annotation.image

        # TODO is this really needed?
        try:
            latest_task = mark_task.get_latest_task(paper, question)
        except ObjectDoesNotExist as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        if latest_task != annotation_task:
            return _error_response(
                "Integrity error: task has been modified by server.",
                status.HTTP_406_NOT_ACCEPTABLE,
            )

        return FileResponse(annotation_image.image, status=status.HTTP_200_OK)


class TagsFromCodeView(APIView):
    """Handle getting and setting tags for marking tasks."""

    def get(self, request, code):
        """Get all of the tags for a particular task.

        Args:
            code: str, question/paper code for a task

        Returns:
            200: list of tag texts

        Raises:
            406: Invalid task code
            404: Task is not found
        """
        mts = MarkingTaskService()
        try:
            return Response(mts.get_tags_for_task(code), status=status.HTTP_200_OK)
        except ValueError as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)

    def patch(self, request, code):
        """Add a tag to a task. If the tag does not exist in the database, create it as a side effect.

        Args:
            code: str, question/paper code for a task

        Returns:
            200: OK response

        Raises:
            406: Invalid tag text
            404: Task is not found
            410: Invalid task code

        TODO: legacy uses 204 in the case of "already tagged", which
        I think we just silently accept and return 200.
        """
        mts = MarkingTaskService()
        tag_text = request.data["tag_text"]
        tag_text = mts.sanitize_tag_text(tag_text)
        user = request.user

        try:
            mts.add_tag_text_from_task_code(tag_text, code, user=user)
        except ValueError as e:
            return _error_response(e, status.HTTP_410_GONE)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, code):
        """Remove a tag from a task.

        Args:
            request (Request): with ``tag_text`` (`str`) as a data field
            code: str, question/paper code for a task

        Returns:
            200: OK response

        Raises:
            409: Invalid task code, no such tag, or this task does not
                have this tag.
            404: Task is not found
        """
        mts = MarkingTaskService()
        tag_text = request.data["tag_text"]
        tag_text = mts.sanitize_tag_text(tag_text)

        try:
            mts.remove_tag_text_from_task_code(tag_text, code)
        except ValueError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
        except RuntimeError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_200_OK)


class GetAllTags(APIView):
    """Respond with all of the tags in the server."""

    def get(self, request):
        mts = MarkingTaskService()
        return Response(mts.get_all_tags(), status=status.HTTP_200_OK)


class GetSolutionImage(APIView):
    """Get a solution image from the server."""

    def get(self, request, question, version):
        try:
            return FileResponse(SolnImageService().get_soln_image(question, version))
        except ObjectDoesNotExist:
            return _error_response("Image does not exist.", status.HTTP_404_NOT_FOUND)
