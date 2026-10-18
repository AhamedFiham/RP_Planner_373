"""FastAPI entry point for the diabetes research backend."""

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api import diabetes, diet, retinopathy, wound

app = FastAPI(title="DiaCare AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

for router in (diabetes.router, retinopathy.router, wound.router, diet.router):
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
