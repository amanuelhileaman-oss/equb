import uuid
import logging
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from apps.audit_app.models import SecurityIncident, SecurityEvent, AuditLog

logger = logging.getLogger(__name__)


def record_and_block_security_violation(
    request,
    attempted_operation: str,
    affected_resource: str,
    security_rule_triggered: str,
    risk_level: str = SecurityIncident.RiskLevel.HIGH,
    group=None,
    target_user=None,
    details=None
):
    """
    Core backend security barrier for Digital Equb Ethiopia.
    When an unauthorized or prohibited financial action is attempted:
    1. Rejects operation immediately on backend.
    2. Does not execute financial transaction or alter ledger.
    3. Records the attempted action as an immutable SecurityIncident.
    4. Notifies/alerts Super Admin via SecurityEvent.
    5. Raises PermissionDenied with reference ID.
    """
    user = target_user or (request.user if hasattr(request, 'user') and request.user.is_authenticated else None)
    incident_uuid = uuid.uuid4().hex[:8].upper()
    incident_id = f"SEC-2026-{incident_uuid}"

    # Extract client IP and user agent
    ip_address = None
    user_agent = ""
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

    # Determine user role in group
    user_role = "UNAUTHENTICATED"
    if user and group:
        membership = group.memberships.filter(user=user).first()
        if membership:
            roles = list(membership.role_assignments.values_list('role__code', flat=True))
            user_role = ", ".join(roles) if roles else "GROUP_MEMBER"
        elif user.is_platform_admin:
            user_role = "PLATFORM_SUPER_ADMIN"
    elif user and user.is_platform_admin:
        user_role = "PLATFORM_SUPER_ADMIN"
    elif user:
        user_role = "AUTHENTICATED_USER"

    organizer = group.organizer if group else (user if user and hasattr(user, 'organizer_profile') else None)

    evidence_dict = {
        "ip_address": ip_address,
        "user_agent": user_agent,
        "payload": details or {},
        "timestamp": timezone.now().isoformat()
    }

    # 1. Create SecurityIncident record
    incident = SecurityIncident.objects.create(
        incident_id=incident_id,
        organizer=organizer,
        group=group,
        user=user,
        user_group_role=user_role,
        attempted_operation=attempted_operation,
        affected_resource=affected_resource,
        risk_level=risk_level,
        request_result=SecurityIncident.RequestResult.BLOCKED,
        security_rule_triggered=security_rule_triggered,
        evidence_references=evidence_dict,
        status=SecurityIncident.IncidentStatus.BLOCKED
    )

    # 2. Create SecurityEvent for live platform monitoring
    severity_map = {
        SecurityIncident.RiskLevel.LOW: SecurityEvent.Severity.LOW,
        SecurityIncident.RiskLevel.MEDIUM: SecurityEvent.Severity.MEDIUM,
        SecurityIncident.RiskLevel.HIGH: SecurityEvent.Severity.HIGH,
        SecurityIncident.RiskLevel.CRITICAL: SecurityEvent.Severity.CRITICAL,
    }
    SecurityEvent.objects.create(
        event_type=SecurityEvent.EventType.PERMISSION_ESCALATION,
        severity=severity_map.get(risk_level, SecurityEvent.Severity.HIGH),
        user=user,
        ip_address=ip_address,
        description=f"[{incident_id}] {attempted_operation} on {affected_resource} was blocked by security policy.",
        details=evidence_dict
    )

    # 3. Write immutable audit log
    try:
        AuditLog.objects.create(
            actor=user,
            group=group,
            action="FINANCIAL_SECURITY_INCIDENT_BLOCKED",
            target_model=affected_resource,
            target_id=incident_id,
            details={
                "incident_id": incident_id,
                "operation": attempted_operation,
                "rule": security_rule_triggered,
                "risk_level": risk_level
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        logger.error(f"Failed to record audit log for security incident: {e}")

    logger.warning(
        f"[SECURITY BARRIER BLOCKED] Incident {incident_id} by user {getattr(user, 'email', 'Anon')} "
        f"for operation '{attempted_operation}' on resource '{affected_resource}'."
    )

    raise PermissionDenied(
        f"Security Violation: Unauthorized financial action blocked ({attempted_operation}). Incident Reference: {incident_id}."
    )

