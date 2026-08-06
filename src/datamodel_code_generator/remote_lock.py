"""Integrity locks for remote schema resources.

The lock deliberately records safe display origins and SHA-256 digests only.
``request_sha256`` is an opaque digest of the complete request material,
including credentials and query values when configured; those values are never
persisted directly. Local mirror paths and response bodies never leave the
generation process either.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TypeGuard, cast
from urllib.parse import SplitResult, urlsplit, urlunsplit

if TYPE_CHECKING:
    from collections.abc import Sequence


_LOCK_VERSION = 1
_SHA256_PREFIX = "sha256:"


class RemoteLockError(Exception):
    """Raised when a remote resource does not match its integrity lock."""


@dataclass(frozen=True, slots=True)
class RemoteLockEntry:
    """One safe-to-persist remote resource identity and its raw body digest."""

    request_sha256: str
    url: str
    body_sha256: str


def _sha256(value: bytes) -> str:
    return f"{_SHA256_PREFIX}{hashlib.sha256(value).hexdigest()}"


def _split_remote_url(url: str, *, persisted: bool = False) -> tuple[SplitResult, int | None]:
    """Parse and validate the HTTP(S) origin fields used by a lock entry."""
    message = "Invalid remote lock resource URL" if persisted else f"Invalid remote lock URL: {url!r}"
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise RemoteLockError(message) from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise RemoteLockError(message)
    return parsed, port


def _display_url(url: str) -> str:
    """Return a safe origin suitable for a committed lock.

    URL paths are deliberately omitted as deployments frequently put access
    tokens in a path segment. The request digest remains the identity; this
    field is only safe diagnostic context.
    """
    parsed, port = _split_remote_url(url)
    hostname = parsed.hostname
    assert hostname is not None
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, "", "", ""))


def _request_sha256(
    url: str,
    headers: Sequence[tuple[str, str]] | None,
    query_parameters: Sequence[tuple[str, str]] | None,
) -> str:
    """Hash canonical request material without retaining its secret values."""
    parsed, _ = _split_remote_url(url)
    canonical = {
        "headers": sorted((name.lower(), value) for name, value in headers or ()),
        "query_parameters": list(query_parameters or ()),
        "url": urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")),
    }
    encoded = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return _sha256(encoded)


def _is_sha256(value: object) -> TypeGuard[str]:
    if not isinstance(value, str) or not value.startswith(_SHA256_PREFIX) or len(value) != len(_SHA256_PREFIX) + 64:
        return False
    try:
        bytes.fromhex(value.removeprefix(_SHA256_PREFIX))
    except ValueError:
        return False
    return True


def _validate_persisted_display_url(url: str) -> None:
    """Reject malformed display URLs before lock verification can proceed."""
    parsed, _ = _split_remote_url(url, persisted=True)
    has_sensitive_url_parts = any((parsed.query, parsed.fragment, parsed.username, parsed.password))
    if parsed.scheme not in {"http", "https"} or has_sensitive_url_parts:
        msg = "Invalid remote lock resource URL"
        raise RemoteLockError(msg)


def _entry_from_data(value: object) -> RemoteLockEntry:
    if not isinstance(value, dict):
        msg = "Invalid remote lock: each resource must be an object"
        raise RemoteLockError(msg)
    resource = cast("dict[str, object]", value)
    request_sha256 = resource.get("request_sha256")
    url = resource.get("url")
    body_sha256 = resource.get("body_sha256")
    if not _is_sha256(request_sha256) or not _is_sha256(body_sha256) or not isinstance(url, str):
        msg = "Invalid remote lock resource"
        raise RemoteLockError(msg)
    _validate_persisted_display_url(url)
    return RemoteLockEntry(request_sha256=request_sha256, url=url, body_sha256=body_sha256)


def _read_entries(path: Path) -> dict[str, RemoteLockEntry]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = f"Unable to read remote lock {path}: {exc}"
        raise RemoteLockError(msg) from exc
    version = data.get("version") if isinstance(data, dict) else None
    if not isinstance(data, dict) or type(version) is not int or version != _LOCK_VERSION:
        msg = f"Invalid remote lock {path}: expected version {_LOCK_VERSION}"
        raise RemoteLockError(msg)
    resources = data.get("resources")
    if not isinstance(resources, list):
        msg = f"Invalid remote lock {path}: resources must be a list"
        raise RemoteLockError(msg)
    entries: dict[str, RemoteLockEntry] = {}
    for resource in resources:
        entry = _entry_from_data(resource)
        if entry.request_sha256 in entries:
            msg = f"Invalid remote lock {path}: duplicate request identity"
            raise RemoteLockError(msg)
        entries[entry.request_sha256] = entry
    return entries


def _remove_temporary_file(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink()


@dataclass(slots=True)
class RemoteReferenceLock:
    """Collect and verify all remote bytes for exactly one generation.

    ``commit()`` is intentionally explicit so a future batch executor can
    share a collector across targets and write only after every target succeeds.
    """

    path: Path
    update: bool
    _entries: dict[str, RemoteLockEntry]
    _seen: dict[str, RemoteLockEntry] = field(default_factory=dict)
    _committed: bool = False

    @classmethod
    def open(cls, path: Path, *, update: bool, locked: bool) -> RemoteReferenceLock:
        """Open an existing lock or prepare a new one for an explicit update."""
        if path.is_file():
            return cls(path=path, update=update, _entries=_read_entries(path))
        if locked:
            msg = f"Remote lock file not found: {path}"
            raise RemoteLockError(msg)
        return cls(path=path, update=update, _entries={})

    def record_response(
        self,
        url: str,
        headers: Sequence[tuple[str, str]] | None,
        query_parameters: Sequence[tuple[str, str]] | None,
        body: bytes,
    ) -> None:
        """Validate or stage the raw bytes returned for one HTTP(S) request."""
        request_sha256 = _request_sha256(url, headers, query_parameters)
        entry = RemoteLockEntry(
            request_sha256=request_sha256,
            url=_display_url(url),
            body_sha256=_sha256(body),
        )
        if (seen_entry := self._seen.get(request_sha256)) is not None:
            if seen_entry.body_sha256 != entry.body_sha256:
                msg = f"Remote resource returned different content in one generation: {entry.url}"
                raise RemoteLockError(msg)
            return
        if (locked_entry := self._entries.get(request_sha256)) is None:
            if self.update:
                self._entries[request_sha256] = entry
                self._seen[request_sha256] = entry
                return
            msg = f"Remote resource is not recorded in lock: {entry.url}"
            raise RemoteLockError(msg)
        if locked_entry.body_sha256 == entry.body_sha256:
            self._seen[request_sha256] = entry
            return
        if self.update:
            self._entries[request_sha256] = entry
            self._seen[request_sha256] = entry
            return
        msg = f"Remote resource content does not match lock: {entry.url}"
        raise RemoteLockError(msg)

    def commit(self) -> None:
        """Atomically persist a successful explicit update at most once."""
        if self._committed or not self.update:
            return
        payload = {
            "resources": [asdict(entry) for _, entry in sorted(self._seen.items())],
            "version": _LOCK_VERSION,
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        try:
            with contextlib.ExitStack() as cleanup:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
                    mode="w",
                    encoding="utf-8",
                    dir=self.path.parent,
                    prefix=f".{self.path.name}.",
                    delete=False,
                )
                temporary_path = Path(temporary_file.name)
                # Register cleanup immediately after allocation: write(), flush(),
                # fsync(), and close() can all fail before replacement.
                cleanup.callback(_remove_temporary_file, temporary_path)
                with temporary_file:
                    temporary_file.write(content)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                temporary_path.replace(self.path)
                self._committed = True
        except OSError as exc:
            msg = f"Unable to update remote lock {self.path}: {exc}"
            raise RemoteLockError(msg) from exc
