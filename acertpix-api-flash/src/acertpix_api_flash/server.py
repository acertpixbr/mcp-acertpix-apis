import asyncio
import base64
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, AnyUrl
import httpx

import os
from dotenv import load_dotenv

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Carrega variáveis de ambiente de um arquivo .env (opcional)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

# Configurações da API
API_BASE_URL = os.getenv("ACERTPIX_API_URL", "https://devapi.plataformaacertpix.com.br")
CLIENT_ID = os.getenv("ACERTPIX_CLIENT_ID", "acertpix-api")
CLIENT_SECRET = os.getenv("ACERTPIX_CLIENT_SECRET", "acertpix-api")
SSL_VERIFY = os.getenv("ACERTPIX_API_SSL_VERIFY", "true").lower() != "true"

print(f"INFO:     Iniciando API Flash Acertpix")
print(f"INFO:     API Base URL: {API_BASE_URL}")
print(f"INFO:     Client ID: {CLIENT_ID}")
print(f"INFO:     Client Secret: {CLIENT_SECRET}")
print(f"INFO:     SSL Verify: {SSL_VERIFY}")

TOKEN_ENDPOINT = "/OAuth2/Token"
FLASH_ENDPOINT = "/Flash/V2"

server = Server("acertpix-api-flash")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lista as ferramentas disponíveis para interação com a API de Facematch.
    """
    return [
        types.Tool(
            name="consultar-flash",
            description="Consulta resultado Flash de uma chave na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                },
                "required": ["chave"]
            },
        ),
        types.Tool(
            name="enviar-documento-flash",
            description="Envia documento para Flash na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "modelo": {"type": "string"},
                    "chave": {"type": "string"},
                    "caminho_imagem_documento": {"type": "string"},
                    "tipo_documento": {"type": "string"},
                    "cpf": {"type": "string"},
                },
                "required": ["modelo", "chave", "caminho_imagem_documento"]
            },
        ),
        types.Tool(
            name="extrair-dados-documento-flash",
            description="Extrair dados de um documento com Flash na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "modelo": {"type": "string"},
                    "chave": {"type": "string"},
                    "caminho_imagem_documento": {"type": "string"},
                    "tipo_documento": {"type": "string"},
                    "cpf": {"type": "string"},
                },
                "required": ["modelo", "chave", "caminho_imagem_documento"]
            },
        )
    ]
    
    
async def _internal_get_access_token(client_id: str, client_secret: str) -> str:
    """
    Lógica interna para obter o token de acesso da API.
    Chamada pelas ferramentas que precisam de autenticação.
    Levanta exceção em caso de erro.
    """
    url = f"{API_BASE_URL}{TOKEN_ENDPOINT}"
    payload = {
        "Scope": "api",
        "GrantType": "client_credentials",
        "ClientId": client_id,
        "ClientSecret": client_secret
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    print(f"INFO:     Tentando obter token de: {url}")

    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            print(f"INFO:     Resposta Token Status: {response.status_code}")

            response.raise_for_status()

            token_data = response.json()
            if "access_token" not in token_data:
                raise ValueError(f"Campo 'access_token' não encontrado na resposta da API de Token: {token_data}")

            token = token_data["access_token"]
            print(f"INFO:     Token obtido com sucesso (prefixo): {token[:10]}...")
            return token
        except httpx.RequestError as e:
            print(f"ERRO:     Erro de rede ao obter token: {e}")
            raise Exception(f"Erro de rede ao conectar com {e.request.url!r}: {e}") from e
        except httpx.HTTPStatusError as e:
            print(f"ERRO:     Erro HTTP ao obter token: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Erro HTTP {e.response.status_code} da API de Token: {e.response.text}") from e
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"ERRO:     Erro ao processar resposta do token: {e}")
            raise Exception(f"Erro ao processar resposta da API de Token: {e}") from e
    
        
def converter_para_base64(caminhoImagem: str) -> str:
    try:
        with open(caminhoImagem, "rb") as imagem:
            imagem_bytes = imagem.read()
            imagem_base64 = base64.b64encode(imagem_bytes).decode("utf-8")
            return imagem_base64
    except Exception as e:
        print(f"Erro ao converter imagem: {e}")
        return ""  


async def consultar_flash(chave: str) -> Dict[str, Any]:
    """
    Consulta o resultado Flash de uma chave na API.
    """
    try:
        # 1. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"Token gerado: {access_token[:10]}...")
        
        url = f"{API_BASE_URL}{FLASH_ENDPOINT}/Consultar?chave={chave}"
        print(url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        print(f"INFO:     Consultando flash em: {url}")

        # 2. Fazer a chamada GET para a API de Facematch
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.get(url, headers=headers)
            print(f"INFO:     Resposta Flash Status: {response.status_code}")
            response.raise_for_status()
            flash_data = response.json()
        
        print(f"Flash response status: {response.status_code}")
        
        return {
            "status": "sucesso",
            "resultado": flash_data
        }
    
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'consultar-flash': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar flash: {str(e)}"}


async def enviar_documento_flash(modelo: str, chave: str, imagem_documento_base64: str, tipo_documento: str, cpf: str) -> Dict[str, Any]:
    """
    Envia o documento para Flash na API.
    """
    try:
        # 1. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"Token gerado: {access_token[:10]}...")
        
        url = f"{API_BASE_URL}{FLASH_ENDPOINT}/Enviar/{modelo}"
        print(url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        content = {
            "Chave": chave,
            "TipoDocumento": tipo_documento,
            "ImagemDocumento": imagem_documento_base64,
            "CPF": cpf
        }
        
        print(f"INFO:     Enviando documento para flash em: {url}")

        # 2. Fazer a chamada POST para a API de Facematch
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.post(url, headers=headers, json=content)
            print(f"INFO:     Resposta Flash Status: {response.status_code}")
            response.raise_for_status()
            flash_data = response.json()
        
        print(f"Flash response status: {response.status_code}")
        
        return {
            "status": "sucesso",
            "resultado": flash_data
        }
    
    #Retornar mensagem de erro retornado pela API
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'enviar-documento-flash': {e}")
        return {"status": "erro", "mensagem": f"Erro ao enviar documento para flash: {str(e)}"}
    
    
async def extrair_dados_documento_flash(modelo: str, chave: str, imagem_documento_base64: str, tipo_documento: str, cpf: str) -> Dict[str, Any]:
    """
    Extrair dados do documento com Flash na API.
    """
    try:
        # 1. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"Token gerado: {access_token[:10]}...")
        
        url = f"{API_BASE_URL}{FLASH_ENDPOINT}/ExtrairDados/{modelo}"
        print(url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        content = {
            "Chave": chave,
            "TipoDocumento": tipo_documento,
            "ImagemDocumento": imagem_documento_base64,
            "CPF": cpf
        }
        
        print(f"INFO:     Extraindo dados documento com flash em: {url}")

        # 2. Fazer a chamada POST para a API de Facematch
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.post(url, headers=headers, json=content)
            print(f"INFO:     Resposta Flash Status: {response.status_code}")
            response.raise_for_status()
            flash_data = response.json()
        
        print(f"Flash response status: {response.status_code}")
        
        return {
            "status": "sucesso",
            "resultado": flash_data
        }
    
    #Retornar mensagem de erro retornado pela API
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'extrair-dados-documento-flash': {e}")
        return {"status": "erro", "mensagem": f"Erro ao extrair dados do documento com flash: {str(e)}"}
    
    
@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Manipula as chamadas às ferramentas disponíveis.
    """
    if not arguments:
        raise ValueError("Argumentos ausentes")

    match name: 
        case "consultar-flash":
            chave_flash = arguments.get("chave")

            if chave_flash is None:
                raise ValueError("Chave é obrigatório")

            try:
                resultado = await consultar_flash(chave_flash)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado da consulta do Flash para Chave: {chave_flash}:\n{json.dumps(resultado, indent=2, ensure_ascii=False)}"
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao consultar flash: {str(e)}"
                    )
                ]
                
        case "enviar-documento-flash":
            modelo = arguments.get("modelo")
            chave_flash = arguments.get("chave")
            caminho_imagem_documento = arguments.get("caminho_imagem_documento")
            tipo_documento = arguments.get("tipo_documento", "")
            cpf = arguments.get("cpf", "")

            if chave_flash is None:
                raise ValueError("Chave é obrigatório")
            
            if modelo is None:
                raise ValueError("Modelo é obrigatório")
            
            if caminho_imagem_documento is None:
                raise ValueError("CaminhoImagemDocumento é obrigatório")
            
            imagem_documento_base64 = converter_para_base64(caminho_imagem_documento);

            try:
                resultado = await enviar_documento_flash(modelo=modelo, chave=chave_flash, imagem_documento_base64=imagem_documento_base64, tipo_documento=tipo_documento, cpf=cpf)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado do envio documento do Flash para Chave: {chave_flash}:\n{json.dumps(resultado, indent=2, ensure_ascii=False)}"
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao enviar documento para flash: {str(e)}"
                    )
                ]
                
                
        case "extrair-dados-documento-flash":
            modelo = arguments.get("modelo")
            chave_flash = arguments.get("chave")
            caminho_imagem_documento = arguments.get("caminho_imagem_documento")
            tipo_documento = arguments.get("tipo_documento", "")
            cpf = arguments.get("cpf", "")

            if chave_flash is None:
                raise ValueError("Chave é obrigatório")
            
            if modelo is None:
                raise ValueError("Modelo é obrigatório")
            
            if caminho_imagem_documento is None:
                raise ValueError("CaminhoImagemDocumento é obrigatório")
            
            imagem_documento_base64 = converter_para_base64(caminho_imagem_documento);

            try:
                resultado = await extrair_dados_documento_flash(modelo=modelo, chave=chave_flash, imagem_documento_base64=imagem_documento_base64, tipo_documento=tipo_documento, cpf=cpf)
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado extrair dados do documento com Flash para Chave: {chave_flash}:\n{json.dumps(resultado, indent=2, ensure_ascii=False)}"
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao extrair dados do documento com flash: {str(e)}"
                    )
                ]

        
    
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
                server_name="acertpix-api-flash",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())