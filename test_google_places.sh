curl -X POST "https://places.googleapis.com/v1/places:searchNearby" \
  -H "Content-Type: application/json" \
  -H "X-Goog-Api-Key: AIzaSyAPpXX0HnkCU0kdInDSJ4MZmbeuhbCwLOI" \
  -H "X-Goog-FieldMask: places.displayName,places.rating,places.userRatingCount,places.location,places.types" \
  -d '{
    "locationRestriction": {
      "circle": {
        "center": {"latitude": 37.5219, "longitude": 129.1145},
        "radius": 1000.0
      }
    },
    "maxResultCount": 10,
    "languageCide": "ko"
  }'