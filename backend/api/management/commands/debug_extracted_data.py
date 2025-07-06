# backend/api/management/commands/debug_extracted_data.py

from django.core.management.base import BaseCommand
from api.models import Fatura
import subprocess
import sys
import json
import tempfile
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Debug dos dados extraídos vs dados salvos nas faturas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fatura-id',
            type=int,
            help='ID específico da fatura para analisar'
        )
        parser.add_argument(
            '--reextract',
            action='store_true',
            help='Reextrair dados do PDF atual'
        )

    def handle(self, *args, **options):
        fatura_id = options.get('fatura_id')
        reextract = options['reextract']
        
        if fatura_id:
            faturas = Fatura.objects.filter(id=fatura_id)
        else:
            faturas = Fatura.objects.all().order_by('-created_at')[:10]  # Últimas 10
        
        self.stdout.write('='*80)
        self.stdout.write('DEBUG - DADOS EXTRAÍDOS VS DADOS SALVOS')
        self.stdout.write('='*80)
        
        for fatura in faturas:
            self.stdout.write(f'\n{"="*50}')
            self.stdout.write(f'FATURA ID: {fatura.id}')
            self.stdout.write(f'{"="*50}')
            
            # Dados salvos no banco
            self.stdout.write('\n📊 DADOS SALVOS NO BANCO:')
            self.stdout.write(f'  UC: {fatura.unidade_consumidora.codigo}')
            self.stdout.write(f'  Cliente: {fatura.unidade_consumidora.customer.nome}')
            self.stdout.write(f'  Mês Referência: {fatura.mes_referencia}')
            self.stdout.write(f'  Mês Número: {fatura.mes_referencia.month}')
            self.stdout.write(f'  Ano: {fatura.mes_referencia.year}')
            self.stdout.write(f'  Valor: {fatura.valor}')
            self.stdout.write(f'  Vencimento: {fatura.vencimento}')
            self.stdout.write(f'  Arquivo: {fatura.arquivo.name if fatura.arquivo else "N/A"}')
            self.stdout.write(f'  Criado em: {fatura.created_at}')
            
            # Tentar reextrair dados se solicitado
            if reextract and fatura.arquivo:
                self.stdout.write('\n🔍 REEXTRAINDO DADOS DO PDF ATUAL:')
                
                try:
                    # Caminho do arquivo
                    arquivo_path = fatura.arquivo.path
                    
                    if os.path.exists(arquivo_path):
                        self.stdout.write(f'  Arquivo encontrado: {arquivo_path}')
                        
                        # Executar script de extração
                        script_path = os.path.join(settings.BASE_DIR, 'scripts', 'extract_fatura_data.py')
                        
                        result = subprocess.run(
                            [sys.executable, script_path, arquivo_path],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if result.returncode == 0:
                            try:
                                extracted_data = json.loads(result.stdout)
                                
                                self.stdout.write('\n📤 DADOS EXTRAÍDOS AGORA:')
                                for key, value in extracted_data.items():
                                    if key != 'dados_completos':  # Evitar dados muito verbosos
                                        self.stdout.write(f'  {key}: {value}')
                                
                                # Comparar dados críticos
                                self.stdout.write('\n⚖️ COMPARAÇÃO:')
                                
                                # Mês de referência
                                mes_extraido = extracted_data.get('mes_referencia')
                                if mes_extraido:
                                    self.stdout.write(f'  Mês no PDF: {mes_extraido}')
                                    self.stdout.write(f'  Mês no banco: {fatura.mes_referencia.strftime("%b/%Y").upper()}')
                                    if mes_extraido != fatura.mes_referencia.strftime("%b/%Y").upper():
                                        self.stdout.write(f'  ❌ DIVERGÊNCIA NO MÊS!')
                                    else:
                                        self.stdout.write(f'  ✅ Mês consistente')
                                
                                # UC
                                uc_extraida = extracted_data.get('unidade_consumidora')
                                if uc_extraida:
                                    self.stdout.write(f'  UC no PDF: {uc_extraida}')
                                    self.stdout.write(f'  UC no banco: {fatura.unidade_consumidora.codigo}')
                                    if uc_extraida != fatura.unidade_consumidora.codigo:
                                        self.stdout.write(f'  ❌ DIVERGÊNCIA NA UC!')
                                    else:
                                        self.stdout.write(f'  ✅ UC consistente')
                                
                                # Valor
                                valor_extraido = extracted_data.get('valor_total')
                                if valor_extraido:
                                    self.stdout.write(f'  Valor no PDF: {valor_extraido}')
                                    self.stdout.write(f'  Valor no banco: {fatura.valor}')
                                    if str(valor_extraido) != str(fatura.valor):
                                        self.stdout.write(f'  ❌ DIVERGÊNCIA NO VALOR!')
                                    else:
                                        self.stdout.write(f'  ✅ Valor consistente')
                                
                                # Data de vencimento
                                venc_extraido = extracted_data.get('data_vencimento')
                                if venc_extraido and fatura.vencimento:
                                    self.stdout.write(f'  Vencimento no PDF: {venc_extraido}')
                                    self.stdout.write(f'  Vencimento no banco: {fatura.vencimento.strftime("%d/%m/%Y")}')
                                    if venc_extraido != fatura.vencimento.strftime("%d/%m/%Y"):
                                        self.stdout.write(f'  ❌ DIVERGÊNCIA NO VENCIMENTO!')
                                    else:
                                        self.stdout.write(f'  ✅ Vencimento consistente')
                                
                            except json.JSONDecodeError:
                                self.stdout.write(f'  ❌ Erro ao decodificar JSON da extração')
                                self.stdout.write(f'  Output: {result.stdout}')
                        else:
                            self.stdout.write(f'  ❌ Erro na extração: {result.stderr}')
                    else:
                        self.stdout.write(f'  ❌ Arquivo não encontrado: {arquivo_path}')
                        
                except Exception as e:
                    self.stdout.write(f'  ❌ Erro ao reextrair: {str(e)}')
            
            # Análise do nome do arquivo
            if fatura.arquivo:
                arquivo_nome = fatura.arquivo.name
                self.stdout.write(f'\n📁 ANÁLISE DO NOME DO ARQUIVO:')
                self.stdout.write(f'  Nome: {arquivo_nome}')
                
                # Extrair informações do path
                path_parts = arquivo_nome.split('/')
                if len(path_parts) >= 3:
                    ano_pasta = path_parts[1] if path_parts[1].isdigit() else 'N/A'
                    mes_pasta = path_parts[2] if path_parts[2].isdigit() else 'N/A'
                    
                    self.stdout.write(f'  Ano na pasta: {ano_pasta}')
                    self.stdout.write(f'  Mês na pasta: {mes_pasta}')
                    
                    if ano_pasta.isdigit() and ano_pasta != str(fatura.mes_referencia.year):
                        self.stdout.write(f'  ❌ DIVERGÊNCIA: Ano da pasta ({ano_pasta}) != Ano do banco ({fatura.mes_referencia.year})')
                    
                    if mes_pasta.isdigit() and int(mes_pasta) != fatura.mes_referencia.month:
                        self.stdout.write(f'  ❌ DIVERGÊNCIA: Mês da pasta ({mes_pasta}) != Mês do banco ({fatura.mes_referencia.month})')
                        self.stdout.write(f'  📅 Mês da pasta seria: {self.get_month_name(int(mes_pasta)) if mes_pasta.isdigit() else "N/A"}')
                        self.stdout.write(f'  📅 Mês do banco é: {self.get_month_name(fatura.mes_referencia.month)}')
            
            self.stdout.write('\n' + '-'*50)
    
    def get_month_name(self, month_num):
        """Converte número do mês para nome"""
        months = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        return months.get(month_num, f'Mês {month_num}')