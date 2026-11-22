from fastapi import APIRouter

from app.api.routes import ai, items, photos, plans, spaces, system

api_router = APIRouter(prefix="/api")
for module in (system, spaces, photos, items, plans, ai):
    api_router.include_router(module.router)
