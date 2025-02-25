from fastapi import FastAPI
from app.api.routes.v1 import packing_list, dashboard
from app.services.monitoring import system_monitor

app = FastAPI(title="Rohdex POC")
app.include_router(packing_list.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

# Initialize system monitor on startup
system_monitor.print_summary()
