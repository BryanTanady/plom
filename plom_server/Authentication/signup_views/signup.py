# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.shortcuts import render

from ..services import AuthenticationServices
from ..form.signupForm import CreateUserForm, CreateMultiUsersForm
from Base.base_group_views import ManagerRequiredView


class SingleUserSignUp(ManagerRequiredView):
    template_name = "Authentication/signup_single_user.html"
    form = CreateUserForm()

    def get(self, request):
        context = {"form": self.form, "current_page": "single"}
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateUserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            user_email = form.cleaned_data.get("email")
            user_type = form.cleaned_data.get("user_types")

            created_username = AuthenticationServices().create_user_and_add_to_group(
                username=username, group_name=user_type, email=user_email
            )
            usernames_list = list(created_username.split(" "))
            password_reset_links = (
                AuthenticationServices().generate_password_reset_links_dict(
                    request=request, username_list=usernames_list
                )
            )
            context = {
                "form": self.form,
                "current_page": "single",
                "links": password_reset_links,
                "created": True,
            }
        else:
            context = {
                "form": form,
                "current_page": "single",
                "created": False,
                "error": form.errors["username"][0],
            }
        return render(request, self.template_name, context)


class MultiUsersSignUp(ManagerRequiredView):
    template_name = "Authentication/signup_multiple_users.html"
    form = CreateMultiUsersForm()

    def get(self, request):
        context = {"form": self.form, "current_page": "multiple"}
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateMultiUsersForm(request.POST)

        if form.is_valid():
            num_users = form.cleaned_data.get("num_users")
            username_choices = form.cleaned_data.get("basic_or_funky_username")
            user_type = form.cleaned_data.get("user_types")

            if username_choices == "basic":
                usernames_list = (
                    AuthenticationServices().generate_list_of_basic_usernames(
                        group_name=user_type, num_users=num_users
                    )
                )
            elif username_choices == "funky":
                usernames_list = (
                    AuthenticationServices().generate_list_of_funky_usernames(
                        group_name=user_type, num_users=num_users
                    )
                )
            else:
                raise RuntimeError("Tertium non datur: unexpected third choice!")

            password_reset_links = (
                AuthenticationServices().generate_password_reset_links_dict(
                    request=request, username_list=usernames_list
                )
            )

            context = {
                "form": self.form,
                "current_page": "multiple",
                "links": password_reset_links,
                "created": True,
            }
            return render(request, self.template_name, context)
