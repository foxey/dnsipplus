# Requirements Document

## Introduction

This document specifies requirements for transforming the DNS IP+ Home Assistant integration from a single-instance IP address resolver into a multi-device DNS resolver monitoring system. The primary use case is monitoring multiple DNS resolvers (such as Pi-hole instances) to ensure operational availability and performance, enabling users to create automations that alert when resolvers become unavailable or slow.

## Glossary

- **Integration**: The DNS IP+ Home Assistant custom component
- **Resolver_Device**: A configured DNS resolver instance (e.g., a Pi-hole server) represented as a Home Assistant device
- **Response_Time_Entity**: A sensor entity that measures DNS query response time in milliseconds
- **Domain_Monitor_Entity**: A sensor entity that monitors availability of a specific domain record
- **DNS_Record_Type**: The type of DNS record to query (A, AAAA, PTR, MX, TXT, CNAME, NS, SOA, SRV, etc.)
- **Config_Flow**: Home Assistant's UI-based configuration interface
- **Resolver_Address**: The IP address or hostname of the DNS resolver
- **Resolver_Port**: The network port for DNS queries (default 53)
- **Query_Interval**: The time period between DNS queries in seconds

## Requirements

### Requirement 1: Multi-Device Architecture

**User Story:** As a Home Assistant user, I want to add multiple DNS resolver devices to the integration, so that I can monitor multiple Pi-hole instances or other DNS servers independently.

#### Acceptance Criteria

1. THE Integration SHALL support multiple Resolver_Device instances within a single integration installation
2. WHEN a user adds a new resolver through Config_Flow, THE Integration SHALL create a new Resolver_Device
3. THE Integration SHALL maintain independent state for each Resolver_Device
4. WHEN a Resolver_Device is removed, THE Integration SHALL remove all associated entities

### Requirement 2: Resolver Device Configuration

**User Story:** As a user, I want to configure each DNS resolver with its connection details, so that the integration can query the correct server.

#### Acceptance Criteria

1. WHEN configuring a Resolver_Device, THE Config_Flow SHALL prompt for Resolver_Address
2. WHEN configuring a Resolver_Device, THE Config_Flow SHALL prompt for Resolver_Port with a default value of 53
3. WHEN configuring a Resolver_Device, THE Config_Flow SHALL prompt for a device name
4. THE Config_Flow SHALL validate that Resolver_Address is a valid IP address or hostname
5. THE Config_Flow SHALL validate that Resolver_Port is a valid port number between 1 and 65535
6. WHEN validation fails, THE Config_Flow SHALL display a descriptive error message

### Requirement 3: Response Time Monitoring

**User Story:** As a user, I want each resolver device to measure DNS query response times, so that I can monitor resolver performance and detect slowdowns.

#### Acceptance Criteria

1. THE Integration SHALL create one Response_Time_Entity for each Resolver_Device
2. WHEN a DNS query completes successfully, THE Response_Time_Entity SHALL update its state to the query duration in milliseconds
3. WHEN a DNS query fails, THE Response_Time_Entity SHALL update its state to unavailable
4. THE Response_Time_Entity SHALL use the duration device class
5. THE Response_Time_Entity SHALL use milliseconds as the unit of measurement
6. THE Integration SHALL perform response time queries at the configured Query_Interval

### Requirement 4: Domain Monitoring Configuration

**User Story:** As a user, I want to configure multiple domains to monitor per resolver, so that I can verify that specific DNS records are resolvable.

#### Acceptance Criteria

1. WHEN configuring a Resolver_Device, THE Config_Flow SHALL allow the user to add zero or more domain monitors
2. WHEN adding a domain monitor, THE Config_Flow SHALL prompt for the domain name
3. WHEN adding a domain monitor, THE Config_Flow SHALL prompt for the DNS_Record_Type
4. THE Config_Flow SHALL support all standard DNS_Record_Type values including A, AAAA, PTR, MX, TXT, CNAME, NS, SOA, and SRV
5. THE Config_Flow SHALL validate that the domain name is a valid DNS name format
6. WHEN validation fails, THE Config_Flow SHALL display a descriptive error message

### Requirement 5: Domain Monitoring Entities

**User Story:** As a user, I want each configured domain to have its own sensor entity, so that I can monitor the availability of specific DNS records and create targeted automations.

#### Acceptance Criteria

1. THE Integration SHALL create one Domain_Monitor_Entity for each configured domain monitor
2. WHEN a DNS query for the domain succeeds, THE Domain_Monitor_Entity SHALL update its state to the resolved value
3. WHEN a DNS query for the domain fails, THE Domain_Monitor_Entity SHALL update its state to unavailable
4. THE Domain_Monitor_Entity SHALL include the DNS_Record_Type as a state attribute
5. THE Domain_Monitor_Entity SHALL include the query response time as a state attribute
6. THE Integration SHALL perform domain monitoring queries at the configured Query_Interval

### Requirement 6: Resolver Availability Status

**User Story:** As a user, I want clear availability status for each resolver device, so that I can easily create automations that alert when a resolver goes down.

#### Acceptance Criteria

1. WHEN the response time DNS query to a Resolver_Device fails for three consecutive Query_Interval periods, THE Integration SHALL mark the Resolver_Device as unavailable
2. WHEN the response time DNS query to a Resolver_Device succeeds, THE Integration SHALL mark the Resolver_Device as available
3. THE Response_Time_Entity SHALL reflect the Resolver_Device availability status
4. WHEN a Resolver_Device becomes unavailable, THE Integration SHALL set all associated Domain_Monitor_Entity states to unavailable
5. THE Integration SHALL determine Resolver_Device availability based solely on the response time query, not on Domain_Monitor_Entity query results

### Requirement 7: Query Interval Configuration

**User Story:** As a user, I want to configure how frequently the integration queries each resolver, so that I can balance monitoring responsiveness with network load.

#### Acceptance Criteria

1. WHEN configuring a Resolver_Device, THE Config_Flow SHALL prompt for Query_Interval with a default value of 60 seconds
2. THE Config_Flow SHALL validate that Query_Interval is between 10 and 3600 seconds
3. THE Integration SHALL perform all DNS queries for a Resolver_Device at the configured Query_Interval
4. WHEN Query_Interval is updated, THE Integration SHALL apply the new interval within one previous interval period

### Requirement 8: DNS Query Implementation

**User Story:** As a developer, I want the integration to use async DNS queries, so that it performs efficiently within Home Assistant's async architecture.

#### Acceptance Criteria

1. THE Integration SHALL use the aiodns library version 3.6.1 for all DNS queries
2. THE Integration SHALL perform all DNS queries asynchronously
3. WHEN a DNS query exceeds 10 seconds, THE Integration SHALL cancel the query and mark it as failed
4. THE Integration SHALL handle DNS query exceptions without crashing the integration
5. WHEN a DNS query exception occurs, THE Integration SHALL log the error with the resolver address and domain name

### Requirement 9: Entity Naming and Organization

**User Story:** As a user, I want entities to be clearly named and organized under their resolver device, so that I can easily identify which entities belong to which resolver.

#### Acceptance Criteria

1. THE Integration SHALL assign all entities to their parent Resolver_Device
2. THE Response_Time_Entity SHALL be named "{device_name} Response Time"
3. THE Domain_Monitor_Entity SHALL be named "{device_name} {domain_name} {record_type}"
4. THE Integration SHALL use the Resolver_Device name as the device name in Home Assistant
5. THE Integration SHALL generate unique entity IDs using the pattern "dnsipplus_{device_id}_{entity_type}"

### Requirement 10: Configuration Persistence and Migration

**User Story:** As a user, I want my resolver configurations to persist across Home Assistant restarts, so that I don't need to reconfigure the integration after updates.

#### Acceptance Criteria

1. THE Integration SHALL store all Resolver_Device configurations in Home Assistant's config entry system
2. WHEN Home Assistant restarts, THE Integration SHALL restore all Resolver_Device instances from stored configuration
3. THE Integration SHALL restore all entity states from Home Assistant's state database
4. WHEN the integration is updated, THE Integration SHALL preserve existing Resolver_Device configurations

### Requirement 11: Device Reconfiguration

**User Story:** As a user, I want to modify resolver configurations after initial setup, so that I can update addresses, ports, domains, or query intervals without removing and re-adding the device.

#### Acceptance Criteria

1. THE Config_Flow SHALL provide an options flow for each Resolver_Device
2. WHEN the options flow is opened, THE Config_Flow SHALL display current configuration values
3. THE Config_Flow SHALL allow modification of Resolver_Address, Resolver_Port, and Query_Interval
4. THE Config_Flow SHALL allow adding and removing domain monitors
5. WHEN configuration is updated, THE Integration SHALL apply changes within one Query_Interval period

### Requirement 12: Error Handling and Logging

**User Story:** As a user troubleshooting DNS issues, I want clear error messages and logs, so that I can diagnose problems with my DNS resolvers.

#### Acceptance Criteria

1. WHEN a DNS query fails, THE Integration SHALL log the failure with the resolver address, domain, and error reason
2. WHEN a Resolver_Device becomes unavailable, THE Integration SHALL log a warning with the device name
3. WHEN a Resolver_Device becomes available after being unavailable, THE Integration SHALL log an info message
4. THE Integration SHALL use Home Assistant's standard logging system with the colorlog library
5. THE Integration SHALL include resolver address and domain name in all DNS-related log messages
