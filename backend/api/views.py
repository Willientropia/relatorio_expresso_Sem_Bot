# backend/api/views.py
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Customer, UnidadeConsumidora, FaturaTask, Fatura
from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
import threading

# Imports para autenticação
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from .serializers import UserSerializer, MyTokenObtainPairSerializer
from django.http import HttpResponseRedirect

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

# --- Views existentes ---

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


@api_view(['GET'])
def get_fatura_tasks(request, customer_id):
    """Retorna o status das tarefas de importação"""
    try:
        customer = Customer.objects.get(pk=customer_id)
        tasks = FaturaTask.objects.filter(customer=customer).order_by('-created_at')[:10]
        serializer = FaturaTaskSerializer(tasks, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_faturas(request, customer_id):
    """Retorna as faturas baixadas do cliente"""
    try:
        customer = Customer.objects.get(pk=customer_id)
        faturas = Fatura.objects.filter(customer=customer).order_by('-mes_referencia')
        serializer = FaturaSerializer(faturas, many=True, context={'request': request})
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)