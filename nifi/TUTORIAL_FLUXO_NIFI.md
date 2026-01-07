# Tutorial: Criando um Fluxo ETL no Apache NiFi

## Objetivo
Criar um fluxo que:
1. Conecta ao servidor SFTP (caixagis-sftp)
2. Baixa arquivos CSV da pasta `/download`
3. Divide o CSV em registros individuais
4. Converte e renomeia os campos do CSV
5. Insere os dados na tabela `dados_csv` do PostgreSQL

## Estrutura da Tabela de Destino

```sql
CREATE TABLE public.dados_csv (
    projeto text NULL,
    tipo text NULL,
    situacao text NULL,
    titulo text NULL,
    descricao text NULL,
    ultimas_notas text NULL,
    id int4 NULL
);
```

---

## Visão Geral do Fluxo

```
GetSFTP → SplitText → ConvertRecord → RenameRecordField → PutDatabaseRecord
```

### Detalhamento dos Processors

1. **GetSFTP (2.2.0)**: Conecta ao servidor SFTP e baixa arquivos CSV
2. **SplitText (2.2.0)**: Divide o arquivo CSV em blocos menores para processamento
3. **ConvertRecord (2.2.0)**: Converte o formato CSV para registros estruturados
4. **RenameRecordField (2.2.0)**: Renomeia os campos do CSV para corresponder à tabela do banco
5. **PutDatabaseRecord (2.2.0)**: Insere os registros no PostgreSQL

### Mapeamento de Campos CSV → Banco de Dados

O CSV de origem possui campos com maiúsculas e acentuação que precisam ser renomeados:

| Campo no CSV         | Campo no Banco |
|---------------------|----------------|
| ID                  | id             |
| Projeto             | projeto        |
| Tipo                | tipo           |
| Situação            | situacao       |
| Título              | titulo         |
| Descrição           | descricao      |
| Últimas notas       | ultimas_notas  |

---

## Passo 1: Acessar o NiFi

1. Acesse: https://localhost:8443/nifi/
2. Login:
   - Usuário: `admin`
   - Senha: `adminadminadmin`
3. Aceite o aviso de certificado SSL (ambiente de desenvolvimento)

---

## Passo 2: Configurar Controller Services

Antes de criar o fluxo, precisamos configurar os serviços de leitura/escrita de registros e a conexão com o banco de dados.

### 2.1 Acessar Controller Services

1. No menu superior direito, clique no ícone de **hambúrguer** (☰)
2. Selecione **Controller Settings**
3. Vá para a aba **MANAGEMENT CONTROLLER SERVICES**

### 2.2 Adicionar e Configurar CSVReader

O CSVReader lerá os dados do arquivo CSV.

1. **Adicionar CSVReader:**
   - Clique no botão **+** (adicionar)
   - Busque por `CSVReader`
   - Clique em **ADD**

2. **Configurar o CSVReader:**
   - Clique no ícone de **engrenagem** (⚙️)
   - Vá para **PROPERTIES**
   - Configure:
     - **Schema Access Strategy**: `Use String Fields From Header`
     - **CSV Format**: `Custom Format`
     - **Value Separator**: `,` (vírgula)
     - **Skip Header Line**: `false`
     - **Treat First Line as Header**: `true`
     - **Quote Character**: `"`
     - **Escape Character**: `\`
     - **Trim Fields**: `true`
     - **Charset Encoding**: `UTF-8`

3. Clique em **APPLY**
4. **Habilite** o service (ícone de raio ⚡)

### 2.3 Adicionar e Configurar JsonRecordSetWriter

Este writer será usado para escrever registros no formato JSON intermediário.

1. **Adicionar JsonRecordSetWriter:**
   - Clique em **+**
   - Busque por `JsonRecordSetWriter`
   - Clique em **ADD**

2. **Configurar:**
   - **Schema Write Strategy**: `Do Not Write Schema`
   - **Schema Access Strategy**: `Inherit Record Schema`
   - **Pretty Print JSON**: `false`
   - Deixe as demais configurações padrão

3. Clique em **APPLY**
4. **Habilite** o service (⚡)

### 2.4 Adicionar e Configurar DBCPConnectionPool

Configuração da conexão com o PostgreSQL.

1. **Adicionar DBCPConnectionPool:**
   - Clique no botão **+**
   - Busque por `DBCPConnectionPool`
   - Clique em **ADD**

2. **Configurar o DBCPConnectionPool:**
   - Clique no ícone de **engrenagem** (⚙️)
   - Vá para **PROPERTIES**
   - Configure:
     - **Database Connection URL**: `jdbc:postgresql://postgres:5432/postgres`
     - **Database Driver Class Name**: `org.postgresql.Driver`
     - **Database Driver Location(s)**: `/opt/nifi/nifi-current/lib/postgresql-jdbc.jar`
     - **Database User**: `postgres`
     - **Password**: `postgres`

3. **Instalar o driver PostgreSQL no container:**

   Abra um terminal e execute:
   ```bash
   # Baixar o driver PostgreSQL
   docker exec -it nifi bash -c "cd /opt/nifi/nifi-current/lib && curl -O https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar && mv postgresql-42.7.1.jar postgresql-jdbc.jar"
   ```

4. Clique em **APPLY**
5. **Habilite** o service (ícone de raio ⚡)

---

## Passo 3: Criar o Fluxo

### 3.1 Adicionar GetSFTP Processor

Este processor conectará ao servidor SFTP e baixará os arquivos CSV.

1. **Adicionar o Processor:**
   - Arraste o ícone de **Processor** (⚙️) para o canvas
   - Na busca, digite `GetSFTP`
   - Selecione **GetSFTP** e clique em **ADD**

2. **Configurar o GetSFTP:**
   - Clique duas vezes no processor para abrir as configurações
   - Vá para a aba **PROPERTIES**
   - Configure:
     - **Hostname**: `sftp-caixagis`
     - **Port**: `22`
     - **Username**: `caixagis`
     - **Password**: `caixagis123`
     - **Remote Path**: `/download`
     - **File Filter Regex**: `.*\.csv` (apenas arquivos CSV)
     - **Path Filter Regex**: (deixe em branco)
     - **Polling Interval**: `60 sec`
     - **Search Recursively**: `false`
     - **Delete Original**: `false` (mude para `true` se quiser remover após download)
     - **Connection Timeout**: `30 sec`
     - **Data Timeout**: `30 sec`
     - **Strict Host Key Checking**: `false`
     - **Use Compression**: `false`

3. **Configurar Scheduling:**
   - Vá para a aba **SCHEDULING**
   - **Run Schedule**: `60 sec` (verifica novos arquivos a cada 60 segundos)

4. **Configurar Relationships (Auto-terminate):**
   - Vá para a aba **Relationships**
   - Deixe **success** desmarcado

5. Clique em **APPLY**

---

### 3.2 Adicionar SplitText Processor

O SplitText dividirá o CSV em blocos de linhas para processamento mais eficiente.

1. **Adicionar o Processor:**
   - Arraste um **Processor** para o canvas
   - Digite `SplitText`
   - Clique em **ADD**

2. **Configurar o SplitText:**
   - Clique duas vezes no processor
   - Vá para **PROPERTIES**
   - Configure:
     - **Line Split Count**: `100` (processa 100 linhas por vez, ajuste conforme necessário)
     - **Maximum Fragment Size**: `0` (sem limite de tamanho) ou deixe em branco
     - **Header Line Count**: `1` (mantém o cabeçalho em cada split)
     - **Header Line Marker Characters**: (deixe em branco)
     - **Remove Trailing Newlines**: `true`

3. **Configurar Relationships:**
   - Vá para **SETTINGS**
   - Marque para **auto-terminate**:
     - `failure`
     - `original`
   - Deixe **splits** desmarcado

4. Clique em **APPLY**

---

### 3.3 Conectar GetSFTP ao SplitText

1. Passe o mouse sobre o **GetSFTP**
2. Arraste a seta que aparece até o **SplitText**
3. Na janela de conexão, selecione **success**
4. Clique em **ADD**

---

### 3.4 Adicionar ConvertRecord Processor

O ConvertRecord validará e converterá o CSV para um formato de registro estruturado.

1. **Adicionar o Processor:**
   - Arraste um **Processor** para o canvas
   - Digite `ConvertRecord`
   - Clique em **ADD**

2. **Configurar o ConvertRecord:**
   - **Record Reader**: Selecione o `CSVReader` criado anteriormente
   - **Record Writer**: Selecione o `JsonRecordSetWriter` criado anteriormente
   - **Include Zero Record FlowFiles**: `false`

3. **Configurar Relationships:**
   - Marque para **auto-terminate**:
     - `failure`
   - Deixe **success** desmarcado

4. Clique em **APPLY**

---

### 3.5 Conectar SplitText ao ConvertRecord

1. Arraste a seta do **SplitText** até o **ConvertRecord**
2. Selecione **splits**
3. Clique em **ADD**

---

### 3.6 Adicionar RenameRecordField Processor

O RenameRecordField renomeará os campos do CSV para corresponder aos nomes das colunas no banco de dados.

1. **Adicionar o Processor:**
   - Arraste um **Processor** para o canvas
   - Digite `RenameRecordField`
   - Clique em **ADD**

2. **Configurar o RenameRecordField:**
   - **Record Reader**: Selecione o `JsonTreeReader` criado anteriormente
   - **Record Writer**: Selecione o `JsonRecordSetWriter` criado anteriormente

3. **Adicionar Mapeamentos de Campos** (clique no **+** para adicionar propriedades customizadas):

   Adicione cada mapeamento no formato `/campo_origem` → `/campo_destino`:

   | Nome da Propriedade | Valor da Propriedade |
   |---------------------|---------------------|
   | `/"ID"`               | `/id`               |
   | `/"Projeto"`          | `/projeto`          |
   | `/"Tipo"`             | `/tipo`             |
   | `/"Situação"`         | `/situacao`         |
   | `/"Título"`           | `/titulo`           |
   | `/"Descrição"`        | `/descricao`        |
   | `/"Últimas notas"`    | `/ultimas_notas`    |

   > **Importante**: O RenameRecordField usa o formato `/campo_origem` como nome da propriedade e `/campo_destino` como valor.

4. **Configurar Relationships:**
   - Vá para a aba **SETTINGS**
   - Marque para **auto-terminate**:
     - `failure`
   - Deixe **success** desmarcado

5. Clique em **APPLY**

---

### 3.7 Conectar ConvertRecord ao RenameRecordField

1. Arraste a seta do **ConvertRecord** até o **RenameRecordField**
2. Selecione **success**
3. Clique em **ADD**

---

### 3.8 Adicionar PutDatabaseRecord Processor

Este processor inserirá os dados no PostgreSQL.

1. **Adicionar o Processor:**
   - Arraste um **Processor** para o canvas
   - Digite `PutDatabaseRecord`
   - Clique em **ADD**

2. **Configurar o PutDatabaseRecord:**
   - **Record Reader**: Selecione o `JsonTreeReader`
   - **Database Type**: `PostgreSQL`
   - **Statement Type**: `INSERT`
   - **Database Connection Pooling Service**: Selecione o `DBCPConnectionPool` criado
   - **Schema Name**: (deixe em branco)
   - **Table Name**: `dados_csv`
   - **Translate Field Names**: `true`
   - **Unmatched Field Behavior**: `Ignore Unmatched Fields`
   - **Unmatched Column Behavior**: `Ignore Unmatched Columns`
   - **Update Keys**: (deixe em branco)
   - **Field Containing SQL**: (deixe em branco)
   - **Allow Multiple Statements**: `false`
   - **Quote Column Identifiers**: `false`
   - **Quote Table Identifiers**: `false`
   - **Maximum Batch Size**: `100`

3. **Configurar Relationships:**
   - Marque para **auto-terminate**:
     - `failure`
     - `retry`
   - Deixe **success** desmarcado (para monitorar)

4. Clique em **APPLY**

---

### 3.9 Conectar RenameRecordField ao PutDatabaseRecord

1. Arraste a seta do **RenameRecordField** até o **PutDatabaseRecord**
2. Selecione **success**
3. Clique em **ADD**

---

### 3.10 Adicionar LogAttribute (Opcional - para monitoramento)

Para debug e monitoramento, adicione um processor para logar o sucesso.

1. **Adicionar o Processor:**
   - Arraste um **Processor**
   - Digite `LogAttribute`
   - Clique em **ADD**

2. **Configurar:**
   - **Log Level**: `info`
   - **Log Payload**: `false`
   - **Attributes to Log**: (deixe em branco para logar todos)
   - **Log Prefix**: `[SUCCESS] `

3. **Configurar Relationships:**
   - Marque **success** para auto-terminate

4. Clique em **APPLY**

5. **Conectar:**
   - Arraste a seta do **PutDatabaseRecord** até o **LogAttribute**
   - Selecione **success**
   - Clique em **ADD**

---

## Passo 4: Criar a Tabela no PostgreSQL

Antes de executar o fluxo, crie a tabela de destino no banco de dados.

Execute no terminal:

```bash
# Acessar o container do PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Criar a tabela usando o script init.sql
CREATE TABLE IF NOT EXISTS public.dados_csv (
    projeto text NULL,
    tipo text NULL,
    situacao text NULL,
    titulo text NULL,
    descricao text NULL,
    ultimas_notas text NULL,
    id int4 NULL
);

# Verificar se a tabela foi criada
\dt

# Visualizar a estrutura da tabela
\d dados_csv

# Sair
\q
```

> **Dica**: O arquivo `init.sql` na raiz do projeto contém essa mesma estrutura de tabela.

---

## Passo 5: Verificar Conectividade SFTP ↔ NiFi

Antes de executar o fluxo, certifique-se de que o NiFi consegue acessar o servidor SFTP.

### 5.1 Verificar se os containers estão rodando

```bash
# Verificar containers do NiFi e PostgreSQL
docker compose ps

# Verificar container do SFTP (no diretório caixagis-sftp)
cd ../caixagis-sftp
docker compose ps
cd ../nifi
```

### 5.2 Testar conectividade

```bash
# Entrar no container do NiFi
docker exec -it nifi bash

# Tentar ping no servidor SFTP
ping -c 3 sftp-caixagis

# Sair
exit
```

Se o ping não funcionar, você precisará conectar ambos os containers na mesma rede Docker. Consulte o README do caixagis-sftp para instruções.

---

## Passo 6: Executar o Fluxo

### 6.1 Adicionar arquivo de teste (se necessário)

Certifique-se de que há pelo menos um arquivo CSV na pasta download do SFTP:

```bash
cd ../caixagis-sftp

# Verificar se há arquivos
ls -la data/download/

# Se não houver arquivo, crie um de teste
cat > data/download/teste.csv << 'EOF'
ID,Projeto,Tipo,Situação,Título,Descrição,Últimas notas
1,Sistema X,Demanda,Aberto,Implementar login,Sistema de autenticação,Em desenvolvimento
2,Portal Y,Bug,Fechado,Corrigir menu,Menu lateral quebrado,Corrigido
EOF

cd ../nifi
```

### 6.2 Iniciar o Fluxo

1. **Selecionar todos os processors:**
   - No canvas do NiFi, pressione `Ctrl+A` ou arraste para selecionar todos

2. **Iniciar o fluxo:**
   - Clique no botão **Play** (▶️) na barra de operações (ou clique com o botão direito e selecione "Start")

3. **Monitorar:**
   - Você verá números aparecendo nas conexões (flowfiles sendo processados)
   - Os números indicam quantos arquivos/registros estão em cada etapa
   - Verde indica processamento bem-sucedido
   - Vermelho indica erros

### 6.3 Verificar o processamento

1. **Ver filas:**
   - Clique com botão direito nas conexões → **List queue**
   - Você pode visualizar o conteúdo dos flowfiles

2. **Ver status dos processors:**
   - Cada processor mostra estatísticas:
     - **In**: FlowFiles recebidos
     - **Out**: FlowFiles enviados
     - **Tasks/Time**: Tarefas executadas e tempo total

3. **Ver logs em tempo real:**
   ```bash
   docker compose logs -f nifi
   ```

---

## Passo 7: Verificar os Dados no PostgreSQL

Após alguns minutos (dependendo do tamanho do arquivo), verifique se os dados foram inseridos:

```bash
# Acessar o container do PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Consultar os dados inseridos
SELECT * FROM dados_csv;

# Consultar com formatação limitada
SELECT
    id,
    projeto,
    tipo,
    situacao,
    titulo
FROM dados_csv
LIMIT 10;

# Contar registros
SELECT COUNT(*) FROM dados_csv;

# Ver distribuição por tipo
SELECT tipo, COUNT(*) as quantidade
FROM dados_csv
GROUP BY tipo
ORDER BY quantidade DESC;

# Ver distribuição por situação
SELECT situacao, COUNT(*) as quantidade
FROM dados_csv
GROUP BY situacao
ORDER BY quantidade DESC;

# Sair
\q
```

---

## Diagrama do Fluxo Completo

```
┌──────────────────────────────────────────────────────────────────────┐
│                           FLUXO ETL COMPLETO                         │
│                      SFTP CSV → PostgreSQL                           │
└──────────────────────────────────────────────────────────────────────┘

    Servidor SFTP (sftp-caixagis)
    /download/*.csv
           │
           │ SFTP Connection
           │ Port 22
           ↓
    ┌─────────────────┐
    │                 │
    │    GetSFTP      │  ← Conecta ao servidor SFTP
    │    (v2.2.0)     │    Host: sftp-caixagis
    │                 │    Path: /download
    │                 │    Filter: *.csv
    └────────┬────────┘
             │ success
             │ (arquivo CSV completo)
             ↓
    ┌─────────────────┐
    │                 │
    │   SplitText     │  ← Divide o CSV em blocos
    │   (v2.2.0)      │    Line Split Count: 100
    │                 │    Header Line Count: 1
    └────────┬────────┘
             │ splits
             │ (múltiplos flowfiles com blocos)
             ↓
    ┌─────────────────┐
    │                 │
    │ ConvertRecord   │  ← Converte CSV → Record
    │   (v2.2.0)      │    Reader: CSVReader
    │                 │    Writer: JsonRecordSetWriter
    └────────┬────────┘
             │ success
             │ (registros estruturados)
             ↓
    ┌─────────────────────┐
    │                     │
    │ RenameRecordField   │  ← Renomeia campos
    │     (v2.2.0)        │    ID → id
    │                     │    Projeto → projeto
    │                     │    Situação → situacao
    │                     │    Título → titulo
    │                     │    Descrição → descricao
    │                     │    Últimas notas → ultimas_notas
    └────────┬────────────┘
             │ success
             │ (campos renomeados)
             ↓
    ┌─────────────────────┐
    │                     │
    │ PutDatabaseRecord   │  ← Insere no PostgreSQL
    │     (v2.2.0)        │    Host: postgres:5432
    │                     │    Table: dados_csv
    │                     │    Type: INSERT
    └────────┬────────────┘
             │ success
             │
             ↓
         PostgreSQL
    Table: dados_csv
    Columns: id, projeto, tipo,
             situacao, titulo,
             descricao, ultimas_notas
```

### Visualização do Canvas Real

```
┌────────────────────────────────────────────────────────────────┐
│  Apache NiFi - Flow Canvas                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   [GetSFTP]────────────────────────────────────────────┐       │
│        │                                                │       │
│        │ success (Queue: 0)                             │       │
│        ↓                                                │       │
│   [SplitText]                          original_splits  │       │
│        │                               (Queue: 112)     │       │
│        │ splits (Queue: 0)                   └──────────┘       │
│        ↓                                                        │
│   [ConvertRecord]                                               │
│        │                                                        │
│        │ success (Queue: 0)                                     │
│        ↓                                                        │
│   [RenameRecordField]                                           │
│        │                                                        │
│        │ success (Queue: 0)                                     │
│        ↓                                                        │
│   [PutDatabaseRecord]                                           │
│                                                                │
│  Status: ▶ Running    Tasks/Time: 0 / 00:00:00.000            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Tratamento de Erros e Melhorias

### Adicionar Tratamento de Falhas

Para cada processor, você pode conectar a saída `failure` a um **LogAttribute** para debug:

1. Adicione um processor **LogAttribute** no canvas
2. Configure:
   - **Log Level**: `error`
   - **Log Payload**: `true` (para ver o conteúdo que falhou)
   - **Attributes to Log**: (deixe em branco)
   - **Log Prefix**: `[ERROR] `

3. Conecte as saídas de **failure** de cada processor para este LogAttribute

4. Auto-terminate a saída **success** do LogAttribute

### Adicionar Retry em Caso de Falha de Banco

1. Adicione um processor **RetryFlowFile** após o PutDatabaseRecord
2. Conecte a saída **retry** do PutDatabaseRecord para ele
3. Configure:
   - **Retry Attribute**: `retry.count`
   - **Maximum Retries**: `3`
   - **Penalize Retries**: `true`
   - **Reuse Mode**: `Fail on Reuse`

4. Conecte a saída **retry** do RetryFlowFile de volta para o PutDatabaseRecord
5. Conecte a saída **retries_exceeded** para um LogAttribute

### Adicionar UpdateAttribute para Metadados

Para adicionar informações de processamento:

1. Adicione **UpdateAttribute** após o GetSFTP
2. Adicione propriedades customizadas:
   - `data.processamento`: `${now():format('yyyy-MM-dd HH:mm:ss')}`
   - `arquivo.origem`: `${filename}`
   - `sftp.host`: `sftp-caixagis`

### Configurar Backpressure

Para evitar sobrecarga de memória em arquivos grandes:

1. Clique com botão direito em cada conexão → **Configure**
2. Configure:
   - **Object Threshold**: `1000` (máximo de flowfiles na fila)
   - **Size Threshold**: `100 MB` (tamanho máximo da fila)

---

## Dicas Importantes

1. **Performance**:
   - Ajuste o **Line Split Count** do SplitText conforme o tamanho dos seus arquivos
   - Para arquivos pequenos (< 1000 linhas), você pode remover o SplitText
   - Para arquivos grandes (> 100.000 linhas), aumente para 1000 ou mais

2. **Encoding**:
   - Se o CSV tiver caracteres especiais, verifique o encoding no CSVReader
   - Opções comuns: `UTF-8`, `ISO-8859-1`, `Windows-1252`

3. **Separadores**:
   - O CSV de exemplo usa vírgula (`,`), mas se o seu usar ponto e vírgula (`;`), altere o **Value Separator** no CSVReader

4. **Monitoramento**:
   - Use o **Bulletin Board** (canto superior direito) para ver alertas
   - Configure **Bulletin Level** como `DEBUG` nos processors para mais detalhes

5. **Data Provenance**:
   - Clique com botão direito em qualquer flowfile → **View Data Provenance**
   - Isso mostra todo o histórico de processamento do dado

6. **Salvar como Template**:
   - Selecione todos os processors (`Ctrl+A`)
   - Menu hambúrguer (☰) → **Create Template**
   - Nome sugerido: "SFTP CSV to PostgreSQL"

---

## Troubleshooting

### Erro: "Connection refused" ao conectar no SFTP

**Causa**: NiFi não consegue acessar o container do SFTP.

**Solução**:
1. Verifique se o SFTP está rodando:
   ```bash
   cd ../caixagis-sftp
   docker compose ps
   ```

2. Verifique se estão na mesma rede:
   ```bash
   docker network ls
   docker network inspect nifi_network
   ```

3. Se necessário, conecte manualmente:
   ```bash
   docker network connect nifi_network sftp-caixagis
   ```

---

### Erro: "Cannot load driver class org.postgresql.Driver"

**Causa**: Driver PostgreSQL não foi instalado corretamente.

**Solução**:
1. Instale o driver (veja Passo 2.4)
2. Reinicie o NiFi:
   ```bash
   docker compose restart nifi
   ```
3. Aguarde 2-3 minutos para o NiFi reiniciar
4. Verifique se o arquivo existe:
   ```bash
   docker exec -it nifi ls -la /opt/nifi/nifi-current/lib/postgresql-jdbc.jar
   ```

---

### Erro: "Table doesn't exist"

**Causa**: Tabela não foi criada no PostgreSQL.

**Solução**:
1. Crie a tabela antes de executar o fluxo (veja Passo 4)
2. Verifique se a tabela existe:
   ```bash
   docker exec -it postgres psql -U postgres -d postgres -c "\dt"
   ```

---

### Erro: "Authentication failed" no SFTP

**Causa**: Credenciais incorretas ou servidor SFTP não está pronto.

**Solução**:
1. Verifique as credenciais no GetSFTP:
   - Username: `caixagis`
   - Password: `caixagis123`
   - Hostname: `sftp-caixagis`
   - Port: `22`

2. Teste manualmente:
   ```bash
   docker exec -it nifi bash
   sftp -P 22 caixagis@sftp-caixagis
   # Senha: caixagis123
   ls /download
   exit
   ```

---

### CSV com encoding errado (caracteres estranhos como �)

**Causa**: Encoding incorreto configurado no CSVReader.

**Solução**:
1. No CSVReader, teste diferentes encodings:
   - `UTF-8` (padrão)
   - `ISO-8859-1` (comum em sistemas antigos)
   - `Windows-1252` (comum em arquivos do Windows)

2. Ou converta o arquivo antes:
   ```bash
   cd ../caixagis-sftp/data/download
   iconv -f ISO-8859-1 -t UTF-8 arquivo.csv > arquivo_utf8.csv
   ```

---

### FlowFiles ficam presos na fila

**Causa**: Erro de processamento não visível.

**Solução**:
1. Clique com botão direito no processor → **View Configuration** → **Settings**
2. Altere **Bulletin Level** para `DEBUG`
3. Veja os logs:
   ```bash
   docker compose logs -f nifi | grep ERROR
   ```
4. Verifique os bulletins no canto superior direito da interface

---

### Nenhum arquivo é baixado do SFTP

**Causa**: Não há arquivos correspondentes ao filtro, ou polling não está funcionando.

**Solução**:
1. Verifique se há arquivos CSV na pasta:
   ```bash
   cd ../caixagis-sftp
   ls -la data/download/*.csv
   ```

2. No GetSFTP, verifique:
   - **File Filter Regex**: `.*\.csv`
   - **Remote Path**: `/download`

3. Force uma execução manual:
   - Clique com botão direito no GetSFTP → **Run Once**

---

### Dados duplicados no banco

**Causa**: O mesmo arquivo está sendo processado múltiplas vezes.

**Solução**:
1. Configure **Delete Original** como `true` no GetSFTP (remove arquivo após download)
2. Ou configure **Move Destination Directory** para mover arquivos processados para outra pasta
3. Ou adicione constraint UNIQUE na coluna `id` da tabela:
   ```sql
   ALTER TABLE dados_csv ADD CONSTRAINT dados_csv_id_unique UNIQUE (id);
   ```

---

## Alternativas e Otimizações

### Opção 1: Processar sem SplitText (para arquivos pequenos)

Se seus arquivos CSV têm menos de 1000 linhas, você pode remover o SplitText:

```
GetSFTP → ConvertRecord → UpdateRecord → PutDatabaseRecord
```

### Opção 2: Usar UPSERT ao invés de INSERT

Para evitar duplicatas e atualizar registros existentes:

1. No **PutDatabaseRecord**, altere:
   - **Statement Type**: `INSERT`
   - **Update Keys**: `id`
   - Isso fará um INSERT ou UPDATE baseado no campo `id`

### Opção 3: Adicionar Validação de Dados

1. Adicione **ValidateRecord** após o ConvertRecord
2. Configure um schema para validar os campos obrigatórios
3. Conecte:
   - **valid** → UpdateRecord
   - **invalid** → LogAttribute (para registrar dados inválidos)

### Opção 4: Particionar por Tipo ou Situação

Se você quiser processar diferentes tipos de dados de forma diferente:

1. Adicione **PartitionRecord** ou **RouteOnAttribute**
2. Configure rotas baseadas no campo **tipo** ou **situacao**
3. Processe cada partição em fluxos separados

---

## Monitoramento e Métricas

### Ver Estatísticas do Fluxo

1. Menu hambúrguer (☰) → **Summary**
2. Veja estatísticas de cada processor:
   - FlowFiles In/Out
   - Bytes In/Out
   - Tasks/Time
   - Erros

### Configurar Alertas

1. Menu hambúrguer (☰) → **Controller Settings** → **Reporting Tasks**
2. Adicione **Bulletin Reporter** para enviar alertas
3. Configure notificações por email, Slack, etc.

### Exportar Métricas

1. Configure **PrometheusReportingTask** para exportar métricas
2. Integre com Grafana para dashboards visuais

---

## Próximos Passos

1. **Implementar auditoria**: Crie uma tabela de controle para rastrear:
   - Arquivo processado
   - Data/hora
   - Quantidade de registros
   - Status (sucesso/falha)

2. **Adicionar notificações**: Configure email ou webhook para alertas de falha

3. **Implementar backup**: Mova arquivos processados para uma pasta de backup

4. **Configurar schedules**: Ajuste os intervalos de polling conforme necessidade

5. **Adicionar transformações**: Use **QueryRecord** ou **JoltTransformJSON** para transformações complexas

6. **Implementar versionamento**: Salve o fluxo como template e versione no Git

---

## Exemplo de Tabela de Controle de Importação

```sql
CREATE TABLE IF NOT EXISTS controle_importacao (
    id SERIAL PRIMARY KEY,
    arquivo_nome VARCHAR(255) NOT NULL,
    arquivo_tamanho BIGINT,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    registros_processados INTEGER,
    registros_sucesso INTEGER,
    registros_falha INTEGER,
    status VARCHAR(50),
    mensagem_erro TEXT,
    tempo_processamento_ms BIGINT
);
```

Use um **PutSQL** adicional paralelo ao fluxo principal para registrar cada processamento.

---

**Parabéns! Você criou um fluxo ETL completo de SFTP para PostgreSQL usando Apache NiFi!** 🎉

Para mais informações, consulte:
- [Documentação oficial do Apache NiFi](https://nifi.apache.org/docs.html)
- README.md do projeto caixagis-sftp
- Arquivo init.sql para estrutura da tabela
