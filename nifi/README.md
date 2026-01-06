# Apache NiFi com Docker

Mini projeto para executar o Apache NiFi através do Docker de forma simples e rápida.

## O que é Apache NiFi?

Apache NiFi é uma plataforma de integração de dados que permite automatizar o fluxo de dados entre sistemas. Ele oferece uma interface web intuitiva para criar, monitorar e controlar fluxos de dados em tempo real.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado (versão 20.10 ou superior)
- Docker Compose v2/v5 (integrado ao Docker CLI)
- Mínimo de 4GB de RAM disponível para o container

## Estrutura do Projeto

```
nifi-docker/
├── docker-compose.yml         # Configuração do Docker Compose
├── .env                       # Variáveis de ambiente (credenciais)
├── .gitignore                # Arquivos ignorados pelo Git
├── init.sql                  # Script SQL para criar tabela no PostgreSQL
├── README.md                 # Este arquivo
├── TUTORIAL_FLUXO_NIFI.md    # Tutorial completo do fluxo ETL
└── DIAGRAMA_FLUXO.md         # Diagramas visuais do fluxo
```

## Como Usar

### 1. Clonar ou baixar este projeto

```bash
git clone <seu-repositorio>
cd nifi-docker
```

### 2. Configurar credenciais (opcional)

As credenciais padrão estão definidas no arquivo [.env](.env):
- **Usuário**: `admin`
- **Senha**: `adminadminadmin`

Para alterar, edite o arquivo [.env](.env) antes de iniciar o container.

### 3. Iniciar o Apache NiFi

```bash
docker network create nifi_network
```

Este comando irá:
- Criar a rede manualmente

```bash
docker compose up -d
```

Este comando irá:
- Baixar a imagem oficial do Apache NiFi (se necessário)
- Criar os volumes para persistência de dados
- Iniciar o container em background

### 4. Verificar o status

```bash
docker compose ps
```

Aguarde alguns minutos até o NiFi inicializar completamente. Você pode acompanhar os logs:

```bash
docker compose logs -f nifi
```

### 5. Criar a tabela no PostgreSQL

Antes de usar o NiFi, crie a tabela de destino no banco de dados:

```bash
# Acessar o container do PostgreSQL
docker exec -it postgres psql -U postgres -d postgres

# Executar o script init.sql
# Copie e cole o conteúdo de init.sql ou execute:
\i /caminho/para/init.sql

# Ou crie a tabela manualmente:
CREATE TABLE public.dados_csv (
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

# Sair
\q
```

### 6. Acessar a interface web

Após a inicialização (pode levar de 2 a 5 minutos), acesse:

**URL**: https://localhost:8443/nifi/

**Credenciais**:
- Usuário: `admin`
- Senha: `adminadminadmin`

> **Nota**: O navegador irá alertar sobre o certificado SSL auto-assinado. Isso é normal em ambiente de desenvolvimento. Aceite o aviso de segurança para continuar.

## Comandos Úteis

### Parar o NiFi
```bash
docker compose stop
```

### Reiniciar o NiFi
```bash
docker compose restart
```

### Parar e remover o container (mantém os dados)
```bash
docker compose down
```

### Remover tudo, incluindo volumes (CUIDADO: apaga todos os dados)
```bash
docker compose down -v
```

### Ver logs em tempo real
```bash
docker compose logs -f nifi
```

### Acessar o shell do container
```bash
docker exec -it nifi bash
```

## Volumes e Persistência

O projeto utiliza volumes Docker para persistir os dados do NiFi:

- `nifi_conf`: Configurações do NiFi
- `nifi_database_repository`: Banco de dados interno
- `nifi_flowfile_repository`: FlowFiles em processamento
- `nifi_content_repository`: Conteúdo dos FlowFiles
- `nifi_provenance_repository`: Histórico de eventos
- `nifi_state`: Estado dos componentes
- `nifi_logs`: Logs da aplicação

Esses volumes garantem que seus workflows e dados não sejam perdidos ao reiniciar o container.

## Configurações

### Portas

- **8443**: Interface HTTPS do NiFi (porta padrão)

### Recursos

O NiFi pode consumir bastante memória. Se necessário, você pode limitar os recursos adicionando ao serviço `nifi` no [docker-compose.yml](docker-compose.yml) ou usando o arquivo `compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 2G
```

## Solução de Problemas

### Container não inicia

1. Verifique se a porta 8443 não está em uso:
   ```bash
   netstat -tuln | grep 8443
   ```

2. Verifique os logs:
   ```bash
   docker compose logs nifi
   ```

### Não consigo acessar a interface

1. Aguarde alguns minutos para o NiFi inicializar completamente
2. Verifique o health check:
   ```bash
   docker compose ps
   ```
3. Certifique-se de estar usando HTTPS (não HTTP)

### Erro de memória

Aumente a memória disponível para o Docker nas configurações do Docker Desktop ou adicione limites de memória no arquivo de configuração do Compose.

## Segurança

⚠️ **IMPORTANTE**: Este projeto é configurado para ambiente de desenvolvimento/teste.

Para ambiente de produção, você deve:
- Alterar as credenciais padrão
- Usar certificados SSL válidos
- Configurar autenticação adequada
- Revisar as configurações de segurança do NiFi
- Não expor a porta 8443 diretamente na internet

## Fluxo ETL Implementado

Este projeto inclui um fluxo ETL completo que demonstra como:

```
GetSFTP → SplitText → ConvertRecord → RenameRecordField → PutDatabaseRecord
```

### Componentes do Fluxo

1. **GetSFTP (v2.2.0)**: Conecta ao servidor SFTP e baixa arquivos CSV da pasta `/download`
2. **SplitText (v2.2.0)**: Divide o arquivo CSV em blocos de 100 linhas para processamento eficiente
3. **ConvertRecord (v2.2.0)**: Converte o formato CSV para registros estruturados usando CSVReader
4. **RenameRecordField (v2.2.0)**: Renomeia campos do CSV (ex: "ID" → "id", "Situação" → "situacao")
5. **PutDatabaseRecord (v2.2.0)**: Insere os registros no PostgreSQL na tabela `dados_csv`

### Mapeamento de Campos

O fluxo transforma campos do CSV para o formato do banco de dados:

| Campo CSV       | Campo Banco     |
|-----------------|-----------------|
| ID              | id              |
| Projeto         | projeto         |
| Tipo            | tipo            |
| Situação        | situacao        |
| Título          | titulo          |
| Descrição       | descricao       |
| Últimas notas   | ultimas_notas   |

## Próximos Passos

Após ter o NiFi rodando, você pode:

1. **Seguir o tutorial completo**: Consulte o arquivo [TUTORIAL_FLUXO_NIFI.md](TUTORIAL_FLUXO_NIFI.md) para criar o fluxo ETL passo a passo
2. **Visualizar os diagramas**: Veja o [DIAGRAMA_FLUXO.md](DIAGRAMA_FLUXO.md) para entender o fluxo de dados visualmente
3. Criar seu primeiro workflow arrastando processadores na interface
4. Conectar-se a fontes de dados (APIs, bancos de dados, arquivos, etc.)
5. Configurar processadores para transformar e rotear dados
6. Monitorar o fluxo de dados em tempo real

### Tabela de Destino

O projeto está configurado para inserir dados na tabela `dados_csv` com os seguintes campos:
- `projeto` (text): Nome ou identificador do projeto
- `tipo` (text): Tipo do registro
- `situacao` (text): Status ou situação atual
- `titulo` (text): Título ou nome descritivo
- `descricao` (text): Descrição detalhada
- `ultimas_notas` (text): Observações ou notas recentes
- `id` (integer): Identificador único

## Documentação Oficial

- [Apache NiFi Documentation](https://nifi.apache.org/docs.html)
- [NiFi User Guide](https://nifi.apache.org/docs/nifi-docs/html/user-guide.html)
- [Docker Hub - Apache NiFi](https://hub.docker.com/r/apache/nifi)

## Licença

Este projeto usa o Apache NiFi, que é licenciado sob a [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

---

**Desenvolvido para facilitar o uso do Apache NiFi com Docker** 🚀
# poc-nifi-etl
