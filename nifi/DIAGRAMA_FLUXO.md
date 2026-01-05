# Diagrama Visual do Fluxo NiFi

## Fluxo Simplificado (Quick Start)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FLUXO COMPLETO                              │
└─────────────────────────────────────────────────────────────────────┘

API Externa                                              Banco SQLite
     │                                                         ▲
     │ GET Request                                             │
     ▼                                                         │
┌──────────────┐                                              │
│              │                                              │
│ InvokeHTTP   │  Faz requisição GET para API                 │
│              │  https://api.exemplo.com/users               │
└──────┬───────┘                                              │
       │                                                       │
       │ Response (JSON Array)                                │
       │ [{"id":1, "name":"João"}, ...]                       │
       ▼                                                       │
┌──────────────┐                                              │
│              │                                              │
│  SplitJson   │  Divide array em FlowFiles individuais       │
│              │  Cada objeto JSON vira um FlowFile           │
└──────┬───────┘                                              │
       │                                                       │
       │ split (múltiplos FlowFiles)                          │
       │ FlowFile 1: {"id":1, "name":"João"}                  │
       │ FlowFile 2: {"id":2, "name":"Maria"}                 │
       ▼                                                       │
┌─────────────────────┐                                       │
│                     │                                       │
│ EvaluateJsonPath    │  Extrai campos do JSON               │
│                     │  e cria atributos:                    │
│  $.id → user.id     │  - user.id = 1                        │
│  $.name → user.name │  - user.name = João                   │
│  $.email → ...      │  - user.email = joao@...              │
│                     │                                       │
└──────┬──────────────┘                                       │
       │                                                       │
       │ matched (FlowFile com atributos)                     │
       ▼                                                       │
┌──────────────────────┐                                      │
│                      │                                      │
│ AttributesToJSON     │  Converte atributos de volta         │
│                      │  para JSON no conteúdo:              │
│                      │  Content: {"user.id":1, ...}         │
│                      │                                      │
└──────┬───────────────┘                                      │
       │                                                       │
       │ success (JSON válido)                                │
       ▼                                                       │
┌──────────────────────┐                                      │
│                      │                                      │
│ PutDatabaseRecord    │  Lê JSON e insere no banco          │
│                      │  INSERT INTO users ...              │
│ Reader: JsonTreeRead │                                      │
│ Table: users         │                                      │
│                      │─────────────────────────────────────┘
│                      │
└──────────────────────┘
       │
       │ success
       ▼
   [Terminate]
```

---

## Fluxo com Tratamento de Erros

```
                                API Externa
                                     │
                                     │ GET
                                     ▼
                            ┌──────────────┐
                            │              │
                            │ InvokeHTTP   │
                            │              │
                            └──────┬───────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
               Response        Failure        No Retry
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────┐    ┌────────────┐  [Terminate]
            │          │    │            │
            │SplitJson │    │LogAttribute│
            │          │    │  (Error)   │
            └────┬─────┘    └──────┬─────┘
                 │                 │
        ┌────────┼────────┐        │
        │        │        │        ▼
     split   original  failure  ┌─────────┐
        │        │        │      │ PutFile │
        ▼        ▼        ▼      │ (Erros) │
   ┌─────────┐  [Term]  [Term]   └─────────┘
   │Evaluate │
   │JsonPath │
   └────┬────┘
        │
    ┌───┼────┐
    │   │    │
matched │ unmatched
    │   │    │
    ▼   ▼    ▼
  ┌────────────┐  ┌────────────┐
  │Attributes  │  │LogAttribute│
  │  ToJSON    │  │(Unmatched) │
  └─────┬──────┘  └────────────┘
        │
    ┌───┼────┐
    │   │    │
success │ failure
    │   │    │
    ▼   ▼    ▼
  ┌──────────────┐  ┌─────────┐
  │PutDatabase   │  │ PutFile │
  │   Record     │  │(Failures)│
  └──────┬───────┘  └─────────┘
         │
     ┌───┼────┐
     │   │    │
 success │  retry
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

### 1. InvokeHTTP
```
┌─────────────────────────────────────────┐
│          InvokeHTTP                     │
├─────────────────────────────────────────┤
│ Configuração:                           │
│  • HTTP Method: GET                     │
│  • Remote URL: https://api.com/users    │
│  • Connection Timeout: 30 sec           │
│  • Read Timeout: 30 sec                 │
│                                         │
│ Scheduling:                             │
│  • Run Schedule: 60 sec                 │
│  • Concurrent Tasks: 1                  │
│                                         │
│ Saídas:                                 │
│  • Response ─────→ (FlowFile com JSON)  │
│  • Failure ──────→ [Auto-terminate]     │
│  • Retry ────────→ [Auto-terminate]     │
│  • No Retry ─────→ [Auto-terminate]     │
└─────────────────────────────────────────┘
```

### 2. SplitJson
```
┌─────────────────────────────────────────┐
│           SplitJson                     │
├─────────────────────────────────────────┤
│ Entrada:                                │
│  Content: [                             │
│    {"id":1, "name":"João"},             │
│    {"id":2, "name":"Maria"}             │
│  ]                                      │
│                                         │
│ Configuração:                           │
│  • JsonPath: $                          │
│                                         │
│ Saídas:                                 │
│  • split ────→ FlowFile 1: {"id":1...}  │
│           └──→ FlowFile 2: {"id":2...}  │
│  • original ─→ [Auto-terminate]         │
│  • failure ──→ [Auto-terminate]         │
└─────────────────────────────────────────┘
```

### 3. EvaluateJsonPath
```
┌─────────────────────────────────────────┐
│        EvaluateJsonPath                 │
├─────────────────────────────────────────┤
│ Entrada:                                │
│  Content: {"id":1, "name":"João"}       │
│                                         │
│ Extração (Properties):                  │
│  user.id     ← $.id                     │
│  user.name   ← $.name                   │
│  user.email  ← $.email                  │
│  user.phone  ← $.phone                  │
│  user.website← $.website                │
│                                         │
│ Saída:                                  │
│  Attributes:                            │
│    user.id = "1"                        │
│    user.name = "João"                   │
│    user.email = "joao@exemplo.com"      │
│    ...                                  │
│                                         │
│ Relationships:                          │
│  • matched ──→ (tem todos os campos)    │
│  • unmatched → (faltam campos)          │
│  • failure ──→ (erro no parse)          │
└─────────────────────────────────────────┘
```

### 4. AttributesToJSON
```
┌─────────────────────────────────────────┐
│        AttributesToJSON                 │
├─────────────────────────────────────────┤
│ Entrada (Attributes):                   │
│  user.id = "1"                          │
│  user.name = "João"                     │
│  user.email = "joao@exemplo.com"        │
│                                         │
│ Configuração:                           │
│  • Attributes List:                     │
│    user.id,user.name,user.email,...     │
│  • Destination: flowfile-content        │
│  • Include Core Attributes: false       │
│                                         │
│ Saída (Content):                        │
│  {                                      │
│    "user.id": "1",                      │
│    "user.name": "João",                 │
│    "user.email": "joao@exemplo.com"     │
│  }                                      │
└─────────────────────────────────────────┘
```

### 5. PutDatabaseRecord
```
┌─────────────────────────────────────────┐
│       PutDatabaseRecord                 │
├─────────────────────────────────────────┤
│ Entrada (Content):                      │
│  {"user.id":"1", "user.name":"João"}    │
│                                         │
│ Configuração:                           │
│  • Record Reader: JsonTreeReader        │
│  • Statement Type: INSERT               │
│  • Table Name: users                    │
│  • DBCP Service: DBCPConnectionPool     │
│  • Translate Field Names: true          │
│  • Unmatched Fields: Ignore             │
│                                         │
│ Processo:                               │
│  1. Lê JSON via JsonTreeReader          │
│  2. Mapeia campos para colunas:         │
│     user.id → id                        │
│     user.name → name                    │
│  3. Gera SQL:                           │
│     INSERT INTO users                   │
│     (id, name, email, phone, website)   │
│     VALUES (1, 'João', ...)             │
│  4. Executa no SQLite                   │
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
┌──────────────────────────────────────────────────────────┐
│              CONTROLLER SERVICES                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. DBCPConnectionPool                                   │
│     ┌──────────────────────────────────────┐            │
│     │ • Driver: org.sqlite.JDBC            │            │
│     │ • URL: jdbc:sqlite:/tmp/database.db  │            │
│     │ • Driver Jar: .../sqlite-jdbc.jar    │            │
│     │                                      │            │
│     │ Status: [ENABLED] ⚡                 │            │
│     └──────────────────────────────────────┘            │
│                                                          │
│  2. JsonTreeReader                                       │
│     ┌──────────────────────────────────────┐            │
│     │ • Schema Access: Infer Schema        │            │
│     │ • Starting Field Strategy: Root Node │            │
│     │                                      │            │
│     │ Status: [ENABLED] ⚡                 │            │
│     └──────────────────────────────────────┘            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Fluxo de Dados (FlowFile Lifecycle)

```
┌──────────────────────────────────────────────────────────────┐
│                    LIFECYCLE DE UM FLOWFILE                  │
└──────────────────────────────────────────────────────────────┘

Estado Inicial: NENHUM FLOWFILE
                    │
                    │ Trigger: Run Schedule (60 sec)
                    ▼
        ┌──────────────────────┐
        │   InvokeHTTP         │
        │   Cria FlowFile      │
        └──────┬───────────────┘
               │
               │ Attributes:
               │  - filename: random-uuid
               │  - invokehttp.status.code: 200
               │  - mime.type: application/json
               │
               │ Content:
               │  [{"id":1,...}, {"id":2,...}, ...]
               │
               ▼
        ┌──────────────────────┐
        │   SplitJson          │
        │   1 → N FlowFiles    │
        └──────┬───────────────┘
               │
               ├─→ FlowFile 1
               │   Attributes:
               │    - fragment.index: 0
               │    - fragment.count: 10
               │   Content:
               │    {"id":1, "name":"João", ...}
               │
               ├─→ FlowFile 2
               │   Attributes:
               │    - fragment.index: 1
               │   Content:
               │    {"id":2, "name":"Maria", ...}
               │
               └─→ ... (mais FlowFiles)
                   │
                   ▼
        ┌──────────────────────┐
        │  EvaluateJsonPath    │
        │  Adiciona Attributes │
        └──────┬───────────────┘
               │
               │ Attributes ADICIONADOS:
               │  - user.id: "1"
               │  - user.name: "João"
               │  - user.email: "joao@exemplo.com"
               │  - user.phone: "123-456"
               │  - user.website: "site.com"
               │
               │ Content: (mantém o mesmo)
               │  {"id":1, "name":"João", ...}
               │
               ▼
        ┌──────────────────────┐
        │ AttributesToJSON     │
        │ Reescreve Content    │
        └──────┬───────────────┘
               │
               │ Attributes: (mantém)
               │  - user.id: "1"
               │  - user.name: "João"
               │  ...
               │
               │ Content: (NOVO)
               │  {
               │    "user.id": "1",
               │    "user.name": "João",
               │    "user.email": "joao@exemplo.com",
               │    "user.phone": "123-456",
               │    "user.website": "site.com"
               │  }
               │
               ▼
        ┌──────────────────────┐
        │ PutDatabaseRecord    │
        │ Insere no Banco      │
        └──────┬───────────────┘
               │
               │ SQL Executado:
               │  INSERT INTO users
               │  (id, name, email, phone, website, imported_at)
               │  VALUES
               │  (1, 'João', 'joao@exemplo.com', '123-456',
               │   'site.com', '2025-12-29 15:30:00')
               │
               ▼
         [FlowFile removido]
         (auto-terminate success)
```

---

## Visualização do Canvas do NiFi

```
┌─────────────────────────────────────────────────────────────┐
│ Apache NiFi Canvas                                    [x]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────┐                                             │
│  │ InvokeHTTP │ ◄─── In: 0 / Out: 10                        │
│  └──────┬─────┘                                             │
│         │                                                   │
│         │ (Response) Queue: 0                               │
│         ↓                                                   │
│  ┌────────────┐                                             │
│  │ SplitJson  │ ◄─── In: 10 / Out: 100                      │
│  └──────┬─────┘                                             │
│         │                                                   │
│         │ (split) Queue: 0                                  │
│         ↓                                                   │
│  ┌────────────────┐                                         │
│  │EvaluateJsonPath│ ◄─── In: 100 / Out: 100                 │
│  └──────┬─────────┘                                         │
│         │                                                   │
│         │ (matched) Queue: 0                                │
│         ↓                                                   │
│  ┌─────────────────┐                                        │
│  │AttributesToJSON │ ◄─── In: 100 / Out: 100                │
│  └──────┬──────────┘                                        │
│         │                                                   │
│         │ (success) Queue: 0                                │
│         ↓                                                   │
│  ┌──────────────────┐                                       │
│  │PutDatabaseRecord │ ◄─── In: 100 / Out: 100               │
│  └──────────────────┘                                       │
│                                                             │
│  Status: All components running ▶                           │
│  Last 5 min: 100 FlowFiles / 45 KB transferred              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
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
