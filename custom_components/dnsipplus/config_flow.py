"""Adds config flow for dnsip+ integration."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import re
from typing import Any, Literal

import aiodns
import voluptuous as vol
from aiodns.error import DNSError
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOSTNAME,
    CONF_IPV4,
    CONF_IPV6,
    CONF_IPV6_V4,
    CONF_PORT_IPV6,
    CONF_RESOLVER,
    CONF_RESOLVER_IPV6,
    DEFAULT_HOSTNAME,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_RESOLVER,
    DEFAULT_RESOLVER_IPV6,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOSTNAME, default=DEFAULT_HOSTNAME): cv.string,
    }
)
DATA_SCHEMA_ADV = vol.Schema(
    {
        vol.Required(CONF_HOSTNAME, default=DEFAULT_HOSTNAME): cv.string,
        vol.Optional(CONF_RESOLVER): cv.string,
        vol.Optional(CONF_PORT): cv.port,
        vol.Optional(CONF_RESOLVER_IPV6): cv.string,
        vol.Optional(CONF_PORT_IPV6): cv.port,
    }
)


async def async_validate_hostname(
    hostname: str,
    resolver_ipv4: str,
    resolver_ipv6: str,
    port: int,
    port_ipv6: int,
) -> dict[str, bool]:
    """Validate hostname."""

    async def async_check(
        hostname: str, resolver: str, qtype: Literal["A", "AAAA"], port: int = 53
    ) -> bool:
        """Return if able to resolve hostname."""
        result: bool = False
        with contextlib.suppress(DNSError):
            _resolver = aiodns.DNSResolver(
                nameservers=[resolver], udp_port=port, tcp_port=port
            )
            result = bool(await _resolver.query(hostname, qtype))

        return result

    result: dict[str, bool] = {}

    tasks = await asyncio.gather(
        async_check(hostname, resolver_ipv4, "A", port=port),
        async_check(hostname, resolver_ipv6, "AAAA", port=port_ipv6),
        async_check(hostname, resolver_ipv4, "AAAA", port=port),
    )

    result[CONF_IPV4] = tasks[0]
    result[CONF_IPV6] = tasks[1]
    result[CONF_IPV6_V4] = tasks[2]

    return result


class DnsIPPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for dnsip+ integration."""

    VERSION = 1
    MINOR_VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> DnsIPPlusOptionsFlowHandler:
        """Return Option handler."""
        del config_entry
        return DnsIPPlusOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input:
            hostname = user_input[CONF_HOSTNAME]
            name = DEFAULT_NAME if hostname == DEFAULT_HOSTNAME else hostname
            resolver = user_input.get(CONF_RESOLVER, DEFAULT_RESOLVER)
            resolver_ipv6 = user_input.get(CONF_RESOLVER_IPV6, DEFAULT_RESOLVER_IPV6)
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            port_ipv6 = user_input.get(CONF_PORT_IPV6, DEFAULT_PORT)

            validate = await async_validate_hostname(
                hostname, resolver, resolver_ipv6, port, port_ipv6
            )

            set_resolver = resolver
            if validate[CONF_IPV6]:
                set_resolver = resolver_ipv6

            if (
                not validate[CONF_IPV4]
                and not validate[CONF_IPV6]
                and not validate[CONF_IPV6_V4]
            ):
                errors["base"] = "invalid_hostname"
            else:
                await self.async_set_unique_id(hostname)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_HOSTNAME: hostname,
                        CONF_NAME: name,
                        CONF_IPV4: validate[CONF_IPV4],
                        CONF_IPV6: validate[CONF_IPV6] or validate[CONF_IPV6_V4],
                    },
                    options={
                        CONF_RESOLVER: resolver,
                        CONF_PORT: port,
                        CONF_RESOLVER_IPV6: set_resolver,
                        CONF_PORT_IPV6: port_ipv6,
                    },
                )

        if self.show_advanced_options is True:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA_ADV,
                errors=errors,
            )
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class DnsIPPlusOptionsFlowHandler(OptionsFlowWithReload):
    """Handle a option config flow for dnsip+ integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if self.config_entry.data[CONF_HOSTNAME] == DEFAULT_HOSTNAME:
            return self.async_abort(reason="no_options")

        errors = {}
        if user_input is not None:
            resolver = user_input.get(CONF_RESOLVER, DEFAULT_RESOLVER)
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            resolver_ipv6 = user_input.get(CONF_RESOLVER_IPV6, DEFAULT_RESOLVER_IPV6)
            port_ipv6 = user_input.get(CONF_PORT_IPV6, DEFAULT_PORT)
            validate = await async_validate_hostname(
                self.config_entry.data[CONF_HOSTNAME],
                resolver,
                resolver_ipv6,
                port,
                port_ipv6,
            )

            if (
                validate[CONF_IPV4] is False
                and self.config_entry.data[CONF_IPV4] is True
            ):
                errors[CONF_RESOLVER] = "invalid_resolver"
            elif (
                validate[CONF_IPV6] is False
                and self.config_entry.data[CONF_IPV6] is True
            ):
                errors[CONF_RESOLVER_IPV6] = "invalid_resolver"
            else:
                return self.async_create_entry(
                    title=self.config_entry.title,
                    data={
                        CONF_RESOLVER: resolver,
                        CONF_PORT: port,
                        CONF_RESOLVER_IPV6: resolver_ipv6,
                        CONF_PORT_IPV6: port_ipv6,
                    },
                )

        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Optional(CONF_RESOLVER): cv.string,
                    vol.Optional(CONF_PORT): cv.port,
                    vol.Optional(CONF_RESOLVER_IPV6): cv.string,
                    vol.Optional(CONF_PORT_IPV6): cv.port,
                }
            ),
            self.config_entry.options,
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


# DNS Resolver Monitoring Config Flow


class DnsResolverMonitoringConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for DNS resolver monitoring."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config_data: dict[str, Any] = {}
        self._domain_monitors: list[dict[str, str]] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> "DnsResolverMonitoringOptionsFlow":
        """Return the options flow handler."""
        return DnsResolverMonitoringOptionsFlow()


# DNS Resolver Monitoring Config Flow


class DnsResolverMonitoringConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for DNS resolver monitoring."""

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config_data: dict[str, Any] = {}
        self._domain_monitors: list[dict[str, str]] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> DnsResolverMonitoringOptionsFlow:
        """Return the options flow handler."""
        return DnsResolverMonitoringOptionsFlow()

    def _validate_resolver_address(self, address: str) -> bool:
        """Validate resolver address format (IPv4, IPv6, or hostname)."""
        import ipaddress
        import re
        # Try IPv4
        with contextlib.suppress(ValueError):
            ipaddress.IPv4Address(address)
            return True
        # Try IPv6
        with contextlib.suppress(ValueError):
            ipaddress.IPv6Address(address)
            return True
        # Try hostname format (DNS name)
        hostname_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        return bool(re.match(hostname_pattern, address))

    def _validate_domain_name(self, domain: str) -> bool:
        """Validate domain name format (DNS name format)."""
        domain = domain.rstrip(".")
        if not domain:
            return False
        domain_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        return bool(re.match(domain_pattern, domain))

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial resolver configuration step."""
        errors = {}
        if user_input is not None:
            device_name = user_input["device_name"]
            resolver_address = user_input["resolver_address"]
            resolver_port = user_input["resolver_port"]
            query_interval = user_input["query_interval"]
            if not self._validate_resolver_address(resolver_address):
                errors["resolver_address"] = "invalid_resolver_address"
            if not errors:
                self._config_data = {
                    "device_name": device_name,
                    "resolver_address": resolver_address,
                    "resolver_port": resolver_port,
                    "query_interval": query_interval,
                }
                return await self.async_step_domains()
        data_schema = vol.Schema({
            vol.Required("device_name"): cv.string,
            vol.Required("resolver_address"): cv.string,
            vol.Required("resolver_port", default=53): cv.port,
            vol.Required("query_interval", default=60): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_domains(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle domain monitor configuration step."""
        errors = {}
        if user_input is not None:
            if user_input.get("add_another", False):
                domain = user_input.get("domain", "").strip()
                record_type = user_input.get("record_type")
                if not domain:
                    errors["domain"] = "domain_required"
                elif not self._validate_domain_name(domain):
                    errors["domain"] = "invalid_domain_name"
                if not errors:
                    self._domain_monitors.append({"domain": domain, "record_type": record_type})
                    return await self.async_step_domains()
            else:
                await self.async_set_unique_id(f"{self._config_data['resolver_address']}:{self._config_data['resolver_port']}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._config_data["device_name"],
                    data={
                        "device_name": self._config_data["device_name"],
                        "resolver_address": self._config_data["resolver_address"],
                        "resolver_port": self._config_data["resolver_port"],
                    },
                    options={
                        "query_interval": self._config_data["query_interval"],
                        "domain_monitors": self._domain_monitors,
                    },
                )
        description_placeholders = {}
        if self._domain_monitors:
            monitors_text = "\n".join(f"• {m['domain']} ({m['record_type']})" for m in self._domain_monitors)
            description_placeholders["monitors"] = monitors_text
        else:
            description_placeholders["monitors"] = "None added yet"
        data_schema = vol.Schema({
            vol.Optional("add_another", default=True): cv.boolean,
            vol.Optional("domain", default=""): cv.string,
            vol.Optional("record_type", default="A"): vol.In(["A", "AAAA", "PTR", "MX", "TXT", "CNAME", "NS", "SOA", "SRV"]),
        })
        return self.async_show_form(step_id="domains", data_schema=data_schema, errors=errors, description_placeholders=description_placeholders)


class DnsResolverMonitoringOptionsFlow(OptionsFlowWithReload):
    """Handle options flow for DNS resolver monitoring reconfiguration."""

    def __init__(self, config_entry: ConfigEntry | None = None) -> None:
        """Initialize the options flow."""
        super().__init__()
        self._domain_monitors: list[dict[str, str]] = []

    def _validate_resolver_address(self, address: str) -> bool:
        """Validate resolver address format (IPv4, IPv6, or hostname)."""
        import ipaddress
        import re
        with contextlib.suppress(ValueError):
            ipaddress.IPv4Address(address)
            return True
        with contextlib.suppress(ValueError):
            ipaddress.IPv6Address(address)
            return True
        hostname_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        return bool(re.match(hostname_pattern, address))

    def _validate_domain_name(self, domain: str) -> bool:
        """Validate domain name format (DNS name format)."""
        import re
        domain = domain.rstrip(".")
        if not domain:
            return False
        domain_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        return bool(re.match(domain_pattern, domain))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow initialization."""
        errors = {}
        if user_input is None and not self._domain_monitors:
            current_monitors = self.config_entry.options.get("domain_monitors", [])
            self._domain_monitors = [dict(m) for m in current_monitors]
        if user_input is not None:
            action = user_input.get("action", "save")
            if action == "add_domain":
                return await self.async_step_add_domain()
            if action == "remove_domain":
                return await self.async_step_remove_domain()
            if action == "save":
                resolver_address = user_input["resolver_address"]
                resolver_port = user_input["resolver_port"]
                query_interval = user_input["query_interval"]
                if not self._validate_resolver_address(resolver_address):
                    errors["resolver_address"] = "invalid_resolver_address"
                if not errors:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={
                            "device_name": self.config_entry.data["device_name"],
                            "resolver_address": resolver_address,
                            "resolver_port": resolver_port,
                        },
                    )
                    return self.async_create_entry(title="", data={"query_interval": query_interval, "domain_monitors": self._domain_monitors})
        current_data = self.config_entry.data
        current_options = self.config_entry.options
        resolver_address = current_data.get("resolver_address", "")
        resolver_port = current_data.get("resolver_port", 53)
        query_interval = current_options.get("query_interval", 60)
        description_placeholders = {}
        if self._domain_monitors:
            monitors_text = "\n".join(f"{i+1}. {m['domain']} ({m['record_type']})" for i, m in enumerate(self._domain_monitors))
            description_placeholders["monitors"] = monitors_text
        else:
            description_placeholders["monitors"] = "No domain monitors configured"
        data_schema = vol.Schema({
            vol.Required("resolver_address", default=resolver_address): cv.string,
            vol.Required("resolver_port", default=resolver_port): cv.port,
            vol.Required("query_interval", default=query_interval): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            vol.Required("action", default="save"): vol.In({"save": "Save configuration", "add_domain": "Add domain monitor", "remove_domain": "Remove domain monitor"}),
        })
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors, description_placeholders=description_placeholders)

    async def async_step_add_domain(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a new domain monitor."""
        errors = {}
        if user_input is not None:
            domain = user_input.get("domain", "").strip()
            record_type = user_input.get("record_type")
            if not domain:
                errors["domain"] = "domain_required"
            elif not self._validate_domain_name(domain):
                errors["domain"] = "invalid_domain_name"
            if not errors:
                self._domain_monitors.append({"domain": domain, "record_type": record_type})
                return await self.async_step_init()
        data_schema = vol.Schema({
            vol.Required("domain"): cv.string,
            vol.Required("record_type", default="A"): vol.In(["A", "AAAA", "PTR", "MX", "TXT", "CNAME", "NS", "SOA", "SRV"]),
        })
        return self.async_show_form(step_id="add_domain", data_schema=data_schema, errors=errors)

    async def async_step_remove_domain(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle removing domain monitors."""
        if not self._domain_monitors:
            return await self.async_step_init()
        if user_input is not None:
            remove_indices = user_input.get("remove_indices", [])
            if remove_indices:
                # Convert string indices back to integers
                int_indices = [int(idx) for idx in remove_indices]
                for idx in sorted(int_indices, reverse=True):
                    if 0 <= idx < len(self._domain_monitors):
                        self._domain_monitors.pop(idx)
            return await self.async_step_init()
        # Use string keys for multi_select compatibility
        monitor_options = {str(i): f"{m['domain']} ({m['record_type']})" for i, m in enumerate(self._domain_monitors)}
        data_schema = vol.Schema({vol.Optional("remove_indices", default=[]): cv.multi_select(monitor_options)})
        return self.async_show_form(step_id="remove_domain", data_schema=data_schema)
