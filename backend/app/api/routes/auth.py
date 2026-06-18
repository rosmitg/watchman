from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/health")
async def auth_health() -> dict:
    return {"status": "ok"}


@router.get("/me")
async def read_current_user(user: dict = Depends(get_current_user)) -> dict:
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
    }
