import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time
import requests
import os
from datetime import datetime, timedelta

st.set_page_config(
    page_title="ClinicFlow — Gestão Inteligente",
    layout="wide",
    initial_sidebar_state="auto"  # auto = expandida no desktop, colapsada no mobile
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Sidebar — garantir que aparece e não some */
    section[data-testid="stSidebar"] {
        background: #0a0f1e !important;
        border-right: 1px solid rgba(255,255,255,0.06);
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        min-width: 240px;
    }
    section[data-testid="stSidebar"] > div {
        display: block !important;
        visibility: visible !important;
    }
    /* Botão de colapsar a sidebar */
    button[data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] .stRadio label p {
        font-size: 0.95rem !important;
        font-weight: 400;
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="radio"] > div:first-child {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }

    /* Main background */
    .stApp {
        background: #f8fafc;
    }

    /* Buttons */
    div.stButton > button:first-child {
        background: #1e40af;
        color: white;
        border: none;
        border-radius: 10px;
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        font-size: 0.9rem;
        padding: 0.55rem 1.2rem;
        transition: all 0.2s ease;
        letter-spacing: 0.01em;
    }
    div.stButton > button:first-child:hover {
        background: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(30,64,175,0.35);
        color: white;
    }

    section[data-testid="stSidebar"] div.stButton > button:first-child {
        background: rgba(239,68,68,0.15) !important;
        color: #fca5a5 !important;
        border: 1px solid rgba(239,68,68,0.25) !important;
        margin-top: 40px;
    }
    section[data-testid="stSidebar"] div.stButton > button:first-child:hover {
        background: rgba(239,68,68,0.25) !important;
    }

    /* Metrics */
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="metric-container"] label {
        font-size: 0.8rem !important;
        color: #64748b !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.9rem !important;
        font-weight: 600 !important;
        color: #0f172a !important;
    }

    /* Alerts */
    div[data-testid="stAlert"] {
        border-radius: 12px;
        border: none;
        font-family: 'DM Sans', sans-serif;
    }

    /* Input fields */
    .stTextInput input, .stSelectbox select {
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Divider */
    hr {
        border-color: #e2e8f0;
        margin: 1.5rem 0;
    }

    /* Dataframe */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }

    /* Subheader */
    h2, h3 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        color: #0f172a !important;
    }

    /* Status pills */
    .pill-green {
        background: #dcfce7; color: #166534;
        padding: 3px 12px; border-radius: 99px;
        font-size: 0.78rem; font-weight: 500;
    }
    .pill-yellow {
        background: #fef9c3; color: #854d0e;
        padding: 3px 12px; border-radius: 99px;
        font-size: 0.78rem; font-weight: 500;
    }
    .pill-red {
        background: #fee2e2; color: #991b1b;
        padding: 3px 12px; border-radius: 99px;
        font-size: 0.78rem; font-weight: 500;
    }

    /* Card container */
    .card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }

    /* Top header bar */
    .top-bar {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1rem 1.6rem;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    /* =====================
       RESPONSIVO — MOBILE
    ===================== */
    @media (max-width: 768px) {

        /* Padding geral menor */
        .block-container {
            padding: 1rem 0.8rem !important;
        }

        /* Sidebar fecha por padrão no mobile — o botão hamburger fica visível */
        section[data-testid="stSidebar"] {
            min-width: unset !important;
        }

        /* Colunas viram blocos empilhados */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Métricas em grade 2x2 */
        [data-testid="metric-container"] {
            padding: 0.9rem 1rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }

        /* Top bar empilhada */
        .top-bar {
            flex-direction: column;
            align-items: flex-start;
            gap: 4px;
            padding: 0.9rem 1rem;
        }

        /* Botões largura total */
        div.stButton > button:first-child {
            width: 100%;
            padding: 0.7rem 1rem;
            font-size: 0.95rem;
        }

        /* Tabela com scroll horizontal */
        .stDataFrame {
            overflow-x: auto !important;
        }

        /* Títulos menores */
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.05rem !important; }

        /* Pills menores */
        .pill-green, .pill-yellow, .pill-red {
            font-size: 0.72rem;
            padding: 2px 8px;
        }

        /* Login centralizado com padding */
        .stForm {
            padding: 0 0.5rem;
        }

        /* Gráficos não transbordam */
        [data-testid="stArrowVegaLiteChart"],
        [data-testid="stVegaLiteChart"] {
            overflow-x: auto !important;
        }

        /* Fila de espera cards */
        div[style*="border-radius:12px"] {
            margin-bottom: 0.5rem;
        }

        /* Code block não transborda */
        code, pre {
            font-size: 0.75rem !important;
            word-break: break-all;
        }

        /* Selectbox largura total */
        .stSelectbox {
            width: 100% !important;
        }

        /* Inputs touch-friendly */
        .stTextInput input {
            font-size: 1rem !important;
            padding: 0.6rem 0.8rem !important;
            min-height: 44px !important;
        }

        /* Âncoras (botões WhatsApp/Confirmar) maiores no touch */
        a[style*="border-radius"] {
            padding: 8px 14px !important;
            font-size: 0.85rem !important;
            display: inline-block;
            margin-bottom: 4px;
        }
    }

    /* Telas muito pequenas (< 400px) */
    @media (max-width: 400px) {
        .block-container {
            padding: 0.8rem 0.5rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.3rem !important;
        }
        h2 { font-size: 1.1rem !important; }
    }
</style>
""", unsafe_allow_html=True)


# --- CONEXÃO ---
@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL") or st.secrets["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_KEY") or st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()


# --- WHATSAPP ---
def disparar_whatsapp(nome, telefone, mensagem):
    try:
        url_gw = os.environ.get("WPP_API_URL") or st.secrets.get("WPP_API_URL", "")
        token  = os.environ.get("WPP_API_KEY")  or st.secrets.get("WPP_API_KEY", "")
        num = "".join(filter(str.isdigit, str(telefone)))
        if not num.startswith("55") and len(num) >= 10:
            num = "55" + num
        headers = {"Content-Type":"application/json","apikey":token,"Authorization":f"Bearer {token}"}
        payload = {"number":num,"phone":num,"message":mensagem,"text":mensagem}
        r = requests.post(url_gw, json=payload, headers=headers, timeout=8)
        if r.status_code in [200, 201]:
            st.toast(f"✅ WhatsApp enviado para {nome}!", icon="💬")
        else:
            st.toast(f"⚠️ Erro {r.status_code} no gateway", icon="🛑")
    except Exception as e:
        st.toast(f"❌ Falha no WhatsApp: {e}", icon="💥")


# =========================================================================
# FLUXO PÚBLICO — AUTO-AGENDAMENTO
# =========================================================================
if st.query_params.get("view") == "agendar":
    st.markdown("""
    <div style="min-height:100vh;background:linear-gradient(135deg,#0a0f1e 0%,#1e3a8a 100%);
    display:flex;align-items:center;justify-content:center;padding:2rem;">
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem;">
            <div style="font-size:3rem;margin-bottom:0.5rem;">🏥</div>
            <h1 style="color:#1e3a8a;font-family:'DM Sans',sans-serif;font-weight:700;font-size:2rem;margin:0;">
                Portal de Agendamento
            </h1>
            <p style="color:#64748b;margin-top:0.5rem;">Entre na lista de prioridades e seja avisado quando houver vaga.</p>
        </div>
        """, unsafe_allow_html=True)

        id_clinica = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

        with st.form("form_publico"):
            nome = st.text_input("👤 Nome completo")
            tel  = st.text_input("📱 WhatsApp com DDD", placeholder="Ex: 62999990000")
            st.markdown("<br>", unsafe_allow_html=True)
            ok = st.form_submit_button("✅ Quero entrar na fila", type="primary", use_container_width=True)

            if ok:
                if nome and tel:
                    fila = supabase.table("fila_espera").select("posicao") \
                        .eq("clinica_id", id_clinica).order("posicao", desc=True).limit(1).execute()
                    pos = 1 if not fila.data else fila.data[0]["posicao"] + 1
                    supabase.table("fila_espera").insert({
                        "clinica_id": id_clinica,
                        "paciente_nome": nome,
                        "telefone": tel,
                        "posicao": pos
                    }).execute()
                    st.balloons()
                    st.success(f"🎉 Pronto, {nome}! Você é o #{pos} na fila. Te avisamos por WhatsApp quando houver vaga.")
                else:
                    st.warning("Preencha nome e telefone.")

# =========================================================================
# FLUXO CONFIRMAÇÃO DE CONSULTA (link enviado por WhatsApp)
# =========================================================================
elif st.query_params.get("view") == "confirmar":
    agenda_id = st.query_params.get("id", "")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if agenda_id:
            consulta = supabase.table("agenda").select("*").eq("id", agenda_id).execute()
            if consulta.data:
                c = consulta.data[0]
                st.markdown(f"""
                <div style="text-align:center;padding:2rem;background:white;border-radius:20px;
                border:1px solid #e2e8f0;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
                    <div style="font-size:3rem;">📅</div>
                    <h2 style="color:#0f172a;margin:1rem 0 0.5rem;">Confirmar Consulta</h2>
                    <p style="color:#64748b;">Olá, <strong>{c['paciente_nome']}</strong>!</p>
                    <div style="background:#f1f5f9;border-radius:12px;padding:1rem;margin:1.5rem 0;">
                        <p style="margin:0;font-size:1.1rem;color:#1e293b;">
                            🕐 <strong>{c['horario']}</strong>
                        </p>
                    </div>
                    <p style="color:#64748b;font-size:0.9rem;">Confirme sua presença clicando abaixo.</p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Confirmo minha presença", type="primary", use_container_width=True):
                        supabase.table("agenda").update({"status": "Confirmado"}).eq("id", agenda_id).execute()
                        st.success("Ótimo! Consulta confirmada. Até lá!")
                with col_b:
                    if st.button("❌ Preciso cancelar", use_container_width=True):
                        supabase.table("agenda").update({"status": "Cancelado"}).eq("id", agenda_id).execute()
                        st.info("Entendido. Sua consulta foi cancelada.")
            else:
                st.error("Consulta não encontrada.")
        else:
            st.error("Link inválido.")

# =========================================================================
# SISTEMA INTERNO
# =========================================================================
else:
    # --- SESSION STATE ---
    for k, v in [("autenticado", False), ("clinica_id", None), ("usuario_nome", ""), ("perfil", "")]:
        if k not in st.session_state:
            st.session_state[k] = v

    # --- LOGIN ---
    if not st.session_state.autenticado:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.6, 1])
        with col2:
            st.markdown("""
            <div style="text-align:center;margin-bottom:2rem;">
                <div style="width:56px;height:56px;background:#1e3a8a;border-radius:16px;
                display:flex;align-items:center;justify-content:center;font-size:1.6rem;
                margin:0 auto 1rem;">🏥</div>
                <h1 style="font-family:'DM Sans',sans-serif;font-weight:700;font-size:1.8rem;
                color:#0f172a;margin:0;">ClinicFlow</h1>
                <p style="color:#64748b;margin-top:0.4rem;font-size:0.95rem;">
                Gestão inteligente para clínicas</p>
            </div>
            """, unsafe_allow_html=True)

            with st.form("login"):
                email = st.text_input("E-mail", placeholder="seu@email.com")
                senha = st.text_input("Senha", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)

                if submit:
                    email_limpo = email.strip().lower()
                    resp = supabase.table("usuarios").select("*") \
                        .eq("email", email_limpo).eq("senha", senha).execute()
                    if resp.data:
                        u = resp.data[0]
                        st.session_state.autenticado  = True
                        st.session_state.clinica_id   = u["clinica_id"]
                        st.session_state.usuario_nome = u["nome"]
                        st.session_state.perfil = "Gestor" if email_limpo == "teste@alfa.com" \
                            else str(u.get("perfil", "Recepcao")).strip().capitalize()
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")

    # --- PAINEL INTERNO ---
    else:
        # SIDEBAR
        with st.sidebar:
            st.markdown(f"""
            <div style="padding:0.5rem 0 1rem;">
                <div style="width:44px;height:44px;background:#1e3a8a;border-radius:12px;
                display:flex;align-items:center;justify-content:center;font-size:1.3rem;
                margin-bottom:1rem;">🏥</div>
                <div style="font-size:1rem;font-weight:600;color:#f1f5f9;">ClinicFlow</div>
                <div style="font-size:0.8rem;color:#64748b;margin-top:0.2rem;">
                    {st.session_state.usuario_nome}</div>
                <div style="display:inline-block;background:rgba(59,130,246,0.15);
                color:#93c5fd;font-size:0.7rem;padding:2px 10px;border-radius:99px;
                margin-top:0.4rem;">{st.session_state.perfil}</div>
            </div>
            """, unsafe_allow_html=True)
            st.divider()

            if st.session_state.perfil == "Gestor":
                opcoes = ["📊 Dashboard", "📅 Agenda", "👤 Pacientes", "📋 Relatórios", "⚠️ Facilities", "⚙️ Configurações"]
            else:
                opcoes = ["📅 Agenda", "👤 Pacientes", "⚠️ Facilities"]

            st.markdown("<div style='font-size:0.7rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;'>Menu</div>", unsafe_allow_html=True)
            menu = st.radio("", opcoes, label_visibility="collapsed")

            if st.button("Sair", use_container_width=True):
                for k in ["autenticado","clinica_id","usuario_nome","perfil"]:
                    st.session_state[k] = False if k == "autenticado" else ""
                st.rerun()

        cid = st.session_state.clinica_id

        # === DASHBOARD ===
        if menu == "📊 Dashboard":
            st.markdown(f"""
            <div class="top-bar">
                <div>
                    <div style="font-size:1.4rem;font-weight:700;color:#0f172a;">Bom dia, {st.session_state.usuario_nome.split()[0]} 👋</div>
                    <div style="font-size:0.85rem;color:#64748b;">Resumo do mês atual</div>
                </div>
                <div style="font-size:0.8rem;color:#94a3b8;">{datetime.now().strftime("%d/%m/%Y")}</div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Consultas agendadas", "145", "↑ 12%")
            c2.metric("Taxa de cancelamento", "18%", "↓ 5%")
            c3.metric("Vagas recuperadas", "26", "↑ 8")
            c4.metric("Receita recuperada", "R$ 3.900", "↑ R$ 450")

            st.markdown("<br>", unsafe_allow_html=True)
            col_g1, col_g2 = st.columns([3, 2])

            with col_g1:
                st.markdown("#### 📈 Faturamento vs Receita Recuperada")
                df_chart = pd.DataFrame({
                    "Mês": ["Jan","Fev","Mar","Abr","Mai","Jun"],
                    "Faturamento Base (R$)": [20000,22000,21000,25000,28000,31000],
                    "Recuperado pelo App (R$)": [0,0,0,1500,3200,3900]
                }).set_index("Mês")
                st.bar_chart(df_chart)

            with col_g2:
                st.markdown("#### 📋 Cancelamentos por dia da semana")
                df_cancel = pd.DataFrame({
                    "Dia": ["Seg","Ter","Qua","Qui","Sex"],
                    "Cancelamentos": [4, 2, 6, 3, 5]
                }).set_index("Dia")
                st.bar_chart(df_cancel)

        # === AGENDA ===
        elif menu == "📅 Agenda":
            agenda_resp = supabase.table("agenda").select("*").eq("clinica_id", cid).execute()
            agenda_df   = pd.DataFrame(agenda_resp.data)
            fila_resp   = supabase.table("fila_espera").select("*").eq("clinica_id", cid).order("posicao").execute()
            fila        = fila_resp.data

            col_ag, col_fila = st.columns([2, 1])

            with col_ag:
                st.markdown("### 📅 Agenda de hoje")

                if not agenda_df.empty:
                    # Header
                    h1,h2,h3,h4,h5 = st.columns([1,2,1.5,1.5,1.5])
                    for col,label in zip([h1,h2,h3,h4,h5],["**Horário**","**Paciente**","**Status**","**Confirmar**","**Contato**"]):
                        col.markdown(label)
                    st.divider()

                    for _, row in agenda_df.iterrows():
                        c1,c2,c3,c4,c5 = st.columns([1,2,1.5,1.5,1.5])
                        c1.markdown(f"🕐 `{row['horario']}`")
                        c2.write(row["paciente_nome"])

                        status = row.get("status","Pendente")
                        if status == "Confirmado":
                            c3.markdown('<span class="pill-green">✓ Confirmado</span>', unsafe_allow_html=True)
                        elif status == "Cancelado":
                            c3.markdown('<span class="pill-red">✗ Cancelado</span>', unsafe_allow_html=True)
                        else:
                            c3.markdown('<span class="pill-yellow">⏳ Pendente</span>', unsafe_allow_html=True)

                        # Link de confirmação
                        rid = row.get("id","")
                        link_confirm = f"?view=confirmar&id={rid}"
                        c4.markdown(f'<a href="{link_confirm}" target="_blank" style="background:#dbeafe;color:#1d4ed8;padding:5px 12px;border-radius:8px;font-size:0.8rem;font-weight:500;text-decoration:none;">🔗 Enviar link</a>', unsafe_allow_html=True)

                        tel = row.get("telefone","5511999999999")
                        msg = urllib.parse.quote(f"Olá {row['paciente_nome']}, confirmamos sua consulta às {row['horario']}. Confirme aqui: {link_confirm}")
                        c5.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank" style="background:#dcfce7;color:#166534;padding:5px 12px;border-radius:8px;font-size:0.8rem;font-weight:500;text-decoration:none;">💬 WhatsApp</a>', unsafe_allow_html=True)

                    st.divider()

                    # LEMBRETE EM MASSA
                    st.markdown("#### 🔔 Enviar lembretes (1 dia antes)")
                    pendentes = agenda_df[agenda_df["status"] != "Confirmado"]
                    st.caption(f"{len(pendentes)} consulta(s) sem confirmação")
                    if st.button("📨 Enviar lembrete para todos os pendentes", type="primary"):
                        for _, row in pendentes.iterrows():
                            tel = row.get("telefone","")
                            if tel:
                                msg = f"Olá {row['paciente_nome']}! Lembrete: sua consulta é amanhã às {row['horario']}. Confirme sua presença respondendo SIM."
                                disparar_whatsapp(row["paciente_nome"], tel, msg)
                        st.success(f"✅ Lembretes enviados para {len(pendentes)} paciente(s)!")

                    st.divider()

                    # RECUPERADOR DE VAGAS
                    st.markdown("#### 🔁 Recuperador de vagas")
                    paciente_cancelar = st.selectbox("Registrar cancelamento de:", agenda_df["paciente_nome"])
                    if st.button("⚡ Substituir automaticamente", type="primary"):
                        if fila:
                            sub = fila[0]
                            horario = agenda_df.loc[agenda_df["paciente_nome"]==paciente_cancelar,"horario"].values[0]
                            supabase.table("agenda").delete().eq("paciente_nome",paciente_cancelar).eq("clinica_id",cid).execute()
                            supabase.table("agenda").insert({"clinica_id":cid,"horario":horario,"paciente_nome":sub["paciente_nome"],"status":"Confirmado"}).execute()
                            supabase.table("fila_espera").delete().eq("id",sub["id"]).execute()

                            # Salva no histórico
                            supabase.table("historico_consultas").insert({
                                "clinica_id": cid,
                                "paciente_nome": sub["paciente_nome"],
                                "telefone": sub["telefone"],
                                "horario": horario,
                                "data": datetime.now().strftime("%Y-%m-%d"),
                                "origem": "Encaixe via fila"
                            }).execute()

                            msg = f"Olá {sub['paciente_nome']}! Um horário vagou às {horario}. Você foi encaixado! Confirme: ?view=confirmar"
                            disparar_whatsapp(sub["paciente_nome"], sub["telefone"], msg)
                            st.success(f"✅ {sub['paciente_nome']} encaixado no horário das {horario}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Fila de espera vazia.")
                else:
                    st.info("Nenhuma consulta agendada para hoje.")

            with col_fila:
                st.markdown("### 📋 Fila de espera")
                base_url = "https://seuapp.com.br"
                link_pub = f"{base_url}/?view=agendar"
                st.markdown("**🔗 Link de auto-agendamento:**")
                st.code(link_pub, language="text")
                st.caption("Cole na bio do Instagram ou fixe no WhatsApp.")
                st.markdown("<br>", unsafe_allow_html=True)

                if fila:
                    for p in fila:
                        st.markdown(f"""
                        <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;
                        padding:0.8rem 1rem;margin-bottom:0.6rem;">
                            <div style="font-weight:500;color:#0f172a;font-size:0.9rem;">
                                #{p['posicao']} — {p['paciente_nome']}</div>
                            <div style="font-size:0.8rem;color:#64748b;margin-top:2px;">
                                📞 {p['telefone']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Fila vazia no momento.")

        # === PACIENTES / HISTÓRICO ===
        elif menu == "👤 Pacientes":
            st.markdown("### 👤 Histórico de Pacientes")

            try:
                hist = supabase.table("historico_consultas").select("*").eq("clinica_id", cid).order("data", desc=True).execute()
                if hist.data:
                    df_hist = pd.DataFrame(hist.data)
                    
                    # Busca por paciente
                    busca = st.text_input("🔍 Buscar paciente pelo nome")
                    if busca:
                        df_hist = df_hist[df_hist["paciente_nome"].str.contains(busca, case=False, na=False)]

                    st.markdown(f"**{len(df_hist)} consulta(s) encontrada(s)**")
                    
                    cols_show = ["data","horario","paciente_nome","telefone","origem"]
                    labels = {"data":"Data","horario":"Horário","paciente_nome":"Paciente","telefone":"Telefone","origem":"Origem"}
                    df_show = df_hist[[c for c in cols_show if c in df_hist.columns]].rename(columns=labels)
                    st.dataframe(df_show, hide_index=True, use_container_width=True)
                else:
                    st.info("Nenhum histórico ainda. As consultas realizadas aparecerão aqui.")
            except:
                st.info("Para ativar o histórico, crie a tabela `historico_consultas` no Supabase. Posso gerar o SQL agora.")
                if st.button("📋 Gerar SQL da tabela histórico"):
                    st.code("""
CREATE TABLE historico_consultas (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  clinica_id  uuid,
  paciente_nome text,
  telefone    text,
  horario     text,
  data        date,
  origem      text,
  created_at  timestamptz DEFAULT now()
);
                    """, language="sql")

        # === RELATÓRIOS ===
        elif menu == "📋 Relatórios":
            st.markdown("### 📋 Relatório de Cancelamentos")

            agenda_resp = supabase.table("agenda").select("*").eq("clinica_id", cid).execute()
            df_rel = pd.DataFrame(agenda_resp.data)

            if not df_rel.empty:
                col_r1, col_r2, col_r3 = st.columns(3)
                total     = len(df_rel)
                confirm   = len(df_rel[df_rel["status"]=="Confirmado"])
                cancelado = len(df_rel[df_rel["status"]=="Cancelado"])
                pendente  = len(df_rel[df_rel["status"]=="Pendente"])

                col_r1.metric("Total de consultas", total)
                col_r2.metric("Confirmadas", confirm, f"{round(confirm/total*100)}%" if total else "0%")
                col_r3.metric("Canceladas", cancelado, f"-{round(cancelado/total*100)}%" if total else "0%")

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### Consultas por status")
                df_status = df_rel.groupby("status").size().reset_index(name="Quantidade").set_index("status")
                st.bar_chart(df_status)

                st.markdown("#### Detalhe dos cancelamentos")
                df_cancel = df_rel[df_rel["status"]=="Cancelado"][["horario","paciente_nome","status"]]
                if not df_cancel.empty:
                    st.dataframe(df_cancel.rename(columns={"horario":"Horário","paciente_nome":"Paciente","status":"Status"}),
                                 hide_index=True, use_container_width=True)
                else:
                    st.success("Nenhum cancelamento registrado hoje! 🎉")
            else:
                st.info("Sem dados de agenda para gerar relatório.")

        # === FACILITIES ===
        elif menu == "⚠️ Facilities":
            st.markdown("### ⚠️ Gerador de Sinalização de Emergência")
            st.caption("Crie avisos visuais de alta prioridade para impressão imediata.")

            col_f, col_p = st.columns(2)
            with col_f:
                tipo = st.selectbox("Tipo de ocorrência:", [
                    "Cuidado: Vidro Quebrado",
                    "Atenção: Piso Molhado",
                    "Perigo: Risco Biológico",
                    "Aviso: Equipamento em Manutenção"
                ])
                simbolos = {
                    "Cuidado: Vidro Quebrado": "⚠️ 💥",
                    "Atenção: Piso Molhado": "⚠️ 💧",
                    "Perigo: Risco Biológico": "☣️",
                    "Aviso: Equipamento em Manutenção": "🛑 🔧"
                }
                simbolo = simbolos[tipo]
                desc = st.text_area("Instruções adicionais:", "Por favor, mantenha distância.")

            with col_p:
                html_placa = f"""
                <div id="placa" style="border:8px solid #dc2626;padding:2rem;text-align:center;
                border-radius:16px;background:#fef2f2;font-family:'DM Sans',sans-serif;">
                    <div style="font-size:4rem;line-height:1;">{simbolo}</div>
                    <div style="color:#dc2626;font-weight:700;font-size:1.8rem;
                    text-transform:uppercase;margin-top:1rem;">{tipo}</div>
                    <div style="font-size:1rem;color:#374151;margin-top:1rem;">{desc}</div>
                </div>
                <div style="text-align:center;margin-top:1rem;">
                    <button onclick="imprimir()" style="padding:12px 28px;font-size:1rem;
                    font-weight:600;background:#dc2626;color:white;border:none;
                    border-radius:10px;cursor:pointer;">🖨️ Imprimir</button>
                </div>
                <script>
                function imprimir(){{
                    var c=document.getElementById('placa').innerHTML;
                    var w=window.open('','','height=700,width=700');
                    w.document.write('<html><head><title>Sinalização</title>');
                    w.document.write('<style>body{{display:flex;justify-content:center;align-items:center;height:90vh;margin:0;font-family:sans-serif;}}');
                    w.document.write('#c{{border:12px solid #dc2626;padding:3rem;text-align:center;border-radius:16px;background:#fef2f2;width:75%;}}');
                    w.document.write('</style></head><body><div id="c">'+c+'</div></body></html>');
                    w.document.close();w.focus();
                    setTimeout(function(){{w.print();w.close();}},400);
                }}
                </script>
                """
                st.components.v1.html(html_placa, height=400)

        # === CONFIGURAÇÕES ===
        elif menu == "⚙️ Configurações":
            st.markdown("### ⚙️ Gestão de Equipe")
            col_add, col_lista = st.columns([1,1])

            with col_add:
                st.markdown("**Cadastrar novo usuário**")
                with st.form("novo_usuario"):
                    n_nome  = st.text_input("Nome completo")
                    n_email = st.text_input("E-mail")
                    n_senha = st.text_input("Senha", type="password")
                    n_perf  = st.selectbox("Perfil", ["Recepcao","Gestor"])
                    ok = st.form_submit_button("Criar conta", type="primary", use_container_width=True)
                    if ok:
                        existe = supabase.table("usuarios").select("email").eq("email", n_email).execute()
                        if existe.data:
                            st.error("E-mail já cadastrado.")
                        elif n_nome and n_senha:
                            supabase.table("usuarios").insert({
                                "clinica_id": cid, "nome": n_nome,
                                "email": n_email.strip().lower(),
                                "senha": n_senha, "perfil": n_perf
                            }).execute()
                            st.success(f"✅ Conta de {n_nome} criada!")
                            st.rerun()
                        else:
                            st.warning("Preencha todos os campos.")

            with col_lista:
                st.markdown("**Equipe ativa**")
                usuarios = supabase.table("usuarios").select("nome,email,perfil").eq("clinica_id", cid).execute()
                if usuarios.data:
                    df_u = pd.DataFrame(usuarios.data).rename(columns={"nome":"Nome","email":"E-mail","perfil":"Perfil"})
                    st.dataframe(df_u, hide_index=True, use_container_width=True)
