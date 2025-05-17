# Acertpix API Facematch (Biometria) MCP Server

Servidor MCP para integração com a API Facematch (Biometria) da Acertpix.

## Tabela de Conteúdo

1.  [Funcionalidades](#funcionalidades)
2.  [Requisitos](#requisitos)
3.  [Instalação](#instalação)
4.  [Uso](#uso)
5.  [Exemplo de Uso](#exemplo-de-uso)
6.  [Configuração](#configuração)
7.  [Informações da API](#informações-da-api)
8.  [Licença](#licença)

## Funcionalidades

-   **Consulta de facematch por chave:** Permite consultar o facematch das fotos de uma pessoa física.

## Requisitos

- Python 3.8+
- Dependências listadas no `pyproject.toml`

## Instalação

1.  Clone este repositório:

    ```bash
    git clone <repository_url>
    cd acertpix-api-facematch
    ```

2.  Instale os pacotes:

    ```bash
    pip install -e .
    ```

3. Para usar Docker, build a imagem

    ```bash
    docker build -t acertpix-api-facematch .
    ```

4. Precisa informar as variáveis de ambiente:

    ```bash
    ACERTPIX_API_URL=https://devapi.plataformaacertpix.com.br (ou para produção: https://api.plataformaacertpix.com.br)
    ACERTPIX_CLIENT_ID=clientId credenciais de acesso da API
    ACERTPIX_CLIENT_SECRET=clientSecret credenciais de acesso da API
    ACERTPIX_API_SSL_VERIFY=false (depende se for ambiente de teste)
    ```

Obs: também pode utilizar .env ou direto no "run" do docker

## Exemplo de Uso 

### MCP no VSCode 

Arquivo de configuração mcp.json, configuração para acesso por docker ou direto no código.

```json
{
    "servers": {
        "acertpix-api-facematch-docker": {
            "type": "stdio",
            "command": "docker",
            "args": ["run", "-i", 
            "-e","MCP_API_KEY=bff37c482a6d42b7b4a1f6045dff6d63",
            "-e","ACERTPIX_API_URL=https://devapi.plataformaacertpix.com.br",
            "-e","ACERTPIX_CLIENT_ID=xxxxxx",
            "-e","ACERTPIX_CLIENT_SECRET=yyyyyyy",
            "-e","ACERTPIX_API_SSL_VERIFY=false",
            "--rm", 
            "-p", "8000:8000", "acertpix-api-facematch"]
        },
        "acertpix-api-facematch-src": {
            "command": "python",
            "args": [
                "-m",
                "acertpix_api_facematch"
            ]
        },        
    }
}
```

### Em Python

```python
# Exemplo de chamada à ferramenta (para referência)
resultado = await server.call_tool("consultar-facematch", {
    "chave": "12345678900"
})
```

## Configuração

O servidor se conecta à API da Acertpix. 
Para configurar a autenticação OAuth2, defina as seguintes variáveis de ambiente:

-   `ACERTPIX_API_URL`: Url da API do Ambiente
-   `ACERTPIX_CLIENT_ID`: Client ID da API Acertpix.
-   `ACERTPIX_CLIENT_SECRET`: Client Secret da API Acertpix.
-   `ACERTPIX_API_SSL_VERIFY`: Verificação de SSL

## Informações da API
https://docs.acertpix.com.br/ 

## Licença

Proprietário - Acertpix
