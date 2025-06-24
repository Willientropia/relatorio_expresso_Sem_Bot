from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from api.models import Customer, UnidadeConsumidora, Fatura, FaturaTask


class Command(BaseCommand):
    help = 'Delete a user and all related data from the system'

    def add_arguments(self, parser):
        parser.add_argument(
            'identifier',
            type=str,
            help='User identifier (username, email, or user ID)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        force = options['force']
        dry_run = options['dry_run']

        # Try to find the user by different criteria
        user = self.find_user(identifier)
        if not user:
            raise CommandError(f'User not found: {identifier}')

        # Show user information and related data
        self.show_user_info(user)

        # If dry run, just show what would be deleted
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No data will be deleted')
            )
            return

        # Ask for confirmation unless force is used
        if not force:
            confirm = input('\nAre you sure you want to delete this user and ALL related data? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled.')
                return

        # Delete the user and all related data
        self.delete_user(user)

    def find_user(self, identifier):
        """Find user by username, email, or ID"""
        try:
            # Try to find by ID first
            if identifier.isdigit():
                return User.objects.get(id=int(identifier))
        except (User.DoesNotExist, ValueError):
            pass

        try:
            # Try to find by username
            return User.objects.get(username=identifier)
        except User.DoesNotExist:
            pass

        try:
            # Try to find by email
            return User.objects.get(email=identifier)
        except User.DoesNotExist:
            pass

        return None

    def show_user_info(self, user):
        """Display comprehensive user information"""
        self.stdout.write(
            self.style.SUCCESS(f'\n=== USER INFORMATION ===')
        )
        self.stdout.write(f'ID: {user.id}')
        self.stdout.write(f'Username: {user.username}')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'First Name: {user.first_name}')
        self.stdout.write(f'Last Name: {user.last_name}')
        self.stdout.write(f'Date Joined: {user.date_joined}')
        self.stdout.write(f'Last Login: {user.last_login}')
        self.stdout.write(f'Is Active: {user.is_active}')
        self.stdout.write(f'Is Staff: {user.is_staff}')
        self.stdout.write(f'Is Superuser: {user.is_superuser}')

        # Show related customers
        customers = Customer.objects.filter(user=user)
        self.stdout.write(
            self.style.SUCCESS(f'\n=== RELATED CUSTOMERS ({customers.count()}) ===')
        )
        
        total_ucs = 0
        total_faturas = 0
        total_tasks = 0

        for customer in customers:
            self.stdout.write(f'\nCustomer: {customer.nome}')
            self.stdout.write(f'  CPF: {customer.cpf}')
            self.stdout.write(f'  Email: {customer.email}')
            self.stdout.write(f'  Created: {customer.created_at}')

            # Show UCs for this customer
            ucs = UnidadeConsumidora.objects.filter(customer=customer)
            total_ucs += ucs.count()
            self.stdout.write(f'  Unidades Consumidoras: {ucs.count()}')

            for uc in ucs:
                faturas = Fatura.objects.filter(unidade_consumidora=uc)
                tasks = FaturaTask.objects.filter(unidade_consumidora=uc)
                total_faturas += faturas.count()
                total_tasks += tasks.count()

                self.stdout.write(f'    UC: {uc.codigo} ({uc.tipo})')
                self.stdout.write(f'      Status: {"Ativa" if uc.is_active else "Inativa"}')
                self.stdout.write(f'      Faturas: {faturas.count()}')
                self.stdout.write(f'      Tasks: {tasks.count()}')

        # Summary
        self.stdout.write(
            self.style.WARNING(f'\n=== DELETION SUMMARY ===')
        )
        self.stdout.write(f'Total items that will be PERMANENTLY DELETED:')
        self.stdout.write(f'  - 1 User')
        self.stdout.write(f'  - {customers.count()} Customer(s)')
        self.stdout.write(f'  - {total_ucs} Unidade(s) Consumidora(s)')
        self.stdout.write(f'  - {total_faturas} Fatura(s)')
        self.stdout.write(f'  - {total_tasks} Task(s)')
        
        self.stdout.write(
            self.style.ERROR('\nWARNING: This operation cannot be undone!')
        )

    @transaction.atomic
    def delete_user(self, user):
        """Delete user and all related data in a transaction"""
        try:
            username = user.username
            user_id = user.id

            # Get counts before deletion for reporting
            customers_count = Customer.objects.filter(user=user).count()
            ucs_count = UnidadeConsumidora.objects.filter(customer__user=user).count()
            faturas_count = Fatura.objects.filter(unidade_consumidora__customer__user=user).count()
            tasks_count = FaturaTask.objects.filter(unidade_consumidora__customer__user=user).count()

            # Delete the user (this will cascade to all related objects due to FK constraints)
            user.delete()

            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Successfully deleted user "{username}" (ID: {user_id})')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Deleted {customers_count} customer(s)')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Deleted {ucs_count} unidade(s) consumidora(s)')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Deleted {faturas_count} fatura(s)')
            )
            self.stdout.write(
                self.style.SUCCESS(f'✓ Deleted {tasks_count} task(s)')
            )

        except Exception as e:
            raise CommandError(f'Error deleting user: {str(e)}')
