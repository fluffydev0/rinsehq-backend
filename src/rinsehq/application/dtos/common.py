from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SuccessResult(Generic[T]):
    data: T


@dataclass(frozen=True)
class ErrorResult:
    error: str


Result = Union[SuccessResult[T], ErrorResult]
