# backend/api/management/commands/debug_edit_fatura.py

from django.core.management.base import BaseCommand
from api.models import Fatura, Customer
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Debug da funcionalidade de edição de fatura'

    def add_arguments(self, parser):
        parser.add_argument('fatura_id', type=int, help='ID da fatura para debugar')

    def handle(self, *args, **options):
        fatura_id = options['fatura_id']
        
        self.stdout.write('='*60)
        self.stdout.write(f'DEBUG - EDIÇÃO DE FATURA ID: {fatura_id}')
        self.stdout.write('='*60)
        
        try:
            # Verificar se a fatura existe
            fatura = Fatura.objects.get(pk=fatura_id)
            
            self.stdout.write(f'✅ FATURA ENCONTRADA:')
            self.stdout.write(f'  ID: {fatura.id}')
            self.stdout.write(f'  UC: {fatura.unidade_consumidora.codigo}')
            self.stdout.write(f'  Cliente: {fatura.unidade_consumidora.customer.nome}')
            self.stdout.write(f'  Mês Referência: {fatura.mes_referencia}')
            self.stdout.write(f'  Valor: {fatura.valor}')
            self.stdout.write(f'  Vencimento: {fatura.vencimento}')
            self.stdout.write(f'  Arquivo: {fatura.arquivo.name if fatura.arquivo else "N/A"}')
            self.stdout.write(f'  Downloaded at: {fatura.downloaded_at}')
            
            # Verificar o usuário associado
            customer = fatura.unidade_consumidora.customer
            user = customer.user
            
            self.stdout.write(f'\n👤 USUÁRIO ASSOCIADO:')
            if user:
                self.stdout.write(f'  User ID: {user.id}')
                self.stdout.write(f'  Username: {user.username}')
                self.stdout.write(f'  Email: {user.email}')
                self.stdout.write(f'  Ativo: {user.is_active}')
            else:
                self.stdout.write(f'  ❌ Nenhum usuário associado ao customer!')
            
            # Testar a lógica da view de edição
            self.stdout.write(f'\n🧪 TESTANDO LÓGICA DA VIEW:')
            
            try:
                # Simular dados de resposta da view GET
                response_data = {
                    "id": fatura.id,
                    "unidade_consumidora": fatura.unidade_consumidora.codigo,
                    "mes_referencia": fatura.mes_referencia.strftime('%b/%Y').upper(),
                    "data_vencimento": fatura.vencimento.strftime('%d/%m/%Y') if fatura.vencimento else '',
                    "valor_total": str(fatura.valor) if fatura.valor else '',
                    "arquivo_url": fatura.arquivo.url if fatura.arquivo else None,
                    "downloaded_at": fatura.downloaded_at.strftime('%d/%m/%Y %H:%M') if fatura.downloaded_at else None
                }
                
                self.stdout.write(f'  ✅ Dados para resposta:')
                for key, value in response_data.items():
                    self.stdout.write(f'    {key}: {value}')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Erro ao processar dados: {str(e)}')
                import traceback
                traceback.print_exc()
            
            # Verificar formatação de datas
            self.stdout.write(f'\n📅 TESTE DE FORMATAÇÃO:')
            
            try:
                if fatura.mes_referencia:
                    mes_ref_formatted = fatura.mes_referencia.strftime('%b/%Y').upper()
                    self.stdout.write(f'  Mês Referência formatado: {mes_ref_formatted}')
                else:
                    self.stdout.write(f'  ⚠️ mes_referencia é None')
                
                if fatura.vencimento:
                    venc_formatted = fatura.vencimento.strftime('%d/%m/%Y')
                    self.stdout.write(f'  Vencimento formatado: {venc_formatted}')
                else:
                    self.stdout.write(f'  ⚠️ vencimento é None')
                
                if fatura.downloaded_at:
                    download_formatted = fatura.downloaded_at.strftime('%d/%m/%Y %H:%M')
                    self.stdout.write(f'  Downloaded formatado: {download_formatted}')
                else:
                    self.stdout.write(f'  ⚠️ downloaded_at é None')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Erro na formatação: {str(e)}')
                import traceback
                traceback.print_exc()
            
            # Verificar arquivo
            self.stdout.write(f'\n📁 VERIFICAÇÃO DE ARQUIVO:')
            try:
                if fatura.arquivo:
                    self.stdout.write(f'  Nome do arquivo: {fatura.arquivo.name}')
                    self.stdout.write(f'  URL do arquivo: {fatura.arquivo.url}')
                    
                    # Verificar se o arquivo existe fisicamente
                    import os
                    if os.path.exists(fatura.arquivo.path):
                        self.stdout.write(f'  ✅ Arquivo existe fisicamente: {fatura.arquivo.path}')
                    else:
                        self.stdout.write(f'  ❌ Arquivo não existe: {fatura.arquivo.path}')
                else:
                    self.stdout.write(f'  ⚠️ Nenhum arquivo associado')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Erro ao verificar arquivo: {str(e)}')
            
            # Simular uma requisição completa
            self.stdout.write(f'\n🔄 SIMULANDO REQUISIÇÃO COMPLETA:')
            
            try:
                from django.test import RequestFactory
                from django.contrib.auth.models import AnonymousUser
                from api.views import edit_fatura
                
                factory = RequestFactory()
                request = factory.get(f'/api/faturas/{fatura_id}/edit/')
                
                # Simular usuário autenticado
                if user:
                    request.user = user
                else:
                    request.user = AnonymousUser()
                
                self.stdout.write(f'  Usuário da requisição: {request.user}')
                self.stdout.write(f'  É autenticado: {request.user.is_authenticated}')
                
                # Chamar a view
                response = edit_fatura(request, fatura_id)
                
                self.stdout.write(f'  ✅ Status da resposta: {response.status_code}')
                
                if response.status_code == 200:
                    self.stdout.write(f'  ✅ Resposta da view: {response.data}')
                else:
                    self.stdout.write(f'  ❌ Erro na view: {response.data}')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Erro ao simular requisição: {str(e)}')
                import traceback
                traceback.print_exc()
                
        except Fatura.DoesNotExist:
            self.stdout.write(f'❌ FATURA NÃO ENCONTRADA: ID {fatura_id}')
            
            # Listar faturas existentes
            faturas = Fatura.objects.all().order_by('-id')[:10]
            self.stdout.write(f'\n📋 ÚLTIMAS 10 FATURAS:')
            for f in faturas:
                self.stdout.write(f'  ID {f.id}: UC {f.unidade_consumidora.codigo}, Cliente: {f.unidade_consumidora.customer.nome}')
                
        except Exception as e:
            self.stdout.write(f'❌ ERRO GERAL: {str(e)}')
            import traceback
            traceback.print_exc()
        
        self.stdout.write('\n' + '='*60)