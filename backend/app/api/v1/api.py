from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, drawings, processing, analysis


api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)

api_router.include_router(
    drawings.router,
    prefix="/drawings",
    tags=["Drawings"]
)

api_router.include_router(
    processing.router,
    prefix="/processing",
    tags=["Processing"]
)

api_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis"],
)
