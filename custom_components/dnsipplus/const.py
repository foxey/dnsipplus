"""Constants for dnsip+ integration."""

from dataclasses import dataclass
from datetime import datetime

from homeassistant.const import Platform

DOMAIN = "dnsipplus"
PLATFORMS = [Platform.SENSOR]

# Legacy configuration constants (for existing IP resolver functionality)
CONF_HOSTNAME = "hostname"
CONF_RESOLVER = "resolver"
CONF_RESOLVER_IPV6 = "resolver_ipv6"
CONF_PORT_IPV6 = "port_ipv6"
CONF_IPV4 = "ipv4"
CONF_IPV6 = "ipv6"
CONF_IPV6_V4 = "ipv6_v4"

DEFAULT_HOSTNAME = "myip.opendns.com"
DEFAULT_IPV6 = False
DEFAULT_NAME = "myip"
DEFAULT_RESOLVER = "208.67.222.222"
DEFAULT_PORT = 53
DEFAULT_RESOLVER_IPV6 = "2620:119:53::53"

# DNS Resolver Monitoring - Response time test domain
# Using a reliable, globally available domain for response time testing
RESPONSE_TIME_TEST_DOMAIN = "dns.google"
RESPONSE_TIME_TEST_RECORD_TYPE = "A"

# DNS Resolver Monitoring configuration constants
CONF_DEVICE_NAME = "device_name"
CONF_RESOLVER_ADDRESS = "resolver_address"
CONF_RESOLVER_PORT = "resolver_port"
CONF_QUERY_INTERVAL = "query_interval"
CONF_DOMAIN_MONITORS = "domain_monitors"
CONF_DOMAIN = "domain"
CONF_RECORD_TYPE = "record_type"

# DNS Resolver Monitoring default values
DEFAULT_QUERY_INTERVAL = 60  # seconds
DEFAULT_RESOLVER_PORT = 53
MIN_QUERY_INTERVAL = 10  # seconds
MAX_QUERY_INTERVAL = 3600  # seconds

# Supported DNS record types
SUPPORTED_RECORD_TYPES = [
    "A",
    "AAAA",
    "PTR",
    "MX",
    "TXT",
    "CNAME",
    "NS",
    "SOA",
    "SRV",
]

# Availability detection constants
CONSECUTIVE_FAILURES_THRESHOLD = 3
DNS_QUERY_TIMEOUT = 10  # seconds


@dataclass
class DomainMonitorConfig:
    """Configuration for a single domain monitor."""

    domain: str
    record_type: str


@dataclass
class DnsQueryResult:
    """Result of a single DNS query."""

    success: bool
    value: str | None
    response_time_ms: float | None
    error: str | None
    timestamp: datetime


@dataclass
class DnsResolverData:
    """Aggregated data from coordinator update."""

    response_time_result: DnsQueryResult
    domain_results: dict[str, DnsQueryResult]  # Key: f"{domain}_{record_type}"
    resolver_available: bool
    consecutive_failures: int
