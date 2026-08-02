from app.services.category_map import infer_indoor, map_category


def normalize_tourapi_place(item: dict) -> dict | None:
    """TourAPI 원본 데이터를 Place 테이블 스키마에 맞는 딕셔너리로 변환.
    카테고리 매핑 안 되면 None 반환 (화이트리스트 제외 대상)."""
    category_tag = map_category(item, source="tourapi")
    if category_tag is None:
        return None

    cat3 = item.get("cat3")

    return {
        "source": "tourapi",
        "source_id": item.get("contentid"),
        "name": item.get("title"),
        "address": item.get("addr1"),
        "category_tag": category_tag,
        "is_indoor": infer_indoor("tourapi", cat3, cat1=item.get("cat1"), name=item.get("title")),
        "lat": float(item.get("mapy")),
        "lng": float(item.get("mapx")),
        "image_url": item.get("firstimage") or None,
        "description": None,
        "rating": None,
        "user_rating_count": None,
        "operating_hours": None,
        "parking_available": None,
        "raw_category_source": cat3 or item.get("contenttypeid"),
    }


def normalize_kakao_place(item: dict) -> dict | None:
    """카카오 검색 결과를 Place 테이블 스키마로 변환. 카테고리 매핑 안 되면 None."""
    category_tag = map_category(item, source="kakao")
    if category_tag is None:
        return None

    return {
        "source": "kakao",
        "source_id": item.get("id"),
        "name": item.get("place_name"),
        "address": item.get("road_address_name") or item.get("address_name"),
        "category_tag": category_tag,
        "is_indoor": None,  # 카카오는 실내외 정보 안 줌, 정보 없음으로 둠
        "lat": float(item.get("y")),
        "lng": float(item.get("x")),
        "image_url": None,
        "description": None,
        "rating": None,
        "user_rating_count": None,
        "operating_hours": None,
        "parking_available": None,
        "raw_category_source": item.get("category_group_code"),
    }
