#!/usr/bin/env python3
"""
Script de inicio para Railway deployment
"""
import os
import sys
import uvicorn

def main():
    # Get port from environment variable (Railway sets this)
    port = int(os.getenv("PORT", 8000))
    
    # Print startup information
    print("=" * 50)
    print("🚀 API Auth Gateway - Starting...")
    print(f"📡 Port: {port}")
    print(f"🏠 Host: 0.0.0.0")
    print(f"🔍 Health check: http://0.0.0.0:{port}/health")
    print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
    print("=" * 50)
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print("✅ Database configured")
    else:
        print("⚠️  DATABASE_URL not configured - using mock database for healthcheck only")
    
    # Check critical environment variables
    # No fallback: src/auth/jwt_utils.py rejects missing, short or placeholder keys.
    if not os.getenv("JWT_SECRET_KEY"):
        print("❌ JWT_SECRET_KEY is not set. Generate one with:")
        print('   python -c "import secrets; print(secrets.token_urlsafe(48))"')
        sys.exit(1)
    
    try:
        # Start the server
        print("🔥 Starting uvicorn server...")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            workers=1,
            reload=False,
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        print("📋 Full traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()