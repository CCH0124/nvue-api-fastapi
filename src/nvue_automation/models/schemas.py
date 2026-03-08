from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConfigApplyRequest(BaseModel):
    """定義套用設定的請求結構"""
    path: str = Field(default="/", description="NVUE API 目標路徑")
    payload: Dict[str, Any] = Field(..., description="要套用的 JSON 配置內容")

class GenericResponse(BaseModel):
    """統一的 API 回應格式"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ConfigResponse(BaseModel):
    """配置查詢回應模型"""
    path: str | None = Field(default=None, description="NVUE API 路徑")
    data: Dict[str, Any]
