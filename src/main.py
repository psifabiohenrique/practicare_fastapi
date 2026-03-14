import asyncio
import sys

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from src.core.bootstrap import init_storage_dirs
from src.core.exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.routers import (
    auth_controller,
    patients_with_treatment_controller,
    treatment_record_controller,
    treatment_report_controller,
    users_controller,
)
from src.routers.deps import csrf_protect
from src.settings import settings

if sys.platform == "win32":  # pragma: no cover
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


app = FastAPI(
    title="Practicare FastAPI",
    docs_url=None if settings.PRODUCTION else "/docs",
    redoc_url=None if settings.PRODUCTION else "/redoc",
    openapi_url=None if settings.PRODUCTION else "/openapi.json",
    redirect_slashes=False,
    dependencies=[Depends(csrf_protect)],
)

# app.add_middleware(HTTPSRedirectMiddleware)

origins = [str(url).rstrip("/") for url in settings.ALLOWED_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_storage_dirs()


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ForbiddenError)
async def forbidden_exception_handler(request: Request, exc: ForbiddenError):
    return JSONResponse(status_code=403, content={"detail": exc.message})


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_exception_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.exception_handler(UnauthorizedError)
async def unauthorized_exception_handler(
    request: Request, exc: UnauthorizedError
):
    return JSONResponse(status_code=401, content={"detail": exc.message})


@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=500, content={"detail": exc.message})


app.include_router(auth_controller.router)
app.include_router(users_controller.router)
app.include_router(patients_with_treatment_controller.router)
app.include_router(treatment_record_controller.router)
app.include_router(treatment_report_controller.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}
