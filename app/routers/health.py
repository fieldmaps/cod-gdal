from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", description="Health Check", tags=["Health Check"])
def ping() -> dict[str, str]:
    """Makes sure server isn't dead.

    Returns:
        Proof of life.
    """
    return {"ping": "pong"}
