import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

class RuleVersion(models.Model):
    class RuleStatus(models.TextChoices):
        PROPOSED = 'PROPOSED', _('Proposed')
        APPROVED = 'APPROVED', _('Approved')
        SUPERSEDED = 'SUPERSEDED', _('Superseded')
        REJECTED = 'REJECTED', _('Rejected')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='rule_versions'
    )
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    terms_text = models.TextField(help_text=_("Full contractual Equb terms and conditions for this version."))
    contribution_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('1000.00'))
    contribution_frequency = models.CharField(max_length=20, default='MONTHLY')
    payout_method = models.CharField(max_length=25, default='ROTATION_ORDER')
    payout_order_manifest = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Ordered list of membership/user IDs specifying rotation sequence.")
    )
    approval_threshold_percent = models.PositiveIntegerField(
        default=100,
        help_text=_("Required percentage of active members who must approve.")
    )
    status = models.CharField(
        max_length=20,
        choices=RuleStatus.choices,
        default=RuleStatus.PROPOSED,
        db_index=True
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='proposed_rules'
    )
    proposed_at = models.DateTimeField(auto_now_add=True)
    effective_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rule_versions'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'version_number'],
                name='unique_rule_version_per_group'
            )
        ]
        ordering = ['group', '-version_number']

    def __str__(self):
        return f"{self.group.name} - v{self.version_number} [{self.status}]"


class RuleApproval(models.Model):
    class Decision(models.TextChoices):
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_version = models.ForeignKey(
        RuleVersion,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    membership = models.ForeignKey(
        'groups.GroupMembership',
        on_delete=models.CASCADE,
        related_name='rule_votes'
    )
    decision = models.CharField(
        max_length=15,
        choices=Decision.choices,
        default=Decision.APPROVED
    )
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rule_approvals'
        constraints = [
            models.UniqueConstraint(
                fields=['rule_version', 'membership'],
                name='unique_rule_approval_vote_per_member'
            )
        ]

    def __str__(self):
        return f"{self.membership.user.full_name} -> {self.decision} on v{self.rule_version.version_number}"
