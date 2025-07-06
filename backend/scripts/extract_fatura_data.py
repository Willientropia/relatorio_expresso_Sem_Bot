# backend/scripts/extract_fatura_data.py
import os
import sys
import json
import pdfplumber
import pytesseract
from PIL import Image
import re
from decimal import Decimal, InvalidOperation

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
    """Captura o mês de referência e a data de vencimento."""
    try:
        match = re.search(r'CFOP \d{4}:.*?\n(\w{3}/\d{4})\s+(\d{2}/\d{2}/\d{4})', text)
        if match:
            return {
                'mes_referencia': match.group(1),
                'data_vencimento': match.group(2)
            }
        return {
            'mes_referencia': None,
            'data_vencimento': None
        }
    except Exception:
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
    """Processa o texto extraído para buscar dados específicos - versão melhorada."""
    data = {}

    # Extração de CPF/CNPJ
    try:
        cpf_match = re.search(r'CNPJ/CPF: (\d{3}\.\d{3}\.\d{3}-\d{2})', text)
        data['cpf_cnpj'] = cpf_match.group(1) if cpf_match else None
    except Exception:
        data['cpf_cnpj'] = None

    # Extração de Consumo (kWh)
    try:
        consumo_match = re.search(r'CONSUMO.*?(\d+\,\d+)', text)
        data['consumo_kwh'] = consumo_match.group(1).replace(',', '.') if consumo_match else None
    except Exception:
        data['consumo_kwh'] = None

    # Extração de Valor Total
    try:
        valor_match = re.search(r'R\$[*]+([\d.,]+)', text)
        data['valor_total'] = safe_decimal_convert(valor_match.group(1)) if valor_match else None
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

    # Extração de Informações de Leitura
    reading_info = extract_reading_info(text)
    data.update(reading_info)

    # Extração do Mês de Referência e Data de Vencimento
    ref_due_info = extract_reference_month_and_due_date(text)
    data.update(ref_due_info)

    # Extração da Contribuição de Iluminação Pública
    try:
        ilum_match = re.search(r'CONTRIB\.\s+ILUM\.\s+PÚBLICA\s+-\s+MUNICIPAL\s+(\d{1,3}(?:\.\d{3})*,\d{2})', text)
        data['contribuicao_iluminacao'] = safe_decimal_convert(ilum_match.group(1)) if ilum_match else "0"
    except Exception:
        data['contribuicao_iluminacao'] = "0"

    # Extração de Injeção SCEE
    try:
        injection_match = re.search(r'INJEÇÃO SCEE.*?\s(\d+\,\d+).*?\s(\d+\,\d+)', text)
        if injection_match:
            data['energia_injetada'] = injection_match.group(1).replace(',', '.')
            data['preco_energia_injetada'] = safe_decimal_convert(injection_match.group(2))
        else:
            data['energia_injetada'] = None
            data['preco_energia_injetada'] = None
    except Exception:
        data['energia_injetada'] = None
        data['preco_energia_injetada'] = None

    # Extração de Consumo SCEE
    try:
        scee_match = re.search(r'CONSUMO SCEE.*?\s(\d+\,\d+).*?\s(\d+\,\d+)', text)
        if scee_match:
            data['consumo_scee'] = scee_match.group(1).replace(',', '.')
            data['preco_energia_compensada'] = safe_decimal_convert(scee_match.group(2))
        else:
            data['consumo_scee'] = None
            data['preco_energia_compensada'] = None
    except Exception:
        data['consumo_scee'] = None
        data['preco_energia_compensada'] = None

    # Extração de Preço do Fio B
    try:
        fio_match = re.search(r'PARC INJET S/DESC.*?\d+\,\d+.*?\d+\,\d+.*?\s(\d+\,\d+)', text)
        data['preco_fio_b'] = safe_decimal_convert(fio_match.group(1)) if fio_match else None
    except Exception:
        data['preco_fio_b'] = None

    # Extração de Consumo Não Compensado
    try:
        nao_compensado_match = re.search(r'CONSUMO NÃO COMPENSADO.*?(\d+\,\d+)', text)
        data['consumo_nao_compensado'] = nao_compensado_match.group(1).replace(',', '.') if nao_compensado_match else "0"
    except Exception:
        data['consumo_nao_compensado'] = "0"

    # Preço do kWh Não Compensado
    try:
        preco_kwh_match = re.search(r'CONSUMO NÃO COMPENSADO.*?\d+\,\d+.*?\s(\d+\,\d+)', text)
        data['preco_kwh_nao_compensado'] = safe_decimal_convert(preco_kwh_match.group(1)) if preco_kwh_match else "0"
    except Exception:
        data['preco_kwh_nao_compensado'] = "0"

    # Extração de Preço do ADC Bandeira
    try:
        adc_match = re.search(r'ADC BANDEIRA.*?\d+\,\d+.*?\s(\d+\,\d+)', text)
        data['preco_adc_bandeira'] = safe_decimal_convert(adc_match.group(1)) if adc_match else "0"
    except Exception:
        data['preco_adc_bandeira'] = "0"

    # Extração de Geração do Ciclo
    try:
        gen_match = re.search(r'GERAÇÃO CICLO \((\d{2}/\d{4})\) KWH: UC (\d+) : ([\d\.,]+)', text)
        if gen_match:
            data['ciclo_geracao'] = gen_match.group(1)
            data['uc_geradora'] = gen_match.group(2)
            data['geracao_ultimo_ciclo'] = gen_match.group(3).strip().rstrip(',').replace(',', '.')
        else:
            data['ciclo_geracao'] = None
            data['uc_geradora'] = None
            data['geracao_ultimo_ciclo'] = None
    except Exception:
        data['ciclo_geracao'] = None
        data['uc_geradora'] = None
        data['geracao_ultimo_ciclo'] = None

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

if __name__ == "__main__":
    main()