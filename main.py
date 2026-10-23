import os
from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from src.config.database import create_tables
from src.routers import auth, inventory

# Load environment variables from .env file
load_dotenv()


# Configure Sentry for error tracking
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables (only if DATABASE_URL is configured)
    database_url = os.getenv("DATABASE_URL")
    if database_url and not database_url.startswith("postgresql://user:password@localhost"):
        try:
            print("🔄 Initializing database tables...")
            await create_tables()
            print("✅ Database tables initialized successfully")
        except Exception as e:
            print(f"⚠️  Database initialization failed: {e}")
            print("🔄 Continuing without database (health check only mode)")
    else:
        print("⚠️  Skipping database initialization - Configure DATABASE_URL for production")
    yield
    # Shutdown: Clean up resources if needed
    print("🔄 Shutting down API Gateway...")


# Create FastAPI app instance
app = FastAPI(
    title="API Auth Gateway",
    description="API Gateway que proporciona acceso autenticado a la API de inventario de activos",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for Railway deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(inventory.router, prefix="/inventario", tags=["Inventory"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "API Auth Gateway",
        "status": "active",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "timestamp": "2025-09-19T00:00:00Z"}


@app.get("/debug")
async def debug_info():
    """Debug endpoint to check configuration"""
    from src.config.db_status import check_database_available
    
    # Public endpoint: report what is configured, never any part of the values
    return {
        "database_configured": check_database_available(),
        "jwt_secret_configured": bool(os.getenv("JWT_SECRET_KEY")),
        "inventory_api_url": os.getenv("INVENTORY_API_BASE_URL"),
        "environment": os.getenv("ENVIRONMENT", "production")
    }


# Railway compatibility: Run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting API Auth Gateway on port {port}")
    print(f"📊 Health check endpoint: http://0.0.0.0:{port}/health")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        access_log=True,
        log_level="info"
    )