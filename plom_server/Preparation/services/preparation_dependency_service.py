# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from plom.plom_exceptions import PlomDependencyConflict

# move all service imports into the functions in order
# to avoid circular-dependency hell

# preparation steps are
# 1 = test-spec
# 2 = source pdfs
# 3 = classlist and prenaming
# 4 = qv-mapping and db-populate
# 5 = build tests paper pdfs
# 6 = tell plom papers are printed.

# give assert raising tests followed by true/false returning functions


# 1 the test spec depends on nothing, but sources depend on the spec
def assert_can_modify_spec():
    from . import PapersPrinted, SourceService

    # cannot modify spec if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # if any sources uploaded, then cannot modify spec.
    if SourceService.how_many_source_versions_uploaded() > 0:
        raise PlomDependencyConflict(
            "Source PDFs for your assessment have been uploaded."
        )


# 2 = the sources depend on the spec, and built-papers depend on the sources
def assert_can_modify_sources():
    from . import PapersPrinted
    from Papers.services import SpecificationService
    from BuildPaperPDF.services import BuildPapersService

    # cannot modify sources if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # if there is no spec, then cannot modify sources
    if not SpecificationService.is_there_a_spec():
        raise PlomDependencyConflict("There is no test specification")
    # cannot modify sources if any papers have been produced
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict(
            "Test PDFs have been built - these depend on the source pdfs."
        )


# 3 = classlist and prenaming.
# 3a = classlist - does not depend on spec, but the database depends on prenaming and classlist.
def assert_can_modify_classlist():
    from . import PapersPrinted, PrenameSettingService
    from Papers import PaperInfoService

    # cannot modify classlist if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # if db populated and prenaming is set, then cannot modify classlist
    if (
        PaperInfoService().is_paper_database_populated()
        and PrenameSettingService().get_prenaming_setting()
    ):
        raise PlomDependencyConflict(
            "Database has been populated with some prenamed papers, cannot change the classlist."
        )


# 3b - does not depend on spec, but qvmap/database depends on it (since prenamed papers have 'predictions' stored with those names)
def assert_can_modify_prenaming():
    from . import PapersPrinted
    from Papers.services import PaperInfoService

    # cannot modify prenaming if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")

    # if the qv-mapping/database is built then cannot modify prenaming.
    if PaperInfoService().is_paper_database_populated():
        raise PlomDependencyConflict(
            "The database has been populated, so cannot change the prenaming setting."
        )


def assert_can_modify_qv_mapping_database():
    from . import PapersPrinted, PrenameSettingService, StagingStudentService
    from Papers.services import SpecificationService
    from BuildPaperPDF.services import BuildPapersService

    # cannot modify qv mapping / database if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # cannot modify the qv-mapping if there is no spec
    if not SpecificationService.is_there_a_spec():
        raise PlomDependencyConflict("There is no test specification")

    # if prenaming set, then we must have a classlist before can modify qv-map.
    # else we can modify independent of the classlist.
    if PrenameSettingService().get_prenaming_setting():
        if not StagingStudentService().are_there_students():
            raise PlomDependencyConflict(
                "Prenaming enabled, but no classlist has been uploaded"
            )
        else:  # have classlist and prenaming set, so can modify qv-map
            pass
    else:  # prenaming not set, so can modify qv-map indep of classlist.
        pass

    # cannot modify qv-mapping if test papers have been produced
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict("Test PDFs have been built.")


# 5 - the test pdfs depend on the qv-map/db and source pdfs. Nothing depends on the test-pdfs
def assert_can_rebuild_test_pdfs():
    from . import PapersPrinted, SourceService
    from Papers.services import PaperInfoService

    # cannot rebuild test pdfs if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # and we need sources-pdfs and a populated db
    if not SourceService.are_all_sources_uploaded():
        raise PlomDependencyConflict("Not all source PDFs have been uploaded.")
    if not PaperInfoService().is_paper_database_populated():
        raise PlomDependencyConflict(
            "The qv-mapping has been built and the database have been populated."
        )


# now the true/false versions of these functions
# assert_can_modify_spec
def can_modify_spec():
    try:
        assert_can_modify_spec()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_sources
def can_modify_sources():
    try:
        assert_can_modify_sources()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_classlist
def can_modify_classlist():
    try:
        assert_can_modify_classlist()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_prenaming
def can_modify_prenaming():
    try:
        assert_can_modify_prenaming()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_qv_mapping_database
def can_modify_qv_mapping_database():
    try:
        assert_can_modify_qv_mapping_database()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_rebuild_test_pdfs
def can_rebuild_test_pdfs():
    try:
        assert_can_rebuild_test_pdfs()
        return True
    except PlomDependencyConflict:
        return False

def assert_can_set_papers_printed():
    # can set papers_printed once all PDFs are built.
    from BuildPaperPDF.services import BuildPapersService
    if not BuildPapersService().are_all_papers_built():
        raise PlomDependencyConflict("Cannot set papers-printed since not all paper-pdfs have been built.")
        
def assert_can_unset_papers_printed():
    # can unset papers_printed provided no bundles have neen scanned.
    from Papers.models import Bundle
    from Scan.models import StagingBundle
    return not (StagingBundle.objects.exists() or Bundle.objects.exists())
        raise PlomDependencyConflict("Cannot unset papers-printed because bundles have been uploaded.")

def can_set_papers_printed():
    try:
        assert_can_set_papers_printed()
        return True
    except PlomDependencyConflict:
        return False

def can_unset_papers_printed():
    try:
        assert_can_unset_papers_printed()
        return True
    except PlomDependencyConflict:
        return False
