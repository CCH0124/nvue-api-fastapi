from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Response
from fastapi import status
from fastapi.responses import JSONResponse
from loguru import logger

from nvue_automation.config.settings import Settings
from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.core.exceptions import ConfigurationError
from nvue_automation.core.exceptions import NVUEAPIError
from nvue_automation.models.schemas import ApplyOptions
from nvue_automation.models.schemas import ConfigApplyRequest
from nvue_automation.models.schemas import ConfigResponse
from nvue_automation.models.schemas import ConfirmRequest
from nvue_automation.models.schemas import ErrorResponse
from nvue_automation.models.schemas import GenericResponse
from nvue_automation.models.schemas import RevisionState
from nvue_automation.models.schemas import RollbackRequest
from nvue_automation.services.nvue_service import AsyncNVUEService

router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])


async def get_nvue_service():
    """
    FastAPI dependency injection: Automatically create and close async connection pool.
    """
    settings = Settings()
    async with AsyncNVUEClient(settings) as client:
        yield AsyncNVUEService(client)


@router.put(
    "/deploy",
    tags=["Configuration"],
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Replace and Deploy Configuration",
    description="""
    Completely replace and deploy configuration at the specified path. This operation will:
    1. Create a new Revision
    2. Delete old configuration at the specified path
    3. Apply new configuration
    4. Commit changes
    5. Verify application status

    **Safety Features**:
    - `message`: Add a commit message for tracking changes
    - `confirm_timeout`: Require manual confirmation within N seconds, or auto-rollback (useful for critical changes)

    **Note**: This operation will delete all existing configuration under the path. Please confirm before using.
    """,
    responses={
        201: {"description": "Configuration successfully replaced and deployed", "model": GenericResponse},
        400: {"description": "Invalid request parameters or configuration format", "model": ErrorResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def replace_config_and_deploy(request: ConfigApplyRequest, service: AsyncNVUEService = Depends(get_nvue_service)):
    """
    One-click deployment: Create Revision -> Delete old config -> Apply new config -> Commit -> Verify status
    """
    logger.info(f"[API] PUT /config/deploy | path={request.path}")
    try:
        options = request.options
        logger.debug(f"[API] Replace request details | path={request.path} | has_options={options is not None}")
        revision_info = await service.config_replace(path=request.path, payload=request.payload, options=options)

        logger.info(f"[API] Replace deployed successfully | path={request.path} | revision={revision_info.rev_id}")
        return GenericResponse(
            success=True,
            message="Configuration deployed and verified successfully.",
            revision=revision_info.rev_id,
            parent_revision=revision_info.parent_rev_id,
            data=revision_info.model_dump(),
        )
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | path={request.path} | status={e.status_code} | detail={e.detail}")
        raise
    except Exception as e:
        logger.error(f"[API] Replace deployment failed | path={request.path} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to replace and deploy configuration: {str(e)}") from e


@router.patch(
    "/deploy",
    tags=["Configuration"],
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Merge and Deploy Configuration",
    description="""
    Merge and deploy configuration without deleting existing configuration under the path. This operation will:
    1. Create a new Revision
    2. Merge new configuration with existing configuration (incremental update)
    3. Commit changes
    4. Verify application status

    **Safety Features**:
    - `message`: Add a commit message for tracking changes
    - `confirm_timeout`: Require manual confirmation within N seconds, or auto-rollback (useful for critical changes)

    **Use Case**: Set or unset specific configuration items without affecting other configurations under the path.
    """,
    responses={
        201: {"description": "Configuration successfully merged and deployed", "model": GenericResponse},
        202: {"description": "No configuration changes detected. Merge operation skipped", "model": GenericResponse},
        400: {"description": "Invalid request parameters or configuration format", "model": ErrorResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def merge_config_and_deploy(request: ConfigApplyRequest, service: AsyncNVUEService = Depends(get_nvue_service)):
    """
    Merge configuration: Set or unset specific configuration items without deleting the entire path configuration.

    Args:
        request: Request body containing path and configuration payload
        service: NVUE service dependency injection

    Returns:
        GenericResponse: Contains deployment status, version information and detailed data

    Raises:
        NVUEAPIError: NVUE API related errors
        HTTPException: Other server errors
    """
    logger.info(f"[API] PATCH /config/deploy | path={request.path}")
    try:
        logger.debug(f"[API] Merge request details | path={request.path} | has_options={request.options is not None}")
        revision_info = await service.config_merge(path=request.path, payload=request.payload, options=request.options)

        logger.info(f"[API] Merge deployed successfully | path={request.path} | revision={revision_info.rev_id}")
        return GenericResponse(
            success=True,
            message="Configuration deployed and verified successfully.",
            revision=revision_info.rev_id,
            parent_revision=revision_info.parent_rev_id,
            data=revision_info.model_dump(exclude_computed_fields=True),
        )
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error | path={request.path} | status={e.status_code} | detail={e.detail}")
        raise
    except ConfigurationError as e:
        logger.info(f"[API] No changes detected | path={request.path} | reason={str(e)}")
        return Response(status_code=202)
    except Exception as e:
        logger.error(f"[API] Merge deployment failed | path={request.path} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to merge and deploy configuration: {str(e)}") from e


@router.post(
    "/{changeset}/rollback",
    tags=["Configuration"],
    response_model=GenericResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rollback Configuration",
    description="""
    Rollback to a specified historical configuration version.
    """,
    responses={
        201: {"description": "Successfully rolled back to specified version", "model": GenericResponse},
        400: {"description": "Specified revision ID does not exist or is invalid", "model": ErrorResponse},
        404: {"description": "Specified revision ID not found", "model": ErrorResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def rollback_config(
    changeset: str = Path(..., description="Revision ID (version number) to rollback to"),
    options: RollbackRequest | None = None,
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    """
    Rollback to a specified configuration revision.

    Args:
        changeset: The revision ID to rollback to
        options: Optional request body with message and confirm_timeout
        service: NVUE service dependency injection

    Returns:
        GenericResponse: Contains rollback status and revision information

    Raises:
        NVUEAPIError: NVUE API related errors
        HTTPException: Other server errors
    """
    logger.info(f"[API] POST /config/{changeset}/rollback")
    try:
        # Build options from request body (if provided)
        options = options.to_apply_options() if options else ApplyOptions()
        logger.debug(
            f"[API] Rollback request | target_changeset={changeset} | has_custom_options={options is not None}"
        )
        revision_info = await service.config_rollback(changeset=changeset, options=options)

        logger.info(f"[API] Rollback completed | target_changeset={changeset} | revision={revision_info.rev_id}")
        return GenericResponse(
            success=True,
            message=f"Configuration rolled back to revision '{changeset}' successfully.",
            revision=revision_info.rev_id,
            parent_revision=revision_info.parent_rev_id,
            data=revision_info.model_dump(exclude_computed_fields=True),
        )
    except NVUEAPIError as e:
        # Let exception propagate to global handler, return complete error info (including validation)
        logger.warning(f"[API] NVUE API error during rollback | changeset={changeset} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Rollback failed | changeset={changeset} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to rollback to changeset '{changeset}': {str(e)}") from e


@router.post(
    "/{changeset}/confirm",
    tags=["Configuration"],
    response_model=GenericResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm the apply, keeping it.",
    description="""
    Confirm a confirm_during configuration that was applied with a confirm timeout.

    This endpoint is used to explicitly confirm configuration changes that are waiting
    for user confirmation. When you apply a configuration with `confirm_timeout`, the
    system waits for manual confirmation within the specified timeout period. Use this
    endpoint to confirm the changes and prevent automatic rollback.

    **Workflow**:
    1. Deploy configuration with `confirm_timeout` (e.g., 300 seconds)
    2. Test the configuration changes
    3. Call this endpoint to confirm within the timeout period
    4. Configuration becomes permanently applied

    **Note**: If not confirmed within timeout, the configuration will automatically rollback.
    """,
    responses={
        200: {"description": "Configuration successfully confirmed", "model": GenericResponse},
        202: {
            "description": "Specified changeset is already in final state - no action needed",
            "model": GenericResponse,
        },
        400: {
            "description": "Specified changeset does not exist or is not in confirmable state",
            "model": ErrorResponse,
        },
        404: {"description": "Specified revision ID not found", "model": ErrorResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def confirm_config(
    changeset: str = Path(..., description="Changeset ID (revision number) to confirm"),
    request: ConfirmRequest | None = None,
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    """
    Confirm a confirm_during configuration changeset.

    Args:
        changeset: The changeset ID to confirm
        request: Optional request body with commit message
        service: NVUE service dependency injection

    Returns:
        GenericResponse: Contains confirmation status and revision information

    Raises:
        NVUEAPIError: NVUE API related errors
        HTTPException: Other server errors
    """
    logger.info(f"[API] POST /config/{changeset}/confirm")
    try:
        message = request.message if request else None
        logger.debug(f"[API] Confirm request | changeset={changeset} | has_message={message is not None}")

        revision_info = await service.config_confirm(changeset=changeset, message=message)

        if revision_info.state in (
            RevisionState.APPLIED_AND_SAVED.value,
            RevisionState.CONFIRM_FAIL.value,
            RevisionState.DETACHED.value,
        ):
            logger.info(
                f"[API] Changeset already in final state | changeset={changeset} | state={revision_info.state} | "
                f"status_code=202"
            )
            return JSONResponse(
                status_code=202,
                content=GenericResponse(
                    success=True,
                    message=f"Changeset '{changeset}' is already in '{revision_info.state}' state. No action taken.",
                    revision=changeset,
                    parent_revision=revision_info.parent_rev_id,
                    data=revision_info.model_dump(exclude_computed_fields=True),
                ).model_dump(),
            )

        logger.info(f"[API] Configuration confirmed | changeset={changeset} | state={revision_info.state}")
        return GenericResponse(
            success=True,
            message=f"Configuration changeset '{changeset}' confirmed successfully.",
            revision=changeset,
            parent_revision=revision_info.parent_rev_id,
            data=revision_info.model_dump(exclude_computed_fields=True),
        )
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error during confirm | changeset={changeset} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Confirm failed | changeset={changeset} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm changeset '{changeset}': {str(e)}") from e


@router.post(
    "/{changeset}/reject",
    tags=["Configuration"],
    response_model=GenericResponse,
    status_code=status.HTTP_200_OK,
    summary="Roll back the unconfirmed apply now.",
    description="""
    Reject a confirm_during configuration that was applied with a confirm error, triggering immediate rollback.

    This endpoint is used to explicitly reject configuration changes that are waiting
    for user confirmation. When you apply a configuration with `confirm_timeout`, you can
    use this endpoint to immediately rollback the changes without waiting for the timeout.

    **Workflow**:
    1. Deploy configuration with `confirm_timeout` (e.g., 300 seconds)
    2. Test the configuration changes
    3. If issues detected, call this endpoint to immediately rollback
    4. Configuration is rolled back to previous state

    **Use Case**: When testing reveals issues and you want to rollback immediately rather than
    waiting for automatic timeout rollback.
    """,
    responses={
        200: {"description": "Configuration successfully rejected and rolled back", "model": GenericResponse},
        202: {
            "description": "Specified changeset is already in final state - no action needed",
            "model": GenericResponse,
        },
        400: {
            "description": "Specified changeset does not exist or is not in rejectable state",
            "model": ErrorResponse,
        },
        404: {"description": "Specified revision ID not found", "model": ErrorResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def reject_config(
    changeset: str = Path(..., description="Changeset ID (revision number) to reject"),
    request: ConfirmRequest | None = None,
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    """
    Reject a pending configuration changeset, triggering rollback.

    Args:
        changeset: The changeset ID to reject
        request: Optional request body with commit message
        service: NVUE service dependency injection

    Returns:
        GenericResponse: Contains rejection/rollback status and revision information

    Raises:
        NVUEAPIError: NVUE API related errors
        HTTPException: Other server errors
    """
    logger.info(f"[API] POST /config/{changeset}/reject")
    try:
        message = request.message if request else None
        logger.debug(f"[API] Reject request | changeset={changeset} | has_message={message is not None}")

        revision_info = await service.config_reject(changeset=changeset, message=message)

        if revision_info.state in (
            RevisionState.APPLIED_AND_SAVED.value,
            RevisionState.CONFIRM_FAIL.value,
            RevisionState.DETACHED.value,
        ):
            logger.info(
                f"[API] Changeset already in final state | changeset={changeset} | state={revision_info.state} | "
                f"status_code=202"
            )
            return JSONResponse(
                status_code=202,
                content=GenericResponse(
                    success=True,
                    message=f"Changeset '{changeset}' is already in '{revision_info.state}' state. No action taken.",
                    revision=changeset,
                    parent_revision=revision_info.parent_rev_id,
                    data=revision_info.model_dump(exclude_computed_fields=True),
                ).model_dump(),
            )

        logger.warning(f"[API] Configuration rejected | changeset={changeset} | state={revision_info.state}")
        return GenericResponse(
            success=True,
            message=f"Configuration changeset '{changeset}' rejected and rolled back successfully.",
            revision=changeset,
            parent_revision=revision_info.parent_rev_id,
            data=revision_info.model_dump(exclude_computed_fields=True),
        )
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error during reject | changeset={changeset} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Reject failed | changeset={changeset} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reject changeset '{changeset}': {str(e)}") from e


@router.post(
    "/{changeset}/apply",
    tags=["Configuration"],
    response_model=GenericResponse,
    summary="Apply Configuration Changeset",
    description="""
    Apply a pending configuration changeset to become the applied configuration.

    This endpoint applies the specified pending revision, making it the active configuration.
    Equivalent to the `nv config apply` command.

    **Use Case**: Apply a previously created revision that is in pending state.

    **Response Codes**:
    - 201: Configuration successfully applied and saved
    - 202: Configuration already in final state (applied_and_saved, confirm_fail, or detached) - no action taken
    """,
    responses={
        201: {"description": "Configuration changeset successfully applied", "model": GenericResponse},
        202: {"description": "Configuration already in final state - no action needed", "model": GenericResponse},
        400: {
            "description": "Specified changeset ID does not exist or is not in pending state",
            "model": ErrorResponse,
        },
        404: {"description": "Specified revision ID not found", "model": ErrorResponse},
        500: {"description": "Internal server error or NVUE API error", "model": ErrorResponse},
    },
)
async def apply_and_save_changeset(
    changeset: str = Path(..., description="Changeset ID (revision number) to apply"),
    request: ConfirmRequest | None = None,
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    """
    Apply a pending configuration changeset.

    Args:
        changeset: The changeset ID to apply
        service: NVUE service dependency injection

    Returns:
        GenericResponse: Contains application status and revision information

    Response Status:
        - 201: Configuration successfully applied
        - 202: Configuration already in final state (no action taken)

    Raises:
        NVUEAPIError: NVUE API related errors
        HTTPException: Other server errors
    """
    logger.info(f"[API] POST /config/{changeset}/apply")
    try:
        logger.debug(f"[API] Apply/save changeset request | changeset={changeset}")
        apply_result = await service.config_save(changeset=changeset, message=request.message if request else None)

        # Check if configuration is already in a final state
        if apply_result.state in (
            RevisionState.APPLIED_AND_SAVED.value,
            RevisionState.CONFIRM_FAIL.value,
            RevisionState.DETACHED.value,
        ):
            logger.info(
                f"[API] Changeset already in final state | changeset={changeset} | state={apply_result.state} | "
                f"status_code=202"
            )
            return JSONResponse(
                status_code=202,
                content=GenericResponse(
                    success=True,
                    message=f"Changeset '{changeset}' is already in '{apply_result.state}' state. No action taken.",
                    revision=changeset,
                    parent_revision=apply_result.parent_rev_id,
                    data=apply_result.model_dump(exclude_computed_fields=True),
                ).model_dump(),
            )

        logger.info(f"[API] Changeset applied and saved | changeset={changeset} | state={apply_result.state}")
        return GenericResponse(
            success=True,
            message=f"Changeset '{changeset}' applied successfully.",
            revision=changeset,
            parent_revision=apply_result.parent_rev_id,
            data=apply_result.model_dump(exclude_computed_fields=True),
        )
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error during apply | changeset={changeset} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Apply changeset failed | changeset={changeset} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to apply changeset '{changeset}': {str(e)}") from e


@router.get(
    "/revisions",
    tags=["Configuration"],
    response_model=ConfigResponse,
    summary="Get Configuration History",
    description="""
    Get configuration history. Optionally specify a specific revision ID to query the configuration content of that version.

    - **Without parameters**: Returns a list of all historical versions
    - **With changeset parameter**: Returns detailed configuration content of the specified version
    """,
    responses={
        200: {"description": "Successfully retrieved configuration history", "model": ConfigResponse},
        400: {"description": "Specified revision ID does not exist", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_config_history(
    changeset: str = Query(None, description="Optional Revision ID for querying a specific version's configuration"),
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    logger.info(f"[API] GET /config/revisions | changeset={changeset or 'all'}")
    try:
        resp = await service.config_history(changeset)
        logger.debug(f"[API] Retrieved config history | changeset={changeset or 'all'}")
        return ConfigResponse(path=f"/revision/{changeset}", data=resp)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error retrieving history | changeset={changeset} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to retrieve history | changeset={changeset} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Could not retrieve history: {str(e)}") from e


@router.get(
    "/find",
    tags=["Configuration"],
    response_model=ConfigResponse,
    summary="Search Configuration",
    description="""
    Search configuration items by keyword. Supports fuzzy search of configuration paths and values.
    **Use Cases**:
    - Find configuration for specific interfaces or features
    - Search for configuration items containing specific values
    - Explore available configuration options
    """,
    responses={
        200: {"description": "Successfully returned search results", "model": ConfigResponse},
        400: {"description": "Search string cannot be empty", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def search_config(
    search_string: str = Query(
        ...,
        description="Search keyword for finding related configuration items",
        openapi_examples={
            "interface": {"summary": "Search for interface-related configuration", "value": "interface"},
            "bgp": {"summary": "Search for BGP routing configuration", "value": "bgp"},
            "eth0": {"summary": "Search for configuration items containing specific string", "value": "eth0"},
        },
    ),
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    """
    Find configuration: Search for configuration items based on the provided search string.
    """
    logger.info(f"[API] GET /config/find | query='{search_string}'")
    try:
        resp = await service.config_find(search_string)
        logger.debug(f"[API] Search completed | query='{search_string}' | results={len(resp) if resp else 0}")
        return ConfigResponse(data=resp)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error during search | query='{search_string}' | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Search failed | query='{search_string}' | error={type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search configuration for '{search_string}': {str(e)}"
        ) from e


@router.get(
    "/",
    tags=["Configuration"],
    response_model=ConfigResponse,
    summary="Get All Current Configuration",
    description="""
    Get the complete current active configuration in JSON format.
    **Corresponding Command**: `nv config show`
    **Returns**: Complete configuration information for all systems, networks, interfaces, etc.
    **Note**: The returned data may be large, it's recommended to use specific path queries to get partial configuration.
    """,
    responses={
        200: {"description": "Successfully returned complete current configuration", "model": ConfigResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_current_config(service: AsyncNVUEService = Depends(get_nvue_service)):
    """
    Display the complete current applied configuration (JSON format).
    """
    logger.info("[API] GET /config")
    try:
        resp = await service.config_show()
        return ConfigResponse(path="/", data=resp)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error retrieving config | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to retrieve current config | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current configuration: {str(e)}") from e


@router.get(
    "/diff/{resource:path}",
    tags=["Configuration"],
    response_model=ConfigResponse,
    summary="Get Configuration Diff",
    description="""
    Compare differences between two configuration versions.

    **Parameter Description**:
    - `resource`: Configuration path to compare (e.g., `/interface`, `/system`)
    - `base_changeset`: Base version (default: `applied` - currently applied configuration)
    - `target_changeset`: Target version (default: `empty` - empty configuration)

    **Common Combinations**:
    - `applied` vs `empty`: View differences between current configuration and initial state
    - `applied` vs `[revision_id]`: View differences between current configuration and specific historical version
    - `[revision_id_1]` vs `[revision_id_2]`: Compare two historical versions
    """,
    responses={
        200: {"description": "Successfully returned configuration differences", "model": ConfigResponse},
        400: {"description": "Invalid revision ID", "model": ErrorResponse},
        404: {"description": "Specified path does not exist", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_config_diff(
    resource: str = Path(
        ...,
        description="NVUE API configuration path to compare",
        openapi_examples={
            "interfaces": {"summary": "Compare interface configurations", "value": "interface"},
            "specific_interface": {"summary": "Compare specific interface configuration", "value": "interface/swp1"},
            "system": {"summary": "Compare system configuration", "value": "system"},
            "bgp": {"summary": "Compare BGP routing configuration", "value": "router/bgp"},
        },
    ),
    base_changeset: str = Query("applied", description="Base version ID (defaults to currently applied configuration)"),
    target_changeset: str = Query("empty", description="Target version ID (defaults to empty configuration)"),
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    logger.info(f"[API] GET /config/diff/{resource} | base={base_changeset} | target={target_changeset}")
    try:
        resp = await service.get_revision_diff(resource, base_changeset, target_changeset)
        changes = len(resp) if resp else 0
        logger.debug(f"[API] Retrieved diff | resource={resource} | changes={changes}")
        return ConfigResponse(path=resource, data=resp)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error retrieving diff | resource={resource} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(
            f"[API] Failed to retrieve diff | resource={resource} | base={base_changeset} | "
            f"target={target_changeset} | error={type(e).__name__}: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve diff between '{base_changeset}' and '{target_changeset}': {str(e)}",
        ) from e


@router.get(
    "/{path:path}",
    tags=["Configuration"],
    response_model=ConfigResponse,
    summary="Get Configuration by Path",
    description="""
    Get current configuration information at the specified path.

    **Path Examples**:
    - `/interface` - Get all interface configurations
    - `/interface/swp1` - Get specific interface configuration
    - `/system` - Get system configuration
    - `/router/bgp` - Get BGP routing configuration

    **Tip**: Use the `/config/find` endpoint to find available configuration paths.
    """,
    responses={
        200: {"description": "Successfully returned configuration at specified path", "model": ConfigResponse},
        404: {"description": "Specified configuration path does not exist", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_config_by_path(
    path: str = Path(
        ...,
        description="NVUE API configuration path (e.g., interface/swp1, system)",
        openapi_examples={
            "interface": {"summary": "Get all interface configurations", "value": "interface"},
            "specific_interface": {"summary": "Get specific interface configuration", "value": "interface/swp1"},
            "system": {"summary": "Get system configuration", "value": "system"},
            "bgp": {"summary": "Get BGP routing configuration", "value": "router/bgp"},
        },
    ),
    service: AsyncNVUEService = Depends(get_nvue_service),
):
    """
    Get current configuration at the specified path.
    """
    logger.info(f"[API] GET /config/{path}")
    try:
        resp = await service.get_config(path)
        logger.debug(f"[API] Retrieved config | path={path}")
        return ConfigResponse(path=path, data=resp)
    except NVUEAPIError as e:
        logger.warning(f"[API] NVUE API error retrieving config | path={path} | status={e.status_code}")
        raise
    except Exception as e:
        logger.error(f"[API] Failed to retrieve config | path={path} | error={type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Configuration not found at path '{path}': {str(e)}") from e
