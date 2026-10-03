"""FastAPI entry point for the diabetes research backend."""

from fastapi import FastAPI

from app.api import diabetes, diet, retinopathy, wound

app = FastAPI(title="DiaCare AI Backend")

for router in (diabetes.router, retinopathy.router, wound.router, diet.router):
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
