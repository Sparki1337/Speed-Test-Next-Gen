# coding: utf-8
"""Вспомогательные функции для гибкого импорта модулей и атрибутов.

Позволяет использовать единую точку входа при запуске проекта как пакета
(`python -m fluent_speedtest`) и как скрипта из каталога (`python main.py`).
"""
from __future__ import annotations

from importlib import import_module as _import_module
from types import ModuleType
from typing import Iterable, Tuple

_DEFAULT_PACKAGE = "fluent_speedtest"


def _iter_candidates(name: str, package: str | None, fallback: Iterable[str] | None) -> Iterable[str]:
    module_name = name.lstrip(".")

    if package:
        yield f"{package}.{module_name}"

    yield module_name

    if fallback:
        for candidate in fallback:
            yield candidate


def _should_retry(exc: ImportError, candidate: str) -> bool:
    missing = getattr(exc, "name", None)
    if missing is None:
        return True
    return missing in {candidate, candidate.split(".")[0]}


def import_module(name: str, *, package: str | None = _DEFAULT_PACKAGE, fallback: Iterable[str] | None = None) -> ModuleType:
    last_exc: ImportError | None = None
    for candidate in _iter_candidates(name, package, fallback):
        try:
            return _import_module(candidate)
        except ImportError as exc:  # pragma: no cover - логика защиты
            if not _should_retry(exc, candidate):
                raise
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise ImportError(f"Не удалось импортировать модуль '{name}'")


def import_attrs(name: str, *attrs: str, package: str | None = _DEFAULT_PACKAGE, fallback: Iterable[str] | None = None) -> Tuple:
    module = import_module(name, package=package, fallback=fallback)
    if not attrs:
        return (module,)
    return tuple(getattr(module, attr) for attr in attrs)
