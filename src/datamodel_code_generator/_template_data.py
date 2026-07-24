"""Copy mutable template data without changing observable custom values."""

from __future__ import annotations

import contextlib
from collections import OrderedDict, defaultdict, deque
from copy import copy, deepcopy
from types import MemberDescriptorType
from typing import Any
from weakref import ref

_IMMUTABLE_TEMPLATE_VALUE_TYPES = frozenset({bool, bytes, complex, float, int, type(None), str})


class TemplateDataRecord(dict[str, Any]):  # noqa: FURB189
    """Per-model data carrying one request-scoped copy memo."""

    __slots__ = ("_copy_context",)

    def __init__(self, copy_context: TemplateDataCopyContext) -> None:
        super().__init__()
        self._copy_context = ref(copy_context)

    @property
    def copy_memo(self) -> dict[int, Any]:
        """Return the live request memo without retaining the request."""
        return context.memo if (context := self._copy_context()) is not None else {}


class TemplateDataCopyContext:
    """Own copied request values while records keep only weak references."""

    __slots__ = ("__weakref__", "memo")

    def __init__(self) -> None:
        self.memo: dict[int, Any] = {}


def _restore_template_memo(memo: dict[int, Any], previous_memo: dict[int, Any]) -> None:
    """Discard an incomplete copy attempt without retaining detached aliases."""
    memo.clear()
    memo.update(previous_memo)


def _find_builtin_copy_method(value: Any, name: str) -> Any:
    """Return the first C-level copy protocol method in the value's MRO."""
    from inspect import isbuiltin, ismethoddescriptor  # noqa: PLC0415

    for cls in type(value).__mro__:
        if (callback := cls.__dict__.get(name)) is None:
            continue
        if isinstance(callback, staticmethod | classmethod):
            callback = callback.__func__
        if isbuiltin(callback) or ismethoddescriptor(callback):
            return callback
    return None  # pragma: no cover - object provides built-in protocol methods


def _get_builtin_reduction(value: Any) -> Any:
    """Return reduction data without invoking user-defined reducers."""
    if (reduce_ex := _find_builtin_copy_method(value, "__reduce_ex__")) is not None:
        return reduce_ex(value, 4)
    return None  # pragma: no cover - object provides __reduce_ex__


def _reconstruct_with_builtin_copy_protocol(value: Any, memo: dict[int, Any]) -> Any | None:
    """Return a detached extension value when its built-in protocol is usable."""
    from inspect import isbuiltin  # noqa: PLC0415

    if not isinstance(reduced := _get_builtin_reduction(value), tuple):  # pragma: no cover
        return None
    match reduced:
        case (factory, tuple() as args, *_):
            pass
        case _:  # pragma: no cover - built-in reducers return protocol tuples
            return None
    if isbuiltin(factory):
        detached = factory(*args)
    elif (new := _find_builtin_copy_method(value, "__new__")) is not None and (
        factory is type(value) or getattr(factory, "__name__", "") == "__newobj__"
    ):
        if args and args[0] is type(value):  # pragma: no cover - copyreg.__newobj__ reduction
            args = args[1:]
        detached = new(type(value), *args)
    else:
        return None  # pragma: no cover - no known built-in reducer returns an unsafe Python factory
    if type(detached) is not type(value) or detached is value:  # pragma: no cover - safe built-ins allocate exact types
        return None
    memo[id(value)] = detached
    return detached


def _copy_without_custom_copy_hook(value: Any, memo: dict[int, Any]) -> Any:
    """Reconstruct an extension value through its built-in copy protocol."""
    previous_memo = memo.copy()
    try:
        detached = _reconstruct_with_builtin_copy_protocol(value, memo)
    except Exception:  # noqa: BLE001  # pragma: no cover - defensive built-in protocol failure
        detached = None
    if detached is not None:
        return detached
    _restore_template_memo(memo, previous_memo)
    return value


def _new_template_value(value: Any, memo: dict[int, Any]) -> Any:  # noqa: PLR0911
    """Allocate a shallow shell without invoking user-defined copy hooks."""
    match value:
        case defaultdict():
            return dict.__new__(type(value))
        case OrderedDict():
            return OrderedDict.__new__(type(value))
        case dict():
            return dict.__new__(type(value))
        case list():
            return list.__new__(type(value))
        case set():
            return set.__new__(type(value))
        case tuple():
            return tuple.__new__(type(value), value)
        case frozenset():
            return frozenset.__new__(type(value), value)
        case deque():
            detached = deque.__new__(type(value))
            deque.__init__(detached, (), value.maxlen)  # noqa: PLC2801
            return detached
        case _:
            try:
                return object.__new__(type(value))
            except TypeError:
                if any("__copy__" in cls.__dict__ for cls in type(value).__mro__):
                    return _copy_without_custom_copy_hook(value, memo)
                return copy(value)


def _copy_object_state(
    value: Any,
    detached: Any,
    memo: dict[int, Any],
    *,
    use_deepcopy: bool,
) -> bool:
    """Detach object state without invoking user-defined attribute setters."""
    try:
        try:
            source_dict = object.__getattribute__(value, "__dict__")  # noqa: PLC2801
        except AttributeError:
            source_dict = None
        try:
            detached_dict = object.__getattribute__(detached, "__dict__")  # noqa: PLC2801
        except AttributeError:
            detached_dict = None
        if isinstance(source_dict, dict) and isinstance(detached_dict, dict):
            dict.clear(detached_dict)
            dict.update(
                detached_dict,
                (
                    (name, copy_template_value(item, memo, use_deepcopy=use_deepcopy))
                    for name, item in source_dict.items()
                ),
            )
        elif source_dict is not None or detached_dict is not None:  # pragma: no cover - one type owns both dictionaries
            return False

        for cls in type(value).__mro__:
            slots = cls.__dict__.get("__slots__", ())
            for slot in (slots,) if isinstance(slots, str) else slots:
                if slot in {"__dict__", "__weakref__"}:
                    continue
                attribute = (
                    f"_{cls.__name__.lstrip('_')}{slot}" if slot.startswith("__") and not slot.endswith("__") else slot
                )
                descriptor = cls.__dict__.get(attribute)
                if type(descriptor) is not MemberDescriptorType:
                    return False
                try:
                    item = descriptor.__get__(value, type(value))
                except AttributeError:
                    with contextlib.suppress(AttributeError):
                        descriptor.__delete__(detached)
                    continue
                detached_item = copy_template_value(item, memo, use_deepcopy=use_deepcopy)
                descriptor.__set__(detached, detached_item)
                if descriptor.__get__(detached, type(value)) is not detached_item:  # pragma: no cover
                    return False  # built-in slot descriptors retain the assigned object
    except Exception:  # noqa: BLE001
        return False
    return True


def copy_template_value(  # noqa: PLR0911, PLR0912, PLR0915
    value: Any,
    memo: dict[int, Any],
    *,
    use_deepcopy: bool = True,
) -> Any:
    """Copy mutable template values while preserving aliases and cycles."""
    if type(value) in _IMMUTABLE_TEMPLATE_VALUE_TYPES:
        return value
    if (value_id := id(value)) in memo:
        return memo[value_id]
    custom_copy: Any = None
    if type(value) not in {dict, list, set, tuple, frozenset}:
        previous_memo = memo.copy()
        if use_deepcopy:
            try:
                return deepcopy(value, memo)
            except Exception:  # noqa: BLE001
                _restore_template_memo(memo, previous_memo)
        with contextlib.suppress(Exception):
            custom_copy = copy(value) if use_deepcopy else _new_template_value(value, memo)
        if use_deepcopy and (custom_copy is None or custom_copy is value):
            try:
                custom_copy = _new_template_value(value, memo)
            except Exception:  # noqa: BLE001
                custom_copy = None
        if custom_copy is None or custom_copy is value:
            return value
        if not isinstance(value, dict | list | set | tuple | frozenset | deque):
            memo[value_id] = custom_copy
            if _copy_object_state(value, custom_copy, memo, use_deepcopy=use_deepcopy):
                return custom_copy
            _restore_template_memo(memo, previous_memo)
            return value
    match value:
        case tuple():
            detached_items = [copy_template_value(item, memo, use_deepcopy=use_deepcopy) for item in value]
            if value_id in memo:
                return memo[value_id]
            changed = any(original is not copied for original, copied in zip(value, detached_items, strict=True))
            if custom_copy is not None:
                detached = custom_copy
                if changed:
                    detached = tuple.__new__(type(value), detached_items)
            else:
                detached = tuple(detached_items) if changed else value
            memo[value_id] = detached
            if custom_copy is not None and not _copy_object_state(
                value,
                detached,
                memo,
                use_deepcopy=use_deepcopy,
            ):
                _restore_template_memo(memo, previous_memo)
                return value
            return detached
        case frozenset():
            original_items = list(value)
            detached_items = [copy_template_value(item, memo, use_deepcopy=use_deepcopy) for item in original_items]
            changed = any(
                original is not copied for original, copied in zip(original_items, detached_items, strict=True)
            )
            if custom_copy is not None:
                detached = custom_copy
                if changed:
                    detached = frozenset.__new__(type(value), detached_items)
            else:
                detached = frozenset(detached_items) if changed else value
            memo[value_id] = detached
            if custom_copy is not None and not _copy_object_state(
                value,
                detached,
                memo,
                use_deepcopy=use_deepcopy,
            ):
                _restore_template_memo(memo, previous_memo)
                return value
            return detached
    match value:
        case dict():
            detached = custom_copy if isinstance(custom_copy, dict) and custom_copy is not value else {}
            clear = OrderedDict.clear if isinstance(detached, OrderedDict) else dict.clear
            clear(detached)
            memo[value_id] = detached
            if isinstance(value, defaultdict) and isinstance(detached, defaultdict):
                object.__setattr__(  # noqa: PLC2801
                    detached,
                    "default_factory",
                    copy_template_value(value.default_factory, memo, use_deepcopy=use_deepcopy),
                )
            if type(detached) is dict:
                for item_key, item_value in value.items():
                    detached[
                        item_key
                        if (key_type := type(item_key)) is str or key_type in _IMMUTABLE_TEMPLATE_VALUE_TYPES
                        else copy_template_value(item_key, memo, use_deepcopy=use_deepcopy)
                    ] = copy_template_value(item_value, memo, use_deepcopy=use_deepcopy)
            else:
                set_item = OrderedDict.__setitem__ if isinstance(detached, OrderedDict) else dict.__setitem__
                for item_key, item_value in value.items():
                    set_item(
                        detached,
                        item_key
                        if (key_type := type(item_key)) is str or key_type in _IMMUTABLE_TEMPLATE_VALUE_TYPES
                        else copy_template_value(item_key, memo, use_deepcopy=use_deepcopy),
                        copy_template_value(item_value, memo, use_deepcopy=use_deepcopy),
                    )
        case list():
            detached = custom_copy if isinstance(custom_copy, list) and custom_copy is not value else []
            list.clear(detached)
            memo[value_id] = detached
            list.extend(
                detached,
                (copy_template_value(item, memo, use_deepcopy=use_deepcopy) for item in value),
            )
        case set():
            detached = custom_copy if isinstance(custom_copy, set) and custom_copy is not value else set()
            set.clear(detached)
            memo[value_id] = detached
            set.update(
                detached,
                (copy_template_value(item, memo, use_deepcopy=use_deepcopy) for item in value),
            )
        case deque():  # pragma: no branch - all other container types return above
            detached = custom_copy if isinstance(custom_copy, deque) and custom_copy is not value else deque()
            deque.clear(detached)
            memo[value_id] = detached
            deque.extend(
                detached,
                (copy_template_value(item, memo, use_deepcopy=use_deepcopy) for item in value),
            )
    if custom_copy is not None and not _copy_object_state(
        value,
        detached,
        memo,
        use_deepcopy=use_deepcopy,
    ):
        _restore_template_memo(memo, previous_memo)
        return value
    return detached
