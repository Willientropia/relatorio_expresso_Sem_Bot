# backend/scripts/extract_fatura_data.py - VERSÃO COMPLETA CORRIGIDA
import os
import sys
import json
import pdfplumber
import pytesseract
from PIL import Image
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

# Configure o caminho do Tesseract OCR
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract", 
    "tesseract"
]

# Configurar Tesseract
tesseract_found = False
for path in TESSERACT_PATHS:
    if os.path.exists(path) or path == "tesseract":
        try:
            pytesseract.pytesseract_cmd = path
            pytesseract.get_tesseract_version()
            tesseract_found = True
            break
        except:
            continue

if not tesseract_found:
    print("⚠️ Tesseract não encontrado, OCR não estará disponível", file=sys.stderr)
    pytesseract = None

def format_date_to_brazilian(date_obj):
    """Converte objeto date para formato brasileiro DD/MM/YYYY"""
    if isinstance(date_obj, date):
        return date_obj.strftime('%d/%m/%Y')
    return None

def parse_and_format_date(date_string):
    """
    Tenta extrair e formatar data no padrão brasileiro
    Entrada: qualquer formato de data
    Saída: DD/MM/YYYY ou None
    """
    if not date_string:
        return None
    
    try:
        # Limpar string
        clean_date = re.sub(r'[^\d/.-]', '', str(date_string).strip())
        
        # Padrão DD/MM/YYYY ou DD/MM/YY
        if re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', clean_date):
            parts = clean_date.split('/')
            if len(parts) == 3:
                day, month, year = parts
                
                # Ajustar ano de 2 dígitos
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                
                # Validar e reformatar
                date_obj = date(int(year), int(month), int(day))
                return date_obj.strftime('%d/%m/%Y')
        
        # Padrão YYYY-MM-DD
        elif re.match(r'\d{4}-\d{1,2}-\d{1,2}', clean_date):
            date_obj = datetime.strptime(clean_date, '%Y-%m-%d').date()
            return date_obj.strftime('%d/%m/%Y')
        
        # Padrão YYYYMMDD
        elif re.match(r'\d{8}', clean_date):
            date_obj = datetime.strptime(clean_date, '%Y%m%d').date()
            return date_obj.strftime('%d/%m/%Y')
            
    except (ValueError, IndexError) as e:
        print(f"Erro ao converter data '{date_string}': {e}")
        return None
    
    return None

def extract_text_from_pdf(pdf_path):
    """Extrai texto do PDF, utilizando OCR se necessário."""
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                elif pytesseract:
                    # Fallback para OCR se necessário
                    try:
                        image = page.to_image(resolution=300).original
                        text += pytesseract.image_to_string(image, lang='por')
                    except Exception as ocr_error:
                        print(f"Erro no OCR: {ocr_error}", file=sys.stderr)
                        continue
    except Exception as e:
        raise Exception(f"Erro ao processar PDF: {str(e)}")
    
    return text

def extract_reading_info(text):
    """Captura as informações de leitura anterior, leitura atual e quantidade de dias."""
    try:
        match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)', text)
        if match:
            return {
                'leitura_anterior': match.group(1),
                'leitura_atual': match.group(2),
                'quantidade_dias': match.group(3)
            }
        else:
            return {
                'leitura_anterior': None,
                'leitura_atual': None,
                'quantidade_dias': None
            }
    except Exception as e:
        print(f"Erro ao processar informações de leitura: {e}", file=sys.stderr)
        return {
            'leitura_anterior': None,
            'leitura_atual': None,
            'quantidade_dias': None
        }

def extract_reference_month_and_due_date(text):
    """Captura o mês de referência e a data de vencimento - CORRIGIDO"""
    try:
        # Buscar padrão: CFOP seguido de mês e data
        match = re.search(r'CFOP \d{4}:.*?\n(\w{3}/\d{4})\s+(\d{2}/\d{2}/\d{4})', text)
        if match:
            mes_ref = match.group(1).strip()
            data_venc = parse_and_format_date(match.group(2).strip())
            
            return {
                'mes_referencia': mes_ref,
                'data_vencimento': data_venc
            }
        
        # Padrão alternativo: buscar datas separadamente
        # Mês de referência (formato MAI/2025, etc.)
        mes_match = re.search(r'(?:JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)/\d{4}', text)
        mes_ref = mes_match.group(0) if mes_match else None
        
        # Data de vencimento (formato DD/MM/YYYY)
        venc_match = re.search(r'(?:VENCIMENTO|Vencimento)[:\s]*(\d{2}/\d{2}/\d{4})', text)
        data_venc = parse_and_format_date(venc_match.group(1)) if venc_match else None
        
        return {
            'mes_referencia': mes_ref,
            'data_vencimento': data_venc
        }
        
    except Exception as e:
        print(f"Erro ao extrair datas: {e}")
        return {
            'mes_referencia': None,
            'data_vencimento': None
        }

def extract_address(text):
    """Captura o endereço a partir do texto."""
    try:
        match = re.search(r'(RUA .*?\n.*?CEP: .*?BRASIL)', text, re.DOTALL)
        return match.group(1).replace("\n", " ") if match else None
    except Exception:
        return None

def extract_client_name(text):
    """Captura o nome do cliente a partir do texto."""
    try:
        match = re.search(r'Tensão Nominal Disp: .*?\n(.*?)\n', text)
        return match.group(1) if match else None
    except Exception:
        return None

def extract_balance(text):
    """Captura o saldo de energia (KWH) no texto."""
    try:
        match = re.search(r'SALDO KWH:\s*([\d\.,]+)', text)
        if match:
            return match.group(1).strip().rstrip(',')
        return None
    except Exception:
        return None

def extract_uc_info(text):
    """Captura a informação da Unidade Consumidora (UC)."""
    try:
        match = re.search(r'Consulte pela Chave de Acesso em:\s*(\d+)', text)
        return match.group(1) if match else None
    except Exception:
        return None

def safe_decimal_convert(value_str):
    """Converte string de moeda brasileira para Decimal de forma segura."""
    if not value_str:
        return None
    
    try:
        # Remove pontos de milhares e substitui vírgula decimal por ponto
        cleaned = str(value_str).strip()
        # Remove caracteres não numéricos exceto vírgula, ponto e hífen
        cleaned = re.sub(r'[^\d,.-]', '', cleaned)
        # Para valores monetários brasileiros: remove pontos de milhares, vírgula vira ponto decimal
        cleaned = cleaned.replace('.', '').replace(',', '.')
        return str(Decimal(cleaned))
    except (InvalidOperation, Exception):
        return None

def extract_data_from_text(text, pdf_path=None):
    """Processa o texto extraído - VERSÃO CORRIGIDA COM DATAS BRASILEIRAS"""
    data = {}

    # Extração de CPF/CNPJ
    try:
        cpf_match = re.search(r'CNPJ/CPF: (\d{3}\.\d{3}\.\d{3}-\d{2})', text)
        data['cpf_cnpj'] = cpf_match.group(1) if cpf_match else None
    except Exception:
        data['cpf_cnpj'] = None

    # Extração de Consumo (kWh)
    try:
        consumo_match = re.search(r'CONSUMO.*?(\d+[,.]?\d*)', text)
        if consumo_match:
            consumo_str = consumo_match.group(1).replace(',', '.')
            data['consumo_kwh'] = consumo_str
        else:
            data['consumo_kwh'] = None
    except Exception:
        data['consumo_kwh'] = None

    # Extração de Valor Total
    try:
        valor_match = re.search(r'R\$[*\s]*([\d.,]+)', text)
        if valor_match:
            valor_str = valor_match.group(1)
            # Limpar e converter para formato decimal
            valor_clean = re.sub(r'[^\d,]', '', valor_str)
            if ',' in valor_clean:
                # Assumir que a vírgula é decimal
                valor_final = valor_clean.replace(',', '.')
            else:
                valor_final = valor_clean
            data['valor_total'] = valor_final
        else:
            data['valor_total'] = None
    except Exception:
        data['valor_total'] = None

    # Extração do Saldo de Energia
    data['saldo_kwh'] = extract_balance(text)

    # Extração do Nome do Cliente
    data['nome_cliente'] = extract_client_name(text)

    # Extração do Endereço
    data['endereco_cliente'] = extract_address(text)

    # Extração da Unidade Consumidora
    data['unidade_consumidora'] = extract_uc_info(text)

    # ✅ CORREÇÃO PRINCIPAL: Usar função corrigida para datas
    ref_due_info = extract_reference_month_and_due_date(text)
    data.update(ref_due_info)

    # Extração da Contribuição de Iluminação Pública
    try:
        ilum_match = re.search(r'CONTRIB\.\s+ILUM\.\s+PÚBLICA\s+-\s+MUNICIPAL\s+([\d.,]+)', text)
        if ilum_match:
            contrib_str = ilum_match.group(1).replace(',', '.')
            data['contribuicao_iluminacao'] = contrib_str
        else:
            data['contribuicao_iluminacao'] = "0"
    except Exception:
        data['contribuicao_iluminacao'] = "0"

    # Extração de Injeção SCEE
    try:
        injection_match = re.search(r'INJEÇÃO SCEE.*?\s(\d+[,.]?\d*).*?\s([\d.,]+)', text)
        if injection_match:
            energia_str = injection_match.group(1).replace(',', '.')
            preco_str = injection_match.group(2).replace(',', '.')
            data['energia_injetada'] = energia_str
            data['preco_energia_injetada'] = preco_str
        else:
            data['energia_injetada'] = "0"
            data['preco_energia_injetada'] = "0"
    except Exception:
        data['energia_injetada'] = "0"
        data['preco_energia_injetada'] = "0"

    # Extração de Consumo SCEE
    try:
        scee_match = re.search(r'CONSUMO SCEE.*?\s(\d+[,.]?\d*).*?\s([\d.,]+)', text)
        if scee_match:
            consumo_str = scee_match.group(1).replace(',', '.')
            preco_str = scee_match.group(2).replace(',', '.')
            data['consumo_scee'] = consumo_str
            data['preco_energia_compensada'] = preco_str
        else:
            data['consumo_scee'] = "0"
            data['preco_energia_compensada'] = "0"
    except Exception:
        data['consumo_scee'] = "0"
        data['preco_energia_compensada'] = "0"

    # Extração de Preço do Fio B
    try:
        fio_match = re.search(r'PARC INJET S/DESC.*?\d+[,.]?\d*.*?\d+[,.]?\d*.*?\s([\d.,]+)', text)
        if fio_match:
            fio_str = fio_match.group(1).replace(',', '.')
            data['preco_fio_b'] = fio_str
        else:
            data['preco_fio_b'] = "0"
    except Exception:
        data['preco_fio_b'] = "0"

    # Extração de Consumo Não Compensado
    try:
        nao_compensado_match = re.search(r'CONSUMO NÃO COMPENSADO.*?(\d+[,.]?\d*)', text)
        if nao_compensado_match:
            consumo_str = nao_compensado_match.group(1).replace(',', '.')
            data['consumo_nao_compensado'] = consumo_str
        else:
            data['consumo_nao_compensado'] = "0"
    except Exception:
        data['consumo_nao_compensado'] = "0"

    # Preço do kWh Não Compensado
    try:
        preco_kwh_match = re.search(r'CONSUMO NÃO COMPENSADO.*?\d+[,.]?\d*.*?\s([\d.,]+)', text)
        if preco_kwh_match:
            preco_str = preco_kwh_match.group(1).replace(',', '.')
            data['preco_kwh_nao_compensado'] = preco_str
        else:
            data['preco_kwh_nao_compensado'] = "0"
    except Exception:
        data['preco_kwh_nao_compensado'] = "0"

    # Extração de Preço do ADC Bandeira
    try:
        adc_match = re.search(r'ADC BANDEIRA.*?\d+[,.]?\d*.*?\s([\d.,]+)', text)
        if adc_match:
            adc_str = adc_match.group(1).replace(',', '.')
            data['preco_adc_bandeira'] = adc_str
        else:
            data['preco_adc_bandeira'] = "0"
    except Exception:
        data['preco_adc_bandeira'] = "0"

    # Extração de Geração do Ciclo
    try:
        gen_match = re.search(r'GERAÇÃO CICLO \((\d{2}/\d{4})\) KWH: UC (\d+) : ([\d\.,]+)', text)
        if gen_match:
            data['ciclo_geracao'] = gen_match.group(1)
            data['uc_geradora'] = gen_match.group(2)
            geracao_str = gen_match.group(3).strip().rstrip(',').replace(',', '.')
            data['geracao_ultimo_ciclo'] = geracao_str
        else:
            data['ciclo_geracao'] = None
            data['uc_geradora'] = None
            data['geracao_ultimo_ciclo'] = None
    except Exception:
        data['ciclo_geracao'] = None
        data['uc_geradora'] = None
        data['geracao_ultimo_ciclo'] = None

    # ✅ CORREÇÃO: Extração de informações de leitura com datas brasileiras
    try:
        # Buscar padrão: data_anterior data_atual dias
        leitura_match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)', text)
        if leitura_match:
            data['leitura_anterior'] = leitura_match.group(1)  # Já em formato brasileiro
            data['leitura_atual'] = leitura_match.group(2)     # Já em formato brasileiro
            data['quantidade_dias'] = leitura_match.group(3)
        else:
            data['leitura_anterior'] = None
            data['leitura_atual'] = None
            data['quantidade_dias'] = None
    except Exception:
        data['leitura_anterior'] = None
        data['leitura_atual'] = None
        data['quantidade_dias'] = None

    # Campos padrão para compatibilidade
    data.setdefault('distribuidora', 'Equatorial Energia')
    
    # Se não conseguiu extrair alguns campos importantes, definir valores padrão
    if not data.get('nome_cliente'):
        data['nome_cliente'] = 'Não identificado'
    if not data.get('endereco_cliente'):
        data['endereco_cliente'] = 'Não identificado'
    if not data.get('saldo_kwh'):
        data['saldo_kwh'] = '0'
    if not data.get('energia_injetada'):
        data['energia_injetada'] = '0'
    if not data.get('consumo_scee'):
        data['consumo_scee'] = '0'

    return data

def process_single_pdf(pdf_path):
    """Processa um único PDF e retorna os dados extraídos."""
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
        
        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            raise Exception("Não foi possível extrair texto do PDF")
        
        data = extract_data_from_text(text, pdf_path)
        
        # Adicionar metadata
        data['arquivo_processado'] = os.path.basename(pdf_path)
        data['status'] = 'success'
        
        return data
        
    except Exception as e:
        return {
            'arquivo_processado': os.path.basename(pdf_path) if pdf_path else 'unknown',
            'status': 'error',
            'erro': str(e)
        }

def validate_brazilian_date_format():
    """Testa se as funções de data estão funcionando corretamente"""
    test_cases = [
        "15/03/2025",
        "28/03/2025", 
        "17/04/2025",
        "2025-03-15",
        "20250315"
    ]
    
    print("🧪 Testando conversão de datas:")
    for test_date in test_cases:
        result = parse_and_format_date(test_date)
        print(f"  {test_date} → {result}")
    
    print("\n🧪 Testando mês de referência:")
    test_months = ["MAI/2025", "MARÇO/2024", "JAN/25", "03/2025"]
    for test_month in test_months:
        result = extract_reference_month_and_due_date(f"CFOP 1234: teste\n{test_month} 15/06/2025")
        print(f"  {test_month} → {result}")

def main():
    """Função principal para uso via linha de comando."""
    if len(sys.argv) != 2:
        print(json.dumps({
            'status': 'error',
            'erro': 'Uso: python extract_fatura_data.py <caminho_do_pdf>'
        }))
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = process_single_pdf(pdf_path)
    
    # Imprimir resultado como JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))

# Executar validação se script for chamado diretamente
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-dates":
        validate_brazilian_date_format()
    else:
        # Código principal do script
        main()