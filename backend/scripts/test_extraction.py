# backend/scripts/test_extraction.py
"""
Script para testar a extração de dados de faturas localmente
Uso: python test_extraction.py caminho/para/fatura.pdf
"""

import sys
import os
import json
from extract_fatura_data import process_single_pdf

def test_single_pdf(pdf_path):
    """Testa a extração de dados de um único PDF."""
    print(f"📄 Testando extração do arquivo: {pdf_path}")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    try:
        result = process_single_pdf(pdf_path)
        
        if result.get('status') == 'success':
            print("✅ Extração bem-sucedida!")
            print("\n📊 DADOS EXTRAÍDOS:")
            print("-" * 40)
            
            # Campos principais
            main_fields = [
                'unidade_consumidora',
                'cpf_cnpj', 
                'nome_cliente',
                'mes_referencia',
                'data_vencimento',
                'valor_total',
                'consumo_kwh'
            ]
            
            print("🔍 INFORMAÇÕES PRINCIPAIS:")
            for field in main_fields:
                value = result.get(field, 'N/A')
                print(f"  {field.replace('_', ' ').title()}: {value}")
            
            print("\n⚡ DADOS DE ENERGIA:")
            energy_fields = [
                'saldo_kwh',
                'energia_injetada',
                'consumo_scee',
                'consumo_nao_compensado',
                'geracao_ultimo_ciclo'
            ]
            
            for field in energy_fields:
                value = result.get(field, 'N/A')
                print(f"  {field.replace('_', ' ').title()}: {value}")
            
            print("\n💰 VALORES FINANCEIROS:")
            financial_fields = [
                'preco_energia_injetada',
                'preco_energia_compensada',
                'preco_kwh_nao_compensado',
                'preco_fio_b',
                'preco_adc_bandeira',
                'contribuicao_iluminacao'
            ]
            
            for field in financial_fields:
                value = result.get(field, 'N/A')
                print(f"  {field.replace('_', ' ').title()}: {value}")
            
            print("\n📅 INFORMAÇÕES DE LEITURA:")
            reading_fields = [
                'leitura_anterior',
                'leitura_atual',
                'quantidade_dias'
            ]
            
            for field in reading_fields:
                value = result.get(field, 'N/A')
                print(f"  {field.replace('_', ' ').title()}: {value}")
            
            print("\n🏢 INFORMAÇÕES ADICIONAIS:")
            additional_fields = [
                'endereco_cliente',
                'distribuidora',
                'ciclo_geracao',
                'uc_geradora'
            ]
            
            for field in additional_fields:
                value = result.get(field, 'N/A')
                print(f"  {field.replace('_', ' ').title()}: {value}")
            
            # Verificar campos que não foram extraídos
            missing_fields = []
            for field in main_fields + energy_fields + financial_fields + reading_fields + additional_fields:
                if not result.get(field) or result.get(field) == 'N/A':
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n⚠️  CAMPOS NÃO EXTRAÍDOS ({len(missing_fields)}):")
                for field in missing_fields:
                    print(f"  - {field.replace('_', ' ').title()}")
            else:
                print("\n🎉 TODOS OS CAMPOS FORAM EXTRAÍDOS COM SUCESSO!")
            
        else:
            print("❌ Erro na extração:")
            print(f"   {result.get('erro', 'Erro desconhecido')}")
        
        print("\n📄 DADOS COMPLETOS (JSON):")
        print("-" * 40)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")

def main():
    """Função principal."""
    if len(sys.argv) != 2:
        print("❌ Uso: python test_extraction.py <caminho_do_pdf>")
        print("\nExemplo:")
        print("  python test_extraction.py ../faturas/fatura_exemplo.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_single_pdf(pdf_path)

if __name__ == "__main__":
    main()