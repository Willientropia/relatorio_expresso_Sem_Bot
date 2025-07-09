# backend/api/management/commands/test_force_upload.py

from django.core.management.base import BaseCommand
from api.models import Customer, UnidadeConsumidora, Fatura
from datetime import date, datetime
from django.utils import timezone
import tempfile
import os

class Command(BaseCommand):
    help = 'Testa a funcionalidade de força upload de faturas'

    def add_arguments(self, parser):
        parser.add_argument('customer_id', type=int, help='ID do cliente')
        parser.add_argument('--uc-codigo', type=str, default='1340008741', help='Código da UC')
        parser.add_argument('--mes', type=int, default=3, help='Mês (1-12)')
        parser.add_argument('--ano', type=int, default=2025, help='Ano')
        parser.add_argument('--valor', type=str, default='10.00', help='Valor da fatura')

    def handle(self, *args, **options):
        customer_id = options['customer_id']
        uc_codigo = options['uc_codigo']
        mes = options['mes']
        ano = options['ano']
        valor = options['valor']

        try:
            customer = Customer.objects.get(pk=customer_id)
            self.stdout.write(f'🧪 TESTE DE FORÇA UPLOAD')
            self.stdout.write(f'Cliente: {customer.nome} (ID: {customer_id})')
            self.stdout.write(f'UC: {uc_codigo}')
            self.stdout.write(f'Período: {mes:02d}/{ano}')
            self.stdout.write(f'Valor: R$ {valor}')
            self.stdout.write('='*50)

            # Buscar UC
            uc = customer.unidades_consumidoras.filter(codigo=uc_codigo).first()
            if not uc:
                self.stdout.write(f'❌ UC {uc_codigo} não encontrada para este cliente')
                return

            self.stdout.write(f'✅ UC encontrada: {uc.codigo} - {uc.endereco}')

            # Verificar se já existe fatura
            mes_referencia = date(ano, mes, 1)
            fatura_existente = Fatura.objects.filter(
                unidade_consumidora=uc,
                mes_referencia=mes_referencia
            ).first()

            if fatura_existente:
                self.stdout.write(f'⚠️ FATURA EXISTENTE:')
                self.stdout.write(f'   ID: {fatura_existente.id}')
                self.stdout.write(f'   Valor atual: R$ {fatura_existente.valor}')
                self.stdout.write(f'   Vencimento atual: {fatura_existente.vencimento}')
                self.stdout.write(f'   Arquivo: {fatura_existente.arquivo.name if fatura_existente.arquivo else "N/A"}')
                
                # Deletar fatura existente (simulando o comportamento da view)
                self.stdout.write(f'🗑️ Removendo fatura existente...')
                fatura_existente.delete()
                self.stdout.write(f'✅ Fatura existente removida')

            # Criar arquivo temporário simulando upload
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(b'%PDF-1.4 fake content for testing')
                temp_file_path = temp_file.name

            # Criar nova fatura
            self.stdout.write(f'📄 Criando nova fatura...')
            
            try:
                # Processar dados como a view faria
                data_vencimento = None
                if mes == 3:  # Março
                    data_vencimento = date(ano, 4, 20)  # 20/04/2025
                
                valor_decimal = float(valor.replace(',', '.'))
                
                nova_fatura = Fatura.objects.create(
                    unidade_consumidora=uc,
                    mes_referencia=mes_referencia,
                    valor=valor_decimal,
                    vencimento=data_vencimento,
                    downloaded_at=timezone.now()
                )
                
                self.stdout.write(f'✅ NOVA FATURA CRIADA:')
                self.stdout.write(f'   ID: {nova_fatura.id}')
                self.stdout.write(f'   UC: {nova_fatura.unidade_consumidora.codigo}')
                self.stdout.write(f'   Mês: {nova_fatura.mes_referencia}')
                self.stdout.write(f'   Valor: R$ {nova_fatura.valor}')
                self.stdout.write(f'   Vencimento: {nova_fatura.vencimento}')
                self.stdout.write(f'   Criada em: {nova_fatura.created_at}')
                
                # Verificar se foi salva corretamente
                fatura_verificacao = Fatura.objects.filter(
                    unidade_consumidora=uc,
                    mes_referencia=mes_referencia
                ).first()
                
                if fatura_verificacao:
                    self.stdout.write(f'✅ VERIFICAÇÃO: Fatura encontrada no banco')
                    self.stdout.write(f'   Valor verificado: R$ {fatura_verificacao.valor}')
                    self.stdout.write(f'   Vencimento verificado: {fatura_verificacao.vencimento}')
                else:
                    self.stdout.write(f'❌ ERRO: Fatura não encontrada na verificação!')
                
            finally:
                # Limpar arquivo temporário
                os.unlink(temp_file_path)

            self.stdout.write(f'\n🧪 TESTE CONCLUÍDO')
            self.stdout.write(f'💡 Agora teste no frontend para ver se os valores aparecem corretamente')

        except Customer.DoesNotExist:
            self.stdout.write(f'❌ Cliente {customer_id} não encontrado')
        except Exception as e:
            self.stdout.write(f'❌ Erro durante o teste: {str(e)}')
            import traceback
            traceback.print_exc()