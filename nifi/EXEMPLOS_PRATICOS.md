# Exemplos Práticos - Fluxo NiFi

## Exemplo Completo: API de Usuários

### 1. API de Exemplo (JSON Response)

Suponha que sua API retorne este JSON:

```json
{
  "status": "success",
  "data": {
    "users": [
      {
        "id": 1,
        "name": "João Silva",
        "email": "joao@exemplo.com",
        "age": 30,
        "created_at": "2025-01-15T10:30:00Z"
      },
      {
        "id": 2,
        "name": "Maria Santos",
        "email": "maria@exemplo.com",
        "age": 25,
        "created_at": "2025-01-16T14:20:00Z"
      }
    ]
  }
}
```

### 2. Configuração do EvaluateJsonPath

Para extrair os dados do array de usuários, você tem duas opções:

#### Opção A: Processar o array completo
```
Nome: json.users
Valor: $.data.users
```

#### Opção B: Usar SplitJson antes

1. Adicione o processor **SplitJson** após o InvokeHTTP
2. Configure:
   - **JsonPath Expression**: `$.data.users`

3. Depois no EvaluateJsonPath:
```
Nome: user.id
Valor: $.id

Nome: user.name
Valor: $.name

Nome: user.email
Valor: $.email

Nome: user.age
Valor: $.age

Nome: user.created_at
Valor: $.created_at
```

### 3. Criar Tabela SQLite

```sql
-- Criar tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    age INTEGER,
    created_at TEXT,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Criar índice para melhorar performance
CREATE INDEX IF NOT EXISTS idx_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_created_at ON users(created_at);
```

### 4. Verificar dados inseridos

```sql
-- Ver todos os registros
SELECT * FROM users;

-- Ver apenas os mais recentes
SELECT * FROM users ORDER BY processed_at DESC LIMIT 10;

-- Contar registros
SELECT COUNT(*) as total FROM users;

-- Ver registros de hoje
SELECT * FROM users
WHERE DATE(processed_at) = DATE('now');
```

---

## Exemplo 2: API de Produtos

### 1. JSON da API

```json
{
  "products": [
    {
      "sku": "PROD001",
      "name": "Notebook Dell",
      "price": 3500.00,
      "stock": 15,
      "category": "Eletrônicos",
      "supplier": {
        "id": 100,
        "name": "Fornecedor A"
      }
    }
  ]
}
```

### 2. EvaluateJsonPath

Após SplitJson em `$.products`:

```
Nome: product.sku
Valor: $.sku

Nome: product.name
Valor: $.name

Nome: product.price
Valor: $.price

Nome: product.stock
Valor: $.stock

Nome: product.category
Valor: $.category

Nome: product.supplier_id
Valor: $.supplier.id

Nome: product.supplier_name
Valor: $.supplier.name
```

### 3. Tabela SQLite

```sql
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    category TEXT,
    supplier_id INTEGER,
    supplier_name TEXT,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para atualizar timestamp
CREATE TRIGGER IF NOT EXISTS update_product_timestamp
AFTER UPDATE ON products
BEGIN
    UPDATE products SET last_updated = CURRENT_TIMESTAMP
    WHERE sku = NEW.sku;
END;
```

---

## Exemplo 3: Fluxo Completo com Tratamento de Erros

### Estrutura do Fluxo

```
InvokeHTTP
    │
    ├─→ Response → ValidateRecord ─→ valid → SplitJson → EvaluateJsonPath
    │                    │
    │                    └─→ invalid → LogAttribute → RouteOnAttribute
    │
    └─→ Failure → LogAttribute → PutFile (salvar erros)


EvaluateJsonPath
    │
    ├─→ matched → UpdateAttribute → PutDatabaseRecord → success → LogAttribute
    │                                       │
    │                                       └─→ failure → PutFile (salvar falhas)
    │
    └─→ unmatched → LogAttribute
```

### UpdateAttribute - Adicionar Metadados

Propriedades customizadas:
```
processing.timestamp = ${now():format('yyyy-MM-dd HH:mm:ss')}
source.api = products-api
database.table = products
batch.id = ${UUID()}
```

---

## Exemplo 4: APIs Reais para Teste

### API 1: JSONPlaceholder (Usuários)

```
URL: https://jsonplaceholder.typicode.com/users
Método: GET
```

**Estrutura do JSON:**
```json
[
  {
    "id": 1,
    "name": "Leanne Graham",
    "username": "Bret",
    "email": "Sincere@april.biz",
    "phone": "1-770-736-8031 x56442",
    "website": "hildegard.org"
  }
]
```

**Tabela SQLite:**
```sql
CREATE TABLE IF NOT EXISTS jsonplaceholder_users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**EvaluateJsonPath (após SplitJson em `$`):**
```
user.id = $.id
user.name = $.name
user.username = $.username
user.email = $.email
user.phone = $.phone
user.website = $.website
```

### API 2: JSONPlaceholder (Posts)

```
URL: https://jsonplaceholder.typicode.com/posts
Método: GET
```

**Estrutura:**
```json
[
  {
    "userId": 1,
    "id": 1,
    "title": "sunt aut facere...",
    "body": "quia et suscipit..."
  }
]
```

**Tabela:**
```sql
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title TEXT,
    body TEXT,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### API 3: ViaCEP (Consulta de CEP)

```
URL: https://viacep.com.br/ws/01001000/json/
Método: GET
```

**JSON:**
```json
{
  "cep": "01001-000",
  "logradouro": "Praça da Sé",
  "complemento": "lado ímpar",
  "bairro": "Sé",
  "localidade": "São Paulo",
  "uf": "SP",
  "ibge": "3550308"
}
```

**Tabela:**
```sql
CREATE TABLE IF NOT EXISTS enderecos (
    cep TEXT PRIMARY KEY,
    logradouro TEXT,
    complemento TEXT,
    bairro TEXT,
    cidade TEXT,
    uf TEXT,
    ibge TEXT,
    consultado_em DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Scripts Úteis de SQLite

### 1. Script de Limpeza

```sql
-- Limpar todos os dados
DELETE FROM users;

-- Resetar auto-increment
DELETE FROM sqlite_sequence WHERE name='users';

-- Vacuum para liberar espaço
VACUUM;
```

### 2. Script de Análise

```sql
-- Ver tamanho da tabela
SELECT
    COUNT(*) as total_registros,
    (SELECT COUNT(*) FROM users WHERE DATE(processed_at) = DATE('now')) as hoje,
    (SELECT COUNT(*) FROM users WHERE DATE(processed_at) = DATE('now', '-1 day')) as ontem
FROM users;

-- Ver distribuição por data
SELECT
    DATE(processed_at) as data,
    COUNT(*) as quantidade
FROM users
GROUP BY DATE(processed_at)
ORDER BY data DESC;
```

### 3. Backup e Restore

```bash
# Fazer backup
docker exec nifi sqlite3 /tmp/nifi_database.db ".backup /tmp/backup.db"
docker cp nifi:/tmp/backup.db ./backup_$(date +%Y%m%d).db

# Restaurar backup
docker cp ./backup_20250129.db nifi:/tmp/restore.db
docker exec nifi sqlite3 /tmp/nifi_database.db ".restore /tmp/restore.db"
```

---

## Configurações Avançadas

### 1. InvokeHTTP com Autenticação

#### Bearer Token:
```
Properties:
- HTTP Method: GET
- Remote URL: https://api.exemplo.com/dados
- Authorization Header: Bearer ${api.token}
```

Adicione antes um **UpdateAttribute**:
```
api.token = seu_token_aqui
```

#### Basic Auth:
```
- Remote URL: https://api.exemplo.com/dados
- Basic Authentication Username: usuario
- Basic Authentication Password: senha
```

### 2. InvokeHTTP com Headers Customizados

```
Properties customizadas (botão +):
- Content-Type: application/json
- Accept: application/json
- X-API-Key: ${api.key}
- User-Agent: NiFi-ETL/1.0
```

### 3. Rate Limiting

Para evitar sobrecarregar a API:

```
InvokeHTTP Scheduling:
- Run Schedule: 60 sec (executa a cada minuto)
- Concurrent Tasks: 1 (apenas uma execução por vez)
```

### 4. Retry em caso de falha

Conecte a saída `Retry` do InvokeHTTP de volta para ele mesmo com um delay:

1. Clique com botão direito na conexão
2. Configure:
   - **FlowFile Expiration**: 5 min
   - **Back Pressure Object Threshold**: 10

---

## Monitoramento e Debug

### 1. Ver conteúdo do FlowFile

1. Pare o fluxo
2. Clique com botão direito em uma conexão
3. **List queue**
4. Clique no ícone de visualização (olho)
5. Veja os dados em **CONTENT** e **ATTRIBUTES**

### 2. Logs detalhados

No processor:
```
Settings → Bulletin Level: DEBUG
Settings → Log Level: DEBUG
```

Ver logs:
```bash
docker-compose logs -f nifi | grep -i error
```

### 3. Estatísticas

No canvas, você verá:
- **In**: FlowFiles entrando
- **Read/Write**: Taxa de leitura/escrita
- **Out**: FlowFiles saindo
- **Tasks/Time**: Número de tarefas e tempo total

---

## Template Pronto

Após configurar seu fluxo:

1. Selecione todos os processors (Ctrl+A)
2. Menu hambúrguer → **Create Template**
3. Nome: `API_to_SQLite_ETL`
4. Descrição: `Fluxo para consumir API e inserir no SQLite`
5. Salvar

Para importar em outro NiFi:
1. Menu hambúrguer → **Upload Template**
2. Selecione o arquivo XML
3. Arraste um **Template** para o canvas
4. Selecione seu template

---

## Performance Tips

1. **Batch Processing**: Configure o PutDatabaseRecord para inserir em lotes
   ```
   Maximum Batch Size: 100
   ```

2. **Connection Pooling**: No DBCPConnectionPool
   ```
   Max Wait Time: 500 millis
   Max Total Connections: 8
   ```

3. **Backpressure**: Ajuste nas conexões
   ```
   Object Threshold: 10000
   Size Threshold: 1 GB
   ```

4. **Concurrent Tasks**: Aumente se necessário
   ```
   Scheduling → Concurrent Tasks: 2
   ```

---

**Estes exemplos cobrem os casos mais comuns. Ajuste conforme sua necessidade!**
