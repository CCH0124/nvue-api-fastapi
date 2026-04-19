import httpx
from loguru import logger

from nvue_automation.config.settings import Settings
from nvue_automation.core.exceptions import NVUEAPIError


class AsyncNVUEClient:
    """處理非同步 HTTP 請求"""

    def __init__(self, settings: Settings):
        self.settings = settings
        # httpx 的 BasicAuth 類別
        self.auth = httpx.BasicAuth(settings.username, settings.password)
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """進入非同步上下文管理器"""
        self.client = httpx.AsyncClient(
            auth=self.auth,
            verify=False,  # 測試環境跳過 SSL
            timeout=httpx.Timeout(30.0),
            headers={"Content-Type": "application/json"},
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
        logger.debug(f"[HTTP] Preparing request | method={method} | path={path}")

        try:
            response = await self.client.request(method, url, **kwargs)
            await self._log_request(response)
            response.raise_for_status()
            logger.debug(f"[HTTP] Request successful | method={method} | status={response.status_code}")
            return response
        except httpx.HTTPStatusError as e:
            error_detail = self._extract_error_detail(e.response)
            logger.error(
                f"[HTTP] Request failed | method={method} | path={path} | "
                f"status={e.response.status_code} | error={error_detail.get('detail', str(e))}"
            )
            raise NVUEAPIError(
                status_code=e.response.status_code,
                detail=error_detail.get("detail", str(e)),
                title=error_detail.get("title"),
                error_type=error_detail.get("type"),
                validation=error_detail.get("validation"),
                response_body=error_detail,
            ) from e
        except httpx.TimeoutException:
            logger.error(f"[HTTP] Request timeout | method={method} | path={path} | timeout={self.client.timeout}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"[HTTP] Network error | method={method} | path={path} | error={str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"[HTTP] Unexpected error | method={method} | path={path} | error={type(e).__name__}: {str(e)}"
            )
            raise

    def _extract_error_detail(self, response: httpx.Response) -> dict:
        """提取 NVUE API 錯誤響應中的詳細信息"""
        try:
            error_body = response.json()
            return error_body if isinstance(error_body, dict) else {}
        except Exception:
            return {"detail": response.text or "Unknown error"}

    async def _log_request(self, r: httpx.Response):
        """偵錯日誌"""
        logger.debug(f"[HTTP] Request details | method={r.request.method} | url={r.request.url}")
        logger.debug(f"[HTTP] Response status | code={r.status_code}")
        if r.text:
            try:
                preview = r.text[:500] if len(r.text) > 500 else r.text
                logger.debug(f"[HTTP] Response body preview | length={len(r.text)} bytes | preview={preview}")
            except Exception:
                pass
