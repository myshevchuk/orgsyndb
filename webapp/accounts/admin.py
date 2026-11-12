"""Accounts in the admin, where staff create and change them."""

from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from accounts.models import User


class CreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "initials", "first_name", "last_name")


class ChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


@admin.register(User)
class AccountAdmin(UserAdmin):
    form = ChangeForm
    add_form = CreationForm
    list_display = ("username", "initials", "first_name", "last_name",
                    "is_active", "is_staff")
    search_fields = ("username", "initials", "first_name", "last_name",
                     "email")
    ordering = ("initials",)
    fieldsets = (
        (None, {"fields": ("username", "initials", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name",
                                         "email")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff",
                                       "is_superuser", "groups",
                                       "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("username", "initials", "first_name",
                           "last_name", "usable_password", "password1",
                           "password2")}),
    )

    def get_readonly_fields(self, request: Any, obj: Any = None
                            ) -> tuple[str, ...]:
        """Show the user name of an existing account read-only: files name
        authors by it, so a value posted for it is ignored."""
        fixed = tuple(super().get_readonly_fields(request, obj))
        return fixed if obj is None else (*fixed, "username")

    def has_delete_permission(self, request: Any, obj: Any = None
                              ) -> bool:
        """Refuse every deletion: an account's name stays on the records
        and history it touched. Staff deactivate an account instead."""
        return False
