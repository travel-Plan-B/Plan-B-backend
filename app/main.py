from fastapi import FastAPI

app = FastAPI(title="Plan-B API")

@app.get("/health")
def health_check():
    return {"status": "ok"}