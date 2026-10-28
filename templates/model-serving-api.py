"""Template: model-serving API (FastAPI).

Dependency: fastapi, uvicorn (Module 24-এ pin করা version সহ শেখানো হবে)
চালানো:  uvicorn model-serving-api:app --port 8000   (file নাম বদলে model_api.py করুন)

নিয়ম:
- response-এ model version ফেরত দিন (debug ও rollback-এর জন্য)
- input validate করুন (pydantic)
- /health = process বেঁচে আছে; /ready = model load হয়েছে
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_VERSION = os.environ.get("MODEL_VERSION", "dev")
_model = None  # startup-এ load হবে


@asynccontextmanager
async def lifespan(_: FastAPI):
    # startup: model load (পুরোনো @app.on_event("startup") deprecated, lifespan ব্যবহার করুন)
    global _model
    # আসল implementation: registry থেকে নির্দিষ্ট version load
    _model = lambda xs: sum(xs) / len(xs)  # noqa: E731 — placeholder model, স্পষ্টভাবে mock
    yield
    _model = None  # shutdown


app = FastAPI(title="model-api", version=MODEL_VERSION, lifespan=lifespan)


class PredictRequest(BaseModel):
    features: list[float] = Field(min_length=1, max_length=100)


class PredictResponse(BaseModel):
    prediction: float
    model_version: str
    latency_ms: float


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    if _model is None:
        raise HTTPException(503, "model not loaded")
    return {"status": "ready", "model_version": MODEL_VERSION}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    if _model is None:
        raise HTTPException(503, "model not loaded")
    start = time.perf_counter()
    y = _model(req.features)
    return PredictResponse(prediction=y, model_version=MODEL_VERSION,
                           latency_ms=(time.perf_counter() - start) * 1000)
