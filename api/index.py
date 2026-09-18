"""Vercel serverless entrypoint — exposes the NEXUS FastAPI app.

Vercel rewrites every path to /api/index (see vercel.json), which would
hide the original URL. The rewrite appends ?__route__=/original/path and
this middleware restores it before FastAPI routing.
"""
from urllib.parse import parse_qsl, urlencode

from nexus.server import app as fastapi_app  # noqa: F401

_ROUTE_PARAM = "__route__"


class RestoreRouteMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            qs = parse_qsl(scope.get("query_string", b"").decode("latin-1"))
            route = None
            rest = []
            for k, v in qs:
                if k == _ROUTE_PARAM and route is None:
                    route = v
                else:
                    rest.append((k, v))
            if route:
                scope["path"] = route or "/"
                scope["raw_path"] = route.encode("latin-1")
                scope["query_string"] = urlencode(rest).encode("latin-1")
        await self.app(scope, receive, send)


app = RestoreRouteMiddleware(fastapi_app)
