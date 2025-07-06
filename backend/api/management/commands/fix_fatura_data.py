# backend/api/management/commands/fix_fatura_data.py

from django.core.management.base import BaseCommand
from api.models import Fatura
from datetime import date
import re

class Command(BaseCommand):
    help = 'Corrige dados de faturas baseado no nome do arquivo'

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
        
        # Dicionário de meses
        MESES_MAP = {
            'JAN': 1, 'JANEIRO': 1,
            'FEV': 2, 'FEVEREIRO': 2, 'FEB': 2,
            'MAR': 3, 'MARÇO': 3, 'MARCO': 3,
            'ABR': 4, 'ABRIL': 4, 'APR': 4,
            'MAI': 5, 'MAIO': 5, 'MAY': 5,
            'JUN': 6, 'JUNHO': 6,
            'JUL': 7, 'JULHO': 7,
            'AGO': 8, 'AGOSTO': 8, 'AUG': 8,
            'SET': 9, 'SETEMBRO': 9, 'SEP': 9,
            'OUT': 10, 'OUTUBRO': 10, 'OCT': 10,
            'NOV': 11, 'NOVEMBRO': 11,
            'DEZ': 12, 'DEZEMBRO': 12, 'DEC': 12
        }
        
        # Filtrar faturas
        if fatura_id:
            faturas = Fatura.objects.filter(id=fatura_id)
        else:
            faturas = Fatura.objects.all()
        
        self.stdout.write(f'Analisando {faturas.count()} fatura(s)...')
        
        faturas_corrigidas = 0
        faturas_com_problema = 0
        
        for fatura in faturas:
            try:
                arquivo_nome = fatura.arquivo.name if fatura.arquivo else ''
                self.stdout.write(f'\nFatura ID {fatura.id}:')
                self.stdout.write(f'  Arquivo: {arquivo_nome}')
                self.stdout.write(f'  Mês atual: {fatura.mes_referencia}')
                
                # Tentar extrair mês e ano do nome do arquivo
                mes_detectado = None
                ano_detectado = None
                
                # Buscar padrões de mês
                arquivo_upper = arquivo_nome.upper()
                for mes_str, mes_num in MESES_MAP.items():
                    if mes_str in arquivo_upper:
                        mes_detectado = mes_num
                        self.stdout.write(f'  Mês detectado: {mes_str} ({mes_num})')
                        break
                
                # Buscar ano (formato 20XX)
                ano_match = re.search(r'20\d{2}', arquivo_nome)
                if ano_match:
                    ano_detectado = int(ano_match.group())
                    self.stdout.write(f'  Ano detectado: {ano_detectado}')
                
                # Verificar se há discrepância
                mes_atual = fatura.mes_referencia.month
                ano_atual = fatura.mes_referencia.year
                
                correcao_necessaria = False
                nova_data = None
                
                if mes_detectado and mes_detectado != mes_atual:
                    self.stdout.write(f'  ❌ DISCREPÂNCIA NO MÊS: arquivo sugere {mes_detectado}, banco tem {mes_atual}')
                    correcao_necessaria = True
                
                if ano_detectado and ano_detectado != ano_atual:
                    self.stdout.write(f'  ❌ DISCREPÂNCIA NO ANO: arquivo sugere {ano_detectado}, banco tem {ano_atual}')
                    correcao_necessaria = True
                
                if correcao_necessaria:
                    # Usar dados detectados ou manter atuais
                    novo_mes = mes_detectado if mes_detectado else mes_atual
                    novo_ano = ano_detectado if ano_detectado else ano_atual
                    
                    nova_data = date(novo_ano, novo_mes, 1)
                    
                    self.stdout.write(f'  🔧 CORREÇÃO: {fatura.mes_referencia} → {nova_data}')
                    
                    if not dry_run:
                        fatura.mes_referencia = nova_data
                        fatura.save()
                        self.stdout.write(f'  ✅ CORRIGIDA!')
                    else:
                        self.stdout.write(f'  🔄 SERIA CORRIGIDA (dry-run)')
                    
                    faturas_corrigidas += 1
                else:
                    self.stdout.write(f'  ✅ OK - sem discrepâncias')
                
            except Exception as e:
                self.stdout.write(f'  ❌ ERRO: {str(e)}')
                faturas_com_problema += 1
        
        # Resumo
        self.stdout.write('\n' + '='*50)
        self.stdout.write('RESUMO:')
        self.stdout.write(f'Faturas analisadas: {faturas.count()}')
        self.stdout.write(f'Faturas corrigidas: {faturas_corrigidas}')
        self.stdout.write(f'Faturas com problema: {faturas_com_problema}')
        
        if dry_run and faturas_corrigidas > 0:
            self.stdout.write(
                self.style.WARNING('\nEste foi um DRY RUN - execute sem --dry-run para aplicar as correções')
            )
        elif faturas_corrigidas > 0:
            self.stdout.write(
                self.style.SUCCESS('\nCorreções aplicadas com sucesso!')
            )