import asyncio
import json
from typing import Optional, Dict, Any # Adicionado Dict, Any para type hints
import httpx # Adicionado para chamadas HTTP assíncronas
import uvicorn # Necessário para rodar o servidor ASGI
import os # Para carregar variáveis de ambiente (opcional, mas bom)
import base64 # Para codificar imagens em base64
from dotenv import load_dotenv # Para carregar .env (opcional)
from fastapi import FastAPI, Request 

# Importações da biblioteca MCP - Usando FastMCP 
from mcp.server.fastmcp import FastMCP
import mcp.types as types

# Carrega variáveis de ambiente de um arquivo .env (opcional)
# load_dotenv()

# Configurações da API - mantidas do código original
# É uma boa prática carregar URLs de variáveis de ambiente
API_BASE_URL = os.getenv("ACERTPIX_API_URL", "https://devapi.plataformaacertpix.com.br")
CLIENT_ID = os.getenv("ACERTPIX_CLIENT_ID", "acertpix-api")
CLIENT_SECRET = os.getenv("ACERTPIX_CLIENT_SECRET", "acertpix-api")
MCP_API_KEY = os.getenv("MCP_API_KEY", "chave-segura")
# NOTA: Usando httpx.AsyncClient para chamadas de rede assíncronas.
# NOTA: A questão de 'verify=False' (desabilitar verificação SSL) ainda é um risco de segurança.
#       Idealmente, configure a verificação corretamente ou use variáveis de ambiente para controlar.
SSL_VERIFY = os.getenv("ACERTPIX_API_SSL_VERIFY", "false").lower() != "true" # Exemplo: default False se não definido como true

print(f"INFO:     Iniciando API Score Acertpix Score com FastMCP...")
print(f"INFO:     API Base URL: {API_BASE_URL}")
print(f"INFO:     Client ID: {CLIENT_ID}")
print(f"INFO:     Client Secret: {CLIENT_SECRET}")
print(f"INFO:     MCP API Key: {MCP_API_KEY}")
print(f"INFO:     SSL Verify: {SSL_VERIFY}")

TOKEN_ENDPOINT = "/OAuth2/Token"
SCORE_ENDPOINT_CONSULTA = "/Score/Consultar"
SCORE_ENDPOINT_ENVIO = "/Score/Enviar"

# Global variable to keep a token a for a request
auth_token = ""
app = FastAPI()

# --- Instância do Servidor FastMCP ---
mcp = FastMCP("acertpix-api-score")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_header = request.headers.get("api-key")
    if auth_header:
        print(f"DEBUG:    Auth Header: {auth_header}")
        # extract token from the header and keep it in the global variable
        global auth_token
        auth_token = auth_header
    
    response = await call_next(request)
    
    return response

def require_auth():
    """
    Check access and raise an error if the token is not valid.
    """
    print(f"DEBUG:    Auth Header: {auth_token}")
     
    if auth_token != MCP_API_KEY:
       raise ValueError("Invalid MCP Server Token Access")
    return None

# --- Funções Auxiliares (Refatoradas para serem chamadas pelas ferramentas) ---

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


# --- Definições de Ferramentas (Usando @mcp.tool) ---
@mcp.tool()
async def consultar_score(chave: str) -> Dict[str, Any]:
    """
    Consulta o score de uma chave na API da Acertpix.
    Retorna um dicionário com o status e o resultado (ou mensagem de erro).
    """
    print(f"INFO:     Executando ferramenta 'consultar-score' para chave: {chave}")

    require_auth()
    try:

        client_id = CLIENT_ID
        client_secret = CLIENT_SECRET

        # 1. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(client_id, client_secret)

        # 2. Montar a requisição para a API de Score
        url = f"{API_BASE_URL}{SCORE_ENDPOINT_CONSULTA}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        params = {"chave": chave} # Parâmetros GET vão em 'params' com httpx

        print(f"INFO:     Consultando score em: {url}")

        # 3. Fazer a chamada GET para a API de Score
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.get(url, headers=headers, params=params)
            print(f"INFO:     Resposta Score Status: {response.status_code}")
            response.raise_for_status() # Levanta exceção para status >= 400
            score_data = response.json()

        print(f"INFO:     Consulta de score bem-sucedida para chave: {chave}")
        return {
            "status": "sucesso",
            "resultado": score_data
        }

    except Exception as e:
        print(f"ERRO:     Falha na ferramenta 'consultar-score': {e}")
        return {"status": "erro", "mensagem": f"Erro ao consultar score: {str(e)}"}

@mcp.tool()
async def enviar_score(chave: str, cpf: Optional[str], ImagemFrentePath: str , ImagemVersoPath: Optional[str], ImagemSelfiePath: Optional[str], ImagemQrCodePath: Optional[str] ) -> Dict[str, Any]:
    """
    Envia Analise para Score na API da Acertpix.
    Os campos são:
    - chave: Chave de acesso da conta do cliente (Obrigario)
    - ImagemFrente: path da imagem da frente do documento do cliente  (Obrigatorio)
    - cpf: CPF do cliente
    - ImagemVerso: path da imagem do verso do documento do cliente
    - ImagemSelfie: path da imagem da selfie do cliente 
    - ImagemQrCode: path da imagem do QR Code do cliente 
    Retorna o resultado (ou mensagem de erro).
    """
    print(f"INFO:     Executando ferramenta 'enviar-score' para chave: {chave}, cpf {cpf}")

    # 1. Autenticação (verifica o API-KEY vindo do middleware)
    require_auth()

    try:

        # 2. Obter Client ID/Secret (definidos globalmente ou via env var)
        if not CLIENT_ID or not CLIENT_SECRET:
             raise ValueError("Client ID ou Client Secret não configurados no servidor.")

        client_id = CLIENT_ID
        client_secret = CLIENT_SECRET

        # 3. Obter o token de acesso usando a lógica interna
        access_token = await _internal_get_access_token(client_id, client_secret)

        # 4. Converter Imagens para Base64
        base64_frente_str = None
        base64_verso_str = None
        base64_selfie_str = None
        base64_qrcode_str = None

        if ImagemFrentePath:
            with open(ImagemFrentePath, "rb") as frente_file:
                base64_frente_str = base64.b64encode(frente_file.read()).decode('utf-8')
                print(f"INFO:     Imagem Frente convertida para Base64: {base64_frente_str}")
        
        if ImagemVersoPath:
            with open(ImagemVersoPath, "rb") as verso_file:
                base64_verso_str = base64.b64encode(verso_file.read()).decode('utf-8')
                print(f"INFO:     Imagem Verso convertida para Base64: {base64_verso_str}")
        
        if ImagemSelfiePath:
            with open(ImagemSelfiePath, "rb") as selfie_file:
                base64_selfie_str = base64.b64encode(selfie_file.read()).decode('utf-8')
                print(f"INFO:     Imagem Selfie convertida para Base64: {base64_selfie_str}")
        
        if ImagemQrCodePath:
            with open(ImagemQrCodePath, "rb") as qrcode_file:
                base64_qrcode_str = base64.b64encode(qrcode_file.read()).decode('utf-8')
                print(f"INFO:     Imagem QRCode convertida para Base64: {base64_qrcode_str}")

        # 5. Montar a requisição para a API de Score
        url = f"{API_BASE_URL}{SCORE_ENDPOINT_ENVIO}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        payload = { # httpx prefere dicts para json
            "Chave": chave,
            "ImagemFrente": base64_frente_str,    
            "ImagemVerso": base64_verso_str,
            "ImagemSelfie": base64_selfie_str,
            "ImagemQrCode": base64_qrcode_str,
            "CPF": cpf
        }        
        # Remove chaves com valor None do payload, se a API externa não os aceitar
        # payload = {k: v for k, v in payload.items() if v is not None}

        print(f"INFO:     Consultando score em: {url}")

        # 3. Fazer a chamada GET para a API de Score
        async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
            response = await client.post(url, json=payload, headers=headers, timeout=60.0)
            print(f"INFO:     Resposta Token Status: {response.status_code}")
            response.raise_for_status() # Levanta exceção para status >= 400
            score_data = response.json()

        print(f"INFO:     Envio para score bem-sucedido para chave: {chave}")
        return {
            "status": "sucesso",
            "resultado": score_data
        }

    except Exception as e:
        print(f"ERRO:     Falha geral na ferramenta 'enviar_score': {e}")
        # Em produção, evite expor detalhes de exceções internas
        return {"status": "erro", "mensagem": f"Erro interno ao processar 'enviar_score'."}



# --- Criação da Aplicação ASGI/SSE a partir do FastMCP ---
# FastMCP deve ter o método sse_app() conforme a documentação
try:
    app.mount("/", mcp.sse_app())
    #asgi_app = mcp.sse_app()
    print("INFO:     Aplicação ASGI/SSE criada a partir do objeto FastMCP.")
except AttributeError:
     # Isso não deveria acontecer se estivermos usando FastMCP corretamente
    print("ERRO:     O objeto FastMCP não possui o método sse_app(). Verifique a versão da lib mcp.")
    asgi_app = None
except Exception as e:
    print(f"ERRO:     Erro inesperado ao criar aplicação ASGI com FastMCP: {e}")
    asgi_app = None

# --- Bloco para Iniciar com Uvicorn ---
if __name__ == "__main__":
    # Verifica se a montagem foi bem-sucedida antes de tentar rodar
    # (Uma forma simples é verificar se alguma rota foi adicionada além do mount)
    if len(app.routes) > 0: # A montagem adiciona rotas
        port = int(os.getenv("PORT", 8000))
        host = os.getenv("HOST", "0.0.0.0")
        log_level = os.getenv("LOG_LEVEL", "info")

        print(f"INFO:     Iniciando servidor FastAPI/MCP em http://{host}:{port}")
        # Executa a aplicação FastAPI 'app' com Uvicorn
        uvicorn.run(
            app, # <--- Passa a instância do FastAPI para o Uvicorn
            host=host,
            port=port,
            log_level=log_level
        )
    else:
        print("ERRO:     Aplicação FastAPI não parece ter rotas montadas. Servidor não iniciado.")
