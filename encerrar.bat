@echo off
echo Encerrando Minha Agenda...

:: Mata o processo do streamlit na porta 8501
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo Servidor encerrado.
timeout /t 2 /nobreak >nul