from fastapi import FastAPI
from callus_research.api.routes import router
from callus_research.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(router)
