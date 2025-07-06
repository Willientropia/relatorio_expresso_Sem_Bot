# backend/api/management/commands/debug_faturas.py

from django.core.management.base import BaseCommand
from api.models import Fatura, UnidadeConsumidora, Customer
from datetime import datetime

class Command(BaseCommand):
    help = 'Debug das faturas para verificar dados atuais'

    def handle(self, *args, **options):
        self.stdout.write('='*50)
        self.stdout.write('DEBUG - ANÁLISE DAS FATURAS')
        self.stdout.write('='*50)
        
        # Listar todas as faturas
        faturas = Fatura.objects.all().order_by('-created_at')
        
        self.stdout.write(f'\nTotal de faturas: {faturas.count()}')
        
        for fatura in faturas:
            self.stdout.write(f'\nFatura ID: {fatura.id}')
            self.stdout.write(f'  UC: {fatura.unidade_consumidora.codigo}')
            self.stdout.write(f'  Cliente: {fatura.unidade_consumidora.customer.nome}')
            self.stdout.write(f'  Mês Referência: {fatura.mes_referencia}')
            self.stdout.write(f'  Dia da data: {fatura.mes_referencia.day}')
            self.stdout.write(f'  Valor: {fatura.valor}')
            self.stdout.write(f'  Arquivo: {fatura.arquivo.name if fatura.arquivo else "N/A"}')
            self.stdout.write(f'  Criada em: {fatura.created_at}')
        
        # Verificar UCs
        self.stdout.write('\n' + '='*30)
        self.stdout.write('UNIDADES CONSUMIDORAS')
        self.stdout.write('='*30)
        
        ucs = UnidadeConsumidora.objects.all()
        for uc in ucs:
            self.stdout.write(f'\nUC: {uc.codigo}')
            self.stdout.write(f'  Cliente: {uc.customer.nome}')
            self.stdout.write(f'  Ativa: {uc.is_active}')
            self.stdout.write(f'  Tipo: {uc.tipo}')
            self.stdout.write(f'  Faturas: {uc.faturas.count()}')
        
        # Verificar clientes
        self.stdout.write('\n' + '='*20)
        self.stdout.write('CLIENTES')
        self.stdout.write('='*20)
        
        customers = Customer.objects.all()
        for customer in customers:
            self.stdout.write(f'\nCliente: {customer.nome}')
            self.stdout.write(f'  CPF: {customer.cpf}')
            self.stdout.write(f'  UCs: {customer.unidades_consumidoras.count()}')
            self.stdout.write(f'  User ID: {customer.user_id if customer.user else "N/A"}')
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('FIM DO DEBUG')
        self.stdout.write('='*50)