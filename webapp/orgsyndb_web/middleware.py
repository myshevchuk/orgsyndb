"""Middleware that speaks the language of the collection index."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import translation

from orgsyndb_web import index


class IndexLanguageMiddleware:
    """Activate the site language of the collection index for each
    request, and set ``request.LANGUAGE_CODE`` to it."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]
                 ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = index.current().language
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()
        response.headers.setdefault("Content-Language", language)
        return response
