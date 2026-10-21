from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.db import connect_db, close_db, get_db
from app.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bolkhata")

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BolKhata backend server...")
    await connect_db()
    yield
    # Shutdown
    logger.info("Shutting down BolKhata backend server...")
    await close_db()

app = FastAPI(
    title="BolKhata Voice-Entry Ledger API",
    description="Phase 1 Backend API for voice-entry ledger",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS hardening
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def get_client_ip(request: Request) -> str:
    """
    Extract client IP safely.
    Only trust X-Forwarded-For if request comes directly from a configured trusted proxy.
    """
    remote_ip = request.client.host if request.client else "127.0.0.1"
    if remote_ip in settings.trusted_proxy_list:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in X-Forwarded-For is client origin
            return forwarded.split(",")[0].strip()
    return remote_ip

# Security & CSRF middleware
@app.middleware("http")
async def security_headers_and_csrf_middleware(request: Request, call_next):
    # Reject oversized requests immediately
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:
        return Response("Payload too large", status_code=413)

    # CSRF Check: On mutating/state-changing methods (POST, PUT, PATCH, DELETE)
    # Check Origin header against allowed CORS origins or same-origin proxy
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        origin = request.headers.get("origin")
        host = request.headers.get("host")
        if origin:
            # Normalize origin
            norm_origin = origin.rstrip("/")
            allowed = [o.rstrip("/") for o in settings.cors_origin_list]
            # Also allow direct same-origin host matches (e.g. http://host or https://host)
            host_matches = any(norm_origin.endswith(f"://{host}") or norm_origin == f"http://{host}" or norm_origin == f"https://{host}" for _ in [1])
            if norm_origin not in allowed and not host_matches:
                logger.warning(f"CSRF Origin check failed: origin '{origin}' not in allowed origins or matching host '{host}'")
                return Response(
                    '{"detail": "Cross-site request rejected (Origin mismatch)"}',
                    status_code=403,
                    media_type="application/json"
                )

    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    return response

# Include routes
app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    """
    Health check: In production (ENV=prod), verify that MongoDB is reachable.
    Fail health check with HTTP 503 if Mongo is down.
    """
    db = get_db()
    if settings.ENV == "prod":
        try:
            from app.db import client as mongo_client
            if mongo_client is None:
                return Response('{"status": "error", "detail": "MongoDB client uninitialized"}', status_code=503, media_type="application/json")
            await mongo_client.admin.command('ping')
        except Exception as e:
            logger.error(f"Health check failed in production: {e}")
            return Response(f'{{"status": "unhealthy", "error": "{str(e)}"}}', status_code=503, media_type="application/json")

    return {"status": "ok", "env": settings.ENV}
