# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib import admin

from .models.paper_structure import (
    Paper,
    MobilePage,
    FixedPage,
    IDPage,
    DNMPage,
    QuestionPage,
)
from .models.specifications import Specification
from .models.background_tasks import CreateImageHueyTask
from .models.image_bundle import Image, DiscardPage, Bundle

# This makes models appear in the admin interface
admin.site.register(Paper)
admin.site.register(Specification)
admin.site.register(MobilePage)
admin.site.register(FixedPage)
admin.site.register(IDPage)
admin.site.register(DNMPage)
admin.site.register(QuestionPage)
admin.site.register(CreateImageHueyTask)
admin.site.register(Bundle)
admin.site.register(Image)
admin.site.register(DiscardPage)
