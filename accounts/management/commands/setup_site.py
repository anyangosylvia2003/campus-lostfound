"""
Run once after initial migration:
    python manage.py setup_site

Sets the Sites framework domain so password reset links
point to the correct address instead of example.com.
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Configure the Sites framework domain for password reset links'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            default='127.0.0.1:8000',
            help='Domain to use in emails (default: 127.0.0.1:8000 for local dev)',
        )
        parser.add_argument(
            '--name',
            default='Campus Lost & Found',
            help='Site display name',
        )

    def handle(self, *args, **options):
        from django.contrib.sites.models import Site
        domain = options['domain']
        name   = options['name']
        site, created = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={'domain': domain, 'name': name},
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} site: {name} ({domain})'
        ))
        self.stdout.write(
            'Password reset links will now use: '
            f'http://{domain}/accounts/password-reset/...'
        )
