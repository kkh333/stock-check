from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StockResult:
    in_stock: bool
    summary: str
    raw: dict[str, Any] | None = None


class SiteAdapter(ABC):
    """사이트별 URL 파싱 및 재고 조회."""

    site_id: str
    display_name: str

    @abstractmethod
    def supports(self, url: str) -> bool: ...

    @abstractmethod
    def build_meta(self, url: str, option_label: str) -> dict[str, Any]:
        """DB에 저장할 사이트별 메타 (옵션 포함)."""

    @abstractmethod
    def check(self, meta: dict[str, Any]) -> StockResult: ...