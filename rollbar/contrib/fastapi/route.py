__all__ = ['add_to']

import logging
import sys
from typing import Callable, Type

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.types import ASGIApp

import rollbar
from rollbar.contrib.fastapi.utils import fastapi_min_version
from rollbar.contrib.fastapi.utils import get_installed_middlewares

log = logging.getLogger(__name__)


@fastapi_min_version('0.41.0')
def add_to(app: ASGIApp) -> Type[APIRoute]:
    installed_middlewares = get_installed_middlewares(app)
    if installed_middlewares:
        log.warn(
            f'Detected installed middlewares {installed_middlewares}'
            ' while loading Rollbar route handler.'
            ' This can cause duplicated occurrences.'
        )

    # Route handler must be added before adding routes
    if len(app.routes) == 4:
        route_class = app.router.route_class
    elif len(app.routes) == 0:
        route_class = app.route_class
    else:
        log.error(
            'RollbarLoggingRoute has to be added to a bare router. '
            'See docs for more details.'
        )
        return

    class RollbarLoggingRoute(route_class):
        def get_route_handler(self) -> Callable:
            original_router_handler = super().get_route_handler()

            async def custom_route_handler(request: Request) -> Response:
                try:
                    return await original_router_handler(request)
                except Exception:
                    await request.body()
                    exc_info = sys.exc_info()
                    rollbar.report_exc_info(exc_info, request)
                    raise

            return custom_route_handler

    if len(app.routes) == 4:
        app.router.route_class = RollbarLoggingRoute
    elif len(app.routes) == 0:
        app.route_class = RollbarLoggingRoute
    return RollbarLoggingRoute
