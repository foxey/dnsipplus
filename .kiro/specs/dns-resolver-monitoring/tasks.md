# Implementation Plan: DNS Resolver Monitoring

## Overview

This implementation plan transforms the DNS IP+ integration from a single-instance IP resolver into a multi-device DNS resolver monitoring system. The implementation follows a multi-device architecture where each DNS resolver (e.g., Pi-hole) is a separate Home Assistant device with its own config entry, coordinator, and entities.

Key architectural changes:
- Multi-device pattern with independent config entries per resolver
- DataUpdateCoordinator for async DNS query scheduling
- Response time sensors and domain monitor sensors per device
- Config flow with multi-step domain configuration
- Options flow for reconfiguration
- Availability detection with consecutive failure tracking

## Tasks

- [x] 1. Update constants and add data models
  - Add new configuration constants (CONF_DEVICE_NAME, CONF_RESOLVER_ADDRESS, CONF_RESOLVER_PORT, CONF_QUERY_INTERVAL, CONF_DOMAIN_MONITORS, CONF_DOMAIN, CONF_RECORD_TYPE)
  - Add default values (DEFAULT_QUERY_INTERVAL=60, DEFAULT_RESOLVER_PORT=53, MIN_QUERY_INTERVAL=10, MAX_QUERY_INTERVAL=3600)
  - Add SUPPORTED_RECORD_TYPES list (A, AAAA, PTR, MX, TXT, CNAME, NS, SOA, SRV)
  - Add availability constants (CONSECUTIVE_FAILURES_THRESHOLD=3, DNS_QUERY_TIMEOUT=10)
  - Create DomainMonitorConfig dataclass
  - Create DnsQueryResult dataclass
  - Create DnsResolverData dataclass
  - _Requirements: 2.1, 2.2, 4.4, 7.1, 7.2, 8.3_

- [ ] 2. Implement DNS query coordinator
  - [x] 2.1 Create DnsResolverCoordinator class extending DataUpdateCoordinator
    - Initialize with resolver_address, resolver_port, domain_monitors, query_interval
    - Set up update interval from query_interval parameter
    - Initialize consecutive failure counter and availability flag
    - _Requirements: 1.3, 7.3, 8.2_
  
  - [x] 2.2 Implement _async_update_data method
    - Create aiodns.DNSResolver instance with configured address/port
    - Query response time domain (myip.opendns.com A record)
    - Query each configured domain monitor
    - Aggregate results into DnsResolverData structure
    - Update availability status based on query results
    - Handle exceptions without crashing
    - _Requirements: 3.2, 3.3, 5.2, 5.3, 6.1, 6.2, 8.1, 8.2, 8.4_
  
  - [x] 2.3 Implement _query_with_timeout helper method
    - Execute DNS query with asyncio.timeout(10 seconds)
    - Measure response time using time.perf_counter
    - Handle TimeoutError and DNSError exceptions
    - Return DnsQueryResult with success status, value, response_time_ms, error
    - Log failures with resolver address, domain, and error reason
    - _Requirements: 8.1, 8.3, 8.5, 12.1_
  
  - [x] 2.4 Implement extract_dns_value helper function
    - Handle A/AAAA records (return first IP or comma-separated list)
    - Handle MX records (return servers with priority)
    - Handle TXT records (return text values)
    - Handle CNAME/PTR/NS records (return hostnames)
    - Handle SOA records (return primary nameserver)
    - Handle SRV records (return service records with priority/weight/port)
    - _Requirements: 4.4, 5.2_
  
  - [x] 2.5 Implement availability detection logic
    - Track consecutive failures counter
    - Mark unavailable after 3 consecutive failures
    - Reset counter and mark available on any successful query
    - Log availability state changes (warning for unavailable, info for recovery)
    - _Requirements: 6.1, 6.2, 12.2, 12.3_
  
  - [x] 2.6 Write property test for availability recovery (Property 15)
    - **Property 15: Availability Recovery**
    - **Validates: Requirements 6.2**
    - Generate random sequences of query success/failure
    - Verify device marked available when any query succeeds
    - Run minimum 100 iterations

- [ ] 3. Implement config flow with validation
  - [x] 3.1 Create DnsResolverMonitoringConfigFlow class
    - Implement async_step_user for initial resolver configuration
    - Prompt for device_name, resolver_address, resolver_port, query_interval
    - Use voluptuous schema for input validation
    - _Requirements: 2.1, 2.2, 2.3, 7.1_
  
  - [x] 3.2 Implement resolver validation
    - Validate resolver_address format (IPv4, IPv6, or hostname)
    - Validate resolver_port range (1-65535)
    - Validate query_interval range (10-3600 seconds)
    - Display descriptive error messages on validation failure
    - _Requirements: 2.4, 2.5, 2.6, 7.2_
  
  - [x] 3.3 Implement async_step_domains for domain monitor configuration
    - Allow adding multiple domain monitors (0 or more)
    - Prompt for domain name and record_type for each monitor
    - Validate domain name format (DNS name format)
    - Support all SUPPORTED_RECORD_TYPES
    - Display descriptive error messages on validation failure
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [x] 3.4 Implement config entry creation
    - Store device_name, resolver_address, resolver_port in data section
    - Store query_interval and domain_monitors in options section
    - Create unique config entry ID
    - _Requirements: 1.2, 10.1_
  
  - [x] 3.5 Write property test for resolver address validation (Property 4)
    - **Property 4: Resolver Address Validation**
    - **Validates: Requirements 2.4**
    - Generate random strings (valid/invalid IPs, hostnames, garbage)
    - Verify validation accepts only valid IPv4, IPv6, or hostname formats
    - Run minimum 100 iterations
  
  - [x] 3.6 Write property test for port number validation (Property 5)
    - **Property 5: Port Number Validation**
    - **Validates: Requirements 2.5**
    - Generate random integers (negative, zero, valid range, too large)
    - Verify validation accepts only 1-65535
    - Run minimum 100 iterations
  
  - [x] 3.7 Write property test for domain name validation (Property 10)
    - **Property 10: Domain Name Validation**
    - **Validates: Requirements 4.5**
    - Generate random strings (valid domains, invalid formats, special chars)
    - Verify validation accepts only valid DNS name format
    - Run minimum 100 iterations
  
  - [x] 3.8 Write property test for query interval validation (Property 18)
    - **Property 18: Query Interval Validation**
    - **Validates: Requirements 7.2**
    - Generate random integers (negative, too small, valid range, too large)
    - Verify validation accepts only 10-3600 seconds
    - Run minimum 100 iterations

- [ ] 4. Implement options flow for reconfiguration
  - [x] 4.1 Create DnsResolverMonitoringOptionsFlow class
    - Implement async_step_init with current configuration values
    - Allow modification of resolver_address, resolver_port, query_interval
    - Allow adding and removing domain monitors
    - Use same validation as config flow
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  
  - [x] 4.2 Implement config entry reload on options update
    - Trigger config entry reload when options are saved
    - Apply changes within one query interval period
    - _Requirements: 11.5, 7.4_

- [x] 5. Checkpoint - Ensure config flow and validation work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement response time sensor entity
  - [x] 6.1 Create DnsResponseTimeSensor class extending CoordinatorEntity and SensorEntity
    - Set device_class to SensorDeviceClass.DURATION
    - Set native_unit_of_measurement to UnitOfTime.MILLISECONDS
    - Set state_class to SensorStateClass.MEASUREMENT
    - Implement native_value property returning response_time_ms from coordinator data
    - Implement available property based on coordinator resolver_available status
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.3_
  
  - [x] 6.2 Implement entity naming and unique ID
    - Set name to "{device_name} Response Time"
    - Set unique_id to "{config_entry_id}_response_time"
    - Assign entity to parent device
    - _Requirements: 9.1, 9.2, 9.5_
  
  - [ ] 6.3 Write property test for response time entity creation (Property 6)
    - **Property 6: Response Time Entity Creation**
    - **Validates: Requirements 3.1**
    - Generate random resolver configurations
    - Verify exactly one response time entity created per device
    - Run minimum 100 iterations
  
  - [ ] 6.4 Write property test for response time entity configuration (Property 7)
    - **Property 7: Response Time Entity Configuration**
    - **Validates: Requirements 3.4, 3.5**
    - Generate random response time entities
    - Verify device_class is DURATION and unit is MILLISECONDS
    - Run minimum 100 iterations
  
  - [ ] 6.5 Write property test for response time state on success (Property 8)
    - **Property 8: Response Time State on Success**
    - **Validates: Requirements 3.2**
    - Generate random successful query results with durations
    - Verify entity state updates to query duration in milliseconds
    - Run minimum 100 iterations
  
  - [ ] 6.6 Write property test for response time state on failure (Property 9)
    - **Property 9: Response Time State on Failure**
    - **Validates: Requirements 3.3**
    - Generate random failed query results
    - Verify entity state updates to unavailable
    - Run minimum 100 iterations

- [ ] 7. Implement domain monitor sensor entity
  - [x] 7.1 Create DomainMonitorSensor class extending CoordinatorEntity and SensorEntity
    - Initialize with domain name and record type
    - Implement native_value property returning resolved value from coordinator data
    - Implement available property based on query success and resolver availability
    - _Requirements: 5.1, 5.2, 5.3, 6.4_
  
  - [x] 7.2 Implement entity attributes
    - Add record_type attribute
    - Add response_time_ms attribute
    - Add query_timestamp attribute
    - _Requirements: 5.4, 5.5_
  
  - [x] 7.3 Implement entity naming and unique ID
    - Set name to "{device_name} {domain_name} {record_type}"
    - Set unique_id to "{config_entry_id}_domain_{sanitized_domain}_{record_type}"
    - Assign entity to parent device
    - _Requirements: 9.1, 9.3, 9.5_
  
  - [ ] 7.4 Write property test for domain monitor entity creation (Property 11)
    - **Property 11: Domain Monitor Entity Creation**
    - **Validates: Requirements 5.1**
    - Generate random lists of domain monitor configurations
    - Verify exactly one entity created per configuration
    - Run minimum 100 iterations
  
  - [ ] 7.5 Write property test for domain monitor entity attributes (Property 12)
    - **Property 12: Domain Monitor Entity Attributes**
    - **Validates: Requirements 5.4, 5.5**
    - Generate random domain monitor entities
    - Verify record_type and response_time_ms attributes present
    - Run minimum 100 iterations
  
  - [ ] 7.6 Write property test for domain monitor state on success (Property 13)
    - **Property 13: Domain Monitor State on Success**
    - **Validates: Requirements 5.2**
    - Generate random successful domain query results
    - Verify entity state updates to resolved value
    - Run minimum 100 iterations
  
  - [ ] 7.7 Write property test for domain monitor state on failure (Property 14)
    - **Property 14: Domain Monitor State on Failure**
    - **Validates: Requirements 5.3**
    - Generate random failed domain query results
    - Verify entity state updates to unavailable
    - Run minimum 100 iterations

- [x] 8. Checkpoint - Ensure sensor entities work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Update integration entry point
  - [x] 9.1 Update async_setup_entry in __init__.py
    - Create DnsResolverCoordinator with config entry data
    - Perform initial coordinator refresh
    - Register device in device registry with proper identifiers
    - Set device manufacturer to "DNS"
    - Set device model to "Resolver Monitor (aiodns {version})"
    - Forward setup to sensor platform
    - Store coordinator in hass.data
    - _Requirements: 1.2, 9.1, 9.4_
  
  - [x] 9.2 Update async_unload_entry in __init__.py
    - Stop coordinator updates
    - Unload sensor platform
    - Clean up hass.data
    - _Requirements: 1.4_
  
  - [x] 9.3 Update async_setup_entry in sensor.py
    - Create one DnsResponseTimeSensor per device
    - Create one DomainMonitorSensor per configured domain monitor
    - Add all entities to Home Assistant
    - _Requirements: 3.1, 5.1_
  
  - [ ] 9.4 Write property test for config flow creates device (Property 1)
    - **Property 1: Config Flow Creates Device**
    - **Validates: Requirements 1.2**
    - Generate random valid resolver configurations
    - Verify exactly one device created with matching configuration
    - Run minimum 100 iterations
  
  - [ ] 9.5 Write property test for device removal cleanup (Property 3)
    - **Property 3: Device Removal Cleanup**
    - **Validates: Requirements 1.4**
    - Generate random resolver devices with entities
    - Remove device and verify all entities removed from registry
    - Run minimum 100 iterations

- [ ] 10. Implement multi-device independence
  - [ ] 10.1 Write property test for device state independence (Property 2)
    - **Property 2: Device State Independence**
    - **Validates: Requirements 1.3**
    - Generate random sets of multiple resolver devices
    - Update one device state and verify others unchanged
    - Run minimum 100 iterations
  
  - [ ] 10.2 Write property test for cascading unavailability (Property 17)
    - **Property 17: Cascading Unavailability**
    - **Validates: Requirements 6.4**
    - Generate random resolver devices with domain monitors
    - Mark device unavailable and verify all domain monitors unavailable
    - Run minimum 100 iterations
  
  - [ ] 10.3 Write property test for response time reflects device availability (Property 16)
    - **Property 16: Response Time Reflects Device Availability**
    - **Validates: Requirements 6.3**
    - Generate random resolver devices with varying availability
    - Verify response time entity availability matches device availability
    - Run minimum 100 iterations

- [ ] 11. Implement entity naming and organization
  - [ ] 11.1 Write property test for entity naming conventions (Property 21)
    - **Property 21: Entity Naming Conventions**
    - **Validates: Requirements 9.2, 9.3**
    - Generate random device names, domain names, record types
    - Verify entity names follow "{D} Response Time" and "{D} {M} {R}" patterns
    - Run minimum 100 iterations
  
  - [ ] 11.2 Write property test for entity ID uniqueness (Property 22)
    - **Property 22: Entity ID Uniqueness**
    - **Validates: Requirements 9.5**
    - Generate random sets of entities
    - Verify all entity IDs unique and follow "dnsipplus_{device_id}_{entity_type}_{identifier}" pattern
    - Run minimum 100 iterations
  
  - [ ] 11.3 Write property test for entity device assignment (Property 20)
    - **Property 20: Entity Device Assignment**
    - **Validates: Requirements 9.1**
    - Generate random entities from resolver devices
    - Verify each entity assigned to its parent device in device registry
    - Run minimum 100 iterations

- [ ] 12. Implement error handling and logging
  - [x] 12.1 Add comprehensive error logging
    - Log DNS query failures with resolver address, domain, error reason
    - Log resolver unavailability warnings with device name
    - Log resolver recovery info messages
    - Use Home Assistant's standard logging with colorlog
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  
  - [ ] 12.2 Write property test for exception handling robustness (Property 19)
    - **Property 19: Exception Handling Robustness**
    - **Validates: Requirements 8.4**
    - Generate random DNS queries that raise various exceptions
    - Verify integration handles exceptions without crashing
    - Verify subsequent queries continue processing
    - Run minimum 100 iterations
  
  - [ ] 12.3 Write property test for DNS error logging with context (Property 23)
    - **Property 23: DNS Error Logging with Context**
    - **Validates: Requirements 8.5, 12.1, 12.5**
    - Generate random DNS query failures
    - Verify log messages include resolver address, domain name, error reason
    - Run minimum 100 iterations

- [x] 13. Update manifest.json and dependencies
  - Ensure aiodns 3.6.1 is in requirements list
  - Update version number if needed
  - Verify config_flow is enabled
  - _Requirements: 8.1_

- [x] 14. Final checkpoint - Integration testing
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties across randomized inputs
- The implementation uses Python with Home Assistant's async architecture
- All DNS queries use aiodns 3.6.1 for async non-blocking operations
- Multi-device architecture allows independent monitoring of multiple DNS resolvers
- Config flow provides intuitive UI-based setup and reconfiguration
- Availability detection uses 3 consecutive failures threshold
- All entities properly organized under their parent resolver device
