"""Tests for the atomic publication seams."""

from __future__ import annotations

import errno
import os
from typing import TYPE_CHECKING

import pytest

from datamodel_code_generator import _publication as publication_module

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def _transient_replace_error(winerror: int) -> PermissionError:
    error = PermissionError(errno.EACCES, "Access is denied")
    error.winerror = winerror
    return error


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("winerror", [5, 32], ids=["access_denied", "sharing_violation"])
def test_publish_staged_files_retries_transient_windows_replace_error(
    tmp_path: Path, mocker: MockerFixture, winerror: int
) -> None:
    """A target another process briefly holds open on Windows is swapped in once the handle is released."""
    staged = tmp_path / "staged.py"
    staged.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "target.py"
    replace = mocker.patch(
        "os.replace", wraps=os.replace, side_effect=[_transient_replace_error(winerror), mocker.DEFAULT]
    )
    sleep = mocker.patch("time.sleep")

    publication_module.publish_staged_files([(staged, target)])

    assert target.read_text(encoding="utf-8") == "generated\n"
    assert replace.call_count == 2
    sleep.assert_called_once_with(0.05)


@pytest.mark.allow_direct_assert
def test_publish_staged_files_gives_up_after_repeated_transient_replace_errors(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """A target that stays locked is reported after a bounded number of attempts."""
    staged = tmp_path / "staged.py"
    staged.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "target.py"
    replace = mocker.patch("os.replace", side_effect=_transient_replace_error(5))
    sleep = mocker.patch("time.sleep")

    with pytest.raises(PermissionError, match="Access is denied"):
        publication_module.publish_staged_files([(staged, target)])

    assert replace.call_count == 10
    assert sleep.call_count == 9
    assert not target.exists()


@pytest.mark.allow_direct_assert
def test_publish_staged_files_does_not_retry_other_permission_errors(tmp_path: Path, mocker: MockerFixture) -> None:
    """Permission errors that are not Windows sharing conflicts fail immediately."""
    staged = tmp_path / "staged.py"
    staged.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "target.py"
    replace = mocker.patch("os.replace", side_effect=PermissionError(errno.EPERM, "Operation not permitted"))
    sleep = mocker.patch("time.sleep")

    with pytest.raises(PermissionError, match="Operation not permitted"):
        publication_module.publish_staged_files([(staged, target)])

    replace.assert_called_once()
    sleep.assert_not_called()
