from fastapi import APIRouter

from app.auth import CurrentUser
from app.schemas import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user
