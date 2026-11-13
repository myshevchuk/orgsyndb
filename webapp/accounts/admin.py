"""Accounts in the admin, where staff create and change them, and the
accounts' access tokens, which staff see and delete."""

from typing import Any

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from accounts.models import AccessToken, User


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

    def save_model(self, request: Any, obj: Any, form: Any, change: bool
                   ) -> None:
        """Save the account as ``ModelAdmin.save_model`` does, and warn,
        once the save has committed, when its Forgejo account could not
        be set in line with it."""
        super().save_model(request, obj, form, change)

        def warn() -> None:
            if obj.forge_failed:
                messages.warning(request, _(
                    "Forgejo was not updated; manage.py forge_accounts "
                    "brings it in line."))

        transaction.on_commit(warn)

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


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    """The access tokens, which staff list and delete; a token is made
    only by its account, on the token page, so the admin adds and
    changes none."""

    list_display = ("name", "user", "created_at", "last_used_at")
    list_select_related = ("user",)
    search_fields = ("name", "user__username")
    fields = ("user", "name", "created_at", "last_used_at")
    readonly_fields = fields

    def has_add_permission(self, request: Any, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: Any, obj: Any = None
                              ) -> bool:
        return False
