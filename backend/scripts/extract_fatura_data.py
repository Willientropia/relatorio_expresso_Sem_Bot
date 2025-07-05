# backend/scripts/extract_fatura_data.py
import os
import sys
import json
import pdfplumber
import pytesseract
from PIL import Image
import re
import tempfile
from decimal import Decimal

# Configure o caminho do Tesseract OCR
TESSERACT_PATH = os.getenv('TESSERACT_PATH', r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract_cmd = TESSERACT_PATH

def extract_text_from_pdf(pdf_path):
    """Extrai texto do PDF, utilizando OCR se necessário."""
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                else:
                    # Fallback para OCR se o texto não for extraível
                    try:
                        image = page.to_image(resolution=300).original
                        text += pytesseract.image_to_string(image, lang='por')
                    except Exception as ocr_error:
                        print(f"Erro no OCR: {ocr_error}")
                        continue
    except Exception as e:
        raise Exception(f"Erro ao processar PDF: {str(e)}")
    
    return text

def extract_reading_info(text):
    """Captura as informações de leitura anterior, leitura atual e quantidade de dias."""
    match = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)', text)
    return {
        'leitura_anterior': match.group(1) if match else None,
        'leitura_atual': match.group(2) if match else None,
        'quantidade_dias': match.group(3) if match else None
    }

def extract_reference_month_and_due_date(text):
    """Captura o mês de referência e a data de vencimento."""
    match = re.search(r'CFOP \d{4}:.*?\n(\w{3}/\d{4})\s+(\d{2}/\d{2}/\d{4})', text)
    return {
        'mes_referencia': match.group(1) if match else None,
        'data_vencimento': match.group(2) if match else None
    }

def convert_currency_to_decimal(value_str):
    """Converte string de moeda brasileira para Decimal."""
    if not value_str:
        return None
    
    # Remove pontos e substitui vírgula por ponto
    cleaned = value_str.replace('.', '').replace(',', '.')
    try:
        return str(Decimal(cleaned))
    except:
        return None

def extract_data_from_text(text):
    """Processa o texto extraído para buscar dados específicos."""
    data = {}

    # Extração de CPF/CNPJ
    cpf_match = re.search(r'CNPJ/CPF: (\d{3}\.\d{3}\.\d{3}-\d{2})', text)
    data['cpf_cnpj'] = cpf_match.group(1) if cpf_match else None

    # Extração de Consumo (kWh)
    consumo_match = re.search(r'CONSUMO.*?(\d+\,\d+)', text)
    data['consumo_kwh'] = consumo_match.group(1).replace(',', '.') if consumo_match else None

    # Extração de Valor Total
    valor_match = re.search(r'R\$[*]+([\d.,]+)', text)
    data['valor_total'] = convert_currency_to_decimal(valor_match.group(1)) if valor_match else None

    # Extração do Saldo de Energia
    saldo_match = re.search(r'SALDO KWH:\s*([\d\.,]+)', text)
    data['saldo_kwh'] = saldo_match.group(1).strip().rstrip(',').replace(',', '.') if saldo_match else None

    # Extração do Nome do Cliente
    cliente_match = re.search(r'Tensão Nominal Disp: .*?\n(.*?)\n', text)
    data['nome_cliente'] = cliente_match.group(1) if cliente_match else None

    # Extração do Endereço
    endereco_match = re.search(r'(RUA .*?\n.*?CEP: .*?BRASIL)', text, re.DOTALL)
    data['endereco_cliente'] = endereco_match.group(1).replace("\n", " ") if endereco_match else None

    # Extração da Unidade Consumidora
    uc_match = re.search(r'Consulte pela Chave de Acesso em:\s*(\d+)', text)
    data['unidade_consumidora'] = uc_match.group(1) if uc_match else None

    # Extração de Informações de Leitura
    data.update(extract_reading_info(text))

    # Extração do Mês de Referência e Data de Vencimento
    data.update(extract_reference_month_and_due_date(text))

    # Extração da Contribuição de Iluminação Pública
    ilum_match = re.search(r'CONTRIB\.\s+ILUM\.\s+PÚBLICA\s+-\s+MUNICIPAL\s+(\d{1,3}(?:\.\d{3})*,\d{2})', text)
    data['contribuicao_iluminacao'] = convert_currency_to_decimal(ilum_match.group(1)) if ilum_match else "0"

    # Extração de Injeção SCEE
    injection_match = re.search(r'INJEÇÃO SCEE.*?\s(\d+\,\d+).*?\s(\d+\,\d+)', text)
    if injection_match:
        data['energia_injetada'] = injection_match.group(1).replace(',', '.')
        data['preco_energia_injetada'] = convert_currency_to_decimal(injection_match.group(2))
    else:
        data['energia_injetada'] = None
        data['preco_energia_injetada'] = None

    # Extração de Consumo SCEE
    scee_match = re.search(r'CONSUMO SCEE.*?\s(\d+\,\d+).*?\s(\d+\,\d+)', text)
    if scee_match:
        data['consumo_scee'] = scee_match.group(1).replace(',', '.')
        data['preco_energia_compensada'] = convert_currency_to_decimal(scee_match.group(2))
    else:
        data['consumo_scee'] = None
        data['preco_energia_compensada'] = None

    # Extração de Preço do Fio B
    fio_match = re.search(r'PARC INJET S/DESC.*?\d+\,\d+.*?\d+\,\d+.*?\s(\d+\,\d+)', text)
    data['preco_fio_b'] = convert_currency_to_decimal(fio_match.group(1)) if fio_match else None

    # Extração de Consumo Não Compensado
    nao_compensado_match = re.search(r'CONSUMO NÃO COMPENSADO.*?(\d+\,\d+)', text)
    data['consumo_nao_compensado'] = nao_compensado_match.group(1).replace(',', '.') if nao_compensado_match else "0"

    # Preço do kWh Não Compensado
    preco_kwh_match = re.search(r'CONSUMO NÃO COMPENSADO.*?\d+\,\d+.*?\s(\d+\,\d+)', text)
    data['preco_kwh_nao_compensado'] = convert_currency_to_decimal(preco_kwh_match.group(1)) if preco_kwh_match else "0"

    # Extração de Preço do ADC Bandeira
    adc_match = re.search(r'ADC BANDEIRA.*?\d+\,\d+.*?\s(\d+\,\d+)', text)
    data['preco_adc_bandeira'] = convert_currency_to_decimal(adc_match.group(1)) if adc_match else "0"

    # Extração de Geração do Ciclo
    gen_match = re.search(r'GERAÇÃO CICLO \((\d{2}/\d{4})\) KWH: UC (\d+) : ([\d\.,]+)', text)
    if gen_match:
        data['ciclo_geracao'] = gen_match.group(1)
        data['uc_geradora'] = gen_match.group(2)
        data['geracao_ultimo_ciclo'] = gen_match.group(3).strip().rstrip(',').replace(',', '.')
    else:
        data['ciclo_geracao'] = None
        data['uc_geradora'] = None
        data['geracao_ultimo_ciclo'] = None

    return data

def process_single_pdf(pdf_path):
    """Processa um único PDF e retorna os dados extraídos."""
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
        
        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            raise Exception("Não foi possível extrair texto do PDF")
        
        data = extract_data_from_text(text)
        
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

def main():
    """Função principal para uso via linha de comando."""
    if len(sys.argv) != 2:
        print("Uso: python extract_fatura_data.py <caminho_do_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = process_single_pdf(pdf_path)
    
    # Imprimir resultado como JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()