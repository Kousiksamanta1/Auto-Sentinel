"""Operating system detection helpers."""

from __future__ import annotations

import platform

from core.models import RuntimeEnvironment


def detect_environment() -> RuntimeEnvironment:
    """Detects the current host operating system.

    Returns:
        RuntimeEnvironment: Structured environment information.
    """

    system_name = platform.system().strip()
    normalized = system_name.lower()

    if normalized == "linux":
        return RuntimeEnvironment(
            platform_name="Linux",
            mock_mode=False,
            supported=True,
        )

    if normalized == "darwin":
        return RuntimeEnvironment(
            platform_name="macOS",
            mock_mode=True,
            supported=True,
        )

    return RuntimeEnvironment(
        platform_name=system_name or "Unknown",
        mock_mode=True,
        supported=False,
    )
