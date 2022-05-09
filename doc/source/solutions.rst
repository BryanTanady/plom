.. Plom documentation
   Copyright 2022 Colin B. Macdonald
   SPDX-License-Identifier: AGPL-3.0-or-later


Solutions
=========

Plom can manage solutions for your exam.  These are used for showing
solutions on-screen to markers and for returning a custom solutions
file alongside a student's returned work.

The solutions can be revised, at least until they are returned to
students.


Making solutions
----------------

Your solutions can use the same structure as your blank exam or a
completely different structure.  See ``plom-solutions --help`` for
details.


Getting solutions onto the server
---------------------------------

The command-line tool :doc:`plom-solutions` can extract solutions from
PDF files, push to server, etc.  See ``plom-solutions --help`` for
more information.

The ``plom-manager`` GUI tool currently allows some manipulation of
the solutions but is not yet a replacement for the command-line tool.


Preparing solutions for students
--------------------------------

As part of a digital return, The command-line tool :doc:`plom-finish`
can construct individual PDF files for each student based on the
question-versions used in their test.  See :doc:`returning` for more
information.



Python module: ``plom.solutions``
---------------------------------

For scripting or other advanced usage, you can ``import plom.solutions``
in your own Python code.

.. automodule:: plom.solutions
    :members:
