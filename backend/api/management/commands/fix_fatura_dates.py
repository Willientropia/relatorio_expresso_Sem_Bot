# backend/api/management/commands/fix_fatura_dates.py

from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Fatura
from datetime import datetime, date
import re

class Command(BaseCommand):
    help = 'Corrige o formato das datas de mês de referência das faturas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria alterado sem fazer alterações reais'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO DRY RUN - Nenhuma alteração será feita')
            )
        
        # Buscar todas as faturas
        faturas = Fatura.objects.all()
        
        self.stdout.write(f'Encontradas {faturas.count()} faturas para analisar')
        
        faturas_corrigidas = 0
        faturas_com_erro = 0
        
        with transaction.atomic():
            for fatura in faturas:
                try:
                    # Verificar se a data está no formato correto (primeiro dia do mês)
                    if fatura.mes_referencia.day != 1:
                        self.stdout.write(
                            f'Fatura {fatura.id}: Data atual {fatura.mes_referencia} '
                            f'- UC {fatura.unidade_consumidora.codigo}'
                        )
                        
                        # Corrigir para primeiro dia do mês
                        nova_data = date(
                            fatura.mes_referencia.year, 
                            fatura.mes_referencia.month, 
                            1
                        )
                        
                        if not dry_run:
                            fatura.mes_referencia = nova_data
                            fatura.save()
                        
                        self.stdout.write(
                            f'  -> Corrigida para: {nova_data}'
                        )
                        
                        faturas_corrigidas += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Erro ao processar fatura {fatura.id}: {str(e)}'
                        )
                    )
                    faturas_com_erro += 1
        
        # Resumo
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Faturas analisadas: {faturas.count()}')
        self.stdout.write(
            self.style.SUCCESS(f'Faturas corrigidas: {faturas_corrigidas}')
        )
        
        if faturas_com_erro > 0:
            self.stdout.write(
                self.style.ERROR(f'Faturas com erro: {faturas_com_erro}')
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nEste foi um DRY RUN - nenhuma alteração foi feita')
            )
            self.stdout.write('Execute sem --dry-run para aplicar as correções')
        else:
            self.stdout.write(
                self.style.SUCCESS('\nCorreções aplicadas com sucesso!')
            )