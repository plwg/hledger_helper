from __future__ import annotations

import base64
import binascii
import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from hhelper.helpers.backup import backup_file
from hhelper.helpers.safe_write import safe_write
from hhelper.web.csv_import import (
    RulesPathError,
    find_rules_files,
    match_rules,
    preview_csv,
    resolve_rules_path,
)

if TYPE_CHECKING:
    from pathlib import Path

# Bank exports are small; this keeps a stray upload from filling memory
MAX_BODY_BYTES = 20 * 1024 * 1024

LOCAL_HOSTS = ("127.0.0.1", "localhost")


class ApiError(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _index_html() -> bytes:
    return files("hhelper.web").joinpath("static/index.html").read_bytes()


def _mtime_ns(path: Path) -> str:
    # A string: nanoseconds since 1970 are beyond a JavaScript number's precision
    return str(path.stat().st_mtime_ns)


class Api:
    # The page's operations, kept apart from HTTP so they can be tested directly
    def __init__(self, rules_dir: Path) -> None:
        self.rules_dir = rules_dir

    def _resolve(self, relative: object) -> Path:
        if not isinstance(relative, str):
            raise ApiError(HTTPStatus.BAD_REQUEST, "A rules file path is required")
        try:
            return resolve_rules_path(self.rules_dir, relative)
        except RulesPathError as error:
            raise ApiError(HTTPStatus.BAD_REQUEST, str(error)) from error

    def list_rules(self) -> dict[str, Any]:
        return {
            "rules_dir": str(self.rules_dir),
            "rules": find_rules_files(self.rules_dir),
        }

    def match(self, csv_name: str) -> dict[str, Any]:
        return asdict(match_rules(csv_name, find_rules_files(self.rules_dir)))

    def read_rules(self, relative: str) -> dict[str, Any]:
        path = self._resolve(relative)
        if not path.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, f"No such rules file: {relative}")
        return {"path": relative, "content": path.read_text(), "mtime": _mtime_ns(path)}

    def save_rules(self, body: dict[str, Any]) -> dict[str, Any]:
        relative = body.get("path")
        path = self._resolve(relative)
        content = body.get("content")
        if not isinstance(content, str):
            raise ApiError(HTTPStatus.BAD_REQUEST, "The rules content is missing")

        # None creates a new file; a number must match the file on disk, so
        # an edit made elsewhere since the page loaded it is not overwritten
        expected = body.get("mtime")
        if expected is None:
            if path.exists():
                raise ApiError(HTTPStatus.CONFLICT, f"{relative} already exists")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        else:
            if not path.is_file():
                raise ApiError(HTTPStatus.NOT_FOUND, f"No such rules file: {relative}")
            if _mtime_ns(path) != expected:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    f"{relative} changed on disk since it was opened; reload it",
                )
            backup_file(path)
            safe_write(path, content)

        return {"path": relative, "mtime": _mtime_ns(path)}

    def preview(self, body: dict[str, Any]) -> dict[str, Any]:
        csv_name = body.get("csv_name")
        if not isinstance(csv_name, str) or not csv_name:
            raise ApiError(HTTPStatus.BAD_REQUEST, "The CSV file name is missing")

        try:
            csv_content = base64.b64decode(body.get("csv_base64", ""), validate=True)
        except (binascii.Error, TypeError) as error:
            raise ApiError(HTTPStatus.BAD_REQUEST, "The CSV is not valid") from error

        path = self._resolve(body.get("rules"))
        rules_content = body.get("rules_content")
        if rules_content is not None and not isinstance(rules_content, str):
            raise ApiError(HTTPStatus.BAD_REQUEST, "The rules content is not text")
        if rules_content is None and not path.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, f"No such rules file: {path.name}")

        return asdict(preview_csv(csv_content, csv_name, path, rules_content))


def make_handler(api: Api) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "hhelper"

        def log_message(self, format: str, *args: Any) -> None:
            # Request lines would print file names to the terminal; stay quiet
            pass

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: HTTPStatus, data: dict[str, Any]) -> None:
            self._send(status, json.dumps(data).encode(), "application/json")

        def _check_origin(self) -> None:
            # Only this machine's pages may talk to the server: the Host check
            # stops DNS rebinding, the Origin check stops other sites' forms
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in LOCAL_HOSTS:
                raise ApiError(HTTPStatus.FORBIDDEN, "Open the page via localhost")

            origin = self.headers.get("Origin")
            if origin is not None and urlsplit(origin).hostname not in LOCAL_HOSTS:
                raise ApiError(HTTPStatus.FORBIDDEN, "Cross-site request refused")

        def _read_json(self) -> dict[str, Any]:
            if self.headers.get_content_type() != "application/json":
                raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send JSON")

            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "File too large")

            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Invalid JSON") from error

            if not isinstance(data, dict):
                raise ApiError(HTTPStatus.BAD_REQUEST, "Expected a JSON object")
            return data

        def _handle(self, method: str) -> None:
            try:
                self._check_origin()
                url = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}

                if method == "GET" and url.path == "/":
                    self._send(HTTPStatus.OK, _index_html(), "text/html; charset=utf-8")
                    return

                routes = {
                    ("GET", "/api/rules"): lambda: api.list_rules(),
                    ("GET", "/api/rules/file"): lambda: api.read_rules(
                        query.get("path", "")
                    ),
                    ("PUT", "/api/rules/file"): lambda: api.save_rules(
                        self._read_json()
                    ),
                    ("GET", "/api/match"): lambda: api.match(query.get("name", "")),
                    ("POST", "/api/preview"): lambda: api.preview(self._read_json()),
                }
                route = routes.get((method, url.path))
                if route is None:
                    raise ApiError(HTTPStatus.NOT_FOUND, "Not found")

                self._json(HTTPStatus.OK, route())

            except ApiError as error:
                self._json(error.status, {"error": error.message})
            except OSError as error:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

        def do_GET(self) -> None:
            self._handle("GET")

        def do_POST(self) -> None:
            self._handle("POST")

        def do_PUT(self) -> None:
            self._handle("PUT")

    return Handler


def make_server(rules_dir: Path, port: int) -> ThreadingHTTPServer:
    # Bound to the loopback address only: the page edits files on this machine
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(Api(rules_dir)))


def serve(rules_dir: Path, port: int) -> None:
    server = make_server(rules_dir, port)
    print(f"CSV import page: http://127.0.0.1:{server.server_address[1]}/")
    print(f"Rules folder: {rules_dir}")
    print("Press Ctrl-C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
