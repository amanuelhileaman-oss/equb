import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.groups.models import EqubGroup, LotteryRound
from apps.groups.lottery_services import (
    ensure_active_cycle,
    get_or_create_lottery_round,
    check_round_readiness,
    execute_lottery_for_round,
    complete_cycle_if_eligible,
)
from apps.groups.overdue_services import (
    evaluate_group_deadlines_and_grace_periods,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Autonomous Equb Cycle Manager daemon: evaluates contribution deadlines, "
        "processes grace periods, handles overdue resolutions, and executes scheduled lotteries."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run one execution cycle and terminate immediately instead of looping indefinitely.',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between scan iterations when running continuously (default: 60s).',
        )

    def handle(self, *args, **options):
        run_once = options['once']
        interval = options['interval']

        self.stdout.write(self.style.SUCCESS(
            f"Starting Equb Cycle Manager [run_once={run_once}, interval={interval}s]..."
        ))

        while True:
            try:
                self.process_all_groups()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error in cycle manager loop: {str(e)}"))
                logger.exception("Cycle manager loop error")

            if run_once:
                self.stdout.write(self.style.SUCCESS("Cycle manager single run complete."))
                break

            time.sleep(interval)

    def process_all_groups(self):
        active_groups = EqubGroup.objects.filter(status=EqubGroup.GroupStatus.ACTIVE)
        today = timezone.now().date()
        self.stdout.write(f"[{timezone.now().isoformat()}] Processing {active_groups.count()} active Equb group(s)...")

        for group in active_groups:
            try:
                # 1. Evaluate contribution deadlines & grace periods
                cases = evaluate_group_deadlines_and_grace_periods(group)
                if cases:
                    self.stdout.write(f"  Group '{group.name}': {len(cases)} overdue case(s) initiated.")

                # 2. Check / get active cycle
                cycle = ensure_active_cycle(group)

                # 3. Check for scheduled round ready for lottery
                round_obj = get_or_create_lottery_round(group)
                if round_obj and round_obj.status in [LotteryRound.RoundStatus.SCHEDULED, LotteryRound.RoundStatus.POSTPONED]:
                    is_ready, pending_count, reasons = check_round_readiness(round_obj)
                    if is_ready:
                        success, msg, res = execute_lottery_for_round(round_obj)
                        if success:
                            self.stdout.write(self.style.SUCCESS(
                                f"  Group '{group.name}' Round {round_obj.round_number}: {msg}"
                            ))
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"  Group '{group.name}' Round {round_obj.round_number}: {msg}"
                            ))
                    else:
                        round_obj.status = LotteryRound.RoundStatus.POSTPONED
                        round_obj.postponed_reason = "; ".join(reasons)
                        round_obj.save(update_fields=['status', 'postponed_reason'])
                        self.stdout.write(self.style.NOTICE(
                            f"  Group '{group.name}' Round {round_obj.round_number} postponed: {round_obj.postponed_reason}"
                        ))

                # 4. Check cycle completion
                complete_cycle_if_eligible(cycle)

            except Exception as ex:
                self.stderr.write(self.style.ERROR(f"  Error processing group {group.id} ({group.name}): {str(ex)}"))
                logger.exception(f"Error processing group {group.id}")
