# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2022 Brennen Chiu

import logging
from typing import Dict

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from plom import SpecVerifier

from ..models import Specification, SpecQuestion
from ..serializers import SpecSerializer

# TODO - build similar for solution specs
# NOTE - this does not **validate** test specs, it assumes the spec is valid


log = logging.getLogger("ValidatedSpecService")


@transaction.atomic
def is_there_a_spec():
    """Has a test-specification been uploaded to the database."""
    return Specification.objects.count() == 1


@transaction.atomic
def get_the_spec() -> Dict:
    """Return the test-specification from the database.

    Returns:
        The exam specification as a dictionary.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    try:
        spec = Specification.objects.get()
        serializer = SpecSerializer(
            spec, context={"question": SpecQuestion.objects.all()}
        )
        return serializer.data
    except Specification.DoesNotExist:
        raise ObjectDoesNotExist("The database does not contain a test specification.")


@transaction.atomic
def get_the_spec_as_toml():
    """Return the test-specification from the database.

    If present, remove the private seed.  But the public code
    is included (if present).
    """
    spec = get_the_spec()
    spec.pop("privateSeed", None)
    sv = SpecVerifier(spec)
    return sv.as_toml_string()


@transaction.atomic
def get_the_spec_as_toml_with_codes(self):
    """Return the test-specification from the database.

    .. warning::
        Note this includes both the public code and the private
        seed.  If you are calling this, consider carefully whether
        you need the private seed.  At the time of writing, no one
        is calling this.
    """
    sv = SpecVerifier(get_the_spec())
    return sv.as_toml_string()


@transaction.atomic
def store_validated_spec(validated_spec: Dict) -> None:
    """Takes the validated test specification and stores it in the db.

    Args:
        validated_spec (dict): A dictionary containing a validated test
            specification.
    """
    serializer = SpecSerializer()
    serializer.create(validated_spec)


@transaction.atomic
def remove_spec() -> None:
    """Removes the test specification from the db, if possible.

    This can only be done if no tests have been created.

    Raises:
        ObjectDoesNotExist: no exam specification yet.
        MultipleObjectsReturned: cannot remove spec because
            there are already papers.
    """
    if not self.is_there_a_spec():
        raise ObjectDoesNotExist("The database does not contain a test specification.")

    from .paper_info import PaperInfoService

    if PaperInfoService().is_paper_database_populated():
        raise MultipleObjectsReturned("Database is already populated with test-papers.")

    Specification.objects.filter().delete()


@transaction.atomic
def get_longname() -> str:
    """Get the long name of the exam.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.longName


@transaction.atomic
def get_shortname() -> str:
    """Get the short name of the exam.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.name


@transaction.atomic
def get_n_questions() -> int:
    """Get the number of questions in the test.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfQuestions


@transaction.atomic
def get_n_versions() -> int:
    """Get the number of test versions.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfVersions


@transaction.atomic
def get_n_pages() -> int:
    """Get the number of pages in the test.

    Exceptions:
        ObjectDoesNotExist: no exam specification yet.
    """
    spec = Specification.objects.get()
    return spec.numberOfPages


@transaction.atomic
def get_question_mark(question_one_index) -> int:
    """Get the max mark of a given question.

    Args:
        question_one_index (str/int): question number, indexed from 1.

    Returns:
        The maximum mark.

    Raises:
        ObjectDoesNotExist: no question exists with the given index.
    """
    question = SpecQuestion.objects.get(question_number=question_one_index)
    return question.mark


@transaction.atomic
def n_pages_for_question(question_one_index) -> int:
    question = SpecQuestion.objects.get(question_number=question_one_index)
    return len(question.pages)


@transaction.atomic
def get_question_label(question_one_index) -> str:
    """Get the question label from its one-index.

    Args:
        question_one_index (str | int): question number indexed from 1.

    Returns:
        The question label.

    Raises:
        ObjectDoesNotExist: no question exists with the given index.
    """
    question = SpecQuestion.objects.get(question_number=question_one_index)
    return question.label


@transaction.atomic
def question_list_to_dict(questions: list[Dict]) -> Dict[str, Dict]:
    """Convert a list of question dictionaries to a nested dict with question numbers as keys."""
    return {str(i + 1): q for i, q in enumerate(questions)}
