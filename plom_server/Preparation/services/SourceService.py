# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations
from collections import defaultdict
import hashlib
import pathlib
from pathlib import Path
import tempfile
from typing import Any
import fitz
from django.core.files import File
from django.db import transaction
from Papers.services import SpecificationService
from ..models import PaperSourcePDF
from Preparation.services.preparation_dependency_service import (
    assert_can_modify_sources,
)
from Preparation.services.mocker import ExamMockerService
from plom.scan import QRextract
from Scan.services import ScanService
from Papers.models import ReferenceImage


def _get_source_file(source_version: int) -> File:
    """Return the Django-file for a specified source version.

    Args:
        source_version: which source version.

    Returns:
        Some sort of file abstraction, not for use outside Django.

    Raises:
        ObjectDoesNotExist: not yet uploaded or out of range.
    """
    return PaperSourcePDF.objects.get(version=source_version).source_pdf


@transaction.atomic
def how_many_source_versions_uploaded() -> int:
    return PaperSourcePDF.objects.count()


@transaction.atomic
def are_all_sources_uploaded() -> bool:
    if SpecificationService.is_there_a_spec():
        return PaperSourcePDF.objects.count() == SpecificationService.get_n_versions()
    else:
        return False


@transaction.atomic()
def delete_source_pdf(source_version: int) -> None:
    """Delete a particular version of the source PDF files.

    If no such version exists (either out of range or never uploaded)
    then silently return (no error is raised).
    """
    # raises a PlomDependencyException if cannot modify
    assert_can_modify_sources()

    # delete the DB entry and the file
    try:
        pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
        Path(pdf_obj.source_pdf.path).unlink()
        pdf_obj.delete()
    except PaperSourcePDF.DoesNotExist:
        pass


@transaction.atomic()
def delete_all_source_pdfs() -> None:
    """Delete all versions of the source PDF files."""
    # raises a PlomDependencyException if cannot modify
    assert_can_modify_sources()

    # delete the DB entry and the file
    for pdf_obj in PaperSourcePDF.objects.all():
        Path(pdf_obj.source_pdf.path).unlink()
        pdf_obj.delete()


@transaction.atomic()
def get_source(version: int) -> dict[str, Any]:
    """Return a dictionary with the source version.

    Args:
        version: which version, indexed from one.

    Returns:
        A dictionary with the version and uploaded status.
    """
    try:
        pdf_obj = PaperSourcePDF.objects.filter(version=version).get()
        return {"version": pdf_obj.version, "uploaded": True, "hash": pdf_obj.hash}
    except PaperSourcePDF.DoesNotExist:
        return {"version": version, "uploaded": False}


@transaction.atomic
def get_list_of_sources() -> list[dict[str, Any]]:
    """Return a list of sources, indicating if each is uploaded or not along with other info.

    The list is sorted by the version.
    """
    vers = SpecificationService.get_list_of_versions()
    status = []
    for v in vers:
        status.append(get_source(v))
    return status


@transaction.atomic
def store_source_pdf(version: int, source_pdf: pathlib.Path) -> None:
    """Store one of the source PDF files into the database.

    This does very little error checking; its perhaps intended for internal use.

    Args:
        version: which version, indexed from one.
        source_pdf: a path to an actual file.

    Returns:
        None

    Raises:
        ValueError: source already present for that version.
    """
    # raises a PlomDependencyException if cannot modify
    assert_can_modify_sources()

    try:
        PaperSourcePDF.objects.get(version=version)
    except PaperSourcePDF.DoesNotExist:
        pass
    else:
        raise ValueError(f"Source pdf with version {version} already present.")

    with open(source_pdf, "rb") as fh:
        the_bytes = fh.read()  # read entire file as bytes
        hashed = hashlib.sha256(the_bytes).hexdigest()

    with open(source_pdf, "rb") as fh:
        dj_file = File(fh, name=f"version{version}.pdf")
        PaperSourcePDF.objects.create(version=version, source_pdf=dj_file, hash=hashed)


def take_source_from_upload(version: int, in_memory_file: File) -> tuple[bool, str]:
    """Store a PDF file as one of the source versions, after doing some checks.

    Args:
        version: which version, one-based index.
        in_memory_file: File-object containing the pdf
            (can also be a TemporaryUploadedFile or InMemoryUploadedFile).
            TODO: I'm still very uncertain about the types of these, see
            also :py:`ScanService.upload_bundle`.  This one is also called by
            `Preparation/management/commands/plom_preparation_source.py`
            which passes a plain-old open file handle.

    Raises:
        PlomDependencyException: if prepration dependencies prevent modification of source files.

    Returns:
        A tuple with a boolean for success and a message or error message.
    """
    # raises a PlomDependencyException if cannot modify
    assert_can_modify_sources()

    if version not in SpecificationService.get_list_of_versions():
        return (False, f"Version {version} is out of range")
    required_pages = SpecificationService.get_n_pages()
    # save the file to a temp directory
    # TODO - size limits please
    with tempfile.TemporaryDirectory() as td:
        tmp_pdf = Path(td) / "unvalidated.pdf"
        with open(tmp_pdf, "wb") as fh:
            for chunk in in_memory_file:
                fh.write(chunk)
        # now check it has correct number of pages
        with fitz.open(tmp_pdf) as doc:
            if doc.page_count != int(required_pages):
                return (
                    False,
                    f"Uploaded pdf has {doc.page_count} pages, but spec requires {required_pages}",
                )
        # now try to store it
        try:
            store_source_pdf(version, tmp_pdf)
        except ValueError as err:
            return (False, str(err))

        store_reference_images(version)

        return (True, "PDF successfully uploaded")


@transaction.atomic
def check_pdf_duplication() -> dict[str, list[int]]:
    hashes = defaultdict(list)
    for pdf_obj in PaperSourcePDF.objects.all():
        hashes[pdf_obj.hash].append(pdf_obj.version)
    duplicates = {}
    for hash, versions in hashes.items():
        if len(versions) > 1:
            duplicates[hash] = versions
    return duplicates


@transaction.atomic
def get_source_as_bytes(source_version: int) -> bytes:
    try:
        pdf_obj = PaperSourcePDF.objects.filter(version=source_version).get()
        with pdf_obj.source_pdf.open("rb") as fh:
            return fh.read()
    except PaperSourcePDF.DoesNotExist:
        raise ValueError("Version does not exist")


@transaction.atomic
def store_reference_images(source_version: int):
    """From an uploaded source pdf create reference images of each page.

    Uses the exam mocker to put qr codes stamps in correct pages.
    Then stores the images with that qr-code information.
    """
    mocker = ExamMockerService()
    scanner = ScanService()

    # remove any existing reference images for this version
    for ri_obj in ReferenceImage.objects.filter(
        version=source_version
    ).select_for_update():
        ri_obj.image_file.path.unlink(missing_ok=True)
        ri_obj.delete()

    source_pdf_obj = PaperSourcePDF.objects.get(version=source_version)
    source_path = Path(source_pdf_obj.source_pdf.path)

    n_pages = SpecificationService.get_n_pages()
    mock_exam_pdf_bytes = mocker.mock_exam(
        source_version, source_path, n_pages, SpecificationService.get_short_name_slug()
    )
    doc = fitz.Document(stream=mock_exam_pdf_bytes)

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = pathlib.Path(tmpdir)
        for n, pg in enumerate(doc.pages()):
            pix = pg.get_pixmap(dpi=200, annots=True)
            fname = save_path / f"ref_{source_version}_{n+1}.png"
            pix.save(fname)
            code_dict = QRextract(fname)
            page_data = scanner.parse_qr_code([code_dict])
            with open(fname, "rb") as fh:
                pix_file = File(fh, name=fname.name)
                ReferenceImage.objects.create(
                    page_number=n + 1,
                    version=source_version,
                    image_file=pix_file,
                    parsed_qr=page_data,
                    source_pdf=source_pdf_obj,
                )


def _get_reference_image_file(source_version: int, page_number: int) -> File:
    """Return the Django-file for a specified reference image page / version.

    Args:
        source_version: which source version.
        page_number: which page

    Returns:
        Some sort of file abstraction, not for use outside Django.

    Raises:
        ObjectDoesNotExist: not yet uploaded or out of range.
    """
    return ReferenceImage.objects.get(
        version=source_version, page_number=page_number
    ).image_file
