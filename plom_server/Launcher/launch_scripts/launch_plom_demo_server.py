#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

import argparse
from pathlib import Path
from shlex import split
import subprocess
import sys
import time

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


# we specify this directory relative to the plom_server
# root directory, rather than getting Django things up and
# running, just to get at these useful files.

demo_file_directory = Path("./Launcher/launch_scripts/demo_files/")


def wait_for_user_to_type_quit() -> None:
    """Wait for correct user input and then return."""
    while True:
        x = input("Type 'quit' and press Enter to exit the demo: ")
        if x.casefold() == "quit":
            break


def set_argparse_and_get_args() -> argparse.Namespace:
    """Configure argparse to collect commandline options."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
    The --stop-after and --wait-after options take many possible values.

    * users = the basic plom-system (server, db, etc) are set up, and demo-users are created.
    * spec = a demo assessment specification is uploaded.
    * sources = demo assessment sources are uploaded. Also a classlist and (if selected) solutions.
    * populate = the database is populated with papers.
    * papers-built = assessment PDFs are created from the sources.
    * bundles-created = PDF bundles are created to simulate scanned student work.
    * bundles-uploaded = those PDF bundles are uploaded and their qr-codes read (but not processed further).
    * bundles-pushed = those bundles are "pushed" so that they can be graded.
    * rubrics = system and demo rubrics are created for marking.
    * randomarking = several rando-markers are run in parallel to leave comments and annotations on student work. Random ID-ing of papers is also done.
    * tagging = (future/not-yet-implemented) = pedagogy tags will be applied to questions to label them with learning goals.
    * spreadsheet = a marking spreadsheet is downloaded.
    * reassembly = marked papers are reassembled (along, optionally, with solutions).
    * reports = (future/not-yet-implemented) = instructor and student reports are built.
    """,
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port number on which to launch server"
    )
    parser.add_argument(
        "--length",
        action="store",
        choices=["quick", "normal", "long", "plaid"],
        default="normal",
        help="Describe length of demo",
    )
    parser.add_argument(
        "--solutions",
        default=True,
        action="store_true",
        help="Upload solutions to demo server",
    )
    parser.add_argument("--no-solutions", dest="solutions", action="store_false")
    parser.add_argument(
        "--prename",
        default=True,
        action="store_true",
        help="Prename papers as determined by the demo classlist",
    )
    parser.add_argument("--no-prename", dest="prename", action="store_false")
    parser.add_argument(
        "--muck",
        default=True,
        action="store_true",
        help="Run pdf-mucking to simulate poor scanning of papers (not functional yet)",
    )
    parser.add_argument("--no-muck", dest="muck", action="store_false")
    stop_wait_choices = [
        "users",
        "spec",
        "sources",
        "populate",
        "papers-built",
        "bundles-created",
        "bundles-uploaded",
        "bundles-pushed",
        "rubrics",
        "randomarking",
        "tagging",
        "spreadsheet",
        "reassembly",
        "reports",
    ]
    stop_wait_group = parser.add_mutually_exclusive_group()
    stop_wait_group.add_argument(
        "--stop-after",
        action="store",
        choices=stop_wait_choices,
        nargs=1,
        help="Stop the demo sequence at a certain breakpoint.",
    )
    stop_wait_group.add_argument(
        "--wait-after",
        action="store",
        choices=stop_wait_choices,
        nargs=1,
        help="Stop the demo sequence at a certain breakpoint.",
    )
    prod_dev_group = parser.add_mutually_exclusive_group()
    prod_dev_group.add_argument(
        "--development",
        action="store_true",
        help="Run the django development webserver - definitely do not use in production.",
    )
    prod_dev_group.add_argument(
        "--production", action="store_true", help="Run a production gunicorn server."
    )

    return parser.parse_args()


def run_django_manage_command(cmd) -> None:
    """Run the given command with 'python3 manage.py' and wait for return.

    Command must finish successfully (zero return code).

    Args:
        cmd: the command to run.
    """
    full_cmd = "python3 manage.py " + cmd
    subprocess.run(split(full_cmd), check=True)


def popen_django_manage_command(cmd) -> subprocess.Popen:
    """Run the given command with 'python3 manage.py' using process Popen and return a handle to the process.

    Args:
        cmd: the command to run.

    Returns:
        A subprocess.Popen class that can be used to terminate the
        background command.  You'll probably want to do some checking
        that the process is up, as it could fail almost instantly
        following this command.  Or at any time really.

    Raises:
        OSError: such as FileNotFoundError if the command cannot be
            found.  But note lack of failure here is no guarantee
            the process is still running at any later time; such is
            the nature of inter-process communication.
    """
    full_cmd = "python3 manage.py " + cmd
    return subprocess.Popen(split(full_cmd))


def confirm_run_from_correct_directory() -> None:
    """Confirm that the script is being run from the directory containing django's manage.py command."""
    if not Path("./manage.py").exists():
        raise RuntimeError(
            "This script needs to be run from the same directory as django's manage.py script."
        )


def pre_launch():
    """Run commands required before the plom-server can be launched.

    Note that this runs:
        * plom_clean_all_and_build_db: cleans out any old database and misc user-generated file, then rebuilds the blank db.
        * plom_make_groups_and_first_users: creates user-groups needed by plom, and an admin user and a manager-user.
        * plom_build_scrap_extra_pdfs: build the scrap-paper and extra-page pdfs.

    Note that this can easily be extended in the future to run more commands as required.
    """
    # start by cleaning out the old db and misc files.
    run_django_manage_command("plom_clean_all_and_build_db")
    # build the user-groups and the admin and manager users
    run_django_manage_command("plom_make_groups_and_first_users")
    # build extra-page and scrap-paper PDFs
    run_django_manage_command("plom_build_scrap_extra_pdfs")


def launch_huey_process() -> subprocess.Popen:
    """Launch the huey-consumer for processing background tasks.

    Note that this runs the django manage command 'djangohuey --quiet'.
    """
    print("Launching huey.")
    # this needs to be run in the background
    return popen_django_manage_command("djangohuey --quiet")


def launch_django_dev_server_process(*, port: int | None = None) -> subprocess.Popen:
    """Launch django's native development server.

    Note that this should never be used in production.

    KWargs:
        port: the port for the server.

    """
    # TODO - put in an 'are we in production' check.

    print("Launching django's development server.")
    # this needs to be run in the background
    if port:
        print(f"Dev server will run on port {port}")
        return popen_django_manage_command(f"runserver {port}")
    else:
        return popen_django_manage_command("runserver")


def launch_gunicorn_production_server_process(port: int) -> subprocess.Popen:
    """Launch the gunicorn web server.

    Note that this should always be used in production.

    Args:
        port: the port for the server.
    """
    print("Launching gunicorn web-server.")
    # TODO - put in an 'are we in production' check.
    cmd = f"gunicorn Web_Plom.wsgi --bind 0.0.0.0:{port}"
    return subprocess.Popen(split(cmd))


def upload_demo_assessment_spec_file():
    """Use 'plom_preparation_test_spec' to upload a demo assessment spec."""
    print("Uploading demo assessment spec")
    spec_file = demo_file_directory / "demo_assessment_spec.toml"
    run_django_manage_command(f"plom_preparation_test_spec upload {spec_file}")


def upload_demo_test_source_files():
    """Use 'plom_preparation_source' to upload a demo assessment source pdfs."""
    print("Uploading demo assessment source pdfs")
    for v in [1, 2]:
        source_pdf = demo_file_directory / f"source_version{v}.pdf"
        run_django_manage_command(f"plom_preparation_source upload -v {v} {source_pdf}")


def upload_demo_solution_files():
    """Use 'plom_solution_spec' to upload demo solution spec and source pdfs."""
    print("Uploading demo solution spec")
    soln_spec_path = demo_file_directory / "demo_solution_spec.toml"
    print("Uploading demo solution pdfs")
    run_django_manage_command(f"plom_soln_spec upload {soln_spec_path}")
    for v in [1, 2]:
        soln_pdf_path = demo_file_directory / f"solutions{v}.pdf"
        run_django_manage_command(f"plom_soln_sources upload -v {v} {soln_pdf_path}")


def upload_demo_classlist(length="normal", prename=True):
    """Use 'plom_preparation_classlist' to the appropriate classlist for the demo."""
    if length == "long":
        cl_path = demo_file_directory / "cl_for_long_demo.csv"
    elif length == "plaid":
        cl_path = demo_file_directory / "cl_for_plaid_demo.csv"
    elif length == "quick":
        cl_path = demo_file_directory / "cl_for_quick_demo.csv"
    else:  # for normal
        cl_path = demo_file_directory / "cl_for_demo.csv"

    run_django_manage_command(f"plom_preparation_classlist upload {cl_path}")

    if prename:
        run_django_manage_command("plom_preparation_prenaming --enable")
    else:
        run_django_manage_command("plom_preparation_prenaming --disable")


def populate_the_database(length="normal"):
    """Use 'plom_qvmap' to build a qv-map for the demo and populate the database."""
    production = {"quick": 35, "normal": 70, "long": 600, "plaid": 1200}
    print(
        f"Building a question-version map and populating the database with {production[length]} papers"
    )
    run_django_manage_command(
        f"plom_qvmap build_db -n {production[length]} --first-paper 1"
    )
    print("Paper database is now populated")


def build_all_papers_and_wait():
    """Trigger build all the printable paper pdfs and wait for completion."""
    from time import sleep

    run_django_manage_command("plom_build_paper_pdfs --start-all")
    # since this is a background huey job, we need to
    # wait until all those pdfs are actually built -
    # we can get that by looking at output from plom_build_paper_pdfs --status
    pdf_status_cmd = "python3 manage.py plom_build_paper_pdfs --count-done"
    while True:
        out_papers = subprocess.check_output(split(pdf_status_cmd)).decode("utf-8")
        if "all" in out_papers.casefold():
            break
        else:
            print(out_papers.strip())
            sleep(1)
    print("All paper PDFs are now built.")


def download_zip() -> None:
    """Use 'plom_build_paper_pdfs' to download a zip of all paper-pdfs."""
    run_django_manage_command("plom_build_paper_pdfs --download-all")
    print("Downloaded a zip of all the papers")


def run_demo_preparation_commands(
    *, length="normal", stop_after=None, solutions=True, prename=True
) -> bool:
    """Run commands to prepare a demo assessment.

    In order it runs:
        * (users): create demo users,
        * (spec): upload the demo spec,
        * (sources): upload the test-source pdfs
            >> will also upload solutions at this point if instructed by user
            >> will also upload the classlist
        * (populate): make the qv-map and populate the database
        * (papers-built): make the paper-pdfs
        * finally - download a zip of all the papers, and set preparation as completed.

    KWargs:
        length = the length of the demo: quick, normal, long, plaid.
        stop_after = after which step should the demo be stopped, see list above.
        solutions = whether or not to upload solutions as part of the demo.
        prename = whether or not to prename some papers in the demo.

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    # in order the demo will

    # TODO = remove this demo-specific command
    run_django_manage_command("plom_create_demo_users")
    if stop_after == "users":
        print("Stopping after users created.")
        return False

    run_django_manage_command("plom_demo_spec")
    if stop_after == "spec":
        print("Stopping after assessment specification uploaded.")
        return False

    upload_demo_test_source_files()
    if solutions:
        upload_demo_solution_files()
    upload_demo_classlist(length, prename)
    if stop_after == "sources":
        print("Stopping after assessment sources and classlist uploaded.")
        return False

    populate_the_database(length)
    if stop_after == "populate":
        print("Stopping after paper-database populated.")
        return False

    build_all_papers_and_wait()
    if stop_after == "papers-built":
        print("Stopping after papers_built.")
        return False
    # download a zip of all the papers.
    download_zip()

    # now set preparation status as done
    run_django_manage_command("plom_preparation_status --set finished")

    return True


def _read_bundle_config(length):
    # read the config toml file
    if length == "quick":
        fname = "bundle_for_quick_demo.toml"
    elif length == "long":
        fname = "bundle_for_long_demo.toml"
    elif length == "plaid":
        fname = "bundle_for_plaid_demo.toml"
    else:
        fname = "bundle_for_demo.toml"
    with open(demo_file_directory / fname, "rb") as fh:
        try:
            return tomllib.load(fh)
        except tomllib.TOMLDecodeError as e:
            raise RuntimeError(e)


def build_the_bundles(length="normal"):
    """Create bundles of papers to simulate scanned student papers.

    Note: takes the pdf of each paper directly from the file
        system, not the downloaded zip. The bundles are then
        saved in the current directory.

    KWargs:
        length = the length of the demo.
    """
    run_django_manage_command(f"plom_demo_bundles --length {length} --action build")


def upload_the_bundles(length="normal"):
    """Uploads the demo bundles from the working directory.

    Note that this waits for the uploads to process and then also
    triggers the qr-code reading and waits for that to finish.

    KWargs:
        length = the length of the demo.
    """
    run_django_manage_command(f"plom_demo_bundles --length {length} --action upload")
    run_django_manage_command("plom_staging_bundles wait")
    run_django_manage_command(f"plom_demo_bundles --length {length} --action read")
    run_django_manage_command("plom_staging_bundles wait")


def push_the_bundles(length):
    """Pushes the demo bundles from staging to the server.

    Only pushes 'perfect' bundles (those without errors). It
    also IDs any (pushed) homework bundles.
    """
    run_django_manage_command(f"plom_demo_bundles --length {length} --action push")
    run_django_manage_command(f"plom_demo_bundles --length {length} --action id_hw")


def run_demo_bundle_scan_commands(
    *, stop_after=None, length="normal", muck=False
) -> bool:
    """Run commands to step through the scanning process in the demo.

    In order it runs:
        * (bundles-created): create bundles of papers; system will also make random annotations on these papers to simulate student work. (Optionally) the system will "muck" the papers to simulate poor scanning.
        * (bundles-uploaded): upload the bundles and read their qr-codes
        * finally - push the bundles and id any homework bundles.

    KWargs:
        stop_after = after which step should the demo be stopped, see list above.
        length = the length of the demo: quick, normal, long, plaid.
        muck = whether or not to "muck" with the mock test bundles - this is intended to imitate the effects of poor scanning. Not yet functional.

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    build_the_bundles(length)
    if stop_after == "bundles-created":
        return False

    upload_the_bundles(length)
    if stop_after == "bundles-uploaded":
        return False

    push_the_bundles(length)
    if stop_after == "bundles-pushed":
        return True

    return True


def run_the_randomarker(*, port):
    """Run the rando-IDer and rando-Marker.

    All papers will be ID'd and marked after this call.
    """
    from time import sleep

    # TODO: hardcoded http://
    srv = f"http://localhost:{port}"
    # list of markers and their passwords and percentage to mark
    users = [
        ("demoMarker1", "demoMarker1", 100),
        ("demoMarker2", "demoMarker2", 75),
        ("demoMarker3", "demoMarker3", 75),
        ("demoMarker4", "demoMarker4", 50),
        ("demoMarker5", "demoMarker5", 50),
    ]

    # rando-id and then rando-mark
    cmd = f"python3 -m plom.client.randoIDer -s {srv} -u {users[0][0]} -w {users[0][1]}"
    print(f"RandoIDing!  calling: {cmd}")
    subprocess.check_call(split(cmd))

    randomarker_processes = []
    for X in users[1:]:
        cmd = f"python3 -m plom.client.randoMarker -s {srv} -u {X[0]} -w {X[1]} --partial {X[2]}"
        print(f"RandoMarking!  calling: {cmd}")
        randomarker_processes.append(subprocess.Popen(split(cmd)))
        sleep(0.5)
    # now wait for those markers
    while True:
        if any(X.poll() is None for X in randomarker_processes):
            # we are still waiting on a rando-marker.
            sleep(2)
        else:  # all rando-markers are done
            break

    # now a final run to do any remaining tasks
    for X in users[:1]:
        cmd = f"python3 -m plom.client.randoMarker -s {srv} -u {X[0]} -w {X[1]} --partial 100"
        print(f"RandoMarking!  calling: {cmd}")
        subprocess.check_call(split(cmd))


def run_marking_commands(*, port: int, stop_after=None) -> bool:
    """Run commands to step through the marking process in the demo.

    In order it runs:
        * (rubrics): Make system and demo rubrics.
        * (randomarker): make random marking-annotations on papers and assign random student-ids.

    KWargs:
        stop_after = after which step should the demo be stopped, see list above.
        port = the port on which the demo is running.

    Returns: a bool to indicate if the demo should continue (true) or stop (false).
    """
    # add rubrics and tags, and then run the randomaker.
    run_django_manage_command("plom_rubrics init manager")
    run_django_manage_command("plom_rubrics push --demo manager")
    if stop_after == "rubrics":
        return False

    run_the_randomarker(port=args.port)
    if stop_after == "randomarker":
        return False

    print(">> Future plom dev will include pedagogy tagging here.")
    return True


def run_finishing_commands(*, stop_after=None, solutions=True) -> bool:
    print("Reassembling all marked papers.")
    run_django_manage_command("plom_reassemble")
    if solutions:
        print("Constructing individual solution pdfs for students.")
        run_django_manage_command("plom_build_all_soln")

    if stop_after == "reassembly":
        return False

    print("Downloading a csv of student marks.")
    run_django_manage_command("plom_download_marks_csv")
    if stop_after == "spreadsheet":
        return False

    print(">> Future plom dev will include instructor-report download here.")
    print(">> Future plom dev will include strudent-reports download here.")
    return True


if __name__ == "__main__":
    args = set_argparse_and_get_args()
    # cast stop-after, wait-after from list of options to a singleton or None
    if args.stop_after:
        stop_after = args.stop_after[0]
        wait_at_end = False
    else:
        wait_at_end = True
        if args.wait_after:
            stop_after = args.wait_after[0]
        else:
            stop_after = None

    if args.production and not args.port:
        print("You must supply a port for the production server.")

    # make sure we are in the correct directory to run things.
    confirm_run_from_correct_directory()
    # clean up and rebuild things before launching.
    pre_launch()
    # now put main things inside a try/finally so that we
    # can clean up the huey/server processes on exit.
    huey_process, server_process = None, None
    try:
        print("v" * 50)
        huey_process = launch_huey_process()
        server_process = launch_django_dev_server_process(port=args.port)
        # both processes still running after small delay? probably working
        time.sleep(0.25)
        r = huey_process.poll()
        if r is not None:
            raise RuntimeError(f"Problem with huey process: exit code {r}")
        r = server_process.poll()
        if r is not None:
            raise RuntimeError(f"Problem with server process: exit code {r}")
        print("^" * 50)

        print("*" * 50)
        print("> Running demo specific commands")
        print(">> Preparation of assessment")
        while True:
            if not run_demo_preparation_commands(
                length=args.length,
                stop_after=stop_after,
                solutions=args.solutions,
                prename=args.prename,
            ):
                break

            print(">> Scanning of papers")
            if not run_demo_bundle_scan_commands(
                length=args.length, stop_after=stop_after, muck=args.muck
            ):
                break

            print("*" * 50)
            print(">> Ready for marking")
            if not run_marking_commands(port=args.port, stop_after=stop_after):
                break

            print("*" * 50)
            print(">> Ready for finishing")
            run_finishing_commands(stop_after=stop_after, solutions=args.solutions)
            break

        if args.production:
            print("Running production server, will not quit on user-input.")
            while True:
                pass
        elif wait_at_end:
            wait_for_user_to_type_quit()
        else:
            print("Demo process finished.")
    finally:
        print("v" * 50)
        print("Shutting down huey and django dev server")
        if huey_process:
            huey_process.terminate()
        if server_process:
            server_process.terminate()
        print("^" * 50)
