from fastapi import APIRouter, HTTPException
from app.services.email_service import EmailService

#
router = APIRouter(prefix="/packing-list", tags=["Packing List"])


@router.post("/process-email")
async def process_rohdex_email():
    """
    Fetches emails by subject processes attachments,
    generates packing list, and sends response email.
    """
    try:
        email_service = EmailService()
        result = await email_service.process_rohdex_emails()
        return {
            "status": "success",
            "message": "Email processing completed",
            "details": result,
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing email: {str(e)}")
