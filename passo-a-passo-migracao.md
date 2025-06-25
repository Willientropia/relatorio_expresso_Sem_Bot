# Passo a Passo: Migração para Sistema de Titularidade

## 🎯 Objetivo
Permitir que uma UC (Unidade Consumidora) possa ter diferentes titulares ao longo do tempo, mantendo o histórico completo.

## 📝 Passo 1: Adicionar Nova Model no models.py

Adicione esta classe ao final do seu arquivo `models.py`:

```python
class TitularidadeUC(models.Model):
    """
    Registra o histórico de titularidade das UCs.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='titularidades')
    unidade_consumidora = models.ForeignKey('UnidadeConsumidora', on_delete=models.CASCADE, related_name='titularidades')
    data_inicio = models.DateField()
    data_fim = models.DateField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    motivo_encerramento = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data_inicio']
        verbose_name = "Titularidade de UC"
        verbose_name_plural = "Titularidades de UC"
    
    def __str__(self):
        status = "Ativa" if self.ativo else "Inativa"
        return f"{self.customer.nome} - UC {self.unidade_consumidora.codigo} ({status})"
```

## 📝 Passo 2: Adicionar Métodos Auxiliares

### No modelo Customer, adicione:

```python
def get_ucs_ativas(self):
    """Retorna as UCs atualmente ativas do cliente"""
    return self.titularidades.filter(ativo=True).select_related('unidade_consumidora')

def get_historico_ucs(self):
    """Retorna todo o histórico de UCs do cliente"""
    return self.titularidades.all().select_related('unidade_consumidora').order_by('-data_inicio')
```

### No modelo UnidadeConsumidora, adicione:

```python
def get_titular_atual(self):
    """Retorna o titular atual da UC"""
    titularidade = self.titularidades.filter(ativo=True).first()
    return titularidade.customer if titularidade else None

def get_titular_em_data(self, data):
    """Retorna quem era o titular da UC em uma data específica"""
    from django.db.models import Q
    titularidade = self.titularidades.filter(
        data_inicio__lte=data
    ).filter(
        Q(data_fim__gte=data) | Q(data_fim__isnull=True)
    ).first()
    return titularidade.customer if titularidade else None
```

### No modelo Fatura, adicione:

```python
def get_titular(self):
    """Retorna o titular da UC no mês de referência da fatura"""
    from calendar import monthrange
    from datetime import date
    # Usa o último dia do mês de referência
    ultimo_dia = monthrange(self.mes_referencia.year, self.mes_referencia.month)[1]
    data_referencia = date(self.mes_referencia.year, self.mes_referencia.month, ultimo_dia)
    return self.unidade_consumidora.get_titular_em_data(data_referencia)
```

## 📝 Passo 3: Criar Migrações

```bash
# 1. Criar migração para a nova tabela
python manage.py makemigrations

# 2. Criar migração para transferir dados existentes
python manage.py makemigrations api --empty --name migrate_existing_titularidades
```

## 📝 Passo 4: Editar Migração de Dados

No arquivo `api/migrations/XXXX_migrate_existing_titularidades.py`:

```python
from django.db import migrations

def create_titularidades(apps, schema_editor):
    UnidadeConsumidora = apps.get_model('api', 'UnidadeConsumidora')
    TitularidadeUC = apps.get_model('api', 'TitularidadeUC')
    
    # Para cada UC existente, criar registro de titularidade
    for uc in UnidadeConsumidora.objects.all():
        TitularidadeUC.objects.create(
            customer_id=uc.customer_id,
            unidade_consumidora=uc,
            data_inicio=uc.data_vigencia_inicio,
            data_fim=uc.data_vigencia_fim,
            ativo=(uc.data_vigencia_fim is None)
        )

def reverse_migration(apps, schema_editor):
    TitularidadeUC = apps.get_model('api', 'TitularidadeUC')
    TitularidadeUC.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('api', 'XXXX_titularidadeuc'),  # Substitua XXXX pelo número da migração anterior
    ]

    operations = [
        migrations.RunPython(create_titularidades, reverse_migration),
    ]
```

## 📝 Passo 5: Aplicar Migrações

```bash
python manage.py migrate
```

## 📝 Passo 6: Atualizar Admin (admin.py)

```python
from django.contrib import admin
from .models import Customer, UnidadeConsumidora, Fatura, FaturaTask, TitularidadeUC

class TitularidadeUCInline(admin.TabularInline):
    model = TitularidadeUC
    extra = 0
    fields = ['unidade_consumidora', 'data_inicio', 'data_fim', 'ativo']
    readonly_fields = ['created_at']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'email', 'created_at']
    search_fields = ['nome', 'cpf', 'email']
    inlines = [TitularidadeUCInline]

@admin.register(TitularidadeUC)
class TitularidadeUCAdmin(admin.ModelAdmin):
    list_display = ['customer', 'unidade_consumidora', 'data_inicio', 'data_fim', 'ativo']
    list_filter = ['ativo', 'data_inicio']
    search_fields = ['customer__nome', 'unidade_consumidora__codigo']
```

## 📝 Passo 7: Função Auxiliar para Transferências

Adicione ao final do models.py:

```python
def transferir_uc(uc, cliente_novo, data_transferencia=None):
    """
    Transfere uma UC para um novo cliente
    """
    from datetime import date, timedelta
    
    if data_transferencia is None:
        data_transferencia = date.today()
    
    # Encerra titularidade atual
    titularidade_atual = TitularidadeUC.objects.filter(
        unidade_consumidora=uc,
        ativo=True
    ).first()
    
    if titularidade_atual:
        titularidade_atual.data_fim = data_transferencia - timedelta(days=1)
        titularidade_atual.ativo = False
        titularidade_atual.motivo_encerramento = 'Transferência de titularidade'
        titularidade_atual.save()
    
    # Cria nova titularidade
    TitularidadeUC.objects.create(
        customer=cliente_novo,
        unidade_consumidora=uc,
        data_inicio=data_transferencia,
        ativo=True
    )
```

## 📝 Passo 8: Remover Campos Antigos (OPCIONAL - Fazer depois de testar)

Após confirmar que tudo funciona, você pode:

1. Remover o campo `customer` de UnidadeConsumidora
2. Remover `data_vigencia_inicio` e `data_vigencia_fim`
3. Adicionar `unique=True` no campo `codigo` de UnidadeConsumidora
4. Remover a constraint `unique_active_uc_per_customer`

## ⚡ Exemplo de Uso

```python
# Criar UC para um cliente
from api.models import Customer, UnidadeConsumidora, TitularidadeUC
from datetime import date

# Cliente Pedro
pedro = Customer.objects.get(cpf='123.456.789-00')

# Criar UC
uc = UnidadeConsumidora.objects.create(
    codigo='123',
    endereco='Rua A, 100',
    tipo='Residencial'
)

# Criar titularidade
TitularidadeUC.objects.create(
    customer=pedro,
    unidade_consumidora=uc,
    data_inicio=date(2024, 8, 1),
    data_fim=date(2024, 12, 31),
    ativo=False
)

# Transferir para Lucas em janeiro/2025
lucas = Customer.objects.get(cpf='987.654.321-00')
transferir_uc(uc, lucas, date(2025, 1, 1))

# Verificar titular em outubro/2024
titular_outubro = uc.get_titular_em_data(date(2024, 10, 15))
print(titular_outubro.nome)  # Pedro

# Verificar titular em fevereiro/2025
titular_fevereiro = uc.get_titular_em_data(date(2025, 2, 15))
print(titular_fevereiro.nome)  # Lucas
```

## ✅ Benefícios do Novo Sistema

1. **Histórico Completo**: Mantém registro de todos os titulares anteriores
2. **Integridade**: Impossível ter dois titulares simultâneos
3. **Flexibilidade**: Transferências em qualquer data
4. **Rastreabilidade**: Sempre possível saber quem era titular em determinado período
5. **Compatibilidade**: Mantém os dados existentes durante a migração

## ⚠️ Importante

- Teste em ambiente de desenvolvimento primeiro
- Faça backup do banco antes de aplicar em produção
- A migração preserva todos os dados existentes
- Você pode manter temporariamente os campos antigos até ter certeza que tudo funciona