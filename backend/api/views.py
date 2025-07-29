# backend/api/
import sys

from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Customer, UnidadeConsumidora, FaturaTask, Fatura
from rest_framework import serializers
from django.utils import timezone
from django.db import transaction



import threading
import subprocess
import tempfile
import json
import os
from django.conf import settings
from django.db.models import Q
from datetime import datetime, date
import calendar

# Imports para autenticação
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from .serializers import FaturaLogSerializer, FaturaSerializer, FaturaTaskSerializer, UserSerializer, MyTokenObtainPairSerializer
from django.http import HttpResponseRedirect, JsonResponse

# Imports para extração de dados de fatura
from scripts.extract_fatura_data import process_single_pdf

@api_view(['GET'])
def get_fatura_logs(request, fatura_id):
    try:
        fatura = Fatura.objects.get(pk=fatura_id)
        logs = fatura.logs.all().order_by('-timestamp')
        serializer = FaturaLogSerializer(logs, many=True)
        return Response(serializer.data)
    except Fatura.DoesNotExist:
        return Response({'error': 'Fatura not found'}, status=status.HTTP_404_NOT_FOUND)

# --- Views de Autenticação ---

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []  # No authentication required for registration
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Adicionar o usuário ao grupo 'empresa_adm' (criar o grupo se não existir)
        from django.contrib.auth.models import Group
        empresa_adm_group, created = Group.objects.get_or_create(name='empresa_adm')
        user.groups.add(empresa_adm_group)
        
        # Generate token and send email
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
          # Build the absolute URL for email confirmation
        # Usamos o FRONTEND_URL ao invés de construir a URL a partir do request
        from django.conf import settings
        base_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else request.build_absolute_uri('/')
        confirm_path = reverse('confirm-email', kwargs={'uidb64': uid, 'token': token})
        confirm_url = base_url.rstrip('/') + confirm_path

        send_mail(
            'Confirme seu e-mail',
            f'Por favor, clique no link para confirmar seu registro: {confirm_url}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({"user": serializer.data, "message": "Registro bem-sucedido. Por favor, verifique seu e-mail para confirmação."}, status=status.HTTP_201_CREATED)

class ConfirmEmailView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []  # No authentication required for email confirmation

    def get(self, request, uidb64, token, *args, **kwargs):
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                if user.is_active:
                    return HttpResponseRedirect(f'{frontend_url}/login?already_confirmed=true')
                user.is_active = True
                user.save()
                return HttpResponseRedirect(f'{frontend_url}/login?confirmed=true')
            else:
                return HttpResponseRedirect(f'{frontend_url}/confirm-email-failed')
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return HttpResponseRedirect(f'{frontend_url}/confirm-email-failed')

class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = []  # No authentication required for login
    serializer_class = MyTokenObtainPairSerializer

# --- Views de Clientes e UCs ---

class CustomerSerializer(serializers.ModelSerializer):
    data_nascimento = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d', '%d/%m/%Y'])
    
    class Meta:
        model = Customer
        fields = ['id', 'nome', 'cpf', 'cpf_titular', 'data_nascimento', 
                  'endereco', 'telefone', 'email', 'created_at', 'updated_at']

class UnidadeConsumidoraSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UnidadeConsumidora
        fields = ['id', 'customer', 'codigo', 'endereco', 'tipo', 
                 'data_vigencia_inicio', 'data_vigencia_fim', 'is_active',
                 'created_at', 'updated_at']
        read_only_fields = ['is_active']

@api_view(['GET', 'POST'])
def customer_list(request):
    user = request.user
    if request.method == 'GET':
        customers = Customer.objects.filter(user=user)
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def customer_detail(request, pk):
    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = CustomerSerializer(customer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def uc_list(request, customer_id):
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        ucs = UnidadeConsumidora.objects.filter(customer=customer)
        serializer = UnidadeConsumidoraSerializer(ucs, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['customer'] = customer_id
        serializer = UnidadeConsumidoraSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def uc_detail(request, customer_id, uc_id):
    try:
        uc = UnidadeConsumidora.objects.get(pk=uc_id, customer_id=customer_id)
    except UnidadeConsumidora.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UnidadeConsumidoraSerializer(uc)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UnidadeConsumidoraSerializer(uc, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Só permite deletar UCs inativas
        if uc.is_active:
            return Response(
                {"error": "Não é possível deletar uma UC ativa. Desative-a primeiro."},
                status=status.HTTP_400_BAD_REQUEST
            )
        uc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
def uc_toggle_status(request, customer_id, uc_id):
    try:
        uc = UnidadeConsumidora.objects.get(pk=uc_id, customer_id=customer_id)
    except UnidadeConsumidora.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if uc.is_active:
        # Desativar UC
        uc.data_vigencia_fim = timezone.now().date()
    else:
        # Reativar UC
        uc.data_vigencia_fim = None
    
    uc.save()
    serializer = UnidadeConsumidoraSerializer(uc)
    return Response(serializer.data)

# Views para faturas
class FaturaSerializer(serializers.ModelSerializer):
    arquivo_url = serializers.SerializerMethodField()
    unidade_consumidora_codigo = serializers.CharField(source='unidade_consumidora.codigo', read_only=True)

    class Meta:
        model = Fatura
        fields = ['id', 'unidade_consumidora', 'unidade_consumidora_codigo', 'mes_referencia', 'arquivo', 
                  'arquivo_url', 'valor', 'vencimento', 'downloaded_at']
    
    def get_arquivo_url(self, obj):
        if obj.arquivo:
            # Corrigido para retornar a URL relativa correta
            return obj.arquivo.url
        return None


class FaturaTaskSerializer(serializers.ModelSerializer):
    unidade_consumidora_codigo = serializers.CharField(source='unidade_consumidora.codigo', read_only=True)
    
    class Meta:
        model = FaturaTask
        fields = ['id', 'unidade_consumidora', 'unidade_consumidora_codigo', 
                  'status', 'created_at', 'completed_at', 'error_message']


# backend/api/views.py - Adicione no início das views problemáticas:

# backend/api/views.py - CORREÇÃO da view get_fatura_tasks

@api_view(['GET'])
def get_fatura_tasks(request, customer_id):
    """Retorna o status das tarefas de importação"""
    print(f"DEBUG: Buscando tasks para customer_id={customer_id}, user={request.user}")
    
    try:
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        print(f"DEBUG: Customer encontrado: {customer.nome}")
        
        # ✅ CORREÇÃO: Usar ordem por ID ao invés de created_at
        tasks = FaturaTask.objects.filter(
            unidade_consumidora__customer=customer
        ).order_by('-id')[:10]  # ✅ CORREÇÃO: Ordenar por ID decrescente
        
        print(f"DEBUG: Encontradas {tasks.count()} tasks")
        
        serializer = FaturaTaskSerializer(tasks, many=True)
        return Response(serializer.data)
        
    except Customer.DoesNotExist:
        print(f"DEBUG: Customer {customer_id} não encontrado para user {request.user}")
        return Response({"error": "Cliente não encontrado"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"DEBUG: Erro inesperado: {str(e)}")
        return Response({"error": f"Erro interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['GET'])
def get_faturas(request, customer_id):
    """Retorna as faturas baixadas do cliente"""
    try:
        # Verificar se o customer existe e pertence ao usuário logado
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        
        # Buscar faturas relacionadas às UCs deste customer
        faturas = Fatura.objects.filter(
            unidade_consumidora__customer=customer
        ).order_by('-mes_referencia')
        
        serializer = FaturaSerializer(faturas, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Customer.DoesNotExist:
        return Response(
            {"error": "Cliente não encontrado"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Erro interno: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@api_view(['POST'])
def start_fatura_import(request, customer_id):
    # Aqui você implementará a lógica para iniciar a importação de faturas.
    # Por enquanto, podemos retornar uma mensagem de sucesso.
    try:
        customer = Customer.objects.get(pk=customer_id)
        # Exemplo: iniciar uma task em background (não implementado aqui)
        print(f"Iniciando importação para o cliente: {customer.nome}")
        return Response({"message": "Importação de faturas iniciada com sucesso."}, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response({"error": "Cliente não encontrado."}, status=status.HTTP_404_NOT_FOUND)


# backend/api/views.py - Adicione esta view

@api_view(['POST'])
def upload_faturas(request, customer_id):
    """Processa upload manual de faturas com dados extraídos"""
    try:
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        
        if not request.FILES.getlist('faturas'):
            return Response(
                {"error": "Nenhum arquivo enviado"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        faturas_processadas = []
        faturas_com_erro = []
        
        for arquivo in request.FILES.getlist('faturas'):
            # Validar tipo de arquivo
            if not arquivo.name.lower().endswith('.pdf'):
                faturas_com_erro.append({
                    "arquivo": arquivo.name,
                    "erro": "Apenas arquivos PDF são aceitos"
                })
                continue
            
            # Aqui você pode integrar com seu script de extração real
            # Por enquanto, vamos criar uma fatura básica
            try:
                # Buscar UC correspondente (você pode implementar lógica mais sofisticada)
                uc = customer.unidades_consumidoras.filter(is_active=True).first()
                
                if not uc:
                    faturas_com_erro.append({
                        "arquivo": arquivo.name,
                        "erro": "Cliente não possui UC ativa"
                    })
                    continue
                
                # Criar fatura (usar dados do frontend se enviados)
                fatura_data = {
                    'unidade_consumidora': uc,
                    'mes_referencia': timezone.now().date().replace(day=1),  # Primeiro dia do mês atual
                    'arquivo': arquivo,
                }
                
                # Se dados específicos foram enviados no request, usar eles
                if hasattr(request, 'data'):
                    if request.data.get('mes_referencia'):
                        fatura_data['mes_referencia'] = request.data['mes_referencia']
                    if request.data.get('valor_total'):
                        fatura_data['valor'] = request.data['valor_total']
                    if request.data.get('data_vencimento'):
                        fatura_data['vencimento'] = request.data['data_vencimento']
                
                fatura = Fatura.objects.create(**fatura_data)
                
                faturas_processadas.append({
                    "id": fatura.id,
                    "arquivo": arquivo.name,
                    "uc": uc.codigo,
                    "mes_referencia": fatura.mes_referencia,
                })
                
            except Exception as e:
                faturas_com_erro.append({
                    "arquivo": arquivo.name,
                    "erro": str(e)
                })
        
        return Response({
            "message": f"{len(faturas_processadas)} fatura(s) processada(s) com sucesso",
            "faturas_processadas": faturas_processadas,
            "faturas_com_erro": faturas_com_erro,
            "total_enviadas": len(request.FILES.getlist('faturas'))
        }, status=status.HTTP_201_CREATED)
        
    except Customer.DoesNotExist:
        return Response(
            {"error": "Cliente não encontrado"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Erro interno: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    


@api_view(['POST'])
def extract_fatura_data(request):
    """Extrai dados de uma fatura PDF usando script Python"""
    if 'fatura' not in request.FILES:
        return Response(
            {"error": "Nenhum arquivo enviado"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    arquivo = request.FILES['fatura']
    
    # Validar tipo de arquivo
    if not arquivo.name.lower().endswith('.pdf'):
        return Response(
            {"error": "Apenas arquivos PDF são aceitos"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            for chunk in arquivo.chunks():
                temp_file.write(chunk)
            temp_pdf_path = temp_file.name
        
        # Caminho para o script de extração
        script_path = os.path.join(settings.BASE_DIR, 'scripts', 'extract_fatura_data.py')
        
        # Executar script Python
        result = subprocess.run(
            [sys.executable, script_path, temp_pdf_path],
            capture_output=True,
            text=True,
            timeout=30  # Timeout de 30 segundos
        )
        
        # Limpar arquivo temporário
        os.unlink(temp_pdf_path)
        
        if result.returncode == 0:
            # Parse do resultado JSON
            extracted_data = json.loads(result.stdout)
            
            if extracted_data.get('status') == 'error':
                return Response(
                    {"error": f"Erro na extração: {extracted_data.get('erro')}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Formatar dados para o frontend
            formatted_data = {
                'numero': extracted_data.get('arquivo_processado', ''),
                'unidade_consumidora': extracted_data.get('unidade_consumidora', ''),
                'fornecedor': 'Equatorial Energia Goiás',
                'cnpj': extracted_data.get('cpf_cnpj', ''),
                'data_emissao': None,  # Você pode extrair isso se necessário
                'data_vencimento': extracted_data.get('data_vencimento', ''),
                'valor_total': extracted_data.get('valor_total', ''),
                'consumo_kwh': extracted_data.get('consumo_kwh', ''),
                'mes_referencia': extracted_data.get('mes_referencia', ''),
                'distribuidora': 'Equatorial Energia',
                'nome_cliente': extracted_data.get('nome_cliente', ''),
                'endereco_cliente': extracted_data.get('endereco_cliente', ''),
                'saldo_kwh': extracted_data.get('saldo_kwh', ''),
                'energia_injetada': extracted_data.get('energia_injetada', ''),
                'consumo_scee': extracted_data.get('consumo_scee', ''),
                # Adicionar outros campos conforme necessário
                'dados_completos': extracted_data  # Manter dados originais para debug
            }
            
            return Response(formatted_data, status=status.HTTP_200_OK)
            
        else:
            return Response(
                {"error": f"Erro ao executar script: {result.stderr}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except subprocess.TimeoutExpired:
        return Response(
            {"error": "Timeout na extração de dados"}, 
            status=status.HTTP_408_REQUEST_TIMEOUT
        )
    except json.JSONDecodeError:
        return Response(
            {"error": "Erro ao processar resultado da extração"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Erro interno: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# backend/api/views.py - FUNÇÃO CORRIGIDA

@api_view(['POST'])
def upload_faturas_with_extraction(request, customer_id):
    """Upload de faturas com extração automática de dados e validações CORRIGIDAS"""
    try:
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        
        if not request.FILES.getlist('faturas'):
            return Response(
                {"error": "Nenhum arquivo enviado"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        faturas_processadas = []
        faturas_com_erro = []
        avisos = []
        
        for arquivo in request.FILES.getlist('faturas'):
            if not arquivo.name.lower().endswith('.pdf'):
                faturas_com_erro.append({
                    "arquivo": arquivo.name,
                    "erro": "Apenas arquivos PDF são aceitos"
                })
                continue
            
            try:
                # Extrair dados usando o script
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    for chunk in arquivo.chunks():
                        temp_file.write(chunk)
                    temp_pdf_path = temp_file.name
                
                script_path = os.path.join(settings.BASE_DIR, 'scripts', 'extract_fatura_data.py')
                result = subprocess.run(
                    [sys.executable, script_path, temp_pdf_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                os.unlink(temp_pdf_path)
                
                if result.returncode == 0:
                    extracted_data = json.loads(result.stdout)
                    
                    if extracted_data.get('status') == 'error':
                        faturas_com_erro.append({
                            "arquivo": arquivo.name,
                            "erro": extracted_data.get('erro', 'Erro na extração')
                        })
                        continue
                    
                    # ✅ CORREÇÃO: Verificar UC correspondente COM VALIDAÇÃO ADEQUADA
                    uc_codigo = extracted_data.get('unidade_consumidora')
                    uc = None
                    
                    if uc_codigo:
                        print(f"🔍 DEBUG: UC extraída do PDF: {uc_codigo}")
                        
                        # ✅ PRIMEIRO: Verificar se UC existe no cliente atual
                        uc = customer.unidades_consumidoras.filter(codigo=uc_codigo).first()
                        
                        if uc:
                            print(f"✅ UC {uc_codigo} encontrada no cliente atual")
                        else:
                            print(f"❌ UC {uc_codigo} NÃO encontrada no cliente atual")
                            
                            # ✅ VERIFICAR se UC existe em outros clientes
                            uc_outros_clientes = UnidadeConsumidora.objects.filter(
                                codigo=uc_codigo
                            ).exclude(customer=customer).first()
                            
                            if uc_outros_clientes:
                                print(f"⚠️ UC {uc_codigo} encontrada em outro cliente: {uc_outros_clientes.customer.nome}")
                                
                                # ✅ AVISO CORRETO: UC pertence a outro cliente
                                avisos.append({
                                    "tipo": "uc_outro_cliente",
                                    "arquivo": arquivo.name,
                                    "uc_codigo": uc_codigo,
                                    "cliente_nome": uc_outros_clientes.customer.nome,
                                    "cliente_id": uc_outros_clientes.customer.id,
                                    "mensagem": f"A UC {uc_codigo} está cadastrada no cliente '{uc_outros_clientes.customer.nome}', não no cliente atual."
                                })
                                continue  # ✅ PULAR este arquivo, não processar
                            else:
                                print(f"❌ UC {uc_codigo} não encontrada em nenhum cliente")
                                
                                # ✅ AVISO CORRETO: UC não existe no sistema
                                avisos.append({
                                    "tipo": "uc_nao_encontrada",
                                    "arquivo": arquivo.name,
                                    "uc_codigo": uc_codigo,
                                    "mensagem": f"A UC {uc_codigo} não está cadastrada no sistema. Cadastre-a primeiro ou verifique se o código está correto."
                                })
                                continue  # ✅ PULAR este arquivo, não processar
                    else:
                        print("❌ Nenhuma UC extraída do PDF")
                        
                        # ✅ ERRO: Não conseguiu extrair UC
                        faturas_com_erro.append({
                            "arquivo": arquivo.name,
                            "erro": "Não foi possível extrair o código da UC do PDF"
                        })
                        continue
                    
                    # ✅ Se chegou até aqui, a UC existe no cliente atual
                    # Processar mês de referência
                    mes_referencia = None
                    if extracted_data.get('mes_referencia'):
                        try:
                            # Formato: JAN/2024
                            mes_ano = extracted_data['mes_referencia']
                            mes_referencia = datetime.strptime(f"01/{mes_ano}", '%d/%b/%Y').date()
                        except:
                            mes_referencia = timezone.now().date().replace(day=1)
                    else:
                        mes_referencia = timezone.now().date().replace(day=1)
                    
                    print(f"📅 Data de referência: {mes_referencia}")
                    
                    # ✅ VERIFICAR se fatura já existe PARA ESTA UC ESPECÍFICA
                    fatura_existente = Fatura.objects.filter(
                        unidade_consumidora=uc,  # ✅ UC correta do cliente atual
                        mes_referencia=mes_referencia
                    ).first()
                    
                    if fatura_existente:
                        print(f"⚠️ Fatura já existe: UC {uc.codigo}, mês {mes_referencia}")
                        
                        # ✅ AVISO CORRETO: Fatura duplicada para a UC correta
                        avisos.append({
                            "tipo": "fatura_duplicada",
                            "arquivo": arquivo.name,
                            "uc_codigo": uc.codigo,
                            "mes_referencia": mes_referencia.strftime('%m/%Y'),
                            "fatura_existente_id": fatura_existente.id,
                            "mensagem": f"Já existe uma fatura para a UC {uc.codigo} no período {mes_referencia.strftime('%m/%Y')}."
                        })
                        continue  # ✅ PULAR este arquivo
                    
                    # ✅ Processar data de vencimento
                    data_vencimento = None
                    if extracted_data.get('data_vencimento'):
                        try:
                            data_vencimento = datetime.strptime(
                                extracted_data['data_vencimento'], 
                                '%d/%m/%Y'
                            ).date()
                        except:
                            pass
                    
                    # ✅ Criar fatura para a UC CORRETA
                    fatura = Fatura.objects.create(
                        unidade_consumidora=uc,  # ✅ UC correta
                        mes_referencia=mes_referencia,
                        arquivo=arquivo,
                        valor=extracted_data.get('valor_total'),
                        vencimento=data_vencimento,
                        downloaded_at=timezone.now()
                    )
                    
                    print(f"✅ Fatura criada: ID {fatura.id}, UC {uc.codigo}")
                    
                    faturas_processadas.append({
                        "id": fatura.id,
                        "arquivo": arquivo.name,
                        "uc": uc.codigo,
                        "mes_referencia": mes_referencia,
                        "valor": fatura.valor,
                        "dados_extraidos": extracted_data
                    })
                    
                else:
                    faturas_com_erro.append({
                        "arquivo": arquivo.name,
                        "erro": f"Erro na extração: {result.stderr}"
                    })
                    
            except Exception as e:
                print(f"❌ Erro ao processar {arquivo.name}: {str(e)}")
                faturas_com_erro.append({
                    "arquivo": arquivo.name,
                    "erro": str(e)
                })
        
        # ✅ Resposta com avisos corretos
        response_data = {
            "message": f"{len(faturas_processadas)} fatura(s) processada(s) com sucesso",
            "faturas_processadas": faturas_processadas,
            "faturas_com_erro": faturas_com_erro,
            "avisos": avisos,
            "total_enviadas": len(request.FILES.getlist('faturas'))
        }
        
        print(f"📊 RESULTADO FINAL: {len(faturas_processadas)} processadas, {len(avisos)} avisos, {len(faturas_com_erro)} erros")
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Customer.DoesNotExist:
        return Response(
            {"error": "Cliente não encontrado"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        return Response(
            {"error": f"Erro interno: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def extract_fatura_data_view(request):
    """Extrai dados de uma fatura PDF - versão corrigida com mapeamento consistente"""
    
    # Verificar diferentes nomes de campo
    file_field_names = ['file', 'fatura', 'pdf', 'document']
    uploaded_file = None
    
    for field_name in file_field_names:
        if field_name in request.FILES:
            uploaded_file = request.FILES[field_name]
            break
    
    if not uploaded_file:
        return JsonResponse({
            'error': f'Nenhum arquivo enviado. Campos esperados: {", ".join(file_field_names)}'
        }, status=400)

    # Validar tipo de arquivo
    if not uploaded_file.name.lower().endswith('.pdf'):
        return JsonResponse({
            'error': 'Apenas arquivos PDF são aceitos'
        }, status=400)

    try:
        import tempfile
        import uuid
        
        # Criar nome único para o arquivo temporário
        temp_filename = f"fatura_{uuid.uuid4().hex}.pdf"
        temp_dir = tempfile.gettempdir()
        temp_pdf_path = os.path.join(temp_dir, temp_filename)
        
        # Salvar arquivo temporário
        with open(temp_pdf_path, 'wb') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
        
        # Chamar função de extração
        from scripts.extract_fatura_data import process_single_pdf
        extracted_data = process_single_pdf(temp_pdf_path)
        
        # Remover arquivo temporário
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        
        # Verificar se houve erro na extração
        if extracted_data.get('status') == 'error':
            return JsonResponse({
                'error': f"Erro na extração: {extracted_data.get('erro', 'Erro desconhecido')}"
            }, status=400)
        
        # ✅ CORREÇÃO: Formatação consistente dos dados
        formatted_data = {
            'status': 'success',
            
            # Informações básicas
            'numero': extracted_data.get('arquivo_processado', ''),
            'arquivo_processado': extracted_data.get('arquivo_processado', ''),
            'unidade_consumidora': extracted_data.get('unidade_consumidora', ''),
            'mes_referencia': extracted_data.get('mes_referencia', ''),
            'data_vencimento': extracted_data.get('data_vencimento', ''),
            
            # Valores financeiros
            'valor_total': extracted_data.get('valor_total', ''),
            'contribuicao_iluminacao': extracted_data.get('contribuicao_iluminacao', ''),
            'preco_fio_b': extracted_data.get('preco_fio_b', ''),
            'preco_adc_bandeira': extracted_data.get('preco_adc_bandeira', ''),
            
            # Consumo de energia
            'consumo_kwh': extracted_data.get('consumo_kwh', ''),
            'saldo_kwh': extracted_data.get('saldo_kwh', ''),
            'consumo_nao_compensado': extracted_data.get('consumo_nao_compensado', ''),
            'preco_kwh_nao_compensado': extracted_data.get('preco_kwh_nao_compensado', ''),
            
            # Energia solar (SCEE)
            'energia_injetada': extracted_data.get('energia_injetada', ''),
            'preco_energia_injetada': extracted_data.get('preco_energia_injetada', ''),
            'consumo_scee': extracted_data.get('consumo_scee', ''),
            'preco_energia_compensada': extracted_data.get('preco_energia_compensada', ''),
            
            # Informações do cliente
            'nome_cliente': extracted_data.get('nome_cliente', ''),
            'cpf_cnpj': extracted_data.get('cpf_cnpj', ''),
            'endereco_cliente': extracted_data.get('endereco_cliente', ''),
            
            # Informações de leitura
            'leitura_anterior': extracted_data.get('leitura_anterior', ''),
            'leitura_atual': extracted_data.get('leitura_atual', ''),
            'quantidade_dias': extracted_data.get('quantidade_dias', ''),
            
            # Geração solar
            'ciclo_geracao': extracted_data.get('ciclo_geracao', ''),
            'uc_geradora': extracted_data.get('uc_geradora', ''),
            'geracao_ultimo_ciclo': extracted_data.get('geracao_ultimo_ciclo', ''),
            
            # Distribuidora
            'distribuidora': extracted_data.get('distribuidora', 'Equatorial Energia'),
            
            # Campos de compatibilidade
            'fornecedor': 'Equatorial Energia Goiás',
            'cnpj': extracted_data.get('cpf_cnpj', ''),  # Mapeamento para compatibilidade
            
            # Dados completos para debug
            'dados_completos': extracted_data
        }
        
        return JsonResponse(formatted_data, status=200)
        
    except Exception as e:
        # Limpar arquivo temporário em caso de erro
        if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except:
                pass
        
        return JsonResponse({
            'error': f'Erro interno no servidor: {str(e)}'
        }, status=500)

# Nova view para buscar faturas organizadas por ano/mês
# backend/api/views.py - Atualizar a view get_faturas_por_ano

# backend/api/views.py - CORREÇÃO DEFINITIVA da view get_faturas_por_ano

@api_view(['GET'])
def get_faturas_por_ano(request, customer_id):
    """Retorna as faturas organizadas por ano e mês em português"""
    try:
        print(f"🔍 DEBUG: Buscando faturas para customer_id={customer_id}")
        print(f"🔍 DEBUG: User={request.user}")
        
        # ✅ CORREÇÃO: Verificar se o customer existe e pertence ao usuário
        try:
            customer = Customer.objects.get(pk=customer_id, user=request.user)
            print(f"✅ DEBUG: Customer encontrado: {customer.nome}")
        except Customer.DoesNotExist:
            print(f"❌ DEBUG: Customer {customer_id} não encontrado para user {request.user}")
            return Response(
                {"error": "Cliente não encontrado"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        ano = request.GET.get('ano', datetime.now().year)
        print(f"🔍 DEBUG: Ano solicitado: {ano}")
        
        # Nomes dos meses em português
        MESES_PT_BR = {
            1: {'nome': 'Janeiro', 'abrev': 'JAN'},
            2: {'nome': 'Fevereiro', 'abrev': 'FEV'},
            3: {'nome': 'Março', 'abrev': 'MAR'},
            4: {'nome': 'Abril', 'abrev': 'ABR'},
            5: {'nome': 'Maio', 'abrev': 'MAI'},
            6: {'nome': 'Junho', 'abrev': 'JUN'},
            7: {'nome': 'Julho', 'abrev': 'JUL'},
            8: {'nome': 'Agosto', 'abrev': 'AGO'},
            9: {'nome': 'Setembro', 'abrev': 'SET'},
            10: {'nome': 'Outubro', 'abrev': 'OUT'},
            11: {'nome': 'Novembro', 'abrev': 'NOV'},
            12: {'nome': 'Dezembro', 'abrev': 'DEZ'},
        }
        
        # Buscar todas as UCs do cliente
        ucs = customer.unidades_consumidoras.all()
        print(f"🔍 DEBUG: UCs encontradas: {ucs.count()}")
        for uc in ucs:
            print(f"  - UC {uc.codigo}: {uc.endereco} (Ativa: {uc.is_active})")
        
        # Buscar faturas do ano
        try:
            faturas = Fatura.objects.filter(
                unidade_consumidora__customer=customer,
                mes_referencia__year=ano
            ).order_by('mes_referencia')
            print(f"🔍 DEBUG: Faturas encontradas: {faturas.count()}")
            for fatura in faturas:
                print(f"  - Fatura {fatura.id}: UC {fatura.unidade_consumidora.codigo}, Mês {fatura.mes_referencia}")
        except Exception as e:
            print(f"❌ DEBUG: Erro ao buscar faturas: {str(e)}")
            faturas = Fatura.objects.none()
        
        # Organizar por mês
        faturas_por_mes = {}
        
        try:
            for mes in range(1, 13):
                mes_info = MESES_PT_BR[mes]
                faturas_por_mes[mes] = {
                    'mes_numero': mes,
                    'mes_nome': mes_info['nome'],
                    'mes_abrev': mes_info['abrev'],
                    'ucs': []
                }
                
                # Para cada UC, verificar se tem fatura neste mês
                for uc in ucs:
                    try:
                        fatura_mes = faturas.filter(
                            unidade_consumidora=uc,
                            mes_referencia__month=mes
                        ).first()
                        
                        uc_info = {
                            'uc_id': uc.id,
                            'uc_codigo': uc.codigo,
                            'uc_endereco': uc.endereco,
                            'uc_tipo': uc.tipo,
                            'uc_is_active': uc.is_active,  # ✅ CORREÇÃO: Usar propriedade Python
                            'fatura': None
                        }
                        
                        if fatura_mes:
                            uc_info['fatura'] = {
                                'id': fatura_mes.id,
                                'valor': str(fatura_mes.valor) if fatura_mes.valor else None,
                                'vencimento': fatura_mes.vencimento.strftime('%d/%m/%Y') if fatura_mes.vencimento else None,
                                'arquivo_url': fatura_mes.arquivo.url if fatura_mes.arquivo else None,
                                'downloaded_at': fatura_mes.downloaded_at.strftime('%d/%m/%Y') if fatura_mes.downloaded_at else None
                            }
                        
                        faturas_por_mes[mes]['ucs'].append(uc_info)
                        
                    except Exception as e:
                        print(f"❌ DEBUG: Erro ao processar UC {uc.codigo} no mês {mes}: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"❌ DEBUG: Erro ao organizar faturas por mês: {str(e)}")
            # Retornar estrutura mínima em caso de erro
            faturas_por_mes = {}
        
        # Anos disponíveis
        try:
            anos_disponiveis = list(Fatura.objects.filter(
                unidade_consumidora__customer=customer
            ).dates('mes_referencia', 'year').values_list('mes_referencia__year', flat=True))
            
            anos_disponiveis = sorted(set(anos_disponiveis), reverse=True)
            if not anos_disponiveis:
                anos_disponiveis = [datetime.now().year]
            
            print(f"🔍 DEBUG: Anos disponíveis: {anos_disponiveis}")
            
        except Exception as e:
            print(f"❌ DEBUG: Erro ao buscar anos disponíveis: {str(e)}")
            anos_disponiveis = [datetime.now().year]
        
        # ✅ CORREÇÃO: Calcular UCs ativas usando filtro correto
        ucs_ativas_count = 0
        for uc in ucs:
            if uc.is_active:  # Usar a propriedade Python
                ucs_ativas_count += 1
        
        # Preparar resposta
        response_data = {
            'ano_atual': int(ano),
            'anos_disponiveis': anos_disponiveis,
            'faturas_por_mes': faturas_por_mes,
            'total_ucs': ucs.count(),
            'total_ucs_ativas': ucs_ativas_count  # ✅ CORREÇÃO: Usar contagem manual
        }
        
        print(f"✅ DEBUG: Resposta preparada com {len(faturas_por_mes)} meses")
        
        return Response(response_data)
        
    except Exception as e:
        print(f"❌ DEBUG: Erro geral na view get_faturas_por_ano: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response(
            {
                "error": f"Erro interno: {str(e)}",
                "debug": "Verifique os logs do servidor para mais detalhes"
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# View para forçar upload mesmo com avisos
@api_view(['POST'])
def force_upload_fatura(request, customer_id):
    """Força o upload de uma fatura mesmo com avisos - VERSÃO CORRIGIDA"""
    try:
        print(f"🔧 DEBUG FORCE UPLOAD: Iniciando para customer_id={customer_id}")
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        
        # Dados da requisição
        uc_codigo = request.data.get('uc_codigo')
        mes_referencia_str = request.data.get('mes_referencia')  # formato: MM/YYYY
        arquivo = request.FILES.get('arquivo')
        dados_extraidos = request.data.get('dados_extraidos', {})
        
        print(f"🔧 DEBUG DADOS RECEBIDOS:")
        print(f"  uc_codigo: {uc_codigo}")
        print(f"  mes_referencia_str: {mes_referencia_str}")
        print(f"  arquivo: {arquivo.name if arquivo else 'None'}")
        print(f"  dados_extraidos (raw): {dados_extraidos}")
        print(f"  dados_extraidos type: {type(dados_extraidos)}")
        
        # ✅ CORREÇÃO: Tratar dados_extraidos como string JSON se necessário
        if isinstance(dados_extraidos, str):
            try:
                dados_extraidos = json.loads(dados_extraidos)
                print(f"🔧 DEBUG: dados_extraidos após JSON parse: {dados_extraidos}")
            except json.JSONDecodeError:
                print(f"❌ DEBUG: Erro ao fazer parse JSON dos dados_extraidos")
                dados_extraidos = {}
        
        if not all([uc_codigo, mes_referencia_str, arquivo]):
            print(f"❌ DEBUG: Dados incompletos")
            return Response(
                {"error": "Dados incompletos"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar UC
        uc = customer.unidades_consumidoras.filter(codigo=uc_codigo).first()
        if not uc:
            print(f"❌ DEBUG: UC {uc_codigo} não encontrada")
            return Response(
                {"error": "UC não encontrada"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        print(f"✅ DEBUG: UC encontrada: {uc.codigo}")
        
        # Processar mês de referência
        try:
            mes, ano = mes_referencia_str.split('/')
            mes_referencia = date(int(ano), int(mes), 1)
            print(f"✅ DEBUG: Mês de referência processado: {mes_referencia}")
        except:
            print(f"❌ DEBUG: Formato de data inválido: {mes_referencia_str}")
            return Response(
                {"error": "Formato de data inválido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ✅ CORREÇÃO: Verificar se já existe e DELETAR antes de criar nova
        faturas_existentes = Fatura.objects.filter(
            unidade_consumidora=uc,
            mes_referencia=mes_referencia
        )
        
        if faturas_existentes.exists():
            print(f"🗑️ DEBUG: Removendo {faturas_existentes.count()} fatura(s) existente(s)")
            for fatura_existente in faturas_existentes:
                print(f"  - Fatura ID {fatura_existente.id}, Valor: {fatura_existente.valor}")
            faturas_existentes.delete()
        
        # ✅ CORREÇÃO: Processar data de vencimento corretamente
        data_vencimento = None
        if dados_extraidos.get('data_vencimento'):
            try:
                # Tentar diferentes formatos de data
                venc_str = str(dados_extraidos['data_vencimento'])
                print(f"🔧 DEBUG: Processando data_vencimento: '{venc_str}'")
                
                # Formato DD/MM/YYYY
                if '/' in venc_str:
                    data_vencimento = datetime.strptime(venc_str, '%d/%m/%Y').date()
                # Formato YYYY-MM-DD
                elif '-' in venc_str:
                    data_vencimento = datetime.strptime(venc_str, '%Y-%m-%d').date()
                
                print(f"✅ DEBUG: Data de vencimento processada: {data_vencimento}")
                    
            except (ValueError, TypeError) as e:
                print(f"⚠️ DEBUG: Erro ao processar data de vencimento: {e}")
                data_vencimento = None
        else:
            print(f"⚠️ DEBUG: Nenhuma data_vencimento nos dados_extraidos")
        
        # ✅ CORREÇÃO: Processar valor total corretamente
        valor_total = None
        if dados_extraidos.get('valor_total'):
            try:
                valor_str = str(dados_extraidos['valor_total'])
                print(f"🔧 DEBUG: Processando valor_total: '{valor_str}'")
                # Remover símbolos de moeda e converter
                valor_str = valor_str.replace('R$', '').replace(' ', '').replace(',', '.')
                valor_total = float(valor_str)
                print(f"✅ DEBUG: Valor total processado: {valor_total}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ DEBUG: Erro ao processar valor total: {e}")
                valor_total = None
        else:
            print(f"⚠️ DEBUG: Nenhum valor_total nos dados_extraidos")
        
        # Criar nova fatura
        print(f"🔧 DEBUG: Criando nova fatura com:")
        print(f"  UC: {uc.codigo}")
        print(f"  Mês: {mes_referencia}")
        print(f"  Valor: {valor_total}")
        print(f"  Vencimento: {data_vencimento}")
        
        fatura = Fatura.objects.create(
            unidade_consumidora=uc,
            mes_referencia=mes_referencia,
            arquivo=arquivo,
            valor=valor_total,
            vencimento=data_vencimento,
            downloaded_at=timezone.now()
        )
        
        print(f"✅ DEBUG: Fatura criada: ID {fatura.id}, Valor: {fatura.valor}, Vencimento: {fatura.vencimento}")
        
        return Response({
            "message": "Fatura enviada com sucesso",
            "fatura": {
                "id": fatura.id,
                "uc": uc.codigo,
                "mes_referencia": mes_referencia.strftime('%m/%Y'),
                "valor": str(fatura.valor) if fatura.valor else None,
                "vencimento": fatura.vencimento.strftime('%d/%m/%Y') if fatura.vencimento else None
            }
        }, status=status.HTTP_201_CREATED)
        
    except Customer.DoesNotExist:
        return Response(
            {"error": "Cliente não encontrado"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"❌ Erro interno: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response(
            {"error": f"Erro interno: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ✅ NOVA: View para editar fatura existente
@api_view(['GET', 'PUT'])
def edit_fatura(request, fatura_id):
    """Permite visualizar e editar dados de uma fatura existente - VERSÃO CORRIGIDA"""
    try:
        print(f"🔍 DEBUG: Buscando fatura ID {fatura_id}")
        fatura = Fatura.objects.get(pk=fatura_id)
        print(f"✅ DEBUG: Fatura encontrada: {fatura}")
        
        # Verificar se o usuário tem permissão para esta fatura
        if fatura.unidade_consumidora.customer.user != request.user:
            print(f"❌ DEBUG: Permissão negada. User da fatura: {fatura.unidade_consumidora.customer.user}, User da requisição: {request.user}")
            return Response(
                {"error": "Permissão negada"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        print(f"✅ DEBUG: Permissão OK para user {request.user}")
        
        if request.method == 'GET':
            print(f"📖 DEBUG: Processando GET request")
            
            try:
                # ✅ CORREÇÃO: Verificações de segurança para campos None
                mes_referencia_formatted = ''
                if fatura.mes_referencia:
                    mes_referencia_formatted = fatura.mes_referencia.strftime('%b/%Y').upper()
                
                data_vencimento_formatted = ''
                if fatura.vencimento:
                    data_vencimento_formatted = fatura.vencimento.strftime('%d/%m/%Y')
                
                valor_total_formatted = ''
                if fatura.valor:
                    valor_total_formatted = str(fatura.valor)
                
                arquivo_url = None
                if fatura.arquivo:
                    try:
                        arquivo_url = fatura.arquivo.url
                    except:
                        arquivo_url = None
                
                downloaded_at_formatted = None
                if fatura.downloaded_at:
                    try:
                        downloaded_at_formatted = fatura.downloaded_at.strftime('%d/%m/%Y %H:%M')
                    except:
                        downloaded_at_formatted = None
                
                response_data = {
                    "id": fatura.id,
                    "unidade_consumidora": fatura.unidade_consumidora.codigo,
                    "mes_referencia": mes_referencia_formatted,
                    "data_vencimento": data_vencimento_formatted,
                    "valor_total": valor_total_formatted,
                    "arquivo_url": arquivo_url,
                    "downloaded_at": downloaded_at_formatted
                }
                
                print(f"✅ DEBUG: Dados preparados: {response_data}")
                return Response(response_data)
                
            except Exception as format_error:
                print(f"❌ DEBUG: Erro na formatação: {str(format_error)}")
                import traceback
                traceback.print_exc()
                
                return Response(
                    {"error": f"Erro na formatação dos dados: {str(format_error)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        elif request.method == 'PUT':
            print(f"💾 DEBUG: Processando PUT request")
            
            # Atualizar dados da fatura
            data = request.data
            print(f"📝 DEBUG: Dados recebidos: {data}")
            
            try:
                # Atualizar valor se fornecido
                if 'valor_total' in data and data['valor_total']:
                    try:
                        valor_str = str(data['valor_total']).replace('R$', '').replace(' ', '').replace(',', '.')
                        fatura.valor = float(valor_str)
                        print(f"✅ DEBUG: Valor atualizado para: {fatura.valor}")
                    except (ValueError, TypeError) as e:
                        print(f"❌ DEBUG: Erro no valor: {e}")
                        return Response(
                            {"error": "Valor inválido"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Atualizar data de vencimento se fornecida
                if 'data_vencimento' in data and data['data_vencimento']:
                    try:
                        fatura.vencimento = datetime.strptime(data['data_vencimento'], '%d/%m/%Y').date()
                        print(f"✅ DEBUG: Vencimento atualizado para: {fatura.vencimento}")
                    except ValueError as e:
                        print(f"❌ DEBUG: Erro na data: {e}")
                        return Response(
                            {"error": "Data de vencimento inválida"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Atualizar mês de referência se fornecido
                if 'mes_referencia' in data and data['mes_referencia']:
                    try:
                        # Formato: JAN/2025
                        mes_str, ano_str = data['mes_referencia'].split('/')
                        mes_map = {
                            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
                            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
                        }
                        mes_num = mes_map.get(mes_str.upper())
                        if mes_num:
                            nova_data_ref = date(int(ano_str), mes_num, 1)
                            # Verificar se já existe outra fatura para esta UC neste mês
                            conflito = Fatura.objects.filter(
                                unidade_consumidora=fatura.unidade_consumidora,
                                mes_referencia=nova_data_ref
                            ).exclude(id=fatura.id).exists()
                            
                            if conflito:
                                return Response(
                                    {"error": "Já existe fatura para esta UC neste mês"}, 
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                            
                            fatura.mes_referencia = nova_data_ref
                            print(f"✅ DEBUG: Mês referência atualizado para: {fatura.mes_referencia}")
                        else:
                            return Response(
                                {"error": f"Mês inválido: {mes_str}"}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    except (ValueError, KeyError) as e:
                        print(f"❌ DEBUG: Erro no mês: {e}")
                        return Response(
                            {"error": "Mês de referência inválido"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                # Salvar as alterações
                fatura.save()
                print(f"✅ DEBUG: Fatura salva com sucesso")
                
                return Response({
                    "message": "Fatura atualizada com sucesso",
                    "fatura": {
                        "id": fatura.id,
                        "valor": str(fatura.valor) if fatura.valor else None,
                        "vencimento": fatura.vencimento.strftime('%d/%m/%Y') if fatura.vencimento else None,
                        "mes_referencia": fatura.mes_referencia.strftime('%b/%Y').upper() if fatura.mes_referencia else None
                    }
                })
                
            except Exception as update_error:
                print(f"❌ DEBUG: Erro na atualização: {str(update_error)}")
                import traceback
                traceback.print_exc()
                
                return Response(
                    {"error": f"Erro ao atualizar fatura: {str(update_error)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    except Fatura.DoesNotExist:
        print(f"❌ DEBUG: Fatura {fatura_id} não encontrada")
        return Response(
            {"error": "Fatura não encontrada"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"❌ DEBUG: Erro geral ao editar fatura: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response(
            {"error": f"Erro interno: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )