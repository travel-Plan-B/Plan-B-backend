curl -G "https://apis-navi.kakaomobility.com/v1/directions" \
  -H "Authorization: KakaoAK 8a818736e569edb631f9cc7d15838e12" \
  --data-urlencode "origin=129.1145,37.5219" \
  --data-urlencode "destination=129.1223,37.5199" \
  --data-urlencode "priority=RECOMMEND"
