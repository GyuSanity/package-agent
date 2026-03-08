#!/bin/bash
# container-runner teardown script
# Called by debian/prerm during package removal.
#
# This script:
#   1. Stops all *-container.service systemd units
#   2. Stops and removes Docker containers per service
#   3. Disables and removes dynamically generated systemd units

set -euo pipefail

readonly CONFIG_DIR="/etc/container-runner"
readonly UNIT_SUFFIX="-container"
readonly SYSTEMD_DIR="/lib/systemd/system"

log() {
    echo "[container-runner] $*"
}

# --- 1. Stop and disable all *-container services ---
for unit_file in "${SYSTEMD_DIR}"/*${UNIT_SUFFIX}.service; do
    [ -f "${unit_file}" ] || continue

    unit=$(basename "${unit_file}")
    service="${unit%${UNIT_SUFFIX}.service}"

    if systemctl is-active --quiet "${unit}" 2>/dev/null; then
        log "Stopping ${unit}..."
        systemctl stop "${unit}" || true
    fi

    if systemctl is-enabled --quiet "${unit}" 2>/dev/null; then
        log "Disabling ${unit}..."
        systemctl disable "${unit}" || true
    fi

    # Stop containers via compose
    service_dir="${CONFIG_DIR}/${service}"
    if [ -f "${service_dir}/docker-compose.yml" ] && [ -f "${service_dir}/.env" ]; then
        log "Stopping containers for ${service}..."
        docker compose --env-file "${service_dir}/.env" \
            -f "${service_dir}/docker-compose.yml" down --remove-orphans 2>/dev/null || true
    fi

    # Remove the dynamically generated unit file
    log "Removing ${unit_file}..."
    rm -f "${unit_file}"
done

# --- 2. Reload systemd ---
systemctl daemon-reload || true

log "Teardown complete."
