# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.http import FileResponse

from Base.base_group_views import ManagerRequiredView
from ..services import (
    ReassembleService,
)


class StudentReportView(ManagerRequiredView):
    def get(self, request, paper_number):
        pdf_file = ReassembleService().get_single_student_report(paper_number)
        return FileResponse(pdf_file)
