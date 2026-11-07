import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import SaasPlan, OrganizerSubscription, SubscriptionInvoice
from .serializers import SaasPlanSerializer, OrganizerSubscriptionSerializer, SubscriptionInvoiceSerializer
from .services import get_or_create_active_subscription
from apps.groups.models import EqubGroup
from apps.audit_app.services import log_audit_event

class PlanListView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = SaasPlan.objects.filter(is_active=True).order_by('price_etb')
        return Response(SaasPlanSerializer(plans, many=True).data)

    def post(self, request):
        # Only Platform Super Admin can create plans
        if not request.user.is_authenticated or not request.user.is_platform_admin:
            raise PermissionDenied("Only Platform Super Admins can configure SaaS subscription plans.")

        serializer = SaasPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()
        log_audit_event(
            action="SAAS_PLAN_CREATED",
            actor=request.user,
            target_model="SaasPlan",
            target_id=plan.id,
            details={"code": plan.code, "price_etb": str(plan.price_etb)},
            request=request
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CurrentSubscriptionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub = get_or_create_active_subscription(request.user)
        active_groups_count = EqubGroup.objects.filter(
            organizer=request.user,
            status__in=[EqubGroup.GroupStatus.ACTIVE, EqubGroup.GroupStatus.PENDING_APPROVAL, EqubGroup.GroupStatus.DRAFT]
        ).count()

        return Response({
            'subscription': OrganizerSubscriptionSerializer(sub).data,
            'usage': {
                'active_groups_count': active_groups_count,
                'max_active_groups': sub.plan.max_active_groups,
                'remaining_capacity': max(0, sub.plan.max_active_groups - active_groups_count)
            }
        })


class SubscribePlanView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_code = request.data.get('plan_code')
        try:
            plan = SaasPlan.objects.get(code=plan_code, is_active=True)
        except SaasPlan.DoesNotExist:
            raise ValidationError("Specified SaaS plan does not exist.")

        user = request.user
        sub = get_or_create_active_subscription(user)
        sub.plan = plan
        sub.expires_at = timezone.now() + timedelta(days=30 if plan.billing_cycle == 'MONTHLY' else 365)
        sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
        sub.save()

        # Generate invoice if paid plan
        invoice = None
        if plan.price_etb > 0:
            inv_num = f"INV-{uuid.uuid4().hex[:8].upper()}"
            invoice = SubscriptionInvoice.objects.create(
                subscription=sub,
                invoice_number=inv_num,
                amount_etb=plan.price_etb,
                due_date=timezone.now().date() + timedelta(days=7),
                status=SubscriptionInvoice.InvoiceStatus.PAID, # Simulated immediate activation for test tier
                paid_at=timezone.now(),
                payment_reference="SUBS-TEST-CONFIRMED"
            )

        log_audit_event(
            action="SUBSCRIPTION_UPDATED",
            actor=user,
            target_model="OrganizerSubscription",
            target_id=sub.id,
            details={"plan": plan.code, "price_etb": str(plan.price_etb)},
            request=request
        )

        return Response({
            'success': True,
            'message': f"Successfully subscribed to {plan.name}.",
            'subscription': OrganizerSubscriptionSerializer(sub).data
        })


class SubscriptionInvoicesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_platform_admin:
            invoices = SubscriptionInvoice.objects.all().select_related('subscription__organizer', 'subscription__plan')
        else:
            invoices = SubscriptionInvoice.objects.filter(
                subscription__organizer=request.user
            ).select_related('subscription__plan')

        serializer = SubscriptionInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
