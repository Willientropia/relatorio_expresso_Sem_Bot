# backend/api/management/commands/test_date_fixes.py

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from api.models import Customer, UnidadeConsumidora, Fatura
from api.views import parse_brazilian_date, parse_mes_referencia
from datetime import date
import tempfile
import os

class Command(BaseCommand):
    help = 'Testa as correções de formato de data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['parse_dates', 'upload_simulation', 'create_test_data'],
            default='parse_dates',
            help='Tipo de teste a executar'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        
        if test_type == 'parse_dates':
            self.test_date_parsing()
        elif test_type == 'upload_simulation':
            self.test_upload_simulation()
        elif test_type == 'create_test_data':
            self.create_test_data()

    def test_date_parsing(self):
        """Testa as funções de parsing de data"""
        self.stdout.write('🧪 TESTANDO FUNÇÕES DE PARSING DE DATA')
        self.stdout.write('='*50)
        
        # Testar parse_brazilian_date
        self.stdout.write('\n📅 Testando parse_brazilian_date:')
        date_tests = [
            "15/03/2025",
            "28/03/2025", 
            "17/04/2025",
            "01/12/2024",
            "31/01/25",  # Ano de 2 dígitos
            "2025-03-15",  # Formato ISO
            "invalid_date",
            "",
            None
        ]
        
        for test_date in date_tests:
            try:
                result = parse_brazilian_date(test_date)
                status = "✅" if result else "❌"
                self.stdout.write(f"  {status} '{test_date}' → {result}")
            except Exception as e:
                self.stdout.write(f"  ❌ '{test_date}' → ERRO: {e}")
        
        # Testar parse_mes_referencia
        self.stdout.write('\n📅 Testando parse_mes_referencia:')
        month_tests = [
            "MAI/2025",
            "MARÇO/2024", 
            "JAN/25",
            "03/2025",
            "MAIO/2024",
            "DEZ/2023",
            "invalid_month",
            "13/2025",  # Mês inválido
            ""
        ]
        
        for test_month in month_tests:
            try:
                result = parse_mes_referencia(test_month)
                status = "✅" if result else "❌"
                self.stdout.write(f"  {status} '{test_month}' → {result}")
            except Exception as e:
                self.stdout.write(f"  ❌ '{test_month}' → ERRO: {e}")

    def test_upload_simulation(self):
        """Simula upload com diferentes formatos de data"""
        self.stdout.write('🧪 SIMULANDO UPLOAD COM DIFERENTES FORMATOS')
        self.stdout.write('='*55)
        
        # Dados de teste simulados
        test_extractions = [
            {
                "nome": "Fatura Normal",
                "dados": {
                    "unidade_consumidora": "123456",
                    "mes_referencia": "MAI/2025",
                    "data_vencimento": "15/06/2025",
                    "valor_total": "150.75"
                }
            },
            {
                "nome": "Fatura com Ano Curto",
                "dados": {
                    "unidade_consumidora": "123456",
                    "mes_referencia": "JUN/25",
                    "data_vencimento": "17/07/25",
                    "valor_total": "200.50"
                }
            },
            {
                "nome": "Fatura com Data Problemática",
                "dados": {
                    "unidade_consumidora": "123456",
                    "mes_referencia": "28/03/2025",  # Formato errado
                    "data_vencimento": "2025-04-15",  # Formato ISO
                    "valor_total": "175.25"
                }
            }
        ]
        
        for i, test_case in enumerate(test_extractions, 1):
            self.stdout.write(f'\n📋 Teste {i}: {test_case["nome"]}')
            self.stdout.write('-' * 40)
            
            dados = test_case["dados"]
            
            # Testar processamento do mês de referência
            mes_ref_original = dados.get("mes_referencia")
            mes_ref_processado = parse_mes_referencia(mes_ref_original)
            
            self.stdout.write(f"  Mês Original: '{mes_ref_original}'")
            self.stdout.write(f"  Mês Processado: {mes_ref_processado}")
            
            # Testar processamento da data de vencimento
            data_venc_original = dados.get("data_vencimento")
            data_venc_processada = parse_brazilian_date(data_venc_original)
            
            self.stdout.write(f"  Data Venc. Original: '{data_venc_original}'")
            self.stdout.write(f"  Data Venc. Processada: {data_venc_processada}")
            
            # Resultado final
            if mes_ref_processado and data_venc_processada:
                self.stdout.write(f"  ✅ PROCESSAMENTO OK")
            else:
                self.stdout.write(f"  ❌ PROBLEMA NO PROCESSAMENTO")

    def create_test_data(self):
        """Cria dados de teste para validar as correções"""
        self.stdout.write('🏗️ CRIANDO DADOS DE TESTE PARA VALIDAÇÃO')
        self.stdout.write('='*50)
        
        # Verificar se já existem dados de teste
        existing_customer = Customer.objects.filter(nome__icontains='[TESTE-DATA]').first()
        if existing_customer:
            self.stdout.write('⚠️ Dados de teste já existem. Removendo...')
            Customer.objects.filter(nome__icontains='[TESTE-DATA]').delete()
        
        # Criar usuário de teste
        from django.contrib.auth.models import User
        user, created = User.objects.get_or_create(
            username='teste_data_fixes',
            defaults={
                'email': 'teste.data@fixes.com',
                'first_name': 'Teste',
                'last_name': 'Data Fixes'
            }
        )
        
        # Criar cliente
        customer = Customer.objects.create(
            nome='Cliente Teste Data [TESTE-DATA]',
            cpf='123.456.789-99',
            endereco='Rua Teste, 123',
            user=user
        )
        
        # Criar UC
        uc = UnidadeConsumidora.objects.create(
            customer=customer,
            codigo='UC-DATA-TEST',
            endereco='Rua Teste, 123',
            tipo='Residencial'
        )
        
        # Criar faturas com diferentes formatos de data para testar
        test_faturas = [
            {
                "mes_ref": date(2025, 3, 1),
                "vencimento": date(2025, 4, 15),
                "valor": 150.75
            },
            {
                "mes_ref": date(2025, 4, 1),
                "vencimento": date(2025, 5, 17),
                "valor": 200.50
            }
        ]
        
        for i, fatura_data in enumerate(test_faturas, 1):
            Fatura.objects.create(
                unidade_consumidora=uc,
                mes_referencia=fatura_data["mes_ref"],
                vencimento=fatura_data["vencimento"],
                valor=fatura_data["valor"]
            )
            
            self.stdout.write(f"  ✅ Fatura {i} criada: {fatura_data['mes_ref'].strftime('%m/%Y')}")
        
        self.stdout.write(f'\n✅ Dados de teste criados:')
        self.stdout.write(f'   Cliente: {customer.nome} (ID: {customer.id})')
        self.stdout.write(f'   UC: {uc.codigo}')
        self.stdout.write(f'   Faturas: {len(test_faturas)}')
        
        self.stdout.write(f'\n💡 Para testar upload:')
        self.stdout.write(f'   1. Acesse o cliente ID {customer.id}')
        self.stdout.write(f'   2. Tente fazer upload de fatura para UC {uc.codigo}')
        self.stdout.write(f'   3. Use datas como "MAI/2025" e "15/06/2025"')
        
        self.stdout.write(f'\n🧹 Para limpar:')
        self.stdout.write(f'   python manage.py shell -c "from api.models import Customer; Customer.objects.filter(nome__icontains=\'[TESTE-DATA]\').delete()"')

    def test_extraction_script(self):
        """Testa o script de extração com datas"""
        self.stdout.write('🧪 TESTANDO SCRIPT DE EXTRAÇÃO')
        self.stdout.write('='*40)
        
        # Criar PDF de teste simples
        test_text = """
        CFOP 1234: Teste
        MAI/2025 15/06/2025
        UC: 123456
        Valor Total: R$ 150,75
        CNPJ/CPF: 123.456.789-00
        """
        
        try:
            # Simular extração
            from scripts.extract_fatura_data import extract_data_from_text
            
            result = extract_data_from_text(test_text)
            
            self.stdout.write('📊 Resultado da extração:')
            for key, value in result.items():
                if key in ['mes_referencia', 'data_vencimento', 'valor_total', 'unidade_consumidora']:
                    status = "✅" if value else "❌"
                    self.stdout.write(f"  {status} {key}: '{value}'")
            
            # Verificar se as datas estão no formato correto
            data_venc = result.get('data_vencimento')
            if data_venc and '/' in data_venc and len(data_venc) == 10:
                self.stdout.write(f"  ✅ Data de vencimento no formato brasileiro: {data_venc}")
            else:
                self.stdout.write(f"  ❌ Data de vencimento em formato incorreto: {data_venc}")
                
        except Exception as e:
            self.stdout.write(f'❌ Erro no teste de extração: {e}')

# Função auxiliar para importar as funções do views.py
def import_view_functions():
    """Importa as funções corrigidas das views"""
    try:
        from api.views import parse_brazilian_date, parse_mes_referencia
        return True
    except ImportError as e:
        print(f"Erro ao importar funções: {e}")
        return False