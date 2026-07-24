"""Coordinate request-local access to process-wide generation state."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from threading import Condition, Lock, get_ident, local
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_CONTEXT = Condition(Lock())
_ACTIVE_CWD: str | None = None
_ACTIVE_READERS = 0
_WRITER_THREAD: int | None = None
_WRITER_DEPTH = 0
_WRITER_BLOCK_SHARED = 0
_WRITER_CLOSING = False
_WRITER_RETAINED_READERS = 0
_WRITER_SUSPENDED_READERS = 0
_WAITING_WRITERS = 0
_UPGRADING_THREAD: int | None = None
_LOCAL = local()


def process_cwd() -> str:
    """Return the request-visible cwd without entering a process context."""
    if get_ident() == _WRITER_THREAD:
        return os.getcwd()  # noqa: PTH109
    while True:
        if (active_cwd := _ACTIVE_CWD) is not None:
            return active_cwd
        cwd = os.getcwd()  # noqa: PTH109
        if _ACTIVE_CWD is None:  # pragma: no branch - retry only when a writer races this snapshot
            return cwd


def _activate(cwd: str) -> None:
    global _ACTIVE_CWD  # noqa: PLW0603

    if _ACTIVE_CWD is None:
        _ACTIVE_CWD = cwd


def _deactivate() -> None:
    global _ACTIVE_CWD  # noqa: PLW0603

    if _ACTIVE_READERS or _WRITER_THREAD is not None:
        return
    _ACTIVE_CWD = None
    _CONTEXT.notify_all()


def _enter_shared(*, borrow_writer: bool) -> tuple[bool, bool, int, str]:
    global _ACTIVE_READERS, _WRITER_DEPTH  # noqa: PLW0603

    thread_id = get_ident()
    with _CONTEXT:
        if thread_id == _WRITER_THREAD:
            _WRITER_DEPTH += 1
            return True, False, _WRITER_RETAINED_READERS, os.getcwd()  # noqa: PTH109

        reader_depth = getattr(_LOCAL, "reader_depth", 0)
        while True:
            if (
                borrow_writer
                and _WRITER_THREAD is not None
                and not _WRITER_BLOCK_SHARED
                and (not _WRITER_CLOSING or reader_depth)
            ):
                cwd = _ACTIVE_CWD or os.getcwd()  # noqa: PTH109
                break
            if _WRITER_THREAD is None and (not _WAITING_WRITERS or reader_depth):
                cwd = os.getcwd()  # noqa: PTH109
                if _ACTIVE_CWD in {None, cwd}:
                    break
                if reader_depth:
                    msg = "A process context cannot change its working directory while it is active."
                    raise RuntimeError(msg)
            _CONTEXT.wait()
        _activate(cwd)
        _ACTIVE_READERS += 1
        _LOCAL.reader_depth = reader_depth + 1
        return False, False, 0, cwd


def _enter_exclusive(*, allow_shared: bool) -> tuple[bool, bool, int, str]:  # noqa: PLR0914
    global _ACTIVE_READERS, _UPGRADING_THREAD, _WAITING_WRITERS, _WRITER_BLOCK_SHARED, _WRITER_DEPTH, _WRITER_RETAINED_READERS, _WRITER_SUSPENDED_READERS, _WRITER_THREAD  # noqa: E501, PLW0603

    thread_id = get_ident()
    with _CONTEXT:
        if thread_id == _WRITER_THREAD:
            _WRITER_DEPTH += 1
            blocks_shared = not allow_shared
            _WRITER_BLOCK_SHARED += blocks_shared
            return True, blocks_shared, _WRITER_RETAINED_READERS, os.getcwd()  # noqa: PTH109

        reader_depth = getattr(_LOCAL, "reader_depth", 0)
        if reader_depth and os.getcwd() != _ACTIVE_CWD:  # noqa: PTH109
            msg = "A process context cannot change its working directory while it is active."
            raise RuntimeError(msg)
        _WAITING_WRITERS += 1
        suspended_readers = 0
        claimed_upgrade = False
        try:
            if reader_depth:
                if _WRITER_THREAD is not None or _UPGRADING_THREAD is not None:
                    _ACTIVE_READERS -= reader_depth
                    suspended_readers = reader_depth
                    _CONTEXT.notify_all()
                while _UPGRADING_THREAD is not None:
                    _CONTEXT.wait()
                _UPGRADING_THREAD = thread_id
                claimed_upgrade = True
            retained_readers = reader_depth - suspended_readers
            while (
                _WRITER_THREAD is not None
                or retained_readers != _ACTIVE_READERS
                or (_UPGRADING_THREAD is not None and thread_id != _UPGRADING_THREAD)
            ):
                _CONTEXT.wait()
            cwd = os.getcwd()  # noqa: PTH109
            _activate(cwd)
            _WRITER_THREAD = thread_id
            _WRITER_DEPTH = 1
            _WRITER_RETAINED_READERS = retained_readers
            _WRITER_SUSPENDED_READERS = suspended_readers
            blocks_shared = not allow_shared
            _WRITER_BLOCK_SHARED = int(blocks_shared)
        except BaseException:
            if claimed_upgrade:
                _UPGRADING_THREAD = None
            if suspended_readers:
                _ACTIVE_READERS += suspended_readers
            _ = _UPGRADING_THREAD, _ACTIVE_READERS
            raise
        else:
            return True, blocks_shared, retained_readers, cwd
        finally:
            _WAITING_WRITERS -= 1
            _CONTEXT.notify_all()


def _close_writer(retained_readers: int) -> None:
    global _WRITER_CLOSING  # noqa: PLW0603

    with _CONTEXT:
        _WRITER_CLOSING = True
        while retained_readers < _ACTIVE_READERS:
            _CONTEXT.wait()


def _reopen_writer() -> None:
    global _WRITER_CLOSING  # noqa: PLW0603

    with _CONTEXT:
        _WRITER_CLOSING = False
        _CONTEXT.notify_all()


def _exit(*, writer: bool, blocks_shared: bool, retained_readers: int) -> None:
    global _ACTIVE_READERS, _UPGRADING_THREAD, _WRITER_BLOCK_SHARED, _WRITER_CLOSING, _WRITER_DEPTH, _WRITER_RETAINED_READERS, _WRITER_SUSPENDED_READERS, _WRITER_THREAD  # noqa: E501, PLW0603

    with _CONTEXT:
        if writer:
            if _WRITER_DEPTH == 1:
                _WRITER_CLOSING = True
                while retained_readers < _ACTIVE_READERS:
                    _CONTEXT.wait()
            _WRITER_BLOCK_SHARED -= blocks_shared
            _WRITER_DEPTH -= 1
            if _WRITER_DEPTH == 0:
                _ACTIVE_READERS += _WRITER_SUSPENDED_READERS
                _WRITER_THREAD = None
                _WRITER_CLOSING = False
                _WRITER_RETAINED_READERS = 0
                _WRITER_SUSPENDED_READERS = 0
                _ = _WRITER_SUSPENDED_READERS
                if get_ident() == _UPGRADING_THREAD:
                    _UPGRADING_THREAD = None
        else:
            _ACTIVE_READERS -= 1
            if _LOCAL.reader_depth == 1:
                del _LOCAL.reader_depth
            else:
                _LOCAL.reader_depth -= 1
        _deactivate()
        _CONTEXT.notify_all()


@contextmanager
def process_context(
    *,
    exclusive: bool = False,
    allow_shared: bool = False,
    borrow_writer: bool = True,
) -> Iterator[str]:
    """Hold a request-local view of cwd and other process-wide import state."""
    writer, blocks_shared, retained_readers, cwd = (
        _enter_exclusive(allow_shared=allow_shared) if exclusive else _enter_shared(borrow_writer=borrow_writer)
    )
    try:
        yield cwd
    finally:
        _exit(writer=writer, blocks_shared=blocks_shared, retained_readers=retained_readers)


@contextmanager
def process_chdir(path: str) -> Iterator[None]:
    """Change cwd while preventing it from moving under a shared request."""
    writer, blocks_shared, retained_readers, _ = _enter_exclusive(allow_shared=True)
    try:
        _close_writer(retained_readers)
        previous_cwd = os.getcwd()  # noqa: PTH109
        try:
            target = Path(path)
            os.chdir(target if target.is_dir() else target.parent)
        finally:
            _reopen_writer()
        try:
            yield
        finally:
            _close_writer(retained_readers)
            try:
                os.chdir(previous_cwd)
            finally:
                _reopen_writer()
    finally:
        _exit(writer=writer, blocks_shared=blocks_shared, retained_readers=retained_readers)
