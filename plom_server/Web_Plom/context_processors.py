# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
from plom import __version__ as plom_version


def user_group_information(request):
    """Add user group membership booleans to the view context.

    Adds booleans "user_is_admin", "user_is_manager", "user_is_scanner", "user_is_marker", and "user_is_lead_marker".

    Also adds navbar_color information via bootstrap standard colors
      * admin = danger
      * manager = warning
      * scanner = info
      * marker = primary (we also use this as the default color)
      * lead_marker = secondary
    """
    group_list = list(request.user.groups.values_list("name", flat=True))
    context = {
        "user_is_admin": "admin" in group_list,
        "user_is_manager": "manager" in group_list,
        "user_is_scanner": "scanner" in group_list,
        "user_is_lead_marker": "lead_marker" in group_list,
        "user_is_marker": "marker" in group_list,
        "navbar_color": "primary",
        # default to the marker color, no 'u' to keep north americans happy
    }
    if "admin" in group_list:
        context["navbar_color"] = "danger"
    elif "manager" in group_list:
        context["navbar_color"] = "warning"
    elif "scanner" in group_list:
        context["navbar_color"] = "info"
    elif "lead_marker" in group_list:
        context["navbar_color"] = "dark"
    return context


def plom_version_information(request):
    """Adds plom version information to the view context.

    Adds string "plom_version".
    """
    return {"plom_version": plom_version}
