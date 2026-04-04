"""
Management command to promote a user to security staff.

Usage:
    python manage.py promote_security <username> --badge SEC-001 --office "Main Security Office"
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from security.models import SecurityProfile


class Command(BaseCommand):
    help = 'Promote a registered user to security staff'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to promote')
        parser.add_argument('--badge', type=str, required=True, help='Badge number e.g. SEC-001')
        parser.add_argument('--office', type=str, default='Main Security Office', help='Office location')

    def handle(self, *args, **options):
        username = options['username']
        badge = options['badge']
        office = options['office']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist.')

        if hasattr(user, 'security_profile'):
            raise CommandError(f'"{username}" already has a security profile (badge: {user.security_profile.badge_number}).')

        if SecurityProfile.objects.filter(badge_number=badge).exists():
            raise CommandError(f'Badge number "{badge}" is already assigned to another officer.')

        SecurityProfile.objects.create(
            user=user,
            badge_number=badge,
            office_location=office,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f'✅ {user.get_full_name() or username} ({username}) is now security staff — Badge: {badge}'
        ))
