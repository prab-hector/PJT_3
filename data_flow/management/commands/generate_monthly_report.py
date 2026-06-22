from django.core.management.base import BaseCommand
from django.utils import timezone
from data_flow.service import generate_monthly_report
from datetime import timedelta

class Command(BaseCommand):
    help = 'Generate previous month attendance report and optionally delete those attendance logs.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Year for report (defaults to previous month)')
        parser.add_argument('--month', type=int, help='Month number for report (1-12). Defaults to previous month')
        parser.add_argument('--no-delete', action='store_true', help="Don't delete attendance logs after report generation")
        parser.add_argument('--outdir', type=str, help='Directory to save the report')

    def handle(self, *args, **options):
        now = timezone.localdate()
        year = options.get('year')
        month = options.get('month')
        if not year or not month:
            # Default to previous month
            first_of_this_month = now.replace(day=1)
            prev_month_last_day = first_of_this_month - timedelta(days=1)
            year = prev_month_last_day.year
            month = prev_month_last_day.month

        delete_after = not options.get('no_delete', False)
        outdir = options.get('outdir')

        path = generate_monthly_report(year, month, save_dir=outdir, delete_after=delete_after)
        if path:
            self.stdout.write(self.style.SUCCESS(f'Report created: {path}'))
            if delete_after:
                self.stdout.write(self.style.WARNING('Attendance logs for the reported month were deleted.'))
        else:
            self.stdout.write('No attendance logs found for that month.')
