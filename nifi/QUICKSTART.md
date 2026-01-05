# Quick Start - API para SQLite em 10 minutos

Este guia rápido mostra como criar um fluxo funcional em poucos minutos usando uma API pública.

---

## Passo 1: Preparar o SQLite (2 minutos)

```bash
# Acessar o container do NiFi
docker exec -it nifi bash

# Instalar o driver SQLite
cd /opt/nifi/nifi-current/lib
curl -O https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/3.44.1.0/sqlite-jdbc-3.44.1.0.jar

# Criar o banco e tabela
sqlite3 /tmp/nifi_database.db << 'EOF'
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    website TEXT,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
.quit
EOF

# Sair do container
exit

# Reiniciar o NiFi para carregar o driver
docker-compose restart nifi
```

Aguarde cerca de 2 minutos para o NiFi reiniciar.

---

## Passo 2: Acessar o NiFi (1 minuto)

1. Acesse: https://localhost:8443/nifi/
2. Login:
   - Usuário: `admin`
   - Senha: `adminadminadmin`
3. Aceite o aviso do certificado SSL

---

## Passo 3: Configurar Controller Services (3 minutos)

### 3.1 DBCPConnectionPool

1. Menu hambúrguer (canto superior direito) → **Controller Settings**
2. Aba **CONTROLLER SERVICES**
3. Clique em **+** (adicionar)
4. Busque: `DBCPConnectionPool`
5. Clique em **ADD**
6. Clique no ícone de **engrenagem** (configurações)
7. Aba **PROPERTIES**:
   - **Database Connection URL**: `jdbc:sqlite:/tmp/nifi_database.db`
   - **Database Driver Class Name**: `org.sqlite.JDBC`
   - **Database Driver Location(s)**: `/opt/nifi/nifi-current/lib/sqlite-jdbc-3.44.1.0.jar`
8. **APPLY**
9. Clique no ícone de **raio** (enable) → **ENABLE**

### 3.2 JsonTreeReader

1. Ainda em **CONTROLLER SERVICES**, clique em **+**
2. Busque: `JsonTreeReader`
3. **ADD**
4. Clique no ícone de **raio** → **ENABLE**

Feche a janela de Controller Settings.

---

## Passo 4: Criar o Fluxo (4 minutos)

### 4.1 InvokeHTTP

1. Arraste um **Processor** para o canvas
2. Busque: `InvokeHTTP`
3. **ADD**
4. Clique duas vezes no processor
5. Aba **PROPERTIES**:
   - **HTTP Method**: `GET`
   - **Remote URL**: `https://jsonplaceholder.typicode.com/users`
6. Aba **SCHEDULING**:
   - **Run Schedule**: `60 sec`
7. Aba **SETTINGS**:
   - Marque **Automatically Terminate Relationships**:
     - ✓ Retry
     - ✓ No Retry
     - ✓ Failure
8. **APPLY**

### 4.2 SplitJson

1. Arraste outro **Processor**
2. Busque: `SplitJson`
3. **ADD**
4. Clique duas vezes
5. Aba **PROPERTIES**:
   - **JsonPath Expression**: `$`
6. Aba **SETTINGS**:
   - Marque **Automatically Terminate Relationships**:
     - ✓ failure
     - ✓ original
7. **APPLY**

### 4.3 EvaluateJsonPath

1. Arraste um **Processor**
2. Busque: `EvaluateJsonPath`
3. **ADD**
4. Clique duas vezes
5. Aba **PROPERTIES**:
   - **Destination**: `flowfile-attribute`

6. Adicione propriedades customizadas (clique no **+**):
   - **Nome**: `user.id` → **Valor**: `$.id`
   - **Nome**: `user.name` → **Valor**: `$.name`
   - **Nome**: `user.email` → **Valor**: `$.email`
   - **Nome**: `user.phone` → **Valor**: `$.phone`
   - **Nome**: `user.website` → **Valor**: `$.website`

7. Aba **SETTINGS**:
   - Marque:
     - ✓ failure
     - ✓ unmatched
8. **APPLY**

### 4.4 AttributesToJSON

1. Arraste um **Processor**
2. Busque: `AttributesToJSON`
3. **ADD**
4. Clique duas vezes
5. Aba **PROPERTIES**:
   - **Attributes List**: `user.id,user.name,user.email,user.phone,user.website`
   - **Destination**: `flowfile-content`
   - **Include Core Attributes**: `false`
6. Aba **SETTINGS**:
   - Marque:
     - ✓ failure
7. **APPLY**

### 4.5 PutDatabaseRecord

1. Arraste um **Processor**
2. Busque: `PutDatabaseRecord`
3. **ADD**
4. Clique duas vezes
5. Aba **PROPERTIES**:
   - **Record Reader**: Selecione `JsonTreeReader`
   - **Statement Type**: `INSERT`
   - **Database Connection Pooling Service**: Selecione `DBCPConnectionPool`
   - **Table Name**: `users`
   - **Translate Field Names**: `true`
   - **Field Containing SQL**: (deixe vazio)
   - **Unmatched Field Behavior**: `Ignore Unmatched Fields`
   - **Unmatched Column Behavior**: `Ignore Unmatched Columns`
   - **Update Keys**: (deixe vazio)
6. Aba **SETTINGS**:
   - Marque:
     - ✓ failure
     - ✓ retry
7. **APPLY**

### 4.6 Conectar os Processors

1. **InvokeHTTP** → **SplitJson**
   - Passe o mouse sobre InvokeHTTP
   - Arraste a seta até SplitJson
   - Selecione: **Response**
   - **ADD**

2. **SplitJson** → **EvaluateJsonPath**
   - Arraste de SplitJson para EvaluateJsonPath
   - Selecione: **split**
   - **ADD**

3. **EvaluateJsonPath** → **AttributesToJSON**
   - Arraste de EvaluateJsonPath para AttributesToJSON
   - Selecione: **matched**
   - **ADD**

4. **AttributesToJSON** → **PutDatabaseRecord**
   - Arraste de AttributesToJSON para PutDatabaseRecord
   - Selecione: **success**
   - **ADD**

5. **PutDatabaseRecord** → **Auto-terminate success**
   - Clique duas vezes em PutDatabaseRecord
   - Aba **SETTINGS**
   - Marque também:
     - ✓ success
   - **APPLY**

---

## Passo 5: Executar o Fluxo (1 minuto)

1. Selecione todos os processors:
   - Pressione `Ctrl+A` ou arraste o mouse sobre todos

2. Clique no botão **Play** (▶) na barra de operações no topo

3. Aguarde alguns segundos e você verá números nas conexões mostrando FlowFiles sendo processados

---

## Passo 6: Verificar os Dados

```bash
# Acessar o container
docker exec -it nifi bash

# Consultar os dados
sqlite3 /tmp/nifi_database.db "SELECT * FROM users;"

# Ou de forma formatada
sqlite3 /tmp/nifi_database.db << 'EOF'
.headers on
.mode column
SELECT id, name, email FROM users LIMIT 5;
EOF

# Sair
exit
```

Você deverá ver 10 usuários importados da API JSONPlaceholder!

---

## Resultado Esperado

```
id  name              email
--  ----------------  ---------------------------
1   Leanne Graham     Sincere@april.biz
2   Ervin Howell      Shanna@melissa.tv
3   Clementine Bauch  Nathan@yesenia.net
4   Patricia Lebsack  Julianne.OConner@kory.org
5   Chelsey Dietrich  Lucio_Hettinger@annie.ca
...
```

---

## Troubleshooting Rápido

### Erro: "Cannot load driver"
```bash
# Verifique se o JAR existe
docker exec nifi ls -lh /opt/nifi/nifi-current/lib/sqlite*

# Se não existir, baixe novamente
docker exec nifi bash -c "cd /opt/nifi/nifi-current/lib && curl -O https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/3.44.1.0/sqlite-jdbc-3.44.1.0.jar"

# Reinicie
docker-compose restart nifi
```

### Erro: "Table doesn't exist"
```bash
# Recriar a tabela
docker exec nifi sqlite3 /tmp/nifi_database.db "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT, website TEXT, imported_at DATETIME DEFAULT CURRENT_TIMESTAMP);"
```

### FlowFiles não fluem
1. Verifique se todos os processors estão rodando (ícone de play verde)
2. Clique com botão direito em cada processor → **View Configuration** → **Settings** → **Bulletin Level**: DEBUG
3. Veja se há erros nos bulletins (ícone de sino no canto superior direito)

### Ver o conteúdo do FlowFile
1. Pare o fluxo (selecione todos e clique em Stop)
2. Clique com botão direito em uma conexão
3. **List queue**
4. Clique no ícone de olho para ver o conteúdo

---

## Próximos Passos

Agora que você tem um fluxo básico funcionando:

1. ✅ Leia o **TUTORIAL_FLUXO_NIFI.md** para entender detalhes
2. ✅ Veja **EXEMPLOS_PRATICOS.md** para mais casos de uso
3. ✅ Substitua a URL da API pela sua API real
4. ✅ Ajuste a tabela SQLite conforme seus dados
5. ✅ Adicione tratamento de erros e validações

---

## Comando para Limpar e Recomeçar

```bash
# Limpar os dados do banco
docker exec nifi sqlite3 /tmp/nifi_database.db "DELETE FROM users;"

# No NiFi, pare o fluxo
# Clique com botão direito nas conexões → Empty queue
# Inicie novamente
```

---

## Salvar como Template

1. Selecione todos os processors (Ctrl+A)
2. Menu hambúrguer → **Create Template**
3. Nome: `API_to_SQLite_QuickStart`
4. **CREATE**

Pronto! Você pode reusar esse template em outros projetos.

---

**Parabéns! Você criou seu primeiro fluxo ETL no Apache NiFi!** 🎉
