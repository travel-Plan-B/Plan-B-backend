curl -G "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst" \
  --data-urlencode "serviceKey=b822316089526ad4f95916723eccd60b338cb51473270ee33cd55967d7d8575f" \
  --data-urlencode "numOfRows=100" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "dataType=JSON" \
  --data-urlencode "base_date=20260722" \
  --data-urlencode "base_time=0500" \
  --data-urlencode "nx=90" \
  --data-urlencode "ny=100" 
