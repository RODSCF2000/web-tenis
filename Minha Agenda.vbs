' Lança o Streamlit sem abrir janela de terminal
Dim shell
Set shell = CreateObject("WScript.Shell")

' Caminho da pasta do app (mesmo diretório deste .vbs)
Dim pasta
pasta = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))

' Executa o bat silenciosamente (0 = janela oculta)
shell.Run """" & pasta & "iniciar.bat""", 0, False

Set shell = Nothing