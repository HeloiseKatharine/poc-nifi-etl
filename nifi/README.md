# Apache NiFi com Docker

Mini projeto para executar o Apache NiFi através do Docker de forma simples e rápida.

## O que é Apache NiFi?

Apache NiFi é uma plataforma de integração de dados que permite automatizar o fluxo de dados entre sistemas. Ele oferece uma interface web intuitiva para criar, monitorar e controlar fluxos de dados em tempo real.

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado (versão 20.10 ou superior)
- [Docker Compose](https://docs.docker.com/compose/install/) instalado (versão 1.29 ou superior)
- Mínimo de 4GB de RAM disponível para o container

## Estrutura do Projeto

```
nifi-docker/
├── docker-compose.yml    # Configuração do Docker Compose
├── .env                  # Variáveis de ambiente (credenciais)
├── .gitignore           # Arquivos ignorados pelo Git
└── README.md            # Este arquivo
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
docker-compose up -d
```

Este comando irá:
- Baixar a imagem oficial do Apache NiFi (se necessário)
- Criar os volumes para persistência de dados
- Iniciar o container em background

### 4. Verificar o status

```bash
docker-compose ps
```

Aguarde alguns minutos até o NiFi inicializar completamente. Você pode acompanhar os logs:

```bash
docker-compose logs -f nifi
```

### 5. Acessar a interface web

Após a inicialização (pode levar de 2 a 5 minutos), acesse:

**URL**: https://localhost:8443/nifi/

**Credenciais**:
- Usuário: `admin`
- Senha: `adminadminadmin`

> **Nota**: O navegador irá alertar sobre o certificado SSL auto-assinado. Isso é normal em ambiente de desenvolvimento. Aceite o aviso de segurança para continuar.

## Comandos Úteis

### Parar o NiFi
```bash
docker-compose stop
```

### Reiniciar o NiFi
```bash
docker-compose restart
```

### Parar e remover o container (mantém os dados)
```bash
docker-compose down
```

### Remover tudo, incluindo volumes (CUIDADO: apaga todos os dados)
```bash
docker-compose down -v
```

### Ver logs em tempo real
```bash
docker-compose logs -f nifi
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

O NiFi pode consumir bastante memória. Se necessário, você pode limitar os recursos adicionando ao serviço `nifi` no [docker-compose.yml](docker-compose.yml):

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
   docker-compose logs nifi
   ```

### Não consigo acessar a interface

1. Aguarde alguns minutos para o NiFi inicializar completamente
2. Verifique o health check:
   ```bash
   docker-compose ps
   ```
3. Certifique-se de estar usando HTTPS (não HTTP)

### Erro de memória

Aumente a memória disponível para o Docker nas configurações do Docker Desktop ou adicione limites de memória no docker-compose.yml.

## Segurança

⚠️ **IMPORTANTE**: Este projeto é configurado para ambiente de desenvolvimento/teste.

Para ambiente de produção, você deve:
- Alterar as credenciais padrão
- Usar certificados SSL válidos
- Configurar autenticação adequada
- Revisar as configurações de segurança do NiFi
- Não expor a porta 8443 diretamente na internet

## Próximos Passos

Após ter o NiFi rodando, você pode:

1. Criar seu primeiro workflow arrastando processadores na interface
2. Explorar os templates disponíveis
3. Conectar-se a fontes de dados (APIs, bancos de dados, arquivos, etc.)
4. Configurar processadores para transformar e rotear dados
5. Monitorar o fluxo de dados em tempo real

## Documentação Oficial

- [Apache NiFi Documentation](https://nifi.apache.org/docs.html)
- [NiFi User Guide](https://nifi.apache.org/docs/nifi-docs/html/user-guide.html)
- [Docker Hub - Apache NiFi](https://hub.docker.com/r/apache/nifi)

## Licença

Este projeto usa o Apache NiFi, que é licenciado sob a [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

---

**Desenvolvido para facilitar o uso do Apache NiFi com Docker** 🚀
# poc-nifi-etl
