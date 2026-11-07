import logging
from django.conf import settings
from django.core.mail import send_mail
from .models import Notification

logger = logging.getLogger(__name__)

def create_notification(
    user,
    title: str,
    message: str,
    title_am: str = "",
    message_am: str = "",
    notification_type: str = Notification.NotificationType.GENERAL,
    group=None,
    link_url: str = ""
):
    """
    Creates an in-app notification reliably without interrupting financial transactions.
    """
    try:
        return Notification.objects.create(
            user=user,
            group=group,
            title=title,
            title_am=title_am or title,
            message=message,
            message_am=message_am or message,
            notification_type=notification_type,
            link_url=link_url
        )
    except Exception as e:
        logger.error(f"Failed to create notification for {getattr(user, 'email', str(user))}: {e}")
        return None


def send_platform_notification(
    user,
    title: str,
    message: str,
    title_am: str = "",
    message_am: str = "",
    notification_type: str = Notification.NotificationType.GENERAL,
    group=None,
    link_url: str = "",
    channels=None
):
    """
    Multi-channel platform notification dispatcher:
    - IN_APP: Persisted to PostgreSQL notifications table.
    - EMAIL: Dispatched via Django mail backend (SMTP/Console).
    - SMS: Simulated / logged via Ethio Telecom SMS gateway adapter.
    """
    channels = channels or ['IN_APP']
    notif = None

    if 'IN_APP' in channels:
        notif = create_notification(
            user=user,
            title=title,
            message=message,
            title_am=title_am,
            message_am=message_am,
            notification_type=notification_type,
            group=group,
            link_url=link_url
        )

    if 'EMAIL' in channels and getattr(user, 'email', None):
        try:
            send_mail(
                subject=f"[Digital Equb Ethiopia] {title}",
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'notifications@digitalequb.et'),
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.warning(f"Email dispatch failed for {user.email}: {e}")

    if 'SMS' in channels and getattr(user, 'phone_number', None):
        # Simulated Ethio Telecom SMS gateway integration
        logger.info(f"[EthioTelecom SMS Gateway] Dispatched SMS to {user.phone_number}: {title} - {message}")

    return notif


def dispatch_announcement_fanout(announcement):
    """
    Fans out a published platform announcement to targeted users across selected channels.
    """
    from apps.accounts.models import User
    from apps.groups.models import EqubGroup, GroupMembership

    category_to_type = {
        'MAINTENANCE': Notification.NotificationType.MAINTENANCE,
        'FEATURE': Notification.NotificationType.NEW_FEATURE,
        'SUBSCRIPTION': Notification.NotificationType.SUBSCRIPTION_RENEWAL,
        'VERIFICATION': Notification.NotificationType.VERIFICATION_DECISION,
        'CONTRIBUTION_DEADLINE': Notification.NotificationType.CONTRIBUTION_DEADLINE,
        'GENERAL': Notification.NotificationType.GENERAL,
    }
    notif_type = category_to_type.get(announcement.category, Notification.NotificationType.GENERAL)
    channels = announcement.channels if announcement.channels else ['IN_APP']

    # Target Resolution
    recipients = []
    if announcement.target_audience == 'ALL':
        recipients = list(User.objects.filter(is_active=True))
    elif announcement.target_audience == 'ORGANIZERS':
        recipients = list(User.objects.filter(
            is_active=True
        ).filter(
            models.Q(organizer_profile__isnull=False) |
            models.Q(groups_organized__isnull=False)
        ).distinct())
    elif announcement.target_audience == 'MEMBERS':
        member_ids = GroupMembership.objects.filter(
            status=GroupMembership.MembershipStatus.ACTIVE
        ).values_list('user_id', flat=True).distinct()
        recipients = list(User.objects.filter(id__in=member_ids, is_active=True))
    elif announcement.target_audience == 'SPECIFIC_ORGANIZER' and announcement.target_user:
        recipients = [announcement.target_user]
    elif announcement.target_audience == 'SPECIFIC_GROUP' and announcement.target_group:
        member_ids = GroupMembership.objects.filter(
            group=announcement.target_group,
            status=GroupMembership.MembershipStatus.ACTIVE
        ).values_list('user_id', flat=True).distinct()
        recipients = list(User.objects.filter(id__in=member_ids, is_active=True))
    elif announcement.target_user:
        recipients = [announcement.target_user]

    # Bulk create IN_APP notifications
    if 'IN_APP' in channels and recipients:
        notifications_to_create = [
            Notification(
                user=recipient,
                group=announcement.target_group,
                title=announcement.title,
                title_am=announcement.title_am or announcement.title,
                message=announcement.content,
                message_am=announcement.content_am or announcement.content,
                notification_type=notif_type,
                link_url=f"/announcements"
            )
            for recipient in recipients
        ]
        Notification.objects.bulk_create(notifications_to_create, ignore_conflicts=True)

    # Multi-channel delivery for external channels (EMAIL / SMS)
    for recipient in recipients:
        if 'EMAIL' in channels and recipient.email:
            try:
                send_mail(
                    subject=f"[Digital Equb Announcement] {announcement.title}",
                    message=announcement.content,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'notifications@digitalequb.et'),
                    recipient_list=[recipient.email],
                    fail_silently=True
                )
            except Exception as e:
                logger.warning(f"Announcement email failed for {recipient.email}: {e}")

        if 'SMS' in channels and recipient.phone_number:
            logger.info(f"[EthioTelecom SMS] Broadcast to {recipient.phone_number}: {announcement.title}")

    return len(recipients)


def notify_verification_decision(organizer_user, decision: str, notes: str = ""):
    """
    Sends automated verification decision notification to an organizer.
    """
    decision_titles = {
        'APPROVE': "Organizer Verification Approved",
        'REJECT': "Organizer Verification Rejected",
        'REQUEST_INFO': "Additional Verification Information Required",
        'SUSPEND': "Organizer Account Suspended"
    }
    decision_titles_am = {
        'APPROVE': "የአዘጋጅ ማረጋገጫ ጸድቋል",
        'REJECT': "የአዘጋጅ ማረጋገጫ ውድቅ ተደርጓል",
        'REQUEST_INFO': "ተጨማሪ የማረጋገጫ መረጃ ያስፈልጋል",
        'SUSPEND': "የአዘጋጅ መለያ ታግዷል"
    }
    title = decision_titles.get(decision, "Organizer Verification Update")
    title_am = decision_titles_am.get(decision, "የአዘጋጅ ማረጋገጫ ዝማኔ")

    msg = f"Your organizer verification status is now {decision}."
    if notes:
        msg += f" Note: {notes}"

    msg_am = f"የእርስዎ የአዘጋጅ ማረጋገጫ ሁኔታ አሁን {decision} ሆኗል።"
    if notes:
        msg_am += f" ማስታወሻ: {notes}"

    return send_platform_notification(
        user=organizer_user,
        title=title,
        message=msg,
        title_am=title_am,
        message_am=msg_am,
        notification_type=Notification.NotificationType.VERIFICATION_DECISION,
        channels=['IN_APP', 'EMAIL', 'SMS']
    )


def notify_subscription_renewal(organizer_user, plan_name: str, renewal_date, amount_etb):
    """
    Sends subscription renewal notice to an organizer.
    """
    title = f"Subscription Renewal Due: {plan_name}"
    title_am = f"የደንበኝነት ምዝገባ ማደስ ጊዜ: {plan_name}"
    msg = f"Your Equb organizer subscription for {plan_name} (ETB {amount_etb}) is scheduled for renewal on {renewal_date}. Please ensure payment is completed."
    msg_am = f"የእርስዎ {plan_name} እቁብ አዘጋጅ የደንበኝነት ምዝገባ (ብር {amount_etb}) በ {renewal_date} ይታደሳል። እባክዎ ክፍያውን ያጠናቅቁ።"

    return send_platform_notification(
        user=organizer_user,
        title=title,
        message=msg,
        title_am=title_am,
        message_am=msg_am,
        notification_type=Notification.NotificationType.SUBSCRIPTION_RENEWAL,
        channels=['IN_APP', 'EMAIL', 'SMS']
    )


def notify_contribution_deadline(member_user, group, due_date, amount_etb):
    """
    Sends contribution deadline reminder to a group member.
    """
    title = f"Contribution Due: {group.name}"
    title_am = f"የእቁብ መዋጮ ጊዜ: {group.name}"
    msg = f"Friendly reminder: your contribution of ETB {amount_etb} for {group.name} is due on {due_date}."
    msg_am = f"ማስታወሻ: ለ{group.name} የሚጠበቅብዎት ብር {amount_etb} መዋጮ ቀን {due_date} ነው።"

    return send_platform_notification(
        user=member_user,
        title=title,
        message=msg,
        title_am=title_am,
        message_am=msg_am,
        notification_type=Notification.NotificationType.CONTRIBUTION_DEADLINE,
        group=group,
        channels=['IN_APP', 'EMAIL', 'SMS']
    )


def notify_group_officers(group, title, message, title_am="", message_am="", notification_type=Notification.NotificationType.GENERAL, exclude_user=None):
    """
    Notifies organizers and treasurers of a group.
    """
    from apps.groups.models import GroupMembership
    officer_memberships = GroupMembership.objects.filter(
        group=group,
        status=GroupMembership.MembershipStatus.ACTIVE,
        role_assignments__role__code__in=['GROUP_ORGANIZER', 'GROUP_TREASURER']
    ).select_related('user').distinct()

    for m in officer_memberships:
        if exclude_user and m.user_id == exclude_user.id:
            continue
        create_notification(
            user=m.user,
            group=group,
            title=title,
            message=message,
            title_am=title_am,
            message_am=message_am,
            notification_type=notification_type
        )
