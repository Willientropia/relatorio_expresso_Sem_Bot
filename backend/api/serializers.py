from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Customer, Fatura, FaturaTask, UnidadeConsumidora, FaturaLog

class FaturaLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaturaLog
        fields = '__all__'

class FaturaSerializer(serializers.ModelSerializer):
    arquivo_url = serializers.SerializerMethodField()
    unidade_consumidora_codigo = serializers.CharField(source='unidade_consumidora.codigo', read_only=True)
    mes_referencia_formatado = serializers.ReadOnlyField()
    mes_referencia_texto = serializers.ReadOnlyField()
    mes_nome_completo = serializers.ReadOnlyField()

    class Meta:
        model = Fatura
        fields = [
            'id', 'unidade_consumidora', 'unidade_consumidora_codigo', 
            'mes_referencia', 'mes_referencia_formatado', 'mes_referencia_texto', 
            'mes_nome_completo', 'arquivo', 'arquivo_url', 'valor', 'vencimento', 
            'downloaded_at', 'created_at', 'updated_at'
        ]
    
    def get_arquivo_url(self, obj):
        if obj.arquivo:
            return obj.arquivo.url
        return None

class FaturaTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaturaTask
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False  # User is inactive until email confirmation
        )
        return user

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        # ...

        return token

    def validate(self, attrs):
        # O `get_user_model` é usado para obter o modelo de usuário ativo
        User = get_user_model()
        # Tenta encontrar o usuário pelo email
        try:
            user = User.objects.get(email=attrs.get('username'))
            # Se encontrado, atualiza o `username` no `attrs` para o `username` real do usuário
            attrs['username'] = user.username
        except User.DoesNotExist:
            # Se não encontrar pelo email, não faz nada e deixa a validação padrão (por username) continuar
            pass

        data = super().validate(attrs)
        return data
