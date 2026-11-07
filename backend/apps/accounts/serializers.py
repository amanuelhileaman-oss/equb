from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, OrganizerProfile

class UserSerializer(serializers.ModelSerializer):
    is_organizer = serializers.SerializerMethodField()
    is_treasurer = serializers.SerializerMethodField()
    has_organizer_profile = serializers.SerializerMethodField()
    primary_role = serializers.SerializerMethodField()
    organizer_profile_summary = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'full_name', 'avatar',
            'preferred_language', 'is_email_verified', 'is_phone_verified',
            'account_status', 'is_platform_admin', 'mfa_enabled', 'created_at',
            'is_organizer', 'is_treasurer', 'has_organizer_profile',
            'primary_role', 'organizer_profile_summary'
        ]
        read_only_fields = [
            'id', 'is_platform_admin', 'account_status', 'is_email_verified',
            'is_phone_verified', 'mfa_enabled', 'created_at',
            'is_organizer', 'is_treasurer', 'has_organizer_profile',
            'primary_role', 'organizer_profile_summary'
        ]

    def get_is_organizer(self, obj):
        if getattr(obj, 'is_platform_admin', False):
            return False
        if hasattr(obj, 'organizer_profile'):
            return True
        from apps.groups.models import EqubGroup, GroupMembership
        if EqubGroup.objects.filter(organizer=obj).exists():
            return True
        return GroupMembership.objects.filter(
            user=obj,
            role_assignments__role__code='GROUP_ORGANIZER'
        ).exists()

    def get_is_treasurer(self, obj):
        if getattr(obj, 'is_platform_admin', False):
            return False
        from apps.groups.models import GroupMembership
        return GroupMembership.objects.filter(
            user=obj,
            role_assignments__role__code='GROUP_TREASURER'
        ).exists()

    def get_has_organizer_profile(self, obj):
        return hasattr(obj, 'organizer_profile')

    def get_primary_role(self, obj):
        if getattr(obj, 'is_platform_admin', False):
            return 'SUPER_ADMIN'
        if self.get_is_organizer(obj):
            return 'ORGANIZER'
        if self.get_is_treasurer(obj):
            return 'TREASURER'
        return 'MEMBER'

    def get_organizer_profile_summary(self, obj):
        if hasattr(obj, 'organizer_profile'):
            prof = obj.organizer_profile
            from decimal import Decimal
            is_starter = bool(
                (prof.assigned_plan and (prof.assigned_plan.code == 'STARTER_EQUB' or prof.assigned_plan.price_etb == Decimal('0.00'))) or
                prof.subscription_amount == Decimal('0.00') or
                prof.payment_status == prof.PaymentStatus.NOT_REQUIRED
            )
            is_payment_blocked = bool(
                not is_starter and
                prof.payment_status not in [prof.PaymentStatus.PAYMENT_CONFIRMED, prof.PaymentStatus.NOT_REQUIRED]
            )
            return {
                'business_name': prof.business_name,
                'business_type': prof.business_type,
                'verification_status': prof.verification_status,
                'payment_status': prof.payment_status,
                'license_number': prof.license_number,
                'plan_name': prof.assigned_plan.name if prof.assigned_plan else None,
                'plan_code': prof.assigned_plan.code if prof.assigned_plan else None,
                'subscription_amount': str(prof.subscription_amount),
                'is_starter': is_starter,
                'is_payment_blocked': is_payment_blocked,
                'is_activated': prof.is_activated
            }
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'phone_number', 'full_name', 'preferred_language', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        # Always safe default: Normal user, never platform admin from public registration!
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number'),
            full_name=validated_data['full_name'],
            preferred_language=validated_data.get('preferred_language', 'en'),
            is_platform_admin=False
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    mfa_code = serializers.CharField(required=False, allow_blank=True, max_length=6)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')
        mfa_code = attrs.get('mfa_code', '').strip()

        # Check user existence for rate limiting
        user_candidate = User.objects.filter(email=email).first()
        if user_candidate and user_candidate.account_status == User.AccountStatus.SUSPENDED:
            raise serializers.ValidationError("This account has been suspended. Please contact the platform administrator.")

        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active or user.account_status == User.AccountStatus.SUSPENDED:
            raise serializers.ValidationError("This account has been suspended or deactivated. Contact platform administrator.")
        
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs


class MfaVerifySerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)
    secret = serializers.CharField(required=False, allow_blank=True)


class OrganizerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    plan_name = serializers.CharField(source='assigned_plan.name', read_only=True)

    class Meta:
        model = OrganizerProfile
        fields = [
            'id', 'user', 'full_legal_name', 'national_id_or_passport',
            'business_name', 'business_address', 'business_type',
            'registration_number', 'license_number', 'license_document',
            'license_issue_date', 'license_expiry_date', 'other_documents',
            'verification_status', 'reviewed_by', 'reviewed_at',
            'decision_reason', 'verification_notes', 'terms_accepted',
            'conduct_rules_accepted', 'non_interference_agreement',
            'assigned_plan', 'plan_name', 'subscription_amount',
            'billing_period', 'payment_status', 'is_activated',
            'temporary_password_set', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'verification_status', 'reviewed_by',
            'reviewed_at', 'payment_status', 'created_at', 'updated_at'
        ]

