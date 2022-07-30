.. Plom documentation
   Copyright 2020 Andrew Rechnitzer
   Copyright 2022 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Identifying papers
==================

At some point the Plom system needs to know which paper belongs to which student and this can be done in several ways:

1. Papers named from the start — Plom can produce papers with student
   names already printed on them.
   In this case Plom already knows which paper should belong to who and
   typically very little extra work is needed.
2. Automated ID reading — When tests are producing using Plom’s ID
   Template, the system can use `machine learning <https://xkcd.com/1838>`_
   to read the digits from the student-ID boxes and match against the
   classlist.
   In practice these appear to be over 95% accurate, but are not
   infallible.
3. Manual association — The simplest method is for a human to just read
   the ID from the page and enter it into the system.

These last two cases require human-intervention, which is where “identifier” comes in.


Running the auto-identifier
---------------------------

1. Open the manager tool.  "Progress" -> "ID progress".
2. Optionally, adjust the top/bottom crop values, either manually or by clicking "Select interactively".
3. Click "Recognize digits in IDs" which starts a background job.
   Click "Refresh" to update the output window.
4. Click "Run LAP Solver".  This currently blocks and might take a
   few seconds (say 3 seconds for 1000 papers).
5. Click "Refresh Prediction list" to update the table view.

.. caution::

   You should manually and carefully check the results (the Identifier client
   will show you these by default) because it does make mistakes, especially
   when there are additional names available in your classlist who did not
   write the test.


Manually identifying
--------------------

This is typically quite quick compared to marking and you will not need
to assign much person-time.
Since it does not require any heavy thinking it can be a good task for:

- the instructor-in-charge who is regularly interrupted by questions about papers,
- a (reliable) marker who finishes their other tasks early, or
- the scanner once they have finished scanning and uploading papers.

For now see https://plomgrading.org/docs/clientUse/identifying.html
