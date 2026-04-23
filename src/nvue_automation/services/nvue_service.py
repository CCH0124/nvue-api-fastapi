import asyncio
import urllib.parse
from typing import Any

import orjson
from loguru import logger

from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.core.exceptions import ConfigurationError
from nvue_automation.core.trace import add_span_attributes, trace_span_attributes
from nvue_automation.models.schemas import ApplyOptions
from nvue_automation.models.schemas import AutoPrompt
from nvue_automation.models.schemas import RevisionInfo
from nvue_automation.models.schemas import RevisionState
from nvue_automation.models.schemas import SpecialRevisionName


class AsyncNVUEService:
    """
    Asynchronous NVUE service for managing network device configurations.

    This service provides high-level operations for NVUE (NVIDIA User Experience) API,
    including configuration management, revision control, and deployment workflows.

    Attributes:
        client (AsyncNVUEClient): HTTP client for NVUE API communication
        settings (Settings): Configuration settings for the service
    """

    def __init__(self, client: AsyncNVUEClient):
        """
        Initialize the NVUE service with an async client.

        Args:
            client (AsyncNVUEClient): Configured async HTTP client for NVUE API
        """
        self.client = client
        self.settings = client.settings
    

    async def create_revision(self) -> str:
        """
        Create a new NVUE revision in pending state.

        A revision represents a configuration snapshot that can be modified and applied.
        All configuration changes must be made within a revision before being applied.

        Returns:
            str: Changeset ID (revision identifier) for the newly created revision

        Raises:
            NVUEAPIError: If the API request fails

        Example:
            >>> changeset = await service.create_revision()
            >>> print(f"Created revision: {changeset}")
            Created revision: 7
        """
        logger.info("[REVISION] Creating new NVUE revision with pending state")
        resp = await self.client.request("POST", "/revision")
        data = resp.json()
        # 取得字典中的第一個鍵作為 changeset
        changeset = list(data.keys())[0]
        logger.info(f"[REVISION] Successfully created revision | changeset={changeset} | state=pending")
        logger.debug(f"[REVISION] Full response: {data}")
        return changeset

    async def patch_config(self, path: str, payload: dict[str, Any], changeset: str):
        """
        Write or update configuration at a specific path within a revision.

        This operation patches (merges) the provided configuration into the existing
        configuration at the specified path without deleting other settings.

        Args:
            path (str): NVUE API path (e.g., '/interface/swp1', '/router/bgp')
            payload (dict[str, Any]): Configuration data to apply
            changeset (str): Target revision ID to write the configuration to

        Raises:
            NVUEAPIError: If the API request fails or validation errors occur

        Example:
            >>> await service.patch_config(
            ...     path="/interface/swp1",
            ...     payload={"type": "swp", "link": {"state": {"up": {}}}},
            ...     changeset="7"
            ... )
        """
        logger.info(f"[CONFIG] Patching configuration | path={path} | changeset={changeset}")
        logger.debug(f"[CONFIG] Payload keys: {list(payload.keys())}")
        params = {"rev": changeset}
        await self.client.request("PATCH", path, content=orjson.dumps(payload), params=params)
        logger.info(f"[CONFIG] Successfully patched configuration | path={path}")

    async def detach_config(self, changeset: str):
        """
        Detach and discard a pending revision without applying it.

        This operation removes a pending revision and all its configuration changes.
        The changeset must be in pending state. This is equivalent to 'nv config detach'.
        Use this to abandon changes without affecting the applied configuration.

        Args:
            changeset (str): Revision ID to detach (must be in pending state)

        Raises:
            NVUEAPIError: If the changeset doesn't exist or is not in pending state

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigdetach

        Example:
            >>> await service.detach_config("7")
            # Revision 7 is discarded
        """
        logger.info(f"[CONFIG] Detaching pending configuration | changeset={changeset}")
        await self.client.request("DELETE", f"/revision/{changeset}")
        logger.info(f"[CONFIG] Successfully detached configuration | changeset={changeset}")

    async def delete_config(self, path: str, changeset: str):
        """
        Delete configuration at a specific path within a pending revision.

        This operation removes the configuration object at the specified path.
        The changeset must be in pending state. The path must start with '/'.

        Args:
            path (str): NVUE API path to delete (must start with '/', e.g., '/interface/swp1')
            changeset (str): Target revision ID (must be in pending state)

        Raises:
            NVUEAPIError: If the path doesn't exist or the changeset is not pending

        Example:
            >>> await service.delete_config("/interface/swp1", "7")
            # Deletes swp1 interface configuration from revision 7
        """
        logger.info(f"[CONFIG] Deleting configuration | path={path} | changeset={changeset}")
        params = {"rev": changeset}
        await self.client.request("DELETE", path, params=params)
        logger.info(f"[CONFIG] Successfully deleted configuration | path={path}")

    async def apply_changeset(
        self,
        changeset: str,
        options: ApplyOptions | None = None,
    ) -> dict[str, Any]:
        """
        Applies the pending configuration to become the applied configuration.
        nv config apply
        https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigapply

        Args:
            changeset: The revision ID to apply
            options: Apply operation options (message, auto-prompt, state-controls)

        Returns:
            dict: Response from the NVUE API containing apply operation details

        Examples:
            # Basic apply
            await service.apply_changeset("changeset_123")

            # Apply with commit message
            await service.apply_changeset(
                "changeset_123",
                options=ApplyOptions(message="Critical BGP change")
            )

            # Safe apply with auto-rollback if not confirmed within 5 minutes
            # Note: This returns immediately, requires manual confirmation via separate API call
            await service.apply_changeset(
                "changeset_123",
                options=ApplyOptions.with_confirm(300, "Critical change - requires confirmation")
            )

            # Quick apply (skip health check for testing)
            await service.apply_changeset(
                "changeset_123",
                options=ApplyOptions.quick_apply("Test config", skip_health_check=True)
            )
        """
        logger.info(f"[APPLY] Initiating changeset apply operation | changeset={changeset}")

        # Use default options if not provided
        if options is None:
            options = ApplyOptions()
            logger.debug("[APPLY] Using default apply options")

        # Build base payload
        apply_payload: dict[str, Any] = {"state": RevisionState.APPLY.value}

        # Merge options into payload
        options_payload = options.to_payload()
        logger.debug(f"[APPLY] Options payload: {options_payload}")
        apply_payload.update(options_payload)

        # Log important settings
        if options.message:
            logger.info(f"[APPLY] Commit message: '{options.message}'")

        if options.state_controls and options.state_controls.confirm:
            logger.warning(
                f"[APPLY] AUTO-ROLLBACK ENABLED | timeout={options.state_controls.confirm}s | "
                f"Configuration will auto-rollback if not confirmed. "
                f"Use 'nv config apply --confirm-status' or GET /revision/{{id}} to check status."
            )

        if options.state_controls and options.state_controls.check_health == "skip":
            logger.warning("[APPLY] Health check DISABLED for this operation")

        # 使用標準函式庫進行 URL 安全編碼
        quoted_id = urllib.parse.quote(changeset, safe="")

        logger.debug(f"[APPLY] Sending apply request to NVUE API | endpoint=/revision/{quoted_id}")
        resp = await self.client.request("PATCH", f"/revision/{quoted_id}", content=orjson.dumps(apply_payload))
        result = resp.json()
        logger.info(f"[APPLY] Apply request accepted | changeset={changeset}")
        return result

    async def wait_for_applied(self, changeset: str) -> dict[str, Any]:
        """
        Poll and wait until a revision reaches 'applied_and_saved' state.

        This method continuously checks the revision status at configured intervals
        until the configuration is fully applied and persisted, or until timeout.

        WARNING: Do not use this method when applying with confirm timeout, as the
        configuration requires manual confirmation and won't automatically reach
        'applied_and_saved' state.

        Args:
            changeset (str): Revision ID to monitor

        Returns:
            dict[str, Any]: Complete revision information including:
                - state: Current revision state
                - rev_id: Revision identifier
                - parent_revision_id: Parent revision reference
                - last-apply: Apply operation details

        Raises:
            RuntimeError: If the revision doesn't reach applied state within the timeout period
            NVUEAPIError: If API requests fail during polling

        Example:
            >>> revision_info = await service.wait_for_applied("7")
            >>> print(revision_info['state'])
            applied_and_saved
        """
        logger.info(
            f"[POLL] Starting status polling | changeset={changeset} | "
            f"max_retries={self.settings.retries} | interval={self.settings.poll_interval}s"
        )
        for i in range(self.settings.retries):
            resp = await self.config_history(changeset)
            state = resp.get("state")
            logger.info(
                f"[POLL] Checking status | attempt={i + 1}/{self.settings.retries} | "
                f"current_state={state} | target_state={RevisionState.APPLIED_AND_SAVED.value}"
            )

            if state == RevisionState.APPLIED_AND_SAVED.value:
                logger.info(
                    f"[POLL] Configuration successfully applied and saved | changeset={changeset} | final_state={state}"
                )
                return resp

            logger.debug(f"[POLL] Waiting {self.settings.poll_interval}s before next check...")
            await asyncio.sleep(self.settings.poll_interval)

        logger.error(
            f"[POLL] Deployment timeout | changeset={changeset} | "
            f"final_state={state} | elapsed_time={self.settings.retries * self.settings.poll_interval}s"
        )
        raise RuntimeError(
            f"Deployment timeout: Configuration not fully applied within "
            f"{self.settings.retries * self.settings.poll_interval} seconds. Current state: {state}"
        )

    async def config_replace(
        self,
        path: str,
        payload: dict[str, Any],
        options: ApplyOptions | None = None,
    ) -> RevisionInfo:
        """
        Replace entire configuration at a path with new configuration (full deployment workflow).

        This is a complete workflow that:
        1. Creates a new revision
        2. Deletes existing configuration at the path
        3. Applies new configuration
        4. Commits the changes
        5. Waits for application (unless using confirm timeout)

        Equivalent to 'nv config replace'. Use this when you want to completely
        replace all configuration under a specific path.

        Args:
            path (str): NVUE API path to replace (e.g., '/interface/swp1', '/router/bgp')
            payload (dict[str, Any]): Complete new configuration data for the path
            options (ApplyOptions | None): Apply operation options including:
                - message: Commit message for tracking
                - state_controls: Fine-grained control (confirm timeout, skip health check, etc.)
                - wait_for_applied: Whether to wait for completion (auto-disabled with confirm)

        Returns:
            RevisionInfo: Complete revision information with:
                - .rev_id: The revision ID (auto-extracted)
                - .parent_rev_id: Parent revision ID (auto-extracted)
                - .state: Final revision state
                - Plus all NVUE API response fields

        Raises:
            NVUEAPIError: If API operations fail or configuration is invalid
            RuntimeError: If deployment times out

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigreplace

        Examples:
            >>> # Basic replace
            >>> result = await service.config_replace(
            ...     path="/interface/swp1",
            ...     payload={"type": "swp", "link": {"state": {"up": {}}}}
            ... )

            >>> # Replace with confirmation required (safe mode)
            >>> result = await service.config_replace(
            ...     path="/router/bgp",
            ...     payload={...},
            ...     options=ApplyOptions.with_confirm(
            ...         timeout=300,
            ...         message="Critical BGP change - requires confirmation"
            ...     )
            ... )
        """
        logger.info(f"[REPLACE] ═══ Starting config replace workflow ═══ | path={path}")
        changeset = await self.create_revision()
        logger.debug(f"[REPLACE] Phase 1/4: Revision created | changeset={changeset}")
        try:
            logger.debug("[REPLACE] Phase 2/4: Deleting existing configuration")
            await self.delete_config(path, changeset)
            logger.debug("[REPLACE] Phase 3/4: Applying new configuration")
            await self.patch_config(path, payload, changeset)

            # Use provided options or create default with message
            if options is None:
                options = ApplyOptions(message=f"Replace configuration at {path}")
            elif options.message is None:
                # Preserve other options but add default message
                options.message = f"Replace configuration at {path}"

            logger.debug("[REPLACE] Phase 4/4: Committing changes")
            await self.apply_changeset(changeset, options=options)

            # Only wait for applied if options allow it
            if options.should_wait_for_applied():
                logger.info(f"[REPLACE] Waiting for full application and persistence | changeset={changeset}")
                revision_info = await self.wait_for_applied(changeset)
                logger.info(f"[REPLACE] Config replace completed successfully | path={path} | changeset={changeset}")
            else:
                logger.info(
                    f"[REPLACE] Skipping wait (manual confirmation required or disabled) | changeset={changeset}"
                )
                revision_info = await self.config_history(changeset)
                logger.info(f"[REPLACE] Config replace initiated (pending confirmation) | path={path}")

            # Ensure changeset ID is included in the response
            revision_info["changeset_id"] = changeset
            return RevisionInfo(**revision_info)
        except Exception as e:
            logger.error(
                f"[REPLACE] ✗ Config replace failed | path={path} | changeset={changeset} | error={type(e).__name__}: {str(e)}"
            )
            raise

    async def config_merge(
        self,
        path: str,
        payload: dict[str, Any],
        options: ApplyOptions | None = None,
    ) -> RevisionInfo:
        """
        Merge configuration changes without deleting existing configuration (incremental update).

        This is a complete workflow that:
        1. Creates a new revision
        2. Merges configuration changes at the path
        3. Verifies actual changes exist (detaches if no changes)
        4. Commits the changes
        5. Waits for application (unless using confirm timeout)

        Unlike config_replace, this preserves existing configuration and only updates
        or adds the specified settings. Use this for incremental configuration changes.

        Args:
            path (str): NVUE API path to merge (e.g., '/interface/swp1', '/system')
            payload (dict[str, Any]): Configuration changes to merge (partial configuration)
            options (ApplyOptions | None): Apply operation options including:
                - message: Commit message for tracking
                - state_controls: Fine-grained control (confirm timeout, skip health check, etc.)
                - wait_for_applied: Whether to wait for completion

        Returns:
            dict[str, Any]: Complete revision information including:
                - _changeset: The revision ID used
                - state: Final revision state
                - parent_revision_id: Parent revision reference
                - last-apply: Apply operation details

        Raises:
            ConfigurationError: If no actual configuration changes are detected
            NVUEAPIError: If API operations fail or configuration is invalid
            RuntimeError: If deployment times out

        Examples:
            >>> # Enable an interface without affecting other settings
            >>> result = await service.config_merge(
            ...     path="/interface/swp1",
            ...     payload={"link": {"state": {"up": {}}}}
            ... )

            >>> # Update BGP ASN while preserving other BGP config
            >>> result = await service.config_merge(
            ...     path="/router/bgp",
            ...     payload={"autonomous-system": 65001},
            ...     options=ApplyOptions(message="Update BGP ASN")
            ... )
        """
        logger.info(f"[MERGE] ═══ Starting config merge workflow ═══ | path={path}")
        changeset = await self.create_revision()
        logger.debug(f"[MERGE] Phase 1/4: Revision created | changeset={changeset}")
        try:
            logger.debug("[MERGE] Phase 2/4: Merging configuration")
            await self.patch_config(path, payload, changeset)

            logger.info(f"[MERGE] Phase 3/4: Verifying configuration changes | changeset={changeset}")

            diff_result = await self.get_revision_diff(
                resource="/", base_changeset=SpecialRevisionName.APPLIED.value, target_changeset=changeset
            )

            logger.debug(f"[MERGE] Diff analysis: {len(diff_result) if diff_result else 0} changes detected")

            if not diff_result or len(diff_result) == 0:
                logger.warning(f"[MERGE] No changes detected | path={path} | changeset={changeset} | action=detaching")
                await self.detach_config(changeset)
                raise ConfigurationError("No configuration changes detected. Merge operation skipped.")

            # Use provided options or create default with message
            if options is None:
                options = ApplyOptions(message=f"Merge configuration at {path}")
            elif options.message is None:
                options.message = f"Merge configuration at {path}"

            logger.debug(f"[MERGE] Apply options: {options}")

            logger.debug("[MERGE] Phase 4/4: Committing changes")
            await self.apply_changeset(changeset, options=options)

            # Only wait for applied if options allow it
            if options.should_wait_for_applied():
                logger.info(f"[MERGE] Waiting for full application and persistence | changeset={changeset}")
                revision_info = await self.wait_for_applied(changeset)
                logger.info(f"[MERGE] ✓ Config merge completed successfully | path={path} | changeset={changeset}")
            else:
                logger.info(
                    f"[MERGE] ⚠️  Skipping wait (manual confirmation required or disabled) | changeset={changeset}"
                )
                revision_info = await self.config_history(changeset)
                logger.info(f"[MERGE] Config merge initiated (pending confirmation) | path={path}")

            # Ensure changeset ID is included in the response
            revision_info["changeset_id"] = changeset
            add_span_attributes(
                event_name="merge",
                revision=changeset,
            )
            return RevisionInfo(**revision_info)
        except Exception as e:
            logger.error(
                f"[MERGE] ✗ Config merge failed | path={path} | changeset={changeset} | error={type(e).__name__}: {str(e)}"
            )
            raise
    @trace_span_attributes(
        event_name="rollback", 
        revision="changeset"
    )
    async def config_rollback(
        self,
        changeset: str,
        options: ApplyOptions | None = None,
    ) -> RevisionInfo:
        """
        Rollback configuration to a previous revision state.

        This operation reverts the configuration to a specific historical revision.
        The target revision must exist in the revision history.

        Args:
            changeset (str): The revision ID to rollback to (from config history)
            options (ApplyOptions | None): Apply operation options including:
                - message: Commit message (defaults to "Rollback to revision {changeset}")
                - state_controls: Fine-grained control (confirm timeout, etc.)
                - wait_for_applied: Whether to wait for rollback completion

        Returns:
            dict[str, Any]: Complete revision information including:
                - _changeset: The revision ID (same as input changeset)
                - state: Final revision state
                - parent_revision_id: Parent revision reference
                - last-apply: Apply operation details

        Raises:
            NVUEAPIError: If the changeset doesn't exist or rollback fails
            RuntimeError: If rollback times out

        Examples:
            >>> # Simple rollback
            >>> result = await service.config_rollback("5")

            >>> # Rollback with confirmation (safety mechanism)
            >>> result = await service.config_rollback(
            ...     changeset="5",
            ...     options=ApplyOptions.with_confirm(
            ...         timeout=300,
            ...         message="Emergency rollback - requires confirmation"
            ...     )
            ... )
        """
        logger.info(f"[ROLLBACK] ═══ Starting rollback workflow ═══ | target_changeset={changeset}")
        try:
            # Use provided options or create default with message
            if options is None:
                options = ApplyOptions(message=f"Rollback to revision {changeset}")
                logger.debug("[ROLLBACK] Using default options with auto-generated message")
            elif options.message is None:
                options.message = f"Rollback to revision {changeset}"

            # Apply the rollback
            logger.debug("[ROLLBACK] Applying rollback to target revision")
            await self.apply_changeset(changeset, options=options)

            # Get revision info (either wait for applied or get current status)
            if options.should_wait_for_applied():
                logger.info(f"[ROLLBACK] Waiting for rollback completion | target={changeset}")
                revision_info = await self.wait_for_applied(changeset)
                logger.info(f"[ROLLBACK] ✓ Rollback completed successfully | target_changeset={changeset}")
            else:
                logger.info(
                    f"[ROLLBACK] ⚠️  Skipping wait (manual confirmation required or disabled) | target={changeset}"
                )
                revision_info = await self.config_history(changeset)
                logger.info(f"[ROLLBACK] Rollback initiated (pending confirmation) | target={changeset}")
            # Ensure changeset ID is included in the response
            if not revision_info.get("last-apply", {}).get("rev_id"):
                revision_info["changeset_id"] = changeset
            return RevisionInfo(**revision_info)
        except Exception as e:
            logger.error(
                f"[ROLLBACK] ✗ Rollback failed | target_changeset={changeset} | error={type(e).__name__}: {str(e)}"
            )
            raise

    async def get_config(self, path: str) -> dict[str, Any]:
        """
        Retrieve current applied configuration at a specific path.

        This method fetches the active configuration (not pending changes)
        from the specified NVUE API path.

        Args:
            path (str): NVUE API path to query (e.g., 'interface/swp1', 'system', 'router/bgp')
                       Path will be automatically normalized to start with '/'

        Returns:
            dict[str, Any]: Configuration data at the specified path

        Raises:
            NVUEAPIError: If the path doesn't exist or API request fails

        Examples:
            >>> # Get specific interface config
            >>> config = await service.get_config("interface/swp1")
            >>> print(config['type'])
            swp

            >>> # Get all interface configurations
            >>> interfaces = await service.get_config("interface")
        """
        clean_path = f"/{path.lstrip('/')}"
        resp = await self.client.request("GET", clean_path)
        return resp.json()

    async def get_revision_diff(self, resource: str, base_changeset: str, target_changeset: str) -> dict[str, Any]:
        """
        Get configuration differences between two revisions.

        This method compares configurations between two revision states and returns
        the differences. Equivalent to 'nv config diff' command.

        Args:
            resource (str): Configuration path to compare (e.g., '/', '/interface', '/router/bgp')
            base_changeset (str): Base revision for comparison (e.g., 'applied', 'startup', or revision ID)
            target_changeset (str): Target revision to compare against (e.g., 'pending', 'empty', or revision ID)

        Returns:
            dict[str, Any]: Dictionary containing the configuration differences.
                           Empty dict if no changes detected.

        Raises:
            NVUEAPIError: If either revision doesn't exist or API request fails

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigdiff

        Common Usage Patterns:
            - Compare pending vs applied: base='applied', target='pending'
            - Compare current vs empty: base='applied', target='empty'
            - Compare two revisions: base='5', target='7'
            - Preview changes: base='applied', target=<new_changeset>

        Examples:
            >>> # Check what changed in a pending revision
            >>> diff = await service.get_revision_diff(
            ...     resource="/",
            ...     base_changeset="applied",
            ...     target_changeset="7"
            ... )
            >>> if diff:
            ...     print(f"Changes detected: {len(diff)} items")

            >>> # Compare two historical revisions
            >>> diff = await service.get_revision_diff(
            ...     resource="/interface",
            ...     base_changeset="5",
            ...     target_changeset="7"
            ... )
        """
        logger.info(
            f"[DIFF] Retrieving configuration diff | resource={resource} | "
            f"base={base_changeset} | target={target_changeset}"
        )
        base_quoted = urllib.parse.quote(base_changeset, safe="")
        target_quoted = urllib.parse.quote(target_changeset, safe="")
        clean_resource = resource.strip("/")
        path = f"/{clean_resource}?rev={base_quoted}&diff={target_quoted}"

        resp = await self.client.request("GET", path)
        diff_data = resp.json()
        changes_count = len(diff_data) if diff_data else 0
        logger.info(f"[DIFF] Retrieved diff successfully | changes={changes_count}")
        return diff_data

    async def config_find(self, search_string: str) -> dict[str, Any]:
        """
        Search for configuration items matching a search string.

        This method performs a search across the applied configuration to find
        paths and values containing the specified search string.
        Equivalent to 'nv config find' command.

        Args:
            search_string (str): String to search for in configuration paths and values

        Returns:
            dict[str, Any]: Dictionary of matching configuration items.
                           Keys are configuration paths, values are the configuration data.

        Raises:
            NVUEAPIError: If API request fails

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigfind

        Examples:
            >>> # Find all interface-related configuration
            >>> results = await service.config_find("interface")
            >>> print(f"Found {len(results)} interface items")

            >>> # Search for BGP configuration
            >>> bgp_config = await service.config_find("bgp")

            >>> # Find specific interface
            >>> swp1_config = await service.config_find("swp1")
        """
        logger.info(f"[SEARCH] Searching configuration | query='{search_string}'")
        params = {"rev": SpecialRevisionName.APPLIED.value, "filled": False, "diff": "", "search-string": search_string}

        resp = await self.client.request("GET", "/", params=params)
        results = resp.json()
        results_count = len(results) if results else 0
        logger.info(f"[SEARCH] Search completed | query='{search_string}' | results={results_count}")
        return results

    async def config_history(self, changeset: str | None) -> dict[str, Any]:
        """
        Retrieve revision history or specific revision details.

        This method can either list all revisions or get detailed information about
        a specific revision. Equivalent to 'nv config history' command.

        For pending apply operations with confirm timeout, this shows the confirmation
        status and remaining time before automatic rollback.

        Args:
            changeset (str | None): Revision ID to query. Special values include:
                - None: Returns all revision history
                - 'applied': Current applied configuration
                - 'pending': Current pending configuration
                - 'startup': Startup configuration
                - '<number>': Specific revision ID (e.g., '7')

        Returns:
            dict[str, Any]: For specific changeset:
                - state: Revision state (pending, applied, applied_and_saved, etc.)
                - rev_id: Revision identifier
                - parent_revision_id: Parent revision reference
                - last-apply: Apply operation details
                - confirm-status: Confirmation details (if applicable)

            For all history (changeset=None):
                Dictionary with revision IDs as keys and their details as values

        Raises:
            NVUEAPIError: If the changeset doesn't exist or API request fails

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfighistory

        Examples:
            >>> # Get all revision history
            >>> all_revisions = await service.config_history(None)
            >>> print(f"Total revisions: {len(all_revisions)}")

            >>> # Get specific revision details
            >>> revision = await service.config_history("7")
            >>> print(f"State: {revision['state']}")

            >>> # Check applied configuration
            >>> applied = await service.config_history("applied")

            >>> # Check confirm status for pending apply
            >>> pending = await service.config_history("7")
            >>> if 'confirm-status' in pending:
            ...     print(f"Time remaining: {pending['confirm-status']['timeout']}s")
        """
        if not changeset:
            logger.info("[HISTORY] Retrieving all revision history")
            resp = await self.client.request("GET", "/revision")
            history = resp.json()
            revision_count = len(history) if isinstance(history, dict) else 0
            logger.info(f"[HISTORY] Retrieved history | total_revisions={revision_count}")
            return history

        quoted_id = urllib.parse.quote(changeset, safe="")
        logger.info(f"[HISTORY] Retrieving revision details | changeset={changeset}")
        path = f"/revision/{quoted_id}"

        resp = await self.client.request("GET", path)
        revision_data = resp.json()
        state = revision_data.get("state", "unknown")
        logger.info(f"[HISTORY] Retrieved revision | changeset={changeset} | state={state}")
        return revision_data

    async def _apply_state_with_confirmation(
        self,
        changeset: str,
        target_state: RevisionState,
        message: str | None = None,
    ) -> RevisionInfo:
        """
        Internal helper method to apply state changes with confirmation control.

        This method implements the Template Method pattern to eliminate code duplication
        across config_save, config_confirm, and config_reject methods.

        All parameters are automatically derived from the target_state:
        - RevisionState.APPLY -> "SAVE" log prefix, "confirm_yes" action
        - RevisionState.CONFIRM_YES -> "CONFIRM" log prefix, "confirm_yes" action
        - RevisionState.CONFIRM_NO -> "REJECT" log prefix, "confirm_no" action

        Args:
            changeset: The revision ID to operate on
            target_state: Target revision state to apply (APPLY, CONFIRM_YES, or CONFIRM_NO)
            message: Optional custom commit message (auto-generated if not provided)

        Returns:
            RevisionInfo: Revision information with auto-extracted fields

        Raises:
            NVUEAPIError: If the changeset doesn't exist or operation fails
        """
        # Derive log prefix, message template, and confirm action from target state
        state_mapping = {
            RevisionState.SAVE: ("SAVE", "confirm_yes"),
            RevisionState.CONFIRM_YES: ("CONFIRM", "confirm_yes"),
            RevisionState.CONFIRM_NO: ("REJECT", "confirm_no"),
        }

        log_prefix, confirm_action = state_mapping.get(target_state, ("UNKNOWN", "confirm_yes"))

        logger.info(f"[{log_prefix}] Initiating operation | changeset={changeset}")

        revision_info = await self.config_history(changeset)
        current_state = revision_info.get("state")

        if current_state in (
            RevisionState.APPLIED_AND_SAVED.value,
            RevisionState.CONFIRM_FAIL.value,
            RevisionState.DETACHED.value,
        ):
            logger.warning(
                f"[{log_prefix}] Changeset already in final state | changeset={changeset} | "
                f"state={current_state} | action=skip"
            )
            return RevisionInfo(**revision_info)

        logger.info(
            f"[{log_prefix}] Applying state change | changeset={changeset} | "
            f"current_state={current_state} | target_state={target_state.value}"
        )

        options = ApplyOptions()
        options.auto_prompt = AutoPrompt(ays="ays_yes", confirm=confirm_action)

        if message is not None:
            logger.info(f"[{log_prefix}] Overriding default message with custom message.")
        options.message = message

        if message:
            logger.debug(f"[{log_prefix}] Using custom message: '{message}'")

        options_payload = options.to_payload()

        apply_payload: dict[str, Any] = {"state": target_state.value}
        apply_payload.update(options_payload)

        logger.debug(f"[{log_prefix}] Payload prepared: {apply_payload}")

        quoted_id = urllib.parse.quote(changeset, safe="")
        resp = await self.client.request("PATCH", f"/revision/{quoted_id}", content=orjson.dumps(apply_payload))
        result = resp.json()

        logger.info(f"[{log_prefix}] Operation completed successfully | changeset={changeset}")
        return RevisionInfo(**result)
    @trace_span_attributes(
        event_name="apply",
        revision="changeset"
    )
    async def config_save(self, changeset: str, message: str | None = None) -> RevisionInfo:
        """
        Save applied configuration to startup (persist across reboots) or confirm pending apply.

        This method serves two purposes:
        1. Save applied configuration to startup configuration (nv config save)
        2. Confirm a pending apply operation that used confirm timeout

        The configuration will persist after device reboot only when saved to startup.

        For pending applies with confirm timeout, this method acts as the confirmation
        to prevent automatic rollback. Must be called within the timeout period.

        Note: This method automatically uses confirm_yes. For explicit confirm/reject control,
        use config_confirm() or config_reject() methods instead.

        Args:
            changeset (str): The revision ID to save or confirm
            message (str | None): Optional commit message for the save operation

        Returns:
            dict[str, Any]: Response from NVUE API containing:
                - state: Final revision state
                - rev_id: Revision identifier
                - Operation status and details

        Raises:
            NVUEAPIError: If the changeset doesn't exist or save operation fails

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigsave

        Examples:
            >>> # Simple save to startup
            >>> result = await service.config_save("7")

            >>> # Save with custom message
            >>> result = await service.config_save(
            ...     changeset="7",
            ...     message="Production BGP configuration - verified"
            ... )

            >>> # Confirm a pending apply (within timeout period)
            >>> # Step 1: Apply with confirm
            >>> await service.apply_changeset(
            ...     "7",
            ...     options=ApplyOptions.with_confirm(300, "Critical change")
            ... )
            >>> # Step 2: Test the change
            >>> # Step 3: Confirm within 300 seconds
            >>> await service.config_save("7", "Confirmed after testing")
        """
        return await self._apply_state_with_confirmation(
            changeset=changeset,
            target_state=RevisionState.SAVE,
            message=message,
        )
    @trace_span_attributes(
        event_name="confirm",
        revision="changeset"
    )
    async def config_confirm(self, changeset: str, message: str | None = None) -> RevisionInfo:
        """
        Confirm a pending configuration that was applied with confirm timeout.

        This method explicitly confirms a configuration change that is waiting for
        user confirmation. Use this when you've applied a configuration with a confirm
        timeout and want to permanently apply the changes.

        The changeset must be in a state waiting for confirmation (typically 'applied'
        state with an active confirm timer).

        Args:
            changeset (str): The revision ID to confirm
            message (str | None): Optional commit message for the confirmation

        Returns:
            dict[str, Any]: Response from NVUE API containing:
                - state: Final revision state (should be 'applied_and_saved')
                - rev_id: Revision identifier
                - Operation status and details

        Raises:
            NVUEAPIError: If the changeset doesn't exist or confirm operation fails

        Examples:
            >>> # Apply with confirm timeout
            >>> await service.config_merge(
            ...     path="/interface/swp1",
            ...     payload={"link": {"state": {"up": {}}}},
            ...     options=ApplyOptions.with_confirm(300, "Testing interface change")
            ... )
            >>> # Test the configuration...
            >>> # Confirm the change within timeout
            >>> result = await service.config_confirm(
            ...     changeset="7",
            ...     message="Confirmed: interface working correctly"
            ... )
        """
        return await self._apply_state_with_confirmation(
            changeset=changeset,
            target_state=RevisionState.CONFIRM_YES,
            message=message,
        )
    @trace_span_attributes(
        event_name="reject",
        revision="changeset"
    )
    async def config_reject(self, changeset: str, message: str | None = None) -> RevisionInfo:
        """
        Reject a pending configuration that was applied with confirm timeout.

        This method explicitly rejects a configuration change that is waiting for
        user confirmation, triggering an immediate rollback. Use this when you've
        applied a configuration with a confirm timeout and want to rollback the changes.

        The changeset must be in a state waiting for confirmation (typically 'applied'
        state with an active confirm timer).

        Args:
            changeset (str): The revision ID to reject
            message (str | None): Optional commit message for the rejection/rollback

        Returns:
            dict[str, Any]: Response from NVUE API containing:
                - state: Final revision state (should be 'confirm_fail')
                - rev_id: Revision identifier
                - Operation status and details

        Raises:
            NVUEAPIError: If the changeset doesn't exist or reject operation fails

        Examples:
            >>> # Apply with confirm timeout
            >>> await service.config_merge(
            ...     path="/router/bgp",
            ...     payload={"autonomous-system": 65001},
            ...     options=ApplyOptions.with_confirm(300, "Testing BGP change")
            ... )
            >>> # Test reveals issues...
            >>> # Reject and rollback immediately
            >>> result = await service.config_reject(
            ...     changeset="7",
            ...     message="Rejected: BGP routing issues detected"
            ... )
        """
        return await self._apply_state_with_confirmation(
            changeset=changeset,
            target_state=RevisionState.CONFIRM_NO,
            message=message,
        )

    async def config_show(self) -> dict[str, Any]:
        """
        Retrieve the complete currently applied configuration.

        This method returns the entire active configuration across all subsystems
        (interfaces, routing, system settings, etc.). Equivalent to 'nv config show'.

        The configuration returned is the currently active (applied) configuration,
        not including any pending changes.

        Returns:
            dict[str, Any]: Complete configuration data structure containing all
                           system, network, interface, and routing configurations

        Raises:
            NVUEAPIError: If API request fails

        Reference:
            https://docs.nvidia.com/networking/display/nvidianvosusermanualforinfinibandswitchesv25027002/configuration-management-commands#src-4734125798_ConfigurationManagementCommands-nvconfigshow

        Note:
            The returned data can be large. Consider using get_config() with a specific
            path if you only need configuration for a particular subsystem.

        Examples:
            >>> # Get complete configuration
            >>> full_config = await service.config_show()
            >>> print(full_config.keys())
            dict_keys(['interface', 'router', 'system', 'service', ...])

            >>> # Access specific subsystem from full config
            >>> interfaces = full_config.get('interface', {})
            >>> bgp_config = full_config.get('router', {}).get('bgp', {})
        """
        logger.info("[SHOW] Retrieving current applied configuration")
        query_params = {"rev": SpecialRevisionName.APPLIED.value, "filled": False}
        resp = await self.client.request("GET", "/", params=query_params)
        config = resp.json()
        config_size = len(str(config))
        logger.info(f"[SHOW] Retrieved current config | size={config_size} bytes")
        return config
