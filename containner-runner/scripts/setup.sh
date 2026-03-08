#!/bin/bash
# container-runner setup script
# Called by debian/postinst during package installation or upgrade.
#
# This script:
#   1. Reads ROBOT_MODEL from /etc/environment
#   2. Generates per-service docker-compose.yml, .env, and systemd units
#   3. Pulls required Docker images per service
#   4. Enables and starts each service's systemd unit

set -euo pipefail

readonly CONFIG_DIR="/etc/container-runner"
readonly LIB_DIR="/usr/lib/container-runner"
readonly MODELS_YAML="${CONFIG_DIR}/models.yaml"
readonly COMPOSE_DIR="${LIB_DIR}/compose"
readonly GENERATE_SCRIPT="${LIB_DIR}/generate_config.py"
readonly UNIT_SUFFIX="-container"

log() {
    echo "[container-runner] $*"
}

error() {
    echo "[container-runner] ERROR: $*" >&2
}

# --- 1. Read ROBOT_MODEL from /etc/environment ---
if [ -f /etc/environment ]; then
    # shellcheck source=/dev/null
    set -a
    . /etc/environment
    set +a
fi

if [ -z "${ROBOT_MODEL:-}" ]; then
    error "ROBOT_MODEL is not set in /etc/environment"
    error "Please set ROBOT_MODEL before installing this package."
    error "Example: echo 'ROBOT_MODEL=extreme' >> /etc/environment"
    exit 1
fi

log "Detected robot model: ${ROBOT_MODEL}"

# --- 2. Validate prerequisites ---
if ! command -v docker &>/dev/null; then
    error "Docker is not installed. Please install docker-ce first."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    error "Python3 is not installed. Please install python3 first."
    exit 1
fi

if ! python3 -c "import yaml" &>/dev/null; then
    error "PyYAML is not installed. Please install python3-yaml first."
    exit 1
fi

# --- 3. Ensure config directory exists ---
mkdir -p "${CONFIG_DIR}"

# --- 4. Generate per-service configs and systemd units ---
log "Generating per-service configuration for model: ${ROBOT_MODEL}"
python3 "${GENERATE_SCRIPT}" \
    --model "${ROBOT_MODEL}" \
    --models-yaml "${MODELS_YAML}" \
    --compose-dir "${COMPOSE_DIR}" \
    --output-dir "${CONFIG_DIR}"

# --- 5. Login to BART registry if credentials are available ---
if [ -f "${CONFIG_DIR}/bart-credentials" ]; then
    log "Logging into BART registry..."
    # shellcheck source=/dev/null
    . "${CONFIG_DIR}/bart-credentials"
    echo "${BART_PASSWORD:-}" | docker login "${BART_REGISTRY:-}" \
        --username "${BART_USERNAME:-srbot}" --password-stdin 2>/dev/null || true
fi

# --- 6. Defensive cleanup of existing containers ---
# Remove any existing containers with conflicting names to prevent installation failure
for service_dir in "${CONFIG_DIR}"/*/; do
    [ -d "${service_dir}" ] || continue

    service=$(basename "${service_dir}")
    container_name="${service}-container"

    # Check if a container with this name exists and remove it
    if docker ps -a --format "{{.Names}}" | grep -q "^${container_name}$"; then
        log "Removing existing container ${container_name} to prevent conflicts..."
        docker rm -f "${container_name}" 2>/dev/null || true
    fi
done

# --- 7. Reload systemd to pick up new unit files ---
systemctl daemon-reload

# --- 8. Run container environment setup if available ---
if [ -x "${LIB_DIR}/container_setup.sh" ]; then
    log "Running container environment setup..."
    "${LIB_DIR}/container_setup.sh"
    log "Container environment setup complete."
fi

# --- 9. Pull images and enable/start each service ---
for service_dir in "${CONFIG_DIR}"/*/; do
    [ -d "${service_dir}" ] || continue

    service=$(basename "${service_dir}")
    unit="${service}${UNIT_SUFFIX}.service"
    compose_file="${service_dir}docker-compose.yml"
    env_file="${service_dir}.env"

    # Skip directories without compose files (e.g. stale dirs)
    if [ ! -f "${compose_file}" ] || [ ! -f "${env_file}" ]; then
        continue
    fi

    log "Pulling images for ${service}..."
    if docker compose --env-file "${env_file}" -f "${compose_file}" pull; then
        log "  Images pulled successfully for ${service}"
    else
        error "  Failed to pull images for ${service}. Check network and registry access."
        continue
    fi

    log "Enabling and starting ${unit}..."
    systemctl enable "${unit}"
    systemctl start "${unit}"
done

log "Setup complete."
log "Check status: systemctl status '*${UNIT_SUFFIX}.service'"
log "List all services: systemctl list-units '*${UNIT_SUFFIX}*'"

# --- 10. Install and start robot-deploy-agent ---
readonly AGENT_DIR="/opt/robot-deploy-agent"
readonly AGENT_CONFIG_DIR="/etc/robot-deploy-agent"
readonly AGENT_STATE_DIR="/var/lib/robot-deploy-agent"
readonly AGENT_UNIT="robot-deploy-agent.service"

if [ -d "${AGENT_DIR}" ]; then
    log "Setting up robot-deploy-agent..."

    # Create config and state directories
    mkdir -p "${AGENT_CONFIG_DIR}"
    mkdir -p "${AGENT_STATE_DIR}"

    # Generate agent config if not exists (preserve existing config on upgrade)
    if [ ! -f "${AGENT_CONFIG_DIR}/agent.yaml" ]; then
        DEVICE_NAME=$(hostname)
        log "Generating agent config for device: ${DEVICE_NAME}, model: ${ROBOT_MODEL}"
        cat > "${AGENT_CONFIG_DIR}/agent.yaml" <<AGENT_EOF
# Auto-generated by container-runner setup
control_plane_url: "http://localhost:8000"
device_name: "${DEVICE_NAME}"
robot_model: "${ROBOT_MODEL}"
auth_key: "CHANGE_ME"
polling_interval_sec: 30
heartbeat_interval_sec: 60
service_config_dir: "${CONFIG_DIR}"
state_file: "${AGENT_STATE_DIR}/state.json"
log_level: "INFO"
AGENT_EOF
        log "  Agent config generated at ${AGENT_CONFIG_DIR}/agent.yaml"
        log "  WARNING: Update auth_key and control_plane_url before starting agent"
    else
        log "  Agent config already exists, preserving existing configuration"
    fi

    # Install systemd unit if available
    if [ -f "${AGENT_DIR}/systemd/${AGENT_UNIT}" ]; then
        cp "${AGENT_DIR}/systemd/${AGENT_UNIT}" "/lib/systemd/system/${AGENT_UNIT}"
        systemctl daemon-reload
        systemctl enable "${AGENT_UNIT}"
        log "  Agent systemd unit installed and enabled"

        # Only start if config has been customized (auth_key != CHANGE_ME)
        if grep -q 'auth_key: "CHANGE_ME"' "${AGENT_CONFIG_DIR}/agent.yaml"; then
            log "  Agent NOT started: update auth_key and control_plane_url first"
            log "  Then run: systemctl start ${AGENT_UNIT}"
        else
            systemctl start "${AGENT_UNIT}"
            log "  Agent started"
        fi
    fi
else
    log "robot-deploy-agent not installed at ${AGENT_DIR}, skipping agent setup"
fi
