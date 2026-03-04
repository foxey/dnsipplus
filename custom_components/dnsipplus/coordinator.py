"""Data update coordinator for DNS resolver monitoring."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import aiodns
from aiodns.error import DNSError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONSECUTIVE_FAILURES_THRESHOLD,
    DNS_QUERY_TIMEOUT,
    DOMAIN,
    RESPONSE_TIME_TEST_DOMAIN,
    RESPONSE_TIME_TEST_RECORD_TYPE,
    DnsQueryResult,
    DnsResolverData,
    DomainMonitorConfig,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def extract_dns_value(response: list, record_type: str) -> str:
    """
    Extract displayable value from DNS response.

    Handles different DNS record types and formats the response appropriately
    for display in sensor entities.

    Args:
        response: DNS query response answer list from aiodns query_dns()
        record_type: DNS record type (A, AAAA, PTR, MX, TXT, CNAME, NS, SOA, SRV)

    Returns:
        Formatted string representation of the DNS response

    """
    if not response:
        return ""

    result = None

    # Handle A/AAAA records - return first IP or comma-separated list
    if record_type in ("A", "AAAA"):
        hosts = [r.data.addr for r in response]
        result = hosts[0] if len(hosts) == 1 else ", ".join(hosts)

    # Handle MX records - return mail servers with priority
    elif record_type == "MX":
        mx_records = [(r.data.priority, r.data.exchange) for r in response]
        result = ", ".join(
            f"{host} ({priority})" for priority, host in sorted(mx_records)
        )

    # Handle TXT records - return text values
    elif record_type == "TXT":
        txt_values = []
        for r in response:
            # TXT records are stored in data.text
            text_data = r.data.text
            if isinstance(text_data, bytes):
                txt_values.append(text_data.decode("utf-8", errors="replace"))
            else:
                txt_values.append(str(text_data))
        result = ", ".join(txt_values)

    # Handle CNAME/PTR/NS records - return hostname(s)
    elif record_type in ("CNAME", "PTR", "NS"):
        result = response[0].data.name if hasattr(response[0].data, "name") else str(response[0].data)

    # Handle SOA records - return primary nameserver
    elif record_type == "SOA":
        result = response[0].data.mname

    # Handle SRV records - return service records with priority/weight/port
    elif record_type == "SRV":
        srv_records = [(r.data.priority, r.data.weight, r.data.port, r.data.target) for r in response]
        result = ", ".join(
            f"{host}:{port} (p:{priority} w:{weight})"
            for priority, weight, port, host in sorted(srv_records)
        )

    # Fallback for unknown record types
    else:
        result = str(response)

    return result


class DnsResolverCoordinator(DataUpdateCoordinator[DnsResolverData]):
    """
    Coordinator for DNS resolver monitoring.

    Manages DNS query scheduling and state updates for a single resolver device.
    Tracks response times, domain resolution, and availability status.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        resolver_address: str,
        resolver_port: int,
        domain_monitors: list[DomainMonitorConfig],
        query_interval: int,
    ) -> None:
        """
        Initialize the DNS resolver coordinator.

        Args:
            hass: Home Assistant instance
            resolver_address: IP address or hostname of the DNS resolver
            resolver_port: Port number for DNS queries
            domain_monitors: List of domain monitor configurations
            query_interval: Time between DNS queries in seconds

        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{resolver_address}",
            update_interval=timedelta(seconds=query_interval),
        )

        self.resolver_address = resolver_address
        self.resolver_port = resolver_port
        self.domain_monitors = domain_monitors
        self.query_interval = query_interval

        # Availability tracking
        self._consecutive_failures = 0
        self._available = True

    async def _async_update_data(self) -> DnsResolverData:
        """
        Fetch data from DNS resolver.

        Queries the response time domain and all configured domain monitors.
        Updates availability status based on query results.

        Returns:
            DnsResolverData with query results and availability status

        """
        # Create aiodns.DNSResolver instance with configured address/port
        resolver = aiodns.DNSResolver(
            nameservers=[self.resolver_address],
            udp_port=self.resolver_port,
            tcp_port=self.resolver_port,
        )

        try:
            # Query response time domain (dns.google A record)
            response_time_result = await self._query_with_timeout(
                resolver, RESPONSE_TIME_TEST_DOMAIN, RESPONSE_TIME_TEST_RECORD_TYPE
            )

            # Query each configured domain monitor
            domain_results = {}
            for monitor in self.domain_monitors:
                result = await self._query_with_timeout(
                    resolver, monitor.domain, monitor.record_type
                )
                domain_results[f"{monitor.domain}_{monitor.record_type}"] = result

            # Update availability status based on response time query results
            if response_time_result.success:
                # Reset consecutive failures counter on success
                if self._consecutive_failures > 0:
                    _LOGGER.info(
                        "DNS resolver %s is now available", self.resolver_address
                    )
                self._consecutive_failures = 0
                self._available = True
            else:
                # Increment consecutive failures counter on failure
                self._consecutive_failures += 1
                if self._consecutive_failures >= CONSECUTIVE_FAILURES_THRESHOLD:
                    if self._available:
                        _LOGGER.warning(
                            "DNS resolver %s is unavailable after %d "
                            "consecutive failures",
                            self.resolver_address,
                            self._consecutive_failures,
                        )
                    self._available = False

            # Return aggregated results
            return DnsResolverData(
                response_time_result=response_time_result,
                domain_results=domain_results,
                resolver_available=self._available,
                consecutive_failures=self._consecutive_failures,
            )

        except Exception:
            # Handle exceptions without crashing
            _LOGGER.exception(
                "Unexpected error querying DNS resolver %s",
                self.resolver_address,
            )

            # Create failed result for response time
            failed_result = DnsQueryResult(
                success=False,
                value=None,
                response_time_ms=None,
                error="Unexpected error",
                timestamp=datetime.now(UTC),
            )

            # Increment consecutive failures
            self._consecutive_failures += 1
            if self._consecutive_failures >= CONSECUTIVE_FAILURES_THRESHOLD:
                if self._available:
                    _LOGGER.warning(
                        "DNS resolver %s is unavailable after %d consecutive failures",
                        self.resolver_address,
                        self._consecutive_failures,
                    )
                self._available = False

            # Return failed results for all queries
            domain_results = {}
            for monitor in self.domain_monitors:
                domain_results[f"{monitor.domain}_{monitor.record_type}"] = (
                    failed_result
                )

            return DnsResolverData(
                response_time_result=failed_result,
                domain_results=domain_results,
                resolver_available=self._available,
                consecutive_failures=self._consecutive_failures,
            )

        finally:
            # Clean up resolver
            await resolver.close()

    async def _query_with_timeout(
        self, resolver: aiodns.DNSResolver, domain: str, record_type: str
    ) -> DnsQueryResult:
        """
        Execute DNS query with timeout and error handling.

        Performs a DNS query with a 10-second timeout, measures response time,
        and handles errors gracefully.

        Args:
            resolver: aiodns.DNSResolver instance
            domain: Domain name to query
            record_type: DNS record type (A, AAAA, PTR, MX, TXT, CNAME, NS, SOA, SRV)

        Returns:
            DnsQueryResult with query outcome, response time, and any errors

        """
        start_time = time.perf_counter()

        try:
            # Execute DNS query with 10-second timeout
            async with asyncio.timeout(DNS_QUERY_TIMEOUT):
                response = await resolver.query_dns(domain, record_type)

            # Calculate response time in milliseconds
            response_time = (time.perf_counter() - start_time) * 1000

            # Extract value from response.answer using helper function
            value = extract_dns_value(response.answer, record_type)

            return DnsQueryResult(
                success=True,
                value=value,
                response_time_ms=round(response_time, 2),
                error=None,
                timestamp=datetime.now(UTC),
            )

        except TimeoutError:
            # Query exceeded timeout
            _LOGGER.debug(
                "DNS query timeout for %s (%s) via %s:%d after %d seconds",
                domain,
                record_type,
                self.resolver_address,
                self.resolver_port,
                DNS_QUERY_TIMEOUT,
            )
            return DnsQueryResult(
                success=False,
                value=None,
                response_time_ms=None,
                error="timeout",
                timestamp=datetime.now(UTC),
            )

        except DNSError as err:
            # DNS resolution error (NXDOMAIN, SERVFAIL, etc.)
            _LOGGER.warning(
                "DNS query failed for %s (%s) via %s:%d: %s",
                domain,
                record_type,
                self.resolver_address,
                self.resolver_port,
                err,
            )
            return DnsQueryResult(
                success=False,
                value=None,
                response_time_ms=None,
                error=str(err),
                timestamp=datetime.now(UTC),
            )
