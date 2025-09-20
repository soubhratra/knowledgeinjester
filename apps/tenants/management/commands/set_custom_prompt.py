"""
Django management command to set custom prompts for organizations.
"""
from django.core.management.base import BaseCommand, CommandError
from apps.tenants.models import Organization
from apps.api.services.prompt_service import PromptService


class Command(BaseCommand):
    help = 'Set a custom prompt for an organization'

    def add_arguments(self, parser):
        parser.add_argument(
            'tenant_id',
            type=str,
            help='The tenant ID of the organization'
        )
        parser.add_argument(
            '--prompt-file',
            type=str,
            help='Path to a file containing the prompt template'
        )
        parser.add_argument(
            '--prompt-text',
            type=str,
            help='The prompt template text directly'
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate the prompt template before saving'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear the custom prompt (reset to default)'
        )

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        prompt_file = options.get('prompt_file')
        prompt_text = options.get('prompt_text')
        validate = options.get('validate', False)
        clear = options.get('clear', False)

        try:
            organization = Organization.objects.get(tenant_id=tenant_id)
        except Organization.DoesNotExist:
            raise CommandError(f'Organization with tenant_id "{tenant_id}" does not exist.')

        if clear:
            organization.custom_prompt = ''
            organization.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleared custom prompt for organization "{organization.name}"')
            )
            return

        if not prompt_file and not prompt_text:
            raise CommandError('You must provide either --prompt-file or --prompt-text')

        if prompt_file and prompt_text:
            raise CommandError('You cannot provide both --prompt-file and --prompt-text')

        if prompt_file:
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
            except FileNotFoundError:
                raise CommandError(f'File "{prompt_file}" not found.')
            except Exception as e:
                raise CommandError(f'Error reading file "{prompt_file}": {e}')
        else:
            prompt_template = prompt_text

        if validate:
            if not PromptService.validate_prompt_template(prompt_template):
                raise CommandError(
                    'Prompt template validation failed. Make sure it contains {context} and {question} placeholders.'
                )
            self.stdout.write('Prompt template validation passed.')

        organization.custom_prompt = prompt_template
        organization.save()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully set custom prompt for organization "{organization.name}"')
        )

        # Show a preview of the prompt
        self.stdout.write('\nPrompt preview:')
        self.stdout.write('-' * 50)
        self.stdout.write(prompt_template[:500] + ('...' if len(prompt_template) > 500 else ''))
        self.stdout.write('-' * 50)
