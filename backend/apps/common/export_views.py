import csv
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import views, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from apps.groups.models import EqubGroup, GroupMembership
from apps.ledger.models import LedgerEntry
from apps.contributions.models import ContributionObligation

class GroupLedgerExportCSVView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except EqubGroup.DoesNotExist:
            raise NotFound("Equb group not found.")

        # Ensure user is a member or platform admin
        if not request.user.is_platform_admin:
            membership = GroupMembership.objects.filter(
                group=group,
                user=request.user,
                status=GroupMembership.MembershipStatus.ACTIVE
            ).first()
            if not membership:
                raise PermissionDenied("You must be an active member of this Equb to export financial records.")

        entries = LedgerEntry.objects.filter(group=group).order_by('posted_at')

        filename = f"equb_ledger_{group.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            "Entry ID",
            "Posted At",
            "Direction",
            "Entry Type",
            "Amount (ETB)",
            "Running Balance (ETB)",
            "Receipt/Ref",
            "Reason"
        ])

        running_balance = Decimal('0.00')
        for entry in entries:
            if entry.direction == 'CREDIT':
                running_balance += entry.amount
            else:
                running_balance -= entry.amount

            ref = ""
            if entry.payment:
                ref = entry.payment.receipt_number
            elif entry.payout:
                ref = str(entry.payout.id)

            writer.writerow([
                str(entry.id),
                entry.posted_at.strftime('%Y-%m-%d %H:%M:%S'),
                entry.direction,
                entry.entry_type,
                str(entry.amount),
                str(running_balance),
                ref,
                entry.reason
            ])

        return response


class GroupObligationsExportCSVView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except EqubGroup.DoesNotExist:
            raise NotFound("Equb group not found.")

        # Ensure user is a member or platform admin
        if not request.user.is_platform_admin:
            membership = GroupMembership.objects.filter(
                group=group,
                user=request.user,
                status=GroupMembership.MembershipStatus.ACTIVE
            ).first()
            if not membership:
                raise PermissionDenied("You must be an active member of this Equb to export obligations roster.")

        obligations = ContributionObligation.objects.filter(group=group).select_related('period', 'membership__user').order_by('period__period_number', 'membership__user__full_name')

        filename = f"equb_obligations_{group.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            "Period #",
            "Due Date",
            "Member Name",
            "Member Email",
            "Expected (ETB)",
            "Paid (ETB)",
            "Remaining (ETB)",
            "Currency",
            "Status"
        ])

        for ob in obligations:
            writer.writerow([
                ob.period.period_number if ob.period else "N/A",
                str(ob.due_date),
                ob.membership.user.full_name,
                ob.membership.user.email,
                str(ob.expected_amount),
                str(ob.amount_paid),
                str(ob.remaining_amount),
                ob.currency,
                ob.status
            ])

        return response
