#!/bin/bash
# Container environment setup script
# This script sets up the environment for running the RISE platform in a container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="rise-integrated"
PORT="12000"
SHARE_DIR="/share"

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load ROBOT_MODEL from /etc/environment
if [ -f "/etc/environment" ]; then
    # Source the environment file and extract ROBOT_MODEL
    source /etc/environment
    if [ -n "$ROBOT_MODEL" ]; then
        print_status "Loaded ROBOT_MODEL from /etc/environment: $ROBOT_MODEL"
    else
        print_error "ROBOT_MODEL not found in /etc/environment"
        print_error "Please add 'ROBOT_MODEL=<model_name>' to /etc/environment"
        exit 1
    fi
else
    print_error "/etc/environment file not found"
    print_error "Please ensure /etc/environment exists and contains ROBOT_MODEL=<model_name>"
    exit 1
fi

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

setup_share_directory() {
    print_status "Setting up IPC directory at $SHARE_DIR..."

    if [ ! -d "$SHARE_DIR" ]; then
        print_status "Creating $SHARE_DIR directory..."
        sudo mkdir -p "$SHARE_DIR"
    fi

    print_status "Setting permissions to 777 for $SHARE_DIR..."
    sudo chmod 777 "$SHARE_DIR"

    print_success "IPC directory setup completed"
}

setup_rise_platform_directory() {
    local rise_dir="${HOME}/rise_platform"
    print_status "Setting up RISE platform directory at $rise_dir..."

    if [ ! -d "$rise_dir" ]; then
        print_status "Creating $rise_dir directory..."
        mkdir -p "$rise_dir"
        sudo chmod 777 "$rise_dir"
    fi

    print_success "RISE platform directory setup completed"
}

setup_logs_directory() {
    local logs_dir="${HOME}/logs"
    print_status "Setting up logs directory at $logs_dir..."

    if [ ! -d "$logs_dir" ]; then
        print_status "Creating $logs_dir directory..."
        mkdir -p "$logs_dir"
        sudo chmod 777 "$logs_dir"
    fi

    print_success "Logs directory setup completed"
}

setup_rise_host_directories() {
    print_status "Setting up RISE host directories for volume mounts..."

    # Create /etc/rise directory
    if [ ! -d "/etc/rise" ]; then
        print_status "Creating /etc/rise directory..."
        sudo mkdir -p "/etc/rise"
        sudo chmod 777 "/etc/rise"
    fi

    # Create /var/lib/rise directory
    if [ ! -d "/var/lib/rise" ]; then
        print_status "Creating /var/lib/rise directory..."
        sudo mkdir -p "/var/lib/rise"
        sudo chmod 777 "/var/lib/rise"
    fi

    # Copy RISE configuration files from source if host directory is empty
    if [ -z "$(ls -A /etc/rise)" ]; then
        print_status "Copying RISE configuration files to host /etc/rise..."
        # Copy from external/rise/configs/etc/rise to host /etc/rise
        if [ -d "external/rise/configs/etc/rise" ]; then
            cp -r external/rise/configs/etc/rise/* /etc/rise/
            print_status "RISE configuration files copied from source"
        else
            print_warning "RISE configuration source not found, please ensure files exist in /etc/rise"
        fi
    fi

    # Set ownership and permissions
    print_status "Setting ownership and permissions for RISE directories..."
    sudo chmod -R 777 /etc/rise /var/lib/rise

    print_success "RISE host directories setup completed"
}

setup_iceoryx_permissions() {
    print_status "Setting up iceoryx permissions for cross-container communication..."

    # Create rbq user if not exists
    if ! id "rbq" &>/dev/null; then
        print_status "Creating rbq user..."
        sudo useradd -m -s /bin/bash rbq
        sudo echo "rbq:rbq" | sudo chpasswd
        sudo usermod -aG sudo rbq
        echo "rbq ALL=(ALL) NOPASSWD: ALL" | sudo tee -a /etc/sudoers
        print_success "rbq user created successfully"
    else
        print_status "rbq user already exists"
    fi

    # Set /tmp permissions for iceoryx
    print_status "Setting permissions for /tmp directory..."
    sudo chmod 777 /tmp

    # Clean up existing iceoryx lock files and sockets
    print_status "Cleaning up existing iceoryx lock files and sockets..."
    sudo rm -f /tmp/iox-*.lock /tmp/roudi.lock /tmp/roudi 2>/dev/null || true

    # Set permissions for shared memory
    print_status "Setting permissions for /dev/shm..."
    sudo chmod 777 /dev/shm

    # Set ownership and permissions for iceoryx files and directories
    print_status "Setting ownership and permissions for iceoryx resources..."

    # Set permissions for iceoryx runtime files
    sudo chown -R rbq:rbq /tmp/iox-* /tmp/roudi* 2>/dev/null || true
    sudo chmod -R 777 /tmp/iox-* /tmp/roudi* 2>/dev/null || true

    # Set permissions for shared memory segments
    sudo chown -R rbq:rbq /dev/shm/iox-* /dev/shm/roudi* 2>/dev/null || true
    sudo chmod -R 777 /dev/shm/iox-* /dev/shm/roudi* 2>/dev/null || true

    print_success "Iceoryx permissions setup completed"
    print_status "Iceoryx segment name set to: iceoryx_shared"
    print_status "Use this environment variable when running iceoryx commands on host:"
    print_status "export ICEORYX_SEGMENT_NAME=iceoryx_shared"
}

build_container() {
    print_status "Building integrated Docker container..."
    ROBOT_MODEL="$ROBOT_MODEL" docker compose -f docker/docker-compose.yml build
    print_success "Container build completed"
}

# Main setup function that combines all setup steps
# Configures paths and settings for container environment:
# - Checks Docker installation
# - Sets up IPC directory (/share)
# - Creates RISE platform directory ($HOME/rise_platform)
# - Creates logs directory ($HOME/logs)
# - Sets up RISE host directories (/etc/rise, /var/lib/rise)
# - Configures iceoryx permissions for cross-container communication
setup_container_environment() {
    print_status "Setting up container environment..."
    check_docker
    setup_share_directory
    setup_rise_platform_directory
    setup_logs_directory
    setup_rise_host_directories
    setup_iceoryx_permissions
    print_success "Container environment setup completed"
}

# Run setup if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    setup_container_environment
fi
