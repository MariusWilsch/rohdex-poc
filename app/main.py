from fastapi import FastAPI
from app.api.routes.v1 import packing_list, health
from app.services.monitoring import system_monitor
from app.services.email_service import EmailService
from app.core.config import get_settings
from contextlib import asynccontextmanager

# Create global email service instance
email_service = EmailService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for the FastAPI application.
    Handles both startup and shutdown events in a single function.
    """
    # Startup: Initialize services
    system_monitor.print_summary()

    # Store email service in application state and start polling
    app.state.email_service = email_service

    if get_settings().EMAIL_POLLING_ENABLED:
        email_service.start_polling()
        print(
            f"Automatic email polling started with interval: {email_service.poll_interval}s"
        )
    else:
        print("Automatic email polling disabled by configuration")

    # Yield control back to FastAPI
    yield

    # Shutdown: Clean up resources
    print("Application shutting down")

    if hasattr(app.state, "email_service"):
        app.state.email_service.stop_polling()
        print("Email polling stopped")


# Create FastAPI app with lifespan handler
app = FastAPI(title="Rohdex POC", lifespan=lifespan)
app.include_router(packing_list.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
# Dashboard routes disabled as requested
# app.include_router(dashboard.router, prefix="/api/v1")
