# backend/api/management/commands/fix_month_discrepancy.py

from django.core.management.base import BaseCommand
from api.models import Fatura
import subprocess
import sys
import json
import os
from django.conf import settings
from datetime import date
from django.db import transaction

class Command(BaseCommand):
    help = 'Corrige divergências entre mês extraído do PDF e mês salvo no banco'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria alterado sem fazer alterações reais'
        )
        parser.add_argument(
            '--fatura-id',
            type=int,
            help='ID específico da fatura para corrigir'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fatura_id = options.get('fatura_id')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY RUN - Nenhuma alteração será feita')
            )
        
        # Mapeamento de meses
        MESES_MAP = {
            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
        }
        
        # Filtrar faturas
        if fatura_id:
            faturas = Fatura.objects.filter(id=fatura_id)
        else:
            faturas = Fatura.objects.all()
        
        self.stdout.write(f'Analisando {faturas.count()} fatura(s)...')
        
        faturas_corrigidas = 0
        faturas_com_erro = 0
        problemas_encontrados = []
        
        for fatura in faturas:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'ANALISANDO FATURA ID: {fatura.id}')
            self.stdout.write(f'{"="*60}')
            
            if not fatura.arquivo:
                self.stdout.write('❌ Fatura sem arquivo - pulando')
                continue
            
            try:
                arquivo_path = fatura.arquivo.path
                
                if not os.path.exists(arquivo_path):
                    self.stdout.write(f'❌ Arquivo não encontrado: {arquivo_path}')
                    faturas_com_erro += 1
                    continue
                
                # Extrair dados do PDF
                script_path = os.path.join(settings.BASE_DIR, 'scripts', 'extract_fatura_data.py')
                
                result = subprocess.run(
                    [sys.executable, script_path, arquivo_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    self.stdout.write(f'❌ Erro na extração: {result.stderr}')
                    faturas_com_erro += 1
                    continue
                
                extracted_data = json.loads(result.stdout)
                
                if extracted_data.get('status') != 'success':
                    self.stdout.write(f'❌ Extração falhou: {extracted_data.get("erro", "Erro desconhecido")}')
                    faturas_com_erro += 1
                    continue
                
                # Dados atuais
                mes_atual = fatura.mes_referencia.month
                ano_atual = fatura.mes_referencia.year
                
                # Dados extraídos
                mes_ref_extraido = extracted_data.get('mes_referencia')
                
                self.stdout.write(f'📊 DADOS ATUAIS:')
                self.stdout.write(f'  UC: {fatura.unidade_consumidora.codigo}')
                self.stdout.write(f'  Mês/Ano no banco: {mes_atual}/{ano_atual}')
                self.stdout.write(f'  Data completa: {fatura.mes_referencia}')
                
                self.stdout.write(f'\n📤 DADOS EXTRAÍDOS:')
                self.stdout.write(f'  Mês de referência: {mes_ref_extraido}')
                self.stdout.write(f'  UC extraída: {extracted_data.get("unidade_consumidora")}')
                self.stdout.write(f'  Valor extraído: {extracted_data.get("valor_total")}')
                self.stdout.write(f'  Data vencimento: {extracted_data.get("data_vencimento")}')
                
                # Verificar divergência no mês
                if mes_ref_extraido:
                    try:
                        # Formato: MAI/2025
                        mes_str, ano_str = mes_ref_extraido.split('/')
                        mes_extraido = MESES_MAP.get(mes_str.upper())
                        ano_extraido = int(ano_str)
                        
                        if mes_extraido and (mes_extraido != mes_atual or ano_extraido != ano_atual):
                            self.stdout.write(f'\n❌ DIVERGÊNCIA ENCONTRADA!')
                            self.stdout.write(f'  PDF diz: {mes_str}/{ano_str} (mês {mes_extraido})')
                            self.stdout.write(f'  Banco tem: mês {mes_atual}/{ano_atual}')
                            
                            # Preparar correção
                            nova_data = date(ano_extraido, mes_extraido, 1)
                            
                            problema = {
                                'fatura_id': fatura.id,
                                'uc': fatura.unidade_consumidora.codigo,
                                'data_atual': fatura.mes_referencia,
                                'data_correta': nova_data,
                                'mes_ref_pdf': mes_ref_extraido
                            }
                            problemas_encontrados.append(problema)
                            
                            self.stdout.write(f'🔧 CORREÇÃO: {fatura.mes_referencia} → {nova_data}')
                            
                            if not dry_run:
                                # Verificar se já existe fatura para esta UC neste mês
                                fatura_existente = Fatura.objects.filter(
                                    unidade_consumidora=fatura.unidade_consumidora,
                                    mes_referencia=nova_data
                                ).exclude(id=fatura.id).first()
                                
                                if fatura_existente:
                                    self.stdout.write(f'⚠️ CONFLITO: Já existe fatura para UC {fatura.unidade_consumidora.codigo} em {nova_data}')
                                    self.stdout.write(f'   Fatura existente ID: {fatura_existente.id}')
                                    self.stdout.write(f'   Você precisa decidir qual manter manualmente')
                                    faturas_com_erro += 1
                                    continue
                                
                                # Aplicar correção
                                fatura.mes_referencia = nova_data
                                fatura.save()
                                
                                self.stdout.write(f'✅ CORRIGIDA!')
                                faturas_corrigidas += 1
                            else:
                                self.stdout.write(f'🔄 SERIA CORRIGIDA (dry-run)')
                                faturas_corrigidas += 1
                        else:
                            self.stdout.write(f'✅ Mês consistente: {mes_ref_extraido}')
                            
                    except (ValueError, KeyError) as e:
                        self.stdout.write(f'❌ Erro ao processar mês extraído: {e}')
                        faturas_com_erro += 1
                else:
                    self.stdout.write(f'⚠️ Mês de referência não extraído do PDF')
                
            except Exception as e:
                self.stdout.write(f'❌ Erro ao processar fatura {fatura.id}: {str(e)}')
                faturas_com_erro += 1
        
        # Resumo final
        self.stdout.write('\n' + '='*80)
        self.stdout.write('RESUMO FINAL')
        self.stdout.write('='*80)
        
        self.stdout.write(f'Faturas analisadas: {faturas.count()}')
        self.stdout.write(f'Problemas encontrados: {len(problemas_encontrados)}')
        self.stdout.write(f'Faturas corrigidas: {faturas_corrigidas}')
        self.stdout.write(f'Faturas com erro: {faturas_com_erro}')
        
        if problemas_encontrados:
            self.stdout.write(f'\n📋 LISTA DE PROBLEMAS ENCONTRADOS:')
            for problema in problemas_encontrados:
                self.stdout.write(f'  • Fatura {problema["fatura_id"]} (UC {problema["uc"]}):')
                self.stdout.write(f'    {problema["data_atual"]} → {problema["data_correta"]} ({problema["mes_ref_pdf"]})')
        
        if dry_run and faturas_corrigidas > 0:
            self.stdout.write(
                self.style.WARNING('\nEste foi um DRY RUN - execute sem --dry-run para aplicar as correções')
            )
        elif faturas_corrigidas > 0:
            self.stdout.write(
                self.style.SUCCESS('\nCorreções aplicadas com sucesso!')
            )
            self.stdout.write('Execute o frontend novamente para ver as faturas nos meses corretos.')
        else:
            self.stdout.write('Nenhuma correção necessária.')