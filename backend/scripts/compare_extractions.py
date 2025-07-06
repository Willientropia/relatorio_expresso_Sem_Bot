# backend/scripts/compare_extractions.py
"""
Script para comparar a extração do script original vs novo script da web
"""

import sys
import os
import json
from extract_fatura_data import process_single_pdf

# Mapeamento de campos entre o script original e o novo
FIELD_MAPPING = {
    # Original -> Novo
    'CPF/CNPJ': 'cpf_cnpj',
    'Consumo (kWh)': 'consumo_kwh',
    'Valor Total': 'valor_total',
    'Saldo (kWh)': 'saldo_kwh',
    'Nome do Cliente': 'nome_cliente',
    'Endereço': 'endereco_cliente',
    'Unidade Consumidora': 'unidade_consumidora',
    'Mês de Referência': 'mes_referencia',
    'Data de Vencimento': 'data_vencimento',
    'Contribuição de Iluminação Pública': 'contribuicao_iluminacao',
    'Energia Injetada': 'energia_injetada',
    'Preço da Energia Injetada': 'preco_energia_injetada',
    'Consumo SCEE': 'consumo_scee',
    'Preço da Energia Compensada': 'preco_energia_compensada',
    'Preço do Fio B': 'preco_fio_b',
    'Consumo Não Compensado': 'consumo_nao_compensado',
    'Preço do kWh Não Compensado': 'preco_kwh_nao_compensado',
    'Preço do ADC Bandeira': 'preco_adc_bandeira',
    'Ciclo de Geração': 'ciclo_geracao',
    'UC Geradora': 'uc_geradora',
    'Geração do Último Ciclo': 'geracao_ultimo_ciclo',
    'Leitura Anterior': 'leitura_anterior',
    'Leitura Atual': 'leitura_atual',
    'Quantidade de Dias': 'quantidade_dias'
}

def simulate_original_extraction(pdf_path):
    """
    Simula a extração do script original (leitor.py)
    Na prática, você rodaria o leitor.py aqui
    """
    print("⚠️ Para comparação completa, rode o leitor.py original e compare com o resultado abaixo")
    
    # Retorna estrutura esperada do script original
    return {
        'CPF/CNPJ': None,
        'Consumo (kWh)': None,
        'Valor Total': None,
        'Saldo (kWh)': None,
        'Nome do Cliente': None,
        'Endereço': None,
        'Unidade Consumidora': None,
        'Mês de Referência': None,
        'Data de Vencimento': None,
        'Contribuição de Iluminação Pública': None,
        'Energia Injetada': None,
        'Preço da Energia Injetada': None,
        'Consumo SCEE': None,
        'Preço da Energia Compensada': None,
        'Preço do Fio B': None,
        'Consumo Não Compensado': None,
        'Preço do kWh Não Compensado': None,
        'Preço do ADC Bandeira': None,
        'Ciclo de Geração': None,
        'UC Geradora': None,
        'Geração do Último Ciclo': None,
        'Leitura Anterior': None,
        'Leitura Atual': None,
        'Quantidade de Dias': None
    }

def compare_extractions(pdf_path):
    """Compara as extrações entre o script original e o novo."""
    print(f"🔄 Comparando extrações para: {pdf_path}")
    print("=" * 60)
    
    # Extração do novo script
    print("📄 Executando novo script de extração...")
    new_result = process_single_pdf(pdf_path)
    
    # Simular extração do script original
    print("📄 Simulando script original...")
    original_result = simulate_original_extraction(pdf_path)
    
    print("\n📊 COMPARAÇÃO DE RESULTADOS:")
    print("-" * 40)
    
    success_count = 0
    total_count = 0
    
    for original_field, new_field in FIELD_MAPPING.items():
        total_count += 1
        original_value = original_result.get(original_field, 'N/A')
        new_value = new_result.get(new_field, 'N/A')
        
        # Verificar se o novo script extraiu o valor
        if new_value and new_value != 'N/A' and new_value != 'Não identificado':
            success_count += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"{status} {original_field}")
        print(f"    Original: {original_value}")
        print(f"    Novo:     {new_value}")
        print()
    
    # Estatísticas
    success_rate = (success_count / total_count) * 100
    print(f"📈 ESTATÍSTICAS:")
    print(f"   Campos extraídos: {success_count}/{total_count}")
    print(f"   Taxa de sucesso: {success_rate:.1f}%")
    
    # Campos extras no novo script
    extra_fields = []
    for field in new_result.keys():
        if field not in FIELD_MAPPING.values() and field not in ['arquivo_processado', 'status']:
            extra_fields.append(field)
    
    if extra_fields:
        print(f"\n🆕 CAMPOS EXTRAS NO NOVO SCRIPT:")
        for field in extra_fields:
            value = new_result.get(field, 'N/A')
            print(f"   {field}: {value}")
    
    # Análise de qualidade
    print(f"\n🎯 ANÁLISE DE QUALIDADE:")
    
    critical_fields = ['unidade_consumidora', 'cpf_cnpj', 'valor_total', 'mes_referencia']
    critical_extracted = sum(1 for field in critical_fields if new_result.get(field))
    
    print(f"   Campos críticos extraídos: {critical_extracted}/{len(critical_fields)}")
    
    if critical_extracted == len(critical_fields):
        print("   🟢 Extração EXCELENTE - Todos os campos críticos extraídos")
    elif critical_extracted >= len(critical_fields) * 0.75:
        print("   🟡 Extração BOA - Maioria dos campos críticos extraídos")
    else:
        print("   🔴 Extração PRECISA MELHORAR - Poucos campos críticos extraídos")
    
    return new_result, success_rate

def generate_improvement_suggestions(result, success_rate):
    """Gera sugestões de melhoria baseadas nos resultados."""
    print(f"\n💡 SUGESTÕES DE MELHORIA:")
    print("-" * 30)
    
    if success_rate < 50:
        print("🔧 Taxa de extração baixa. Verificar:")
        print("   - Qualidade do PDF (texto vs imagem)")
        print("   - Padrões de regex muito específicos")
        print("   - Necessidade de OCR")
    
    # Verificar campos específicos
    missing_critical = []
    critical_fields = {
        'unidade_consumidora': 'Unidade Consumidora',
        'cpf_cnpj': 'CPF/CNPJ',
        'valor_total': 'Valor Total',
        'mes_referencia': 'Mês de Referência'
    }
    
    for field, name in critical_fields.items():
        if not result.get(field):
            missing_critical.append(name)
    
    if missing_critical:
        print(f"⚠️  Campos críticos não extraídos:")
        for field in missing_critical:
            print(f"   - {field}")
        print("   Sugestão: Revisar padrões regex para estes campos")
    
    # Verificar campos de energia solar
    solar_fields = ['energia_injetada', 'consumo_scee', 'saldo_kwh']
    solar_extracted = sum(1 for field in solar_fields if result.get(field) and result.get(field) != '0')
    
    if solar_extracted == 0:
        print("🌞 Nenhum campo de energia solar extraído")
        print("   Possíveis causas:")
        print("   - Fatura não é de energia solar")
        print("   - Padrões regex precisam ser ajustados")
    
    # Verificar valores monetários
    financial_fields = ['preco_energia_injetada', 'preco_energia_compensada', 'contribuicao_iluminacao']
    financial_extracted = sum(1 for field in financial_fields if result.get(field) and result.get(field) != '0')
    
    if financial_extracted < len(financial_fields) * 0.5:
        print("💰 Poucos valores financeiros extraídos")
        print("   Sugestão: Verificar padrões para valores monetários")
    
    print("\n🔧 MELHORIAS RECOMENDADAS:")
    print("1. Testar com mais faturas para validar padrões")
    print("2. Adicionar padrões alternativos para campos que falharam")
    print("3. Implementar validação cruzada dos dados extraídos")
    print("4. Considerar usar machine learning para extração")

def main():
    """Função principal."""
    if len(sys.argv) != 2:
        print("❌ Uso: python compare_extractions.py <caminho_do_pdf>")
        print("\nExemplo:")
        print("  python compare_extractions.py ../faturas/fatura_exemplo.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)
    
    try:
        result, success_rate = compare_extractions(pdf_path)
        generate_improvement_suggestions(result, success_rate)
        
        print(f"\n📄 RESULTADO COMPLETO (JSON):")
        print("-" * 40)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Erro durante a comparação: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()