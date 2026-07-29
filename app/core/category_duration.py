CATEGORY_DEFAULT_DURATION = {
    "관광지": 40,
    "문화시설": 60,
    "카페": 40,
    "식당": 50,
    "레포츠": 90,
}


def get_default_duration(category_tag: str) -> int:
    """카테고리별 기본 체류시간(분). 매핑 없으면 보수적으로 30분."""
    return CATEGORY_DEFAULT_DURATION.get(category_tag, 30)
