# Project Structure

## Root Layout

```
.
├── custom_components/dnsipplus/    # Main integration code
├── config/                          # Home Assistant test configuration
├── scripts/                         # Development and maintenance scripts
├── .devcontainer.json              # VS Code dev container config
├── .kiro/                          # Kiro AI assistant configuration
├── hacs.json                       # HACS distribution metadata
└── requirements.txt                # Python dependencies
```

## Integration Structure

The custom component follows Home Assistant's standard integration pattern:

```
custom_components/dnsipplus/
├── __init__.py           # Entry point: async_setup_entry, async_unload_entry
├── config_flow.py        # UI configuration flow
├── const.py              # Constants and configuration keys
├── sensor.py             # Sensor platform implementation
├── manifest.json         # Integration metadata
├── strings.json          # UI strings (English)
├── icons.json            # Icon definitions
└── translations/         # Localized UI strings (40+ languages)
```

## Key Patterns

### Entry Points
- `async_setup_entry()` in `__init__.py` handles integration setup
- `async_unload_entry()` handles cleanup
- Platform forwarding to `PLATFORMS` (currently just sensor)

### Configuration
- All config constants defined in `const.py` with `CONF_*` prefix
- Default values use `DEFAULT_*` prefix
- Domain constant: `DOMAIN = "dnsipplus"`

### Naming Conventions
- Integration domain: `dnsipplus`
- Display name: `DNS IP+`
- Python package: `custom_components.dnsipplus`

## Development Environment

The `config/` directory contains a working Home Assistant instance for testing:
- Configuration files in `config/`
- Storage in `config/.storage/`
- Logs in `config/home-assistant.log*`
- Database in `config/home-assistant_v2.db`

The dev environment uses PYTHONPATH manipulation to load the custom component without symlinks.
