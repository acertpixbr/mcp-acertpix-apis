import asyncio
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, AnyUrl
import requests

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Configurações da API
API_BASE_URL = "https://testapi.plataformaacertpix.com.br"
TOKEN_ENDPOINT = "/OAuth2/Token"
SCORE_ENDPOINT = "/Score/Consultar"

class AuthCredentials(BaseModel):
    client_id: str = Field(..., description="Client ID da API")
    client_secret: str = Field(..., description="Client Secret da API")

class ScoreRequest(BaseModel):
    chave: str = Field(..., description="Chave para consulta de score")
    credentials: AuthCredentials = Field(..., description="Credenciais de autenticação")

server = Server("acertpix-api-score")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lista as ferramentas disponíveis para interação com a API Score.
    """
    return [
        types.Tool(
            name="consultar-score",
            description="Consulta o score de uma chave na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                    "client_id": {"type": "string"},
                    "client_secret": {"type": "string"}
                },
                "required": ["chave", "client_id", "client_secret"]
            },
        ),
        types.Tool(
            name="gerar-token",
            description="Gera um token de acesso na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_id": {"type": "string"},
                    "client_secret": {"type": "string"}
                },
                "required": ["client_id", "client_secret"]
            },
        )
    ]

async def get_access_token(client_id: str, client_secret: str) -> str:
    """
    Obtém o token de acesso da API.
    """
    url = f"{API_BASE_URL}{TOKEN_ENDPOINT}"
    
    payload = json.dumps({
        "Scope": "api",
        "GrantType": "client_credentials",
        "ClientId": client_id,
        "ClientSecret": client_secret
    })
    
    print(f"URL: {url}")
    print(f"Payload: {payload}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Headers: {headers}")
    
    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    
    print(f"Response status: {response.status_code}")
    print(f"Response text: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Erro na requisição Token: {response.status_code} - {response.text} - {url}")
    
    token = response.json()["access_token"]
    print(f"\nToken gerado com sucesso: {token}\n")
    return token

async def consultar_score(chave: str, client_id: str, client_secret: str) -> Dict[str, Any]:
    """
    Consulta o score de uma chave na API.
    """
    access_token = await get_access_token(client_id, client_secret)
    print(f"\nToken gerado: {access_token}\n")
    
    url = f"{API_BASE_URL}{SCORE_ENDPOINT}?chave={chave}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    
    payload = {}
    
    response = requests.request("GET", url, headers=headers, data=payload, verify=False)
    
    print(f"Score response status: {response.status_code}")
    print(f"Score response text: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Erro na requisição Consula: {response.status_code} - {response.text} - {url}")
    
    return response.json()

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Manipula as chamadas às ferramentas disponíveis.
    """
    if not arguments:
        raise ValueError("Argumentos ausentes")

    if name == "gerar-token":
        client_id = arguments.get("client_id")
        client_secret = arguments.get("client_secret")

        if not all([client_id, client_secret]):
            raise ValueError("client_id e client_secret são obrigatórios")

        try:
            token = await get_access_token(client_id, client_secret)
            return [
                types.TextContent(
                    type="text",
                    text=f"Token gerado com sucesso:\n{token}"
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Erro ao gerar token: {str(e)}\nURL: {API_BASE_URL}"
                )
            ]
    
    elif name == "consultar-score":
        chave = arguments.get("chave")
        client_id = arguments.get("client_id")
        client_secret = arguments.get("client_secret")

        if not all([chave, client_id, client_secret]):
            raise ValueError("Chave, client_id e client_secret são obrigatórios")

        try:
            resultado = await consultar_score(chave, client_id, client_secret)
            return [
                types.TextContent(
                    type="text",
                    text=f"Resultado da consulta de score para chave {chave}:\n{resultado}"
                )
            ]
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Erro ao consultar score: {str(e)}\nURL: {API_BASE_URL}"
                )
            ]
    else:
        raise ValueError(f"Ferramenta desconhecida: {name}")

async def main():
    """
    Inicia o servidor MCP.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="acertpix-api-score",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())