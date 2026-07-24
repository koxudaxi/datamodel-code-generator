"""Tests for request-local process and template-data contexts."""

from __future__ import annotations

import os
from collections import OrderedDict, defaultdict, deque
from pathlib import Path
from threading import Barrier, Event, Thread
from typing import Any

import pytest
from typing_extensions import Self

from datamodel_code_generator import (
    _copy_extra_template_data,
    _copy_extra_template_value,
    _GenerationTemplateData,
    chdir,
)
from datamodel_code_generator._process_context import process_chdir, process_context, process_cwd


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("exclusive", [False, True])
def test_process_context_rejects_recursive_cwd_changes(tmp_path: Path, *, exclusive: bool) -> None:
    """Reject a recursive request after its thread changes cwd unexpectedly."""
    original_cwd = Path.cwd()
    with process_context():
        os.chdir(tmp_path)
        try:
            with pytest.raises(RuntimeError, match="cannot change"), process_context(exclusive=exclusive):
                pass  # pragma: no cover - entering the context raises
        finally:
            os.chdir(original_cwd)


@pytest.mark.allow_direct_assert
def test_process_context_tracks_nested_shared_depth() -> None:
    """Restore thread-local reader depth after nested shared contexts."""
    assert process_cwd() == str(Path.cwd())
    with process_context(), process_context():
        pass


@pytest.mark.allow_direct_assert
def test_process_context_serializes_concurrent_reader_upgrades() -> None:
    """Allow concurrent readers to upgrade without retaining each other."""
    barrier = Barrier(2)
    entered: list[int] = []
    errors: list[Exception] = []

    def upgrade(index: int) -> None:
        try:
            with process_context():
                barrier.wait(timeout=5)
                with process_context(exclusive=True):
                    entered.append(index)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            errors.append(exc)

    threads = [Thread(target=upgrade, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert sorted(entered) == [0, 1]
    assert all(not thread.is_alive() for thread in threads)


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("claim_upgrade", [False, True])
def test_process_context_restores_suspended_reader_after_interrupted_upgrade(
    monkeypatch: pytest.MonkeyPatch,
    *,
    claim_upgrade: bool,
) -> None:
    """Restore coordinator state when an abnormal wait interrupts an upgrade."""
    import datamodel_code_generator._process_context as context_state

    reader_entered = Event()
    release_reader = Event()

    def hold_reader() -> None:
        with process_context():
            reader_entered.set()
            release_reader.wait(timeout=5)

    reader_thread = Thread(target=hold_reader)
    reader_thread.start()
    assert reader_entered.wait(timeout=5)

    wait_calls = 0

    def interrupt_wait() -> None:
        nonlocal wait_calls

        wait_calls += 1
        if claim_upgrade and wait_calls == 1:
            context_state._UPGRADING_THREAD = None
            return
        msg = "interrupted upgrade"
        raise RuntimeError(msg)

    with process_context():
        monkeypatch.setattr(context_state, "_UPGRADING_THREAD", -1)
        monkeypatch.setattr(context_state._CONTEXT, "wait", interrupt_wait)
        with pytest.raises(RuntimeError, match="interrupted upgrade"), process_context(exclusive=True):
            pass  # pragma: no cover - entering the context raises

    release_reader.set()
    reader_thread.join(timeout=5)

    assert wait_calls == (2 if claim_upgrade else 1)
    assert not reader_thread.is_alive()


@pytest.mark.allow_direct_assert
def test_process_context_preserves_retained_readers_for_reentrant_chdir(tmp_path: Path) -> None:
    """Carry an upgraded reader count into a reentrant cwd change."""
    completed = Event()

    def change_cwd() -> None:
        with (
            process_context(),
            process_context(exclusive=True, allow_shared=True),
            process_chdir(str(tmp_path)),
        ):
            completed.set()

    thread = Thread(target=change_cwd)
    thread.start()
    thread.join(timeout=5)

    assert completed.is_set()
    assert not thread.is_alive()


@pytest.mark.allow_direct_assert
def test_process_cwd_uses_writer_directory_for_its_own_thread(tmp_path: Path) -> None:
    """Expose the legacy output cwd to reentrant work on the writer thread."""
    with process_chdir(str(tmp_path)):
        assert process_cwd() == str(tmp_path)
        with process_context() as nested_cwd:
            assert nested_cwd == str(tmp_path)


@pytest.mark.allow_direct_assert
def test_process_context_borrowed_reader_keeps_logical_cwd(tmp_path: Path) -> None:
    """Do not expose a writer's temporary cwd as another request's root."""
    original_cwd = str(Path.cwd())
    writer_entered = Event()
    reader_done = Event()
    observed: list[tuple[str, str, str]] = []

    def writer() -> None:
        with process_chdir(str(tmp_path)):
            writer_entered.set()
            reader_done.wait(timeout=5)

    def reader() -> None:
        with process_context() as caller_cwd:
            observed.append((process_cwd(), caller_cwd, str(Path.cwd())))
        reader_done.set()

    writer_thread = Thread(target=writer)
    reader_thread = Thread(target=reader)
    writer_thread.start()
    assert writer_entered.wait(timeout=5)
    reader_thread.start()
    reader_thread.join(timeout=5)
    writer_thread.join(timeout=5)

    assert observed == [(original_cwd, original_cwd, str(tmp_path))]
    assert not reader_thread.is_alive()
    assert not writer_thread.is_alive()


@pytest.mark.allow_direct_assert
def test_process_shared_context_waits_for_blocking_writer() -> None:
    """Wait for an exclusive context that does not admit borrowed readers."""
    writer_entered = Event()
    release_writer = Event()
    reader_entered = Event()

    def writer() -> None:
        with process_context(exclusive=True):
            writer_entered.set()
            release_writer.wait(timeout=5)

    def reader() -> None:
        with process_context(borrow_writer=False):
            reader_entered.set()

    writer_thread = Thread(target=writer)
    reader_thread = Thread(target=reader)
    writer_thread.start()
    assert writer_entered.wait(timeout=5)
    reader_thread.start()
    assert not reader_entered.wait(timeout=0.1)
    release_writer.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=5)

    assert reader_entered.is_set()
    assert not writer_thread.is_alive()
    assert not reader_thread.is_alive()


@pytest.mark.allow_direct_assert
def test_process_shared_context_waits_for_active_cwd_to_finish(tmp_path: Path) -> None:
    """Do not join an existing reader group after an unsupported external cwd change."""
    original_cwd = Path.cwd()
    holder_entered = Event()
    release_holder = Event()
    waiter_entered = Event()

    def holder() -> None:
        with process_context():
            holder_entered.set()
            release_holder.wait(timeout=5)

    def waiter() -> None:
        with process_context():
            waiter_entered.set()

    holder_thread = Thread(target=holder)
    waiter_thread = Thread(target=waiter)
    holder_thread.start()
    assert holder_entered.wait(timeout=5)
    os.chdir(tmp_path)
    try:
        waiter_thread.start()
        waiter_was_isolated = not waiter_entered.wait(timeout=0.1)
    finally:
        release_holder.set()
        holder_thread.join(timeout=5)
        waiter_thread.join(timeout=5)
        os.chdir(original_cwd)

    assert waiter_was_isolated
    assert waiter_entered.is_set()
    assert not holder_thread.is_alive()
    assert not waiter_thread.is_alive()


@pytest.mark.allow_direct_assert
def test_process_chdir_resolves_relative_target_after_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolve a queued relative path after the preceding cwd is restored."""
    target = tmp_path / "target"
    temporary = tmp_path / "temporary"
    target.mkdir()
    temporary.mkdir()
    monkeypatch.chdir(tmp_path)
    writer_entered = Event()
    release_writer = Event()
    observed: list[Path] = []

    def first_writer() -> None:
        with process_chdir(str(temporary)):
            writer_entered.set()
            release_writer.wait(timeout=5)

    def queued_writer() -> None:
        with chdir(Path("target")):
            observed.append(Path.cwd())

    first_thread = Thread(target=first_writer)
    queued_thread = Thread(target=queued_writer)
    first_thread.start()
    assert writer_entered.wait(timeout=5)
    queued_thread.start()
    release_writer.set()
    first_thread.join(timeout=5)
    queued_thread.join(timeout=5)

    assert observed == [target]
    assert Path.cwd() == tmp_path
    assert not first_thread.is_alive()
    assert not queued_thread.is_alive()


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("change_cwd", [False, True])
def test_process_writer_waits_for_borrowed_reader(tmp_path: Path, *, change_cwd: bool) -> None:
    """Keep a writer's cwd stable until a borrowed reader exits."""
    writer_entered = Event()
    writer_release = Event()
    writer_done = Event()
    reader_entered = Event()
    reader_release = Event()
    errors: list[Exception] = []

    def writer() -> None:
        try:
            context = process_chdir(str(tmp_path)) if change_cwd else process_context(exclusive=True, allow_shared=True)
            with context:
                writer_entered.set()
                writer_release.wait(timeout=5)
            writer_done.set()
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            errors.append(exc)

    def reader() -> None:
        try:
            with process_context():
                reader_entered.set()
                reader_release.wait(timeout=5)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            errors.append(exc)

    writer_thread = Thread(target=writer)
    reader_thread = Thread(target=reader)
    writer_thread.start()
    assert writer_entered.wait(timeout=5)
    reader_thread.start()
    assert reader_entered.wait(timeout=5)
    writer_release.set()
    assert not writer_done.wait(timeout=0.1)
    reader_release.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=5)

    assert not errors
    assert writer_done.is_set()
    assert not writer_thread.is_alive()
    assert not reader_thread.is_alive()


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_handles_fallbacks_and_cycles() -> None:  # noqa: PLR0914
    """Detach mutable state even when custom values reject deepcopy."""

    class FrozenSlotLeaf:
        __slots__ = ("items",)

        setter_calls = 0

        def __init__(self) -> None:
            object.__setattr__(self, "items", [])

        def __setattr__(self, name: str, value: Any) -> None:  # pragma: no cover - must not be called
            type(self).setter_calls += 1
            msg = "frozen"
            raise TypeError(msg)

    class UnsupportedSlotLeaf:
        __slots__ = ("items",)

        def __init__(self) -> None:
            self.items: list[str] = []

    class DunderSlotLeaf:
        __slots__ = ("__items__",)

        def __init__(self) -> None:
            self.__items__: list[str] = []

    class SlotLeaf:
        __slots__ = ("__dict__", "__weakref__", "items", "missing")

        def __init__(self) -> None:
            self.items: list[str] = []

        def __deepcopy__(self, memo: dict[int, Any]) -> SlotLeaf:
            memo[id(self)] = self
            msg = "no deepcopy"
            raise TypeError(msg)

    class NewLeaf:
        def __init__(self) -> None:
            self.items: list[str] = []

        def __copy__(self) -> NewLeaf:
            return self

        def __deepcopy__(self, memo: dict[int, Any]) -> NewLeaf:
            memo[id(self)] = self
            msg = "no deepcopy"
            raise TypeError(msg)

    class CopyObservable:
        copy_calls = 0

        def __init__(self, value: str) -> None:
            self.value = value

        def __copy__(self) -> CopyObservable:  # pragma: no cover - a call would violate output compatibility
            type(self).copy_calls += 1
            return type(self)("copied")

    class TupleValue(tuple[list[str]]):
        __slots__ = ()

        def __copy__(self) -> TupleValue:
            return type(self)(self)

        def __deepcopy__(self, memo: dict[int, Any]) -> TupleValue:
            memo[id(self)] = self
            msg = "no deepcopy"
            raise TypeError(msg)

    frozen_slot_leaf = FrozenSlotLeaf()
    unsupported_slot_leaf = UnsupportedSlotLeaf()
    slot_member = UnsupportedSlotLeaf.__dict__["items"]

    class RejectingSlotDescriptor:
        setter_calls = 0

        def __get__(  # pragma: no cover - must not be called
            self,
            instance: UnsupportedSlotLeaf | None,
            owner: type[UnsupportedSlotLeaf],
        ) -> Any:
            return self if instance is None else slot_member.__get__(instance, owner)

        def __set__(self, instance: UnsupportedSlotLeaf, value: Any) -> None:  # pragma: no cover - must not be called
            type(self).setter_calls += 1
            msg = "unsupported slot"
            raise TypeError(msg)

    UnsupportedSlotLeaf.items = RejectingSlotDescriptor()  # ty: ignore[invalid-assignment]
    unsupported_memo: dict[int, Any] = {}
    dunder_slot_leaf = DunderSlotLeaf()
    slot_leaf = SlotLeaf()
    new_leaf = NewLeaf()
    tuple_value = TupleValue(([],))
    cycle: list[Any] = []
    cycle_tuple = (cycle,)
    cycle.append(cycle_tuple)

    copied_frozen_slot = _copy_extra_template_value(frozen_slot_leaf, {}, use_deepcopy=False)
    copied_unsupported_slot = _copy_extra_template_value(
        unsupported_slot_leaf,
        unsupported_memo,
        use_deepcopy=False,
    )
    copied_dunder_slot = _copy_extra_template_value(dunder_slot_leaf, {})
    copied_slot = _copy_extra_template_value(slot_leaf, {})
    copied_new = _copy_extra_template_value(new_leaf, {})
    observable = CopyObservable("original")
    copied_observable = _copy_extra_template_value(observable, {}, use_deepcopy=False)
    copied_tuple = _copy_extra_template_value(tuple_value, {})
    copied_cycle = _copy_extra_template_value(cycle_tuple, {})
    immutable_view = memoryview(b"value")

    assert copied_frozen_slot is not frozen_slot_leaf
    assert copied_frozen_slot.items is not frozen_slot_leaf.items
    assert FrozenSlotLeaf.setter_calls == 0
    assert copied_unsupported_slot is unsupported_slot_leaf
    assert id(unsupported_slot_leaf) not in unsupported_memo
    assert RejectingSlotDescriptor.setter_calls == 0
    assert copied_dunder_slot is not dunder_slot_leaf
    assert copied_dunder_slot.__items__ is not dunder_slot_leaf.__items__
    assert copied_slot is not slot_leaf
    assert copied_slot.items is not slot_leaf.items
    assert copied_new is not new_leaf
    assert copied_new.items is not new_leaf.items
    assert copied_observable is not observable
    assert copied_observable.value == "original"
    assert CopyObservable.copy_calls == 0
    assert copied_tuple is not tuple_value
    assert copied_tuple[0] is not tuple_value[0]
    assert copied_cycle[0][0] is copied_cycle
    assert _copy_extra_template_value(frozenset({1}), {}) == frozenset({1})
    assert _copy_extra_template_value(immutable_view, {}) is immutable_view


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_handles_collection_subclass_fallbacks() -> None:  # noqa: PLR0914
    """Detach collection subclasses when their constructors or copy hooks reject values."""

    class IdentityList(list[list[str]]):  # noqa: FURB189
        """List whose shallow-copy hook preserves identity."""

        def __copy__(self) -> IdentityList:  # pragma: no cover - safe copies bypass user hooks
            return self

    class FixedTuple(tuple[Any, ...]):
        __slots__ = ()

        def __new__(cls, values: Any = ()) -> Self:
            if isinstance(values, list):  # pragma: no cover - protects the fallback under test
                msg = "list construction is unsupported"
                raise TypeError(msg)
            return super().__new__(cls, values)

        def __copy__(self) -> FixedTuple:
            return type(self)(self)

        def __deepcopy__(self, memo: dict[int, Any]) -> FixedTuple:
            memo[id(self)] = self
            msg = "no deepcopy"
            raise TypeError(msg)

    class MutableLeaf:
        def __init__(self) -> None:
            self.items: list[str] = []

    class FrozenValue(frozenset[Any]):
        def __copy__(self) -> FrozenValue:  # pragma: no cover - safe copies bypass user hooks
            return type(self)(self)

    class FixedFrozenValue(frozenset[Any]):
        def __new__(cls, values: Any = ()) -> Self:
            if isinstance(values, list):  # pragma: no cover - protects the fallback under test
                msg = "list construction is unsupported"
                raise TypeError(msg)
            return super().__new__(cls, values)

        def __copy__(self) -> FixedFrozenValue:  # pragma: no cover - safe copies bypass user hooks
            return type(self)(self)

    class CopiedDict(dict[str, list[str]]):  # noqa: FURB189
        def __copy__(self) -> CopiedDict:  # pragma: no cover - safe copies bypass user hooks
            return type(self)(self)

    class CopiedList(list[list[str]]):  # noqa: FURB189
        def __copy__(self) -> CopiedList:  # pragma: no cover - safe copies bypass user hooks
            return type(self)(self)

    class CopiedSet(set[int]):
        def __copy__(self) -> CopiedSet:  # pragma: no cover - safe copies bypass user hooks
            return type(self)(self)

    source_list = IdentityList([[]])
    copied_list = _copy_extra_template_value(source_list, {}, use_deepcopy=False)
    source_tuple = FixedTuple(([],))
    copied_tuple = _copy_extra_template_value(source_tuple, {})
    unchanged_tuple = FixedTuple((1,))
    copied_unchanged_tuple = _copy_extra_template_value(unchanged_tuple, {}, use_deepcopy=False)
    source_frozen = FrozenValue({MutableLeaf()})
    copied_frozen = _copy_extra_template_value(source_frozen, {}, use_deepcopy=False)
    unchanged_frozen = FrozenValue({1})
    copied_unchanged_frozen = _copy_extra_template_value(unchanged_frozen, {}, use_deepcopy=False)
    fallback_frozen = FixedFrozenValue({MutableLeaf()})
    copied_fallback_frozen = _copy_extra_template_value(fallback_frozen, {}, use_deepcopy=False)
    source_dict = {"items": []}
    copied_dict = _copy_extra_template_value(source_dict, {})
    source_custom_dict = CopiedDict({"items": []})
    copied_custom_dict = _copy_extra_template_value(source_custom_dict, {}, use_deepcopy=False)
    source_defaultdict = defaultdict(list, {"items": []})
    copied_defaultdict = _copy_extra_template_value(source_defaultdict, {}, use_deepcopy=False)
    source_ordered_dict = OrderedDict((("items", []),))
    copied_ordered_dict = _copy_extra_template_value(source_ordered_dict, {}, use_deepcopy=False)
    source_custom_list = CopiedList([[]])
    copied_custom_list = _copy_extra_template_value(source_custom_list, {}, use_deepcopy=False)
    source_deque = deque([[]], maxlen=2)
    copied_deque = _copy_extra_template_value(source_deque, {}, use_deepcopy=False)
    source_set = {1}
    copied_set = _copy_extra_template_value(source_set, {})
    source_custom_set = CopiedSet({1})
    copied_custom_set = _copy_extra_template_value(source_custom_set, {}, use_deepcopy=False)

    assert type(copied_list) is IdentityList
    assert copied_list[0] is not source_list[0]
    assert type(copied_tuple) is FixedTuple
    assert copied_tuple[0] is not source_tuple[0]
    assert type(copied_unchanged_tuple) is FixedTuple
    assert copied_unchanged_tuple is not unchanged_tuple
    assert type(copied_frozen) is FrozenValue
    assert copied_frozen is not source_frozen
    assert type(copied_unchanged_frozen) is FrozenValue
    assert copied_unchanged_frozen is not unchanged_frozen
    assert type(copied_fallback_frozen) is FixedFrozenValue
    assert copied_fallback_frozen is not fallback_frozen
    assert copied_dict == source_dict
    assert copied_dict is not source_dict
    assert type(copied_custom_dict) is CopiedDict
    assert copied_custom_dict["items"] is not source_custom_dict["items"]
    assert type(copied_defaultdict) is defaultdict
    assert copied_defaultdict.default_factory is list
    assert copied_defaultdict["items"] is not source_defaultdict["items"]
    assert copied_defaultdict["missing"] == []
    assert type(copied_ordered_dict) is OrderedDict
    assert copied_ordered_dict["items"] is not source_ordered_dict["items"]
    assert type(copied_custom_list) is CopiedList
    assert copied_custom_list[0] is not source_custom_list[0]
    assert type(copied_deque) is deque
    assert copied_deque.maxlen == 2
    assert copied_deque[0] is not source_deque[0]
    assert copied_set == source_set
    assert copied_set is not source_set
    assert type(copied_custom_set) is CopiedSet
    assert copied_custom_set is not source_custom_set


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_discards_incomplete_container_state() -> None:
    """Return the caller value when mutable subclass state cannot be detached completely."""

    class FailingHash:
        def __init__(self) -> None:
            self.fail = False

        def __hash__(self) -> int:
            if self.fail:
                msg = "detached key cannot be hashed"
                raise TypeError(msg)
            return id(self)

    class StatefulTuple(tuple[int, ...]):  # noqa: SLOT001
        pass

    class StatefulFrozenSet(frozenset[int]):
        pass

    class StatefulList(list[int]):  # noqa: FURB189
        pass

    key = FailingHash()
    state = {key: []}
    key.fail = True
    sources = (StatefulTuple((1,)), StatefulFrozenSet({1}), StatefulList([1]))
    for source in sources:
        source.state = state
        memo: dict[int, Any] = {}

        copied = _copy_extra_template_value(source, memo, use_deepcopy=False)

        assert copied is source
        assert id(source) not in memo


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_detaches_mapping_keys_and_default_factory() -> None:
    """Preserve mapping aliases and cycles without exposing caller-owned state."""

    class MutableKey:
        def __init__(self) -> None:
            self.items: list[str] = []

    class MutableFactory:
        def __init__(self) -> None:
            self.items: list[str] = []
            self.mapping: defaultdict[MutableKey, list[str]] | None = None

        def __call__(self) -> list[str]:
            return []

    key = MutableKey()
    factory = MutableFactory()
    mapping = defaultdict(factory, {key: []})
    factory.mapping = mapping
    source = {
        "factory": factory,
        "key": key,
        "mapping": mapping,
    }

    copied = _copy_extra_template_value(source, {}, use_deepcopy=False)
    copied_mapping = copied["mapping"]
    copied_key = next(iter(copied_mapping))
    copied_factory = copied_mapping.default_factory

    assert copied_key is copied["key"]
    assert copied_key is not key
    assert copied_key.items is not key.items
    assert copied_factory is copied["factory"]
    assert copied_factory is not factory
    assert copied_factory.items is not factory.items
    assert copied_factory.mapping is copied_mapping
    assert copied_mapping[MutableKey()] == []


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_skips_inherited_copy_hook() -> None:
    """Safely reconstruct extension subclasses without calling inherited __copy__."""
    from datetime import datetime

    class CopyHookDateBase(datetime):
        def __copy__(self) -> CopyHookDateBase:  # pragma: no cover - must not be called
            self.hook_calls.append("called")
            msg = "copy hook must not be called"
            raise TypeError(msg)

    class CopyHookDate(CopyHookDateBase):
        pass

    source = CopyHookDate(2026, 7, 24)
    source.hook_calls = []

    copied = _copy_extra_template_value(source, {}, use_deepcopy=False)

    assert type(copied) is CopyHookDate
    assert copied is not source
    assert copied == source
    assert copied.hook_calls == []
    assert copied.hook_calls is not source.hook_calls
    assert source.hook_calls == []


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_bypasses_other_custom_copy_protocol_hooks() -> None:
    """Use built-in reconstruction without invoking custom extension hooks."""
    import weakref
    from array import array
    from datetime import datetime

    class UnsafeCopyDate(datetime):
        def __copy__(self) -> UnsafeCopyDate:  # pragma: no cover - must not be called
            self.hook_calls.append("copy")
            msg = "copy hook must not be called"
            raise TypeError(msg)

        def __deepcopy__(self, memo: dict[int, Any]) -> UnsafeCopyDate:  # pragma: no cover - must not be called
            self.hook_calls.append("deepcopy")
            msg = "deepcopy hook must not be called"
            raise TypeError(msg)

    class UnsafeNewDate(datetime):
        new_calls = 0

        def __new__(cls, *args: Any) -> Self:
            cls.new_calls += 1
            return datetime.__new__(cls, *args)

        def __copy__(self) -> UnsafeNewDate:  # pragma: no cover - must not be called
            self.hook_calls.append("copy")
            msg = "copy hook must not be called"
            raise TypeError(msg)

    class CopyHookArrayBase(array):
        copy_calls = 0

        def __copy__(self) -> CopyHookArrayBase:  # pragma: no cover - must not be called
            type(self).copy_calls += 1
            return self

    class CopyHookArray(CopyHookArrayBase):
        pass

    class CopyHookWeakRef(weakref.ref[Any]):
        copy_calls = 0

        def __copy__(self) -> CopyHookWeakRef:  # pragma: no cover - must not be called
            type(self).copy_calls += 1
            return self

    copy_hook_source = UnsafeCopyDate(2026, 7, 24)
    copy_hook_source.hook_calls = []
    new_hook_source = UnsafeNewDate(2026, 7, 24)
    new_hook_source.hook_calls = []
    array_source = CopyHookArray("i", [1])
    array_source.items = []
    weakref_target = UnsafeCopyDate(2026, 7, 24)
    weakref_source = CopyHookWeakRef(weakref_target)

    copy_hook_result = _copy_extra_template_value(copy_hook_source, {}, use_deepcopy=False)
    new_hook_result = _copy_extra_template_value(new_hook_source, {}, use_deepcopy=False)
    array_result = _copy_extra_template_value(array_source, {}, use_deepcopy=False)
    weakref_result = _copy_extra_template_value(weakref_source, {}, use_deepcopy=False)

    assert type(copy_hook_result) is UnsafeCopyDate
    assert copy_hook_result == copy_hook_source
    assert copy_hook_result.hook_calls == []
    assert copy_hook_result.hook_calls is not copy_hook_source.hook_calls
    assert copy_hook_source.hook_calls == []
    assert type(new_hook_result) is UnsafeNewDate
    assert new_hook_result == new_hook_source
    assert new_hook_result.hook_calls == []
    assert new_hook_result.hook_calls is not new_hook_source.hook_calls
    assert new_hook_source.hook_calls == []
    assert UnsafeNewDate.new_calls == 1
    assert type(array_result) is CopyHookArray
    assert array_result is not array_source
    assert array_result == array_source
    assert array_result.items == []
    assert array_result.items is not array_source.items
    assert array_source.items == []
    assert CopyHookArray.copy_calls == 0
    assert weakref_result is weakref_source
    assert CopyHookWeakRef.copy_calls == 0


@pytest.mark.allow_direct_assert
def test_copy_extra_template_value_preserves_tuple_list_cycle() -> None:
    """Resolve a tuple-to-list cycle without recursion or caller sharing."""
    source_list: list[Any] = []
    source_tuple = (source_list,)
    source_list.append(source_tuple)

    copied_tuple = _copy_extra_template_value(source_tuple, {}, use_deepcopy=False)

    assert copied_tuple is not source_tuple
    assert copied_tuple[0] is not source_list
    assert copied_tuple[0][0] is copied_tuple


@pytest.mark.allow_direct_assert
def test_generation_template_data_preserves_detached_aliases() -> None:
    """Reuse one detached model record when source keys alias it."""
    shared = {"items": []}
    eager_data = _copy_extra_template_data({"First": shared, "Second": shared}, deep=False)
    data = _GenerationTemplateData({"First": shared, "Second": shared})

    first = data["First"]
    second = data["Second"]

    assert eager_data["First"] is eager_data["Second"]
    assert eager_data["First"] is not shared
    assert first is second
    assert first is not shared


@pytest.mark.allow_direct_assert
@pytest.mark.parametrize("accessor", ["items", "values", "pop"])
def test_generation_template_data_detaches_mapping_accesses(accessor: str) -> None:
    """Do not expose source records through alternate mapping access methods."""
    source_record = {"items": []}
    data = _GenerationTemplateData({"Model": source_record})

    match accessor:
        case "items":
            detached = dict(data.items())["Model"]
        case "values":
            detached = next(iter(data.values()))
        case _:
            detached = data.pop("Model")

    assert detached is not source_record
    assert detached["items"] is not source_record["items"]


@pytest.mark.allow_direct_assert
def test_generation_template_data_detaches_get_and_setdefault_accesses() -> None:
    """Keep lazy accessors from returning source-owned records."""
    source_record = {"items": []}
    data = _GenerationTemplateData({"Model": source_record})

    detached = data.get("Model")
    inserted = data.setdefault("Inserted")

    assert detached is data.setdefault("Model")
    assert detached is not source_record
    assert detached["items"] is not source_record["items"]
    assert data["Inserted"] is inserted
    assert data.get("Missing", "fallback") == "fallback"
    assert data.pop("Missing", "fallback") == "fallback"
