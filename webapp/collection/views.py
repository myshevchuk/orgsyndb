"""The collection's pages: the manifest the builder posts, the ID path
that issues procedure and sequence IDs, and the list of imports."""

import hmac
import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from accounts.models import AccessToken
from collection import importing, issuing
from collection.models import Import, Procedure, Sequence, latest_accepted


def signed(request: HttpRequest, token: str) -> bool:
    """Whether REQUEST carries ``Authorization: Bearer TOKEN``, compared
    in constant time."""
    scheme, _, given = request.headers.get("Authorization", "").partition(
        " ")
    return scheme == "Bearer" and hmac.compare_digest(
        given.encode("utf-8"), token.encode("utf-8"))


@csrf_exempt
def manifest(request: HttpRequest) -> JsonResponse:
    """Take the builder's manifest and answer, in JSON, how it was
    handled (``importing.receive``).

    With ``ORGSYNDB_BUILDER_TOKEN`` empty every request answers 404; a
    request without that token as its bearer token answers 403, one
    whose method is not POST 405, and a body that is not a manifest 400
    with the reason under ``error``. None of these records anything.
    """
    token = settings.ORGSYNDB_BUILDER_TOKEN
    if not token:
        return JsonResponse({"error": "not found"}, status=404)
    if not signed(request, token):
        return JsonResponse({"error": "forbidden"}, status=403)
    if request.method != "POST":
        answer = JsonResponse({"error": "only POST is allowed"}, status=405)
        answer["Allow"] = "POST"
        return answer
    try:
        body = json.loads(request.body)
    except ValueError as error:
        return JsonResponse({"error": f"not JSON: {error}"}, status=400)
    try:
        read = importing.read(body)
    except importing.Malformed as error:
        return JsonResponse({"error": str(error)}, status=400)
    status, answer = importing.receive(read)
    return JsonResponse(answer, status=status)


@csrf_exempt
def ids(request: HttpRequest) -> JsonResponse:
    """Issue a procedure or sequence ID to the account whose access token
    signs the request, and answer 201 with ``{"id": <ID>}``
    (``issuing.issue``).

    The body is ``{"kind": "procedure"}`` or ``{"kind": "sequence"}``.
    A method other than POST answers 405; a request without the
    ``Bearer`` token of an active account 401, whatever session it
    carries; another body 400; and a request the application cannot
    issue an ID for now 409. These answers carry the reason under
    ``error`` and issue nothing.
    """
    if request.method != "POST":
        answer = JsonResponse({"error": "only POST is allowed"}, status=405)
        answer["Allow"] = "POST"
        return answer
    user = AccessToken.authenticate(request.headers.get("Authorization",
                                                        ""))
    if user is None:
        answer = JsonResponse(
            {"error": "an access token of an active account is needed"},
            status=401)
        answer["WWW-Authenticate"] = "Bearer"
        return answer
    try:
        body = json.loads(request.body)
    except ValueError as error:
        return JsonResponse({"error": f"not JSON: {error}"}, status=400)
    kind = body.get("kind") if isinstance(body, dict) else None
    if not isinstance(kind, str) or kind not in issuing.PREFIXES \
            or len(body) != 1:
        return JsonResponse(
            {"error": 'the body is not {"kind": "procedure"} or '
                      '{"kind": "sequence"}'}, status=400)
    try:
        key = issuing.issue(kind, user)
    except issuing.Unavailable as error:
        return JsonResponse({"error": str(error)}, status=409)
    return JsonResponse({"id": key}, status=201)


def imports(request: HttpRequest) -> HttpResponse:
    """List the imports, newest first, below a line on the latest
    accepted import and the procedures and sequences not withdrawn."""
    return render(request, "collection/imports.html", {
        "imports": Import.objects.order_by("-received_at", "-pk"),
        "latest": latest_accepted(),
        "procedures": Procedure.objects.filter(withdrawn=False).count(),
        "sequences": Sequence.objects.filter(withdrawn=False).count(),
    })
