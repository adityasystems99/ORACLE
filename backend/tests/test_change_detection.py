"""Unit tests for change detection and semantic classification."""

from app.change_detection.detector import ChangeDetector
from app.change_detection.semver_utils import extract_semver, is_major_bump
from app.schemas.event import ChangeCategory, SeverityLevel
from app.schemas.ingestion import RawSignal, SourceType


def test_semver_extraction():
    parsed = extract_semver("v2.14.0-rc1")
    assert parsed == (2, 14, 0, "rc1")
    assert is_major_bump("1.9.0", "2.0.0") is True
    assert is_major_bump("1.9.0", "1.10.0") is False


def test_cve_vulnerability_detection(test_disk_store):
    detector = ChangeDetector(disk_store=test_disk_store)
    signal = RawSignal(
        id="sig_test_cve",
        source_id="src_sec",
        source_type=SourceType.SECURITY_ADVISORY,
        title="CVE-2024-34064: Remote Code Execution flaw discovered",
        url="https://example.com/advisory",
        content="A critical vulnerability in fastapi was identified allowing arbitrary code execution.",
        content_hash="hash_cve_1",
    )
    event = detector.classify_signal(signal)
    assert event is not None
    assert event.category == ChangeCategory.SECURITY_VULNERABILITY
    assert event.cve_id == "CVE-2024-34064"
    assert event.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
    assert len(event.evidence) == 1
    assert "CVE-2024-34064" in event.evidence[0].snippet or "CVE-2024-34064" in event.evidence[0].title


def test_breaking_change_detection(test_disk_store):
    detector = ChangeDetector(disk_store=test_disk_store)
    signal = RawSignal(
        id="sig_test_breaking",
        source_id="src_pydantic",
        source_type=SourceType.GITHUB_RELEASES,
        title="Pydantic v3.0 Released",
        url="https://github.com/pydantic/pydantic/releases/tag/v3.0.0",
        content="This release contains breaking changes and backwards incompatible model validators.",
        content_hash="hash_breaking_1",
        metadata={"repository": "pydantic"},
    )
    event = detector.classify_signal(signal)
    assert event is not None
    assert event.category == ChangeCategory.BREAKING_CHANGE
    assert event.primary_technology == "pydantic"
    assert event.severity == SeverityLevel.HIGH
