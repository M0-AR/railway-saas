import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.audit import router as audit_router
from app.billing import router as billing_router
from app.bookings import router as bookings_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.rate_limit import limiter
from app.core.request import client_ip
from app.core.security import decode_token
from app.db.rls import verify_rls_enforcement
from app.db.session import async_session_maker, engine
from app.identity import router as identity_router
from app.identity.service import ensure_plans
from app.public import router as public_router
from app.reports import router as reports_router
from app.trains import router as trains_router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("railway")

API = settings.api_v1_prefix


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session_maker() as session:
        problems = await verify_rls_enforcement(session)
        if problems:
            for problem in problems:
                logger.error("RLS enforcement problem: %s", problem)
            raise RuntimeError(
                "Refusing to start: multi-tenant isolation is not enforced — " + "; ".join(problems)
            )
        await ensure_plans(session)
        await session.commit()

    await limiter.start()

    if settings.seed_demo:
        from app.seed import seed_all

        async with async_session_maker() as session:
            try:
                await seed_all(session)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("demo seed failed")

    logger.info(
        "%s started (env=%s). Multi-tenant RLS enforcement verified.",
        settings.project_name,
        settings.environment,
    )
    yield
    await limiter.stop()
    await engine.dispose()


app = FastAPI(
    title=settings.project_name,
    description="Multi-tenant railway reservation platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-Request-ID"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/healthz", "/readyz") or not path.startswith(API):
        return await call_next(request)

    auth_path = path.startswith(f"{API}/auth/") or path.startswith(f"{API}/public/")
    limit = (
        settings.auth_rate_limit_per_minute if auth_path else settings.rate_limit_per_minute
    )

    key = None
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        try:
            payload = decode_token(header[7:], expected_type="access")
            key = f"rl:t:{payload['tid']}"
        except Exception:
            key = None
    if key is None:
        key = f"rl:ip:{client_ip(request)}"

    retry_after = await limiter.hit(key, limit)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Too many requests. Please slow down and retry shortly.",
                    "details": None,
                }
            },
            headers={"Retry-After": str(max(1, int(retry_after)))},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": exc.code, "message": exc.message, "details": exc.details}
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed.",
                "details": [
                    {"loc": list(err.get("loc", [])), "msg": err.get("msg", ""),
                     "type": err.get("type", "")}
                    for err in exc.errors()
                ],
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Something went wrong on our side.",
                "details": None,
            }
        },
    )


@app.get("/healthz", tags=["system"])
async def healthz():
    return {"status": "ok", "service": settings.project_name, "version": app.version}


@app.get("/readyz", tags=["system"])
async def readyz():
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


app.include_router(identity_router.router, prefix=API, tags=["identity"])
app.include_router(trains_router.router, prefix=f"{API}/trains", tags=["trains"])
app.include_router(bookings_router.router, prefix=f"{API}/bookings", tags=["bookings"])
app.include_router(reports_router.router, prefix=f"{API}/reports", tags=["reports"])
app.include_router(audit_router.router, prefix=f"{API}/audit", tags=["audit"])
app.include_router(public_router.router, prefix=f"{API}/public", tags=["public"])
app.include_router(billing_router.router, prefix=f"{API}/billing", tags=["billing"])
