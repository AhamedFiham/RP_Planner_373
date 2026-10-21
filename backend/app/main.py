"""FastAPI entry point for the diabetes research backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, diabetes, diet, retinopathy, wound

app = FastAPI(title="DiabeticCARE Backend")

for router in (auth.router, diabetes.router, retinopathy.router, wound.router, diet.router):
    app.include_router(router, prefix="/api")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# Wrap the complete application so unhandled server errors also receive CORS headers.
app = CORSMiddleware(
    app,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
