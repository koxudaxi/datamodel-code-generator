"""Unit tests for persisted remote reference integrity locks."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import remote_lock
from datamodel_code_generator.remote_lock import RemoteLockError, RemoteReferenceLock

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.allow_direct_assert
def test_remote_lock_normalizes_request_headers_and_replaces_the_observed_closure(tmp_path: Path) -> None:
    """Header order is irrelevant and updates remove resources not reached this run."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    first_url = "https://schemas.example/first.json"
    second_url = "https://schemas.example/second.json"
    headers = [("Authorization", "Bearer lock-secret"), ("X-Trace", "trace")]

    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response(first_url, headers, [("revision", "one")], b"first")
    updater.record_response(second_url, headers, [("revision", "one")], b"second")
    updater.commit()

    verifier = RemoteReferenceLock.open(lockfile, update=False, locked=True)
    verifier.record_response(first_url, list(reversed(headers)), [("revision", "one")], b"first")
    verifier.commit()

    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response(first_url, headers, [("revision", "one")], b"first")
    updater.commit()
    lock_data = json.loads(lockfile.read_text(encoding="utf-8"))
    assert [resource["url"] for resource in lock_data["resources"]] == ["https://schemas.example"]


@pytest.mark.allow_direct_assert
def test_remote_lock_never_persists_url_or_request_secrets(tmp_path: Path) -> None:
    """The persisted identity excludes user info, query values, and header values."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response(
        "https://alice:password@schemas.example:8443/path-secret/schema.json?access_token=token#fragment",
        [("Authorization", "Bearer lock-secret")],
        [("access_token", "token")],
        b"schema",
    )
    updater.commit()

    content = lockfile.read_text(encoding="utf-8")
    lock_data = json.loads(content)
    assert lock_data["resources"][0]["url"] == "https://schemas.example:8443"
    assert "alice" not in content
    assert "password" not in content
    assert "lock-secret" not in content
    assert "access_token" not in content
    assert "path-secret" not in content


@pytest.mark.allow_direct_assert
def test_remote_lock_reports_missing_malformed_unknown_and_changed_entries(tmp_path: Path) -> None:
    """Verification fails closed for each lock integrity error condition."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    with pytest.raises(RemoteLockError, match="not found"):
        RemoteReferenceLock.open(lockfile, update=False, locked=True)

    lockfile.write_text("{}", encoding="utf-8")
    with pytest.raises(RemoteLockError, match="expected version"):
        RemoteReferenceLock.open(lockfile, update=False, locked=False)

    lockfile.unlink()
    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response("https://schemas.example/schema.json", None, None, b"before")
    updater.commit()
    verifier = RemoteReferenceLock.open(lockfile, update=False, locked=True)
    with pytest.raises(RemoteLockError, match="not recorded"):
        verifier.record_response("https://schemas.example/new.json", None, None, b"new")
    with pytest.raises(RemoteLockError, match="content does not match"):
        verifier.record_response("https://schemas.example/schema.json", None, None, b"after")


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("version", [True, 1.0, "1", None])
def test_remote_lock_requires_exact_integer_version_one(tmp_path: Path, version: object) -> None:
    """Booleans and numerically equal non-integers are not lock format versions."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    lockfile.write_text(json.dumps({"version": version, "resources": []}), encoding="utf-8")

    with pytest.raises(RemoteLockError, match="expected version 1"):
        RemoteReferenceLock.open(lockfile, update=False, locked=False)


@pytest.mark.allow_direct_assert
def test_remote_lock_rejects_nondeterministic_repeated_responses_even_when_updating(tmp_path: Path) -> None:
    """An update must not silently choose one of two bodies for the same request."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)

    updater.record_response("https://schemas.example/schema.json", None, None, b"first")
    updater.record_response("https://schemas.example/schema.json", None, None, b"first")
    with pytest.raises(RemoteLockError, match="different content in one generation"):
        updater.record_response("https://schemas.example/schema.json", None, None, b"second")

    assert not lockfile.exists()


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{", "Unable to read remote lock"),
        ('{"version":1,"resources":{}}', "resources must be a list"),
        ('{"version":1,"resources":[null]}', "each resource must be an object"),
        ('{"version":1,"resources":[{}]}', "Invalid remote lock resource"),
        (
            '{"version":1,"resources":[{"request_sha256":"sha256:'
            + "0" * 64
            + '","body_sha256":"sha256:'
            + "1" * 64
            + '","url":"https://alice:password@schemas.example/schema.json?token=secret"}]}',
            "Invalid remote lock resource URL",
        ),
        (
            '{"version":1,"resources":[{"request_sha256":"sha256:'
            + "z" * 64
            + '","body_sha256":"sha256:'
            + "1" * 64
            + '","url":"https://schemas.example"}]}',
            "Invalid remote lock resource",
        ),
        (
            '{"version":1,"resources":[{"request_sha256":"sha256:'
            + "0" * 64
            + '","body_sha256":"sha256:'
            + "1" * 64
            + '","url":"https://[not-an-ipv6"}]}',
            "Invalid remote lock resource URL",
        ),
    ],
)
def test_remote_lock_rejects_malformed_resource_shapes(tmp_path: Path, content: str, message: str) -> None:
    """Malformed persisted data always fails before generation can continue."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    lockfile.write_text(content, encoding="utf-8")

    with pytest.raises(RemoteLockError, match=message):
        RemoteReferenceLock.open(lockfile, update=False, locked=False)


@pytest.mark.allow_direct_assert
def test_remote_lock_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Persisted bytes are always decoded into a clean lock error."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    lockfile.write_bytes(b"\xff")

    with pytest.raises(RemoteLockError, match="Unable to read remote lock"):
        RemoteReferenceLock.open(lockfile, update=False, locked=False)


@pytest.mark.allow_direct_assert
def test_remote_lock_rejects_unparseable_request_urls(tmp_path: Path) -> None:
    """Malformed request URLs cannot escape the lock API as URL parser errors."""
    lock = RemoteReferenceLock.open(tmp_path / "unused.lock", update=True, locked=False)

    with pytest.raises(RemoteLockError, match="Invalid remote lock URL"):
        lock.record_response("https://[not-an-ipv6", None, None, b"body")
    with pytest.raises(RemoteLockError, match="Invalid remote lock URL"):
        remote_lock._display_url("https://[not-an-ipv6")


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    "url",
    [
        "schema.example/file.json",
        "file:///schema.json",
        "https:///schema.json",
        "https://schemas.example:bad/schema.json",
        "https://schemas.example:65536/schema.json",
    ],
)
def test_remote_lock_rejects_invalid_request_scheme_host_and_port(tmp_path: Path, url: str) -> None:
    """Only HTTP(S) URLs with a usable host and port can become request identities."""
    lock = RemoteReferenceLock.open(tmp_path / "unused.lock", update=True, locked=False)

    with pytest.raises(RemoteLockError, match="Invalid remote lock URL"):
        lock.record_response(url, None, None, b"body")


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize(
    "url",
    [
        "ftp://schemas.example",
        "https:///schema.json",
        "https://schemas.example:bad",
        "https://schemas.example:65536",
    ],
)
def test_remote_lock_rejects_invalid_persisted_scheme_host_and_port(tmp_path: Path, url: str) -> None:
    """Malformed persisted origins fail closed with a lock-specific diagnostic."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    lockfile.write_text(
        json.dumps({
            "version": 1,
            "resources": [
                {
                    "request_sha256": f"sha256:{'0' * 64}",
                    "body_sha256": f"sha256:{'1' * 64}",
                    "url": url,
                }
            ],
        }),
        encoding="utf-8",
    )

    with pytest.raises(RemoteLockError, match="Invalid remote lock resource URL"):
        RemoteReferenceLock.open(lockfile, update=False, locked=False)


@pytest.mark.allow_direct_assert
def test_remote_lock_rejects_duplicate_identities_and_normalizes_unusual_urls(tmp_path: Path) -> None:
    """Reject duplicate identities while keeping lock display URLs safe and canonical."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response("https://[2001:db8::1]/schema.json", None, None, b"schema")
    updater.commit()
    resource = json.loads(lockfile.read_text(encoding="utf-8"))["resources"][0]
    assert resource["url"] == "https://[2001:db8::1]"
    with pytest.raises(RemoteLockError, match="Invalid remote lock URL"):
        remote_lock._display_url("https://schemas.example:bad/schema.json")

    lockfile.write_text(json.dumps({"version": 1, "resources": [resource, resource]}), encoding="utf-8")
    with pytest.raises(RemoteLockError, match="duplicate request identity"):
        RemoteReferenceLock.open(lockfile, update=False, locked=False)


@pytest.mark.allow_direct_assert
def test_remote_lock_cleans_up_after_atomic_write_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both pre-rename and post-rename failures leave no partial target lock."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response("https://schemas.example/schema.json", None, None, b"schema")

    def raise_os_error(*_args: object, **_kwargs: object) -> None:
        message = "full"
        raise OSError(message)

    monkeypatch.setattr(remote_lock.tempfile, "NamedTemporaryFile", raise_os_error)
    with pytest.raises(RemoteLockError, match="Unable to update remote lock"):
        updater.commit()
    assert not lockfile.exists()

    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response("https://schemas.example/schema.json", None, None, b"schema")
    monkeypatch.undo()
    monkeypatch.setattr(remote_lock.Path, "replace", raise_os_error)
    monkeypatch.setattr(remote_lock.Path, "unlink", raise_os_error)
    with pytest.raises(RemoteLockError, match="Unable to update remote lock"):
        updater.commit()


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("failure", ["write", "fsync"])
def test_remote_lock_atomic_failures_remove_temps_and_allow_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """A transient pre-replace failure leaves no temp file and does not commit the collector."""
    lockfile = tmp_path / "datamodel-codegen.lock"
    updater = RemoteReferenceLock.open(lockfile, update=True, locked=False)
    updater.record_response("https://schemas.example/schema.json", None, None, b"schema")

    def raise_os_error(*_args: object, **_kwargs: object) -> None:
        message = "full"
        raise OSError(message)

    if failure == "write":
        original_named_temporary_file = remote_lock.tempfile.NamedTemporaryFile

        class FailingTemporaryFile:
            def __init__(self, temporary_file: object) -> None:
                self._temporary_file = temporary_file
                self.name = temporary_file.name  # type: ignore[attr-defined]

            def __enter__(self) -> FailingTemporaryFile:  # noqa: PYI034
                self._temporary_file.__enter__()  # type: ignore[attr-defined]
                return self

            def __exit__(self, *args: object) -> None:
                self._temporary_file.__exit__(*args)  # type: ignore[attr-defined]

            def write(self, _content: str) -> None:
                raise_os_error()

        monkeypatch.setattr(
            remote_lock.tempfile,
            "NamedTemporaryFile",
            lambda **kwargs: FailingTemporaryFile(original_named_temporary_file(**kwargs)),
        )
    else:
        monkeypatch.setattr(remote_lock.os, "fsync", raise_os_error)

    with pytest.raises(RemoteLockError, match="Unable to update remote lock"):
        updater.commit()
    assert not lockfile.exists()
    assert not list(tmp_path.glob(".datamodel-codegen.lock.*"))

    monkeypatch.undo()
    updater.commit()
    assert lockfile.is_file()
