"""
Django management command to add development HTTP origins to allowed_origins.
This is needed for local development where the widget runs on http://localhost:3000
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import Organization


class Command(BaseCommand):
    help = 'Add HTTP development origins to allowed_origins for local testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site-key',
            type=str,
            help='Site key of the organization to update (defaults to all)',
            default=None
        )
        parser.add_argument(
            '--origin',
            type=str,
            help='Specific origin to add (e.g., http://localhost:3000)',
            default=None
        )

    def handle(self, *args, **options):
        site_key = options.get('site_key')
        specific_origin = options.get('origin')
        
        # Default development origins to add
        dev_origins = [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'http://localhost:8000',
            'http://127.0.0.1:8000',
        ]
        
        # If specific origin provided, use only that
        if specific_origin:
            dev_origins = [specific_origin]
        
        # Get organizations to update
        if site_key:
            orgs = Organization.objects.filter(site_key=site_key)
        else:
            orgs = Organization.objects.all()
        
        if not orgs.exists():
            self.stdout.write(self.style.ERROR('No organizations found'))
            return
        
        for org in orgs:
            updated = False
            original_origins = org.allowed_origins.copy()
            
            for origin in dev_origins:
                if origin not in org.allowed_origins:
                    org.allowed_origins.append(origin)
                    updated = True
                    self.stdout.write(
                        self.style.SUCCESS(f'Added {origin} to {org.name} ({org.site_key})')
                    )
            
            if updated:
                org.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nUpdated {org.name}:\n'
                        f'  Before: {original_origins}\n'
                        f'  After:  {org.allowed_origins}\n'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'No changes needed for {org.name} ({org.site_key})')
                )
        
        self.stdout.write(self.style.SUCCESS('\n✓ Done!'))

