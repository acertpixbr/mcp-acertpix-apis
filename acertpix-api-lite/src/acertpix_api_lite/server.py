import asyncio
import base64
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

# Carrega variáveis de ambiente de um arquivo .env (opcional)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

# Configurações da API
API_BASE_URL = os.getenv("ACERTPIX_API_URL", "https://devapi.plataformaacertpix.com.br")
CLIENT_ID = os.getenv("ACERTPIX_CLIENT_ID", "acertpix-api")
CLIENT_SECRET = os.getenv("ACERTPIX_CLIENT_SECRET", "acertpix-api")
SSL_VERIFY = os.getenv("ACERTPIX_API_SSL_VERIFY", "true").lower() != "true"

print(f"INFO:     Iniciando API Lite Acertpix")
print(f"INFO:     API Base URL: {API_BASE_URL}")
print(f"INFO:     Client ID: {CLIENT_ID}")
print(f"INFO:     Client Secret: {CLIENT_SECRET}")
print(f"INFO:     SSL Verify: {SSL_VERIFY}")

TOKEN_ENDPOINT = "/OAuth2/Token"
LITE_ENDPOINT = "/Lite"
LITE_ENVIAR_ENDPOINT = "/Lite/Enviar"

server = Server("acertpix-api-lite")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lista as ferramentas disponíveis para interação com a API 
    """
    return [
        types.Tool(
            name="consultar-lite",
            description="Consultar a analise do produto lite com uma chave na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                },
                "required": ["chave"]
            },
        ),
        types.Tool(
            name="enviar-lite",
            description="Enviar documento lite na API da AcertPix",
            inputSchema={
                "type": "object",
                "properties": {
                    "Chave": {"type": "string"},
                    "ImagemFrente": {"type": "string"},
                    "ImagemVerso": {"type": "string"},
                    "ImagemSelfie": {"type": "string"},
                    "ImagemQrCode": {"type": "string"},
                    "CPF": {"type": "string"}
                },
                "required": [
                    "Chave",
                    "ImagemFrente",
                ],
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
   
    
async def consultar_lite(chave: str) -> Dict[str, Any]:
    try:
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"\nToken gerado: {access_token}\n")
        
        url = f"{API_BASE_URL}{LITE_ENDPOINT}/Consultar?chave={chave}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        params = {"chave": chave} # Parâmetros GET vão em 'params' com httpx
        
        print(f"INFO:     Consultando lite em: {url}")

        # 3. Fazer a chamada GET para a API
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.get(url, headers=headers, params=params)
            print(f"INFO:     Resposta Lite Status: {response.status_code}")
            response.raise_for_status() # Levanta exceção para status >= 400
            lite_data = response.json()
        
        print(f"Lite response status: {response.status_code}")
        print(f"Lite response text: {response.text}")
        
        return {
            "status": "sucesso",
            "resultado": lite_data
        }


    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'consultar-lite': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar lite: {str(e)}"}


async def enviar_lite(
    Chave: str,
    ImagemFrente: str,
    ImagemVerso: str,
    ImagemSelfie: str,
    ImagemQrCode: str,
    CPF: str,
) -> Dict[str, Any]:
    try:
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"\nToken gerado: {access_token}\n")

        url = f"{API_BASE_URL}{LITE_ENVIAR_ENDPOINT}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        # params = {"chave": chave} # Parâmetros GET vão em 'params' com httpx

        content = {
            "Chave": Chave,
            "ImagemFrente": ImagemFrente,
            "ImagemVerso": ImagemVerso,
            "ImagemSelfie": ImagemSelfie,
            "ImagemQrCode": ImagemQrCode,
            "CPF": CPF
        }

        print(f"INFO:     enviando documento lite para analise em: {url}")

        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.post(url, headers=headers, json=content)
            print(f"INFO:     Resposta enviar lite Status: {response.status_code}")
            response.raise_for_status()  
            ocr_data = response.json()

        print(f"lite response status: {response.status_code}")
        print(f"lite response text: {response.text}")

        return {"status": "sucesso", "resultado": ocr_data}

    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'enviar-lite': {e}")
        return {"status": "erro", "mensagem": f"Erro ao enviar lite: {str(e)}"}
    
def converter_para_base64(caminhoImagem: str) -> str:
    try:
        with open(caminhoImagem, "rb") as imagem:
            imagem_bytes = imagem.read()
            imagem_base64 = base64.b64encode(imagem_bytes).decode("utf-8")
            return imagem_base64
    except Exception as e:
        print(f"Erro ao converter imagem: {e}")
        return ""
    
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
        case "consultar-lite":
            
            chave = arguments.get("chave")
            if not all([chave]):
                raise ValueError("Chave é obrigatória")
            
            try:
                resultado = await consultar_lite(chave)
                return [
                    types.TextContent(
                    type="text",
                    text=f"Resultado da consulta de analise lite para chave {chave}:\n{resultado}"
                )    
               ]
                
            except Exception as e:
                return [
                    types.TextContent(
                    type="text",
                    text=f"Erro ao consultar analise lite: {str(e)}\nURL: {API_BASE_URL}"
                )
            ]
        case "enviar-lite":

            campos_obrigatorios = [
                "Chave",
                "ImagemFrente"
            ]
            
            valores = {}

            for campo in campos_obrigatorios:
                valor = arguments.get(campo)
                if not valor and valor != 0:
                    raise ValueError(f"O campo '{campo}' é obrigatório")
                valores[campo] = valor

            Chave = valores["Chave"]
            ImagemFrente = valores["ImagemFrente"]
            ImagemVerso = arguments.get("ImagemVerso", "")
            ImagemSelfie = arguments.get("ImagemSelfie", "")
            ImagemQrCode = arguments.get("ImagemQrCode", "")
            CPF = arguments.get("CPF", "")
            
            base64ImagemFrente = converter_para_base64(ImagemFrente);
            
            base64ImagemVerso = ""
            if ImagemVerso:
                base64ImagemVerso = converter_para_base64(ImagemVerso)
                
            base64Selfie = ""
            if ImagemSelfie:
                base64Selfie = converter_para_base64(ImagemSelfie)
                
            base64QrCode = ""
            if ImagemQrCode:
                base64QrCode = converter_para_base64(ImagemQrCode)
            

            try:
                resultado = await enviar_lite(
                    Chave,
                    base64ImagemFrente,
                    base64Selfie,
                    base64ImagemVerso,
                    base64QrCode,
                    CPF,
                )
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado do envio do documento lite para analise :\n{resultado}",
                    )
                ]

            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao enviar documento lite para analise: {str(e)}\nURL: {API_BASE_URL}",
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
                server_name="acertpix-api-lite",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())