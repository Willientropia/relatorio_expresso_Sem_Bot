# backend/api/models.py
from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename
import os

def fatura_upload_path(instance, filename):
    # Extrai o mês e ano da data de referência
    mes_ano_str = instance.mes_referencia.strftime('%b-%Y').upper() # ex: JAN-2025
    # Monta o nome do arquivo a partir do ID da instância
    # O ID será algo como '12345678_01_2025'
    novo_nome_arquivo = f"{instance.id}.pdf"
    return os.path.join('faturas', mes_ano_str, novo_nome_arquivo)

def upload_to(instance, filename):
    """Gera o caminho do arquivo para faturas, organizando por ano e mês."""
    # Assegura que mes_referencia é um objeto date
    if not hasattr(instance, 'mes_referencia') or not instance.mes_referencia:
        # Fallback para o ID se a data não estiver disponível
        return f'faturas/unknown/{instance.id}.pdf'

    # Gera o nome da pasta no formato YYYY/MM (ex: 2025/06)
    folder_path = instance.mes_referencia.strftime('%Y/%m')
    
    # O nome do arquivo agora é o próprio ID da fatura
    # Isso garante consistência e unicidade.
    new_filename = f"{instance.id}.pdf"
    
    return os.path.join('faturas', folder_path, new_filename)

class Customer(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    cpf_titular = models.CharField(max_length=14, blank=True, null=True, 
                                   verbose_name="CPF do Titular da UC")
    data_nascimento = models.DateField(blank=True, null=True)
    endereco = models.CharField(max_length=200)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['-created_at']


class UnidadeConsumidora(models.Model):
    TIPO_CHOICES = [
        ('Residencial', 'Residencial'),
        ('Comercial', 'Comercial'),
        ('Industrial', 'Industrial'),
        ('Rural', 'Rural'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='unidades_consumidoras')
    codigo = models.CharField(max_length=50)
    endereco = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='Residencial')
    data_vigencia_inicio = models.DateField(default=timezone.now)
    data_vigencia_fim = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_active(self):
        """UC é ativa se não tem data de fim ou se a data de fim é futura"""
        if self.data_vigencia_fim is None:
            return True
        return self.data_vigencia_fim > timezone.now().date()
    
    def __str__(self):
        status = "Ativa" if self.is_active else "Inativa"
        return f"{self.codigo} - {self.customer.nome} ({status})"
    
    class Meta:
        ordering = ['-created_at']
        # Garante que um código de UC só pode estar ativo uma vez por cliente
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'codigo'],
                condition=models.Q(data_vigencia_fim__isnull=True),
                name='unique_active_uc_per_customer'
            )
        ]

class Fatura(models.Model):
    unidade_consumidora = models.ForeignKey(UnidadeConsumidora, on_delete=models.CASCADE, related_name='faturas')
    mes_referencia = models.DateField()
    arquivo = models.FileField(upload_to=upload_to)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Fatura {self.unidade_consumidora.codigo} - {self.mes_referencia.strftime('%m/%Y')}"

    class Meta:
        ordering = ['-mes_referencia']
        unique_together = ('unidade_consumidora', 'mes_referencia')

class FaturaTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('IN_PROGRESS', 'Em Progresso'),
        ('SUCCESS', 'Sucesso'),
        ('FAILURE', 'Falha'),
    ]
    unidade_consumidora = models.ForeignKey(UnidadeConsumidora, on_delete=models.CASCADE, related_name='tasks')
    mes_referencia = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Task {self.id} - UC {self.unidade_consumidora.codigo} - {self.mes_referencia.strftime('%m/%Y')} [{self.status}]"

    class Meta:
        ordering = ['-created_at']