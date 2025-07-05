# backend/api/views.py
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

@api_view(['GET'])
def get_fatura_tasks(request, customer_id):
    """Retorna o status das tarefas de importação"""
    print(f"DEBUG: Buscando tasks para customer_id={customer_id}, user={request.user}")
    
    try:
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        print(f"DEBUG: Customer encontrado: {customer.nome}")
        
        tasks = FaturaTask.objects.filter(
            unidade_consumidora__customer=customer
        ).order_by('-created_at')[:10]
        
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

@api_view(['POST'])
def upload_faturas_with_extraction(request, customer_id):
    """Upload de faturas com extração automática de dados"""
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
                    
                    # Buscar UC correspondente
                    uc_codigo = extracted_data.get('unidade_consumidora')
                    uc = None
                    
                    if uc_codigo:
                        uc = customer.unidades_consumidoras.filter(codigo=uc_codigo).first()
                    
                    if not uc:
                        uc = customer.unidades_consumidoras.filter(is_active=True).first()
                    
                    if not uc:
                        faturas_com_erro.append({
                            "arquivo": arquivo.name,
                            "erro": "Cliente não possui UC ativa ou correspondente"
                        })
                        continue
                    
                    # Processar data de vencimento
                    data_vencimento = None
                    if extracted_data.get('data_vencimento'):
                        try:
                            from datetime import datetime
                            data_vencimento = datetime.strptime(
                                extracted_data['data_vencimento'], 
                                '%d/%m/%Y'
                            ).date()
                        except:
                            pass
                    
                    # Processar mês de referência
                    mes_referencia = timezone.now().date().replace(day=1)
                    if extracted_data.get('mes_referencia'):
                        try:
                            from datetime import datetime
                            # Formato: JAN/2024
                            mes_ano = extracted_data['mes_referencia']
                            # Converter para data
                            mes_referencia = datetime.strptime(f"01/{mes_ano}", '%d/%b/%Y').date()
                        except:
                            pass
                    
                    # Criar fatura
                    fatura = Fatura.objects.create(
                        unidade_consumidora=uc,
                        mes_referencia=mes_referencia,
                        arquivo=arquivo,
                        valor=extracted_data.get('valor_total'),
                        vencimento=data_vencimento,
                        downloaded_at=timezone.now()
                    )
                    
                    faturas_processadas.append({
                        "id": fatura.id,
                        "arquivo": arquivo.name,
                        "uc": uc.codigo,
                        "mes_referencia": fatura.mes_referencia,
                        "valor": fatura.valor,
                        "dados_extraidos": extracted_data
                    })
                    
                else:
                    faturas_com_erro.append({
                        "arquivo": arquivo.name,
                        "erro": f"Erro na extração: {result.stderr}"
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
def extract_fatura_data_view(request):
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)

    pdf_file = request.FILES['file']

    # Salvar o arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
        for chunk in pdf_file.chunks():
            temp_pdf.write(chunk)
        temp_pdf_path = temp_pdf.name

    try:
        # Chamar a função de extração
        extracted_data = process_single_pdf(temp_pdf_path)
        return JsonResponse(extracted_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        # Remover o arquivo temporário
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

@api_view(['GET'])
def get_fatura_logs(request, customer_id):
    """Retorna o histórico de faturas (logs) do cliente"""
    try:
        customer = Customer.objects.get(pk=customer_id, user=request.user)
        
        # Buscar logs de faturas (tasks de importação)
        logs = FaturaTask.objects.filter(
            unidade_consumidora__customer=customer
        ).order_by('-created_at')
        
        serializer = FaturaTaskSerializer(logs, many=True)
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