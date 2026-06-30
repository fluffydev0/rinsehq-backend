from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ServiceCategory = Literal["wash", "press", "dry_clean", "addon", "special"]


@dataclass(frozen=True)
class Service:
    id: str
    store_id: str
    name: str
    category: str
    laundry_mode: str
    unit_price: int
    pricing_unit: str
    turnaround_hours: int
    status: str
    description: str
    orders_count: int
    updated_at: datetime


@dataclass(frozen=True)
class ConfigItem:
    id: str
    label: str
    enabled: bool


@dataclass(frozen=True)
class ServicesConfiguration:
    laundry_modes: list[ConfigItem]
    service_types: list[ConfigItem]
    order_types: list[ConfigItem]
