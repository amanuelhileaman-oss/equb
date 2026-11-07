from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db.models import Max
from .models import RuleVersion, RuleApproval
from .serializers import RuleVersionSerializer, RuleProposalSerializer
from .services import evaluate_rule_approvals
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.services import has_group_permission
from apps.audit_app.services import log_audit_event

class RuleListProposeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_group(self, group_id):
        try:
            return EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

    def get(self, request, group_id):
        group = self.get_group(group_id)
        # Check membership
        if not request.user.is_platform_admin and not group.memberships.filter(user=request.user).exists():
            raise PermissionDenied("You must belong to this group to inspect its rules.")

        versions = RuleVersion.objects.filter(group=group).order_by('-version_number')
        return Response(RuleVersionSerializer(versions, many=True, context={'request': request}).data)

    def post(self, request, group_id):
        group = self.get_group(group_id)
        if not has_group_permission(request.user, group, 'group:propose_rules'):
            raise PermissionDenied("You do not have permission to propose rules in this group.")

        serializer = RuleProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_max = RuleVersion.objects.filter(group=group).aggregate(Max('version_number'))['version_number__max'] or 0
        next_version = current_max + 1

        rule_version = RuleVersion.objects.create(
            group=group,
            version_number=next_version,
            proposed_by=request.user,
            status=RuleVersion.RuleStatus.PROPOSED,
            **serializer.validated_data
        )

        # Proposer automatically votes APPROVED
        membership = group.memberships.filter(user=request.user).first()
        if membership:
            RuleApproval.objects.create(
                rule_version=rule_version,
                membership=membership,
                decision=RuleApproval.Decision.APPROVED,
                comment="Proposer automatic acceptance."
            )
            evaluate_rule_approvals(rule_version)

        log_audit_event(
            action="RULE_PROPOSED",
            actor=request.user,
            group=group,
            target_id=rule_version.id,
            details={"version": next_version, "title": rule_version.title},
            request=request
        )

        return Response(RuleVersionSerializer(rule_version, context={'request': request}).data, status=status.HTTP_201_CREATED)


class RuleVoteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, rule_id):
        try:
            rule_version = RuleVersion.objects.get(id=rule_id)
        except (RuleVersion.DoesNotExist, ValueError):
            raise ValidationError("Rule version not found.")

        group = rule_version.group
        membership = group.memberships.filter(user=request.user, status=GroupMembership.MembershipStatus.ACTIVE).first()
        if not membership:
            raise PermissionDenied("Only active group members can vote on proposed rules.")

        if rule_version.status != RuleVersion.RuleStatus.PROPOSED:
            raise ValidationError(f"This rule version is already {rule_version.status.lower()} and no longer accepts votes.")

        decision = request.data.get('decision', 'APPROVED').upper()
        if decision not in ['APPROVED', 'REJECTED']:
            raise ValidationError("Decision must be either 'APPROVED' or 'REJECTED'.")

        comment = request.data.get('comment', '').strip()

        vote, created = RuleApproval.objects.get_or_create(
            rule_version=rule_version,
            membership=membership,
            defaults={'decision': decision, 'comment': comment}
        )
        if not created:
            vote.decision = decision
            vote.comment = comment
            vote.save()

        eval_result = evaluate_rule_approvals(rule_version)
        log_audit_event(
            action="RULE_VOTE_CAST",
            actor=request.user,
            group=group,
            target_id=rule_version.id,
            details={"decision": decision, "approved": eval_result.get('approved')},
            request=request
        )

        return Response({
            'success': True,
            'message': f"Vote recorded as {decision}.",
            'evaluation': eval_result
        })
