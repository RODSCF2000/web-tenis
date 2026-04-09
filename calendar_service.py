from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import TransportError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timezone
import os

SCOPES         = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH      = "token.json"
CREDENTIALS_PATH = "credentials.json"


def _reautorizar() -> Credentials:
    """Abre o navegador para reautorização e salva o novo token."""
    flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    return creds


def _get_credentials() -> Credentials:
    """
    Retorna credenciais válidas.
    - Se o token expirou normalmente: renova com refresh_token (silencioso)
    - Se o token foi revogado / inválido: abre o navegador automaticamente
    """
    if not os.path.exists(TOKEN_PATH):
        return _reautorizar()

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            return creds
        except Exception as e:
            # Token revogado, expirado permanentemente ou inválido → reautoriza
            if "invalid_grant" in str(e) or "Token has been expired or revoked" in str(e):
                return _reautorizar()
            raise

    # Sem refresh_token disponível
    return _reautorizar()


def _get_service():
    creds = _get_credentials()
    return build("calendar", "v3", credentials=creds)


def fetch_events(start_dt: datetime = None, end_dt: datetime = None) -> list[dict]:
    """Busca TODOS os eventos do Google Calendar no intervalo, seguindo paginação."""
    service = _get_service()

    now      = datetime.now(timezone.utc)
    time_min = (start_dt or now).astimezone(timezone.utc).isoformat()

    params = {
        "calendarId": "primary",
        "timeMin":    time_min,
        "maxResults": 2500,
        "singleEvents": True,
        "orderBy":    "startTime",
    }

    if end_dt:
        params["timeMax"] = end_dt.astimezone(timezone.utc).isoformat()

    all_events = []
    while True:
        result = service.events().list(**params).execute()
        all_events.extend(result.get("items", []))
        next_page_token = result.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token

    return all_events


def normalize_event(raw: dict) -> dict:
    """Converte o formato bruto da API para um dict limpo."""
    inicio_raw = raw["start"].get("dateTime", raw["start"].get("date", ""))
    fim_raw    = raw["end"].get("dateTime",   raw["end"].get("date",   ""))

    return {
        "id":         raw["id"],
        "titulo":     raw.get("summary",     "Sem título"),
        "inicio":     inicio_raw,
        "fim":        fim_raw,
        "descricao":  raw.get("description", ""),
        "local":      raw.get("location",    ""),
        "link":       raw.get("htmlLink",    ""),
        "dia_inteiro": "date" in raw["start"],
    }