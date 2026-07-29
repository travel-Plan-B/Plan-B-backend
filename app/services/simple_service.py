def filter_by_category_whitelist(places, problem_reason: str, situational_answer: str | None = None):
    """문제 사유에 맞는 카테고리만 필터링. 시간 문제일 땐 카테고리 제한 없음."""
    if problem_reason == "WEATHER":
        if situational_answer in ("OUTDOOR_ONLY", "BOTH"):
            places = [p for p in places if p.is_indoor is True]
        if situational_answer in ("WALKING_ONLY", "BOTH"):
            places = [p for p in places if p.category_tag != "레포츠"]

    # PLACE_UNAVAILABLE, TIME_CHANGED은 카테고리 자체를 제한하지 않음
    return places