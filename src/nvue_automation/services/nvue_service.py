import asyncio
from importlib.resources import path
import urllib.parse
from loguru import logger
from typing import Any, Dict
import orjson
from nvue_automation.core.client import AsyncNVUEClient


class AsyncNVUEService:
    """處理 NVUE 業務邏輯 (非同步版本)"""
    
    def __init__(self, client: AsyncNVUEClient):
        self.client = client
        self.settings = client.settings

    async def create_revision(self) -> str:
        """建立新的 Revision 並獲取 Changeset ID"""
        logger.info("Creating NVUE Revision...")
        resp = await self.client.request("POST", "/revision")
        data = resp.json()
        # 取得字典中的第一個鍵作為 changeset
        changeset = list(data.keys())[0]
        logger.info(f"Created Revision: {changeset}")
        return changeset

    async def patch_config(self, path: str, payload: Dict[str, Any], changeset: str):
        """將配置寫入特定的 Revision 中"""
        logger.info(f"Writing configuration to path {path} (Revision: {changeset})")
        params = {"rev": changeset}
        await self.client.request("PATCH", path, content=orjson.dumps(payload), params=params)

    async def detach_config(self, changeset: str):
        """
        Detaches the configuration from the current pending configuration.
        nv config detach
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigdetach
        """
        logger.info(f"Detaching configuration from Revision: {changeset}")
        await self.client.request("DELETE", f"/revision/{changeset}")

    async def delete_config(self, path: str, changeset: str):
        """刪除指定路徑的現有設定"""
        logger.info(f"Deleting configuration from path {path} (Revision: {changeset})")
        params = {"rev": changeset}
        await self.client.request("DELETE", path, params=params)

    async def apply_changeset(self, changeset: str):
        """
        Applies the pending configuration to become the applied configuration.
        nv config apply
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigapply
        """
        logger.info(f"Applying Changeset: {changeset}")
        apply_payload = {"state": "apply", "auto-prompt": {"ays": "ays_yes"}}
        
        # 使用標準函式庫進行 URL 安全編碼
        # safe="" 參數確保連 '/' 都會被轉義，這與 requests.utils.quote(..., safe="") 行為一致
        quoted_id = urllib.parse.quote(changeset, safe="")

        await self.client.request(
            "PATCH", 
            f"/revision/{quoted_id}", 
            content=orjson.dumps(apply_payload)
        )

    async def wait_for_applied(self, changeset: str) -> bool:
        """
        輪詢直到 Revision 狀態確認為 'applied'。
        同樣使用 urllib.parse.quote 來建構路徑。
        """
        for i in range(self.settings.retries):
            resp = await self.config_history(changeset)
            state = resp.get("state")
            logger.info(f"Checking deployment status... Current state: {state} (Attempt {i+1})")
            
            if state == "applied_and_saved":
                logger.info("Deployment successful: Configuration has been applied.")
                return True
            
            await asyncio.sleep(self.settings.poll_interval)
        
        logger.error("Deployment failed: Status did not change to 'applied' within the expected time.")
        return False

    async def config_replace(self, path: str, payload: Dict[str, Any]):
        """
        nv config replace
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigreplace
        https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Config-Commands/#hnv-config-replace-nvue-fileh
        """
        logger.info(f"Starting full deployment process for path {path} using config replace method.")
        changeset = await self.create_revision()
        try:
            await self.delete_config(path, changeset)
            await self.patch_config(path, payload, changeset)
            await self.apply_changeset(changeset)
            if not await self.wait_for_applied(changeset):
                raise RuntimeError("NVUE Configuration status check failed, configuration not applied correctly.")
        except Exception as e:
            logger.error(f"Non-blocking deployment process exception: {e}")
            raise

    async def config_merge(self, path: str, payload: Dict[str, Any]):
        """
        """
        logger.info(f"Starting full deployment process for path {path} using merge method.")
        changeset = await self.create_revision()
        try:
            await self.patch_config(path, payload, changeset)
            await self.apply_changeset(changeset)
            if not await self.wait_for_applied(changeset):
                raise RuntimeError("NVUE Configuration status check failed, configuration not applied correctly.")
        except Exception as e:
            logger.error(f"Non-blocking deployment process exception: {e}")
            raise

    async def get_config(self, path: str) -> Dict[str, Any]:
        """獲取當前配置數據"""
        clean_path = f"/{path.lstrip('/')}"
        resp = await self.client.request("GET", clean_path)
        return resp.json()
    
    async def get_revision_diff(self, resource: str, base_changeset: str, target_changeset: str) -> Dict[str, Any]:
        """
        Shows differences between configurations, such as the pending configuration and the applied configuration or the detached configuration and the pending configuration.
        nv config diff applied pending
        nv config diff
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigdiff
        https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Config-Commands/#hnv-config-diff-revision-base-revision-targeth
        """
        logger.info(f"Getting configuration diff between from {base_changeset} to {target_changeset} for resource {resource}")
        base_quoted = urllib.parse.quote(base_changeset, safe="")
        target_quoted = urllib.parse.quote(target_changeset, safe="")
        path = f"/{resource}?rev={base_quoted}&diff={target_quoted}"
        
        resp = await self.client.request("GET", path)
        return resp.json()
    
    async def config_find(self, search_string: str) -> Dict[str, Any]:
        """
        Finds a portion of the applied configuration according to the provided string.
        nv config find
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigfind
        https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Config-Commands/#hnv-config-findh
        """
        logger.info(f"Searching for string in configuration: {search_string}")
        params = {
            "rev": "applied",
            "filled": False,
            "diff": "", 
            "search-string": search_string
        }
        
        resp = await self.client.request("GET", "/", params=params)
        return resp.json()
    async def config_history(self, changeset: str | None) -> Dict[str, Any]:
        """
        changeset: pending configuration, applied configuration, detached configuration, startup configuration
        Shows the apply history for the revision.
        nv config history {changeset}
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfighistory
        https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Config-Commands/#hnv-config-history-resourceh
        """
        if not changeset:
            logger.info("Getting configuration history for all revisions...")
            resp = await self.client.request("GET", "/revision")
            return resp.json()

        quoted_id = urllib.parse.quote(changeset, safe="")
        logger.info(f"Getting configuration history for revision: {changeset}")
        path = f"/revision/{quoted_id}"
        
        resp = await self.client.request("GET", path)
        return resp.json()
    async def save_changeset(self, changeset: str):
        """
        Overwrites the startup configuration with the applied configuration. The configuration persists after a reboot.
        nv config save
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigsave
        https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Config-Commands/#hnv-config-saveh
        """
        logger.info(f"Saving Changeset: {changeset}")
        save_payload = {"state": "save", "auto-prompt": {"ays": "ays_yes"}}
        
        quoted_id = urllib.parse.quote(changeset, safe="")

        await self.client.request(
            "PATCH", 
            f"/revision/{quoted_id}", 
            content=orjson.dumps(save_payload)
        )

    async def config_show(self) -> Dict[str, Any]:
        """
        Shows the currently applied configuration in yaml format.
        nv config show
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigshow
        https://docs.nvidia.com/networking-ethernet-software/nvue-reference/Config-Commands/#hnv-config-showh
        """
        logger.info("Retrieving currently applied configuration...")
        query_params = {
            "rev": "applied",
            "filled": False
        }
        resp = await self.client.request("GET", "/", params=query_params)
        return resp.json()
    
    async def unset_config(self, path: str, payload: Dict[str, Any]):
        """
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/nvue-openapi#src-4734125721_NVUEOpenAPI-UnsetaConfigurationChange
        https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-512/System-Configuration/NVIDIA-User-Experience-NVUE/NVUE-API/#unset-a-configuration-change
        """
        changeset = await self.create_revision()
        try:
            await self.patch_config(path, payload, changeset)
            await self.apply_changeset(changeset)
            if not await self.wait_for_applied(changeset):
                raise RuntimeError("NVUE Configuration status check failed, configuration not applied correctly.")
        except Exception as e:
            logger.error(f"Non-blocking unset configuration process exception: {e}")
            raise