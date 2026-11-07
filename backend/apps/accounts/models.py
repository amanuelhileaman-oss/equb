import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("An email address is required."))
        email = self.normalize_email(email).lower()
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('account_status', 'ACTIVE')
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_platform_admin', True)
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('account_status', 'ACTIVE')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        if extra_fields.get('is_platform_admin') is not True:
            raise ValueError(_('Superuser must have is_platform_admin=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', _('Pending Verification')
        SUSPENDED = 'SUSPENDED', _('Suspended')

    class PreferredLanguage(models.TextChoices):
        ENGLISH = 'en', _('English')
        AMHARIC = 'am', _('Amharic')
        OROMO = 'om', _('Oromo')
        TIGRINYA = 'ti', _('Tigrinya')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    phone_number = models.CharField(_('phone number'), max_length=25, unique=True, null=True, blank=True, db_index=True)
    full_name = models.CharField(_('full name'), max_length=150)
    preferred_language = models.CharField(
        max_length=5,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.ENGLISH
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    account_status = models.CharField(
        max_length=25,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        db_index=True
    )
    is_platform_admin = models.BooleanField(
        default=False,
        help_text=_('Designates whether this user has SaaS Platform Super Admin privileges.')
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    avatar = models.TextField(blank=True, default='', help_text=_('User profile photo as base64 data URL or image URL.'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    suspension_reason = models.TextField(blank=True)
    verification_notes = models.TextField(blank=True)

    # Security & Authentication Controls
    mfa_enabled = models.BooleanField(
        default=False,
        help_text=_('Designates whether two-factor/MFA authentication is active for this account.')
    )
    mfa_secret = models.CharField(max_length=64, blank=True)
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of consecutive failed login attempts.')
    )
    last_failed_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['email', 'account_status']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token_hash = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"ResetToken for {self.user.email} (used={self.is_used})"


class OrganizerProfile(models.Model):
    class BusinessType(models.TextChoices):
        SOLE_PROPRIETORSHIP = 'SOLE_PROPRIETORSHIP', _('Sole Proprietorship')
        PLC = 'PLC', _('Private Limited Company (PLC)')
        SHARE_COMPANY = 'SHARE_COMPANY', _('Share Company (S.C.)')
        SACCO = 'SACCO', _('Savings & Credit Cooperative (SACCO)')
        COOPERATIVE = 'COOPERATIVE', _('Cooperative Union')
        IDDIR = 'IDDIR', _('Traditional Iddir / Community Org')
        OTHER = 'OTHER', _('Other Organization')

    class VerificationStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', _('Pending Verification')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        ADDITIONAL_INFORMATION_REQUIRED = 'ADDITIONAL_INFORMATION_REQUIRED', _('Additional Information Required')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        EXPIRED = 'EXPIRED', _('Expired')

    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = 'NOT_REQUIRED', _('Not Required')
        PAYMENT_REQUIRED = 'PAYMENT_REQUIRED', _('Payment Required')
        PAYMENT_INITIATED = 'PAYMENT_INITIATED', _('Payment Initiated')
        PAYMENT_PENDING = 'PAYMENT_PENDING', _('Payment Pending')
        PAYMENT_CONFIRMED = 'PAYMENT_CONFIRMED', _('Payment Confirmed')
        PAYMENT_FAILED = 'PAYMENT_FAILED', _('Payment Failed')
        PAYMENT_EXPIRED = 'PAYMENT_EXPIRED', _('Payment Expired')
        PAYMENT_REVERSED = 'PAYMENT_REVERSED', _('Payment Reversed')
        PAYMENT_DISPUTED = 'PAYMENT_DISPUTED', _('Payment Disputed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='organizer_profile'
    )
    # Personal info
    full_legal_name = models.CharField(max_length=150, blank=True)
    national_id_or_passport = models.CharField(max_length=60, blank=True)

    # Business Information
    business_name = models.CharField(max_length=200)
    business_address = models.TextField(blank=True)
    business_type = models.CharField(
        max_length=50,
        choices=BusinessType.choices,
        default=BusinessType.SOLE_PROPRIETORSHIP
    )
    registration_number = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=100, blank=True, help_text=_('Market / Business License (Nigd Fikad) number.'))
    license_document = models.TextField(blank=True, help_text=_('Uploaded license file data or document reference.'))
    license_issue_date = models.DateField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    other_documents = models.JSONField(default=list, blank=True)

    # Verification & Legal Compliance
    verification_status = models.CharField(
        max_length=40,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING_VERIFICATION,
        db_index=True
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_organizers'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    verification_notes = models.TextField(blank=True)
    terms_accepted = models.BooleanField(default=False)
    conduct_rules_accepted = models.BooleanField(default=False)
    non_interference_agreement = models.BooleanField(
        default=False,
        help_text=_('Agreement not to interfere with or misuse group members rotating funds.')
    )

    # Subscription Payment Gate
    assigned_plan = models.ForeignKey(
        'subscriptions.SaasPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_organizers'
    )
    subscription_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_period = models.CharField(max_length=20, default='MONTHLY')
    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PAYMENT_REQUIRED,
        db_index=True
    )

    # Secure Account Activation
    activation_token = models.CharField(max_length=128, blank=True, db_index=True)
    activation_token_expires_at = models.DateTimeField(null=True, blank=True)
    is_activated = models.BooleanField(default=False)
    temporary_password_set = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizer_profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} ({self.user.email}) [{self.verification_status} / {self.payment_status}]"

    @property
    def is_dashboard_accessible(self):
        """
        The Organizer Dashboard may be accessed only if:
        - Organizer account is active
        - Organizer verification is APPROVED
        - Required subscription payment is confirmed (or not required)
        - Subscription is ACTIVE (or valid grace period)
        - No applicable security restriction exists
        """
        if not self.user.is_active or self.user.account_status != User.AccountStatus.ACTIVE:
            return False
        if self.verification_status != self.VerificationStatus.APPROVED:
            return False
        if self.payment_status not in [self.PaymentStatus.PAYMENT_CONFIRMED, self.PaymentStatus.NOT_REQUIRED]:
            return False
        return True

