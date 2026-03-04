"""Get your own public IP address or that of any host."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Literal

import aiodns
from aiodns.error import DNSError
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PORT, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_NAME,
    CONF_HOSTNAME,
    CONF_IPV4,
    CONF_IPV6,
    CONF_PORT_IPV6,
    CONF_RESOLVER,
    CONF_RESOLVER_IPV6,
    DOMAIN,
)
from .coordinator import DnsResolverCoordinator

DEFAULT_RETRIES = 2
MAX_RESULTS = 10

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=120)


def sort_ips(ips: list, querytype: Literal["A", "AAAA"]) -> list:
    """Join IPs into a single string."""
    if querytype == "AAAA":
        ips = [IPv6Address(ip) for ip in ips]
    else:
        ips = [IPv4Address(ip) for ip in ips]
    return [str(ip) for ip in sorted(ips)][:MAX_RESULTS]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the dnsip+ sensor entry."""
    # Check if this is a legacy IP resolver entry or new DNS resolver monitoring entry
    if CONF_DEVICE_NAME in entry.data:
        # New DNS resolver monitoring entry
        await _async_setup_dns_resolver_sensors(hass, entry, async_add_entities)
    else:
        # Legacy IP resolver entry
        await _async_setup_legacy_sensors(hass, entry, async_add_entities)


async def _async_setup_legacy_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up legacy IP resolver sensors."""
    hostname = entry.data[CONF_HOSTNAME]
    name = entry.data[CONF_NAME]

    nameserver_ipv4 = entry.options[CONF_RESOLVER]
    nameserver_ipv6 = entry.options[CONF_RESOLVER_IPV6]
    port_ipv4 = entry.options[CONF_PORT]
    port_ipv6 = entry.options[CONF_PORT_IPV6]

    entities = []
    if entry.data[CONF_IPV4]:
        entities.append(WanIpSensor(name, hostname, nameserver_ipv4, False, port_ipv4))
    if entry.data[CONF_IPV6]:
        entities.append(WanIpSensor(name, hostname, nameserver_ipv6, True, port_ipv6))

    async_add_entities(entities, update_before_add=True)


async def _async_setup_dns_resolver_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DNS resolver monitoring sensors."""
    # Get coordinator from hass.data
    coordinator: DnsResolverCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_name = entry.data[CONF_DEVICE_NAME]

    # Create entities list
    entities = []

    # Add response time sensor
    entities.append(DnsResponseTimeSensor(coordinator, entry, device_name))

    # Add domain monitor sensors for each configured domain
    for monitor in coordinator.domain_monitors:
        entities.append(
            DomainMonitorSensor(
                coordinator=coordinator,
                config_entry_id=entry.entry_id,
                device_name=device_name,
                domain=monitor.domain,
                record_type=monitor.record_type,
            )
        )

    # Add all entities
    async_add_entities(entities)


class WanIpSensor(SensorEntity):
    """Implementation of a DNS IP+ sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "dnsipplus"
    _unrecorded_attributes = frozenset(
        {"resolver", "querytype", "ip_addresses", "response_time_ms"}
    )

    resolver: aiodns.DNSResolver

    def __init__(
        self,
        name: str,
        hostname: str,
        nameserver: str,
        ipv6: bool,
        port: int,
    ) -> None:
        """Initialize the DNS IP+ sensor."""
        self._attr_name = "IPv6" if ipv6 else None
        self._attr_unique_id = f"{hostname}_{ipv6}"
        self.hostname = hostname
        self.port = port
        self.nameserver = nameserver
        self.querytype: Literal["A", "AAAA"] = "AAAA" if ipv6 else "A"
        self._retries = DEFAULT_RETRIES
        self._attr_extra_state_attributes = {
            "resolver": nameserver,
            "querytype": self.querytype,
            "response_time_ms": None,
        }
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, hostname)},
            manufacturer="DNS",
            model=aiodns.__version__,
            name=name,
        )
        self.create_dns_resolver()

    def create_dns_resolver(self) -> None:
        """Create the DNS resolver."""
        self.resolver = aiodns.DNSResolver(
            nameservers=[self.nameserver], tcp_port=self.port, udp_port=self.port
        )

    async def async_update(self) -> None:
        """Get the current DNS IP address for hostname."""
        if self.resolver._closed:  # noqa: SLF001
            self.create_dns_resolver()
        response = None
        start_time = time.perf_counter()
        try:
            async with asyncio.timeout(10):
                response = await self.resolver.query(self.hostname, self.querytype)
            response_time = round((time.perf_counter() - start_time) * 1000, 2)
        except TimeoutError as err:
            _LOGGER.debug("Timeout while resolving host: %s", err)
            await self.resolver.close()
            response_time = None
        except DNSError as err:
            _LOGGER.warning("Exception while resolving host: %s", err)
            await self.resolver.close()
            response_time = None

        if response:
            sorted_ips = sort_ips(
                [res.host for res in response], querytype=self.querytype
            )
            self._attr_native_value = sorted_ips[0]
            self._attr_extra_state_attributes["ip_addresses"] = sorted_ips
            self._attr_extra_state_attributes["response_time_ms"] = response_time
            self._attr_available = True
            self._retries = DEFAULT_RETRIES
        elif self._retries > 0:
            self._retries -= 1
        else:
            self._attr_available = False


class DnsResponseTimeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for DNS resolver response time."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self, coordinator, config_entry: ConfigEntry, device_name: str
    ) -> None:
        """Initialize the DNS response time sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._device_name = device_name
        self._attr_unique_id = f"{config_entry.entry_id}_response_time"
        self._attr_name = f"{device_name} Response Time"

    @property
    def native_value(self) -> float | None:
        """Return response time in milliseconds."""
        if self.coordinator.data and self.coordinator.data.response_time_result:
            return self.coordinator.data.response_time_result.response_time_ms
        return None

    @property
    def available(self) -> bool:
        """Return availability based on coordinator status."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.resolver_available
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._device_name,
            manufacturer="DNS",
            model=f"Resolver Monitor (aiodns {aiodns.__version__})",
            entry_type=DeviceEntryType.SERVICE,
        )


class DomainMonitorSensor(CoordinatorEntity[DnsResolverCoordinator], SensorEntity):
    """Sensor for monitoring specific domain resolution."""

    def __init__(
        self,
        coordinator: DnsResolverCoordinator,
        config_entry_id: str,
        device_name: str,
        domain: str,
        record_type: str,
    ) -> None:
        """
        Initialize the domain monitor sensor.

        Args:
            coordinator: The DNS resolver coordinator
            config_entry_id: Config entry ID for unique ID generation
            device_name: Name of the parent device
            domain: Domain name to monitor
            record_type: DNS record type (A, AAAA, PTR, MX, TXT, CNAME, NS, SOA, SRV)

        """
        super().__init__(coordinator)

        self._domain = domain
        self._record_type = record_type
        self._device_name = device_name

        # Sanitize domain for use in unique ID (replace dots with underscores)
        sanitized_domain = domain.replace(".", "_")

        # Set entity naming and unique ID
        # Name: "{device_name} {domain_name} {record_type}"
        self._attr_name = f"{device_name} {domain} {record_type}"

        # Unique ID: "{config_entry_id}_domain_{sanitized_domain}_{record_type}"
        self._attr_unique_id = (
            f"{config_entry_id}_domain_{sanitized_domain}_{record_type}"
        )

        # Assign entity to parent device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry_id)},
        )

    @property
    def native_value(self) -> str | None:
        """
        Return resolved DNS value.

        Returns the resolved value from the coordinator data for this domain
        and record type combination.

        """
        if self.coordinator.data is None:
            return None

        # Get the result for this domain/record_type combination
        key = f"{self._domain}_{self._record_type}"
        result = self.coordinator.data.domain_results.get(key)

        if result is None or not result.success:
            return None

        return result.value

    @property
    def available(self) -> bool:
        """
        Return availability based on query success and resolver availability.

        The entity is available only if:
        1. The resolver device is available (not in failed state)
        2. The specific domain query succeeded

        """
        if self.coordinator.data is None:
            return False

        # Check resolver availability first
        if not self.coordinator.data.resolver_available:
            return False

        # Check if this specific domain query succeeded
        key = f"{self._domain}_{self._record_type}"
        result = self.coordinator.data.domain_results.get(key)

        if result is None:
            return False

        return result.success

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """
        Return additional attributes.

        Provides:
        - record_type: DNS record type queried
        - response_time_ms: Query response time in milliseconds
        - query_timestamp: Last successful query timestamp

        """
        if self.coordinator.data is None:
            return {
                "record_type": self._record_type,
                "response_time_ms": None,
                "query_timestamp": None,
            }

        # Get the result for this domain/record_type combination
        key = f"{self._domain}_{self._record_type}"
        result = self.coordinator.data.domain_results.get(key)

        attributes = {
            "record_type": self._record_type,
        }

        if result is not None:
            attributes["response_time_ms"] = result.response_time_ms
            attributes["query_timestamp"] = (
                result.timestamp.isoformat() if result.timestamp else None
            )
        else:
            attributes["response_time_ms"] = None
            attributes["query_timestamp"] = None

        return attributes
