from fastapi import FastAPI
from app.api.routes.v1 import packing_list

app = FastAPI(title="Rohdex POC")
app.include_router(packing_list.router, prefix="/api/v1")
