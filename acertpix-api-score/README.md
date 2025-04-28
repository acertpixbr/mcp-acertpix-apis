# Acertpix API Score MCP Server

Servidor MCP para integração com a API Score da Acertpix.

## Funcionalidades

- Consulta de score por CPF
- Autenticação OAuth2 com client_id e client_secret

## Requisitos

- Python 3.8+
- Dependências listadas no `pyproject.toml`

## Instalação

```bash
pip install -e .
```

## Uso

O servidor MCP expõe uma ferramenta chamada `consultar-score` que pode ser usada para consultar o score de um CPF.

Parâmetros necessários:
- `cpf`: CPF a ser consultado
- `client_id`: Client ID da API
- `client_secret`: Client Secret da API

## Exemplo de Uso

```python
# Exemplo de chamada à ferramenta
resultado = await server.call_tool("consultar-score", {
    "cpf": "12345678900",
    "client_id": "seu_client_id",
    "client_secret": "seu_client_secret"
})
```

## Configuração

O servidor se conecta à API da Acertpix em `https://api.plataformaacertpix.com.br`.

## Licença

Proprietário - Acertpix