import math
from datetime import datetime, timedelta

import httpx

from app.core.config import settings

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# ===== 격자좌표 변환 =====
RE = 6371.00877
GRID = 5.0
SLAT1 = 30.0
SLAT2 = 60.0
OLON = 126.0
OLAT = 38.0
XO = 43
YO = 136


def latlng_to_grid(lat: float, lng: float) -> tuple[int, int]:
    """위경도를 기상청 격자좌표(nx, ny)로 변환. 기상청 공식 변환 공식."""
    DEGRAD = math.pi / 180.0

    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lng * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + XO + 1.5)
    ny = int(ro - ra * math.cos(theta) + YO + 1.5)

    return nx, ny


# ===== 기상청 API 호출 + 날씨 상태 변환 =====
WEATHER_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

BASE_TIMES = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]


def _get_latest_base_datetime() -> tuple[str, str]:
    """현재 시각 기준, 가장 최근 발표시각을 계산."""
    now = datetime.now(KST)
    today = now.strftime("%Y%m%d")

    available_times = [t for t in BASE_TIMES if t <= now.strftime("%H%M")]
    if available_times:
        return today, available_times[-1]

    yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")
    return yesterday, "2300"


def _get_sky_condition(sky_code: str | None, pty_code: str | None) -> str:
    """SKY, PTY 코드를 프론트가 아이콘 매핑하기 쉬운 상태 이름으로 변환."""
    if pty_code and pty_code != "0":
        return {"1": "RAIN", "2": "RAIN_SNOW", "3": "SNOW", "4": "SHOWER"}.get(pty_code, "RAIN")
    return {"1": "CLEAR", "3": "PARTLY_CLOUDY", "4": "CLOUDY"}.get(sky_code, "CLEAR")


async def get_current_weather(nx: int, ny: int) -> dict | None:
    """현재 위치의 가장 가까운 미래 예보 시각 기준 날씨 정보 조회."""
    base_date, base_time = _get_latest_base_datetime()

    params = {
        "serviceKey": settings.KMA_SERVICE_KEY,
        "numOfRows": 100,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(WEATHER_URL, params=params)
        res.raise_for_status()
        data = res.json()

    items = data.get("response", {}).get("body", {}).get("items", {})
    if items == "" or not items:
        return None

    item_list = items.get("item", [])

    # 지금 시각 이후의 fcstTime 중 가장 이른 것을 찾음
    now_time = datetime.now(KST).strftime("%H%M")
    fcst_times = sorted({item.get("fcstTime") for item in item_list if item.get("fcstTime")})
    target_fcst_time = next((t for t in fcst_times if t >= now_time), fcst_times[0] if fcst_times else None)

    if target_fcst_time is None:
        return None

    values = {}
    for item in item_list:
        category = item.get("category")
        if category in ("TMP", "REH", "WSD", "POP", "SKY", "PTY") and item.get("fcstTime") == target_fcst_time:
            values[category] = item.get("fcstValue")

    if not values:
        return None

    return {
        "temperature": float(values["TMP"]) if "TMP" in values else None,               # 기온
        "humidity": int(values["REH"]) if "REH" in values else None,                    # 습도 
        "wind_speed": float(values["WSD"]) if "WSD" in values else None,                # 풍속
        "precipitation_probability": int(values["POP"]) if "POP" in values else None,   # 강수확률
        "sky_condition": _get_sky_condition(values.get("SKY"), values.get("PTY")),      # 하늘상태
        "forecast_time": target_fcst_time,                                              # 이 예보가 몇 시 기준인지 
    }
