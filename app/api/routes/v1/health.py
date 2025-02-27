from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """
    Simple health check endpoint to verify the API is running
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "rohdex-poc",
    }
