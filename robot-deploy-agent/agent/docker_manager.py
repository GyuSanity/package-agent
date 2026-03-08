"""Docker image pull operations via subprocess."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def pull_image(image_ref: str, dry_run: bool = False) -> bool:
    """Pull a single Docker image by reference.

    Args:
        image_ref: Image reference, typically in the form <repo>@<digest>.
        dry_run: If True, skip actual pull and return True.

    Returns:
        True if the pull succeeded, False otherwise.
    """
    if dry_run:
        logger.info("[DRY RUN] Would pull image: %s", image_ref)
        return True
    logger.info("Pulling image: %s", image_ref)
    try:
        result = subprocess.run(
            ["docker", "pull", image_ref],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            logger.info("Successfully pulled image: %s", image_ref)
            return True
        else:
            logger.error(
                "Failed to pull image %s: returncode=%d, stderr=%s",
                image_ref,
                result.returncode,
                result.stderr.strip(),
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error("Timed out pulling image: %s", image_ref)
        return False
    except Exception as exc:
        logger.error("Error pulling image %s: %s", image_ref, exc)
        return False


def pull_all_images(services: list[dict], dry_run: bool = False) -> bool:
    """Pull Docker images for all services.

    Each service dict must contain 'image_repo' and 'image_digest' keys.
    The image reference is constructed as <image_repo>@<image_digest>.

    Args:
        services: List of service dicts with image info.
        dry_run: If True, skip actual pulls.

    Returns:
        True if all pulls succeeded, False if any failed.
    """
    all_ok = True
    for svc in services:
        image_repo = svc.get("image_repo", "")
        image_digest = svc.get("image_digest", "")
        image_ref = f"{image_repo}@{image_digest}"
        if not pull_image(image_ref, dry_run=dry_run):
            all_ok = False
            logger.error("Image pull failed for service %s", svc.get("service_name", "unknown"))
    return all_ok
