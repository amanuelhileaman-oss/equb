from django.db import transaction
from django.utils import timezone
from .models import RuleVersion, RuleApproval
from apps.groups.models import GroupMembership, EqubGroup

@transaction.atomic
def evaluate_rule_approvals(rule_version: RuleVersion) -> dict:
    """
    Evaluates whether a proposed rule version has met the configured approval threshold.
    If threshold is reached:
    - Updates previous rule versions to SUPERSEDED
    - Sets this version to APPROVED and marks effective_at
    - Updates group.active_rules_version and activates group if in PENDING_APPROVAL
    """
    group = rule_version.group
    active_memberships = GroupMembership.objects.filter(
        group=group,
        status=GroupMembership.MembershipStatus.ACTIVE
    )
    total_active_members = active_memberships.count()

    if total_active_members == 0:
        return {'approved': False, 'current_percent': 0, 'required_percent': rule_version.approval_threshold_percent, 'total_votes': 0}

    approved_votes_count = RuleApproval.objects.filter(
        rule_version=rule_version,
        membership__in=active_memberships,
        decision=RuleApproval.Decision.APPROVED
    ).count()

    current_percent = (approved_votes_count / total_active_members) * 100

    if current_percent >= rule_version.approval_threshold_percent:
        # Supersede existing active rules
        RuleVersion.objects.filter(
            group=group,
            status=RuleVersion.RuleStatus.APPROVED
        ).exclude(id=rule_version.id).update(status=RuleVersion.RuleStatus.SUPERSEDED)

        # Mark this version approved
        rule_version.status = RuleVersion.RuleStatus.APPROVED
        rule_version.effective_at = timezone.now()
        rule_version.save(update_fields=['status', 'effective_at'])

        # Update group configuration
        group.active_rules_version = rule_version
        group.contribution_amount = rule_version.contribution_amount
        group.contribution_frequency = rule_version.contribution_frequency
        group.payout_method = rule_version.payout_method
        if group.status in [EqubGroup.GroupStatus.DRAFT, EqubGroup.GroupStatus.PENDING_APPROVAL]:
            group.status = EqubGroup.GroupStatus.ACTIVE
        group.save()

        # Update accepted_rules_version for members who approved
        approving_memberships = active_memberships.filter(
            rule_votes__rule_version=rule_version,
            rule_votes__decision=RuleApproval.Decision.APPROVED
        )
        approving_memberships.update(accepted_rules_version=rule_version)

        return {
            'approved': True,
            'current_percent': current_percent,
            'required_percent': rule_version.approval_threshold_percent,
            'approved_votes': approved_votes_count,
            'total_active': total_active_members
        }

    return {
        'approved': False,
        'current_percent': current_percent,
        'required_percent': rule_version.approval_threshold_percent,
        'approved_votes': approved_votes_count,
        'total_active': total_active_members
    }
