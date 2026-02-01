"""The dnsip+ component."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import _LOGGER, HomeAssistant

from .const import CONF_PORT_IPV6, DEFAULT_PORT, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DNS IP+ from a config entry."""

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload dnsip+ config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
