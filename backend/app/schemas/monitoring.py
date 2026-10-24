"""Pydantic schemas for ORACLE's Autonomous Monitoring Rules and Scheduled Ingestion."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .event import ChangeCategory, SeverityLevel


class AlertChannel(str, Enum):
    """Destination channels for dispatched alert notifications."""
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SLACK = "slack"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"


class MonitoringTargetType(str, Enum):
    """Category of target asset monitored by a rule."""
    TECHNOLOGY = "technology"
    API = "api"
    PRODUCT = "product"
    REPOSITORY = "repository"
    SECURITY_ADVISORY = "security_advisory"
    TOPIC = "topic"


class NotificationPreferences(BaseModel):
    """Preferences controlling dispatch behavior for triggered alerts."""
    include_dossier: bool = Field(default=True, description="Whether to attach the synthesized impact dossier")
    auto_trigger_investigation: bool = Field(default=True, description="Automatically trigger impact investigation")
    email_recipients: List[str] = Field(default_factory=list, description="Target email recipients")
    webhook_url: Optional[str] = Field(default=None, description="HTTP webhook URL for dispatch")
    slack_channel: Optional[str] = Field(default=None, description="Target Slack channel")


class MonitoringRule(BaseModel):
    """Autonomous rule evaluating ingested intelligence events against alert criteria."""
    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Descriptive rule title")
    description: str = Field(default="", description="Detailed rationale and scope of the rule")
    target_type: MonitoringTargetType = Field(default=MonitoringTargetType.TECHNOLOGY)
    category: str = Field(default="any", description="'any' or specific ChangeCategory")
    min_severity: SeverityLevel = Field(default=SeverityLevel.HIGH, description="Minimum severity gate")
    ecosystem: str = Field(default="all", description="Ecosystem filter: 'all', 'python', 'node', 'cloud', etc.")
    technology_pattern: str = Field(default="*", description="Regex, wildcard, or comma-separated technology filter")
    enabled: bool = Field(default=True, description="Whether rule evaluation is active")
    trigger_count: int = Field(default=0, description="Total times this rule has fired")
    last_triggered_at: Optional[datetime] = None
    alert_channels: List[AlertChannel] = Field(
        default_factory=lambda: [AlertChannel.IN_APP, AlertChannel.WEBHOOK]
    )
    notification_preferences: NotificationPreferences = Field(default_factory=NotificationPreferences)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MonitoringRuleCreate(BaseModel):
    """Payload to create a new monitoring rule."""
    name: str = Field(..., min_length=2, description="Rule name")
    description: Optional[str] = Field(default="", description="Description")
    target_type: Optional[MonitoringTargetType] = Field(default=MonitoringTargetType.TECHNOLOGY)
    category: Optional[str] = Field(default="any")
    min_severity: Optional[SeverityLevel] = Field(default=SeverityLevel.HIGH)
    ecosystem: Optional[str] = Field(default="all")
    technology_pattern: Optional[str] = Field(default="*")
    alert_channels: Optional[List[AlertChannel]] = Field(
        default_factory=lambda: [AlertChannel.IN_APP, AlertChannel.WEBHOOK]
    )
    notification_preferences: Optional[NotificationPreferences] = None


class MonitoringRuleUpdate(BaseModel):
    """Payload to update an existing monitoring rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    target_type: Optional[MonitoringTargetType] = None
    category: Optional[str] = None
    min_severity: Optional[SeverityLevel] = None
    ecosystem: Optional[str] = None
    technology_pattern: Optional[str] = None
    enabled: Optional[bool] = None
    alert_channels: Optional[List[AlertChannel]] = None
    notification_preferences: Optional[NotificationPreferences] = None


class AlertRecord(BaseModel):
    """Audit log of a dispatched alert preventing duplicate notifications for identical event versions."""
    id: str = Field(..., description="Unique alert record ID")
    rule_id: str
    rule_name: str
    event_id: str
    event_title: str
    event_version: str
    severity: SeverityLevel
    dispatched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    channels: List[AlertChannel]
    status: str = "dispatched"
    investigation_id: Optional[str] = None
    dedup_key: str = Field(..., description="Canonical deduplication key (rule:event:version)")


class SourceHealthStatus(BaseModel):
    """Diagnostic health and schedule observability for a monitored source."""
    source_id: str
    name: str
    source_type: str
    url: str
    enabled: bool
    refresh_interval_minutes: int
    last_synced_at: Optional[datetime] = None
    last_successful_run_at: Optional[datetime] = None
    next_scheduled_run_at: Optional[datetime] = None
    last_status: str = "initialized"
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    is_rate_limited: bool = False
    rate_limit_reset_at: Optional[datetime] = None


class SchedulerHealth(BaseModel):
    """Complete operational health of the local monolith ingestion scheduler."""
    is_running: bool
    is_paused: bool = False
    scheduler_type: str = "local_polling_monolith"
    last_tick_at: Optional[datetime] = None
    active_sources_count: int = 0
    active_rules_count: int = 0
    jobs_scheduled: int = 0
    total_runs_completed: int = 0
    total_events_detected: int = 0
    total_investigations_triggered: int = 0
    total_errors: int = 0
    sources: List[SourceHealthStatus] = Field(default_factory=list)
    push_vs_polling_disclaimer: str = (
        "ORACLE operates on scheduled interval polling with HTTP conditional request checkpointing "
        "(ETag / If-None-Match, If-Modified-Since, 304 caching), not persistent push streams. "
        "Monitoring is active only while the ORACLE backend process is running."
    )
