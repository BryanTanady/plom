# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from typing import Optional

from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction, IntegrityError
from django.http import HttpRequest
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from random_username.generate import generate_username


class AuthenticationServices:
    """A service class for managing authentication-related tasks."""

    @transaction.atomic
    def generate_list_of_basic_usernames(
        self, group_name: str, num_users: int, *, basename: Optional[str] = None
    ) -> list[str]:
        """Generate a list of basic numbered usernames.

        Args:
            group_name: The name of the group.
            num_users: The number of users to generate.

        Keyword Args:
            basename: The base part of the username, to which numbers
                will be appended.  If omitted, use the `group_name`
                with a capital letter.

        Returns:
            List of generated basic numbered usernames.
        """
        if not basename:
            basename = group_name.capitalize()

        user_list: list[str] = []
        username_number = 0

        while len(user_list) < num_users:
            username_number += 1
            try:
                user = self.create_user_and_add_to_group(
                    username=basename + str(username_number),
                    group_name=group_name,
                )
                user_list.append(user)
            except IntegrityError:
                pass

        return user_list

    @transaction.atomic
    def create_user_and_add_to_group(
        self, username: str, group_name: str, email: Optional[str] = None
    ) -> str:
        """Create a user and add them to a group.

        Note that by default that new user will not be active.

        Args:
            username: The username of the user.
            group_name: The name of the group.

        Returns:
            The username of the created user.
        """
        group = Group.objects.get(name=group_name)
        User.objects.create_user(
            username=username, email=email, password=None
        ).groups.add(group)
        user = User.objects.get(username=username)
        user.is_active = False
        user.save()

        return user.username

    def generate_list_of_funky_usernames(
        self, group_name: str, num_users: int
    ) -> list[str]:
        """Generate a list of "funky usernames" and add them to a group.

        Args:
            group_name: The name of the group.
            num_users: The number of users to generate.

        Returns:
            List of generated usernames.
        """
        funky_username_list = generate_username(num_users)
        user_list = []
        for username in funky_username_list:
            new_user = self._check_and_create_funky_usernames(
                username=username, group_name=group_name
            )
            user_list.append(new_user)

        return user_list

    def _check_and_create_funky_usernames(self, username: str, group_name: str) -> str:
        """Check if a username exists, and if it does, generate a new one recursively.

        Args:
            username: The username to check.
            group_name: The name of the group.

        Returns:
            The username of the created user.
        """
        if User.objects.filter(username=username).exists():
            new_username = generate_username(1)
            return self._check_and_create_funky_usernames(
                username=new_username, group_name=group_name
            )
        else:
            user = self.create_user_and_add_to_group(
                username=username, group_name=group_name
            )
            return user

    @transaction.atomic
    def generate_password_reset_links_dict(
        self, request: HttpRequest, username_list: list[str]
    ) -> dict[str, str]:
        """Generate a dictionary of password reset links for a list of usernames.

        Args:
            request: The HTTP request object.
            username_list: List of usernames.

        Returns:
            Dictionary of username to password reset link.
        """
        links_dict = {}
        for username in username_list:
            user = User.objects.get(username=username)
            links_dict[username] = self.generate_link(request, user)
        return links_dict

    @transaction.atomic
    def generate_link(self, request: HttpRequest, user: User) -> str:
        """Generate a password reset link for a user.

        Args:
            request: The HTTP request object.
            user: The user object for whom the password reset link is
                generated.

        Returns:
            The generated password reset link as a string.

        Note:
            The generated link follows the format: 'http://<domain>/reset/<uid>/<token>'.
        """
        http_protocol = "http://"
        domain = get_current_site(request).domain
        url_path = "/reset/"
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        forward_slash = "/"
        link = http_protocol + domain + url_path + uid + forward_slash + token

        return link
