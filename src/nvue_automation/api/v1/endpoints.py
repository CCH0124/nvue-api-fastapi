from nvue_automation.config.settings import Settings
from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.models.schemas import ConfigApplyRequest, ConfigResponse, GenericResponse
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status, Query

from nvue_automation.services.nvue_service import AsyncNVUEService
from loguru import logger

router = APIRouter(prefix="/api/v1", tags=["Configuration"])

async def get_nvue_service():
    """
    FastAPI 依賴注入：自動建立與關閉非同步連線池。
    """
    settings = Settings()
    async with AsyncNVUEClient(settings) as client:
        yield AsyncNVUEService(client)

@router.post(
    "/config/deploy",
    response_model=GenericResponse, 
    status_code=status.HTTP_201_CREATED
)
async def api_apply_config(
    request: ConfigApplyRequest,
    service: AsyncNVUEService = Depends(get_nvue_service)
):
    """
    一鍵部署：建立 Revision -> 刪除舊設定 -> 套用新設定 -> 提交 -> 驗證狀態
    """
    try:
        await service.config_replace(path=request.path, payload=request.payload)
        return GenericResponse(
            success=True,
            message="Configuration deployed and verified successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

@router.get("/config/history", response_model=ConfigResponse)
async def get_config_history(
    changeset: str = Query(None, description="Revision ID"),
    service: AsyncNVUEService = Depends(get_nvue_service)
):
    try:
        resp = await service.config_history(changeset)
        return ConfigResponse(data=resp)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not retrieve history: {str(e)}")

@router.get("/config/find", response_model=ConfigResponse)
async def get_config_find(
    search_string: str = Query(None, description="Search string"),
    service: AsyncNVUEService = Depends(get_nvue_service)
):
    """
    查找配置：根據提供的搜索字符串查找配置項。
    nv config find <search_string>
    """
    try:
        resp = await service.config_find(search_string)
        return ConfigResponse(data=resp)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not retrieve history: {str(e)}")
    
@router.get("/config/show/all", response_model=ConfigResponse)
async def get_config_all(
    service: AsyncNVUEService = Depends(get_nvue_service)
):
    """
    Shows the currently applied configuration in json format.
    """
    try:
        resp = await service.config_show()
        return ConfigResponse(data=resp)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not retrieve history: {str(e)}")

@router.get("/config/diff/{resource:path}", response_model=ConfigResponse)
async def get_config_diff(
    resource: str = Path(..., description="NVUE API 路徑"),
    base_changeset: str = Query("applied", description="Base Revision ID"),
    target_changeset: str = Query("empty", description="Target Revision ID"),
    service: AsyncNVUEService = Depends(get_nvue_service)
):
    try:
        resp = await service.get_revision_diff(resource, base_changeset, target_changeset)
        return ConfigResponse(data=resp)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not retrieve history: {str(e)}")


@router.get("/config/{path:path}", response_model=ConfigResponse)
async def get_configuration(
    path: str = Path(..., description="NVUE API 路徑"),
    service: AsyncNVUEService = Depends(get_nvue_service)
):
    """
    獲取指定路徑的當前配置
    """
    try:
        resp = await service.get_config(path)
        return ConfigResponse(path=path, data=resp)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not retrieve config: {str(e)}")