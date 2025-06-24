from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Customer, UnidadeConsumidora
from django.db.models import Count, Q


class Command(BaseCommand):
    help = 'List all users in the system with their related data summary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information for each user'
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Search users by username, email, or name'
        )

    def handle(self, *args, **options):
        detailed = options['detailed']
        search = options['search']

        # Get all users with customer counts
        users_query = User.objects.annotate(
            customer_count=Count('customers')
        ).order_by('-date_joined')        # Apply search filter if provided
        if search:
            users_query = users_query.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        users = list(users_query)

        if not users:
            if search:
                self.stdout.write(f'No users found matching "{search}"')
            else:
                self.stdout.write('No users found in the system')
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {len(users)} user(s):')
        )
        self.stdout.write('=' * 80)

        for user in users:
            self.show_user_summary(user, detailed)
            if detailed:
                self.stdout.write('-' * 80)

    def show_user_summary(self, user, detailed=False):
        """Show user summary information"""
        # Basic user info
        status_indicators = []
        if user.is_superuser:
            status_indicators.append('SUPERUSER')
        if user.is_staff:
            status_indicators.append('STAFF')
        if not user.is_active:
            status_indicators.append('INACTIVE')
        
        status_str = f" [{', '.join(status_indicators)}]" if status_indicators else ""
        
        self.stdout.write(
            self.style.HTTP_INFO(f'ID: {user.id} | Username: {user.username}{status_str}')
        )
        
        if user.email:
            self.stdout.write(f'Email: {user.email}')
        
        if user.first_name or user.last_name:
            full_name = f"{user.first_name} {user.last_name}".strip()
            self.stdout.write(f'Name: {full_name}')

        self.stdout.write(f'Joined: {user.date_joined.strftime("%Y-%m-%d %H:%M")}')
        
        if user.last_login:
            self.stdout.write(f'Last Login: {user.last_login.strftime("%Y-%m-%d %H:%M")}')
        else:
            self.stdout.write('Last Login: Never')

        # Show customer count
        customer_count = user.customer_count
        self.stdout.write(f'Customers: {customer_count}')

        if detailed and customer_count > 0:
            self.show_detailed_customer_info(user)

        self.stdout.write('')  # Empty line for separation

    def show_detailed_customer_info(self, user):
        """Show detailed information about user's customers"""
        customers = Customer.objects.filter(user=user).prefetch_related('unidades_consumidoras')
        
        for customer in customers:
            self.stdout.write(f'  Customer: {customer.nome} (CPF: {customer.cpf})')
            
            # Count UCs, faturas, and tasks
            ucs = customer.unidades_consumidoras.all()
            total_faturas = 0
            total_tasks = 0
            
            for uc in ucs:
                faturas_count = uc.faturas.count()
                tasks_count = uc.tasks.count()
                total_faturas += faturas_count
                total_tasks += tasks_count
                
                status = "Ativa" if uc.is_active else "Inativa"
                self.stdout.write(
                    f'    UC: {uc.codigo} ({uc.tipo}) - {status} | '
                    f'Faturas: {faturas_count} | Tasks: {tasks_count}'
                )
            
            self.stdout.write(
                f'    TOTAL: {len(ucs)} UCs | {total_faturas} Faturas | {total_tasks} Tasks'
            )
