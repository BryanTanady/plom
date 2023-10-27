# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.urls import path

from .signup_views.signup import (
    SingleUserSignUp,
    MultiUsersSignUp,
)
import Authentication.views

urlpatterns = [
    path("login/", Authentication.views.LoginView.as_view(), name="login"),
    path("logout/", Authentication.views.LogoutView.as_view(), name="logout"),
    path("", Authentication.views.Home.as_view(), name="home"),
    path(
        "maintenance/", Authentication.views.Maintenance.as_view(), name="maintenance"
    ),
    # signup path
    path(
        "signup/manager/",
        Authentication.views.SignupManager.as_view(),
        name="signup_manager",
    ),
    path(
        "reset/<slug:uidb64>/<slug:token>/",
        Authentication.views.SetPassword.as_view(),
        name="password_reset",
    ),
    path(
        "reset/done/",
        Authentication.views.SetPasswordComplete.as_view(),
        name="password_reset_complete",
    ),
    path(
        "signup/single/",
        SingleUserSignUp.as_view(),
        name="signup_single",
    ),
    path(
        "signup/multiple/",
        MultiUsersSignUp.as_view(),
        name="signup_multiple",
    ),
    path(
        "passwordresetlinks/",
        Authentication.views.PasswordResetLinks.as_view(),
        name="password_reset",
    ),
]
