from __future__ import annotations

from app.adapters.base import SiteAdapter
from app.adapters.nike import NikeAdapter

_ADAPTERS: list[SiteAdapter] = [
    NikeAdapter(),
]


def adapter_for_url(url: str) -> SiteAdapter:
    for adapter in _ADAPTERS:
        if adapter.supports(url):
            return adapter
    names = ", ".join(a.display_name for a in _ADAPTERS)
    raise ValueError(
        f"이 URL은 아직 지원하지 않습니다. 현재 지원: {names}. "
        "새 쇼핑몰은 app/adapters/ 에 어댑터를 추가하면 됩니다."
    )


def supported_sites() -> list[str]:
    return [a.display_name for a in _ADAPTERS]