# Como criar o atalho na Área de Trabalho

## Passo 1 — Copiar os arquivos novos para a pasta do projeto

Copie para dentro da pasta `agenda-firebase/`:
- `iniciar.bat`
- `Minha Agenda.vbs`
- `encerrar.bat`

---

## Passo 2 — Criar o atalho

1. Clique com o botão direito em **`Minha Agenda.vbs`**
2. Clique em **"Criar atalho"** (ou "Enviar para → Área de trabalho")
3. Se criou na mesma pasta, arraste o atalho para a **Área de Trabalho**

---

## Passo 3 — Colocar um ícone no atalho (opcional)

1. Clique com o botão direito no **atalho** (na área de trabalho)
2. Clique em **Propriedades**
3. Clique em **Alterar ícone...**
4. Clique em **Procurar** e escolha um `.ico` de sua preferência
   - Sugestão gratuita: https://icon-icons.com (busque "calendar")
   - Baixe um `.ico` e aponte para ele

---

## Como usar

| Ação | Como fazer |
|---|---|
| **Abrir o app** | Duplo clique no atalho da área de trabalho |
| **Se já estiver rodando** | Duplo clique abre direto no navegador |
| **Fechar o servidor** | Execute `encerrar.bat` (ou reinicie o PC) |

---

## Como funciona por baixo

```
Atalho (.lnk)
  └── Minha Agenda.vbs       ← sem janela de terminal
        └── iniciar.bat      ← verifica se já está rodando
              └── streamlit run app.py
                    └── abre http://localhost:8501 no navegador
```

---

## Dica: iniciar automaticamente com o Windows (opcional)

1. Pressione `Win + R`, digite `shell:startup` e pressione Enter
2. Copie o atalho da área de trabalho para essa pasta
3. O app vai iniciar automaticamente quando o Windows ligar