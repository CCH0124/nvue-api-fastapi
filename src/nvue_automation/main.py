from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from nvue_automation.api.v1.endpoints import router as api_v1_router
from nvue_automation.api.v1.resources import platform
from nvue_automation.api.v1.resources import system
from nvue_automation.config.logging import setup_logging
from nvue_automation.config.settings import Settings
from nvue_automation.core.exceptions import NVUEAPIError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理應用程式生命週期：初始化與清理資源"""
    # 啟動時：建立全域異步連線客戶端（單例模式）
    settings = Settings()
    logger.info("[STARTUP] Initializing NVUE Automation API...")
    logger.info(f"[STARTUP] Connecting to NVUE API | base_url={settings.base_url}")

    # 初始化全域非同步客戶端（連線池）
    async_client = httpx.AsyncClient(
        auth=httpx.BasicAuth(settings.username, settings.password),
        verify=False,
        timeout=httpx.Timeout(30.0),
        headers={"Content-Type": "application/json"},
    )

    app.state.nvue_client = async_client
    app.state.settings = settings

    logger.info(
        f"[STARTUP] NVUE connection pool initialized | base_url={settings.base_url} | "
        f"timeout={30.0}s | verify_ssl=False"
    )

    yield  # 這裡程式會開始執行並等待請求

    logger.info("[SHUTDOWN] Closing NVUE connection pool...")
    await async_client.aclose()
    logger.warning("[SHUTDOWN] NVUE connection pool closed successfully")


def create_app() -> FastAPI:

    setup_logging()

    app = FastAPI(
        title="NVUE Automation API",
        description="NVUE",
        version="1.1.0",
        lifespan=lifespan,  # 註冊生命週期管理
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加 NVUEAPIError 全局异常处理器
    @app.exception_handler(NVUEAPIError)
    async def nvue_api_error_handler(request: Request, exc: NVUEAPIError):
        """處理 NVUE API 錯誤，返回結構化的錯誤響應"""
        logger.error(
            f"NVUE API Error | path={request.url.path} | method={request.method} | "
            f"status={exc.status_code} | detail={exc.detail}"
        )
        error_response = {
            "detail": exc.detail,
            "status": exc.status_code,
        }
        if exc.title:
            error_response["title"] = exc.title
        if exc.error_type:
            error_response["type"] = exc.error_type
        if exc.validation:
            error_response["validation"] = exc.validation
            logger.debug(f"[ERROR] Validation details: {exc.validation}")

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
        )

    # Register routers
    app.include_router(api_v1_router)
    app.include_router(platform.router)
    app.include_router(system.router)

    @app.get("/", tags=["Health Check"])
    async def root():
        return {"status": "online", "mode": "lifespan_managed"}

    return app


app = create_app()


def start():
    """封裝啟動邏輯，供 Poetry script 呼叫"""
    logger.info("[STARTUP] Starting NVUE Automation API server...")
    logger.info("[STARTUP] Server configuration | host=0.0.0.0 | port=8000 | reload=True")
    uvicorn.run(
        "nvue_automation.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # 使用 loguru
    )


if __name__ == "__main__":
    start()
