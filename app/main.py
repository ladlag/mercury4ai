from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.database import init_db
from app.api import health, tasks, import_export, runs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting application...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Continue anyway - tables might already exist
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title="Mercury4AI Crawl Orchestrator",
    description="Production-ready crawl4ai orchestrator with FastAPI, RQ, PostgreSQL, and MinIO",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(import_export.router)
app.include_router(runs.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Mercury4AI Crawl Orchestrator",
        "version": "1.0.0",
        "docs": "/docs"
    }
