from enum import StrEnum
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import computed_field


class RevisionState(StrEnum):
    """
    NVUE Revision states.
    Corresponds to the 'state' field in revision operations.
    """

    APPLY = "apply"
    APPLIED = "applied"
    APPLIED_AND_SAVED = "applied_and_saved"
    PENDING = "pending"
    EMPTY = "empty"
    CONFIRM_FAIL = "confirm_fail"
    PREVIOUS = "previous"
    DETACHED = "detached"
    CONFIRM = "confirm"
    CONFIRM_YES = "confirm_yes"
    CONFIRM_NO = "confirm_no"
    SAVE = "save"


class SpecialRevisionName(StrEnum):
    """
    Special revision names used for querying configurations.
    These are predefined revision identifiers in NVUE API.
    """

    APPLIED = "applied"
    PENDING = "pending"
    STARTUP = "startup"


class StateControls(BaseModel):
    """
    Control which states to run during Apply FSM (Finite State Machine).
    Corresponds to NVUE API 'state-controls' object.
    """

    apply_type: Literal["CLI", "API", "startup-apply", "Internal", "Unknown"] | None = Field(
        default="API", description="Apply type indicator"
    )
    reload: Literal["skip"] | None = Field(default=None, description="Skip reload/restart state")
    check_health: Literal["skip"] | None = Field(default=None, description="Skip health check state")
    verifying: Literal["skip", "skinny_startup"] | None = Field(
        default=None, description="Control verifying state (skip or call skinny-startup event)"
    )
    readying: Literal["skip"] | None = Field(default=None, description="Skip readying state")
    confirm: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Wait N seconds for user confirmation before finishing. "
            "If not confirmed within timeout, automatically rollback. "
            "0 = no confirmation required."
        ),
    )


class AutoPrompt(BaseModel):
    """
    Define automatic answers to prompts ahead of time.
    Corresponds to NVUE API 'auto-prompt' object.
    """

    ays: Literal["ays_yes", "ays_no"] | None = Field(
        default="ays_yes", description="Automatic answer for 'Are you sure?' prompt"
    )
    ignore_fail: Literal["ignore_fail_yes", "ignore_fail_no"] | None = Field(
        default=None, description="Automatic answer for 'Ignore?' prompt"
    )
    confirm: Literal["confirm_yes", "confirm_no"] | None = Field(
        default=None, description="Automatic answer for 'Confirm?' prompt"
    )


class ApplyOptions(BaseModel):
    """
    Configuration options for applying a changeset.
    Encapsulates all optional parameters for apply operations.
    """

    message: str | None = Field(default=None, description="Commit message for this apply operation")
    auto_prompt: AutoPrompt | None = Field(
        default=None, description="Automatic prompt responses. Defaults to {'ays': 'ays_yes'}"
    )
    state_controls: StateControls | None = Field(
        default=None, description="Fine-grained control over apply state machine"
    )
    wait_for_applied: bool = Field(
        default=True,
        description=(
            "Whether to wait for configuration to be fully applied and saved. "
            "Set to False when using confirm timeout (requires manual confirmation). "
            "Automatically set to False when state_controls.confirm > 0."
        ),
    )

    # Convenience helpers for common scenarios
    @classmethod
    def with_confirm(
        cls,
        timeout: int,
        message: str | None = None,
        wait_for_applied: bool = False,  # 預設不等待，因為需要手動確認
    ) -> "ApplyOptions":
        """
        Create options for confirmed apply (auto-rollback if not confirmed).

        Args:
            timeout: Seconds to wait for confirmation before auto-rollback
            message: Optional commit message
            wait_for_applied: Whether to wait for applied state (default: False, requires manual confirmation)
        """
        return cls(message=message, state_controls=StateControls(confirm=timeout), wait_for_applied=wait_for_applied)

    @classmethod
    def quick_apply(cls, message: str | None = None, skip_health_check: bool = False) -> "ApplyOptions":
        """Create options for quick apply (skip some checks)."""
        state_controls = StateControls(check_health="skip" if skip_health_check else None)
        return cls(message=message, state_controls=state_controls)

    def should_wait_for_applied(self) -> bool:
        """
        Determine if we should wait for applied state.
        Automatically returns False if confirm timeout is set (requires manual confirmation).
        """
        # If user explicitly set wait_for_applied to False, respect it
        if not self.wait_for_applied:
            return False

        # If confirm timeout is set, don't wait (requires manual confirmation)
        state_controls_instance = self.state_controls
        if state_controls_instance is not None:
            confirm_value = getattr(state_controls_instance, "confirm", None)  # pyright: ignore
            if confirm_value:
                return False

        return True

    def to_payload(self) -> dict[str, Any]:
        """Convert to NVUE API payload format."""
        payload: dict[str, Any] = {}

        if self.message:
            payload["message"] = self.message

        # Handle auto_prompt
        if self.auto_prompt is not None:
            # Convert Pydantic model to dict and transform keys
            auto_prompt_data = dict(self.auto_prompt)  # pyright: ignore
            payload["auto-prompt"] = {k.replace("_", "-"): v for k, v in auto_prompt_data.items() if v is not None}
        else:
            # Default auto-prompt
            payload["auto-prompt"] = {"ays": "ays_yes"}

        # Handle state_controls
        if self.state_controls is not None:
            # Convert Pydantic model to dict and transform keys
            controls_data = dict(self.state_controls)  # pyright: ignore
            controls_filtered = {k.replace("_", "-"): v for k, v in controls_data.items() if v is not None}
            if controls_filtered:
                payload["state-controls"] = controls_filtered

        return payload


class ConfigApplyRequest(BaseModel):
    """Define the request structure for applying configuration"""

    path: str = Field(default="/", description="NVUE API target path")
    payload: dict[str, Any] = Field(..., description="JSON configuration content to apply")

    # Option 1: Use ApplyOptions object (recommended for complex scenarios)
    options: ApplyOptions | None = Field(
        default=None, description="Apply operation options (message, confirm, state controls)"
    )


class RollbackRequest(BaseModel):
    """Request body for rollback operation"""

    message: str | None = Field(default=None, description="Optional commit message for the rollback operation")
    confirm_timeout: int | None = Field(
        default=None, ge=0, description="Require confirmation within N seconds or auto-rollback"
    )

    def to_apply_options(self) -> ApplyOptions:
        """Convert to ApplyOptions for service layer"""
        state_controls = StateControls(confirm=self.confirm_timeout) if self.confirm_timeout else None
        return ApplyOptions(message=self.message, state_controls=state_controls)


class ConfirmRequest(BaseModel):
    """Request body for confirm/reject operations"""

    message: str | None = Field(default=None, description="Optional commit message for the confirm/reject operation")


class GenericResponse(BaseModel):
    """Unified API response format"""

    success: bool
    message: str
    revision: str | None = None
    parent_revision: str | None = None
    data: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Error response model"""

    detail: str
    status: int | None = None
    title: str | None = None
    type: str | None = None
    validation: dict[str, Any] | None = None


class ConfigResponse(BaseModel):
    """Configuration query response model"""

    path: str | None = Field(default=None, description="NVUE API path")
    data: dict[str, Any]


class RevisionInfo(BaseModel):
    """
    Revision information returned from NVUE API operations.

    This model wraps the raw NVUE revision response and provides convenient
    computed properties for commonly accessed fields, eliminating manual
    dictionary navigation and field extraction.

    Usage:
        >>> revision_info = RevisionInfo(**raw_response)
        >>> print(revision_info.rev_id)  # Auto-extracts from changeset_id or last-apply
        >>> print(revision_info.parent_rev_id)  # Auto-extracts from additional-data
        >>> data = revision_info.model_dump()  # Excludes internal changeset_id field
    """

    model_config = {
        "extra": "allow",  # Preserve all NVUE API fields
        "populate_by_name": True,  # Allow both snake_case and kebab-case
    }

    # Core fields
    state: str = Field(..., description="Current revision state")

    # Optional fields with alias mapping
    changeset_id: str | None = Field(default=None, exclude=True)  # Internal field for tracking, not serialized
    last_apply: dict[str, Any] | None = Field(default=None, alias="last-apply", exclude=True)
    additional_data: dict[str, Any] | None = Field(default=None, alias="additional-data", exclude=True)

    @computed_field
    @property
    def rev_id(self) -> str | None:
        """
        Revision ID extracted from either changeset_id or last-apply.rev_id.

        Returns:
            str | None: Revision identifier
        """
        return self.changeset_id or (self.last_apply or {}).get("rev_id")

    @computed_field
    @property
    def parent_rev_id(self) -> str | None:
        """
        Parent revision ID extracted from additional-data.

        Returns:
            str | None: Parent revision identifier
        """
        return (self.additional_data or {}).get("parent-revision-id")
