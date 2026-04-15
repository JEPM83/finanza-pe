"""
Script de autenticación OAuth2 para Gmail API.
Ejecutar UNA SOLA VEZ en tu PC local (requiere navegador):
    python scripts/gmail_auth.py

Genera config/token.json que luego se copia a la VM.
"""
import os
import sys
import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
TOKEN_PATH = os.path.join(CONFIG_DIR, "token.json")


def encontrar_credentials():
    # Busca cualquier archivo client_secret_*.json en config/
    patron = os.path.join(CONFIG_DIR, "client_secret_*.json")
    archivos = glob.glob(patron)
    if archivos:
        return archivos[0]
    # Fallback al nombre genérico
    generico = os.path.join(CONFIG_DIR, "credentials.json")
    if os.path.exists(generico):
        return generico
    return None


def autenticar():
    creds = None

    # Reutilizar token existente si es válido
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Renovando token expirado...")
            creds.refresh(Request())
        else:
            credentials_path = encontrar_credentials()
            if not credentials_path:
                print("ERROR: No se encontró archivo de credenciales en config/")
                print("Descarga el archivo desde Google Cloud Console y colócalo en config/")
                sys.exit(1)

            print(f"Usando credenciales: {os.path.basename(credentials_path)}")
            print("\nSe abrirá el navegador para autorizar el acceso a Gmail...")
            print("Selecciona la cuenta: epariona.sistemas@gmail.com\n")

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Guardar token para próximas ejecuciones
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"\nToken guardado en: {TOKEN_PATH}")

    print("Autenticación exitosa.")
    return creds


def verificar_acceso(creds):
    from googleapiclient.discovery import build
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    print(f"Conectado como: {profile['emailAddress']}")
    print(f"Total de mensajes: {profile['messagesTotal']:,}")


if __name__ == "__main__":
    print("=== Autenticación Gmail API — finanza-pe ===\n")
    creds = autenticar()
    verificar_acceso(creds)
    print("\nListo. Copia config/token.json a la VM para el despliegue.")
