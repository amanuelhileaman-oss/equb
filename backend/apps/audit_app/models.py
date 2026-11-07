import uuid
from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100, db_index=True)
    target_model = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['group', 'timestamp']),
        ]

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Audit logs are append-only and immutable. Edits are rejected.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Audit logs are permanent records and cannot be deleted.")

    def __str__(self):
        actor_name = self.actor.full_name if self.actor else "System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {actor_name} -> {self.action}"


class PlatformSetting(models.Model):
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'platform_settings'

    def __str__(self):
        return f"{self.key}: {self.value}"


class VerificationRecord(models.Model):
    class Category(models.TextChoices):
        ORGANIZER = 'ORGANIZER', 'Organizer Identity & Business'
        GROUP = 'GROUP', 'Equb Group Verification'
        PAYMENT_DESTINATION = 'PAYMENT_DESTINATION', 'Group Payment Destination'
        PROVIDER_ONBOARDING = 'PROVIDER_ONBOARDING', 'Provider Onboarding Status'

    class Status(models.TextChoices):
        NOT_SUBMITTED = 'NOT_SUBMITTED', 'Not Submitted'
        PENDING = 'PENDING', 'Pending'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        ADDITIONAL_INFORMATION_REQUIRED = 'ADDITIONAL_INFORMATION_REQUIRED', 'Additional Information Required'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=40, choices=Category.choices, db_index=True)
    target_id = models.CharField(max_length=100, db_index=True)
    target_name = models.CharField(max_length=255)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING, db_index=True)
    submission_notes = models.TextField(blank=True)
    decision_reason = models.TextField(blank=True)
    documents = models.JSONField(default=list, help_text="Metadata list of submitted files/evidence")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verifications_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'verification_records'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.target_name} - {self.status}"


class PaymentProviderConfiguration(models.Model):
    class ProviderCode(models.TextChoices):
        TELEBIRR = 'TELEBIRR', 'Telebirr SuperApp & Web'
        CBE_BIRR = 'CBE_BIRR', 'Commercial Bank of Ethiopia (CBE Birr)'
        CHAPA = 'CHAPA', 'Chapa Payment Gateway'
        ARIFPAY = 'ARIFPAY', 'ArifPay POS & Online'
        SANTIMPAY = 'SANTIMPAY', 'SantimPay Omni-Channel'

    class Environment(models.TextChoices):
        SANDBOX = 'SANDBOX', 'Sandbox / Testing'
        PRODUCTION = 'PRODUCTION', 'Live Production'

    class Health(models.TextChoices):
        HEALTHY = 'HEALTHY', 'Operational / Healthy'
        DEGRADED = 'DEGRADED', 'Degraded Latency'
        DOWN = 'DOWN', 'Offline / Unreachable'
        UNCONFIGURED = 'UNCONFIGURED', 'Credentials Not Configured'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_code = models.CharField(max_length=50, choices=ProviderCode.choices, unique=True, db_index=True)
    display_name = models.CharField(max_length=100)
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.SANDBOX)
    is_enabled = models.BooleanField(default=False)
    is_live_ready = models.BooleanField(default=False, help_text="Compliance check: live-money remains disabled until certified")
    connection_health = models.CharField(max_length=20, choices=Health.choices, default=Health.UNCONFIGURED)
    failed_webhook_count = models.PositiveIntegerField(default=0)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    last_error_message = models.TextField(blank=True)
    config_metadata = models.JSONField(default=dict, blank=True, help_text="Safe metadata without exposing raw secrets")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'payment_provider_configurations'

    def __str__(self):
        return f"{self.display_name} ({self.environment}) - {'ENABLED' if self.is_enabled else 'DISABLED'}"


class Announcement(models.Model):
    class TargetAudience(models.TextChoices):
        ALL = 'ALL', 'All Platform Users'
        ORGANIZERS = 'ORGANIZERS', 'Equb Organizers Only'
        MEMBERS = 'MEMBERS', 'Equb Members Only'
        SPECIFIC_ORGANIZER = 'SPECIFIC_ORGANIZER', 'Specific Organizer'
        SPECIFIC_GROUP = 'SPECIFIC_GROUP', 'Group Members Only'

    class Category(models.TextChoices):
        GENERAL = 'GENERAL', 'General Announcement'
        MAINTENANCE = 'MAINTENANCE', 'System Maintenance'
        FEATURE = 'FEATURE', 'New Feature Release'
        SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription & Billing'
        VERIFICATION = 'VERIFICATION', 'Verification & KYC'
        CONTRIBUTION_DEADLINE = 'CONTRIBUTION_DEADLINE', 'Contribution Deadline'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    title_am = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    content_am = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.GENERAL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    channels = models.JSONField(default=list, blank=True, help_text="Channels: IN_APP, EMAIL, SMS")
    target_audience = models.CharField(max_length=30, choices=TargetAudience.choices, default=TargetAudience.ALL)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_announcements'
    )
    target_group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_announcements'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.title}"


class SecurityEvent(models.Model):
    class EventType(models.TextChoices):
        FAILED_LOGIN = 'FAILED_LOGIN', 'Failed Login Attempt'
        SUSPICIOUS_LOGIN = 'SUSPICIOUS_LOGIN', 'Suspicious Geolocation or IP Login'
        SESSION_REVOKED = 'SESSION_REVOKED', 'Session Administrative Revocation'
        PERMISSION_ESCALATION = 'PERMISSION_ESCALATION', 'Privilege Escalation Attempt'
        ACCOUNT_LOCKED = 'ACCOUNT_LOCKED', 'Account Locked'

    class Severity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.LOW, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_events'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'security_events'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity}] {self.event_type} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        TECHNICAL = 'TECHNICAL', 'Technical Issue'
        BILLING = 'BILLING', 'Billing & Subscription'
        DISPUTE_ESCALATION = 'DISPUTE_ESCALATION', 'Dispute Escalation'
        VERIFICATION = 'VERIFICATION', 'Verification Inquiries'
        OTHER = 'OTHER', 'General Inquiries'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets'
    )
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.OTHER)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    response_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.subject} ({self.user.full_name})"


class SecurityIncident(models.Model):
    class RiskLevel(models.TextChoices):
        LOW = 'LOW', 'Low Risk'
        MEDIUM = 'MEDIUM', 'Medium Risk'
        HIGH = 'HIGH', 'High Risk'
        CRITICAL = 'CRITICAL', 'Critical Risk'

    class RequestResult(models.TextChoices):
        BLOCKED = 'BLOCKED', 'Immediately Blocked on Backend'
        REJECTED = 'REJECTED', 'Rejected'
        RESTRICTED = 'RESTRICTED', 'Access Restricted'

    class IncidentStatus(models.TextChoices):
        DETECTED = 'DETECTED', 'Detected'
        BLOCKED = 'BLOCKED', 'Blocked'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        INFORMATION_REQUESTED = 'INFORMATION_REQUESTED', 'Information Requested'
        CONFIRMED_VIOLATION = 'CONFIRMED_VIOLATION', 'Confirmed Violation'
        FALSE_POSITIVE = 'FALSE_POSITIVE', 'False Positive'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident_id = models.CharField(max_length=64, unique=True, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_incidents_as_organizer'
    )
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_incidents'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_incidents_caused'
    )
    user_group_role = models.CharField(max_length=50, blank=True)
    attempted_operation = models.CharField(max_length=150)
    affected_resource = models.CharField(max_length=150)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.MEDIUM, db_index=True)
    request_result = models.CharField(max_length=20, choices=RequestResult.choices, default=RequestResult.BLOCKED)
    security_rule_triggered = models.CharField(max_length=200)
    evidence_references = models.JSONField(default=dict, blank=True)
    current_restrictions = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=40, choices=IncidentStatus.choices, default=IncidentStatus.DETECTED, db_index=True)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_incidents_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    group_notified = models.BooleanField(default=False)
    group_notification_sent_at = models.DateTimeField(null=True, blank=True)
    group_notification_message = models.TextField(blank=True)

    class Meta:
        db_table = 'security_incidents'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['status', 'risk_level']),
            models.Index(fields=['group', 'timestamp']),
        ]

    def __str__(self):
        return f"[{self.incident_id}] {self.attempted_operation} ({self.risk_level}) - {self.status}"


class OrganizerSuspensionRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suspension_records'
    )
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organizer_suspensions_issued'
    )
    reason = models.TextField()
    evidence = models.TextField(blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    review_date = models.DateTimeField(null=True, blank=True)
    restrictions_applied = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organizer_restorations'
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    restoration_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'organizer_suspension_records'
        ordering = ['-start_date']

    def __str__(self):
        return f"Suspension for {self.organizer.email} ({'ACTIVE' if self.is_active else 'RESTORED'})"


class GroupSuspensionRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='suspension_records'
    )
    suspended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_suspensions_issued'
    )
    reason = models.TextField()
    evidence = models.TextField(blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    review_date = models.DateTimeField(null=True, blank=True)
    restrictions_applied = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='group_restorations'
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    restoration_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'group_suspension_records'
        ordering = ['-start_date']

    def __str__(self):
        return f"Suspension for group {self.group.name} ({'ACTIVE' if self.is_active else 'RESTORED'})"



