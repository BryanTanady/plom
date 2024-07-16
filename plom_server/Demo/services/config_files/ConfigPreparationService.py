# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

"""Handle creating pre-bundle server state from a config file.

Assumes that the config describes a valid server state, and that the
server will be created in order from test specification to building test-papers.
"""

import sys
from typing import Dict
from pathlib import Path

if sys.version_info >= (3, 10):
    from importlib import resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from Papers.services import (
    SpecificationService,
    PaperCreatorService,
)
from Preparation import useful_files_for_testing as useful_files
from Preparation.services import (
    SourceService,
    PrenameSettingService,
    StagingStudentService,
    PQVMappingService,
    PapersPrinted,
)

from . import PlomServerConfig, PlomConfigCreationError


def create_specification(config: PlomServerConfig):
    """Create a test specification from a config."""
    spec_path = config.test_spec
    if spec_path is None:
        return

    try:
        if spec_path == "demo":
            spec_src = resources.files(useful_files) / "testing_test_spec.toml"
        else:
            spec_src = config.parent_dir / spec_path
        SpecificationService.load_spec_from_toml(spec_src)
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def upload_test_sources(config: PlomServerConfig) -> None:
    """Upload test sources specified in a config."""
    source_paths = config.test_sources
    if source_paths == "demo":
        version1 = resources.files(useful_files) / "test_version1.pdf"
        version2 = resources.files(useful_files) / "test_version2.pdf"
        source_paths = [version1, version2]

    assert isinstance(source_paths, list)
    try:
        for i, path in enumerate(source_paths):
            SourceService.store_source_pdf(i + 1, path)
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def set_prenaming_setting(config: PlomServerConfig):
    """Set prenaming according to a config."""
    PrenameSettingService().set_prenaming_setting(config.prenaming_enabled)


def upload_classlist(config: PlomServerConfig):
    """Upload classlist specified in a config."""
    classlist_path = config.classlist
    if classlist_path == "demo":
        classlist_path = resources.files(useful_files) / "cl_for_demo.csv"

    assert isinstance(classlist_path, Path)
    try:
        with open(classlist_path, "rb") as classlist_f:
            sss = StagingStudentService()
            success, warnings = sss.validate_and_use_classlist_csv(
                classlist_f, ignore_warnings=True
            )
        if not success:
            raise PlomConfigCreationError("Unable to upload classlist.")
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def create_qv_map_and_papers(config: PlomServerConfig):
    """Create a QVmap from a config and use it to populate the paper database.

    Either generated from a number-to-produce value or a link to a QVmap CSV.
    """
    qvmap: Dict[int, Dict[int, int]] = {}
    if config.num_to_produce:
        qvmap = PQVMappingService().make_version_map(config.num_to_produce)
    else:
        # TODO: extra validation steps here?
        try:
            qvmap_path = config.qvmap
            if qvmap_path is None:
                raise RuntimeError(
                    "Number to produce and qvmap path missing from config."
                )

            # Some duplicated code here from `plom.version_maps``
            qvmap_path = config.parent_dir / qvmap_path
            with open(qvmap_path, "rb") as qvmap_file:
                qvmap_rows = tomllib.load(qvmap_file)
                for i in range(len(qvmap_rows)):
                    paper_number = i + 1
                    row = qvmap_rows[str(paper_number)]
                    qvmap[paper_number] = {
                        j: row[j - 1] for j in range(1, len(row) + 1)
                    }
            PQVMappingService().use_pqv_map(qvmap)
        except Exception as e:
            raise PlomConfigCreationError(e) from e
    try:
        PaperCreatorService().add_all_papers_in_qv_map(qvmap, background=False)
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def create_test_preparation(config: PlomServerConfig, verbose: bool = False):
    """Instantiate models from the test specification to test-papers."""

    def echo(x):
        return print(x) if verbose else None

    echo("Creating specification...")
    create_specification(config)

    if config.test_sources:
        echo("Uploading test sources...")
        upload_test_sources(config)

    echo("Setting prenaming and uploading classlist...")
    if config.prenaming_enabled:
        set_prenaming_setting(config)
    if config.classlist:
        upload_classlist(config)

    if config.num_to_produce or config.qvmap:
        echo("Creating question-version map and populating database...")
        create_qv_map_and_papers(config)

    # here we override the dependency checking since
    # we do not want to actually build pdfs.
    PapersPrinted.set_papers_printed(True, ignore_dependencies=True)
    echo("Preparation complete, papers printed.")
