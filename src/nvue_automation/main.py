from contextlib import asynccontextmanager

from fastapi import FastAPI
import httpx
import uvicorn
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.config.settings import Settings, settings
from nvue_automation.api.v1.endpoints import router as api_v1_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理應用程式生命週期：初始化與清理資源"""
    # 啟動時：建立全域異步連線客戶端（單例模式）
    settings = Settings()
    # 初始化全域非同步客戶端（連線池）
    async_client = httpx.AsyncClient(
        auth=httpx.BasicAuth(settings.username, settings.password),
        verify=False,
        timeout=httpx.Timeout(30.0),
        headers={"Content-Type": "application/json"}
    )
    
    app.state.nvue_client = async_client
    app.state.settings = settings
    
    logger.info(f"NVUE connection pool has been initialized with base URL: {settings.base_url}")
    
    yield  # 這裡程式會開始執行並等待請求
    
    await async_client.aclose()
    logger.warning("NVUE connection pool has been closed.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="NVUE Automation API",
        description="NVUE",
        version="1.1.0",
        lifespan=lifespan  # 註冊生命週期管理
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)

    @app.get("/", tags=["Health Check"])
    async def root():
        return {"status": "online", "mode": "lifespan_managed"}

    return app

app = create_app()

def start():
    """封裝啟動邏輯，供 Poetry script 呼叫"""
    import uvicorn
    uvicorn.run("nvue_automation.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()