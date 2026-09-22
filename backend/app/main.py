from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api.router import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.services.seed import seed_if_empty


def _ensure_columns(bind=None) -> None:
    """极简启动迁移：为已存在的旧表补新增列（create_all 不会改既有表）。"""
    bind = bind or engine
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if "delivery_routes" in tables:
        cols = {c["name"] for c in inspector.get_columns("delivery_routes")}
        if "seal_weight_kg" not in cols:
            with bind.begin() as conn:
                conn.execute(
                    text("ALTER TABLE delivery_routes ADD COLUMN seal_weight_kg FLOAT")
                )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    if settings.seed_on_empty:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


app = FastAPI(title="BagRoute", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
