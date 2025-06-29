# Comandos de Gerenciamento - Relatorio-Expresso-Fresh

recriar o docker completamente:

.\rebuild_docker.bat






Este documento contém os comandos de gerenciamento disponíveis para administração do sistema Relatorio-Expresso-Fresh, incluindo gerenciamento de usuários e outras operações relacionadas.

## Gerenciamento de Usuários

### Listagem de Usuários (`list_users`)

Este comando permite listar todos os usuários cadastrados no sistema com suas informações e dados relacionados.

**Sintaxe básica:**
```bash
docker-compose exec backend python manage.py list_users
```

**Opções disponíveis:**

| Opção | Descrição |
|-------|-----------|
| `--detailed` | Mostra informações detalhadas para cada usuário |
| `--search <termo>` | Filtra usuários pelo nome de usuário, email ou nome |

**Exemplos de uso:**

1. Listar todos os usuários de forma resumida:
```bash
docker-compose exec backend python manage.py list_users
```

2. Listar todos os usuários com informações detalhadas:
```bash
docker-compose exec backend python manage.py list_users --detailed
```

3. Buscar um usuário específico por nome ou email:
```bash
docker-compose exec backend python manage.py list_users --search joao
```

4. Buscar e mostrar detalhes de um usuário específico:
```bash
docker-compose exec backend python manage.py list_users --detailed --search joao@exemplo.com
```

### Exclusão de Usuários (`delete_user`)

Este comando permite excluir um usuário e todos os seus dados relacionados do sistema. Por segurança, o comando solicita confirmação antes da exclusão, a menos que a opção `--force` seja utilizada.

**Sintaxe básica:**
```bash
docker-compose exec backend python manage.py delete_user <identifier>
```

O `<identifier>` pode ser:
- Nome de usuário
- Email
- ID do usuário

**Opções disponíveis:**

| Opção | Descrição |
|-------|-----------|
| `--force` | Pula a confirmação e executa a exclusão diretamente |
| `--dry-run` | Simula a operação mostrando o que seria excluído, sem excluir de fato |

**Exemplos de uso:**

1. Excluir um usuário pelo nome (com pedido de confirmação):
```bash
docker-compose exec backend python manage.py delete_user pedro
```

2. Excluir um usuário pelo email sem confirmação:
```bash
docker-compose exec backend python manage.py delete_user pedro@email.com --force
```

3. Simular a exclusão para ver o que seria removido:
```bash
docker-compose exec backend python manage.py delete_user pedro --dry-run
```

4. Combinar as opções para simulação sem confirmação:
```bash
docker-compose exec backend python manage.py delete_user 42 --force --dry-run
```

## Outros Comandos de Gerenciamento

### Migração de Usuários para Empresa Administradora (`migrate_users_to_empresa_adm`)

Possivelmente utilizado para migrar usuários para uma empresa administradora específica.

```bash
docker-compose exec backend python manage.py migrate_users_to_empresa_adm
```

> Nota: Consulte o código-fonte em `backend/api/management/commands/migrate_users_to_empresa_adm.py` para mais detalhes sobre este comando.

## Solução de Problemas Docker

### Problemas de Build e Cache

Se você encontrar erros ao construir os containers Docker, especialmente erros relacionados a snapshots ou camadas de imagem, pode ser um problema com o cache do Docker. Alguns erros comuns incluem:

```
failed to solve: failed to prepare extraction snapshot: parent snapshot does not exist: not found
```

#### Solução 1: Limpar o Cache do Docker

Execute os seguintes comandos para limpar o cache e reconstruir as imagens:

```bash
# Parar todos os containers
docker-compose down

# Remover as imagens do projeto
docker rmi relatorio-expresso-fresh-backend relatorio-expresso-fresh-frontend

# Limpar volumes não utilizados
docker volume prune -f

# Limpar o cache do builder
docker builder prune -f

# Reconstruir
docker-compose up --build
```

Ou use o script `rebuild_docker.bat` (Windows) ou `rebuild_docker.sh` (Linux/Mac) na raiz do projeto.

#### Solução 2: Verificar Problemas de Rede

Para problemas de "network error" ao acessar o backend a partir do frontend:

1. Verifique se o backend está rodando na porta 8000
2. Confirme que as configurações CORS estão corretas em `backend/config/settings.py`
3. Verifique a configuração do apiClient em `frontend/src/services/api.js`

Para mais informações sobre a configuração Docker deste projeto, consulte os arquivos `docker-compose.yml` e `docker-compose.override.yml`.

## Boas Práticas

1. Sempre faça um `list_users` antes de executar `delete_user` para confirmar o identificador correto
2. Use `--dry-run` antes de executar exclusões para garantir que apenas os dados corretos serão removidos
3. Mantenha backups do banco de dados antes de operações em massa de exclusão

## Ajuda dos Comandos

Para obter ajuda sobre qualquer comando específico:

```bash
docker-compose exec backend python manage.py <comando> --help
```

Exemplo:
```bash
docker-compose exec backend python manage.py delete_user --help
```

---

**Importante:** A exclusão de usuários é uma operação destrutiva que remove permanentemente todos os dados relacionados. Use com cautela.
