"""HTTP Request Router & Middleware Pipeline."""
from typing import Any, Callable, Dict, List


class RequestRouter:
    """Dispatches HTTP requests through composable middleware pipeline."""

    def __init__(self) -> None:
        self._middlewares: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []
        self._routes: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def use(self, middleware: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._middlewares.append(middleware)

    def route(self, path: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._routes[path] = handler

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = request
        for mw in self._middlewares:
            req = mw(req)
        path = req.get("path", "/")
        handler = self._routes.get(path)
        if not handler:
            return {"status": 404, "body": "Not Found"}
        return handler(req)
