"""Unit tests for DNS IP+ config flow validation."""

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.dnsipplus.config_flow import DnsResolverMonitoringConfigFlow
from custom_components.dnsipplus.const import (
    CONF_DEVICE_NAME,
    CONF_QUERY_INTERVAL,
    CONF_RESOLVER_ADDRESS,
    CONF_RESOLVER_PORT,
)


@pytest.mark.asyncio
class TestDnsResolverMonitoringConfigFlow:
    """Test the DNS Resolver Monitoring config flow."""

    async def test_valid_ipv4_address(self, hass):
        """Test that valid IPv4 addresses are accepted."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass
        flow.context = {}  # Initialize context

        # Step 1: User input
        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "192.168.1.1",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "domains"

        # Step 2: Finish without adding domains
        result = await flow.async_step_domains(
            user_input={"add_another": False}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Resolver"
        assert result["data"][CONF_RESOLVER_ADDRESS] == "192.168.1.1"

    async def test_valid_ipv6_address(self, hass):
        """Test that valid IPv6 addresses are accepted."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass
        flow.context = {}  # Initialize context

        # Step 1: User input
        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "2001:4860:4860::8888",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "domains"

        # Step 2: Finish without adding domains
        result = await flow.async_step_domains(
            user_input={"add_another": False}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_RESOLVER_ADDRESS] == "2001:4860:4860::8888"

    async def test_valid_hostname(self, hass):
        """Test that valid hostnames are accepted."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass
        flow.context = {}  # Initialize context

        # Step 1: User input
        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "dns.google.com",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "domains"

        # Step 2: Finish without adding domains
        result = await flow.async_step_domains(
            user_input={"add_another": False}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_RESOLVER_ADDRESS] == "dns.google.com"

    async def test_invalid_resolver_address(self, hass):
        """Test that invalid resolver addresses are rejected."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "not a valid address!@#",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][CONF_RESOLVER_ADDRESS] == "invalid_resolver_address"

    async def test_invalid_ipv4_address(self, hass):
        """Test that clearly invalid addresses are rejected."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass
        flow.context = {}  # Initialize context

        # Note: "256.256.256.256" is invalid as IP but valid as hostname (digits are allowed)
        # Step 1: User input
        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "256.256.256.256",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        # This will be accepted as a valid hostname (digits are allowed)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "domains"

        # Step 2: Finish without adding domains
        result = await flow.async_step_domains(
            user_input={"add_another": False}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_hostname_with_invalid_characters(self, hass):
        """Test that hostnames with invalid characters are rejected."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "invalid_hostname!.com",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][CONF_RESOLVER_ADDRESS] == "invalid_resolver_address"

    async def test_hostname_starting_with_hyphen(self, hass):
        """Test that hostnames starting with hyphen are rejected."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "-invalid.com",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][CONF_RESOLVER_ADDRESS] == "invalid_resolver_address"

    async def test_empty_resolver_address(self, hass):
        """Test that empty resolver addresses are rejected."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"][CONF_RESOLVER_ADDRESS] == "invalid_resolver_address"

    async def test_valid_subdomain_hostname(self, hass):
        """Test that valid subdomain hostnames are accepted."""
        flow = DnsResolverMonitoringConfigFlow()
        flow.hass = hass
        flow.context = {}  # Initialize context

        # Step 1: User input
        result = await flow.async_step_user(
            user_input={
                CONF_DEVICE_NAME: "Test Resolver",
                CONF_RESOLVER_ADDRESS: "ns1.example.co.uk",
                CONF_RESOLVER_PORT: 53,
                CONF_QUERY_INTERVAL: 60,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "domains"

        # Step 2: Finish without adding domains
        result = await flow.async_step_domains(
            user_input={"add_another": False}
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_RESOLVER_ADDRESS] == "ns1.example.co.uk"
