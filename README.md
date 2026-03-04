# DNS IP+

A Home Assistant custom component that monitors DNS servers and queries DNS records. Track DNS resolver response times, query various DNS record types, and monitor your public IP address via DNS.

## Features

- **DNS Resolver Monitoring**: Track response times and availability of DNS servers
- **Multiple Record Types**: Query A, AAAA, CNAME, MX, TXT, NS, PTR, SOA, and SRV records
- **Domain Monitoring**: Monitor multiple domains per resolver
- **Public IP Detection**: Use DNS queries to determine your public IPv4/IPv6 address
- **Config Flow UI**: Easy setup through Home Assistant's UI
- **HACS Compatible**: Install and update via HACS

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/dnsipplus` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Adding a DNS Resolver

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "DNS IP+"
4. Configure your DNS resolver:
   - **Device Name**: Friendly name for this resolver
   - **Resolver Address**: IP address or hostname of the DNS server (e.g., `8.8.8.8`, `1.1.1.1`)
   - **Resolver Port**: DNS port (default: 53)
   - **Query Interval**: How often to query in seconds (default: 60)

### Adding Domain Monitors

After adding a resolver, you can configure domains to monitor:

1. Go to the integration's options (click "Configure" on the DNS IP+ integration)
2. Select "Add domain monitor"
3. Configure:
   - **Domain**: Domain name to query (e.g., `google.com`, `example.com`)
   - **Record Type**: Type of DNS record (A, AAAA, CNAME, MX, TXT, NS, PTR, SOA, SRV)

You can add multiple domains per resolver and remove them later through the options flow.

## Sensors

### Resolver Sensors

Each DNS resolver creates the following sensors:

- **Response Time**: DNS query response time in milliseconds
- **Status**: Availability status of the DNS resolver

### Domain Monitor Sensors

Each domain monitor creates a sensor showing:

- **A/AAAA Records**: IP addresses (sorted to prevent round-robin changes)
- **CNAME Records**: Canonical name
- **MX Records**: Mail servers with priority (e.g., `smtp.google.com (10)`)
- **TXT Records**: Text values (sorted)
- **NS Records**: Nameservers (sorted)
- **PTR Records**: Reverse DNS hostname
- **SOA Records**: Complete SOA information including serial, refresh, retry, expire, and minimum TTL
- **SRV Records**: Service records with priority, weight, and port

## Use Cases

### Monitor Public IP Address

Configure a resolver (e.g., OpenDNS at `208.67.222.222`) and add domain monitors:
- Domain: `myip.opendns.com`, Record Type: `A` (for IPv4)
- Domain: `myip.opendns.com`, Record Type: `AAAA` (for IPv6)

### Monitor DNS Server Performance

Add multiple resolvers (Google DNS, Cloudflare, your ISP's DNS) and compare response times.

### Track DNS Changes

Monitor your domain's DNS records to detect unauthorized changes or propagation issues.

### Verify Email Configuration

Query MX records to verify your domain's email server configuration.

## Requirements

- Home Assistant >= 2026.2.0
- Python >= 3.13
- aiodns >= 4.0.0

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/foxey/dnsipplus.git
cd dnsipplus

# Start development environment
scripts/develop
```

This starts a local Home Assistant instance with the integration loaded.

### Linting

```bash
scripts/lint
```

Runs ruff formatter and linter with auto-fix enabled.

## Troubleshooting

### Resolver Shows as Unavailable

- Verify the DNS server address and port are correct
- Check if the DNS server is accessible from your Home Assistant instance
- Some DNS servers may block queries from certain sources

### Domain Monitor Shows "Unknown"

- Verify the domain name is correct
- Check if the record type exists for that domain
- Some record types (like PTR) require specific domain formats (e.g., `1.1.1.1.in-addr.arpa`)

### CNAME Errors

If you see errors about CNAME records when querying A/AAAA records, this is normal. The integration filters out CNAME records that may appear in A/AAAA responses.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Built with [aiodns](https://github.com/saghul/aiodns) for async DNS resolution
- Uses [pycares](https://github.com/saghul/pycares) for DNS protocol handling
