# Tutorial: Criando um Fluxo ETL no Apache NiFi

## Objetivo
Criar um fluxo que:
1. Conecta a um serviço externo via GET
2. Recebe um JSON como resposta
3. Processa e transforma o JSON
4. Insere os dados em um banco PostgreSQL

---

## Visão Geral do Fluxo

```
InvokeHTTP → EvaluateJsonPath → ConvertRecord → PutDatabaseRecord
```

---

## Passo 1: Acessar o NiFi

1. Acesse: https://localhost:8443/nifi/
2. Login:
   - Usuário: `admin`
   - Senha: `adminadminadmin`
3. Aceite o aviso de certificado SSL (ambiente de desenvolvimento)

---

## Passo 2: Criar o Fluxo

### 2.1 Adicionar o Processor InvokeHTTP

Este processor fará a chamada GET ao serviço externo.

1. **Adicionar o Processor:**
   - Arraste o ícone de **Processor** (símbolo de engrenagem) para o canvas
   - Na busca, digite `InvokeHTTP`
   - Selecione **InvokeHTTP** e clique em **ADD**

2. **Configurar o InvokeHTTP:**
   - Clique duas vezes no processor para abrir as configurações
   - Vá para a aba **PROPERTIES**
   - Configure:
     - **HTTP Method**: `GET`
     - **Remote URL**: `https://api.exemplo.com/dados` (substitua pela sua URL)
     - **Connection Timeout**: `30 sec`
     - **Read Timeout**: `30 sec`

3. **Configurar Scheduling:**
   - Vá para a aba **SCHEDULING**
   - **Run Schedule**: `60 sec` (executará a cada 60 segundos)
   - Ou use `0 sec` para execução contínua

4. **Configurar Relationships (Auto-terminate):**
   - Vá para a aba **SETTINGS**
   - Marque estas relationships para **auto-terminate** (terminação automática):
     - `Retry`
     - `No Retry`
     - `Failure`
   - Deixe **Response** desmarcado (usaremos essa saída)

5. Clique em **APPLY**

---

### 2.2 Adicionar o Processor EvaluateJsonPath

Este processor extrairá campos específicos do JSON.

1. **Adicionar o Processor:**
   - Arraste outro **Processor** para o canvas
   - Digite `EvaluateJsonPath`
   - Clique em **ADD**

2. **Configurar o EvaluateJsonPath:**
   - Clique duas vezes no processor
   - Vá para **PROPERTIES**
   - Configure:
     - **Destination**: `flowfile-attribute`
     - **Return Type**: `json`

3. **Adicionar propriedades customizadas** (clique no botão **+**):

   Exemplo de extração de campos do JSON:
   ```
   Nome da Propriedade: json.id
   Valor: $.id

   Nome da Propriedade: json.nome
   Valor: $.nome

   Nome da Propriedade: json.email
   Valor: $.email

   Nome da Propriedade: json.data
   Valor: $.data
   ```

   > **Nota**: Ajuste os JSONPath de acordo com a estrutura do seu JSON

   Exemplo de JSON:
   ```json
   {
     "id": 123,
     "nome": "João Silva",
     "email": "joao@exemplo.com",
     "data": "2025-12-29"
   }
   ```

4. **Configurar Relationships:**
   - Em **SETTINGS**, marque para **auto-terminate**:
     - `failure`
     - `unmatched`
   - Deixe **matched** desmarcado

5. Clique em **APPLY**

---

### 2.3 Conectar InvokeHTTP ao EvaluateJsonPath

1. Passe o mouse sobre o **InvokeHTTP**
2. Arraste a seta que aparece até o **EvaluateJsonPath**
3. Na janela de conexão, selecione **Response**
4. Clique em **ADD**

---

### 2.4 Configurar o Controller Service para PostgreSQL

Antes de adicionar o processor de banco de dados, precisamos configurar a conexão.

1. **Acessar Controller Services:**
   - No menu superior direito, clique no ícone de **hambúrguer** (três linhas)
   - Selecione **Controller Settings**
   - Vá para a aba **CONTROLLER SERVICES**

2. **Adicionar DBCPConnectionPool:**
   - Clique no botão **+** (adicionar)
   - Busque por `DBCPConnectionPool`
   - Clique em **ADD**

3. **Configurar o DBCPConnectionPool:**
   - Clique no ícone de **engrenagem** (configurações) do service
   - Vá para **PROPERTIES**
   - Configure:
     - **Database Connection URL**: `jdbc:postgresql://postgres:5432/postgres`
     - **Database Driver Class Name**: `org.postgresql.Driver`
     - **Database User**: `postgres`
     - **Password**: `postgres`
     - **Database Driver Location(s)**: `/opt/nifi/nifi-current/lib/postgresql-jdbc.jar`

4. **Instalar o driver PostgreSQL no container:**

   Abra um terminal e execute:
   ```bash
   # Baixar o driver PostgreSQL
   docker exec -it nifi bash -c "cd /opt/nifi/nifi-current/lib && curl -O https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar && mv postgresql-42.7.1.jar postgresql-jdbc.jar"
   ```

5. **Habilitar o Controller Service:**
   - Clique no ícone de **raio** (enable) no DBCPConnectionPool
   - Clique em **ENABLE**

---

### 2.5 Criar Schema para Conversão (JsonTreeReader)

1. **Voltar para Controller Services**
2. **Adicionar JsonTreeReader:**
   - Clique em **+**
   - Busque `JsonTreeReader`
   - Clique em **ADD**

3. **Configurar JsonTreeReader:**
   - Clique em configurações
   - Deixe as configurações padrão
   - Clique em **APPLY**
   - **Habilite** o service (ícone de raio)

---

### 2.6 Criar Schema Writer (AvroRecordSetWriter)

1. **Adicionar AvroRecordSetWriter:**
   - Clique em **+**
   - Busque `AvroRecordSetWriter`
   - Clique em **ADD**

2. **Configurar:**
   - Deixe configurações padrão
   - Clique em **APPLY**
   - **Habilite** o service

---

### 2.7 Adicionar ConvertRecord (Opcional)

Se você precisar transformar o JSON para outro formato antes de inserir.

1. **Adicionar Processor:**
   - Arraste um **Processor**
   - Digite `ConvertRecord`
   - Clique em **ADD**

2. **Configurar:**
   - **Record Reader**: Selecione o `JsonTreeReader` criado
   - **Record Writer**: Selecione o `AvroRecordSetWriter` criado

3. **Auto-terminate:**
   - `failure`
   - Deixe `success` desmarcado

---

### 2.8 Adicionar PutDatabaseRecord

Este processor inserirá os dados no PostgreSQL.

1. **Adicionar Processor:**
   - Arraste um **Processor**
   - Digite `PutDatabaseRecord`
   - Clique em **ADD**

2. **Configurar o PutDatabaseRecord:**
   - **Record Reader**: Selecione o `JsonTreeReader`
   - **Statement Type**: `INSERT`
   - **Database Connection Pooling Service**: Selecione o `DBCPConnectionPool` criado
   - **Table Name**: `dados_api` (ou o nome da sua tabela)
   - **Translate Field Names**: `true`
   - **Unmatched Field Behavior**: `Ignore Unmatched Fields`
   - **Unmatched Column Behavior**: `Ignore Unmatched Columns`

3. **Auto-terminate:**
   - Marque: `failure`, `retry`
   - Deixe `success` desmarcado (para ver o resultado)

4. Clique em **APPLY**

---

### 2.9 Conectar os Processors

1. Conecte **EvaluateJsonPath** → **PutDatabaseRecord**
   - Relationship: `matched`

---

### 2.10 Criar a Tabela no PostgreSQL

Você precisará criar a tabela no banco de dados antes de executar o fluxo.

Execute no terminal:

```bash
# Acessar o container do PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Criar a tabela (ajuste os campos conforme seu JSON)
CREATE TABLE IF NOT EXISTS dados_api (
    id INTEGER PRIMARY KEY,
    nome VARCHAR(255),
    email VARCHAR(255),
    data VARCHAR(50)
);

# Verificar
\dt

# Sair
\q
```

---

## Passo 3: Executar o Fluxo

1. **Selecionar todos os processors:**
   - Pressione `Ctrl+A` ou arraste para selecionar todos

2. **Iniciar o fluxo:**
   - Clique no botão **Play** (▶) na barra de operações

3. **Monitorar:**
   - Você verá números aparecendo nas conexões (flowfiles)
   - Clique com botão direito nas conexões para ver **List queue**
   - Verifique se os dados estão sendo processados

---

## Passo 4: Verificar os Dados no PostgreSQL

```bash
# Acessar o container do PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Consultar os dados
SELECT * FROM dados_api;

# Sair
\q
```

---

## Alternativas e Melhorias

### Opção 1: Usar PutSQL ao invés de PutDatabaseRecord

Se preferir controle total sobre o SQL:

1. Adicione o processor **PutSQL**
2. Antes dele, adicione **ReplaceText** para criar o INSERT statement:
   ```sql
   INSERT INTO dados_api (id, nome, email, data)
   VALUES (${json.id}, '${json.nome}', '${json.email}', '${json.data}')
   ```

### Opção 2: Transformar JSON com JoltTransformJSON

Se precisar transformar a estrutura do JSON:

1. Adicione **JoltTransformJSON** após o InvokeHTTP
2. Configure a especificação Jolt para transformar o JSON

### Opção 3: Validar JSON com ValidateRecord

1. Adicione **ValidateRecord** para validar o schema do JSON
2. Configure um schema Avro para validação

---

## Tratamento de Erros

### Adicionar LogAttribute

Para debug, adicione um processor **LogAttribute**:

1. Conecte qualquer saída de `failure` para ele
2. Configure para logar todos os atributos
3. Veja os logs: `docker-compose logs -f nifi`

### Adicionar UpdateAttribute

Para adicionar timestamps ou outros metadados:

1. Adicione **UpdateAttribute** no fluxo
2. Adicione propriedades:
   - `processing.timestamp`: `${now():format('yyyy-MM-dd HH:mm:ss')}`
   - `source.api`: `nome-da-api`

---

## Dicas Importantes

1. **Backpressure**: Configure backpressure nas conexões para evitar overflow
   - Clique com botão direito na conexão → Configure
   - Ajuste Object Threshold e Size Threshold

2. **Scheduling**: Ajuste o intervalo de execução do InvokeHTTP conforme necessário

3. **Bulletin Board**: Monitore alertas no canto superior direito

4. **Data Provenance**: Clique com botão direito nos flowfiles → View Data Provenance

5. **Templates**: Salve seu fluxo como template:
   - Selecione todos os processors
   - Menu hambúrguer → Create Template

---

## Fluxo Completo Resumido

```
┌──────────────┐     Response      ┌────────────────────┐
│              │──────────────────→│                    │
│ InvokeHTTP   │                   │ EvaluateJsonPath   │
│              │                   │                    │
└──────────────┘                   └────────────────────┘
                                            │
                                            │ matched
                                            ↓
                                   ┌────────────────────┐
                                   │                    │
                                   │ PutDatabaseRecord  │
                                   │                    │
                                   └────────────────────┘
                                            │
                                            │ success
                                            ↓
                                   ┌────────────────────┐
                                   │                    │
                                   │  LogAttribute      │
                                   │  (opcional)        │
                                   └────────────────────┘
```

---

## Troubleshooting

### Erro: "Cannot load driver class org.postgresql.Driver"
- Verifique se o JAR do PostgreSQL foi baixado corretamente
- Reinicie o NiFi: `docker-compose restart nifi`

### Erro: "Table doesn't exist"
- Crie a tabela no PostgreSQL antes de executar o fluxo

### Erro: "Connection refused"
- Verifique se o container do PostgreSQL está rodando: `docker ps`
- Certifique-se de que ambos os containers estão na mesma network

### FlowFiles ficam presos
- Verifique os logs dos processors
- Clique no processor → View Configuration → Settings → Bulletin Level: DEBUG

### Timeout na chamada HTTP
- Aumente os timeouts no InvokeHTTP
- Verifique se a URL está acessível

---

## Próximos Passos

1. Adicione validação de dados
2. Configure retry em caso de falha
3. Implemente tratamento de duplicatas
4. Adicione notificações (email, Slack, etc)
5. Configure backup dos dados
6. Implemente versionamento do fluxo

---

**Boa sorte com seu fluxo ETL no Apache NiFi!**
