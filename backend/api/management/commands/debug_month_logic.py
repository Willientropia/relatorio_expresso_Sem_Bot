# backend/api/management/commands/debug_month_logic.py

from django.core.management.base import BaseCommand
from api.models import Fatura, UnidadeConsumidora, Customer
from datetime import datetime, date
import json

class Command(BaseCommand):
    help = 'Diagnóstica a lógica de organização por mês'

    def add_arguments(self, parser):
        parser.add_argument('customer_id', type=int, help='ID do cliente para analisar')
        parser.add_argument('--ano', type=int, default=2025, help='Ano para analisar')

    def handle(self, *args, **options):
        customer_id = options['customer_id']
        ano = options['ano']
        
        try:
            customer = Customer.objects.get(pk=customer_id)
            self.stdout.write(f'Analisando cliente: {customer.nome} (ID: {customer_id})')
            self.stdout.write(f'Ano: {ano}')
            self.stdout.write('='*60)
            
            # Buscar todas as UCs do cliente
            ucs = customer.unidades_consumidoras.all()
            self.stdout.write(f'\nUCs do cliente: {ucs.count()}')
            for uc in ucs:
                self.stdout.write(f'  - UC: {uc.codigo} (Ativa: {uc.is_active})')
            
            # Buscar todas as faturas do ano
            faturas = Fatura.objects.filter(
                unidade_consumidora__customer=customer,
                mes_referencia__year=ano
            ).order_by('mes_referencia')
            
            self.stdout.write(f'\nFaturas do ano {ano}: {faturas.count()}')
            
            # Mapear faturas por mês e UC
            mapeamento = {}
            for fatura in faturas:
                mes = fatura.mes_referencia.month
                uc_codigo = fatura.unidade_consumidora.codigo
                
                if mes not in mapeamento:
                    mapeamento[mes] = {}
                
                mapeamento[mes][uc_codigo] = {
                    'fatura_id': fatura.id,
                    'mes_referencia': fatura.mes_referencia,
                    'valor': fatura.valor,
                    'arquivo': fatura.arquivo.name if fatura.arquivo else None
                }
            
            # Mostrar mapeamento detalhado
            MESES = {
                1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
            }
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write('MAPEAMENTO POR MÊS:')
            self.stdout.write('='*60)
            
            for mes in range(1, 13):
                mes_nome = MESES[mes]
                self.stdout.write(f'\n{mes}. {mes_nome.upper()}:')
                
                if mes in mapeamento:
                    for uc_codigo, dados in mapeamento[mes].items():
                        self.stdout.write(f'  ✅ UC {uc_codigo}:')
                        self.stdout.write(f'     ID: {dados["fatura_id"]}')
                        self.stdout.write(f'     Data: {dados["mes_referencia"]}')
                        self.stdout.write(f'     Valor: R$ {dados["valor"]}')
                        self.stdout.write(f'     Arquivo: {dados["arquivo"]}')
                else:
                    self.stdout.write('  ❌ Nenhuma fatura')
            
            # Verificar se há faturas em meses errados
            self.stdout.write('\n' + '='*60)
            self.stdout.write('VERIFICAÇÃO DE CONSISTÊNCIA:')
            self.stdout.write('='*60)
            
            problemas_encontrados = 0
            for fatura in faturas:
                mes_esperado = fatura.mes_referencia.month
                
                # Tentar extrair mês do nome do arquivo
                arquivo_nome = fatura.arquivo.name if fatura.arquivo else ''
                if 'MAI' in arquivo_nome.upper() or 'MAY' in arquivo_nome.upper():
                    if mes_esperado != 5:
                        self.stdout.write(f'❌ PROBLEMA: Fatura {fatura.id}')
                        self.stdout.write(f'   Arquivo sugere MAIO: {arquivo_nome}')
                        self.stdout.write(f'   Mas mes_referencia é: {fatura.mes_referencia} (mês {mes_esperado})')
                        problemas_encontrados += 1
                
                if 'JUN' in arquivo_nome.upper():
                    if mes_esperado != 6:
                        self.stdout.write(f'❌ PROBLEMA: Fatura {fatura.id}')
                        self.stdout.write(f'   Arquivo sugere JUNHO: {arquivo_nome}')
                        self.stdout.write(f'   Mas mes_referencia é: {fatura.mes_referencia} (mês {mes_esperado})')
                        problemas_encontrados += 1
                
                if 'JUL' in arquivo_nome.upper():
                    if mes_esperado != 7:
                        self.stdout.write(f'❌ PROBLEMA: Fatura {fatura.id}')
                        self.stdout.write(f'   Arquivo sugere JULHO: {arquivo_nome}')
                        self.stdout.write(f'   Mas mes_referencia é: {fatura.mes_referencia} (mês {mes_esperado})')
                        problemas_encontrados += 1
            
            if problemas_encontrados == 0:
                self.stdout.write('✅ Nenhum problema de consistência encontrado')
            else:
                self.stdout.write(f'❌ {problemas_encontrados} problema(s) encontrado(s)')
            
            # Simular a API response
            self.stdout.write('\n' + '='*60)
            self.stdout.write('SIMULAÇÃO DA API:')
            self.stdout.write('='*60)
            
            from django.test import RequestFactory
            from api.views import get_faturas_por_ano
            
            factory = RequestFactory()
            request = factory.get(f'/api/customers/{customer_id}/faturas/por-ano/?ano={ano}')
            request.user = customer.user
            
            response = get_faturas_por_ano(request, customer_id)
            
            if response.status_code == 200:
                data = response.data
                for mes_num, mes_data in data['faturas_por_mes'].items():
                    if mes_data['ucs']:
                        self.stdout.write(f'\nMês {mes_num} - {mes_data["mes_nome"]}:')
                        for uc in mes_data['ucs']:
                            if uc['fatura']:
                                self.stdout.write(f'  UC {uc["uc_codigo"]}: TEM fatura')
                            else:
                                self.stdout.write(f'  UC {uc["uc_codigo"]}: SEM fatura')
            else:
                self.stdout.write(f'Erro na API: {response.status_code}')
            
        except Customer.DoesNotExist:
            self.stdout.write(f'❌ Cliente {customer_id} não encontrado')
        except Exception as e:
            self.stdout.write(f'❌ Erro: {str(e)}')
            import traceback
            traceback.print_exc()