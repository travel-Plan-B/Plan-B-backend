# TourAPI contenttypeid -> 내부 표준 category_tag 매핑 (cat3로 못 찾을 때의 대체값)
# 12=관광지, 14=문화시설, 15=축제공연행사, 25=여행코스, 28=레포츠, 32=숙박, 38=쇼핑, 39=음식점
TOURAPI_CONTENTTYPE_MAP = {
    "12": "관광지",
    "14": "문화시설",
    "28": "레포츠",
    "39": "식당",
}
CATEGORY_TAG_TO_CONTENTTYPE = {
    "관광지": "12",
    "문화시설": "14",
    "레포츠": "28",
    "식당": "39",
}
# 위 맵에 없는 contenttypeid(숙박/쇼핑/여행코스/축제행사)는 화이트리스트에서 자동 제외됨

# TourAPI cat3(세부 카테고리) -> 내부 표준 category_tag (contenttypeid보다 우선 적용)
TOURAPI_CAT3_CATEGORY_MAP = {
    "A05020900": "카페",  # 카페/전통찻집
    "A02020600": "문화시설",  # 박물관
    "A02020700": "문화시설",  # 미술관/전시관
    "A02020900": "문화시설",  # 공연장
}

# TourAPI cat3 -> 실내 여부 추정
TOURAPI_INDOOR_HINTS = {
    "A02020600": True,  # 박물관
    "A02020700": True,  # 미술관/전시관 계열
    "A02020900": True,  # 공연장
    "A05020900": True,  # 카페
    "A05020100": True,  # 한식 등 식당류
}

TOURAPI_CAT3_EXCLUDE = {
    "A02010900",  # 종교성지(교회)
    "A02030400",  # 사회복지시설
}

KAKAO_CATEGORY_GROUP_MAP = {
    "CT1": "문화시설",
    "AT4": "관광지",
    "FD6": "식당",
    "CE7": "카페",
}

CATEGORY_TAG_TO_CAT3 = {
    "카페": "A05020900",
}

GOOGLE_TYPE_CATEGORY_MAP = {
    "museum": "문화시설",
    "art_gallery": "문화시설",
    "tourist_attraction": "관광지",
    "park": "관광지",
    "cultural_landmark": "관광지",
    "historical_landmark": "관광지",
    "historical_place": "관광지",
    "cafe": "카페",
    "restaurant": "식당",
    "movie_theater": "문화시설",
}

GOOGLE_INDOOR_TYPE_MAP = {
    "museum": True,
    "art_gallery": True,
    "movie_theater": True,
    "cafe": True,
    "restaurant": True,
    "shopping_mall": True,
    "park": False,
    "tourist_attraction": None,
    "natural_feature": False,
}


# A01(자연) 계열은 명백히 실외로 간주
NATURE_CAT1 = {"A01"}

INDOOR_NAME_KEYWORDS = ["레스토랑", "카페", "센터", "박물관", "전시관", "체험관", "회관"]
OUTDOOR_NAME_KEYWORDS = ["공원", "계곡", "숲", "휴양림", "전망대", "둘레길", "마을"]


def map_category(item, source: str) -> str | None:
    if source == "tourapi":
        cat3 = item.get("cat3")
        if cat3 in TOURAPI_CAT3_CATEGORY_MAP:
            return TOURAPI_CAT3_CATEGORY_MAP[cat3]
        return TOURAPI_CONTENTTYPE_MAP.get(item.get("contenttypeid"))
    if source == "google":
        return GOOGLE_TYPE_CATEGORY_MAP.get(item)
    if source == "kakao":
        return KAKAO_CATEGORY_GROUP_MAP.get(item.get("category_group_code"))
    return None


def infer_indoor_by_cat1(cat1: str | None) -> bool | None:
    """cat1(대분류) 기준 실내 여부 추정. 명확한 경우만 판단."""
    if cat1 in NATURE_CAT1:
        return False
    return None


def infer_indoor_by_name(name: str | None) -> bool | None:
    """이름에 포함된 키워드로 실내 여부 보조 추정."""
    if not name:
        return None
    if any(kw in name for kw in INDOOR_NAME_KEYWORDS):
        return True
    if any(kw in name for kw in OUTDOOR_NAME_KEYWORDS):
        return False
    return None


def infer_indoor(
    source: str, raw_value: str, cat1: str | None = None, name: str | None = None
) -> bool | None:
    """카테고리 코드 기준으로 실내 여부 추정. 판단 불가하면 None.
    우선순위: 정확한 cat3 매핑 > cat1(대분류) > 이름 키워드"""
    if source == "tourapi":
        if raw_value in TOURAPI_INDOOR_HINTS:
            return TOURAPI_INDOOR_HINTS[raw_value]
        result = infer_indoor_by_cat1(cat1)
        if result is not None:
            return result
        return infer_indoor_by_name(name)
    if source == "google":
        return GOOGLE_INDOOR_TYPE_MAP.get(raw_value)
    return None
