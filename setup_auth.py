"""
Execute este script UMA VEZ para autorizar o acesso ao Google Calendar.
Ele vai abrir o navegador, você faz login, e salva o token.json automaticamente.
Depois disso, o app funciona sem precisar de login nunca mais.

Uso:
    python setup_auth.py
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main():
    print("🔐 Iniciando autorização do Google Calendar...")
    print("   O navegador vai abrir. Faça login com sua conta Google.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print()
    print("✅ Autorização concluída! token.json salvo.")
    print("   Agora rode: streamlit run app.py")


if __name__ == "__main__":
    main()