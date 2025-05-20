import asyncio
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, AnyUrl
# import requests
import httpx # Adicionado para chamadas HTTP assíncronas

import os # Para carregar variáveis de ambiente (opcional, mas bom)
from dotenv import load_dotenv # Para carregar .env (opcional)

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

import base64

# Carrega variáveis de ambiente de um arquivo .env (opcional)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

# Configurações da API
API_BASE_URL = os.getenv("ACERTPIX_API_URL", "https://devapi.plataformaacertpix.com.br")
CLIENT_ID = os.getenv("ACERTPIX_CLIENT_ID", "acertpix-api")
CLIENT_SECRET = os.getenv("ACERTPIX_CLIENT_SECRET", "acertpix-api")
SSL_VERIFY = os.getenv("ACERTPIX_API_SSL_VERIFY", "true").lower() != "true"

print(f"INFO:     Iniciando API OCR Acertpix")
print(f"INFO:     API Base URL: {API_BASE_URL}")
print(f"INFO:     Client ID: {CLIENT_ID}")
print(f"INFO:     Client Secret: {CLIENT_SECRET}")
print(f"INFO:     SSL Verify: {SSL_VERIFY}")

TOKEN_ENDPOINT = "/OAuth2/Token"
OCR_ENDPOINT = "/OCR"

server = Server("acertpix-api-ocr")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lista as ferramentas disponíveis para interação com a API
    """
    return [
        types.Tool(
            name="consultar-ocr",
            description="Consultar OCR com uma chave na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                },
                "required": ["chave"]
            },
        ),
        types.Tool(
            name="enviar-documento-ocr",
            description="Enviar um documento para ser gerado um OCR desse documento, os documentos enviados serão convertidos no seu ambiente para base64 e enviados para a função da tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                    "cpf": {"type": "string"},
                    "caminhoImagemFrente": {"type": "string"},
                    "caminhoImagemVerso": {"type": "string"},
                    # Adicionar campos do WebHook
                },
                "required": ["chave", "caminhoImagemFrente"]
            },
        ),
    ]
    
      
async def _internal_get_access_token(client_id: str, client_secret: str) -> str:
    """
    Lógica interna para obter o token de acesso da API.
    Chamada pelas ferramentas que precisam de autenticação.
    Levanta exceção em caso de erro.
    """
    url = f"{API_BASE_URL}{TOKEN_ENDPOINT}"
    payload = { # httpx prefere dicts para json
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

            response.raise_for_status() # Levanta exceção para status >= 400

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
   
    
async def consultar_ocr(chave: str) -> Dict[str, Any]:
    try:
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"\nToken gerado: {access_token}\n")
        
        url = f"{API_BASE_URL}{OCR_ENDPOINT}/Consultar?chave={chave}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        params = {"chave": chave} # Parâmetros GET vão em 'params' com httpx
        
        print(f"INFO:     Consultando ocr em: {url}")

        # 3. Fazer a chamada GET para a API
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.get(url, headers=headers, params=params)
            print(f"INFO:     Resposta ocr Status: {response.status_code}")
            response.raise_for_status() # Levanta exceção para status >= 400
            ocr_data = response.json()
        
        print(f"ocr response status: {response.status_code}")
        print(f"ocr response text: {response.text}")
        
        return {
            "status": "sucesso",
            "resultado": ocr_data
        }


    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'consultar-ocr': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar OCR: {str(e)}"}


async def enviar_documento_ocr(chave: str, cpf: str, imagemFrente: str, imagemVerso: str) -> Dict[str, Any]:
    try:
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"\nToken gerado: {access_token}\n")
    
        url = f"{API_BASE_URL}{OCR_ENDPOINT}/Enviar"
    
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        # params = {"chave": chave} # Parâmetros GET vão em 'params' com httpx
            
        content = {
            "chave": chave,
            "cpf": cpf,
            "imagemFrente": imagemFrente,
            "imagemVerso": imagemVerso
        }
        
        print(f"INFO:     enviando documento para ocr em: {url}")

        # 3. Fazer a chamada GET para a API
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.post(url, headers=headers, json=content)
            print(f"INFO:     Resposta ocr Status: {response.status_code}")
            response.raise_for_status() # Levanta exceção para status >= 400
            ocr_data = response.json()
        
        print(f"ocr response status: {response.status_code}")
        print(f"ocr response text: {response.text}")
        
        return {
        "status": "sucesso",
        "resultado": ocr_data
        }
    
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'consultar-ocr': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar OCR: {str(e)}"}

def converter_para_base64(caminhoImagem: str) -> str:
    try:
        with open(caminhoImagem, "rb") as imagem:
            imagem_bytes = imagem.read()
            imagem_base64 = base64.b64encode(imagem_bytes).decode("utf-8")
            return imagem_base64
    except Exception as e:
        print(f"Erro ao converter imagem: {e}")             
    
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
        case "consultar-ocr":
            
            chave = arguments.get("chave")
            if not all([chave]):
                raise ValueError("Chave é obrigatória")
            
            try:
                resultado = await consultar_ocr(chave)
                return [
                    types.TextContent(
                    type="text",
                    text=f"Resultado da consulta do OCR para chave {chave}:\n{resultado}"
                )    
               ]
                
            except Exception as e:
                return [
                    types.TextContent(
                    type="text",
                    text=f"Erro ao consultar OCR: {str(e)}\nURL: {API_BASE_URL}"
                )
            ]
        
        case "enviar-documento-ocr":
            chave = arguments.get("chave")
            cpf = arguments.get("cpf")
            caminhoImagemFrente = arguments.get("caminhoImagemFrente")
            caminhoImagemVerso = arguments.get("caminhoImagemVerso")
            
            if not all([chave]):
                raise ValueError("Chave é obrigatória")
            
            if not all([caminhoImagemFrente]):
                raise ValueError("ImagemFrente é obrigatória")
            
            base64ImagemFrente = ""
            if(caminhoImagemFrente):
                base64ImagemFrente = converter_para_base64(caminhoImagemFrente)

            base64ImagemVerso = ""
            if(caminhoImagemVerso):
                base64ImagemVerso = converter_para_base64(caminhoImagemVerso)

            try:
                resultado = await enviar_documento_ocr(chave, cpf, base64ImagemFrente, base64ImagemVerso)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado do envio do documento OCR : {resultado}"
                    ) 
                ]
                
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao enviar documento ocr {str(e)}\nURL: {API_BASE_URL}"
                    )
                ]
            
     
async def main():
    """
    Inicia o servidor MCP.
    """
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="acertpix-api-ocr",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())