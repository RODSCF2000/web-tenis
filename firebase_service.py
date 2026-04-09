import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import calendar

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

def _mes_label(year: int, month: int) -> str:
    return f"{MESES_PT[month]}/{year}"


def _get_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccount.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Unidades ───────────────────────────────────────────────────────────────────

def get_unidades() -> list[dict]:
    db = _get_db()
    return [{"id": doc.id, **doc.to_dict()} for doc in db.collection("unidades").stream()]


def _match_unidade(local_evento: str, unidades: list[dict]) -> dict | None:
    if not local_evento:
        return None
    local_lower = local_evento.lower()
    for u in unidades:
        if u.get("local", "").lower() in local_lower:
            return u
        if u.get("nome", "").lower() in local_lower:
            return u
    return None


# ── Cálculo dos resumos mensais ────────────────────────────────────────────────

def _calcular_resumos(events: list[dict], unidades: list[dict], db) -> dict:
    from datetime import timezone as _tz
    agora = datetime.now(_tz.utc)
    meses: dict[str, dict] = {}

    for ev in events:
        try:
            dt     = datetime.fromisoformat(ev["inicio"])
            dt_fim = datetime.fromisoformat(ev["fim"]) if ev.get("fim") else None
        except Exception:
            continue
        # Normaliza para aware se necessário
        if dt_fim is not None and dt_fim.tzinfo is None:
            dt_fim = dt_fim.replace(tzinfo=_tz.utc)
        # Só conta aulas totalmente finalizadas
        if dt_fim is None or dt_fim > agora:
            continue

        chave = f"{dt.year}-{dt.month:02d}"
        if chave not in meses:
            meses[chave] = {
                "mes": chave,
                "mes_label": _mes_label(dt.year, dt.month),
                "total_aulas": 0,
                "dias": {},
                "semanas": {},
                "unidades": {},
            }

        m = meses[chave]
        m["total_aulas"] += 1

        dia_key = dt.strftime("%Y-%m-%d")
        m["dias"][dia_key] = m["dias"].get(dia_key, 0) + 1

        semana_key = dt.strftime("%G-W%V")
        m["semanas"][semana_key] = m["semanas"].get(semana_key, 0) + 1

        unidade = _match_unidade(ev.get("local", ""), unidades)
        if unidade:
            uid = unidade["id"]
            nome = unidade.get("nome", uid)
            ref  = db.collection("unidades").document(uid)
        else:
            uid  = "__sem_unidade__"
            nome = "Sem unidade"
            ref  = None

        if uid not in m["unidades"]:
            m["unidades"][uid] = {"unidade": ref, "nome": nome, "quantidade": 0}
        m["unidades"][uid]["quantidade"] += 1

    resumos = {}
    for chave, m in meses.items():
        resumos[chave] = {
            "mes": chave,
            "mes_label": m["mes_label"],
            "total_aulas": m["total_aulas"],
            "dia_recorde": max(m["dias"].values(), default=0),
            "semana_recorde": max(m["semanas"].values(), default=0),
            "aulas_por_unidade": sorted(
                list(m["unidades"].values()),
                key=lambda x: x["quantidade"],
                reverse=True,
            ),
        }
    return resumos


# ── Cálculo dos resumos anuais ─────────────────────────────────────────────────

def _calcular_resumos_anuais(events: list[dict]) -> dict:
    from datetime import timezone as _tz
    agora = datetime.now(_tz.utc)
    anos: dict[int, dict] = {}

    for ev in events:
        try:
            dt_inicio = datetime.fromisoformat(ev["inicio"])
            dt_fim    = datetime.fromisoformat(ev["fim"]) if ev.get("fim") else None
        except Exception:
            continue

        # Normaliza para aware se necessário
        if dt_fim is not None and dt_fim.tzinfo is None:
            dt_fim = dt_fim.replace(tzinfo=_tz.utc)
        # Só conta aulas totalmente finalizadas (horário de fim anterior ao momento atual)
        if dt_fim is None or dt_fim > agora:
            continue

        ano = dt_inicio.year
        if ano not in anos:
            anos[ano] = {"total_aulas": 0, "dias": {}, "semanas": {}}

        a = anos[ano]
        a["total_aulas"] += 1

        dia_key = dt_inicio.strftime("%Y-%m-%d")
        a["dias"][dia_key] = a["dias"].get(dia_key, 0) + 1

        semana_key = dt_inicio.strftime("%G-W%V")
        a["semanas"][semana_key] = a["semanas"].get(semana_key, 0) + 1

    resumos = {}
    for ano, a in anos.items():
        resumos[ano] = {
            "ano": ano,
            "total_aulas": a["total_aulas"],
            "dia_recorde": max(a["dias"].values(), default=0),
            "semana_recorde": max(a["semanas"].values(), default=0),
        }
    return resumos


# ── Sync ───────────────────────────────────────────────────────────────────────

def sync_events(events: list[dict]) -> tuple[int, int]:
    db = _get_db()
    ultima_sync = datetime.now()

    unidades = get_unidades()
    resumos_m = _calcular_resumos(events, unidades, db)
    resumos_a = _calcular_resumos_anuais(events)

    # Diff de IDs para deletar eventos removidos
    ids_novos  = {ev["id"] for ev in events}
    ids_banco  = {doc.id for doc in db.collection("eventos").stream()}
    ids_deletar = ids_banco - ids_novos

    def commit_batch(ops):
        b = db.batch()
        for op in ops: op(b)
        b.commit()

    # Salva/atualiza eventos individuais
    ops = []
    for ev in events:
        ref  = db.collection("eventos").document(ev["id"])
        data = {**ev, "sincronizado_em": ultima_sync}
        ops.append(lambda b, r=ref, d=data: b.set(r, d))
        if len(ops) == 500:
            commit_batch(ops); ops = []
    if ops: commit_batch(ops)

    # Deleta removidos
    ops = []
    for eid in ids_deletar:
        ref = db.collection("eventos").document(eid)
        ops.append(lambda b, r=ref: b.delete(r))
        if len(ops) == 500:
            commit_batch(ops); ops = []
    if ops: commit_batch(ops)

    # Grava resumos mensais
    for chave, resumo in resumos_m.items():
        db.collection("resumos_mensais").document(chave).set({
            **resumo, "atualizado_em": ultima_sync,
        })
    meses_banco = {doc.id for doc in db.collection("resumos_mensais").stream()}
    for mes_antigo in meses_banco - set(resumos_m.keys()):
        db.collection("resumos_mensais").document(mes_antigo).delete()

    # Grava resumos anuais
    for ano, resumo in resumos_a.items():
        db.collection("resumos_anuais").document(str(ano)).set({
            **resumo, "atualizado_em": ultima_sync,
        })
    anos_banco = {doc.id for doc in db.collection("resumos_anuais").stream()}
    for ano_antigo in anos_banco - {str(a) for a in resumos_a.keys()}:
        db.collection("resumos_anuais").document(ano_antigo).delete()

    return len(events), len(resumos_m)


# ── Leituras do app ────────────────────────────────────────────────────────────

def get_events_by_month(year: int, month: int) -> list[dict]:
    db = _get_db()
    ultimo_dia = calendar.monthrange(year, month)[1]
    start = datetime(year, month, 1).isoformat()
    end   = datetime(year, month, ultimo_dia, 23, 59, 59).isoformat()
    docs  = (
        db.collection("eventos")
        .where("inicio", ">=", start)
        .where("inicio", "<=", end)
        .stream()
    )
    events = [doc.to_dict() for doc in docs]
    events.sort(key=lambda e: e.get("inicio", ""))
    return events


def get_resumos_mensais() -> list[dict]:
    db = _get_db()
    resumos = [doc.to_dict() for doc in db.collection("resumos_mensais").stream()]
    resumos.sort(key=lambda r: r.get("mes", ""))
    return resumos


def get_resumos_anuais() -> list[dict]:
    db = _get_db()
    resumos = [doc.to_dict() for doc in db.collection("resumos_anuais").stream()]
    resumos.sort(key=lambda r: r.get("ano", 0))
    return resumos


def get_ultima_sync() -> datetime | None:
    db = _get_db()
    docs = (
        db.collection("resumos_mensais")
        .order_by("atualizado_em", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    for doc in docs:
        return doc.to_dict().get("atualizado_em")
    return None