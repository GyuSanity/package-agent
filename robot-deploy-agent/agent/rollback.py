"""Backup, restore, and rollback of service .env files."""

import logging
import os
import shutil

from agent.systemd_manager import restart_all_services

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages backup/restore of .env files and service rollback."""

    def __init__(self, service_config_dir: str):
        self.service_config_dir = service_config_dir

    def _env_path(self, service_name: str) -> str:
        return os.path.join(self.service_config_dir, service_name, ".env")

    def _backup_path(self, service_name: str) -> str:
        return os.path.join(self.service_config_dir, service_name, ".env.bak")

    def backup_env_files(self, service_names: list[str]) -> None:
        """Create .env.bak copies for each service.

        Args:
            service_names: List of service names to back up.
        """
        for name in service_names:
            src = self._env_path(name)
            dst = self._backup_path(name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                logger.info("Backed up %s -> %s", src, dst)
            else:
                logger.warning("No .env file to back up for service %s at %s", name, src)

    def restore_env_files(self, service_names: list[str]) -> None:
        """Restore .env files from .env.bak backups.

        Args:
            service_names: List of service names to restore.
        """
        for name in service_names:
            src = self._backup_path(name)
            dst = self._env_path(name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                logger.info("Restored %s -> %s", src, dst)
            else:
                logger.warning("No backup file to restore for service %s at %s", name, src)

    def perform_rollback(self, service_names: list[str]) -> bool:
        """Restore .env backups and restart all services.

        Args:
            service_names: List of service names to roll back.

        Returns:
            True if restore and restart all succeeded, False otherwise.
        """
        logger.info("Performing rollback for services: %s", service_names)
        self.restore_env_files(service_names)
        ok = restart_all_services(service_names)
        if ok:
            logger.info("Rollback completed successfully")
        else:
            logger.error("Rollback restart failed for one or more services")
        return ok
