@echo off
cd /d "%~dp0"

:: Verifica se já está rodando na porta 8501
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul 2>&1
if %errorlevel% == 0 (
    start "" "http://localhost:8501"
    exit
)

:: Inicia o Streamlit
start "" /b streamlit run streamlit_app.py --server.headless true --server.port 8501

:: Aguarda o servidor subir
timeout /t 3 /nobreak >nul

:: Abre o navegador
start "" "http://localhost:8501"