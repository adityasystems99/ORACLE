"""Semantic version parsing and transition analysis."""

import re
from typing import Optional, Tuple

SEMVER_REGEX = re.compile(r"v?(\d+)\.(\d+)(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?")


def extract_semver(text: str) -> Optional[Tuple[int, int, int, Optional[str]]]:
    """Extract semantic version (major, minor, patch, pre_release) from text string."""
    match = SEMVER_REGEX.search(text)
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3)) if match.group(3) else 0
    pre_release = match.group(4)
    return (major, minor, patch, pre_release)


def is_major_bump(old_version: str, new_version: str) -> bool:
    """Return True if new_version is a major bump over old_version."""
    old_parsed = extract_semver(old_version)
    new_parsed = extract_semver(new_version)
    if not old_parsed or not new_parsed:
        return False
    return new_parsed[0] > old_parsed[0]
