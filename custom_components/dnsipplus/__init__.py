"""The dnsip+ component."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiodns
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_DEVICE_NAME,
    CONF_DOMAIN_MONITORS,
    CONF_QUERY_INTERVAL,
    CONF_RESOLVER_ADDRESS,
    CONF_RESOLVER_PORT,
    DEFAULT_QUERY_INTERVAL,
    DEFAULT_RESOLVER_PORT,
    DOMAIN,
    PLATFORMS,
    DomainMonitorConfig,
)
from .coordinator import DnsResolverCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DNS IP+ from a config entry."""
    # Check if this is a legacy IP resolver entry or new DNS resolver monitoring entry
    # Legacy entries have CONF_HOSTNAME, new entries have CONF_DEVICE_NAME
    if CONF_DEVICE_NAME in entry.data:
        # New DNS resolver monitoring entry
        return await _async_setup_dns_resolver_entry(hass, entry)

    # Legacy IP resolver entry - use existing simple setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_setup_dns_resolver_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up DNS resolver monitoring from a config entry."""
    # Extract configuration from entry
    device_name = entry.data[CONF_DEVICE_NAME]
    resolver_address = entry.data[CONF_RESOLVER_ADDRESS]
    resolver_port = entry.data.get(CONF_RESOLVER_PORT, DEFAULT_RESOLVER_PORT)

    # Get options (mutable configuration)
    query_interval = entry.options.get(CONF_QUERY_INTERVAL, DEFAULT_QUERY_INTERVAL)
    domain_monitors_data = entry.options.get(CONF_DOMAIN_MONITORS, [])

    # Convert domain monitors data to DomainMonitorConfig objects
    domain_monitors = [
        DomainMonitorConfig(
            domain=monitor["domain"],
            record_type=monitor["record_type"],
        )
        for monitor in domain_monitors_data
    ]

    # Create coordinator
    coordinator = DnsResolverCoordinator(
        hass=hass,
        resolver_address=resolver_address,
        resolver_port=resolver_port,
        domain_monitors=domain_monitors,
        query_interval=query_interval,
    )

    # Perform initial coordinator refresh
    await coordinator.async_config_entry_first_refresh()

    # Register device in device registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=device_name,
        manufacturer="DNS",
        model=f"Resolver Monitor (aiodns {aiodns.__version__})",
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward setup to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload dnsip+ config entry."""
    # Check if this is a DNS resolver monitoring entry
    if CONF_DEVICE_NAME in entry.data:
        # Unload platforms
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        # Clean up coordinator from hass.data
        if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN].pop(entry.entry_id)

        return unload_ok

    # Legacy IP resolver entry
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Reload config entry when options change.

    This is called by OptionsFlowWithReload after options are saved.
    """
    await hass.config_entries.async_reload(entry.entry_id)
