# Restock Monitor

상품 **URL**과 **옵션**을 등록해 두면 **10분마다** 재고를 확인하고, 품절→재입고로 바뀔 때 **Gmail**으로 알려 줍니다. 여러 상품을 동시에 등록할 수 있습니다.

현재 지원 쇼핑몰: **Nike** (`nike.com`). 다른 몰은 `app/adapters/` 에 어댑터를 추가하면 확장할 수 있습니다.

## 준비

1. Python 3.11+
2. Gmail **2단계 인증** + **앱 비밀번호**
3. `.env` 작성 (`.env.example` 복사)

```bash
cp .env.example .env
# GMAIL_USER, GMAIL_APP_PASSWORD 필수
```

## 실행

```bash
cd restock-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

브라우저에서 http://127.0.0.1:8000

## Nike 예시

| 필드 | 값 |
|------|-----|
| URL | `https://www.nike.com/kr/t/.../3VovIp4L/HQ2335-600` |
| 옵션 | `280` (한국 mm 사이즈) |

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `CHECK_INTERVAL_MINUTES` | 확인 주기(분) | `10` |
| `DEFAULT_ALERT_TO` | 폼에서 이메일 비울 때 | `GMAIL_USER` |
| `DATABASE_PATH` | SQLite 경로 | `data/monitors.db` |

## 새 쇼핑몰 추가

1. `app/adapters/your_shop.py` — `SiteAdapter` 구현 (`supports`, `build_meta`, `check`)
2. `app/adapters/registry.py` 의 `_ADAPTERS` 리스트에 등록

## 주의

- Nike API는 **온라인 배송 재고** 기준입니다.
- 재입고 알림 후에도 빠르게 품절될 수 있습니다.
- Gmail SMTP는 **개인·소규모 사용**에 맞습니다.