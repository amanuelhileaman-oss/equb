from decimal import Decimal
import uuid
from .models import AuditLog

def sanitize_json_payload(obj):
    if isinstance(obj, dict):
        return {str(k): sanitize_json_payload(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_json_payload(x) for x in obj]
    elif isinstance(obj, (Decimal, uuid.UUID)):
        return str(obj)
    return obj

def log_audit_event(action: str, actor=None, group=None, target_model: str = "", target_id: str = "", details: dict = None, request=None):
    ip = None
    ua = ""
    if request:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        ua = request.META.get('HTTP_USER_AGENT', '')[:250]
        if not actor and request.user.is_authenticated:
            actor = request.user

    sanitized_details = sanitize_json_payload(details or {})

    return AuditLog.objects.create(
        action=action,
        actor=actor,
        group=group,
        target_model=target_model,
        target_id=str(target_id),
        details=sanitized_details,
        ip_address=ip if ip and len(ip) <= 45 else None,
        user_agent=ua
    )

