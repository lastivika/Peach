from fastapi import APIRouter, Depends

from app.api.routes import items, me
from app.auth import current_user

# Everything under /api/v1 needs a signed-in user. Declared once here, so a new
# route cannot be added unprotected by forgetting a parameter. Routes that need
# the user object still ask for CurrentUser; FastAPI resolves it only once.
api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(current_user)])
api_router.include_router(items.router)
api_router.include_router(me.router)
