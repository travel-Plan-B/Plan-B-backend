from fastapi import FastAPI

from app.api.places import router as places_router
from app.api.recommendations import router as recommendations_router
from app.api.schedule import router as schedule_router
from app.api.simple import router as simple_router

app = FastAPI(title="Plan-B API")

app.include_router(places_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(simple_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
