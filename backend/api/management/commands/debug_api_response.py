# backend/api/management/commands/debug_api_response.py

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.models import User
from api.models import Customer
from api.views import get_faturas_por_ano
import json

class Command(BaseCommand):
    help = 'Debug da resposta da API que vai para o frontend'

    def add_arguments(self, parser):
        parser.add_argument('customer_id', type=int, help='ID do cliente')
        parser.add_argument('--ano', type=int, default=2025, help='Ano para testar')

    def handle(self, *args, **options):
        customer_id = options['customer_id']
        ano = options['ano']
        
        try:
            customer = Customer.objects.get(pk=customer_id)
            
            self.stdout.write('='*80)
            self.stdout.write(f'DEBUG - RESPOSTA DA API PARA O FRONTEND')
            self.stdout.write(f'Cliente: {customer.nome} (ID: {customer_id})')
            self.stdout.write(f'Ano: {ano}')
            self.stdout.write('='*80)
            
            # Simular request
            factory = RequestFactory()
            request = factory.get(f'/api/customers/{customer_id}/faturas/por-ano/?ano={ano}')
            request.user = customer.user if customer.user else User.objects.first()
            
            # Chamar a view
            response = get_faturas_por_ano(request, customer_id)
            
            if response.status_code == 200:
                data = response.data
                
                self.stdout.write(f'\n📊 DADOS GERAIS:')
                self.stdout.write(f'  Ano atual: {data["ano_atual"]}')
                self.stdout.write(f'  Anos disponíveis: {data["anos_disponiveis"]}')
                self.stdout.write(f'  Total UCs: {data["total_ucs"]}')
                if 'total_ucs_ativas' in data:
                    self.stdout.write(f'  Total UCs ativas: {data["total_ucs_ativas"]}')
                
                # Analisar cada mês
                for mes_num, mes_data in data['faturas_por_mes'].items():
                    mes_nome = mes_data['mes_nome']
                    ucs_com_fatura = [uc for uc in mes_data['ucs'] if uc['fatura']]
                    
                    if ucs_com_fatura:  # Só mostrar meses com faturas
                        self.stdout.write(f'\n📅 MÊS {mes_num} - {mes_nome.upper()}:')
                        self.stdout.write(f'  Total UCs: {len(mes_data["ucs"])}')
                        self.stdout.write(f'  UCs com fatura: {len(ucs_com_fatura)}')
                        
                        for uc in ucs_com_fatura:
                            fatura = uc['fatura']
                            self.stdout.write(f'\n    🏠 UC: {uc["uc_codigo"]}')
                            self.stdout.write(f'      Tipo: {uc["uc_tipo"]}')
                            self.stdout.write(f'      Ativa: {uc.get("uc_is_active", "N/A")}')
                            self.stdout.write(f'      Endereço: {uc["uc_endereco"]}')
                            self.stdout.write(f'      💰 Valor: R$ {fatura["valor"] if fatura["valor"] else "N/A"}')
                            self.stdout.write(f'      📅 Vencimento: {fatura["vencimento"] if fatura["vencimento"] else "N/A"}')
                            self.stdout.write(f'      📥 Baixada em: {fatura["downloaded_at"] if fatura["downloaded_at"] else "N/A"}')
                            self.stdout.write(f'      📁 Arquivo: {fatura["arquivo_url"] if fatura["arquivo_url"] else "N/A"}')
                            self.stdout.write(f'      🆔 Fatura ID: {fatura["id"]}')
                
                # Verificar se há faturas em meses inconsistentes
                self.stdout.write(f'\n🔍 VERIFICAÇÃO DE CONSISTÊNCIA:')
                
                # Buscar faturas direto do banco para comparar
                from api.models import Fatura
                faturas_banco = Fatura.objects.filter(
                    unidade_consumidora__customer=customer,
                    mes_referencia__year=ano
                ).order_by('mes_referencia')
                
                self.stdout.write(f'\n📋 FATURAS NO BANCO:')
                for fatura in faturas_banco:
                    mes_banco = fatura.mes_referencia.month
                    self.stdout.write(f'  Fatura {fatura.id}: UC {fatura.unidade_consumidora.codigo} → Mês {mes_banco}')
                
                self.stdout.write(f'\n📤 FATURAS NA RESPOSTA DA API:')
                for mes_num, mes_data in data['faturas_por_mes'].items():
                    for uc in mes_data['ucs']:
                        if uc['fatura']:
                            self.stdout.write(f'  Fatura {uc["fatura"]["id"]}: UC {uc["uc_codigo"]} → Mês {mes_num}')
                
                # Verificar discrepâncias
                self.stdout.write(f'\n⚖️ COMPARAÇÃO BANCO vs API:')
                problemas = 0
                
                for fatura in faturas_banco:
                    fatura_id = fatura.id
                    mes_banco = fatura.mes_referencia.month
                    uc_codigo = fatura.unidade_consumidora.codigo
                    
                    # Procurar esta fatura na resposta da API
                    encontrada_em_mes = None
                    for mes_num, mes_data in data['faturas_por_mes'].items():
                        for uc in mes_data['ucs']:
                            if uc['fatura'] and uc['fatura']['id'] == fatura_id:
                                encontrada_em_mes = int(mes_num)
                                break
                        if encontrada_em_mes:
                            break
                    
                    if encontrada_em_mes:
                        if encontrada_em_mes != mes_banco:
                            self.stdout.write(f'  ❌ PROBLEMA: Fatura {fatura_id} (UC {uc_codigo})')
                            self.stdout.write(f'      Banco: mês {mes_banco}')
                            self.stdout.write(f'      API: mês {encontrada_em_mes}')
                            problemas += 1
                        else:
                            self.stdout.write(f'  ✅ OK: Fatura {fatura_id} consistente no mês {mes_banco}')
                    else:
                        self.stdout.write(f'  ❓ Fatura {fatura_id} não encontrada na resposta da API')
                        problemas += 1
                
                if problemas == 0:
                    self.stdout.write(f'\n✅ NENHUM PROBLEMA ENCONTRADO!')
                else:
                    self.stdout.write(f'\n❌ {problemas} PROBLEMA(S) ENCONTRADO(S)!')
                
                # Mostrar JSON completo se solicitado
                self.stdout.write(f'\n📄 JSON COMPLETO DA RESPOSTA:')
                self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))
                
            else:
                self.stdout.write(f'❌ Erro na API: {response.status_code}')
                self.stdout.write(f'Dados: {response.data}')
        
        except Customer.DoesNotExist:
            self.stdout.write(f'❌ Cliente {customer_id} não encontrado')
        except Exception as e:
            self.stdout.write(f'❌ Erro: {str(e)}')
            import traceback
            traceback.print_exc()