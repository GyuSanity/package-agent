PACKAGE_NAME := container-runner
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.1.0")
ARCH := all
BUILD_DIR := build
DEB_DIR := $(BUILD_DIR)/$(PACKAGE_NAME)
DEB_FILE := $(PACKAGE_NAME)_v$(VERSION)_$(ARCH).deb

.PHONY: all build clean lint

all: build

build: clean
	@echo "Building $(DEB_FILE)..."

	# Create directory structure
	mkdir -p $(DEB_DIR)/DEBIAN
	mkdir -p $(DEB_DIR)/etc/container-runner
	mkdir -p $(DEB_DIR)/usr/lib/container-runner/compose
	mkdir -p $(DEB_DIR)/usr/lib/container-runner/scripts

	# Copy DEBIAN control files
	cp debian/control $(DEB_DIR)/DEBIAN/
	cp debian/conffiles $(DEB_DIR)/DEBIAN/

	# Set version in control file
	if ! grep -q "^Version:" $(DEB_DIR)/DEBIAN/control; then \
		echo "Version: $(VERSION)" >> $(DEB_DIR)/DEBIAN/control; \
	fi

	# Copy and set permissions for maintainer scripts
	install -m 755 debian/postinst $(DEB_DIR)/DEBIAN/
	install -m 755 debian/prerm $(DEB_DIR)/DEBIAN/
	install -m 755 debian/postrm $(DEB_DIR)/DEBIAN/

	# Install configuration files
	install -m 644 config/models.yaml $(DEB_DIR)/etc/container-runner/

	# Install compose fragments
	install -m 644 compose/rise.yml $(DEB_DIR)/usr/lib/container-runner/compose/
	install -m 644 compose/rise-dashboard.yml $(DEB_DIR)/usr/lib/container-runner/compose/

	# Install scripts
	install -m 755 scripts/generate_config.py $(DEB_DIR)/usr/lib/container-runner/
	install -m 755 scripts/setup.sh $(DEB_DIR)/usr/lib/container-runner/
	install -m 755 scripts/teardown.sh $(DEB_DIR)/usr/lib/container-runner/
	install -m 755 scripts/container_setup.sh $(DEB_DIR)/usr/lib/container-runner/

	# Create additional setup scripts directory
	mkdir -p $(DEB_DIR)/usr/lib/container-runner/scripts/setup

	# Install container-specific setup script
	# This script is used to set up the container environment
	install -m 755 scripts/container_setup.sh $(DEB_DIR)/usr/lib/container-runner/scripts/setup/

	# Create directories that will be used in container environment
	mkdir -p $(DEB_DIR)/usr/lib/container-runner/scripts/setup/directories
	echo "/share" > $(DEB_DIR)/usr/lib/container-runner/scripts/setup/directories/share_dir
	echo "/home/\$${USER}/rise_platform" > $(DEB_DIR)/usr/lib/container-runner/scripts/setup/directories/rise_platform_dir
	echo "/home/\$${USER}/logs" > $(DEB_DIR)/usr/lib/container-runner/scripts/setup/directories/logs_dir
	echo "/etc/rise" > $(DEB_DIR)/usr/lib/container-runner/scripts/setup/directories/etc_rise_dir
	echo "/var/lib/rise" > $(DEB_DIR)/usr/lib/container-runner/scripts/setup/directories/var_lib_rise_dir

	# Create iceoryx setup script
	mkdir -p $(DEB_DIR)/usr/lib/container-runner/scripts/setup/iceoryx
	echo "iceoryx_shared" > $(DEB_DIR)/usr/lib/container-runner/scripts/setup/iceoryx/segment_name

	# Note: systemd unit files are dynamically generated at install time
	# by generate_config.py based on ROBOT_MODEL

	# Build the .deb package
	dpkg-deb --build $(DEB_DIR) $(BUILD_DIR)/$(DEB_FILE)

	@echo "Package built: $(BUILD_DIR)/$(DEB_FILE)"

clean:
	rm -rf $(BUILD_DIR)

lint:
	python3 -m py_compile scripts/generate_config.py
	shellcheck scripts/setup.sh scripts/teardown.sh debian/postinst debian/prerm debian/postrm
	@echo "Lint passed."
