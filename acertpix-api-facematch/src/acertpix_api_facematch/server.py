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

print(f"INFO:     Iniciando API Facematch Acertpix")
print(f"INFO:     API Base URL: {API_BASE_URL}")
print(f"INFO:     Client ID: {CLIENT_ID}")
print(f"INFO:     Client Secret: {CLIENT_SECRET}")
print(f"INFO:     SSL Verify: {SSL_VERIFY}")

TOKEN_ENDPOINT = "/OAuth2/Token"
BIOMETRIA_CONSULTAR_ENDPOINT = "/Biometria/Consultar"
BIOMETRIA_ENVIAR_ENDPOINT = "/Biometria/Enviar"

server = Server("acertpix-api-facematch")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lista as ferramentas disponíveis para interação com a API de Facematch.
    """
    return [
        types.Tool(
            name="consultar-facematch",
            description="Consulta os facematch de uma ID na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                },
                "required": ["id"]
            },
        ),
        types.Tool(
            name="enviar-facematch",
            description="Envia documentos para facematch na API da Acertpix",
            inputSchema={
                "type": "object",
                "properties": {
                    "chave": {"type": "string"},
                    "cpf": {"type": "string"},
                    "caminhoImagemFrente": {"type": "string"},
                    "caminhoImagemVerso": {"type": "string"},
                    "caminhoImagemSelfie": {"type": "string"},
                },
                "required": ["chave", "caminhoImagemFrente", "caminhoImagemSelfie"]
            },
        ),
        types.Tool(
            name="obter-pdf-facematch",
            description="Buscar/Consultar/Obter o pdf do facematch de um ID na API da AcertPix",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "caminho_salvar": {"type": "string"},
                },
                "required": ["id", "caminho_salvar"]
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


async def consultar_facematch(id: int) -> Dict[str, Any]:
    """
    Consulta os dados de facematch por ID na API.
    """
    try:
        # 1. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"Token gerado: {access_token[:10]}...")
        
        url = f"{API_BASE_URL}{BIOMETRIA_CONSULTAR_ENDPOINT}/{id}"
        print(url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        print(f"INFO:     Consultando facematch em: {url}")

        # 2. Fazer a chamada GET para a API de Facematch
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.get(url, headers=headers)
            print(f"INFO:     Resposta Facematch Status: {response.status_code}")
            response.raise_for_status()
            biometria_data = response.json()
        
        print(f"Facematch response status: {response.status_code}")
        
        return {
            "status": "sucesso",
            "resultado": biometria_data
        }
    
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'consultar-facematch': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar facematch: {str(e)}"}


async def enviar_facematch(chave: str, cpf: str, imagemFrente: str, imagemVerso: str, imagemSelfie: str) -> Dict[str, Any]:
    try:
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"\nToken gerado: {access_token}\n")
    
        url = f"{API_BASE_URL}{BIOMETRIA_ENVIAR_ENDPOINT}"
    
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
            "imagemVerso": imagemVerso,
            "imagemSelfie": imagemSelfie
        }
        
        print(f"INFO:     enviando documento para facematch em: {url}")

        # 3. Fazer a chamada GET para a API
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.post(url, headers=headers, json=content)
            print(f"INFO:     Resposta ocr Status: {response.status_code}")
            response.raise_for_status() # Levanta exceção para status >= 400
            facematch_data = response.json()
        
        print(f"facematch response status: {response.status_code}")
        print(f"facematch response text: {response.text}")
        
        return {
        "status": "sucesso",
        "resultado": facematch_data
        }
    
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'enviar-facematch': {e}")
        return {"status": "erro", "mensagem": f"Erro ao enviar facematch: {str(e)}"}

def converter_para_base64(caminhoImagem: str) -> str:
    try:
        with open(caminhoImagem, "rb") as imagem:
            imagem_bytes = imagem.read()
            imagem_base64 = base64.b64encode(imagem_bytes).decode("utf-8")
            return imagem_base64
    except Exception as e:
        print(f"Erro ao converter imagem: {e}")  


async def obter_pdf_facematch(id: int, caminho_salvar: str) -> Dict[str, Any]:
    """
    Obtem pdf do facematch por ID na API.
    """
    try:
        # 1. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(CLIENT_ID, CLIENT_SECRET)
        print(f"Token gerado: {access_token[:10]}...")
        
        url = f"{API_BASE_URL}/Biometria/ObterPdf/{id}"
        print(url)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        print(f"INFO:     Obtendo pdf do facematch em: {url}")
        
        caminho_salvar_completo = os.path.join(caminho_salvar, f"facematch_pdf_{id}.pdf")

        # 2. Fazer a chamada GET para a API de Facematch
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.get(url, headers=headers)
            print(f"INFO:     Resposta Facematch Status: {response.status_code}")
            response.raise_for_status()
            
            with open(caminho_salvar_completo, "wb") as file:
                file.write(response.content)
                
        
        print(f"Facematch response status: {response.status_code}")
        
        return {
            "status": "sucesso",
            "resultado": f"Pdf Facematch salvo em: {caminho_salvar_completo}"
        }
    
    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'obter-pdf-facematch': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar facematch: {str(e)}"}
    

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
        case "consultar-facematch":
            id_biometria = arguments.get("id")

            if id_biometria is None:
                raise ValueError("ID é obrigatório")

            try:
                resultado = await consultar_facematch(id_biometria)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado da consulta de facematch para ID {id_biometria}:\n{json.dumps(resultado, indent=2, ensure_ascii=False)}"
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao consultar facematch: {str(e)}"
                    )
                ]

        case "enviar-facematch":
                chave = arguments.get("chave")
                cpf = arguments.get("cpf", "")
                caminhoImagemFrente = arguments.get("caminhoImagemFrente")
                caminhoImagemVerso = arguments.get("caminhoImagemVerso", "")
                caminhoImagemSelfie = arguments.get("caminhoImagemSelfie")
                
                if not all([chave]):
                    raise ValueError("Chave é obrigatória")
                
                if not all([caminhoImagemFrente]):
                    raise ValueError("ImagemFrente é obrigatória")
                
                if not all([caminhoImagemSelfie]):
                    raise ValueError("ImagemSelfie é obrigatória")
                
                base64ImagemFrente = ""
                if(caminhoImagemFrente):
                    base64ImagemFrente = converter_para_base64(caminhoImagemFrente)

                base64ImagemVerso = ""
                if(caminhoImagemVerso):
                    base64ImagemVerso = converter_para_base64(caminhoImagemVerso)

                base64ImagemSelfie = ""
                if(caminhoImagemSelfie):
                    base64ImagemSelfie = converter_para_base64(caminhoImagemSelfie)

                try:
                    resultado = await enviar_facematch(chave, cpf, base64ImagemFrente, base64ImagemVerso, base64ImagemSelfie)
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Resultado do envio do facematch : {resultado}"
                        ) 
                    ]
                    
                except Exception as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Erro ao enviar facematch {str(e)}\nURL: {API_BASE_URL}"
                        )
                    ]

        case "obter-pdf-facematch":
            
            id_biometria = arguments.get("id")
            
            caminho_salvar = arguments.get("caminho_salvar")

            if id_biometria is None:
                raise ValueError("ID é obrigatório")
            
            if caminho_salvar is None:
                raise ValueError("CaminhoSalvar é obrigatório")
                
            try:
                resultado = await obter_pdf_facematch(id_biometria, caminho_salvar)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Resultado do obter pdf de facematch para ID {id_biometria}:\n{json.dumps(resultado, indent=2, ensure_ascii=False)}"
                    )
                ]
            except Exception as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Erro ao obter pdf do facematch: {str(e)}"
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
                server_name="acertpix-api-facematch",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())