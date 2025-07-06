# backend/api/management/commands/debug_upload_issues.py

from django.core.management.base import BaseCommand
from api.models import Customer, UnidadeConsumidora, Fatura
from django.db import connection
from datetime import date
import json

class Command(BaseCommand):
    help = 'Debug de problemas de upload de faturas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer-id',
            type=int,
            help='ID do cliente para analisar'
        )
        parser.add_argument(
            '--check-conflicts',
            action='store_true',
            help='Verificar conflitos potenciais'
        )
        parser.add_argument(
            '--clean-duplicates',
            action='store_true',
            help='Limpar faturas duplicadas (USE COM CUIDADO)'
        )

    def handle(self, *args, **options):
        customer_id = options.get('customer_id')
        check_conflicts = options['check_conflicts']
        clean_duplicates = options['clean_duplicates']
        
        self.stdout.write('='*80)
        self.stdout.write('DEBUG - PROBLEMAS DE UPLOAD DE FATURAS')
        self.stdout.write('='*80)
        
        if customer_id:
            self.debug_customer_upload(customer_id)
        elif check_conflicts:
            self.check_all_conflicts()
        elif clean_duplicates:
            self.clean_duplicate_faturas()
        else:
            self.general_health_check()

    def debug_customer_upload(self, customer_id):
        """Debug específico para um cliente"""
        try:
            customer = Customer.objects.get(pk=customer_id)
            self.stdout.write(f'\n🔍 ANALISANDO CLIENTE: {customer.nome} (ID: {customer_id})')
            
            # Verificar UCs
            ucs = customer.unidades_consumidoras.all()
            self.stdout.write(f'\n📋 UNIDADES CONSUMIDORAS: {ucs.count()}')
            
            for uc in ucs:
                self.stdout.write(f'\n  UC: {uc.codigo}')
                self.stdout.write(f'    Ativa: {uc.is_active}')
                self.stdout.write(f'    Tipo: {uc.tipo}')
                
                # Verificar faturas desta UC
                faturas = Fatura.objects.filter(unidade_consumidora=uc).order_by('mes_referencia')
                self.stdout.write(f'    Faturas: {faturas.count()}')
                
                # Verificar duplicatas por mês
                faturas_por_mes = {}
                for fatura in faturas:
                    mes_key = fatura.mes_referencia.strftime('%Y-%m')
                    if mes_key not in faturas_por_mes:
                        faturas_por_mes[mes_key] = []
                    faturas_por_mes[mes_key].append(fatura)
                
                # Reportar duplicatas
                for mes_key, faturas_mes in faturas_por_mes.items():
                    if len(faturas_mes) > 1:
                        self.stdout.write(f'    ⚠️  DUPLICATA em {mes_key}: {len(faturas_mes)} faturas')
                        for fatura in faturas_mes:
                            self.stdout.write(f'        - ID {fatura.id}: {fatura.arquivo.name if fatura.arquivo else "SEM ARQUIVO"}')
                
            # Verificar constraints violadas
            self.check_unique_constraints(customer)
            
        except Customer.DoesNotExist:
            self.stdout.write(f'❌ Cliente {customer_id} não encontrado')

    def check_all_conflicts(self):
        """Verificar conflitos em todo o sistema"""
        self.stdout.write('\n🔍 VERIFICANDO CONFLITOS GLOBAIS...')
        
        # Query para encontrar faturas duplicadas
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    unidade_consumidora_id,
                    mes_referencia,
                    COUNT(*) as count,
                    STRING_AGG(CAST(id AS TEXT), ', ') as fatura_ids
                FROM api_fatura 
                GROUP BY unidade_consumidora_id, mes_referencia
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """)
            
            duplicates = cursor.fetchall()
            
            if duplicates:
                self.stdout.write(f'\n❌ ENCONTRADAS {len(duplicates)} DUPLICATAS:')
                for uc_id, mes_ref, count, fatura_ids in duplicates:
                    try:
                        uc = UnidadeConsumidora.objects.get(id=uc_id)
                        self.stdout.write(f'\n  UC {uc.codigo} (Cliente: {uc.customer.nome}):')
                        self.stdout.write(f'    Mês: {mes_ref}')
                        self.stdout.write(f'    Duplicatas: {count}')
                        self.stdout.write(f'    IDs: {fatura_ids}')
                    except UnidadeConsumidora.DoesNotExist:
                        self.stdout.write(f'  ⚠️ UC ID {uc_id} não encontrada')
            else:
                self.stdout.write('\n✅ Nenhuma duplicata encontrada')

    def clean_duplicate_faturas(self):
        """Limpar faturas duplicadas mantendo a mais recente"""
        self.stdout.write('\n🧹 LIMPANDO FATURAS DUPLICADAS...')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    unidade_consumidora_id,
                    mes_referencia,
                    COUNT(*) as count,
                    STRING_AGG(CAST(id AS TEXT), ', ' ORDER BY created_at DESC) as fatura_ids
                FROM api_fatura 
                GROUP BY unidade_consumidora_id, mes_referencia
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                self.stdout.write('✅ Nenhuma duplicata encontrada para limpar')
                return
            
            # Confirmar ação
            confirm = input(f'\nEncontradas {len(duplicates)} duplicatas. Deseja remover as faturas mais antigas? (digite "SIM" para confirmar): ')
            
            if confirm != 'SIM':
                self.stdout.write('❌ Operação cancelada')
                return
            
            removed_count = 0
            
            for uc_id, mes_ref, count, fatura_ids in duplicates:
                fatura_ids_list = fatura_ids.split(', ')
                # Manter a primeira (mais recente devido ao ORDER BY created_at DESC)
                keep_id = fatura_ids_list[0]
                remove_ids = fatura_ids_list[1:]
                
                self.stdout.write(f'\nUC {uc_id}, Mês {mes_ref}:')
                self.stdout.write(f'  Mantendo: {keep_id}')
                self.stdout.write(f'  Removendo: {", ".join(remove_ids)}')
                
                # Remover faturas duplicadas
                for remove_id in remove_ids:
                    try:
                        fatura = Fatura.objects.get(id=remove_id)
                        fatura.delete()
                        removed_count += 1
                        self.stdout.write(f'    ✅ Removida fatura {remove_id}')
                    except Fatura.DoesNotExist:
                        self.stdout.write(f'    ⚠️ Fatura {remove_id} já foi removida')
            
            self.stdout.write(f'\n✅ {removed_count} faturas duplicadas removidas')

    def check_unique_constraints(self, customer):
        """Verificar violações de constraints únicas"""
        self.stdout.write(f'\n🔒 VERIFICANDO CONSTRAINTS PARA {customer.nome}:')
        
        # Verificar constraint de UC ativa única por cliente
        ucs_ativas = customer.unidades_consumidoras.filter(data_vigencia_fim__isnull=True)
        codigos_uc = {}
        
        for uc in ucs_ativas:
            if uc.codigo in codigos_uc:
                self.stdout.write(f'  ❌ VIOLAÇÃO: Código UC {uc.codigo} duplicado')
                self.stdout.write(f'    UC ID {codigos_uc[uc.codigo]} e UC ID {uc.id}')
            else:
                codigos_uc[uc.codigo] = uc.id
        
        if not codigos_uc or len(codigos_uc) == len(ucs_ativas):
            self.stdout.write('  ✅ Constraints de UC OK')

    def general_health_check(self):
        """Verificação geral de saúde do sistema"""
        self.stdout.write('\n🏥 VERIFICAÇÃO GERAL DE SAÚDE...')
        
        # Estatísticas gerais
        total_customers = Customer.objects.count()
        total_ucs = UnidadeConsumidora.objects.count()
        total_faturas = Fatura.objects.count()
        
        self.stdout.write(f'\n📊 ESTATÍSTICAS:')
        self.stdout.write(f'  Clientes: {total_customers}')
        self.stdout.write(f'  UCs: {total_ucs}')
        self.stdout.write(f'  Faturas: {total_faturas}')
        
        # Verificar faturas sem arquivo
        faturas_sem_arquivo = Fatura.objects.filter(arquivo='').count()
        if faturas_sem_arquivo > 0:
            self.stdout.write(f'  ⚠️ Faturas sem arquivo: {faturas_sem_arquivo}')
        
        # Verificar UCs órfãs
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM api_unidadeconsumidora uc
                WHERE NOT EXISTS (
                    SELECT 1 FROM api_customer c WHERE c.id = uc.customer_id
                )
            """)
            orphan_ucs = cursor.fetchone()[0]
            
            if orphan_ucs > 0:
                self.stdout.write(f'  ❌ UCs órfãs: {orphan_ucs}')
        
        # Verificar faturas órfãs
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM api_fatura f
                WHERE NOT EXISTS (
                    SELECT 1 FROM api_unidadeconsumidora uc WHERE uc.id = f.unidade_consumidora_id
                )
            """)
            orphan_faturas = cursor.fetchone()[0]
            
            if orphan_faturas > 0:
                self.stdout.write(f'  ❌ Faturas órfãs: {orphan_faturas}')
        
        self.stdout.write('\n✅ Verificação concluída')
        
        # Sugestões
        self.stdout.write('\n💡 COMANDOS ÚTEIS:')
        self.stdout.write('  python manage.py debug_upload_issues --customer-id X')
        self.stdout.write('  python manage.py debug_upload_issues --check-conflicts')
        self.stdout.write('  python manage.py debug_upload_issues --clean-duplicates')