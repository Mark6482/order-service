from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from src.core.config import settings
from src.api.v1.api import api_router
from src.db.session import engine, Base
from src.utils.kafka.producer import event_producer
from src.utils.kafka.consumer import event_consumer

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Микросервис заказов",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await event_producer.start()
    asyncio.create_task(event_consumer.start())

@app.on_event("shutdown")
async def shutdown_event():
    await event_producer.stop()
    await event_consumer.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.DEBUG
    )