from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from decimal import Decimal

from accounts.models import Driver, ServiceOrder, DailyReport, CashBalance


class Command(BaseCommand):
    help = 'Generate daily driver reports for a given date (defaults to yesterday).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            default=None,
            help='Date to generate report for in YYYY-MM-DD format. Defaults to yesterday.',
        )
        parser.add_argument(
            '--all-drivers',
            action='store_true',
            default=False,
            help='Generate reports for all drivers, even those with zero orders.',
        )

    def handle(self, *args, **options):
        if options['date']:
            try:
                report_date = date.fromisoformat(options['date'])
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {options['date']}. Use YYYY-MM-DD."))
                return
        else:
            report_date = date.today() - timedelta(days=1)

        self.stdout.write(f"Generating daily reports for {report_date} ...")

        finished_orders = ServiceOrder.objects.filter(
            status=ServiceOrder.STATUS_FINISHED,
            created_at__date=report_date,
            driver_assigned__isnull=False,
        ).select_related('driver_assigned')

        driver_stats = {}
        for order in finished_orders:
            driver = order.driver_assigned
            if driver.pk not in driver_stats:
                driver_stats[driver.pk] = {
                    'driver': driver,
                    'orders_count': 0,
                    'cash_total': Decimal('0'),
                    'qliq_total': Decimal('0'),
                }
            driver_stats[driver.pk]['orders_count'] += 1
            price = Decimal(str(order.get_price()))
            if order.payment_method == ServiceOrder.PAYMENT_CASH:
                driver_stats[driver.pk]['cash_total'] += price
            else:
                driver_stats[driver.pk]['qliq_total'] += price

        if options['all_drivers']:
            for driver in Driver.objects.all():
                if driver.pk not in driver_stats:
                    driver_stats[driver.pk] = {
                        'driver': driver,
                        'orders_count': 0,
                        'cash_total': Decimal('0'),
                        'qliq_total': Decimal('0'),
                    }

        created = 0
        updated = 0
        with transaction.atomic():
            for stats in driver_stats.values():
                driver = stats['driver']
                report, was_created = DailyReport.objects.update_or_create(
                    driver=driver,
                    date=report_date,
                    defaults={
                        'orders_count': stats['orders_count'],
                        'cash_total': stats['cash_total'],
                        'qliq_total': stats['qliq_total'],
                    }
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

                if stats['cash_total'] > 0:
                    balance, _ = CashBalance.objects.get_or_create(
                        driver=driver,
                        defaults={'amount_owed': Decimal('0')}
                    )
                    if was_created:
                        balance.amount_owed += stats['cash_total']
                        balance.save(update_fields=['amount_owed', 'last_updated'])

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created} new report(s), updated {updated} existing report(s) for {report_date}."
        ))
