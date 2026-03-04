"""Test the DNS IP+ integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.dnsipplus import (
    _async_setup_dns_resolver_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.dnsipplus.const import (
    CONF_DEVICE_NAME,
    CONF_HOSTNAME,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_setup_entry_routes_to_dns_resolver() -> None:
    """Test that config entries with CONF_DEVICE_NAME route to DNS resolver setup."""
    hass = MagicMock()
    entry = MagicMock()
    entry.data = {CONF_DEVICE_NAME: "Test", "resolver_address": "1.1.1.1"}
    entry.options = {"query_interval": 60, "domain_monitors": []}

    with patch(
        "custom_components.dnsipplus._async_setup_dns_resolver_entry",
        new_callable=AsyncMock,
    ) as mock_dns_setup:
        mock_dns_setup.return_value = True
        result = await async_setup_entry(hass, entry)

        assert result is True
        mock_dns_setup.assert_called_once_with(hass, entry)


@pytest.mark.asyncio
async def test_setup_entry_routes_to_legacy() -> None:
    """Test that config entries with CONF_HOSTNAME route to legacy setup."""
    hass = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    entry = MagicMock()
    entry.data = {CONF_HOSTNAME: "myip.opendns.com"}

    result = await async_setup_entry(hass, entry)

    assert result is True
    hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_dns_resolver_setup_creates_coordinator() -> None:
    """Test that DNS resolver setup creates and stores coordinator."""
    hass = MagicMock()
    hass.data = {}
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_DEVICE_NAME: "Test Resolver",
        "resolver_address": "192.168.1.1",
        "resolver_port": 53,
    }
    entry.options = {
        "query_interval": 60,
        "domain_monitors": [{"domain": "example.com", "record_type": "A"}],
    }

    with (
        patch(
            "custom_components.dnsipplus.DnsResolverCoordinator"
        ) as mock_coordinator_class,
        patch("custom_components.dnsipplus.dr.async_get") as mock_device_registry,
        patch.object(hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock),
    ):
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        mock_registry = MagicMock()
        mock_device_registry.return_value = mock_registry

        result = await _async_setup_dns_resolver_entry(hass, entry)

        assert result is True
        # Verify coordinator was created
        mock_coordinator_class.assert_called_once()
        # Verify coordinator refresh was called
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        # Verify device was registered
        mock_registry.async_get_or_create.assert_called_once()
        # Verify coordinator stored in hass.data
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_dns_resolver_entry() -> None:
    """Test unloading a DNS resolver entry removes coordinator from hass.data."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"test_entry_id": MagicMock()}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_DEVICE_NAME: "Test"}

    result = await async_unload_entry(hass, entry)

    assert result is True
    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_legacy_entry() -> None:
    """Test unloading a legacy entry."""
    hass = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    entry = MagicMock()
    entry.data = {CONF_HOSTNAME: "myip.opendns.com"}

    result = await async_unload_entry(hass, entry)

    assert result is True
    hass.config_entries.async_unload_platforms.assert_called_once()

