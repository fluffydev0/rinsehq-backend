from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    email: str
    phone: str
    address: str = ""
