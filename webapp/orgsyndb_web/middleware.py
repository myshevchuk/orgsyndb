"""Middleware that speaks the language of the collection."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import translation

from collection.models import latest_accepted

DEFAULT_LANGUAGE = "de"


def site_language() -> str:
    """Return the language of the latest accepted import of the
    collection, or ``de`` while none was accepted."""
    latest = latest_accepted()
    return latest.language if latest is not None else DEFAULT_LANGUAGE


class CollectionLanguageMiddleware:
    """Activate the language of the collection (``site_language``) for
    each request, set ``request.LANGUAGE_CODE`` to it and answer with it
    as ``Content-Language``."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]
                 ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = site_language()
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()
        response.headers.setdefault("Content-Language", language)
        return response
