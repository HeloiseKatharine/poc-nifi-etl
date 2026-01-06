# Diagrama Visual do Fluxo NiFi

## Fluxo ETL: SFTP CSV → PostgreSQL

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FLUXO COMPLETO: CSV ETL                           │
│                  SFTP → Transformação → PostgreSQL                   │
└──────────────────────────────────────────────────────────────────────┘

Servidor SFTP                                             PostgreSQL
sftp-caixagis                                             postgres:5432
/download/*.csv                                           dados_csv
     │                                                         ▲
     │ SFTP Port 22                                            │
     │ User: caixagis                                          │
     ▼                                                         │
┌──────────────┐                                              │
│              │                                              │
│   GetSFTP    │  Conecta ao SFTP e baixa CSV                 │
│   (v2.2.0)   │  Remote Path: /download                      │
│              │  File Filter: .*\.csv                        │
└──────┬───────┘  Polling: 60 sec                             │
       │                                                       │
       │ success                                               │
       │ (arquivo CSV completo)                                │
       │ Content: ID,Projeto,Tipo,Situação,...                 │
       ▼                                                       │
┌──────────────┐                                              │
│              │                                              │
│  SplitText   │  Divide CSV em blocos de 100 linhas          │
│  (v2.2.0)    │  Mantém header em cada bloco                 │
│              │  Header Line Count: 1                        │
└──────┬───────┘                                              │
       │                                                       │
       │ splits (múltiplos FlowFiles)                          │
       │ FlowFile 1: (linhas 1-100)                            │
       │ FlowFile 2: (linhas 101-200)                          │
       ▼                                                       │
┌─────────────────────┐                                       │
│                     │                                       │
│  ConvertRecord      │  Converte CSV → Record               │
│    (v2.2.0)         │  Reader: CSVReader                    │
│                     │  Writer: JsonRecordSetWriter          │
│                     │  Schema: From Header                  │
└──────┬──────────────┘                                       │
       │                                                       │
       │ success (registros estruturados)                      │
       │ Record: {ID:1, Projeto:"X", ...}                      │
       ▼                                                       │
┌──────────────────────┐                                      │
│                      │                                      │
│ RenameRecordField    │  Renomeia campos do CSV              │
│     (v2.2.0)         │  Transformações:                     │
│                      │  /ID → /id                           │
│ Reader: CSVReader    │  /Projeto → /projeto                 │
│ Writer: JsonRecordWr │  /Situação → /situacao               │
│                      │  /Título → /titulo                   │
│                      │  /Descrição → /descricao             │
│                      │  /Últimas notas → /ultimas_notas     │
└──────┬───────────────┘                                      │
       │                                                       │
       │ success (campos renomeados)                           │
       │ Record: {id:1, projeto:"X", ...}                      │
       ▼                                                       │
┌──────────────────────┐                                      │
│                      │                                      │
│ PutDatabaseRecord    │  Insere registros no PostgreSQL      │
│     (v2.2.0)         │  INSERT INTO dados_csv               │
│                      │  (id, projeto, tipo,                 │
│ Reader: JsonRecordWr │   situacao, titulo,                  │
│ Table: dados_csv     │   descricao, ultimas_notas)          │
│ DB: DBCPConnectionPl │  VALUES (...)                         │
│                      │──────────────────────────────────────┘
└──────────────────────┘
       │
       │ success
       ▼
   [Terminate]
```

---

## Fluxo com Tratamento de Erros

```
                        Servidor SFTP (sftp-caixagis)
                                     │
                                     │ Port 22
                                     ▼
                            ┌──────────────┐
                            │              │
                            │   GetSFTP    │
                            │   (v2.2.0)   │
                            └──────┬───────┘
                                   │
                    ┌──────────────┼──────────────────────┐
                    │              │                      │
               success      permission.denied      not.found/failure
                    │              │                      │
                    ▼              ▼                      ▼
            ┌──────────┐    ┌────────────┐         [Terminate]
            │          │    │            │
            │SplitText │    │LogAttribute│
            │ (v2.2.0) │    │  (Error)   │
            └────┬─────┘    └──────┬─────┘
                 │                 │
        ┌────────┼────────┐        │
        │        │        │        ▼
     splits  original failure  ┌─────────┐
        │        │        │     │ PutFile │
        ▼        ▼        ▼     │ (Erros) │
   ┌──────────┐ [Term]  [Term]  └─────────┘
   │Convert   │
   │ Record   │
   │(v2.2.0)  │
   └────┬─────┘
        │
    ┌───┼─────┐
    │   │     │
success │  failure
    │   │     │
    ▼   ▼     ▼
  ┌────────────────┐  ┌────────────┐
  │RenameRecord    │  │LogAttribute│
  │Field (v2.2.0)  │  │ (Error)    │
  └─────┬──────────┘  └────────────┘
        │
    ┌───┼────┐
    │   │    │
success │ failure
    │   │    │
    ▼   ▼    ▼
  ┌──────────────────┐  ┌─────────┐
  │PutDatabaseRecord │  │ PutFile │
  │    (v2.2.0)      │  │(Failures)│
  └──────┬───────────┘  └─────────┘
         │
     ┌───┼────┐
     │   │    │
 success │  retry/failure
     │   │    │
     ▼   ▼    ▼
  [Term] │  [Term]
         │
         ▼
   ┌──────────┐
   │LogAttr   │
   │(Success) │
   └──────────┘
```

---

## Componentes Detalhados

### 1. GetSFTP (v2.2.0)
```
┌─────────────────────────────────────────┐
│            GetSFTP                      │
├─────────────────────────────────────────┤
│ Configuração:                           │
│  • Hostname: sftp-caixagis              │
│  • Port: 22                             │
│  • Username: caixagis                   │
│  • Password: caixagis123                │
│  • Remote Path: /download               │
│  • File Filter Regex: .*\.csv           │
│  • Polling Interval: 60 sec             │
│  • Connection Timeout: 30 sec           │
│  • Data Timeout: 30 sec                 │
│  • Delete Original: false               │
│  • Strict Host Key Checking: false      │
│                                         │
│ Scheduling:                             │
│  • Run Schedule: 60 sec                 │
│  • Concurrent Tasks: 1                  │
│                                         │
│ Saídas:                                 │
│  • success ──────→ (FlowFile com CSV)   │
│  • not.found ────→ [Auto-terminate]     │
│  • permission.den→ [Auto-terminate]     │
│  • failure ──────→ [Auto-terminate]     │
└─────────────────────────────────────────┘
```

### 2. SplitText (v2.2.0)
```
┌─────────────────────────────────────────┐
│           SplitText                     │
├─────────────────────────────────────────┤
│ Entrada:                                │
│  Content:                               │
│    ID,Projeto,Tipo,Situação,...         │
│    1,Sistema X,Demanda,Aberto,...       │
│    2,Portal Y,Bug,Fechado,...           │
│    ... (mais 1000 linhas)               │
│                                         │
│ Configuração:                           │
│  • Line Split Count: 100                │
│  • Maximum Fragment Size: 0             │
│  • Header Line Count: 1                 │
│  • Remove Trailing Newlines: true       │
│                                         │
│ Saídas:                                 │
│  • splits ───→ FlowFile 1: (100 linhas) │
│           └──→ FlowFile 2: (100 linhas) │
│           └──→ FlowFile N...            │
│  • original ─→ [Auto-terminate]         │
│  • failure ──→ [Auto-terminate]         │
└─────────────────────────────────────────┘
```

### 3. ConvertRecord (v2.2.0)
```
┌─────────────────────────────────────────┐
│        ConvertRecord                    │
├─────────────────────────────────────────┤
│ Entrada:                                │
│  Content: CSV com header                │
│    ID,Projeto,Tipo,...                  │
│    1,Sistema X,Demanda,...              │
│                                         │
│ Configuração:                           │
│  • Record Reader: CSVReader             │
│    - Schema Access: Use String Fields   │
│      From Header                        │
│    - Treat First Line as Header: true   │
│    - Charset: UTF-8                     │
│  • Record Writer: JsonRecordSetWriter   │
│    - Schema Write Strategy: Do Not Write│
│    - Schema Access: Inherit Record      │
│  • Include Zero Record FlowFiles: false │
│                                         │
│ Saída:                                  │
│  Record estruturado:                    │
│    {ID:1, Projeto:"Sistema X",          │
│     Tipo:"Demanda", ...}                │
│                                         │
│ Relationships:                          │
│  • success ──→ (conversão OK)           │
│  • failure ──→ [Auto-terminate]         │
└─────────────────────────────────────────┘
```

### 4. RenameRecordField (v2.2.0)
```
┌─────────────────────────────────────────┐
│        RenameRecordField                │
├─────────────────────────────────────────┤
│ Entrada (Record):                       │
│  {ID:1, Projeto:"X", Tipo:"Demanda",    │
│   Situação:"Aberto", Título:"Login",    │
│   Descrição:"Sistema auth",             │
│   "Últimas notas":"Em dev"}             │
│                                         │
│ Configuração:                           │
│  • Record Reader: CSVReader             │
│  • Record Writer: JsonRecordSetWriter   │
│  • Field Renaming Properties:           │
│    /ID → /id                            │
│    /Projeto → /projeto                  │
│    /Tipo → /tipo                        │
│    /Situação → /situacao                │
│    /Título → /titulo                    │
│    /Descrição → /descricao              │
│    /Últimas notas → /ultimas_notas      │
│                                         │
│ Saída (Record renomeado):               │
│  {id:1, projeto:"X", tipo:"Demanda",    │
│   situacao:"Aberto", titulo:"Login",    │
│   descricao:"Sistema auth",             │
│   ultimas_notas:"Em dev"}               │
│                                         │
│ Relationships:                          │
│  • success ──→ (renomeação OK)          │
│  • failure ──→ [Auto-terminate]         │
└─────────────────────────────────────────┘
```

### 5. PutDatabaseRecord (v2.2.0)
```
┌─────────────────────────────────────────┐
│       PutDatabaseRecord                 │
├─────────────────────────────────────────┤
│ Entrada (Record):                       │
│  {id:1, projeto:"X", tipo:"Demanda",    │
│   situacao:"Aberto", titulo:"Login",    │
│   descricao:"Sistema auth",             │
│   ultimas_notas:"Em dev"}               │
│                                         │
│ Configuração:                           │
│  • Record Reader: JsonRecordSetWriter   │
│  • Statement Type: INSERT               │
│  • Table Name: dados_csv                │
│  • DBCP Service: DBCPConnectionPool     │
│    - URL: jdbc:postgresql://postgres:   │
│      5432/postgres                      │
│    - Driver: org.postgresql.Driver      │
│    - User: postgres                     │
│    - Password: postgres                 │
│  • Translate Field Names: true          │
│  • Unmatched Fields: Ignore             │
│  • Maximum Batch Size: 100              │
│                                         │
│ Processo:                               │
│  1. Lê Record via JsonRecordSetWriter   │
│  2. Mapeia campos para colunas da       │
│     tabela dados_csv                    │
│  3. Gera SQL:                           │
│     INSERT INTO dados_csv               │
│     (id, projeto, tipo, situacao,       │
│      titulo, descricao, ultimas_notas)  │
│     VALUES (1, 'X', 'Demanda',          │
│             'Aberto', 'Login',          │
│             'Sistema auth', 'Em dev')   │
│  4. Executa no PostgreSQL em batch      │
│                                         │
│ Saídas:                                 │
│  • success ─→ (inserção OK)             │
│  • failure ─→ (erro SQL)                │
│  • retry ───→ (tentar novamente)        │
└─────────────────────────────────────────┘
```

---

## Controller Services

```
┌──────────────────────────────────────────────────────────────┐
│                  CONTROLLER SERVICES                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. DBCPConnectionPool                                       │
│     ┌────────────────────────────────────────────┐          │
│     │ • Driver: org.postgresql.Driver            │          │
│     │ • URL: jdbc:postgresql://postgres:5432/    │          │
│     │   postgres                                 │          │
│     │ • User: postgres                           │          │
│     │ • Password: postgres                       │          │
│     │ • Driver Location: /opt/nifi/nifi-current/ │          │
│     │   lib/postgresql-jdbc.jar                  │          │
│     │                                            │          │
│     │ Status: [ENABLED] ⚡                       │          │
│     └────────────────────────────────────────────┘          │
│                                                              │
│  2. CSVReader                                                │
│     ┌────────────────────────────────────────────┐          │
│     │ • Schema Access Strategy: Use String       │          │
│     │   Fields From Header                       │          │
│     │ • CSV Format: Custom Format                │          │
│     │ • Value Separator: , (comma)               │          │
│     │ • Skip Header Line: false                  │          │
│     │ • Treat First Line as Header: true         │          │
│     │ • Quote Character: "                       │          │
│     │ • Escape Character: \                      │          │
│     │ • Trim Fields: true                        │          │
│     │ • Charset Encoding: UTF-8                  │          │
│     │                                            │          │
│     │ Status: [ENABLED] ⚡                       │          │
│     └────────────────────────────────────────────┘          │
│                                                              │
│  3. JsonRecordSetWriter                                      │
│     ┌────────────────────────────────────────────┐          │
│     │ • Schema Write Strategy: Do Not Write      │          │
│     │   Schema                                   │          │
│     │ • Schema Access Strategy: Inherit Record   │          │
│     │   Schema                                   │          │
│     │ • Pretty Print JSON: false                 │          │
│     │                                            │          │
│     │ Status: [ENABLED] ⚡                       │          │
│     └────────────────────────────────────────────┘          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Fluxo de Dados (FlowFile Lifecycle)

```
┌──────────────────────────────────────────────────────────────┐
│            LIFECYCLE DE UM FLOWFILE - CSV ETL                │
└──────────────────────────────────────────────────────────────┘

Estado Inicial: NENHUM FLOWFILE
                    │
                    │ Trigger: Run Schedule (60 sec)
                    │ Verifica SFTP: /download/*.csv
                    ▼
        ┌──────────────────────┐
        │   GetSFTP            │
        │   Baixa CSV do SFTP  │
        └──────┬───────────────┘
               │
               │ FlowFile criado:
               │ Attributes:
               │  - filename: dados.csv
               │  - path: /download
               │  - file.size: 524288
               │  - sftp.remote.host: sftp-caixagis
               │
               │ Content (arquivo CSV completo):
               │  ID,Projeto,Tipo,Situação,Título,...
               │  1,Sistema X,Demanda,Aberto,Login,...
               │  2,Portal Y,Bug,Fechado,Menu,...
               │  ... (1000 linhas)
               │
               ▼
        ┌──────────────────────┐
        │   SplitText          │
        │   1 → N FlowFiles    │
        └──────┬───────────────┘
               │
               ├─→ FlowFile 1 (Split)
               │   Attributes:
               │    - fragment.index: 0
               │    - fragment.count: 10
               │    - text.line.count: 100
               │   Content:
               │    ID,Projeto,Tipo,Situação,...
               │    1,Sistema X,Demanda,Aberto,...
               │    ... (até linha 100)
               │
               ├─→ FlowFile 2 (Split)
               │   Attributes:
               │    - fragment.index: 1
               │   Content:
               │    ID,Projeto,Tipo,Situação,...
               │    101,App Z,Feature,Análise,...
               │    ... (até linha 200)
               │
               └─→ ... (mais FlowFiles)
                   │
                   ▼
        ┌──────────────────────┐
        │  ConvertRecord       │
        │  CSV → Record        │
        └──────┬───────────────┘
               │
               │ FlowFile transformado:
               │ Content: (agora é um Record estruturado)
               │  Record 1: {
               │    ID: 1,
               │    Projeto: "Sistema X",
               │    Tipo: "Demanda",
               │    Situação: "Aberto",
               │    Título: "Login",
               │    Descrição: "Sistema de autenticação",
               │    Últimas notas: "Em desenvolvimento"
               │  }
               │  Record 2: {...}
               │  ... (100 registros)
               │
               ▼
        ┌──────────────────────┐
        │ RenameRecordField    │
        │ Renomeia campos      │
        └──────┬───────────────┘
               │
               │ FlowFile com campos renomeados:
               │ Content: (Record com nomes padronizados)
               │  Record 1: {
               │    id: 1,
               │    projeto: "Sistema X",
               │    tipo: "Demanda",
               │    situacao: "Aberto",
               │    titulo: "Login",
               │    descricao: "Sistema de autenticação",
               │    ultimas_notas: "Em desenvolvimento"
               │  }
               │  Record 2: {...}
               │  ... (100 registros)
               │
               ▼
        ┌──────────────────────┐
        │ PutDatabaseRecord    │
        │ Insere no PostgreSQL │
        └──────┬───────────────┘
               │
               │ SQL Executado (batch):
               │  INSERT INTO dados_csv
               │  (id, projeto, tipo, situacao,
               │   titulo, descricao, ultimas_notas)
               │  VALUES
               │  (1, 'Sistema X', 'Demanda', 'Aberto',
               │   'Login', 'Sistema de autenticação',
               │   'Em desenvolvimento'),
               │  (2, 'Portal Y', 'Bug', 'Fechado',
               │   'Menu', 'Menu lateral quebrado',
               │   'Corrigido'),
               │  ... (100 registros em batch)
               │
               ▼
         [FlowFile removido]
         (success - auto-terminate)

┌──────────────────────────────────────────────────────────────┐
│ OBSERVAÇÃO: Este ciclo se repete para cada split do CSV     │
│ Se o CSV tem 1000 linhas e split é 100, haverá 10 ciclos    │
└──────────────────────────────────────────────────────────────┘
```

---

## Visualização do Canvas do NiFi

```
┌──────────────────────────────────────────────────────────────────┐
│ Apache NiFi - Flow Canvas                                  [x]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │     GetSFTP         │  In: 0 bytes / 0 (0 bytes)              │
│  │   GetSFTP 2.2.0     │  Out: 0 bytes / 0 (0 bytes)             │
│  │                     │  Read/Write: 0 bytes/0 KB               │
│  │   ┌─────────┐       │  Tasks/Time: 0 / 00:00:00.000           │
│  │   │  sftp   │       │                                         │
│  └───┴─────────┴───────┘                                         │
│         │                                                        │
│         │ success (Queue: 0 / 0 bytes)                           │
│         ↓                                                        │
│  ┌─────────────────────┐              ┌──────────────────┐      │
│  │    SplitText        │──original────│  original_splits │      │
│  │  SplitText 2.2.0    │  (112 bytes) │   (Queue: 112)   │      │
│  │                     │              └──────────────────┘      │
│  │   In: 0 / 0 bytes   │                                         │
│  │   Out: 0 / 0 bytes  │                                         │
│  └──────┬──────────────┘                                         │
│         │                                                        │
│         │ splits (Queue: 0 / 0 bytes)                            │
│         ↓                                                        │
│  ┌─────────────────────┐                                         │
│  │   ConvertRecord     │  In: 0 / 0 bytes                        │
│  │ ConvertRecord 2.2.0 │  Out: 0 / 0 bytes                       │
│  │                     │  Tasks/Time: 0 / 00:00:00.000           │
│  └──────┬──────────────┘                                         │
│         │                                                        │
│         │ success (Queue: 0 / 0 bytes)                           │
│         ↓                                                        │
│  ┌─────────────────────┐                                         │
│  │ RenameRecordField   │  In: 0 / 0 bytes                        │
│  │ RenameRecord.. 2.2.0│  Out: 0 / 0 bytes                       │
│  │                     │  Tasks/Time: 0 / 00:00:00.000           │
│  └──────┬──────────────┘                                         │
│         │                                                        │
│         │ success (Queue: 0 / 0 bytes)                           │
│         ↓                                                        │
│  ┌─────────────────────┐                                         │
│  │ PutDatabaseRecord   │  In: 0 / 0 bytes                        │
│  │ PutDatabase... 2.2.0│  Out: 0 / 0 bytes                       │
│  │                     │  Tasks/Time: 0 / 00:00:00.000           │
│  └─────────────────────┘                                         │
│                                                                  │
│  Status: ▶ 5 components running                                  │
│  NiFi Flow: SFTP → CSV → Transform → PostgreSQL                 │
│  Last 5 min: 0 FlowFiles / 0 KB transferred                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Legenda de Ícones e Estados

```
Ícones dos Processors:
  ⚙️  = Processor parado
  ▶  = Processor rodando
  ⏸  = Processor pausado
  ⚠️  = Processor com warning
  ❌ = Processor com erro

Estados da Conexão (Setas):
  ─────→  = Conexão vazia (queue: 0)
  ═════→  = Conexão com dados (queue: > 0)
  ═══⚠═→  = Backpressure atingido
  ─ ─ ─→  = Conexão auto-terminated

Cores dos Processors (na UI real):
  🟢 Verde = Rodando sem problemas
  🔴 Vermelho = Parado
  🟡 Amarelo = Parado com dados na fila
  🟠 Laranja = Rodando com warnings
```

---

## Exemplo de Monitoramento em Tempo Real

```
┌─────────────────────────────────────────────────────────────┐
│              STATISTICS - Last 5 minutes                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  InvokeHTTP                                                 │
│    Tasks: 5      Time: 2.5 sec                              │
│    In: 0         Out: 5                                     │
│    Read: 0 B     Written: 15 KB                             │
│                                                             │
│  SplitJson                                                  │
│    Tasks: 5      Time: 0.1 sec                              │
│    In: 5         Out: 50                                    │
│    Read: 15 KB   Written: 15 KB                             │
│                                                             │
│  EvaluateJsonPath                                           │
│    Tasks: 50     Time: 0.5 sec                              │
│    In: 50        Out: 50                                    │
│    Read: 15 KB   Written: 15 KB                             │
│                                                             │
│  AttributesToJSON                                           │
│    Tasks: 50     Time: 0.3 sec                              │
│    In: 50        Out: 50                                    │
│    Read: 15 KB   Written: 18 KB                             │
│                                                             │
│  PutDatabaseRecord                                          │
│    Tasks: 50     Time: 1.2 sec                              │
│    In: 50        Out: 50                                    │
│    Read: 18 KB   Written: 0 B                               │
│    Records: 50 inserted                                     │
│                                                             │
│  TOTAL                                                      │
│    FlowFiles: 50 processed                                  │
│    Throughput: 18 KB                                        │
│    Avg Latency: 850 ms                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

Este diagrama ajuda a visualizar todo o processo do fluxo ETL no Apache NiFi!
