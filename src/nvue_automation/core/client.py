from typing import Optional

import httpx
from loguru import logger

from nvue_automation.config.settings import Settings, settings

class AsyncNVUEClient:
    """處理非同步 HTTP 請求"""
    def __init__(self, settings: Settings):
        self.settings = settings
        # httpx 的 BasicAuth 類別
        self.auth = httpx.BasicAuth(settings.username, settings.password)
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """進入非同步上下文管理器"""
        self.client = httpx.AsyncClient(
            auth=self.auth,
            verify=False,  # 測試環境跳過 SSL
            timeout=httpx.Timeout(30.0),
            headers={"Content-Type": "application/json"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """結束非同步上下文管理器並關閉連線"""
        if self.client:
            await self.client.aclose()

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """統一的非同步請求入口"""
        if not self.client:
            raise RuntimeError("Client is not initialized. Use 'async with' context.")
            
        url = f"{self.settings.base_url.rstrip('/')}{path}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            await self._log_request(response)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Async request failed: {e}")
            raise

    async def _log_request(self, r: httpx.Response):
        """偵錯日誌"""
        logger.debug(f"Async Request: {r.request.method} {r.request.url}")
        logger.debug(f"Response Status: {r.status_code}")
        if r.text:
            try:
                # 嘗試格式化 JSON 輸出方便除錯，若非 JSON 則輸出純文字
                logger.debug(f"Response Body: {r.text[:500]}") # 限制長度避免洗板
            except Exception:
                pass