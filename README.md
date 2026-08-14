# Plan-B

여행 중 날씨·장소 휴무·일정 지연 같은 변수가 생겼을 때, 고정 일정은 유지하고 문제된 부분만 대체·재배치해주는 여행 일정 복구 서비스입니다.

## 핵심 기능

- **심플탭**: 지금 상황(위치, 시간, 문제 사유)만 입력하면 즉석에서 대체 장소를 추천
- **디테일탭**: 미리 짜둔 전체 여행 일정 중 문제 생긴 항목만 골라 대체 장소를 추천받고 반영

두 탭 모두 카테고리·이용가능시간·실제 날씨를 고려한 필터링을 거친 뒤, Claude AI가 최종 후보를 선정하고 추천 이유를 자연어로 생성합니다.

## 기술 스택

**백엔드**
- FastAPI, Uvicorn
- PostgreSQL + SQLAlchemy
- httpx (비동기 외부 API 연동)
- Pydantic / pydantic-settings

**외부 API**
- 카카오 Local API (장소 검색), 카카오모빌리티 (자동차 이동시간)
- TourAPI (관광지 정보)
- Google Places API (평점, 리뷰수, 주차 정보 보완)
- 기상청 단기예보 API (실시간 날씨)
- Claude API (Haiku 4.5) — 최종 추천 선정 및 이유 생성

**개발 도구**
- Black, Ruff, mypy — `make check`로 일괄 실행
- Docker, Docker Compose

## 시작하기

### 사전 준비물

- `.env` 파일 (API 키 — 별도 전달받아 프로젝트 루트에 위치)

```
DATABASE_URL=...
KAKAO_REST_API_KEY=...
KMA_SERVICE_KEY=...
TOUR_API_KEY=...
GOOGLE_PLACES_API_KEY=...
CLAUDE_API_KEY=...
```

### Docker로 실행 (권장)

```bash
docker compose up --build
docker compose exec api python3 -m app.init_db
```

`http://localhost:8000/docs`에서 Swagger UI 확인 가능.

### 로컬에서 직접 실행

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# PostgreSQL 로컬 설치 및 DB 생성 후
python3 -m app.init_db
make run
```

## 개발 명령어 (Makefile)

```bash
make run         # 서버 실행 (--reload)
make db          # psql 접속
make initdb      # 테이블 생성
make format      # black + ruff --fix
make lint        # ruff check (자동수정 없음)
make typecheck   # mypy
make check       # format → lint → typecheck 순서로 전체 실행
```

## API 개요

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/v1/health` | 서버 상태 확인 |
| POST | `/api/v1/simple/recommendations` | 심플탭 추천 요청 |
| GET | `/api/v1/places/search` | 디테일탭 장소 검색(담아둘 장소) |
| POST | `/api/v1/detail/recommendations` | 디테일탭 항목별 추천 요청 |
| POST | `/api/v1/schedule/validate` | 디테일탭 시간 변경 충돌 검증 |
| GET | `/api/v1/weather` | 현재 위치 날씨 조회 (프론트 표시용) |

상세 요청/응답 스키마는 팀 공유 API 명세서 참고.

## 프로젝트 구조

```
app/
├── api/            # 라우터 (엔드포인트)
├── core/           # 설정, DB 연결, 카테고리 상수
├── models/         # SQLAlchemy 모델
├── services/       # 외부 API 연동, 비즈니스 로직
├── test/           # 확인용 스크립트 (pytest 아님, 개별 실행)
├── init_db.py      # 테이블 생성 스크립트
├── ingest_places.py
└── main.py
```

## 브랜치 전략 및 커밋 컨벤션

[BRANCH_STRATEGY.md](./BRANCH_STRATEGY.md) 참고.

## 배포 시 확인 사항

- Google Places API 키에 IP 주소 제한 설정 (현재 로컬 개발 편의상 미설정 상태)
- `.env`의 `DATABASE_URL`을 배포 환경 DB로 교체