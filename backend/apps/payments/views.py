from decimal import Decimal
from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Payment, GroupPaymentDestination
from .serializers import (
    PaymentSerializer, CashReceiptCreateSerializer, BankTransferSubmitSerializer,
    ReconciliationDecisionSerializer, GroupPaymentDestinationSerializer
)
from .services import (
    initiate_digital_payment, process_provider_webhook,
    record_cash_receipt, confirm_cash_receipt,
    submit_bank_transfer, reconcile_bank_transfer
)
from apps.contributions.models import ContributionObligation
from apps.groups.models import EqubGroup
from apps.authorization.services import has_group_permission
from apps.audit_app.services import log_audit_event

class DigitalPaymentInitiateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, obligation_id):
        try:
            obligation = ContributionObligation.objects.get(id=obligation_id)
        except (ContributionObligation.DoesNotExist, ValueError):
            raise ValidationError("Contribution obligation not found.")

        # CHAPA is the primary payment gateway
        provider_name = request.data.get('provider_name') or 'CHAPA'
        idempotency_key = request.headers.get('Idempotency-Key') or request.data.get('idempotency_key')

        result = initiate_digital_payment(
            obligation=obligation,
            payer=request.user,
            provider_name=provider_name,
            idempotency_key=idempotency_key
        )
        log_audit_event(
            action="DIGITAL_PAYMENT_INITIATED",
            actor=request.user,
            group=obligation.group,
            target_model="PaymentAttempt",
            target_id=result.get('attempt_id'),
            details={"provider": provider_name, "amount": str(obligation.remaining_amount)},
            request=request
        )
        return Response(result, status=status.HTTP_201_CREATED)


class CashReceiptRecordView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        serializer = CashReceiptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            obligation = ContributionObligation.objects.get(id=data['obligation_id'], group=group)
        except ContributionObligation.DoesNotExist:
            raise ValidationError("Obligation does not belong to this group.")

        evidence_file = request.FILES.get('evidence_file')

        payment = record_cash_receipt(
            obligation=obligation,
            amount=data['amount'],
            treasurer_user=request.user,
            receipt_number=data.get('receipt_number'),
            notes=data.get('notes', ''),
            evidence_file=evidence_file
        )

        log_audit_event(
            action="CASH_RECEIPT_RECORDED",
            actor=request.user,
            group=group,
            target_model="Payment",
            target_id=payment.id,
            details={"receipt_number": payment.receipt_number, "amount": str(payment.amount), "status": payment.status},
            request=request
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class CashReceiptConfirmView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id)
        except (Payment.DoesNotExist, ValueError):
            raise ValidationError("Payment record not found.")

        notes = request.data.get('notes', '')
        confirmed_payment = confirm_cash_receipt(payment, request.user, notes)

        log_audit_event(
            action="CASH_RECEIPT_CONFIRMED",
            actor=request.user,
            group=payment.group,
            target_model="Payment",
            target_id=payment.id,
            details={"receipt_number": payment.receipt_number},
            request=request
        )

        return Response(PaymentSerializer(confirmed_payment).data)


class BankTransferSubmitView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, obligation_id):
        try:
            obligation = ContributionObligation.objects.get(id=obligation_id)
        except (ContributionObligation.DoesNotExist, ValueError):
            raise ValidationError("Contribution obligation not found.")

        payload = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if 'obligation_id' not in payload:
            payload['obligation_id'] = str(obligation_id)
        if 'amount' not in payload:
            payload['amount'] = str(obligation.remaining_amount)

        serializer = BankTransferSubmitSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        evidence_file = request.FILES.get('evidence_file')

        payment = submit_bank_transfer(
            obligation=obligation,
            member_user=request.user,
            transfer_reference=data['transfer_reference'],
            amount=data['amount'],
            evidence_file=evidence_file,
            notes=data.get('notes', '')
        )

        log_audit_event(
            action="TRANSFER_EVIDENCE_SUBMITTED",
            actor=request.user,
            group=obligation.group,
            target_model="Payment",
            target_id=payment.id,
            details={"reference": payment.transfer_reference, "amount": str(payment.amount)},
            request=request
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class BankTransferReconcileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id)
        except (Payment.DoesNotExist, ValueError):
            raise ValidationError("Payment record not found.")

        serializer = ReconciliationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data['decision']
        notes = serializer.validated_data.get('notes', '')

        reconciled = reconcile_bank_transfer(payment, request.user, decision, notes)

        log_audit_event(
            action=f"TRANSFER_RECONCILED_{decision}",
            actor=request.user,
            group=payment.group,
            target_model="Payment",
            target_id=payment.id,
            details={"decision": decision, "reference": payment.transfer_reference},
            request=request
        )

        return Response(PaymentSerializer(reconciled).data)


class ProviderWebhookView(views.APIView):
    """
    Secure Chapa and Digital Provider Webhook receiver.
    Validates cryptographic signature (x-chapa-signature) and idempotently processes payment notifications.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider='chapa'):
        raw_body = request.body
        signature = (
            request.headers.get('x-chapa-signature') or
            request.headers.get('Chapa-Signature') or
            request.headers.get('X-Signature') or
            request.META.get('HTTP_X_CHAPA_SIGNATURE') or
            request.META.get('HTTP_X_SIGNATURE', '')
        )
        payload = request.data

        result = process_provider_webhook(
            provider_name=provider.upper(),
            raw_payload=payload,
            raw_body_bytes=raw_body,
            signature=signature
        )

        log_audit_event(
            action="PROVIDER_WEBHOOK_PROCESSED",
            details={"provider": provider, "result": result},
            request=request
        )

        return Response(result, status=status.HTTP_200_OK)


class ChapaPaymentVerifyView(views.APIView):
    """
    POST /api/v1/payments/chapa/verify/
    Direct server-side verification endpoint for Chapa payments.
    Handles both Member Equb Contributions and Organizer Subscriptions.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_tx_ref = request.data.get('tx_ref')
        tx_ref = str(raw_tx_ref or '').strip()

        # Clean URL parameters or encoding artifacts if present
        if '&' in tx_ref:
            tx_ref = tx_ref.split('&')[0]
        if '?' in tx_ref:
            tx_ref = tx_ref.split('?')[0]
        tx_ref = tx_ref.strip()

        if not tx_ref:
            return Response({
                "status": "FAILED",
                "message": "Transaction reference 'tx_ref' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if reference is for an Organizer Subscription
            if tx_ref.startswith('SUB-ORG-') or 'SUB-' in tx_ref:
                from apps.subscriptions.services import verify_chapa_subscription_payment
                result = verify_chapa_subscription_payment(tx_ref, organizer=request.user)
                return Response(result, status=status.HTTP_200_OK)
            else:
                from apps.payments.services import verify_chapa_contribution_payment
                result = verify_chapa_contribution_payment(tx_ref, payer=request.user)
                return Response(result, status=status.HTTP_200_OK)
        except ValidationError as e:
            detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(detail, dict):
                detail = next(iter(detail.values()))
            if isinstance(detail, list):
                detail = detail[0]
            return Response({
                "status": "FAILED",
                "message": str(detail)
            }, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({
                "status": "FORBIDDEN",
                "message": str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Chapa verify endpoint error for %s: %s", tx_ref, e, exc_info=True)
            return Response({
                "status": "FAILED",
                "message": f"Verification error: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)


class GroupPaymentsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        if not request.user.is_platform_admin and not group.memberships.filter(user=request.user).exists():
            raise PermissionDenied("You must belong to this group to view payments.")

        qs = Payment.objects.filter(group=group).select_related(
            'group', 'obligation', 'payer', 'cash_receiver', 'cash_confirmed_by', 'verified_by'
        ).order_by('-created_at')

        method = request.query_params.get('method')
        if method:
            qs = qs.filter(payment_method=method.upper())

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())

        # Ordinary members see only their payments unless they have financial viewing role
        is_staff_or_admin = (
            request.user.is_platform_admin or
            has_group_permission(request.user, group, 'payments:reconcile') or
            has_group_permission(request.user, group, 'group:view_reports')
        )
        if not is_staff_or_admin:
            qs = qs.filter(payer=request.user)

        serializer = PaymentSerializer(qs, many=True)
        return Response(serializer.data)


class MemberReceiptsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Payment.objects.filter(
            payer=request.user
        ).select_related('group', 'obligation', 'payer', 'verified_by').order_by('-created_at')

        serializer = PaymentSerializer(qs, many=True)
        return Response(serializer.data)


class GroupPaymentDestinationsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        destinations = GroupPaymentDestination.objects.filter(group=group, is_active=True)
        serializer = GroupPaymentDestinationSerializer(destinations, many=True)
        return Response(serializer.data)

    def post(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        if not has_group_permission(request.user, group, 'group:manage'):
            from apps.audit_app.security_monitor import record_and_block_security_violation
            record_and_block_security_violation(
                request=request,
                attempted_operation="UNAUTHORIZED_PAYMENT_DESTINATION_CHANGE",
                affected_resource=f"Group:{group.id}",
                security_rule_triggered="RULE-FIN-04: Unauthorized attempt to alter group payment destination.",
                risk_level="HIGH",
                group=group,
                details=request.data
            )

        provider_or_bank = request.data.get('provider_or_bank', '').strip()
        account_name = request.data.get('account_name', '').strip()
        account_number = request.data.get('account_number', '').strip()
        branch_or_details = request.data.get('branch_or_details', '').strip()
        transfer_instructions = request.data.get('transfer_instructions', '').strip()

        if not provider_or_bank or not account_name or not account_number:
            raise ValidationError("Provider/bank, account name, and account number are required.")

        destination = GroupPaymentDestination.objects.create(
            group=group,
            provider_or_bank=provider_or_bank,
            account_name=account_name,
            account_number=account_number,
            branch_or_details=branch_or_details,
            transfer_instructions=transfer_instructions,
            is_verified=False
        )

        log_audit_event(
            action="GROUP_PAYMENT_DESTINATION_SUBMITTED",
            actor=request.user,
            group=group,
            target_model="GroupPaymentDestination",
            target_id=destination.id,
            details={"bank": provider_or_bank, "account": account_number},
            request=request
        )

        return Response(GroupPaymentDestinationSerializer(destination).data, status=status.HTTP_201_CREATED)


class ChapaSupportedBanksView(views.APIView):
    """
    GET /api/v1/payments/banks/
    Returns supported Ethiopian commercial banks and mobile wallets from Chapa.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.payments.chapa import chapa_client
        banks = chapa_client.get_supported_banks()
        return Response({"banks": banks}, status=status.HTTP_200_OK)


class GroupChapaSubaccountView(views.APIView):
    """
    GET, POST /api/v1/groups/<uuid:group_id>/subaccount/
    Manages Chapa Subaccount for automatic member contribution routing directly to the group's account.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        return Response({
            "group_id": str(group.id),
            "group_name": group.name,
            "chapa_subaccount_id": getattr(group, 'chapa_subaccount_id', '') or '',
            "has_subaccount": bool(getattr(group, 'chapa_subaccount_id', '')),
            "bank_code": getattr(group, 'bank_code', ''),
            "bank_name": getattr(group, 'bank_name', ''),
            "bank_account_name": getattr(group, 'bank_account_name', ''),
            "bank_account_number": getattr(group, 'bank_account_number', '')
        }, status=status.HTTP_200_OK)

    def post(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        # Check permission: Only group organizer or treasurer can configure subaccount
        from apps.authorization.services import has_group_permission
        if not (request.user.is_platform_admin or group.organizer_id == request.user.id or has_group_permission(request.user, group, 'group:manage')):
            raise PermissionDenied("Only the group organizer or treasurer can link a Chapa Subaccount.")

        bank_code = str(request.data.get('bank_code', '')).strip()
        bank_name = str(request.data.get('bank_name', '')).strip()
        account_name = str(request.data.get('account_name', '')).strip()
        account_number = str(request.data.get('account_number', '')).strip()
        business_name = str(request.data.get('business_name', '')).strip() or group.name

        if not bank_code or not account_name or not account_number:
            raise ValidationError({
                "detail": "bank_code, account_name, and account_number are required to create a Chapa subaccount."
            })

        from apps.payments.chapa import chapa_client
        res = chapa_client.create_subaccount(
            business_name=business_name,
            account_name=account_name,
            bank_code=bank_code,
            account_number=account_number,
            split_value=0.0,
            split_type="percentage"
        )

        subaccount_id = res.get('subaccount_id')
        if not subaccount_id:
            raise ValidationError("Chapa did not return a valid subaccount ID.")

        # Save to group
        group.chapa_subaccount_id = subaccount_id
        group.bank_code = bank_code
        group.bank_name = bank_name
        group.bank_account_name = account_name
        group.bank_account_number = account_number
        group.save(update_fields=['chapa_subaccount_id', 'bank_code', 'bank_name', 'bank_account_name', 'bank_account_number'])

        # Also register or update GroupPaymentDestination
        dest, _ = GroupPaymentDestination.objects.get_or_create(
            group=group,
            account_number=account_number,
            defaults={
                'provider_or_bank': bank_name or f"Bank {bank_code}",
                'account_name': account_name,
                'bank_code': bank_code,
                'chapa_subaccount_id': subaccount_id,
                'is_verified': True,
                'verified_by': request.user
            }
        )
        if not dest.chapa_subaccount_id:
            dest.chapa_subaccount_id = subaccount_id
            dest.bank_code = bank_code
            dest.save(update_fields=['chapa_subaccount_id', 'bank_code'])

        log_audit_event(
            action="GROUP_CHAPA_SUBACCOUNT_LINKED",
            actor=request.user,
            group=group,
            target_model="EqubGroup",
            target_id=group.id,
            details={
                "subaccount_id": subaccount_id,
                "bank": bank_name,
                "account_number": account_number,
                "is_sandbox": res.get('is_sandbox', False)
            },
            request=request
        )

        return Response({
            "success": True,
            "message": f"Chapa Subaccount connected successfully to {group.name}!",
            "subaccount_id": subaccount_id,
            "is_sandbox": res.get('is_sandbox', False),
            "bank_name": bank_name,
            "account_number": account_number
        }, status=status.HTTP_201_CREATED)

