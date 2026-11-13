"""The Forgejo accounts of the lab's accounts, kept in line through
Forgejo's admin API.

Forgejo makes an account at the first sign-in through the source
``lab`` and keeps the lab account's primary key as its login name. The
functions here find that account and set its ``prohibit_login``, email
and full name; they call Forgejo only when ``configured`` is true.
"""

import base64
import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Mapping
from typing import Any

from django.conf import settings

# The admin account the application signs in to Forgejo's API as.
ADMIN_LOGIN = "orgsyndb"
# The source id of Forgejo's local accounts, such as ``orgsyndb``.
# Every other account was made at a sign-in through ``lab``, the only
# source forge-setup adds, whatever id Forgejo gave it.
LOCAL_SOURCE_ID = 0
# The most accounts Forgejo's API gives on one page.
PAGE_SIZE = 50
# Seconds to wait for each answer of Forgejo.
TIMEOUT = 10

Account = dict[str, Any]


class ForgeError(Exception):
    """Forgejo could not be reached, or refused or garbled an answer."""


def configured() -> bool:
    """Tell whether the settings name Forgejo's API and the password of
    its admin account; without both, nothing here calls Forgejo."""
    return bool(settings.ORGSYNDB_FORGE_URL
                and settings.ORGSYNDB_FORGE_PASSWORD)


def call(method: str, path: str, query: Mapping[str, Any] | None = None,
         body: Any = None) -> Any:
    """Send METHOD to PATH below ``ORGSYNDB_FORGE_URL``, with the QUERY
    and the JSON BODY when given, authenticated as ``orgsyndb``; return
    the answer's JSON.

    Raise ForgeError when Forgejo cannot be reached, answers with an
    error status or answers anything but JSON.
    """
    url = settings.ORGSYNDB_FORGE_URL + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    pair = f"{ADMIN_LOGIN}:{settings.ORGSYNDB_FORGE_PASSWORD}"
    headers = {"Accept": "application/json",
               "Authorization": "Basic " + base64.b64encode(
                   pair.encode("utf-8")).decode("ascii")}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data, headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            return json.loads(answer.read() or b"null")
    except urllib.error.HTTPError as exc:
        raise ForgeError(f"{method} {url}: HTTP {exc.code}") from exc
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise ForgeError(f"{method} {url}: {exc}") from exc


def lab_accounts(login_name: str | None = None) -> list[Account]:
    """Return the Forgejo accounts of the source ``lab``, every one or,
    with LOGIN_NAME, those whose login name it is, reading every page:
    the accounts that are not local.
    Raise ForgeError as ``call`` does."""
    query: dict[str, Any] = {"limit": PAGE_SIZE}
    if login_name is not None:
        query["login_name"] = login_name
    found: list[Account] = []
    page = 1
    while True:
        shown = call("GET", "/admin/users", {**query, "page": page})
        if not isinstance(shown, list):
            raise ForgeError("Forgejo's list of users is no list")
        found.extend(shown)
        if len(shown) < PAGE_SIZE:
            break
        page += 1
    return [account for account in found
            if account.get("source_id", LOCAL_SOURCE_ID) != LOCAL_SOURCE_ID
            and (login_name is None
                 or account.get("login_name") == login_name)]


def placeholder(user: Any) -> str:
    """Return the address the Forgejo account of the lab account USER
    holds while USER has none: ``<user name>@noreply.localhost``, since
    Forgejo refuses an empty address."""
    return f"{user.get_username()}@noreply.localhost"


def wanted(user: Any) -> dict[str, Any]:
    """Return what the Forgejo account of the lab account USER should
    hold: ``prohibit_login`` the opposite of its ``is_active``,
    ``full_name`` its display name and ``email`` its address, or
    ``placeholder(USER)`` when it has none."""
    return {"prohibit_login": not user.is_active,
            "full_name": user.display_name,
            "email": user.email or placeholder(user)}


def update(account: Account, values: Mapping[str, Any]) -> None:
    """Set VALUES on the Forgejo ACCOUNT, as listed by ``lab_accounts``,
    and on ACCOUNT itself. Raise ForgeError as ``call`` does, leaving
    ACCOUNT as it was."""
    login = urllib.parse.quote(account["login"], safe="")
    call("PATCH", f"/admin/users/{login}",
         body={"login_name": str(account["login_name"]),
               "source_id": int(account["source_id"]), **values})
    account.update(values)


def push(user: Any) -> bool:
    """Set the Forgejo account of the lab account USER to what
    ``wanted`` gives, in one request; return whether it has one.
    Raise ForgeError as ``call`` does."""
    accounts = lab_accounts(str(user.pk))
    for account in accounts:
        update(account, wanted(user))
    return bool(accounts)


def address(account: Account) -> str:
    """Return the address the Forgejo ACCOUNT holds, in lower case, as
    Forgejo compares addresses."""
    return str(account.get("email") or "").lower()


def bring_in_line() -> Iterator[tuple[Account, dict[str, Any]]]:
    """Set every Forgejo account of the source ``lab`` to its lab
    account, as ``push`` does, and block one whose login name names no
    lab account; yield each account changed with the values set on it,
    and nothing for one already in line.

    An address is given to an account only once no other of these
    accounts holds it. When every remaining change waits for an address
    another of them holds, as when two accounts swap addresses, one of
    the holders is first given its ``placeholder`` address, and is
    yielded with it. An address that stays held, as by an account of no
    lab account, is sent all the same, and Forgejo refuses it.

    Raise ForgeError as ``call`` does, at the first request that fails;
    the accounts yielded before it were changed.
    """
    from accounts.models import User
    accounts = lab_accounts()
    keys = {int(a["login_name"]) for a in accounts
            if str(a.get("login_name", "")).isdigit()}
    users = User.objects.in_bulk(keys)
    pending: list[tuple[Account, dict[str, Any], Any]] = []
    for account in accounts:
        name = str(account.get("login_name", ""))
        user = users.get(int(name)) if name.isdigit() else None
        values = wanted(user) if user else {"prohibit_login": True}
        changes = {key: value for key, value in values.items()
                   if account.get(key) != value}
        if changes:
            pending.append((account, changes, user))

    def free(item: tuple[Account, dict[str, Any], Any]) -> bool:
        target = str(item[1].get("email", "")).lower()
        return not target or not any(
            address(other) == target for other in accounts
            if other is not item[0])

    parked: set[int] = set()
    while pending:
        item = next((item for item in pending if free(item)), None)
        if item is None:
            wanted_addresses = {str(changes["email"]).lower()
                                for _account, changes, _user in pending
                                if "email" in changes}
            holder = next(
                (entry for entry in pending
                 if entry[2] is not None and id(entry[0]) not in parked
                 and address(entry[0]) in wanted_addresses), None)
            if holder is not None:
                spare = {"email": placeholder(holder[2])}
                update(holder[0], spare)
                parked.add(id(holder[0]))
                yield holder[0], spare
                continue
            item = pending[0]
        account, changes, _user = item
        update(account, changes)
        pending.remove(item)
        yield account, changes
