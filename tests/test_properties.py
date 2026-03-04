"""
Property-based tests for DNS Resolver Monitoring.

These tests use Hypothesis to verify universal properties across randomized inputs.
Each test runs a minimum of 100 iterations to ensure comprehensive coverage.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from custom_components.dnsipplus.const import (
    CONSECUTIVE_FAILURES_THRESHOLD,
    DnsQueryResult,
)


# Hypothesis strategies for generating test data
@st.composite
def query_sequence_strategy(draw):
    """
    Generate random sequences of query success/failure outcomes.

    Returns a list of booleans where True = success, False = failure.
    """
    # Generate sequences of varying lengths (1-20 queries)
    length = draw(st.integers(min_value=1, max_value=20))
    return draw(st.lists(st.booleans(), min_size=length, max_size=length))


# Property 15: Availability Recovery
# Feature: dns-resolver-monitoring, Property 15: Availability Recovery
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(query_sequence=query_sequence_strategy())
async def test_property_15_availability_recovery(query_sequence):
    """
    **Validates: Requirements 6.2**

    Property: For any resolver device in any availability state, when the response
    time DNS query succeeds, the device should be marked as available.

    This test generates random sequences of query success/failure and verifies
    that any successful query immediately marks the device as available,
    regardless of previous state.
    """
    # Import here to avoid issues with module-level imports
    from custom_components.dnsipplus.coordinator import DnsResolverCoordinator

    # Create a minimal mock Home Assistant instance
    hass = MagicMock()
    hass.data = {}
    hass.loop = MagicMock()

    # Mock the frame helper to avoid the "Frame helper not set up" error
    with patch("homeassistant.helpers.frame.report_usage"):
        # Create coordinator with minimal configuration
        coordinator = DnsResolverCoordinator(
            hass=hass,
            resolver_address="192.168.1.1",
            resolver_port=53,
            domain_monitors=[],
            query_interval=60,
        )

        # Track availability state through the sequence
        for query_success in query_sequence:
            # Mock the DNS query to return success or failure
            mock_result = DnsQueryResult(
                success=query_success,
                value="192.0.2.1" if query_success else None,
                response_time_ms=10.5 if query_success else None,
                error=None if query_success else "timeout",
                timestamp=datetime.now(UTC),
            )

            # Mock the _query_with_timeout method
            with patch.object(
                coordinator,
                "_query_with_timeout",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                # Execute the update
                result = await coordinator._async_update_data()

                # Verify the property: if query succeeded, device must be available
                if query_success:
                    assert result.resolver_available is True, (
                        f"Device should be available after successful query, "
                        f"but resolver_available={result.resolver_available}"
                    )
                    assert coordinator._consecutive_failures == 0, (
                        f"Consecutive failures should be reset to 0 after success, "
                        f"but got {coordinator._consecutive_failures}"
                    )
                # For failures, availability depends on consecutive failure count
                elif result.consecutive_failures >= CONSECUTIVE_FAILURES_THRESHOLD:
                    assert result.resolver_available is False, (
                        f"Device should be unavailable after {CONSECUTIVE_FAILURES_THRESHOLD} "
                        f"consecutive failures, but resolver_available={result.resolver_available}"
                    )


# Additional helper test to verify the recovery specifically
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    failures_before=st.integers(min_value=0, max_value=10),
    successes_after=st.integers(min_value=1, max_value=5),
)
async def test_property_15_recovery_from_unavailable(failures_before, successes_after):
    """
    **Validates: Requirements 6.2**

    Property: A device that becomes unavailable (after 3+ failures) should
    immediately become available when any query succeeds.

    This test specifically verifies recovery from unavailable state.
    """
    # Import here to avoid issues with module-level imports
    from custom_components.dnsipplus.coordinator import DnsResolverCoordinator

    # Create a minimal mock Home Assistant instance
    hass = MagicMock()
    hass.data = {}
    hass.loop = MagicMock()

    # Mock the frame helper to avoid the "Frame helper not set up" error
    with patch("homeassistant.helpers.frame.report_usage"):
        # Create coordinator
        coordinator = DnsResolverCoordinator(
            hass=hass,
            resolver_address="192.168.1.1",
            resolver_port=53,
            domain_monitors=[],
            query_interval=60,
        )

        # First, cause failures to potentially make device unavailable
        for _ in range(failures_before):
            mock_failure = DnsQueryResult(
                success=False,
                value=None,
                response_time_ms=None,
                error="timeout",
                timestamp=datetime.now(UTC),
            )

            with patch.object(
                coordinator,
                "_query_with_timeout",
                new_callable=AsyncMock,
                return_value=mock_failure,
            ):
                await coordinator._async_update_data()

        # Record the state after failures
        was_unavailable = not coordinator._available

        # Now send successful queries
        for _ in range(successes_after):
            mock_success = DnsQueryResult(
                success=True,
                value="192.0.2.1",
                response_time_ms=10.5,
                error=None,
                timestamp=datetime.now(UTC),
            )

            with patch.object(
                coordinator,
                "_query_with_timeout",
                new_callable=AsyncMock,
                return_value=mock_success,
            ):
                result = await coordinator._async_update_data()

                # After ANY successful query, device must be available
                assert result.resolver_available is True, (
                    f"Device should be available after successful query "
                    f"(was_unavailable={was_unavailable}, failures_before={failures_before}), "
                    f"but resolver_available={result.resolver_available}"
                )
                assert coordinator._consecutive_failures == 0, (
                    f"Consecutive failures should be 0 after success, "
                    f"but got {coordinator._consecutive_failures}"
                )


# Property 4: Resolver Address Validation
# Feature: dns-resolver-monitoring, Property 4: Resolver Address Validation
@settings(max_examples=100, deadline=None)
@given(address=st.text(min_size=0, max_size=100))
def test_property_4_resolver_address_validation(address):
    """
    **Validates: Requirements 2.4**

    Property: For any string input, the config flow validation should accept it
    as a resolver address if and only if it is a valid IPv4 address, IPv6 address,
    or hostname format.

    This test generates random strings (valid/invalid IPs, hostnames, garbage)
    and verifies that validation accepts only valid IPv4, IPv6, or hostname formats.
    """
    from custom_components.dnsipplus.config_flow import (
        DnsResolverMonitoringConfigFlow,
    )

    # Create config flow instance
    config_flow = DnsResolverMonitoringConfigFlow()

    # Validate the address
    is_valid = config_flow._validate_resolver_address(address)

    # Determine if the address should be valid
    import ipaddress
    import re

    should_be_valid = False

    # Check if it's a valid IPv4 address
    try:
        ipaddress.IPv4Address(address)
        should_be_valid = True
    except (ValueError, ipaddress.AddressValueError):
        pass

    # Check if it's a valid IPv6 address
    if not should_be_valid:
        try:
            ipaddress.IPv6Address(address)
            should_be_valid = True
        except (ValueError, ipaddress.AddressValueError):
            pass

    # Check if it's a valid hostname
    if not should_be_valid:
        hostname_pattern = (
            r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        )
        should_be_valid = bool(re.match(hostname_pattern, address))

    # Verify the property: validation result matches expected validity
    assert is_valid == should_be_valid, (
        f"Validation mismatch for address '{address}': "
        f"validator returned {is_valid}, but should be {should_be_valid}"
    )


# Additional focused tests for specific address types
@settings(max_examples=100, deadline=None)
@given(
    octet1=st.integers(min_value=0, max_value=255),
    octet2=st.integers(min_value=0, max_value=255),
    octet3=st.integers(min_value=0, max_value=255),
    octet4=st.integers(min_value=0, max_value=255),
)
def test_property_4_valid_ipv4_addresses(octet1, octet2, octet3, octet4):
    """
    **Validates: Requirements 2.4**

    Property: All valid IPv4 addresses should be accepted by the validator.

    This test generates random valid IPv4 addresses and verifies they are accepted.
    """
    from custom_components.dnsipplus.config_flow import (
        DnsResolverMonitoringConfigFlow,
    )

    # Create config flow instance
    config_flow = DnsResolverMonitoringConfigFlow()

    # Generate IPv4 address
    address = f"{octet1}.{octet2}.{octet3}.{octet4}"

    # Validate the address
    is_valid = config_flow._validate_resolver_address(address)

    # All valid IPv4 addresses should be accepted
    assert is_valid is True, f"Valid IPv4 address '{address}' was rejected"


@settings(max_examples=100, deadline=None)
@given(
    # Generate valid hostname labels (1-63 chars, alphanumeric and hyphens, not starting/ending with hyphen)
    labels=st.lists(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                min_codepoint=ord("0"),
                max_codepoint=ord("z"),
            ),
            min_size=1,
            max_size=10,
        ).filter(lambda s: s and s[0].isalnum() and s[-1].isalnum() and len(s) <= 63),
        min_size=1,
        max_size=5,
    )
)
def test_property_4_valid_hostnames(labels):
    """
    **Validates: Requirements 2.4**

    Property: All valid hostname formats should be accepted by the validator.

    This test generates random valid hostnames and verifies they are accepted.
    """
    from custom_components.dnsipplus.config_flow import (
        DnsResolverMonitoringConfigFlow,
    )

    # Create config flow instance
    config_flow = DnsResolverMonitoringConfigFlow()

    # Generate hostname from labels
    hostname = ".".join(labels)

    # Validate the hostname
    is_valid = config_flow._validate_resolver_address(hostname)

    # All valid hostnames should be accepted
    assert is_valid is True, f"Valid hostname '{hostname}' was rejected"


@settings(max_examples=100, deadline=None)
@given(
    invalid_input=st.one_of(
        # Empty string
        st.just(""),
        # Strings with invalid characters
        st.text(
            alphabet=st.characters(blacklist_characters=".-0123456789ABCDEFabcdef:"),
            min_size=1,
        ),
        # Invalid IPv4 (out of range octets)
        st.builds(
            lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
            st.integers(min_value=256, max_value=999),
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255),
        ),
        # Hostnames starting or ending with hyphen
        st.builds(lambda s: f"-{s}", st.text(min_size=1, max_size=10)),
        st.builds(lambda s: f"{s}-", st.text(min_size=1, max_size=10)),
        # Hostnames with labels > 63 chars
        st.builds(
            lambda s: s,
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=64, max_size=100),
        ),
    )
)
def test_property_4_invalid_addresses(invalid_input):
    """
    **Validates: Requirements 2.4**

    Property: Invalid addresses should be rejected by the validator.

    This test generates various types of invalid addresses and verifies they are rejected.
    """
    from custom_components.dnsipplus.config_flow import (
        DnsResolverMonitoringConfigFlow,
    )

    # Create config flow instance
    config_flow = DnsResolverMonitoringConfigFlow()

    # Validate the address
    is_valid = config_flow._validate_resolver_address(invalid_input)

    # Check if it's actually invalid
    import ipaddress
    import re

    is_actually_valid = False

    # Check if it's a valid IPv4 address
    try:
        ipaddress.IPv4Address(invalid_input)
        is_actually_valid = True
    except (ValueError, ipaddress.AddressValueError):
        pass

    # Check if it's a valid IPv6 address
    if not is_actually_valid:
        try:
            ipaddress.IPv6Address(invalid_input)
            is_actually_valid = True
        except (ValueError, ipaddress.AddressValueError):
            pass

    # Check if it's a valid hostname
    if not is_actually_valid:
        hostname_pattern = (
            r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
        )
        is_actually_valid = bool(re.match(hostname_pattern, invalid_input))

    # If it's actually valid, skip this test case
    if is_actually_valid:
        return

    # Invalid addresses should be rejected
    assert is_valid is False, f"Invalid address '{invalid_input}' was accepted"
