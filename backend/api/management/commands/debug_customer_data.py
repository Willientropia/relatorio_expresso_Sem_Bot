# backend/api/management/commands/debug_customer_data.py

from django.core.management.base import BaseCommand
from api.models import Customer, UnidadeConsumidora, Fatura
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Debug dos dados do cliente para troubleshooting'

    def add_arguments(self, parser):
        parser.add_argument('customer_id', type=int, help='ID do cliente para debugar')

    def handle(self, *args, **options):
        customer_id = options['customer_id']
        
        self.stdout.write('='*80)
        self.stdout.write(f'DEBUG - DADOS DO CLIENTE ID: {customer_id}')
        self.stdout.write('='*80)
        
        try:
            # Verificar se o customer existe
            customer = Customer.objects.get(pk=customer_id)
            
            self.stdout.write(f'\n✅ CLIENTE ENCONTRADO:')
            self.stdout.write(f'  Nome: {customer.nome}')
            self.stdout.write(f'  CPF: {customer.cpf}')
            self.stdout.write(f'  User ID: {customer.user_id if customer.user else "N/A"}')
            self.stdout.write(f'  Criado em: {customer.created_at}')
            
            # Verificar usuário associado
            if customer.user:
                user = customer.user
                self.stdout.write(f'\n👤 USUÁRIO ASSOCIADO:')
                self.stdout.write(f'  Username: {user.username}')
                self.stdout.write(f'  Email: {user.email}')
                self.stdout.write(f'  Ativo: {user.is_active}')
            else:
                self.stdout.write(f'\n❌ NENHUM USUÁRIO ASSOCIADO AO CLIENTE')
            
            # Verificar UCs
            ucs = customer.unidades_consumidoras.all()
            self.stdout.write(f'\n🏠 UNIDADES CONSUMIDORAS ({ucs.count()}):')
            
            if ucs.count() == 0:
                self.stdout.write(f'  ❌ Nenhuma UC encontrada para este cliente')
            else:
                for uc in ucs:
                    self.stdout.write(f'\n  UC ID: {uc.id}')
                    self.stdout.write(f'    Código: {uc.codigo}')
                    self.stdout.write(f'    Endereço: {uc.endereco}')
                    self.stdout.write(f'    Tipo: {uc.tipo}')
                    self.stdout.write(f'    Ativa: {uc.is_active}')
                    self.stdout.write(f'    Vigência Início: {uc.data_vigencia_inicio}')
                    self.stdout.write(f'    Vigência Fim: {uc.data_vigencia_fim}')
                    
                    # Verificar faturas desta UC
                    faturas = Fatura.objects.filter(unidade_consumidora=uc)
                    self.stdout.write(f'    Faturas: {faturas.count()}')
                    
                    if faturas.count() > 0:
                        self.stdout.write(f'    📄 FATURAS:')
                        for fatura in faturas[:5]:  # Mostrar apenas as 5 primeiras
                            self.stdout.write(f'      - ID {fatura.id}: {fatura.mes_referencia} | R$ {fatura.valor} | {fatura.arquivo.name if fatura.arquivo else "Sem arquivo"}')
                        
                        if faturas.count() > 5:
                            self.stdout.write(f'      ... e mais {faturas.count() - 5} fatura(s)')
            
            # Verificar anos com faturas
            faturas_all = Fatura.objects.filter(unidade_consumidora__customer=customer)
            anos_com_faturas = set()
            
            for fatura in faturas_all:
                anos_com_faturas.add(fatura.mes_referencia.year)
            
            self.stdout.write(f'\n📅 ANOS COM FATURAS:')
            if anos_com_faturas:
                for ano in sorted(anos_com_faturas, reverse=True):
                    faturas_ano = faturas_all.filter(mes_referencia__year=ano)
                    self.stdout.write(f'  {ano}: {faturas_ano.count()} fatura(s)')
            else:
                self.stdout.write(f'  ❌ Nenhuma fatura encontrada')
            
            # Teste da API endpoint
            self.stdout.write(f'\n🧪 TESTE DA API:')
            self.stdout.write(f'  URL para testar: http://localhost:8000/api/customers/{customer_id}/faturas/por-ano/?ano=2025')
            
            # Simular a view
            from django.test import RequestFactory
            from django.contrib.auth.models import AnonymousUser
            from api.views import get_faturas_por_ano
            
            factory = RequestFactory()
            request = factory.get(f'/api/customers/{customer_id}/faturas/por-ano/?ano=2025')
            
            if customer.user:
                request.user = customer.user
            else:
                request.user = AnonymousUser()
            
            try:
                response = get_faturas_por_ano(request, customer_id)
                self.stdout.write(f'  Status da resposta: {response.status_code}')
                
                if response.status_code == 200:
                    data = response.data
                    self.stdout.write(f'  ✅ API funcionando!')
                    self.stdout.write(f'  Anos disponíveis: {data.get("anos_disponiveis", [])}')
                    self.stdout.write(f'  Total UCs: {data.get("total_ucs", 0)}')
                    self.stdout.write(f'  UCs ativas: {data.get("total_ucs_ativas", 0)}')
                    
                    faturas_por_mes = data.get("faturas_por_mes", {})
                    meses_com_dados = len([m for m in faturas_por_mes.values() if m.get('ucs')])
                    self.stdout.write(f'  Meses com dados: {meses_com_dados}/12')
                else:
                    self.stdout.write(f'  ❌ Erro na API: {response.status_code}')
                    if hasattr(response, 'data'):
                        self.stdout.write(f'  Erro: {response.data}')
                        
            except Exception as e:
                self.stdout.write(f'  ❌ Erro ao testar API: {str(e)}')
                import traceback
                traceback.print_exc()
            
            # Verificar permissões
            self.stdout.write(f'\n🔐 VERIFICAÇÃO DE PERMISSÕES:')
            
            if customer.user:
                # Verificar se outros customers pertencem ao mesmo usuário
                outros_customers = Customer.objects.filter(user=customer.user).exclude(id=customer_id)
                self.stdout.write(f'  Outros clientes do usuário: {outros_customers.count()}')
                
                for outro in outros_customers:
                    self.stdout.write(f'    - {outro.nome} (ID: {outro.id})')
            
        except Customer.DoesNotExist:
            self.stdout.write(f'❌ CLIENTE NÃO ENCONTRADO: ID {customer_id}')
            
            # Listar clientes existentes
            customers = Customer.objects.all()
            self.stdout.write(f'\n📋 CLIENTES EXISTENTES ({customers.count()}):')
            for customer in customers:
                self.stdout.write(f'  ID {customer.id}: {customer.nome} (User: {customer.user_id if customer.user else "N/A"})')
        
        except Exception as e:
            self.stdout.write(f'❌ ERRO GERAL: {str(e)}')
            import traceback
            traceback.print_exc()
        
        self.stdout.write('\n' + '='*80)