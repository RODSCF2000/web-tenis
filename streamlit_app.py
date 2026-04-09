import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

from streamlit_calendar import calendar as st_calendar

from calendar_service import fetch_events, normalize_event
from firebase_service import (
    sync_events,
    get_events_by_month,
    get_resumos_mensais,
    get_resumos_anuais,
    get_ultima_sync,
)

# ── Página ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Minha Agenda", page_icon="📅", layout="wide")
st.title("📅 Minha Agenda")
st.caption("Google Calendar sincronizado com Firebase")

# ── Constantes ─────────────────────────────────────────────────────────────────
DATA_INICIO_FIXA = datetime(2024, 4, 26, tzinfo=timezone.utc)
PALAVRAS_CHAVE   = ["aula", "tênis"]

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

def hoje_mais_30() -> datetime:
    return datetime.combine(
        datetime.now().date() + timedelta(days=30),
        datetime.max.time(), tzinfo=timezone.utc,
    )

def evento_relevante(ev: dict) -> bool:
    return all(p in ev.get("titulo", "").lower() for p in PALAVRAS_CHAVE)

# ── Session state ──────────────────────────────────────────────────────────────
if "eventos_por_mes" not in st.session_state:
    st.session_state.eventos_por_mes = {}

def get_mes_cache(year: int, month: int) -> list[dict]:
    chave = f"{year}-{month:02d}"
    if chave not in st.session_state.eventos_por_mes:
        st.session_state.eventos_por_mes[chave] = get_events_by_month(year, month)
    return st.session_state.eventos_por_mes[chave]

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controles")
    st.subheader("📆 Período")
    st.caption("De: **26/04/2024**")
    st.caption(f"Até: **{(datetime.now().date() + timedelta(days=30)).strftime('%d/%m/%Y')}**")
    st.caption("Filtro: **aula** E **tênis**")

    st.divider()
    st.subheader("🔄 Sincronização")
    ultima_sync = get_ultima_sync()
    if ultima_sync:
        st.caption(f"Última sync: {ultima_sync.strftime('%d/%m/%Y %H:%M')}")
    else:
        st.caption("Nunca sincronizado.")

    if st.button("🔄 Sincronizar agora", use_container_width=True, type="primary"):
        with st.spinner("Buscando eventos do Google Calendar..."):
            try:
                raw   = fetch_events(start_dt=DATA_INICIO_FIXA, end_dt=hoje_mais_30())
                norm  = [normalize_event(e) for e in raw]
                filtr = [e for e in norm if evento_relevante(e)]
                total, meses = sync_events(filtr)
                st.session_state.eventos_por_mes = {}
                st.success(f"✅ {total} eventos • {meses} meses sincronizados!")
                st.rerun()
            except FileNotFoundError:
                st.error("❌ token.json não encontrado. Execute `python setup_auth.py` primeiro.")
            except Exception as ex:
                st.error(f"❌ Erro: {ex}")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_cal, tab_resumo, tab_anual = st.tabs(["🗓️ Calendário", "📊 Resumo por mês", "📅 Acompanhamento anual"])

# ── Calendário ─────────────────────────────────────────────────────────────────
with tab_cal:
    hoje = datetime.now()

    if "cal_year"  not in st.session_state: st.session_state.cal_year  = hoje.year
    if "cal_month" not in st.session_state: st.session_state.cal_month = hoje.month

    col_prev, col_titulo, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("◀ Anterior"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
            st.rerun()
    with col_next:
        if st.button("Próximo ▶"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1
            st.rerun()

    year  = st.session_state.cal_year
    month = st.session_state.cal_month
    label_mes = f"{MESES_PT[month]} de {year}"

    with col_titulo:
        st.markdown(f"<h3 style='text-align:center;margin:0'>{label_mes}</h3>", unsafe_allow_html=True)

    with st.spinner(f"Carregando {label_mes}..."):
        try:
            eventos_mes = get_mes_cache(year, month)
        except Exception as ex:
            st.error(f"Erro ao carregar eventos: {ex}")
            eventos_mes = []

    cores = ["#4285F4", "#34A853", "#FBBC05", "#EA4335", "#8E44AD", "#16A085"]
    cal_events = []
    for i, ev in enumerate(eventos_mes):
        item = {
            "title": ev.get("titulo", "Sem título"),
            "start": ev.get("inicio", ""),
            "end":   ev.get("fim", ""),
            "color": cores[i % len(cores)],
        }
        if ev.get("dia_inteiro"):
            item["allDay"] = True
        cal_events.append(item)

    st_calendar(
        events=cal_events,
        options={
            "headerToolbar": {"left": "", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
            "initialView": "dayGridMonth",
            "initialDate": f"{year}-{month:02d}-01",
            "locale": "pt-br",
            "height": 620,
            "selectable": False,
            "editable": False,
            "navLinks": False,
        },
        key=f"cal_{year}_{month}",
    )
    st.caption(f"{len(eventos_mes)} aula(s) em {label_mes}" if eventos_mes else f"Nenhuma aula em {label_mes}.")

# ── Resumo por mês ─────────────────────────────────────────────────────────────
with tab_resumo:
    with st.spinner("Carregando resumos..."):
        try:
            resumos_mensais = get_resumos_mensais()
        except Exception as ex:
            st.error(f"Erro ao carregar resumos: {ex}")
            resumos_mensais = []

    hoje_mes = datetime.now().strftime("%Y-%m")
    resumos_passados = [r for r in resumos_mensais if r.get("mes", "") < hoje_mes]

    if not resumos_mensais:
        st.info("Nenhum resumo disponível. Sincronize primeiro.")
    else:
        if resumos_passados:
            total_geral  = sum(r["total_aulas"] for r in resumos_passados)
            media_mensal = total_geral / len(resumos_passados)
            melhor       = max(resumos_passados, key=lambda r: r["total_aulas"])
            rec_semana   = max(resumos_passados, key=lambda r: r.get("semana_recorde", 0))
            rec_dia      = max(resumos_passados, key=lambda r: r.get("dia_recorde", 0))

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total de aulas",  total_geral)
            c2.metric("Média mensal",    f"{media_mensal:.1f}")
            c3.metric("Mês recorde",     f"{melhor['mes_label']} ({melhor['total_aulas']})")
            c4.metric("Recorde semanal", f"{rec_semana.get('semana_recorde', 0)} aulas")
            c5.metric("Recorde diário",  f"{rec_dia.get('dia_recorde', 0)} aulas")

        st.divider()

        # Gráfico ordenado cronologicamente — usa índice numérico para preservar ordem
        st.subheader("Aulas por mês")
        df_graf = pd.DataFrame([
            {"Mês": r["mes_label"], "Aulas": r["total_aulas"]}
            for r in sorted(resumos_mensais, key=lambda r: r["mes"])
        ])
        # st.bar_chart reordena labels alfabeticamente; usamos st.dataframe-like via plotly workaround:
        # forçamos ordem mantendo o DataFrame como lista ordenada e usando categoria ordenada
        df_graf["Mês"] = pd.Categorical(df_graf["Mês"], categories=df_graf["Mês"].tolist(), ordered=True)
        st.bar_chart(df_graf.set_index("Mês")["Aulas"], use_container_width=True, height=300, color="#4285F4")

        st.divider()

        st.subheader("Detalhamento mensal")
        for r in reversed(resumos_mensais):
            with st.expander(f"**{r['mes_label']}** — {r['total_aulas']} aulas"):
                m1, m2, m3 = st.columns(3)
                m1.metric("Total",           r["total_aulas"])
                m2.metric("Recorde semanal", f"{r.get('semana_recorde', 0)} aulas")
                m3.metric("Recorde diário",  f"{r.get('dia_recorde', 0)} aulas")

                unidades = r.get("aulas_por_unidade", [])
                if unidades:
                    st.caption("**Aulas por unidade:**")
                    df_u = pd.DataFrame([
                        {"Unidade": u["nome"], "Aulas": u["quantidade"]}
                        for u in unidades
                    ])
                    st.dataframe(df_u, hide_index=True, use_container_width=True)

# ── Acompanhamento anual ───────────────────────────────────────────────────────
with tab_anual:
    import calendar as cal_mod

    with st.spinner("Carregando dados anuais..."):
        try:
            resumos_anuais = get_resumos_anuais()
        except Exception as ex:
            st.error(f"Erro ao carregar resumos anuais: {ex}")
            resumos_anuais = []

    if not resumos_anuais:
        st.info("Nenhum dado anual disponível. Sincronize primeiro.")
    else:
        agora     = datetime.now()
        ano_atual = agora.year
        ANO_INICIO        = 2024
        DATA_INICIO_PRATICAS = datetime(2024, 4, 26)   # início das práticas

        for r in reversed(resumos_anuais):
            ano  = r["ano"]
            aulas = r.get("total_aulas_finalizadas", r["total_aulas"])  # usa campo fino se existir

            # ── Dias úteis do ano (considerando 26/04 para 2024) ──────────────
            if ano == ANO_INICIO:
                inicio_contagem = DATA_INICIO_PRATICAS
                info_inicio     = f"(a partir de 26/04/{ANO_INICIO}, data de início das práticas)"
            else:
                inicio_contagem = datetime(ano, 1, 1)
                info_inicio     = ""

            fim_contagem     = datetime(ano, 12, 31)
            total_dias_periodo = (fim_contagem - inicio_contagem).days + 1
            objetivo           = total_dias_periodo   # 1 aula por dia

            # ── Dias decorridos e progresso ───────────────────────────────────
            if ano < ano_atual:
                dias_decorridos = total_dias_periodo
                encerrado       = True
                status_label    = "✅ Ano encerrado"
            else:
                dias_decorridos = (agora - inicio_contagem).days + 1
                dias_decorridos = min(dias_decorridos, total_dias_periodo)
                encerrado       = False
                status_label    = f"📍 Dia {dias_decorridos} de {total_dias_periodo}"

            atingiu_objetivo = aulas >= objetivo
            cor_objetivo     = "#16A085" if atingiu_objetivo else "#E74C3C"
            pct_objetivo     = min(aulas / objetivo, 1.0) if objetivo > 0 else 0

            with st.expander(
                f"**{ano}** — {aulas} aulas  •  {status_label}",
                expanded=(ano == ano_atual),
            ):
                if info_inicio:
                    st.caption(info_inicio)

                # ── Barra de progresso do ano (dias) ─────────────────────────
                pct_ano = dias_decorridos / total_dias_periodo if total_dias_periodo > 0 else 1.0
                texto_dias = (
                    f"Período completo — {total_dias_periodo} dias"
                    if encerrado
                    else f"Dia {dias_decorridos} de {total_dias_periodo} ({pct_ano*100:.1f}% do período)"
                )
                st.markdown(
                    f"""
                    <div style="margin:6px 0 12px 0">
                        <div style="font-size:0.85em;margin-bottom:4px">📆 {texto_dias}</div>
                        <div style="background:#e0e0e0;border-radius:6px;height:18px;width:100%">
                            <div style="background:#4285F4;width:{pct_ano*100:.1f}%;height:18px;border-radius:6px;min-width:4px"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # ── Barra de objetivo (1 aula/dia) ────────────────────────────
                faltam_texto = "✅ Meta atingida!" if atingiu_objetivo else (
                    f"faltaram {objetivo - aulas}" if encerrado else f"faltam {objetivo - aulas}"
                )
                texto_obj = f"🎯 Objetivo: {aulas}/{objetivo} aulas ({faltam_texto})"
                st.markdown(
                    f"""
                    <div style="margin:6px 0 12px 0">
                        <div style="font-size:0.85em;margin-bottom:4px">{texto_obj}</div>
                        <div style="background:#e0e0e0;border-radius:6px;height:18px;width:100%">
                            <div style="background:{cor_objetivo};width:{pct_objetivo*100:.1f}%;height:18px;border-radius:6px;min-width:4px"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.divider()

                # ── Métricas ──────────────────────────────────────────────────
                semanas_passadas = dias_decorridos / 7 if dias_decorridos > 0 else 1
                media_semana     = aulas / semanas_passadas

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total de aulas",   aulas)
                col2.metric("Recorde semanal",  f"{r.get('semana_recorde', 0)} aulas")
                col3.metric("Recorde diário",   f"{r.get('dia_recorde', 0)} aulas")
                col4.metric("Média por semana", f"{media_semana:.1f}")

                if not encerrado:
                    dias_restantes = total_dias_periodo - dias_decorridos
                    st.caption(f"Dias restantes no período: **{dias_restantes}**")