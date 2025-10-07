# Generated data migration to populate site_key for existing organizations

from django.db import migrations
import secrets
import string


def generate_site_key(name: str) -> str:
    """Generate a site key in format: pub_{name}_{random}"""
    # Clean the name: lowercase, replace spaces with underscores, keep only alphanumeric
    clean_name = ''.join(c if c.isalnum() else '_' for c in name.lower())
    clean_name = clean_name[:20]  # Limit length
    
    # Generate random suffix (8 characters)
    random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    
    return f"pub_{clean_name}_{random_suffix}"


def populate_site_keys(apps, schema_editor):
    """Populate site_key for existing organizations"""
    Organization = apps.get_model('tenants', 'Organization')
    
    for org in Organization.objects.filter(site_key__isnull=True):
        org.site_key = generate_site_key(org.name)
        org.status = 'active'  # Default to active
        org.env = 'prod'  # Default to prod
        org.save(update_fields=['site_key', 'status', 'env'])


def reverse_populate_site_keys(apps, schema_editor):
    """Reverse migration - set site_key to None"""
    Organization = apps.get_model('tenants', 'Organization')
    Organization.objects.all().update(site_key=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_conversation_session_activityaudit_ip_address_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_site_keys, reverse_populate_site_keys),
    ]

