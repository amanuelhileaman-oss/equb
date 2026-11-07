from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Payout, PayoutApproval, PayoutStatus, PayoutSettlementStatus
from apps.ledger.services import get_group_available_funds, record_payout_ledger
from apps.authorization.services import has_group_permission

@transaction.atomic
def request_payout(group, recipient_membership, requesting_user, amount: Decimal = None, period=None, notes="") -> Payout:
    """
    Initiates a payout workflow after verifying group membership, permissions,
    and verified available group funds.
    """
    if not has_group_permission(requesting_user, group, 'payouts:request'):
        raise PermissionDenied("You do not have permission to request payouts for this group.")

    if recipient_membership.group_id != group.id:
        raise ValidationError("Recipient does not belong to this group.")

    if recipient_membership.status != recipient_membership.MembershipStatus.ACTIVE:
        raise ValidationError("Recipient membership is not currently active.")

    # Calculate expected payout amount if not specified: group contribution_amount * active members
    if amount is None or amount <= Decimal('0.00'):
        active_count = group.memberships.filter(status=recipient_membership.MembershipStatus.ACTIVE).count()
        amount = group.contribution_amount * active_count

    available_funds = get_group_available_funds(group)

    payout = Payout.objects.create(
        group=group,
        period=period,
        recipient_membership=recipient_membership,
        amount=amount,
        currency=group.currency,
        requesting_user=requesting_user,
        notes=notes
    )

    if available_funds < amount:
        payout.status = PayoutStatus.BLOCKED_INSUFFICIENT_FUNDS
        payout.blocking_reason = f"Available verified group balance is {available_funds} {group.currency}, which is less than requested payout of {amount} {group.currency}."
        payout.save(update_fields=['status', 'blocking_reason'])
    else:
        payout.status = PayoutStatus.PENDING_APPROVAL
        payout.save(update_fields=['status'])

    return payout


@transaction.atomic
def approve_payout(payout: Payout, approver_user, decision: str, reason: str = "") -> PayoutApproval:
    """
    Records an independent approval decision for a payout.
    Strictly enforces separation of duties: The requesting user cannot approve their own payout!
    """
    if not has_group_permission(approver_user, payout.group, 'payouts:approve'):
        from apps.audit_app.security_monitor import record_and_block_security_violation
        record_and_block_security_violation(
            request=None,
            target_user=approver_user,
            attempted_operation="UNAUTHORIZED_PAYOUT_APPROVAL_ATTEMPT",
            affected_resource=f"Payout:{payout.id}",
            security_rule_triggered="RULE-FIN-02: User lacks payouts:approve permission.",
            risk_level="HIGH",
            group=payout.group,
            details={"payout_id": str(payout.id), "amount": str(payout.amount)}
        )

    # Non-negotiable Separation of Duties
    if approver_user.id == payout.requesting_user_id:
        from apps.audit_app.security_monitor import record_and_block_security_violation
        record_and_block_security_violation(
            request=None,
            target_user=approver_user,
            attempted_operation="PAYOUT_SELF_APPROVAL_ATTEMPT",
            affected_resource=f"Payout:{payout.id}",
            security_rule_triggered="RULE-FIN-01: Prohibit self-approval on rotating fund payouts.",
            risk_level="HIGH",
            group=payout.group,
            details={"payout_id": str(payout.id), "amount": str(payout.amount)}
        )

    if payout.status != PayoutStatus.PENDING_APPROVAL:
        raise ValidationError(f"Payout cannot be approved from its current status '{payout.status}'.")

    approval, created = PayoutApproval.objects.get_or_create(
        payout=payout,
        approver=approver_user,
        defaults={'decision': decision, 'reason': reason}
    )
    if not created:
        approval.decision = decision
        approval.reason = reason
        approval.save()

    if decision == PayoutApproval.Decision.APPROVED:
        payout.status = PayoutStatus.APPROVED
    else:
        payout.status = PayoutStatus.FAILED
        payout.blocking_reason = f"Rejected by {approver_user.full_name}: {reason}"
    
    payout.save(update_fields=['status', 'blocking_reason', 'updated_at'])
    return approval


@transaction.atomic
def execute_payout(payout: Payout, executor_user, execution_reference: str, evidence_file=None, notes: str = "") -> Payout:
    """
    Executes and confirms an approved payout with verifiable execution references.
    Atomically posts a DEBIT ledger entry to preserve financial integrity.
    """
    if not has_group_permission(executor_user, payout.group, 'payouts:record_execution'):
        raise PermissionDenied("You do not have permission to record payout executions.")

    # Concurrency control & verification
    locked_payout = Payout.objects.select_for_update().get(id=payout.id)
    if locked_payout.status != PayoutStatus.APPROVED:
        raise ValidationError(f"Cannot execute payout: Status is '{locked_payout.status}', expected 'APPROVED'.")

    # Re-verify sufficient funds at moment of execution
    available = get_group_available_funds(locked_payout.group)
    if available < locked_payout.amount:
        locked_payout.status = PayoutStatus.BLOCKED_INSUFFICIENT_FUNDS
        locked_payout.blocking_reason = f"Insufficient funds at execution time: Available balance is {available} {locked_payout.currency}."
        locked_payout.save(update_fields=['status', 'blocking_reason', 'updated_at'])
        raise ValidationError(locked_payout.blocking_reason)

    locked_payout.status = PayoutStatus.COMPLETED
    locked_payout.settlement_status = PayoutSettlementStatus.SETTLED
    locked_payout.executed_by = executor_user
    locked_payout.executed_at = timezone.now()
    locked_payout.execution_reference = execution_reference
    if evidence_file:
        locked_payout.settlement_evidence_file = evidence_file
    if notes:
        locked_payout.notes = f"{locked_payout.notes}\nExecution note: {notes}".strip()
    
    locked_payout.save()

    # Append to immutable ledger atomically
    record_payout_ledger(locked_payout, posted_by=executor_user)

    return locked_payout
