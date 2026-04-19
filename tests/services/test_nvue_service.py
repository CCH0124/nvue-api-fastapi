"""
Unit tests for AsyncNVUEService.

Tests the NVUE service functionality including:
- Revision management (create, detach)
- Configuration operations (patch, delete, merge, replace)
- Apply operations with various options
- Rollback and history management
- Configuration queries (get, diff, find, show)
"""

from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from nvue_automation.core.client import AsyncNVUEClient
from nvue_automation.core.exceptions import ConfigurationError
from nvue_automation.core.exceptions import NVUEAPIError
from nvue_automation.models.schemas import ApplyOptions
from nvue_automation.models.schemas import RevisionInfo
from nvue_automation.models.schemas import SpecialRevisionName
from nvue_automation.services.nvue_service import AsyncNVUEService

# ==================== Test Fixtures ====================


@pytest.fixture
def mock_client():
    """Create a mock AsyncNVUEClient."""
    client = MagicMock(spec=AsyncNVUEClient)
    client.request = AsyncMock()

    # Mock settings
    settings = MagicMock()
    settings.retries = 3
    settings.poll_interval = 1
    client.settings = settings

    return client


@pytest.fixture
def service(mock_client):
    """Create an AsyncNVUEService instance with mock client."""
    return AsyncNVUEService(mock_client)


def create_mock_response(data: Any) -> MagicMock:
    """Helper function to create a mock response."""
    response = MagicMock()
    response.json.return_value = data
    return response


class TestInitialization:
    """Test AsyncNVUEService initialization."""

    def test_init_sets_client(self, mock_client):
        """Test that initialization sets the client attribute."""
        service = AsyncNVUEService(mock_client)
        assert service.client is mock_client

    def test_init_sets_settings(self, mock_client):
        """Test that initialization sets settings from client."""
        service = AsyncNVUEService(mock_client)
        assert service.settings is mock_client.settings


class TestRevisionManagement:
    """Test revision creation and management."""

    @pytest.mark.asyncio
    async def test_create_revision_success(self, service, mock_client):
        """Test successful revision creation."""
        # Arrange
        mock_response = create_mock_response({"7": {"state": "pending"}})
        mock_client.request.return_value = mock_response

        # Act
        changeset = await service.create_revision()

        # Assert
        mock_client.request.assert_called_once_with("POST", "/revision")
        assert changeset == "7"

    @pytest.mark.asyncio
    async def test_create_revision_returns_first_key(self, service, mock_client):
        """Test that create_revision returns the first key from response."""
        # Arrange
        mock_response = create_mock_response({"42": {"state": "pending"}})
        mock_client.request.return_value = mock_response

        # Act
        changeset = await service.create_revision()

        # Assert
        assert changeset == "42"

    @pytest.mark.asyncio
    async def test_detach_config_success(self, service, mock_client):
        """Test successful config detach."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.detach_config("7")

        # Assert
        mock_client.request.assert_called_once_with("DELETE", "/revision/7")

    @pytest.mark.asyncio
    async def test_detach_config_with_special_characters(self, service, mock_client):
        """Test detach with changeset containing special characters."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.detach_config("test-123")

        # Assert
        mock_client.request.assert_called_once_with("DELETE", "/revision/test-123")


class TestConfigurationOperations:
    """Test configuration CRUD operations."""

    @pytest.mark.asyncio
    async def test_patch_config_success(self, service, mock_client):
        """Test successful configuration patch."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response
        payload = {"type": "swp", "link": {"state": {"up": {}}}}

        # Act
        await service.patch_config("/interface/swp1", payload, "7")

        # Assert
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "PATCH"
        assert call_args[0][1] == "/interface/swp1"
        assert call_args[1]["params"] == {"rev": "7"}

    @pytest.mark.asyncio
    async def test_delete_config_success(self, service, mock_client):
        """Test successful configuration deletion."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.delete_config("/interface/swp1", "7")

        # Assert
        call_args = mock_client.request.call_args
        assert call_args[0] == ("DELETE", "/interface/swp1")
        assert call_args[1]["params"] == {"rev": "7"}

    @pytest.mark.asyncio
    async def test_get_config_success(self, service, mock_client):
        """Test successful configuration retrieval."""
        # Arrange
        expected_config = {"type": "swp", "link": {"state": "up"}}
        mock_response = create_mock_response(expected_config)
        mock_client.request.return_value = mock_response

        # Act
        config = await service.get_config("interface/swp1")

        # Assert
        mock_client.request.assert_called_once_with("GET", "/interface/swp1")
        assert config == expected_config

    @pytest.mark.asyncio
    async def test_get_config_normalizes_path(self, service, mock_client):
        """Test that get_config normalizes path to start with /."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.get_config("system/hostname")

        # Assert
        mock_client.request.assert_called_once_with("GET", "/system/hostname")


class TestApplyOperations:
    """Test changeset apply operations."""

    @pytest.mark.asyncio
    async def test_apply_changeset_basic(self, service, mock_client):
        """Test basic changeset apply without options."""
        # Arrange
        mock_response = create_mock_response({"state": "apply"})
        mock_client.request.return_value = mock_response

        # Act
        result = await service.apply_changeset("7")

        # Assert
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "PATCH"
        assert "/revision/7" in call_args[0][1]
        assert result == {"state": "apply"}

    @pytest.mark.asyncio
    async def test_apply_changeset_with_options(self, service, mock_client):
        """Test changeset apply with ApplyOptions."""
        # Arrange
        mock_response = create_mock_response({"state": "apply"})
        mock_client.request.return_value = mock_response
        options = ApplyOptions(message="Test apply")

        # Act
        result = await service.apply_changeset("7", options=options)

        # Assert
        assert result == {"state": "apply"}

    @pytest.mark.asyncio
    async def test_apply_changeset_url_encodes_changeset(self, service, mock_client):
        """Test that apply_changeset URL-encodes the changeset ID."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.apply_changeset("test/123")

        # Assert
        call_args = mock_client.request.call_args
        # Should be URL encoded
        assert "/revision/test%2F123" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_wait_for_applied_success(self, service, mock_client):
        """Test successful wait_for_applied."""
        # Arrange
        # First call returns "apply", second returns "applied_and_saved"
        response1 = create_mock_response({"state": "apply"})
        response2 = create_mock_response({"state": "applied_and_saved"})
        mock_client.request.side_effect = [response1, response2]

        # Act
        result = await service.wait_for_applied("7")

        # Assert
        assert result["state"] == "applied_and_saved"
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_applied_immediate_success(self, service, mock_client):
        """Test wait_for_applied when immediately successful."""
        # Arrange
        mock_response = create_mock_response({"state": "applied_and_saved"})
        mock_client.request.return_value = mock_response

        # Act
        result = await service.wait_for_applied("7")

        # Assert
        assert result["state"] == "applied_and_saved"
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_applied_timeout(self, service, mock_client):
        """Test wait_for_applied raises error on timeout."""
        # Arrange
        mock_response = create_mock_response({"state": "apply"})
        mock_client.request.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError, match="Deployment timeout"):
            await service.wait_for_applied("7")


# ==================== High-Level Workflow Tests ====================


class TestConfigReplace:
    """Test config_replace workflow."""

    @pytest.mark.asyncio
    async def test_config_replace_success(self, service, mock_client):
        """Test successful config replace workflow."""
        # Arrange
        create_response = create_mock_response({"7": {"state": "pending"}})
        delete_response = create_mock_response({})
        patch_response = create_mock_response({})
        apply_response = create_mock_response({"state": "apply"})
        wait_response = create_mock_response({"state": "applied_and_saved"})

        mock_client.request.side_effect = [
            create_response,  # create_revision
            delete_response,  # delete_config
            patch_response,  # patch_config
            apply_response,  # apply_changeset
            wait_response,  # wait_for_applied
        ]

        payload = {"type": "swp"}

        # Act
        result = await service.config_replace("/interface/swp1", payload)

        # Assert
        assert isinstance(result, RevisionInfo)
        assert result.changeset_id == "7"
        assert mock_client.request.call_count == 5

    @pytest.mark.asyncio
    async def test_config_replace_with_confirm_skips_wait(self, service, mock_client):
        """Test config replace with confirm timeout skips wait_for_applied."""
        # Arrange
        create_response = create_mock_response({"7": {"state": "pending"}})
        delete_response = create_mock_response({})
        patch_response = create_mock_response({})
        apply_response = create_mock_response({"state": "apply"})
        history_response = create_mock_response({"state": "apply"})

        mock_client.request.side_effect = [
            create_response,
            delete_response,
            patch_response,
            apply_response,
            history_response,  # config_history instead of wait
        ]

        options = ApplyOptions.with_confirm(300, "Test")
        payload = {"type": "swp"}

        # Act
        result = await service.config_replace("/interface/swp1", payload, options)

        # Assert
        assert isinstance(result, RevisionInfo)
        assert mock_client.request.call_count == 5


class TestConfigMerge:
    """Test config_merge workflow."""

    @pytest.mark.asyncio
    async def test_config_merge_success(self, service, mock_client):
        """Test successful config merge workflow."""
        # Arrange
        create_response = create_mock_response({"7": {"state": "pending"}})
        patch_response = create_mock_response({})
        diff_response = create_mock_response({"interface": {"swp1": {"link": "up"}}})
        apply_response = create_mock_response({"state": "apply"})
        wait_response = create_mock_response({"state": "applied_and_saved"})

        mock_client.request.side_effect = [
            create_response,
            patch_response,
            diff_response,
            apply_response,
            wait_response,
        ]

        payload = {"link": {"state": {"up": {}}}}

        # Act
        result = await service.config_merge("/interface/swp1", payload)

        # Assert
        assert isinstance(result, RevisionInfo)
        assert result.changeset_id == "7"

    @pytest.mark.asyncio
    async def test_config_merge_no_changes_raises_error(self, service, mock_client):
        """Test config merge raises error when no changes detected."""
        # Arrange
        create_response = create_mock_response({"7": {"state": "pending"}})
        patch_response = create_mock_response({})
        diff_response = create_mock_response({})  # Empty diff
        detach_response = create_mock_response({})

        mock_client.request.side_effect = [
            create_response,
            patch_response,
            diff_response,
            detach_response,
        ]

        payload = {"link": {"state": {"up": {}}}}

        # Act & Assert
        with pytest.raises(ConfigurationError, match="No configuration changes detected"):
            await service.config_merge("/interface/swp1", payload)

        # Verify detach was called
        assert mock_client.request.call_count == 4


class TestConfigRollback:
    """Test config_rollback workflow."""

    @pytest.mark.asyncio
    async def test_config_rollback_success(self, service, mock_client):
        """Test successful config rollback."""
        # Arrange
        apply_response = create_mock_response({"state": "apply"})
        wait_response = create_mock_response({"state": "applied_and_saved"})

        mock_client.request.side_effect = [
            apply_response,
            wait_response,
        ]

        # Act
        result = await service.config_rollback("5")

        # Assert
        assert isinstance(result, RevisionInfo)
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_config_rollback_with_custom_message(self, service, mock_client):
        """Test rollback with custom message."""
        # Arrange
        apply_response = create_mock_response({"state": "apply"})
        wait_response = create_mock_response({"state": "applied_and_saved"})

        mock_client.request.side_effect = [
            apply_response,
            wait_response,
        ]

        # Act
        result = await service.config_rollback("5", ApplyOptions(message="Emergency rollback"))

        # Assert
        assert isinstance(result, RevisionInfo)


# ==================== Revision Diff and Search Tests ====================


class TestRevisionDiff:
    """Test revision diff operations."""

    @pytest.mark.asyncio
    async def test_get_revision_diff_success(self, service, mock_client):
        """Test successful revision diff retrieval."""
        # Arrange
        diff_data = {"interface": {"swp1": {"link": {"state": "up"}}}}
        mock_response = create_mock_response(diff_data)
        mock_client.request.return_value = mock_response

        # Act
        result = await service.get_revision_diff("/", "applied", "7")

        # Assert
        assert result == diff_data
        call_args = mock_client.request.call_args
        assert "rev=applied" in call_args[0][1]
        assert "diff=7" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_revision_diff_empty_result(self, service, mock_client):
        """Test revision diff with no changes."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        result = await service.get_revision_diff("/", "applied", "7")

        # Assert
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_revision_diff_url_encodes_parameters(self, service, mock_client):
        """Test that changeset IDs are URL-encoded."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.get_revision_diff("/", "test/base", "test/target")

        # Assert
        call_args = mock_client.request.call_args
        path = call_args[0][1]
        assert "test%2Fbase" in path
        assert "test%2Ftarget" in path


class TestConfigFind:
    """Test configuration search operations."""

    @pytest.mark.asyncio
    async def test_config_find_success(self, service, mock_client):
        """Test successful config find."""
        # Arrange
        search_results = {"interface": {"swp1": {"type": "swp"}, "swp2": {"type": "swp"}}}
        mock_response = create_mock_response(search_results)
        mock_client.request.return_value = mock_response

        # Act
        result = await service.config_find("interface")

        # Assert
        assert result == search_results
        call_args = mock_client.request.call_args
        assert call_args[1]["params"]["search-string"] == "interface"

    @pytest.mark.asyncio
    async def test_config_find_no_results(self, service, mock_client):
        """Test config find with no results."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        result = await service.config_find("nonexistent")

        # Assert
        assert result == {}


# ==================== History and Show Tests ====================


class TestConfigHistory:
    """Test configuration history operations."""

    @pytest.mark.asyncio
    async def test_config_history_single_revision(self, service, mock_client):
        """Test getting single revision history."""
        # Arrange
        revision_data = {"state": "applied_and_saved", "rev_id": "7"}
        mock_response = create_mock_response(revision_data)
        mock_client.request.return_value = mock_response

        # Act
        result = await service.config_history("7")

        # Assert
        assert result == revision_data
        call_args = mock_client.request.call_args
        assert "/revision/7" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_config_history_all_revisions(self, service, mock_client):
        """Test getting all revision history."""
        # Arrange
        all_revisions = {
            "7": {"state": "applied_and_saved"},
            "6": {"state": "applied_and_saved"},
        }
        mock_response = create_mock_response(all_revisions)
        mock_client.request.return_value = mock_response

        # Act
        result = await service.config_history(None)

        # Assert
        assert result == all_revisions
        mock_client.request.assert_called_once_with("GET", "/revision")


class TestConfigShow:
    """Test configuration show operations."""

    @pytest.mark.asyncio
    async def test_config_show_success(self, service, mock_client):
        """Test successful config show."""
        # Arrange
        full_config = {"interface": {"swp1": {}}, "router": {"bgp": {}}, "system": {}}
        mock_response = create_mock_response(full_config)
        mock_client.request.return_value = mock_response

        # Act
        result = await service.config_show()

        # Assert
        assert result == full_config
        call_args = mock_client.request.call_args
        assert call_args[1]["params"]["rev"] == SpecialRevisionName.APPLIED.value


# ==================== Confirmation Operations Tests ====================


class TestConfirmationOperations:
    """Test save, confirm, and reject operations."""

    @pytest.mark.asyncio
    async def test_config_save_success(self, service, mock_client):
        """Test successful config save."""
        # Arrange
        history_response = create_mock_response({"state": "applied"})
        save_response = create_mock_response({"state": "save"})

        mock_client.request.side_effect = [
            history_response,
            save_response,
        ]

        # Act
        result = await service.config_save("7")

        # Assert
        assert isinstance(result, RevisionInfo)
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_config_save_already_saved_skips_operation(self, service, mock_client):
        """Test that config_save skips if already in final state."""
        # Arrange
        history_response = create_mock_response({"state": "applied_and_saved"})
        mock_client.request.return_value = history_response

        # Act
        result = await service.config_save("7")

        # Assert
        assert isinstance(result, RevisionInfo)
        # Only history call, no apply
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_confirm_success(self, service, mock_client):
        """Test successful config confirm."""
        # Arrange
        history_response = create_mock_response({"state": "applied"})
        confirm_response = create_mock_response({"state": "applied_and_saved"})

        mock_client.request.side_effect = [
            history_response,
            confirm_response,
        ]

        # Act
        result = await service.config_confirm("7")

        # Assert
        assert isinstance(result, RevisionInfo)

    @pytest.mark.asyncio
    async def test_config_reject_success(self, service, mock_client):
        """Test successful config reject."""
        # Arrange
        history_response = create_mock_response({"state": "applied"})
        reject_response = create_mock_response({"state": "confirm_fail"})

        mock_client.request.side_effect = [
            history_response,
            reject_response,
        ]

        # Act
        result = await service.config_reject("7")

        # Assert
        assert isinstance(result, RevisionInfo)

    @pytest.mark.asyncio
    async def test_config_confirm_with_custom_message(self, service, mock_client):
        """Test config confirm with custom message."""
        # Arrange
        history_response = create_mock_response({"state": "applied"})
        confirm_response = create_mock_response({"state": "applied_and_saved"})

        mock_client.request.side_effect = [
            history_response,
            confirm_response,
        ]

        # Act
        result = await service.config_confirm("7", "Confirmed after testing")

        # Assert
        assert isinstance(result, RevisionInfo)


# ==================== Error Handling Tests ====================


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_create_revision_api_error(self, service, mock_client):
        """Test create_revision handles API errors."""
        # Arrange
        mock_client.request.side_effect = NVUEAPIError(status_code=500, detail="Internal server error")

        # Act & Assert
        with pytest.raises(NVUEAPIError):
            await service.create_revision()

    @pytest.mark.asyncio
    async def test_patch_config_validation_error(self, service, mock_client):
        """Test patch_config handles validation errors."""
        # Arrange
        mock_client.request.side_effect = NVUEAPIError(status_code=400, detail="Validation error")

        # Act & Assert
        with pytest.raises(NVUEAPIError):
            await service.patch_config("/interface/swp1", {}, "7")

    @pytest.mark.asyncio
    async def test_config_replace_handles_exception_and_logs(self, service, mock_client):
        """Test that config_replace properly handles and re-raises exceptions."""
        # Arrange
        create_response = create_mock_response({"7": {"state": "pending"}})
        mock_client.request.side_effect = [create_response, NVUEAPIError(status_code=404, detail="Not found")]

        # Act & Assert
        with pytest.raises(NVUEAPIError):
            await service.config_replace("/interface/swp1", {})


# ==================== Integration Tests ====================


class TestIntegration:
    """Integration tests for complex workflows."""

    @pytest.mark.asyncio
    async def test_full_config_change_workflow(self, service, mock_client):
        """Test a complete configuration change workflow."""
        # Arrange - simulate full workflow
        responses = [
            create_mock_response({"7": {"state": "pending"}}),  # create
            create_mock_response({}),  # patch
            create_mock_response({"interface": {"swp1": {}}}),  # diff
            create_mock_response({"state": "apply"}),  # apply
            create_mock_response({"state": "applied_and_saved"}),  # wait
        ]
        mock_client.request.side_effect = responses

        # Act
        result = await service.config_merge(
            "/interface/swp1", {"link": {"state": {"up": {}}}}, ApplyOptions(message="Test workflow")
        )

        # Assert
        assert isinstance(result, RevisionInfo)
        assert mock_client.request.call_count == 5

    @pytest.mark.asyncio
    async def test_apply_with_confirm_then_confirm_workflow(self, service, mock_client):
        """Test apply with confirm timeout followed by confirmation."""
        # Arrange
        responses = [
            create_mock_response({"7": {"state": "pending"}}),
            create_mock_response({}),
            create_mock_response({"interface": {}}),
            create_mock_response({"state": "apply"}),
            create_mock_response({"state": "apply"}),  # history during merge
            create_mock_response({"state": "apply"}),  # history during confirm
            create_mock_response({"state": "applied_and_saved"}),  # confirm
        ]
        mock_client.request.side_effect = responses

        # Act - Apply with confirm
        merge_result = await service.config_merge(
            "/interface/swp1", {"link": {"state": {"up": {}}}}, ApplyOptions.with_confirm(300, "Test")
        )

        # Act - Confirm
        confirm_result = await service.config_confirm("7")

        # Assert
        assert isinstance(merge_result, RevisionInfo)
        assert isinstance(confirm_result, RevisionInfo)


# ==================== Edge Cases ====================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_apply_changeset_with_special_characters_in_id(self, service, mock_client):
        """Test apply with special characters in changeset ID."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act
        await service.apply_changeset("test-id-123/special")

        # Assert
        call_args = mock_client.request.call_args
        # Verify URL encoding happened
        assert "test-id-123%2Fspecial" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_wait_for_applied_max_retries(self, service, mock_client):
        """Test wait_for_applied respects max retries."""
        # Arrange
        mock_response = create_mock_response({"state": "apply"})
        mock_client.request.return_value = mock_response
        service.settings.retries = 2

        # Act & Assert
        with pytest.raises(RuntimeError):
            await service.wait_for_applied("7")

        # Should call exactly retries times
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_config_history_with_none_changeset(self, service, mock_client):
        """Test config_history with None returns all revisions."""
        # Arrange
        mock_response = create_mock_response({"7": {}, "6": {}})
        mock_client.request.return_value = mock_response

        # Act
        result = await service.config_history(None)

        # Assert
        mock_client.request.assert_called_once_with("GET", "/revision")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_config_with_path_variations(self, service, mock_client):
        """Test get_config handles various path formats."""
        # Arrange
        mock_response = create_mock_response({})
        mock_client.request.return_value = mock_response

        # Act - Test with leading slash
        await service.get_config("/interface/swp1")

        # Assert - Should normalize to single leading slash
        mock_client.request.assert_called_with("GET", "/interface/swp1")

        # Reset mock
        mock_client.request.reset_mock()

        # Act - Test without leading slash
        await service.get_config("interface/swp1")

        # Assert - Should add leading slash
        mock_client.request.assert_called_with("GET", "/interface/swp1")
