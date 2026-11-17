from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from app.adapters.base import SiteAdapter, StockResult

CONSUMER_CHANNEL_ID = "d9a5bc42-4b9c-4976-858a-f159cf99c647"
HEADERS = {
    "Accept": "application/json",
    "nike-api-caller-id": "com.nike:commerce.idpdp.mobile",
    "Origin": "https://www.nike.com",
    "Referer": "https://www.nike.com/kr/",
}


def _parse_nike_url(url: str) -> tuple[str, str]:
    path = urlparse(url).path.rstrip("/")
    if not path:
        raise ValueError("유효한 Nike 상품 URL이 아닙니다.")
    style_color = path.split("/")[-1]
    slug = path.split("/")[-2]
    if not re.match(r"^[A-Z0-9]+-[0-9]{3}$", style_color, re.I):
        raise ValueError("URL 마지막 세그먼트에서 styleColor(예: HQ2335-600)를 찾지 못했습니다.")
    group_key = slug.split("-")[-1]
    if len(group_key) < 4:
        raise ValueError("URL에서 groupKey(슬러그 끝 토큰)를 찾지 못했습니다.")
    return group_key, style_color.upper()


class NikeAdapter(SiteAdapter):
    site_id = "nike"
    display_name = "Nike"

    def supports(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return "nike.com" in host

    def build_meta(self, url: str, option_label: str) -> dict[str, Any]:
        option_label = option_label.strip()
        if not option_label:
            raise ValueError("옵션(사이즈)을 입력해 주세요. 예: 280")
        group_key, style_color = _parse_nike_url(url)
        marketplace = "KR"
        if "/kr/" in url.lower() or urlparse(url).path.lower().startswith("/kr/"):
            marketplace = "KR"
        return {
            "url": url,
            "option_label": option_label,
            "group_key": group_key,
            "style_color": style_color,
            "marketplace": marketplace,
            "language": "ko" if marketplace == "KR" else "en",
        }

    def _availability_url(self, meta: dict[str, Any]) -> str:
        mp = meta["marketplace"]
        lang = meta["language"]
        group_key = meta["group_key"]
        return (
            "https://api.nike.com/discover/product_details_availability/v1/"
            f"marketplace/{mp}/language/{lang}/"
            f"consumerChannelId/{CONSUMER_CHANNEL_ID}/"
            f"groupKey/{group_key}"
        )

    def check(self, meta: dict[str, Any]) -> StockResult:
        req = urllib.request.Request(self._availability_url(meta), headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            raise RuntimeError(f"Nike API HTTP {e.code}: {body}") from e

        style = meta["style_color"]
        option = meta["option_label"]
        for size in data.get("sizes", []):
            if size.get("productCode") != style:
                continue
            if str(size.get("localizedLabel")) != option and str(size.get("label")) != option:
                continue
            avail = size.get("availability") or {}
            in_stock = avail.get("isAvailable") is True
            ship = avail.get("ship", "?")
            summary = f"{'재고 있음' if in_stock else '품절'} (ship={ship})"
            return StockResult(in_stock=in_stock, summary=summary, raw=size)

        raise RuntimeError(
            f"옵션 '{option}' / 컬러 '{style}' 조합을 재고 응답에서 찾지 못했습니다. "
            "옵션은 Nike KR 페이지에 표시된 mm(예: 280)을 입력하세요."
        )