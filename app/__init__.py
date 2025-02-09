from fastapi import FastAPI

from .routers import health, ogr2ogr

app = FastAPI()
app.include_router(health.router)
app.include_router(ogr2ogr.router)
