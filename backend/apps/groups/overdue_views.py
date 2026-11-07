from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.groups.models import (
    EqubGroup,
    GroupMembership,
    OverdueCase,
    PaymentAgreement,
    PaymentInstallment,
    MembershipReview,
    TreasurerAssignmentRecord,
)
from apps.groups.serializers import (
    OverdueCaseSerializer,
    PaymentAgreementSerializer,
    PaymentInstallmentSerializer,
    MembershipReviewSerializer,
)
from apps.groups.overdue_services import (
    evaluate_group_deadlines_and_grace_periods,
    apply_overdue_resolution,
    member_respond_to_payment_agreement,
    record_membership_review_decision,
)

User = get_user_model()


class OrganizerOverdueCasesView(APIView):
    """
    GET: Lists overdue cases for an Equb group.
    POST: Evaluates deadlines & refreshes overdue cases for group.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        if group.organizer_id != request.user.id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        cases = OverdueCase.objects.filter(group=group).select_related(
            'membership__user', 'period', 'resolved_by'
        ).prefetch_related('payment_agreements__installments', 'membership_reviews')

        return Response(OverdueCaseSerializer(cases, many=True).data)

    def post(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        if group.organizer_id != request.user.id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        created_cases = evaluate_group_deadlines_and_grace_periods(group)
        return Response({
            "message": f"Evaluated deadlines for {group.name}. {len(created_cases)} new cases opened.",
            "count": len(created_cases)
        }, status=status.HTTP_200_OK)


class OrganizerResolveOverdueCaseView(APIView):
    """
    POST: Applies Dropdown 2 (Overdue Resolution) to an OverdueCase:
    - resolution_choice: 'CONTINUE_WAITING', 'PAYMENT_AGREEMENT', or 'MEMBERSHIP_REVIEW'
    - data: resolution payload
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id, case_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        if group.organizer_id != request.user.id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        case = get_object_or_404(OverdueCase, id=case_id, group=group)
        resolution_choice = request.data.get('resolution_choice')

        if resolution_choice not in [c[0] for c in OverdueCase.ResolutionChoice.choices]:
            return Response({
                "error": f"Invalid resolution_choice. Must be one of: {[c[0] for c in OverdueCase.ResolutionChoice.choices]}"
            }, status=status.HTTP_400_BAD_REQUEST)

        success, message, result = apply_overdue_resolution(
            overdue_case=case,
            resolution_choice=resolution_choice,
            data=request.data,
            organizer_user=request.user
        )

        if not success:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "case": OverdueCaseSerializer(case).data
        }, status=status.HTTP_200_OK)


class OrganizerRecordReviewDecisionView(APIView):
    """
    POST: Records final decision on a MembershipReview (Option C):
    - decision: 'RETAIN_WITH_WARNING', 'PENALTY_FORGIVENESS', 'REPLACE_MEMBERSHIP', 'TERMINATE_AND_COLLECT'
    - replacement_user_id (optional, required if REPLACE_MEMBERSHIP)
    - notes (optional)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id, review_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        if group.organizer_id != request.user.id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        review = get_object_or_404(MembershipReview, id=review_id, group=group)
        decision = request.data.get('decision')

        if decision not in [d[0] for d in MembershipReview.ReviewDecision.choices]:
            return Response({
                "error": f"Invalid decision. Must be one of: {[d[0] for d in MembershipReview.ReviewDecision.choices]}"
            }, status=status.HTTP_400_BAD_REQUEST)

        replacement_user = None
        replacement_user_id = request.data.get('replacement_user_id')
        if decision == MembershipReview.ReviewDecision.REPLACE_MEMBERSHIP:
            if not replacement_user_id:
                return Response({"error": "replacement_user_id is required when selecting REPLACE_MEMBERSHIP."}, status=status.HTTP_400_BAD_REQUEST)
            replacement_user = get_object_or_404(User, id=replacement_user_id)

        notes = request.data.get('notes', '')
        success, message = record_membership_review_decision(
            review=review,
            decision=decision,
            organizer_user=request.user,
            replacement_user=replacement_user,
            notes=notes
        )

        if not success:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "review": MembershipReviewSerializer(review).data
        }, status=status.HTTP_200_OK)


class MemberPaymentAgreementsView(APIView):
    """
    GET: List all payment agreements involving the authenticated member.
    POST: Member accepts or rejects a payment agreement.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agreements = PaymentAgreement.objects.filter(
            membership__user=request.user
        ).select_related('group', 'overdue_case').prefetch_related('installments')

        return Response(PaymentAgreementSerializer(agreements, many=True).data)

    def post(self, request, agreement_id):
        agreement = get_object_or_404(PaymentAgreement, id=agreement_id, membership__user=request.user)
        accept = request.data.get('accept', True)
        notes = request.data.get('notes', '')

        success, message = member_respond_to_payment_agreement(
            agreement=agreement,
            member_user=request.user,
            accept=accept,
            notes=notes
        )

        if not success:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "agreement": PaymentAgreementSerializer(agreement).data
        }, status=status.HTTP_200_OK)


class TreasurerOverdueMonitoringView(APIView):
    """
    GET: Treasurer financial monitoring of overdue cases, agreements, and installments.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        # Check if user is treasurer
        is_treasurer = TreasurerAssignmentRecord.objects.filter(
            group=group, user=request.user, is_active=True
        ).exists() or group.organizer_id == request.user.id or request.user.is_staff

        if not is_treasurer:
            return Response({"error": "Unauthorized: Only active group treasurer or organizer may access this monitoring view."}, status=status.HTTP_403_FORBIDDEN)

        agreements = PaymentAgreement.objects.filter(group=group).select_related(
            'membership__user'
        ).prefetch_related('installments')

        overdue_cases = OverdueCase.objects.filter(group=group).select_related(
            'membership__user', 'period'
        )

        return Response({
            "group": {"id": str(group.id), "name": group.name},
            "agreements": PaymentAgreementSerializer(agreements, many=True).data,
            "overdue_cases": OverdueCaseSerializer(overdue_cases, many=True).data
        })

