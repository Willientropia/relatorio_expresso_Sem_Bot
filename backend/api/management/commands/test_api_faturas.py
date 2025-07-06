# backend/api/management/commands/test_api_faturas.py

from django.core.management.base import BaseCommand
from api.models import Customer
from api.views import get_faturas_por_ano
from django.test import RequestFactory
from django.contrib.auth.models import User
import json

class Command(BaseCommand):
    help = 'Testa a API de faturas por ano'

    def add_arguments(self, parser):
        parser.add_argument('customer_id', type=int, help='ID do cliente para testar')

    def handle(self, *args, **options):
        customer_id = options['customer_id']
        
        try:
            customer = Customer.objects.get(pk=customer_id)
            self.stdout.write(f'Testando API para cliente: {customer.nome}')
            
            # Criar um request fake
            factory = RequestFactory()
            request = factory.get(f'/api/customers/{customer_id}/faturas/por-ano/')
            request.user = customer.user if customer.user else User.objects.first()
            
            # Chamar a view
            from api.views import get_faturas_por_ano
            response = get_faturas_por_ano(request, customer_id)
            
            if response.status_code == 200:
                data = response.data
                self.stdout.write('\n' + '='*50)
                self.stdout.write('RESPOSTA DA API:')
                self.stdout.write('='*50)
                
                self.stdout.write(f'Ano atual: {data["ano_atual"]}')
                self.stdout.write(f'Anos disponíveis: {data["anos_disponiveis"]}')
                self.stdout.write(f'Total UCs: {data["total_ucs"]}')
                
                self.stdout.write('\nFaturas por mês:')
                for mes, dados in data['faturas_por_mes'].items():
                    self.stdout.write(f'\n  {dados["mes_nome"]} ({dados["mes_abrev"]}):')
                    self.stdout.write(f'    UCs: {len(dados["ucs"])}')
                    
                    for uc in dados['ucs']:
                        status = "✅ COM fatura" if uc['fatura'] else "❌ SEM fatura"
                        self.stdout.write(f'      UC {uc["uc_codigo"]}: {status}')
                        
                        if uc['fatura']:
                            self.stdout.write(f'        Valor: R$ {uc["fatura"]["valor"]}')
                            self.stdout.write(f'        Vencimento: {uc["fatura"]["vencimento"]}')
            else:
                self.stdout.write(f'Erro na API: {response.status_code}')
                self.stdout.write(f'Dados: {response.data}')
                
        except Customer.DoesNotExist:
            self.stdout.write(f'Cliente {customer_id} não encontrado')
        except Exception as e:
            self.stdout.write(f'Erro: {str(e)}')