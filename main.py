from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="AI Voice Agent Backend")

app.include_router(router)