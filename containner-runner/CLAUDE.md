# CLAUDE.md - container-runner

## Project Overview

Debian package that manages Docker container services on Samsung Humanoid robots. Deploys robot-specific Docker containers based on `ROBOT_MODEL` from `/etc/environment`, using `models.yaml` as the single source of truth for model-to-service mapping.

## Build Commands

```bash
make build    # Build .deb package (version from git tags, fallback 0.1.0)
make clean    # Remove build/ directory
make lint     # Python syntax check + shellcheck on all scripts
```

The build produces `container-runner_v<VERSION>_all.deb` using `dpkg-deb`.

## Project Structure

```
containner-runner/
├── config/models.yaml          # Robot model -> image/service mapping (single source of truth)
├── compose/                    # Docker Compose fragment templates (rise.yml, rise-dashboard.yml)
├── scripts/
│   ├── generate_config.py      # Generates per-service docker-compose, .env, systemd units
│   ├── setup.sh                # Main post-install orchestration
│   ├── teardown.sh             # Pre-removal cleanup
│   └── container_setup.sh      # Container env setup (iceoryx, shared memory, rbq user)
├── debian/                     # Debian package definition (control, postinst, prerm, postrm, etc.)
├── actions/                    # GitHub Actions (release_docker_image composite action)
└── Makefile                    # DEB package build automation
```

## Key Architecture

### Workflow
1. Read `ROBOT_MODEL` from `/etc/environment`
2. Parse `models.yaml` to determine required services
3. `generate_config.py` creates per-service `docker-compose.yml`, `.env`, and systemd unit files
4. Pull Docker images from BART registry
5. Register and start systemd services

### Installation Paths
- Config: `/etc/container-runner/` (preserved on upgrade)
- Libraries: `/usr/lib/container-runner/`
- Systemd units: `/lib/systemd/system/` (dynamically generated)
- Per-service configs: `/etc/container-runner/<service>/`

### Package Lifecycle
- **postinst**: Handles config updates, calls `setup.sh`
- **prerm**: Calls `teardown.sh`
- **postrm**: Cleans systemd units, removes images, cleanup dirs

## Languages & Dependencies

- **Python 3** (3.8+): Config generation (`generate_config.py`)
- **Bash**: Installation/teardown scripts
- **YAML**: Configuration and Docker Compose fragments

Runtime deps: `docker-ce/docker.io (>= 20.10)`, `docker-compose-plugin/docker-compose (>= 2.0)`, `python3`, `python3-yaml`, `systemd`

## Conventions

- **Bash scripts**: Always use `set -euo pipefail`; use `log()` and `error()` functions for output
- **Service names**: kebab-case (e.g., `rise-dashboard`)
- **Env vars for images**: `SCREAMING_SNAKE_CASE` with `_IMAGE` suffix (e.g., `RISE_DASHBOARD_IMAGE`)
- **Systemd units**: `<service>-container.service` naming pattern
- **Indentation**: 2 spaces (see `.editorconfig`)
- **Pre-commit hooks**: trailing-whitespace, prettier, actionlint

## Adding a New Service

1. Create `compose/<service-name>.yml` fragment
2. Add image info to `images` section in `config/models.yaml`
3. Add service to the model's `services` list in `models.yaml`
4. Add mapping in `SERVICE_ENV_MAP` in `scripts/generate_config.py`

## CI/CD

- GitHub: Samsung internal (github.sec.samsung.net)
- Docker registry: BART (`samsung-humanoid-docker-local.bart.sec.samsung.net`)
- Runners: `code-linux`
- `repository_dispatch` triggers digest updates in `models.yaml`
