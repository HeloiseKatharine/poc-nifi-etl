# SFTP CaixaGIS - Serviço de Demonstração

Serviço SFTP simulando a CaixaGIS para POC (Proof of Concept). Este ambiente permite o envio e recebimento de arquivos via SFTP para testes e demonstrações.

## Estrutura do Projeto

```
sftp/
├── docker-compose.yml ou compose.yml  # Configuração do Docker Compose
├── config/
│   └── users.conf          # Configuração de usuários SFTP
├── data/
│   ├── upload/             # Diretório para arquivos enviados
│   └── download/           # Diretório para arquivos disponíveis para download
└── README.md               # Este arquivo
```

## Credenciais de Acesso

- **Host:** localhost
- **Porta:** 2222
- **Usuário:** caixagis
- **Senha:** caixagis123

## Como Iniciar

### 1. Subir o serviço

```bash
docker compose up -d
```

### 2. Verificar se está rodando

```bash
docker compose ps
```

### 3. Ver logs

```bash
docker compose logs -f sftp-caixagis
```

## Como Testar a Conexão

### Via SFTP Client (linha de comando)

```bash
sftp -P 2222 caixagis@localhost
# Senha: caixagis123
```

### Via SCP (enviar arquivo)

```bash
scp -P 2222 arquivo.txt caixagis@localhost:/upload/
```

### Via SCP (baixar arquivo)

```bash
scp -P 2222 caixagis@localhost:/download/arquivo.txt ./
```

### Comandos SFTP úteis

Após conectar via `sftp -P 2222 caixagis@localhost`:

```bash
ls                  # Listar arquivos
cd upload           # Navegar para diretório upload
put arquivo.txt     # Enviar arquivo
get arquivo.txt     # Baixar arquivo
exit               # Sair
```

## Integração com NiFi

Para conectar o Apache NiFi a este serviço SFTP:

1. Use o processador **GetSFTP** ou **PutSFTP**
2. Configure com as credenciais acima
3. O hostname dentro da rede Docker será `sftp-caixagis` (não localhost)

### Exemplo de configuração NiFi:

- **Hostname:** sftp-caixagis
- **Port:** 22 (porta interna do container)
- **Username:** caixagis
- **Password:** caixagis123
- **Remote Path:** /upload ou /download

---

# Tutorial Completo: Download de CSV via SFTP e Inserção no PostgreSQL

## Objetivo

Criar um fluxo no Apache NiFi que:
1. Conecta ao serviço SFTP
2. Baixa arquivos CSV da pasta `/download`
3. Processa o conteúdo do CSV
4. Insere os dados no PostgreSQL

---

## Pré-requisitos

Antes de começar, certifique-se de que:

1. O serviço SFTP está rodando:
   ```bash
   docker compose up -d
   ```

2. O NiFi e PostgreSQL estão rodando (no diretório pai):
   ```bash
   cd ..
   docker compose up -d
   ```

3. Os containers estão na mesma rede Docker ou podem se comunicar

---

## Arquitetura do Fluxo

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   GetSFTP    │────→│  SplitText   │────→│  ConvertRecord   │────→│ PutDatabaseRecord│
│              │     │              │     │                  │     │                  │
└──────────────┘     └──────────────┘     └──────────────────┘     └──────────────────┘
       │                    │                      │                        │
       ↓                    ↓                      ↓                        ↓
   Download CSV      Remove Header         CSV → Record              Insert no DB
```

---

## Passo 1: Configurar a Rede Docker

Para que o NiFi possa acessar o SFTP, ambos precisam estar na mesma rede Docker.

### Opção 1: Conectar o SFTP à rede do NiFi

Edite o arquivo `docker-compose.yml` ou `compose.yml` do SFTP e adicione a rede externa:

```yaml
services:
  sftp-caixagis:
    # ... configurações existentes ...
    networks:
      - sftp-network
      - nifi_network  # Adicione esta linha

networks:
  sftp-network:
    driver: bridge
  nifi_network:
    external: true  # Adicione esta rede externa
```

Depois, reinicie o serviço:

```bash
docker compose down
docker compose up -d
```

### Opção 2: Verificar conectividade

Teste se o NiFi consegue acessar o SFTP:

```bash
docker exec -it nifi bash
ping sftp-caixagis
exit
```

---

## Passo 2: Acessar o NiFi

1. Acesse: https://localhost:8443/nifi/
2. Faça login com as credenciais configuradas no `.env` do NiFi
3. Aceite o aviso de certificado SSL (ambiente de desenvolvimento)

---

## Passo 3: Criar o Controller Service para PostgreSQL

Antes de criar o fluxo, precisamos configurar a conexão com o banco de dados.

### 3.1 Acessar Controller Services

1. No menu superior direito, clique no ícone de **hambúrguer** (☰)
2. Selecione **Controller Settings**
3. Vá para a aba **CONTROLLER SERVICES**

### 3.2 Adicionar DBCPConnectionPool

1. Clique no botão **+** (adicionar)
2. Busque por `DBCPConnectionPool`
3. Clique em **ADD**

### 3.3 Configurar o DBCPConnectionPool

1. Clique no ícone de **engrenagem** (⚙️) do service
2. Vá para **PROPERTIES**
3. Configure:
   - **Database Connection URL**: `jdbc:postgresql://postgres:5432/postgres`
   - **Database Driver Class Name**: `org.postgresql.Driver`
   - **Database User**: `postgres`
   - **Password**: `postgres`
   - **Database Driver Location(s)**: `/opt/nifi/nifi-current/lib/postgresql-jdbc.jar`
4. Clique em **APPLY**

### 3.4 Instalar o Driver PostgreSQL

Execute no terminal:

```bash
docker exec -it nifi bash -c "cd /opt/nifi/nifi-current/lib && curl -O https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar && mv postgresql-42.7.1.jar postgresql-jdbc.jar"
```

### 3.5 Habilitar o Controller Service

1. Clique no ícone de **raio** (⚡) no DBCPConnectionPool
2. Clique em **ENABLE**

---

## Passo 4: Criar Record Readers e Writers

### 4.1 Criar CSVReader

1. No **Controller Services**, clique em **+**
2. Busque por `CSVReader`
3. Clique em **ADD**
4. Clique no ícone de **engrenagem** (⚙️)
5. Configure as propriedades:
   - **Schema Access Strategy**: `Infer Schema`
   - **CSV Format**: `Custom Format`
   - **Value Separator**: `;` (ponto e vírgula)
   - **Skip Header Line**: `true`
   - **Treat First Line as Header**: `true`
   - **Charset Encoding**: `ISO-8859-1` ou `UTF-8` (dependendo do arquivo)
6. Clique em **APPLY**
7. **Habilite** o service (⚡)

### 4.2 Criar JsonRecordSetWriter

1. Clique em **+**
2. Busque por `JsonRecordSetWriter`
3. Clique em **ADD**
4. Deixe as configurações padrão
5. Clique em **APPLY**
6. **Habilite** o service (⚡)

---

## Passo 5: Construir o Fluxo no Canvas

### 5.1 Adicionar GetSFTP Processor

Este processor fará o download dos arquivos CSV do servidor SFTP.

1. **Adicionar o Processor:**
   - Arraste o ícone de **Processor** (⚙️) para o canvas
   - Busque por `GetSFTP`
   - Clique em **ADD**

2. **Configurar o GetSFTP:**
   - Clique duas vezes no processor
   - Vá para a aba **PROPERTIES**
   - Configure:
     - **Hostname**: `sftp-caixagis`
     - **Port**: `22`
     - **Username**: `caixagis`
     - **Password**: `caixagis123`
     - **Remote Path**: `/download`
     - **Search Recursively**: `false`
     - **File Filter Regex**: `.*\.csv` (apenas arquivos CSV)
     - **Path Filter Regex**: (deixe em branco)
     - **Polling Interval**: `60 sec`
     - **Connection Timeout**: `30 sec`
     - **Data Timeout**: `30 sec`
     - **Use Compression**: `false`
     - **Delete Original**: `false` (mude para `true` se quiser remover após download)
     - **Strict Host Key Checking**: `false`

3. **Configurar Scheduling:**
   - Vá para a aba **SCHEDULING**
   - **Run Schedule**: `60 sec` (verifica novos arquivos a cada 60 segundos)

4. **Configurar Relationships:**
   - Vá para a aba **SETTINGS**
   - Marque para **auto-terminate**:
     - `not.found` (se não houver arquivos)
     - `permission.denied`
     - `failure`
   - Deixe **success** desmarcado

5. Clique em **APPLY**

---

### 5.2 Adicionar SplitText (Opcional - para processar linha a linha)

Se você quiser processar o CSV linha por linha (útil para arquivos grandes):

1. **Adicionar o Processor:**
   - Arraste um **Processor**
   - Busque por `SplitText`
   - Clique em **ADD**

2. **Configurar:**
   - **Line Split Count**: `1000` (processa 1000 linhas por vez)
   - **Header Line Count**: `1` (pula o cabeçalho)
   - **Remove Trailing Newlines**: `true`

3. **Auto-terminate:**
   - `failure`
   - `original`
   - Deixe `splits` desmarcado

4. Clique em **APPLY**

---

### 5.3 Adicionar ConvertRecord (Opcional - para validar CSV)

Este processor converte o CSV para um formato intermediário e valida a estrutura.

1. **Adicionar o Processor:**
   - Arraste um **Processor**
   - Busque por `ConvertRecord`
   - Clique em **ADD**

2. **Configurar:**
   - **Record Reader**: Selecione o `CSVReader` criado
   - **Record Writer**: Selecione o `JsonRecordSetWriter` criado

3. **Auto-terminate:**
   - `failure`
   - Deixe `success` desmarcado

4. Clique em **APPLY**

---

### 5.4 Adicionar PutDatabaseRecord

Este processor insere os dados do CSV no PostgreSQL.

1. **Adicionar o Processor:**
   - Arraste um **Processor**
   - Busque por `PutDatabaseRecord`
   - Clique em **ADD**

2. **Configurar:**
   - **Record Reader**: Selecione o `CSVReader` criado
   - **Database Connection Pooling Service**: Selecione o `DBCPConnectionPool`
   - **Statement Type**: `INSERT`
   - **Table Name**: `dados_csv` (ou o nome da sua tabela)
   - **Translate Field Names**: `true`
   - **Unmatched Field Behavior**: `Ignore Unmatched Fields`
   - **Unmatched Column Behavior**: `Ignore Unmatched Columns`
   - **Update Keys**: (deixe vazio para INSERT simples)
   - **Field Containing SQL**: (deixe vazio)
   - **Allow Multiple Statements**: `false`
   - **Quote Column Identifiers**: `false`
   - **Quote Table Identifiers**: `false`

3. **Auto-terminate:**
   - `failure`
   - `retry`
   - Deixe `success` desmarcado (para monitorar)

4. Clique em **APPLY**

---

### 5.5 Conectar os Processors

Agora vamos conectar tudo:

1. **GetSFTP → ConvertRecord** (ou PutDatabaseRecord direto)
   - Arraste a seta do GetSFTP para o próximo processor
   - Selecione **success**
   - Clique em **ADD**

2. **ConvertRecord → PutDatabaseRecord** (se estiver usando)
   - Arraste a seta
   - Selecione **success**
   - Clique em **ADD**

3. **PutDatabaseRecord → (Auto-terminate ou LogAttribute)**
   - Configure auto-terminate ou adicione um LogAttribute para debug

---

## Passo 6: Criar a Tabela no PostgreSQL

Antes de executar o fluxo, crie a tabela no PostgreSQL.

### 6.1 Analisar a estrutura do CSV

Primeiro, veja a estrutura do seu arquivo CSV:

```bash
head -n 2 data/download/teste-sftp.csv
```

Exemplo de saída:
```
ID;Projeto;Tipo;Situação;Título;Descrição;Últimas notas
114685;e-SUS Regulação;Demanda;Demanda - Entregue;...
```

### 6.2 Criar a tabela correspondente

Execute no terminal:

```bash
# Acessar o container do PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Criar a tabela (ajuste os campos conforme seu CSV)
CREATE TABLE IF NOT EXISTS dados_csv (
    id INTEGER PRIMARY KEY,
    projeto VARCHAR(255),
    tipo VARCHAR(100),
    situacao VARCHAR(100),
    titulo TEXT,
    descricao TEXT,
    ultimas_notas TEXT
);

# Verificar se a tabela foi criada
\dt

# Ver a estrutura da tabela
\d dados_csv

# Sair
\q
```

**Importante:** Os nomes das colunas devem corresponder aos headers do CSV (considerando `Translate Field Names = true`, o NiFi converterá automaticamente).

---

## Passo 7: Executar o Fluxo

### 7.1 Adicionar arquivo de teste

Se ainda não tiver um arquivo CSV na pasta download:

```bash
# Copiar um arquivo de exemplo
cp ../teste-sftp.csv data/download/

# Ou criar um arquivo de teste simples
cat > data/download/teste.csv << 'EOF'
ID;Projeto;Tipo;Situacao;Titulo;Descricao;Ultimas_notas
1;Projeto A;Demanda;Aberta;Teste 1;Descrição teste 1;Notas 1
2;Projeto B;Bug;Fechada;Teste 2;Descrição teste 2;Notas 2
EOF
```

### 7.2 Iniciar o Fluxo

1. **Selecionar todos os processors:**
   - Pressione `Ctrl+A` ou arraste para selecionar todos

2. **Iniciar o fluxo:**
   - Clique no botão **Play** (▶️) na barra de operações

3. **Monitorar:**
   - Você verá números aparecendo nas conexões (flowfiles)
   - Os números representam quantos arquivos/registros estão sendo processados

### 7.3 Verificar o processamento

1. **Ver filas:**
   - Clique com botão direito nas conexões → **List queue**
   - Você pode visualizar o conteúdo dos flowfiles

2. **Ver logs:**
   - Clique com botão direito no processor → **View Status History**
   - Ou veja os logs do container: `docker compose logs -f nifi`

3. **Verificar contadores:**
   - Cada processor mostra quantos flowfiles foram processados
   - Verde indica sucesso, vermelho indica erro

---

## Passo 8: Verificar os Dados no PostgreSQL

```bash
# Acessar o PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Consultar os dados inseridos
SELECT * FROM dados_csv;

# Contar registros
SELECT COUNT(*) FROM dados_csv;

# Ver as primeiras linhas
SELECT * FROM dados_csv LIMIT 10;

# Sair
\q
```

---

## Tratamento de Erros e Melhorias

### Adicionar LogAttribute para Debug

É útil adicionar um processor para logar informações:

1. Adicione **LogAttribute** no canvas
2. Conecte as saídas de **failure** dos processors para ele
3. Configure:
   - **Log Level**: `info`
   - **Log Payload**: `true` (se quiser ver o conteúdo)
4. Marque todos os relationships como **auto-terminate**

### Adicionar UpdateAttribute

Para adicionar metadados ou timestamps:

1. Adicione **UpdateAttribute** entre GetSFTP e PutDatabaseRecord
2. Adicione propriedades customizadas:
   - `data_importacao`: `${now():format('yyyy-MM-dd HH:mm:ss')}`
   - `arquivo_origem`: `${filename}`

### Configurar Retry em caso de falha

1. Configure um **RetryFlowFile** processor
2. Conecte a saída **failure** do PutDatabaseRecord para ele
3. Configure:
   - **Retry Attribute**: `retry.count`
   - **Maximum Retries**: `3`
   - **Penalize Retries**: `true`

---

## Troubleshooting

### Erro: "Connection refused" ou "No route to host"

**Problema:** NiFi não consegue acessar o SFTP.

**Solução:**
1. Verifique se ambos os containers estão rodando:
   ```bash
   docker ps
   ```

2. Verifique se estão na mesma rede:
   ```bash
   docker network ls
   docker network inspect nifi_network
   ```

3. Teste conectividade:
   ```bash
   docker exec -it nifi ping sftp-caixagis
   ```

4. Se necessário, conecte manualmente:
   ```bash
   docker network connect nifi_network sftp-caixagis
   ```

---

### Erro: "Authentication failed"

**Problema:** Credenciais incorretas.

**Solução:**
1. Verifique as credenciais no GetSFTP:
   - Username: `caixagis`
   - Password: `caixagis123`

2. Teste manualmente:
   ```bash
   docker exec -it nifi bash
   sftp -P 22 caixagis@sftp-caixagis
   # Senha: caixagis123
   ```

---

### Erro: "Table doesn't exist"

**Problema:** Tabela não foi criada no PostgreSQL.

**Solução:**
1. Crie a tabela antes de executar o fluxo (veja Passo 6)
2. Verifique o nome da tabela no PutDatabaseRecord

---

### Erro: "Cannot load driver class"

**Problema:** Driver PostgreSQL não está instalado.

**Solução:**
1. Instale o driver (veja Passo 3.4)
2. Reinicie o NiFi:
   ```bash
   cd ..
   docker compose restart nifi
   ```

---

### CSV com encoding errado (caracteres estranhos)

**Problema:** Caracteres especiais aparecem como `�`.

**Solução:**
1. No CSVReader, ajuste o **Charset Encoding**:
   - Tente `ISO-8859-1`
   - Ou `Windows-1252`
   - Ou `UTF-8`

2. Converta o arquivo antes:
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 arquivo.csv > arquivo_utf8.csv
   ```

---

### FlowFiles ficam presos na fila

**Problema:** Os arquivos não estão sendo processados.

**Solução:**
1. Clique com botão direito no processor → **View Configuration**
2. Vá para **Settings** → **Bulletin Level**: `DEBUG`
3. Veja os logs: `docker compose logs -f nifi`
4. Verifique se há erros nos bulletins (canto superior direito)

---

### CSV com delimitador diferente

**Problema:** Seu CSV usa vírgula (,) em vez de ponto e vírgula (;).

**Solução:**
1. No CSVReader, ajuste o **Value Separator**:
   - Para vírgula: `,`
   - Para tab: `\t`
   - Para pipe: `|`

---

### Arquivos grandes causam timeout

**Problema:** Arquivos CSV muito grandes não são processados.

**Solução:**
1. Use o **SplitText** para quebrar o arquivo em pedaços menores
2. Aumente os timeouts no GetSFTP
3. Aumente a memória do NiFi no arquivo de configuração do Compose:
   ```yaml
   environment:
     - NIFI_JVM_HEAP_MAX=4g
   ```

---

## Fluxo Completo com Validação

Para um fluxo mais robusto, adicione validação:

```
GetSFTP → UpdateAttribute → ConvertRecord → ValidateRecord → RouteOnAttribute
                                                  │                    │
                                                  │                    └─→ PutDatabaseRecord
                                                  │
                                                  └─→ LogAttribute (invalid)
```

### Adicionar ValidateRecord

1. Adicione o processor **ValidateRecord**
2. Configure:
   - **Record Reader**: CSVReader
   - **Record Writer**: JsonRecordSetWriter
   - **Schema Access Strategy**: `Infer Schema`

3. Conecte:
   - **valid** → PutDatabaseRecord
   - **invalid** → LogAttribute (para debug)

---

## Monitoramento e Alertas

### Configurar notificações

Para receber alertas quando algo der errado:

1. Configure um **PutEmail** processor
2. Conecte as saídas de **failure** para ele
3. Configure SMTP e destinatários

### Configurar métricas

1. Use o **MonitorActivity** processor para detectar quando o fluxo para
2. Configure alertas no **Bulletin Board**

---

## Backup e Versionamento

### Salvar o fluxo como Template

1. Selecione todos os processors (Ctrl+A)
2. Menu hambúrguer (☰) → **Create Template**
3. Dê um nome: "SFTP to PostgreSQL CSV Import"
4. Clique em **CREATE**

### Exportar o fluxo

1. Menu hambúrguer (☰) → **NiFi Flow Configuration**
2. Clique em **Download Flow**
3. Salve o arquivo XML em um local seguro

---

## Próximos Passos

1. **Adicionar tratamento de duplicatas:**
   - Use `UPSERT` em vez de `INSERT`
   - Configure **Update Keys** no PutDatabaseRecord

2. **Processar múltiplos arquivos:**
   - GetSFTP já processa múltiplos arquivos automaticamente
   - Use **MergeContent** se precisar juntar vários CSVs

3. **Adicionar transformação de dados:**
   - Use **JoltTransformJSON** para transformar campos
   - Use **QueryRecord** para filtrar ou agregar dados

4. **Implementar particionamento:**
   - Use **PartitionRecord** para dividir por critérios
   - Processe diferentes tipos de dados em fluxos separados

5. **Adicionar auditoria:**
   - Crie uma tabela de controle para rastrear importações
   - Registre: data/hora, arquivo, quantidade de registros, status

---

## Exemplo de Tabela de Controle

```sql
CREATE TABLE IF NOT EXISTS controle_importacao (
    id SERIAL PRIMARY KEY,
    arquivo_nome VARCHAR(255),
    data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    registros_importados INTEGER,
    status VARCHAR(50),
    mensagem_erro TEXT
);
```

Use um **PutSQL** adicional para registrar cada importação nesta tabela.

---

## Conclusão

Agora você tem um fluxo completo e robusto para:
- ✅ Conectar ao SFTP
- ✅ Baixar arquivos CSV
- ✅ Validar e processar os dados
- ✅ Inserir no PostgreSQL
- ✅ Tratar erros e falhas
- ✅ Monitorar e fazer debug

Para mais informações sobre NiFi, consulte a [documentação oficial](https://nifi.apache.org/docs.html).

## Adicionar Arquivos de Teste

Para adicionar arquivos de teste no diretório download:

```bash
echo "Arquivo de teste" > data/download/teste.txt
```

## Parar o Serviço

```bash
docker compose down
```

## Remover Volumes e Dados

```bash
docker compose down -v
rm -rf data/*
```

## Troubleshooting

### Erro de permissão ao conectar

Certifique-se de que os diretórios `data/upload` e `data/download` existem:

```bash
mkdir -p data/upload data/download
```

### Não consegue conectar

Verifique se a porta 2222 não está em uso:

```bash
netstat -an | grep 2222
```

### Ver logs detalhados

```bash
docker compose logs -f
```

## Segurança

**ATENÇÃO:** Este é um ambiente de demonstração/POC. Não use em produção com estas credenciais!

Para produção, considere:
- Usar chaves SSH ao invés de senha
- Alterar as credenciais padrão
- Implementar rate limiting
- Usar volumes persistentes
- Implementar backup dos dados
