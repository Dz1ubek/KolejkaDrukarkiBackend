from fastapi import APIRouter
from app.api.v1.endpoints import admin, health, items

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(items.router)
api_router.include_router(admin.router)
