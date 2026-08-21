from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.places import router as places_router
from app.api.recommendations import router as recommendations_router
from app.api.schedule import router as schedule_router
from app.api.simple import router as simple_router
from app.api.weather import router as weather_router

app = FastAPI(title="Plan-B API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend-domain.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(places_router, prefix="/api/v1")
app.include_router(recommendations_router, prefix="/api/v1")
app.include_router(simple_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(weather_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
