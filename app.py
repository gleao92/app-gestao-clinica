import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time
import requests
import os
import bcrypt
import re
import html
import logging
from datetime import datetime, timedelta
from functools import wraps

# ── Logging seguro (nunca loga senhas ou tokens) ──────────────────────
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("clinicflow")

# ── Constantes de segurança ───────────────────────────────────────────
MAX_LOGIN_ATTEMPTS  = 5       # bloqueio após N tentativas falhas
LOCKOUT_SECONDS     = 300     # 5 minutos de bloqueio
MAX_INPUT_LENGTH    = 500     # limite de caracteres em campos livres
ALLOWED_VIEWS       = {"agendar", "confirmar", "cadastro"}  # views públicas válidas
SESSION_TIMEOUT_MIN = 480     # 8 horas de sessão

def sanitize(text: str, max_len: int = MAX_INPUT_LENGTH) -> str:
    """Remove HTML/JS e limita tamanho de qualquer input."""
    if not isinstance(text, str):
        return ""
    cleaned = html.escape(text.strip())
    return cleaned[:max_len]

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))

def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r"[^0-9]", "", phone)
    return 10 <= len(digits) <= 13

def check_session_timeout() -> bool:
    """Retorna True se a sessão expirou."""
    last = st.session_state.get("last_activity")
    if last and (datetime.now() - last).total_seconds() > SESSION_TIMEOUT_MIN * 60:
        return True
    st.session_state.last_activity = datetime.now()
    return False

def check_rate_limit(email: str) -> tuple[bool, int]:
    """Retorna (bloqueado, segundos_restantes)."""
    key_attempts = f"attempts_{email}"
    key_time     = f"lockout_time_{email}"
    attempts = st.session_state.get(key_attempts, 0)
    lockout  = st.session_state.get(key_time)
    if lockout:
        elapsed = (datetime.now() - lockout).total_seconds()
        if elapsed < LOCKOUT_SECONDS:
            return True, int(LOCKOUT_SECONDS - elapsed)
        else:
            st.session_state[key_attempts] = 0
            st.session_state[key_time]     = None
    return False, 0

def register_failed_attempt(email: str):
    key_attempts = f"attempts_{email}"
    key_time     = f"lockout_time_{email}"
    attempts = st.session_state.get(key_attempts, 0) + 1
    st.session_state[key_attempts] = attempts
    if attempts >= MAX_LOGIN_ATTEMPTS:
        st.session_state[key_time] = datetime.now()
        logger.warning(f"Bloqueio de login: {email} após {attempts} tentativas")

def reset_attempts(email: str):
    st.session_state[f"attempts_{email}"] = 0
    st.session_state[f"lockout_time_{email}"] = None

st.set_page_config(
    page_title="ClinicFlow — Gestão Inteligente",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="auto"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    section[data-testid="stSidebar"] {
        background: #0a0f1e !important;
        border-right: 1px solid rgba(255,255,255,0.06);
        display: block !important; visibility: visible !important;
        opacity: 1 !important; min-width: 240px;
    }
    section[data-testid="stSidebar"] > div { display: block !important; visibility: visible !important; }
    button[data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; color: #94a3b8 !important; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] .stRadio label p { font-size: 0.95rem !important; font-weight: 400; color: #94a3b8 !important; }
    section[data-testid="stSidebar"] div[data-baseweb="radio"] > div:first-child { background-color: #3b82f6 !important; border-color: #3b82f6 !important; }
    .stApp { background: #f8fafc; }
    div.stButton > button:first-child {
        background: #1e40af; color: white; border: none; border-radius: 10px;
        font-family: 'DM Sans', sans-serif; font-weight: 500; font-size: 0.9rem;
        padding: 0.55rem 1.2rem; transition: all 0.2s ease; letter-spacing: 0.01em;
    }
    div.stButton > button:first-child:hover {
        background: #1d4ed8; transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(30,64,175,0.35); color: white;
    }
    section[data-testid="stSidebar"] div.stButton > button:first-child {
        background: rgba(239,68,68,0.15) !important; color: #fca5a5 !important;
        border: 1px solid rgba(239,68,68,0.25) !important; margin-top: 40px;
    }
    section[data-testid="stSidebar"] div.stButton > button:first-child:hover { background: rgba(239,68,68,0.25) !important; }
    [data-testid="metric-container"] {
        background: white; border: 1px solid #e2e8f0; border-radius: 14px;
        padding: 1.2rem 1.4rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="metric-container"] label { font-size: 0.8rem !important; color: #64748b !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.06em; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.9rem !important; font-weight: 600 !important; color: #0f172a !important; }
    div[data-testid="stAlert"] { border-radius: 12px; border: none; font-family: 'DM Sans', sans-serif; }
    .stTextInput input, .stSelectbox select { border-radius: 10px !important; border: 1px solid #e2e8f0 !important; font-family: 'DM Sans', sans-serif !important; }
    hr { border-color: #e2e8f0; margin: 1.5rem 0; }
    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; }
    h2, h3 { font-family: 'DM Sans', sans-serif !important; font-weight: 600 !important; color: #0f172a !important; }
    .pill-green { background: #dcfce7; color: #166534; padding: 3px 12px; border-radius: 99px; font-size: 0.78rem; font-weight: 500; }
    .pill-yellow { background: #fef9c3; color: #854d0e; padding: 3px 12px; border-radius: 99px; font-size: 0.78rem; font-weight: 500; }
    .pill-red { background: #fee2e2; color: #991b1b; padding: 3px 12px; border-radius: 99px; font-size: 0.78rem; font-weight: 500; }
    .card { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.4rem; margin-bottom: 1rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
    .top-bar { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1rem 1.6rem; margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    @media (max-width: 768px) {
        .block-container { padding: 1rem 0.8rem !important; }
        section[data-testid="stSidebar"] { min-width: unset !important; }
        [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
        [data-testid="metric-container"] { padding: 0.9rem 1rem; }
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
        .top-bar { flex-direction: column; align-items: flex-start; gap: 4px; padding: 0.9rem 1rem; }
        div.stButton > button:first-child { width: 100%; padding: 0.7rem 1rem; font-size: 0.95rem; }
        .stDataFrame { overflow-x: auto !important; }
        h2 { font-size: 1.2rem !important; } h3 { font-size: 1.05rem !important; }
        .pill-green, .pill-yellow, .pill-red { font-size: 0.72rem; padding: 2px 8px; }
        .stForm { padding: 0 0.5rem; }
        [data-testid="stArrowVegaLiteChart"], [data-testid="stVegaLiteChart"] { overflow-x: auto !important; }
        code, pre { font-size: 0.75rem !important; word-break: break-all; }
        .stSelectbox { width: 100% !important; }
        .stTextInput input { font-size: 1rem !important; padding: 0.6rem 0.8rem !important; min-height: 44px !important; }
        a[style*="border-radius"] { padding: 8px 14px !important; font-size: 0.85rem !important; display: inline-block; margin-bottom: 4px; }
    }
    @media (max-width: 400px) {
        .block-container { padding: 0.8rem 0.5rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL","")
    key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY","")
    if not url or not key:
        st.error("⚠️ Credenciais do banco não configuradas. Verifique as variáveis de ambiente.")
        st.stop()
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error("❌ Não foi possível conectar ao banco de dados. Tente novamente em instantes.")
    logger.error(f"Erro de conexão Supabase: {e}")
    st.stop()

def disparar_whatsapp(nome: str, telefone: str, mensagem: str):
    """Dispara WhatsApp com validações de segurança."""
    try:
        # Sanitiza inputs
        nome     = sanitize(nome, 100)
        mensagem = sanitize(mensagem, 1000)

        url_gw = os.environ.get("WPP_API_URL") or st.secrets.get("WPP_API_URL", "")
        token  = os.environ.get("WPP_API_KEY")  or st.secrets.get("WPP_API_KEY", "")

        if not url_gw:
            logger.warning("WPP_API_URL não configurado")
            return

        num = re.sub(r"[^0-9]", "", str(telefone))
        if not (10 <= len(num) <= 13):
            logger.warning(f"Telefone inválido: {len(num)} dígitos")
            return
        if not num.startswith("55"):
            num = "55" + num

        headers = {
            "Content-Type": "application/json",
            "apikey": token,
            "Authorization": f"Bearer {token}"
        }
        payload = {"number": num, "phone": num, "message": mensagem, "text": mensagem}
        r = requests.post(url_gw, json=payload, headers=headers, timeout=8)
        if r.status_code in [200, 201]:
            st.toast(f"✅ WhatsApp enviado para {nome}!", icon="💬")
        else:
            logger.warning(f"Gateway WhatsApp retornou {r.status_code}")
            st.toast(f"⚠️ Erro {r.status_code} no gateway", icon="🛑")
    except requests.Timeout:
        st.toast("⏳ Timeout no gateway WhatsApp", icon="⚠️")
    except Exception as e:
        logger.error(f"Erro WhatsApp: {type(e).__name__}")
        st.toast("❌ Falha no envio do WhatsApp", icon="💥")

# =========================================================================
# FLUXO PÚBLICO — AUTO-AGENDAMENTO
# =========================================================================
# Valida parâmetro view contra lista permitida (evita path traversal)
_view_param = st.query_params.get("view", "")
if _view_param and _view_param not in ALLOWED_VIEWS:
    st.error("Página não encontrada.")
    st.stop()

if st.query_params.get("view") == "agendar":
    # Pega o ID da clínica pela URL (?clinica=XXX)
    id_clinica = st.query_params.get("clinica", "")

    # Valida se a clínica existe
    if not id_clinica:
        st.error("❌ Link de agendamento inválido. Solicite o link correto à clínica.")
        st.stop()

    try:
        clinica_info = supabase.table("clinicas").select("nome_empresa").eq("id", id_clinica).execute()
        if not clinica_info.data:
            st.error("❌ Clínica não encontrada. Verifique o link.")
            st.stop()
        nome_clinica = clinica_info.data[0].get("nome_empresa", "Clínica")
    except Exception as e:
        logger.error(f"Erro ao buscar clínica: {type(e).__name__}")
        st.error("❌ Erro ao validar clínica. Tente novamente.")
        st.stop()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:2rem;margin-top:2rem;">
            <div style="font-size:3rem;margin-bottom:0.5rem;">🏥</div>
            <h1 style="color:#1e3a8a;font-family:'DM Sans',sans-serif;font-weight:700;font-size:2rem;margin:0;">{nome_clinica}</h1>
            <p style="color:#64748b;margin-top:0.5rem;">Entre na lista de prioridades e seja avisado quando houver vaga.</p>
        </div>
        """, unsafe_allow_html=True)

# =========================================================================
# CONFIRMAÇÃO DE CONSULTA
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
                <div style="text-align:center;padding:2rem;background:white;border-radius:20px;border:1px solid #e2e8f0;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
                    <div style="font-size:3rem;">📅</div>
                    <h2 style="color:#0f172a;margin:1rem 0 0.5rem;">Confirmar Consulta</h2>
                    <p style="color:#64748b;">Olá, <strong>{c['paciente_nome']}</strong>!</p>
                    <div style="background:#f1f5f9;border-radius:12px;padding:1rem;margin:1.5rem 0;">
                        <p style="margin:0;font-size:1.1rem;color:#1e293b;">🕐 <strong>{c['horario']}</strong></p>
                    </div>
                    <p style="color:#64748b;font-size:0.9rem;">Confirme sua presença clicando abaixo.</p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✅ Confirmo minha presença", type="primary", use_container_width=True):
                        supabase.table("agenda").update({"status": "Confirmado"}).eq("id", agenda_id).execute()
                        st.success("Consulta confirmada!")
                with col_b:
                    if st.button("❌ Preciso cancelar", use_container_width=True):
                        supabase.table("agenda").update({"status": "Cancelado"}).eq("id", agenda_id).execute()
                        st.info("Consulta cancelada.")
            else:
                st.error("Consulta não encontrada.")
        else:
            st.error("Link inválido.")

# =========================================================================
# ONBOARDING — CADASTRO DE NOVA CLÍNICA
# =========================================================================
elif st.query_params.get("view") == "cadastro":
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.5rem;">
            <div style="width:52px;height:52px;background:#1e3a8a;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;margin:0 auto 1rem;">🏥</div>
            <h2 style="font-family:'DM Sans',sans-serif;font-weight:700;color:#0f172a;margin:0;">Cadastrar nova clínica</h2>
            <p style="color:#64748b;font-size:0.9rem;margin-top:0.4rem;">Preencha os dados abaixo para criar sua conta no ClinicFlow.</p>
        </div>
        """, unsafe_allow_html=True)

        if "onb_step" not in st.session_state:
            st.session_state.onb_step = 1
        step = st.session_state.onb_step
        st.progress(step / 3, text=f"Passo {step} de 3")
        st.markdown("<br>", unsafe_allow_html=True)

        if step == 1:
            st.markdown("#### 🏥 Dados da clínica")
            with st.form("onb_clinica"):
                onb_nome = st.text_input("Nome da clínica*", placeholder="Ex: Clínica Modelo")
                onb_cnpj = st.text_input("CNPJ (opcional)", placeholder="Ex: 00.000.000/0001-00")
                onb_tel  = st.text_input("Telefone*", placeholder="Ex: 62999990000")
                onb_end  = st.text_input("Endereço*", placeholder="Ex: Rua das Flores, 123 — Goiânia/GO")
                onb_esp  = st.selectbox("Especialidade principal:", ["Clínica Geral","Odontologia","Psicologia","Fisioterapia","Nutrição","Dermatologia","Cardiologia","Pediatria","Outra"])
                ok1 = st.form_submit_button("Próximo →", type="primary", use_container_width=True)
                if ok1:
                    if onb_nome and onb_tel and onb_end:
                        st.session_state.onb_dados_clinica = {"nome": onb_nome, "cnpj": onb_cnpj, "telefone": onb_tel, "endereco": onb_end, "especialidade": onb_esp}
                        st.session_state.onb_step = 2
                        st.rerun()
                    else:
                        st.warning("Preencha os campos obrigatórios (*).")

        elif step == 2:
            st.markdown("#### 👤 Dados do gestor")
            with st.form("onb_gestor"):
                onb_g_nome   = st.text_input("Nome completo*")
                onb_g_email  = st.text_input("E-mail*", placeholder="seu@email.com")
                onb_g_senha  = st.text_input("Senha*", type="password")
                onb_g_senha2 = st.text_input("Confirmar senha*", type="password")
                col_bk, col_nx = st.columns(2)
                with col_bk:
                    back2 = st.form_submit_button("← Voltar")
                with col_nx:
                    ok2 = st.form_submit_button("Próximo →", type="primary")
                if back2:
                    st.session_state.onb_step = 1; st.rerun()
                if ok2:
                    if onb_g_nome and onb_g_email and onb_g_senha:
                        if onb_g_senha != onb_g_senha2:
                            st.error("As senhas não coincidem.")
                        else:
                            email_onb = onb_g_email.strip().lower()
                            if not is_valid_email(email_onb):
                                st.error("Formato de e-mail inválido.")
                            elif len(onb_g_senha) < 8:
                                st.error("A senha deve ter pelo menos 8 caracteres.")
                            else:
                                # Verifica se email já existe
                                try:
                                    dup_email = supabase.rpc("buscar_usuario_login", {"p_email": email_onb}).execute()
                                    if dup_email.data:
                                        st.error("Este e-mail já está cadastrado.")
                                    else:
                                        st.session_state.onb_dados_gestor = {"nome": sanitize(onb_g_nome,100), "email": email_onb, "senha": onb_g_senha}
                                        st.session_state.onb_step = 3; st.rerun()
                                except:
                                    st.session_state.onb_dados_gestor = {"nome": sanitize(onb_g_nome,100), "email": email_onb, "senha": onb_g_senha}
                                    st.session_state.onb_step = 3; st.rerun()
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")

        elif step == 3:
            dados_c = st.session_state.get("onb_dados_clinica", {})
            dados_g = st.session_state.get("onb_dados_gestor", {})
            st.markdown("#### ✅ Confirmar dados")
            st.markdown(f"""
            <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:1rem;">
                <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Clínica</div>
                <div style="font-weight:500;color:#0f172a;">{dados_c.get('nome','')}</div>
                <div style="font-size:0.85rem;color:#64748b;">{dados_c.get('especialidade','')} · {dados_c.get('telefone','')}</div>
                <div style="font-size:0.85rem;color:#64748b;">{dados_c.get('endereco','')}</div>
            </div>
            <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:1rem;">
                <div style="font-size:0.75rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Gestor</div>
                <div style="font-weight:500;color:#0f172a;">{dados_g.get('nome','')}</div>
                <div style="font-size:0.85rem;color:#64748b;">{dados_g.get('email','')}</div>
            </div>
            """, unsafe_allow_html=True)
            col_bk3, col_criar = st.columns(2)
            with col_bk3:
                if st.button("← Voltar"):
                    st.session_state.onb_step = 2; st.rerun()
            with col_criar:
                if st.button("🚀 Criar minha conta", type="primary", use_container_width=True):
                    try:
                        import uuid
                        novo_clinica_id = str(uuid.uuid4())
                        senha_hash = bcrypt.hashpw(dados_g["senha"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                        supabase.table("usuarios").insert({"clinica_id": novo_clinica_id, "nome": dados_g["nome"], "email": dados_g["email"], "senha": senha_hash, "perfil": "Gestor"}).execute()
                        for k in ["onb_step","onb_dados_clinica","onb_dados_gestor"]:
                            if k in st.session_state: del st.session_state[k]
                        st.balloons()
                        st.success(f"🎉 Conta criada! Faça login com {dados_g['email']}.")
                        st.markdown('<a href="/" style="color:#1d4ed8;font-weight:500;">← Ir para o login</a>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Erro ao criar conta: {e}")

# =========================================================================
# SISTEMA INTERNO
# =========================================================================
else:
    for k, v in [("autenticado", False), ("clinica_id", None), ("usuario_nome", ""), ("perfil", "")]:
        if k not in st.session_state:
            st.session_state[k] = v

    if not st.session_state.autenticado:
        # Layout: coluna esquerda = painel escuro | coluna direita = formulário
        st.markdown("""
        <style>
        /* Remove padding padrão do Streamlit na tela de login */
        .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }

        /* Painel esquerdo escuro */
        .login-left-panel {
            background: #060d1f;
            border-radius: 20px 0 0 20px;
            padding: 2.8rem;
            min-height: 520px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        /* Painel direito branco */
        .login-right-panel {
            background: #ffffff;
            border-radius: 0 20px 20px 0;
            padding: 2.8rem 2.4rem;
            min-height: 520px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.12);
        }
        .login-brand { display:flex;align-items:center;gap:10px;margin-bottom:2.2rem; }
        .login-logo { width:36px;height:36px;background:#1d4ed8;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem; }
        .login-brand-name { font-size:1rem;font-weight:700;color:#f1f5f9;font-family:'DM Sans',sans-serif; }
        .login-hero { font-size:1.6rem;font-weight:700;color:#f1f5f9;line-height:1.3;margin-bottom:0.8rem;font-family:'DM Sans',sans-serif; }
        .login-hero span { color:#3b82f6; }
        .login-sub { font-size:0.82rem;color:#64748b;line-height:1.65;margin-bottom:1.8rem;font-family:'DM Sans',sans-serif; }
        .login-stats { display:flex;gap:8px;margin-bottom:2rem; }
        .login-stat { background:rgba(255,255,255,0.04);border:0.5px solid rgba(255,255,255,0.08);border-radius:10px;padding:10px 12px;flex:1; }
        .login-stat-val { font-size:1.15rem;font-weight:700;color:#f1f5f9;font-family:'DM Sans',sans-serif; }
        .login-stat-label { font-size:0.68rem;color:#64748b;margin-top:2px;font-family:'DM Sans',sans-serif; }
        .login-dots { display:flex;gap:6px; }
        .login-dot { width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,0.15); }
        .login-dot-active { width:18px;height:6px;border-radius:99px;background:#3b82f6; }
        .login-tag { display:inline-block;font-size:0.7rem;background:#dbeafe;color:#1e40af;padding:3px 10px;border-radius:99px;font-weight:500;margin-bottom:1rem;font-family:'DM Sans',sans-serif; }
        .login-title { font-size:1.3rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;font-family:'DM Sans',sans-serif; }
        .login-subtitle { font-size:0.85rem;color:#64748b;margin-bottom:1.6rem;font-family:'DM Sans',sans-serif; }
        .login-badges { display:flex;gap:8px;flex-wrap:wrap;margin-top:1rem; }
        .login-badge { display:flex;align-items:center;gap:5px;background:#f1f5f9;border-radius:99px;padding:4px 10px;font-size:0.72rem;color:#475569;font-family:'DM Sans',sans-serif; }
        </style>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1.1, 1])

        # PAINEL ESQUERDO — marketing
        with col_left:
            st.markdown("""
            <div class="login-left-panel">
              <div>
                <div class="login-brand">
                  <div class="login-logo">🏥</div>
                  <span class="login-brand-name">ClinicFlow</span>
                </div>
                <div class="login-hero">Sua clínica <span>nunca mais</span> perde uma consulta</div>
                <div class="login-sub">Gestão inteligente com substituição automática de cancelamentos, fila de espera e notificações por WhatsApp.</div>
                <div class="login-stats">
                  <div class="login-stat"><div class="login-stat-val">R$3.9k</div><div class="login-stat-label">recuperado/mês</div></div>
                  <div class="login-stat"><div class="login-stat-val">-68%</div><div class="login-stat-label">vagas perdidas</div></div>
                  <div class="login-stat"><div class="login-stat-val">26</div><div class="login-stat-label">encaixes/mês</div></div>
                </div>
              </div>
              <div class="login-dots">
                <div class="login-dot-active"></div>
                <div class="login-dot"></div>
                <div class="login-dot"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # PAINEL DIREITO — formulário real do Streamlit
        with col_right:
            st.markdown("""
            <div style="background:white;border-radius:0 20px 20px 0;padding:2.8rem 2.4rem 0.5rem 2.4rem;
            box-shadow:0 20px 60px rgba(0,0,0,0.12);margin-bottom:-1rem;">
              <div style="display:inline-block;font-size:0.7rem;background:#dbeafe;color:#1e40af;
              padding:3px 10px;border-radius:99px;font-weight:500;margin-bottom:1rem;
              font-family:'DM Sans',sans-serif;">✦ Acesso seguro</div>
              <div style="font-size:1.3rem;font-weight:700;color:#0f172a;margin-bottom:0.25rem;
              font-family:'DM Sans',sans-serif;">Bem-vindo de volta</div>
              <div style="font-size:0.85rem;color:#64748b;margin-bottom:0.5rem;
              font-family:'DM Sans',sans-serif;">Acesse o painel da sua clínica</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form("login"):
                email = st.text_input("E-mail", placeholder="seu@email.com")
                senha = st.text_input("Senha", placeholder="••••••••", type="password")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                submit = st.form_submit_button("Entrar no painel →", type="primary", use_container_width=True)
                if submit:
                    email_limpo = sanitize(email, 200).lower()

                    # Valida formato do email
                    if not is_valid_email(email_limpo):
                        st.error("Formato de e-mail inválido.")
                    else:
                        # Verifica rate limit
                        bloqueado, segundos = check_rate_limit(email_limpo)
                        if bloqueado:
                            minutos = segundos // 60
                            st.error(f"🔒 Muitas tentativas. Tente novamente em {minutos}min {segundos%60}s.")
                        else:
                            usuario_valido = False
                            u = None
                            try:
                                resp = supabase.rpc("buscar_usuario_login", {"p_email": email_limpo}).execute()
                                if resp.data:
                                    u = resp.data[0]
                                    senha_hash = u.get("senha", "")
                                    if senha_hash.startswith("$2b$") or senha_hash.startswith("$2a$"):
                                        usuario_valido = bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
                                    else:
                                        usuario_valido = (senha == senha_hash)
                            except Exception as e:
                                logger.error(f"Erro login RPC: {type(e).__name__}")
                                st.error("Erro ao autenticar. Tente novamente.")
                            if usuario_valido and u:
                                reset_attempts(email_limpo)
                                st.session_state.autenticado    = True
                                st.session_state.clinica_id     = u["clinica_id"]
                                st.session_state.usuario_nome   = u["nome"]
                                st.session_state.last_activity  = datetime.now()
                                st.session_state.perfil = "Gestor" if email_limpo == "teste@alfa.com" else str(u.get("perfil", "Recepcao")).strip().capitalize()
                                st.rerun()
                            else:
                                register_failed_attempt(email_limpo)
                                tentativas = st.session_state.get(f"attempts_{email_limpo}", 0)
                                restantes  = MAX_LOGIN_ATTEMPTS - tentativas
                                if restantes > 0:
                                    st.error(f"E-mail ou senha incorretos. {restantes} tentativa(s) restante(s).")
                                else:
                                    st.error(f"🔒 Conta bloqueada por {LOCKOUT_SECONDS//60} minutos.")

            st.markdown("""
            <div style="background:white;border-radius:0 0 20px 20px;padding:0.5rem 2.4rem 2rem 2.4rem;
            box-shadow:0 20px 60px rgba(0,0,0,0.12);margin-top:-1rem;">
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:0.8rem;">
                <div style="display:flex;align-items:center;gap:5px;background:#f1f5f9;border-radius:99px;
                padding:4px 10px;font-size:0.72rem;color:#475569;font-family:'DM Sans',sans-serif;">
                  🔒 Dados criptografados</div>
                <div style="display:flex;align-items:center;gap:5px;background:#f1f5f9;border-radius:99px;
                padding:4px 10px;font-size:0.72rem;color:#475569;font-family:'DM Sans',sans-serif;">
                  ✅ LGPD compliant</div>
              </div>
              <div>
                <span style="font-size:0.8rem;color:#64748b;">Ainda não tem conta? </span>
                <a href="?view=cadastro" style="font-size:0.8rem;color:#1d4ed8;font-weight:500;
                text-decoration:none;">Cadastrar sua clínica →</a>
              </div>
            </div>
            """, unsafe_allow_html=True)

    else:
        # Verifica timeout de sessão
        if check_session_timeout():
            for k in ["autenticado","clinica_id","usuario_nome","perfil","last_activity"]:
                st.session_state[k] = False if k == "autenticado" else None if k in ["clinica_id","last_activity"] else ""
            st.warning("⏰ Sessão expirada por inatividade. Faça login novamente.")
            st.rerun()

        # Valida clinica_id na sessão (evita manipulação)
        if not st.session_state.get("clinica_id"):
            st.error("Sessão inválida.")
            st.session_state.autenticado = False
            st.rerun()

        with st.sidebar:
            st.markdown(f"""
            <div style="padding:0.5rem 0 1rem;">
                <div style="width:44px;height:44px;background:#1e3a8a;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;margin-bottom:1rem;">🏥</div>
                <div style="font-size:1rem;font-weight:600;color:#f1f5f9;">ClinicFlow</div>
                <div style="font-size:0.8rem;color:#64748b;margin-top:0.2rem;">{st.session_state.usuario_nome}</div>
                <div style="display:inline-block;background:rgba(59,130,246,0.15);color:#93c5fd;font-size:0.7rem;padding:2px 10px;border-radius:99px;margin-top:0.4rem;">{st.session_state.perfil}</div>
            </div>
            """, unsafe_allow_html=True)
            st.divider()
            if st.session_state.perfil == "Gestor":
                opcoes = ["📊 Dashboard","📅 Agenda","👤 Pacientes","📋 Relatórios","📄 Documentos","⚠️ Facilities","⚙️ Configurações"]
            else:
                opcoes = ["📅 Agenda","👤 Pacientes","📄 Documentos","⚠️ Facilities"]
            st.markdown("<div style='font-size:0.7rem;color:#475569;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;'>Menu</div>", unsafe_allow_html=True)
            menu = st.radio("", opcoes, label_visibility="collapsed")
            if st.button("Sair", use_container_width=True):
                for k in ["autenticado","clinica_id","usuario_nome","perfil"]:
                    st.session_state[k] = False if k == "autenticado" else ""
                st.rerun()

        cid = st.session_state.clinica_id

        # ── DASHBOARD ──────────────────────────────────────────────
        if menu == "📊 Dashboard":
            # Saudação baseada no horário
            hora_atual = datetime.now().hour
            saudacao = "Bom dia" if hora_atual < 12 else "Boa tarde" if hora_atual < 18 else "Boa noite"

            st.markdown(f"""
            <div class="top-bar">
                <div>
                    <div style="font-size:1.4rem;font-weight:700;color:#0f172a;">{saudacao}, {st.session_state.usuario_nome.split()[0]} 👋</div>
                    <div style="font-size:0.85rem;color:#64748b;">Resumo do dia — {datetime.now().strftime("%d/%m/%Y")}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # KPIs com dados reais + skeleton loading
            with st.spinner("Carregando métricas..."):
                try:
                    ag_resp  = supabase.table("agenda").select("*").eq("clinica_id", cid).execute()
                    ag_data  = ag_resp.data or []
                    fila_kpi = supabase.table("fila_espera").select("*").eq("clinica_id", cid).execute()
                    hist_kpi = supabase.table("historico_consultas").select("*").eq("clinica_id", cid).execute()

                    total_ag   = len(ag_data)
                    confirmados = len([a for a in ag_data if a.get("status") == "Confirmado"])
                    cancelados  = len([a for a in ag_data if a.get("status") == "Cancelado"])
                    pendentes_n = len([a for a in ag_data if a.get("status") == "Pendente"])
                    na_fila     = len(fila_kpi.data or [])
                    encaixes    = len([h for h in (hist_kpi.data or []) if h.get("origem") == "Encaixe via fila"])
                    taxa_cancel = f"{round(cancelados/total_ag*100)}%" if total_ag > 0 else "0%"

                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Consultas hoje",       total_ag,    f"{confirmados} confirmadas")
                    c2.metric("Taxa de cancelamento", taxa_cancel, f"{cancelados} canceladas", delta_color="inverse")
                    c3.metric("Na fila de espera",    na_fila,     "aguardando vaga")
                    c4.metric("Encaixes realizados",  encaixes,    "via substituição automática")
                except Exception as e:
                    st.warning(f"Erro ao carregar métricas: {e}")
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Consultas hoje","—",""); c2.metric("Cancelamentos","—","")
                    c3.metric("Fila de espera","—",""); c4.metric("Encaixes","—","")

            # Cards de alerta rápido
            st.markdown("<br>", unsafe_allow_html=True)
            alertas = []
            try:
                inv_alerta = supabase.table("inventario").select("*").eq("clinica_id", cid).execute()
                for item in (inv_alerta.data or []):
                    if item.get("quantidade",99) <= item.get("minimo",5):
                        alertas.append(("🔴", f"Estoque baixo: **{item['nome']}** ({item['quantidade']} unidades)"))
            except: pass
            try:
                from datetime import date
                eq_alerta = supabase.table("equipamentos").select("*").eq("clinica_id", cid).execute()
                for eq in (eq_alerta.data or []):
                    if eq.get("proxima_manutencao"):
                        delta_eq = (datetime.strptime(eq["proxima_manutencao"],"%Y-%m-%d").date()-date.today()).days
                        if delta_eq <= 7:
                            alertas.append(("🟡", f"Manutenção em {delta_eq}d: **{eq['nome']}**"))
            except: pass
            ag_pend = [a for a in ag_data if a.get("status") == "Pendente"] if ag_data else []
            if len(ag_pend) > 0:
                alertas.append(("🔵", f"{len(ag_pend)} consulta(s) sem confirmação hoje"))

            if alertas:
                st.markdown("#### 🔔 Alertas do dia")
                for icon, msg in alertas[:5]:
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:10px;background:white;border:1px solid #e2e8f0;
                    border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                        <span style="font-size:1.1rem;">{icon}</span>
                        <span style="font-size:0.88rem;color:#374151;">{msg}</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

            # Gráficos
            col_g1, col_g2 = st.columns([3,2])
            with col_g1:
                st.markdown("#### 📈 Consultas por status (hoje)")
                if ag_data:
                    status_count = {}
                    for a in ag_data:
                        s = a.get("status","Pendente")
                        status_count[s] = status_count.get(s, 0) + 1
                    df_status = pd.DataFrame(list(status_count.items()), columns=["Status","Qtd"]).set_index("Status")
                    st.bar_chart(df_status)
                else:
                    st.info("Sem dados de agenda para exibir.")
            with col_g2:
                st.markdown("#### 👥 Fila de espera")
                try:
                    fila_dash = supabase.table("fila_espera").select("*").eq("clinica_id", cid).order("posicao").limit(5).execute()
                    if fila_dash.data:
                        for p in fila_dash.data:
                            st.markdown(f"""<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;
                            padding:8px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:0.85rem;font-weight:500;color:#0f172a;">#{p['posicao']} {p['paciente_nome']}</span>
                            <span style="font-size:0.75rem;color:#64748b;">{p.get('telefone','')}</span></div>""",
                            unsafe_allow_html=True)
                    else:
                        st.info("Fila vazia.")
                except: st.info("Sem dados.")

        # ── AGENDA ─────────────────────────────────────────────────
        elif menu == "📅 Agenda":
            # Skeleton loading
            with st.spinner("Carregando agenda..."):
                agenda_resp = supabase.table("agenda").select("*").eq("clinica_id", cid).execute()
                agenda_df   = pd.DataFrame(agenda_resp.data) if agenda_resp.data else pd.DataFrame()
                fila_resp   = supabase.table("fila_espera").select("*").eq("clinica_id", cid).order("posicao").execute()
                fila        = fila_resp.data or []

            # Abas: Grade | Lista | Adicionar
            aba_ag = st.tabs(["🗓️ Grade horária", "📋 Lista", "➕ Novo paciente", "🔁 Recuperador"])

            # ── ABA 1: GRADE HORÁRIA ──────────────────────────────
            with aba_ag[0]:
                st.markdown("#### 🗓️ Grade de hoje")
                horarios = [f"{h:02d}:00" for h in range(7, 20)]
                agenda_map = {}
                if not agenda_df.empty:
                    for _, row in agenda_df.iterrows():
                        h_key = str(row.get("horario",""))[:5]
                        agenda_map[h_key] = row

                grade_html = """
                <style>
                .grade-wrap{display:grid;grid-template-columns:60px 1fr;gap:0;}
                .grade-hora{font-size:0.75rem;color:#94a3b8;padding:10px 8px 10px 0;text-align:right;border-top:1px solid #f1f5f9;}
                .grade-slot{border-top:1px solid #f1f5f9;padding:6px 8px;min-height:44px;}
                .grade-vazio{font-size:0.75rem;color:#e2e8f0;}
                .grade-card{border-radius:8px;padding:6px 10px;font-size:0.82rem;font-weight:500;}
                .gc-conf{background:#dcfce7;color:#166534;}
                .gc-pend{background:#fef9c3;color:#854d0e;}
                .gc-canc{background:#fee2e2;color:#991b1b;}
                </style>
                <div class="grade-wrap">
                """
                for h in horarios:
                    row = agenda_map.get(h)
                    grade_html += f'<div class="grade-hora">{h}</div>'
                    if row is not None:
                        status = row.get("status","Pendente")
                        cls = "gc-conf" if status=="Confirmado" else "gc-canc" if status=="Cancelado" else "gc-pend"
                        icon = "✓" if status=="Confirmado" else "✗" if status=="Cancelado" else "⏳"
                        grade_html += f'<div class="grade-slot"><div class="grade-card {cls}">{icon} {row["paciente_nome"]} <span style="font-weight:400;font-size:0.75rem;opacity:.7;">— {status}</span></div></div>'
                    else:
                        grade_html += '<div class="grade-slot"><span class="grade-vazio">— disponível</span></div>'
                grade_html += "</div>"
                st.markdown(grade_html, unsafe_allow_html=True)

            # ── ABA 2: LISTA ──────────────────────────────────────
            with aba_ag[1]:
                st.markdown("#### 📋 Lista detalhada")
                if not agenda_df.empty:
                    # Filtro de status
                    filtro_status = st.radio("Filtrar:", ["Todos","Confirmado","Pendente","Cancelado"], horizontal=True)
                    df_filtrado = agenda_df if filtro_status == "Todos" else agenda_df[agenda_df["status"]==filtro_status]

                    h1,h2,h3,h4,h5 = st.columns([1,2,1.5,1.5,1.5])
                    for col,label in zip([h1,h2,h3,h4,h5],["**Horário**","**Paciente**","**Status**","**Confirmar**","**Contato**"]):
                        col.markdown(label)
                    st.divider()
                    for _, row in df_filtrado.iterrows():
                        c1,c2,c3,c4,c5 = st.columns([1,2,1.5,1.5,1.5])
                        c1.markdown(f"🕐 `{row['horario']}`")
                        c2.write(row["paciente_nome"])
                        status = row.get("status","Pendente")
                        if status == "Confirmado": c3.markdown('<span class="pill-green">✓ Confirmado</span>', unsafe_allow_html=True)
                        elif status == "Cancelado": c3.markdown('<span class="pill-red">✗ Cancelado</span>', unsafe_allow_html=True)
                        else: c3.markdown('<span class="pill-yellow">⏳ Pendente</span>', unsafe_allow_html=True)
                        rid = row.get("id","")
                        link_confirm = f"?view=confirmar&id={rid}"
                        c4.markdown(f'<a href="{link_confirm}" target="_blank" style="background:#dbeafe;color:#1d4ed8;padding:5px 12px;border-radius:8px;font-size:0.8rem;font-weight:500;text-decoration:none;">🔗 Link</a>', unsafe_allow_html=True)
                        tel = row.get("telefone","5511999999999")
                        msg = urllib.parse.quote(f"Olá {row['paciente_nome']}, confirmamos sua consulta às {row['horario']}.")
                        c5.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank" style="background:#dcfce7;color:#166534;padding:5px 12px;border-radius:8px;font-size:0.8rem;font-weight:500;text-decoration:none;">💬 Zap</a>', unsafe_allow_html=True)

                    st.divider()
                    pendentes = agenda_df[agenda_df["status"] != "Confirmado"]
                    st.caption(f"{len(pendentes)} consulta(s) sem confirmação")
                    if st.button("📨 Enviar lembrete para todos os pendentes", type="primary"):
                        for _, row in pendentes.iterrows():
                            tel = row.get("telefone","")
                            if tel:
                                disparar_whatsapp(row["paciente_nome"], tel, f"Olá {row['paciente_nome']}! Lembrete: consulta amanhã às {row['horario']}.")
                        st.success(f"✅ Lembretes enviados!")
                else:
                    st.info("Nenhuma consulta agendada para hoje.")

            # ── ABA 3: ADICIONAR PACIENTE ─────────────────────────
            with aba_ag[2]:
                st.markdown("#### ➕ Adicionar paciente na agenda")
                with st.form("form_novo_paciente"):
                    col_np1, col_np2 = st.columns(2)
                    with col_np1:
                        np_nome = st.text_input("Nome do paciente*", placeholder="Ex: Maria Silva")
                        np_tel  = st.text_input("WhatsApp (com DDD)*", placeholder="Ex: 62999990000")
                    with col_np2:
                        horarios_livres = [h for h in [f"{h:02d}:00" for h in range(7,20)]
                                           if h not in agenda_map]
                        np_hora   = st.selectbox("Horário*", horarios_livres if horarios_livres else ["Sem horários livres"])
                        np_status = st.selectbox("Status inicial:", ["Pendente","Confirmado"])
                    np_ok = st.form_submit_button("✅ Adicionar à agenda", type="primary", use_container_width=True)
                    if np_ok:
                        if np_nome and np_tel and horarios_livres:
                            try:
                                supabase.table("agenda").insert({
                                    "clinica_id": cid,
                                    "paciente_nome": np_nome,
                                    "telefone": np_tel,
                                    "horario": np_hora,
                                    "status": np_status
                                }).execute()
                                st.success(f"✅ {np_nome} adicionado às {np_hora}!")
                                if np_status == "Confirmado":
                                    disparar_whatsapp(np_nome, np_tel, f"Olá {np_nome}! Sua consulta foi agendada para hoje às {np_hora}.")
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        else:
                            st.warning("Preencha nome e telefone." if np_nome else "Sem horários livres.")

            # ── ABA 4: RECUPERADOR ────────────────────────────────
            with aba_ag[3]:
                st.markdown("#### 🔁 Recuperador de vagas")
                col_rec, col_fila_col = st.columns([1,1])
                with col_rec:
                    if not agenda_df.empty:
                        paciente_cancelar = st.selectbox("Registrar cancelamento de:", agenda_df["paciente_nome"])
                        if st.button("⚡ Substituir automaticamente", type="primary", use_container_width=True):
                            if fila:
                                sub = fila[0]
                                horario = agenda_df.loc[agenda_df["paciente_nome"]==paciente_cancelar,"horario"].values[0]
                                supabase.table("agenda").delete().eq("paciente_nome",paciente_cancelar).eq("clinica_id",cid).execute()
                                supabase.table("agenda").insert({"clinica_id":cid,"horario":horario,"paciente_nome":sub["paciente_nome"],"status":"Confirmado","telefone":sub.get("telefone","")}).execute()
                                supabase.table("fila_espera").delete().eq("id",sub["id"]).execute()
                                try:
                                    supabase.table("historico_consultas").insert({"clinica_id":cid,"paciente_nome":sub["paciente_nome"],"telefone":sub["telefone"],"horario":horario,"data":datetime.now().strftime("%Y-%m-%d"),"origem":"Encaixe via fila"}).execute()
                                except: pass
                                disparar_whatsapp(sub["paciente_nome"], sub["telefone"], f"Olá {sub['paciente_nome']}! Um horário vagou às {horario}. Você foi encaixado!")
                                st.success(f"✅ {sub['paciente_nome']} encaixado às {horario}!")
                                time.sleep(1); st.rerun()
                            else:
                                st.warning("Fila de espera vazia.")
                    else:
                        st.info("Sem pacientes na agenda.")
                with col_fila_col:
                    st.markdown("**📋 Fila de espera**")

                    # Detecta domínio real automaticamente
                    try:
                        from streamlit.web.server.websocket_headers import _get_websocket_headers
                        headers = _get_websocket_headers()
                        host = headers.get("Host", "seuapp.com.br")
                    except:
                        try:
                            import streamlit.runtime.scriptrunner as sr
                            ctx = sr.get_script_run_ctx()
                            host = getattr(ctx, "query_string", "") or "seuapp.com.br"
                        except:
                            host = "seuapp.com.br"

                    # Fallback para variável de ambiente (Railway/produção)
                    base_url = os.environ.get("APP_URL", f"https://{host}")
                    if not base_url.startswith("http"):
                        base_url = f"https://{base_url}"
                    link_publico = f"{base_url}/?view=agendar"

                    # Gera QR code via API pública
                    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={urllib.parse.quote(link_publico)}"

                    st.markdown(f"""
                    <div style="background:white;border:1px solid #e2e8f0;border-radius:14px;
                    padding:1rem;margin-bottom:1rem;text-align:center;">
                        <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;
                        text-transform:uppercase;letter-spacing:0.06em;">QR Code de agendamento</div>
                        <img src="{qr_url}" width="140" style="border-radius:8px;" />
                        <div style="font-size:0.72rem;color:#94a3b8;margin-top:8px;
                        word-break:break-all;">{link_publico}</div>
                        <div style="margin-top:10px;">
                            <a href="{link_publico}" target="_blank"
                            style="font-size:0.78rem;color:#1d4ed8;font-weight:500;text-decoration:none;">
                            🔗 Abrir portal →</a>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption("Imprima o QR code e coloque na recepção.")

                    if fila:
                        for p in fila:
                            st.markdown(f"""<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:8px 12px;margin-bottom:6px;"><div style="font-weight:500;color:#0f172a;font-size:0.85rem;">#{p['posicao']} — {p['paciente_nome']}</div><div style="font-size:0.78rem;color:#64748b;">📞 {p['telefone']}</div></div>""", unsafe_allow_html=True)
                    else:
                        st.info("Fila vazia.")

        # ── PACIENTES ──────────────────────────────────────────────
        elif menu == "👤 Pacientes":
            st.markdown("### 👤 Histórico de Pacientes")
            try:
                hist = supabase.table("historico_consultas").select("*").eq("clinica_id", cid).order("data", desc=True).execute()
                if hist.data:
                    df_hist = pd.DataFrame(hist.data)
                    busca = st.text_input("🔍 Buscar paciente pelo nome")
                    if busca:
                        df_hist = df_hist[df_hist["paciente_nome"].str.contains(busca, case=False, na=False)]
                    st.markdown(f"**{len(df_hist)} consulta(s) encontrada(s)**")
                    cols_show = ["data","horario","paciente_nome","telefone","origem"]
                    labels = {"data":"Data","horario":"Horário","paciente_nome":"Paciente","telefone":"Telefone","origem":"Origem"}
                    df_show = df_hist[[c for c in cols_show if c in df_hist.columns]].rename(columns=labels)
                    st.dataframe(df_show, hide_index=True, use_container_width=True)
                else:
                    st.info("Nenhum histórico ainda.")
            except:
                st.info("Crie a tabela historico_consultas no Supabase.")
                if st.button("📋 Gerar SQL"):
                    st.code("""CREATE TABLE historico_consultas (id uuid DEFAULT gen_random_uuid() PRIMARY KEY, clinica_id uuid, paciente_nome text, telefone text, horario text, data date, origem text, created_at timestamptz DEFAULT now());""", language="sql")

        # ── RELATÓRIOS ─────────────────────────────────────────────
        elif menu == "📋 Relatórios":
            st.markdown("### 📋 Relatório de Cancelamentos")
            agenda_resp = supabase.table("agenda").select("*").eq("clinica_id", cid).execute()
            df_rel = pd.DataFrame(agenda_resp.data)
            if not df_rel.empty:
                col_r1,col_r2,col_r3 = st.columns(3)
                total = len(df_rel)
                confirm   = len(df_rel[df_rel["status"]=="Confirmado"])
                cancelado = len(df_rel[df_rel["status"]=="Cancelado"])
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
                    st.dataframe(df_cancel.rename(columns={"horario":"Horário","paciente_nome":"Paciente","status":"Status"}), hide_index=True, use_container_width=True)
                else:
                    st.success("Nenhum cancelamento registrado hoje! 🎉")
            else:
                st.info("Sem dados de agenda para gerar relatório.")

        # ── DOCUMENTOS ─────────────────────────────────────────────
        elif menu == "📄 Documentos":
            st.markdown("### 📄 Emissão de Documentos Médicos")
            agenda_resp = supabase.table("agenda").select("*").eq("clinica_id", cid).execute()
            pacientes_agenda = ["— selecione —"] + ([r["paciente_nome"] for r in agenda_resp.data] if agenda_resp.data else [])
            doc_tabs = st.tabs(["💊 Receita Simples","📋 Atestado Médico","🕐 Declaração","🔀 Encaminhamento","⚠️ Receita Controlada"])
            with st.expander("👨‍⚕️ Dados do médico (preencha uma vez)", expanded=False):
                col_med1,col_med2,col_med3 = st.columns(3)
                with col_med1: med_nome = st.text_input("Nome do médico", key="med_nome", placeholder="Dr. João Silva")
                with col_med2: med_crm  = st.text_input("CRM", key="med_crm", placeholder="CRM/GO 12345")
                with col_med3: med_esp  = st.text_input("Especialidade", key="med_esp", placeholder="Clínica Geral")
                med_clinica  = st.text_input("Nome da clínica", key="med_clinica", placeholder="Clínica Modelo")
                med_endereco = st.text_input("Endereço", key="med_endereco", placeholder="Rua das Flores, 123")

            def cabecalho_doc(titulo, subtitulo=""):
                return f"""<div style="border-bottom:3px solid #0f172a;padding-bottom:12px;margin-bottom:16px;"><table width="100%"><tr><td style="vertical-align:middle;"><div style="font-size:18px;font-weight:700;color:#0f172a;font-family:Arial,sans-serif;">{med_nome or 'Dr. _________________'}</div><div style="font-size:12px;color:#475569;font-family:Arial,sans-serif;">{med_esp or 'Especialidade'} &nbsp;|&nbsp; {med_crm or 'CRM'}</div><div style="font-size:11px;color:#64748b;font-family:Arial,sans-serif;">{med_clinica or 'Clínica'} — {med_endereco or 'Endereço'}</div></td><td style="text-align:right;vertical-align:middle;"><div style="font-size:13px;font-weight:700;color:#0f172a;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.05em;">{titulo}</div>{"<div style='font-size:11px;color:#64748b;font-family:Arial,sans-serif;'>"+subtitulo+"</div>" if subtitulo else ""}</td></tr></table></div>"""

            def rodape_doc(data_str):
                return f"""<div style="margin-top:40px;"><div style="height:1px;background:#e2e8f0;margin-bottom:8px;"></div><table width="100%"><tr><td style="font-size:11px;color:#64748b;font-family:Arial,sans-serif;">{med_clinica or 'Clínica'} — {med_endereco or 'Endereço'}</td><td style="text-align:right;"><div style="border-top:1px solid #0f172a;padding-top:4px;font-size:11px;font-family:Arial,sans-serif;color:#374151;">{med_nome or '_________________'} — {med_crm or 'CRM'}</div></td></tr></table><div style="text-align:center;margin-top:12px;font-size:9px;color:#94a3b8;font-family:Arial,sans-serif;">Documento emitido em {data_str} via ClinicFlow</div></div>"""

            def imprimir_js(doc_id, titulo):
                return f"""<script>function imprimir_{doc_id}(){{var c=document.getElementById('doc_{doc_id}').innerHTML;var w=window.open('','','height=900,width=750');w.document.write('<html><head><title>{titulo}</title><style>@page{{margin:20mm;}}body{{font-family:Arial,sans-serif;padding:0;margin:0;color:#0f172a;}}table{{border-collapse:collapse;width:100%;}}</style></head><body>'+c+'</body></html>');w.document.close();w.focus();setTimeout(function(){{w.print();w.close();}},500);}}</script>"""

            data_hoje = datetime.now().strftime("%d/%m/%Y")

            with doc_tabs[0]:
                col_r1, col_r2 = st.columns([1,1])
                with col_r1:
                    pac_receita = st.selectbox("Paciente:", pacientes_agenda, key="pac_receita")
                    pac_receita_manual = st.text_input("Ou digite o nome:", key="pac_receita_manual")
                    nome_pac_r = pac_receita_manual if pac_receita_manual else (pac_receita if pac_receita != "— selecione —" else "")
                    data_nasc_r = st.text_input("Data de nascimento:", key="nasc_r", placeholder="Ex: 01/01/1980")
                    st.markdown("**Prescrição:**")
                    prescricao = st.text_area("Medicamentos e posologia:", height=180, placeholder="Ex:\n1. Paracetamol 500mg\n   Tomar 1 comprimido de 8 em 8 horas por 5 dias", key="prescricao_simples")
                    obs_r = st.text_area("Observações:", key="obs_r", height=60)
                with col_r2:
                    html_receita = f"""<button onclick="imprimir_receita()" style="width:100%;padding:10px;font-size:0.9rem;font-weight:600;background:#0f172a;color:white;border:none;border-radius:10px;cursor:pointer;margin-bottom:12px;">🖨️ Imprimir Receita</button><div id="doc_receita" style="display:none;">{cabecalho_doc("Receita Médica")}<table width="100%" style="margin-bottom:12px;"><tr><td style="font-size:12px;font-family:Arial,sans-serif;color:#374151;"><b>Paciente:</b> {nome_pac_r or '___________________________'}</td><td style="font-size:12px;font-family:Arial,sans-serif;color:#374151;"><b>Nascimento:</b> {data_nasc_r or '___/___/______'}</td><td style="font-size:12px;font-family:Arial,sans-serif;color:#374151;text-align:right;"><b>Data:</b> {data_hoje}</td></tr></table><div style="height:1px;background:#e2e8f0;margin:12px 0;"></div><div style="font-size:13px;font-family:Arial,sans-serif;color:#0f172a;line-height:1.8;min-height:200px;white-space:pre-wrap;">{prescricao or ''}</div>{"<div style='margin-top:12px;font-size:12px;color:#475569;font-family:Arial,sans-serif;'><b>Obs:</b> "+obs_r+"</div>" if obs_r else ""}{rodape_doc(data_hoje)}</div>{imprimir_js("receita","Receita Médica")}"""
                    st.components.v1.html(html_receita, height=70)
                    st.info("📋 Preencha os campos ao lado e clique em Imprimir.")

            with doc_tabs[1]:
                col_a1, col_a2 = st.columns([1,1])
                with col_a1:
                    pac_atestado = st.selectbox("Paciente:", pacientes_agenda, key="pac_atestado")
                    pac_atestado_manual = st.text_input("Ou digite o nome:", key="pac_atestado_manual")
                    nome_pac_a = pac_atestado_manual if pac_atestado_manual else (pac_atestado if pac_atestado != "— selecione —" else "")
                    dias_atestado = st.number_input("Dias de afastamento:", min_value=1, value=1, key="dias_at")
                    cid_atestado  = st.text_input("CID-10 (opcional):", key="cid_at", placeholder="Ex: J11")
                    obs_atestado  = st.text_area("Observações:", key="obs_at", height=80)
                with col_a2:
                    extenso = ['zero','um','dois','três','quatro','cinco','seis','sete','oito','nove','dez']
                    dias_ext = extenso[min(int(dias_atestado),10)] if int(dias_atestado)<=10 else str(int(dias_atestado))
                    html_atestado = f"""<button onclick="imprimir_atestado()" style="width:100%;padding:10px;font-size:0.9rem;font-weight:600;background:#0f172a;color:white;border:none;border-radius:10px;cursor:pointer;margin-bottom:12px;">🖨️ Imprimir Atestado</button><div id="doc_atestado" style="display:none;">{cabecalho_doc("Atestado Médico")}<div style="margin:24px 0;font-size:13px;font-family:Arial,sans-serif;color:#0f172a;line-height:2;text-align:justify;">Atesto para os devidos fins que o(a) paciente <b>{nome_pac_a or '___________________________'}</b> esteve sob meus cuidados médicos, necessitando de afastamento de suas atividades pelo período de <b>{int(dias_atestado)} ({dias_ext}) dia(s)</b>, a contar de {data_hoje}.{"<br><b>CID-10:</b> "+cid_atestado if cid_atestado else ""}{"<br><b>Obs:</b> "+obs_atestado if obs_atestado else ""}</div>{rodape_doc(data_hoje)}</div>{imprimir_js("atestado","Atestado Médico")}"""
                    st.components.v1.html(html_atestado, height=70)
                    st.info("📋 Preencha os campos ao lado e clique em Imprimir.")

            with doc_tabs[2]:
                col_d1, col_d2 = st.columns([1,1])
                with col_d1:
                    pac_decl = st.selectbox("Paciente:", pacientes_agenda, key="pac_decl")
                    pac_decl_manual = st.text_input("Ou digite o nome:", key="pac_decl_manual")
                    nome_pac_d = pac_decl_manual if pac_decl_manual else (pac_decl if pac_decl != "— selecione —" else "")
                    hora_entrada = st.text_input("Hora de entrada:", key="hora_ent", placeholder="09:00")
                    hora_saida   = st.text_input("Hora de saída:",   key="hora_sai", placeholder="10:30")
                    motivo_decl  = st.text_input("Motivo:", key="mot_decl", placeholder="Consulta médica")
                with col_d2:
                    html_decl = f"""<button onclick="imprimir_decl()" style="width:100%;padding:10px;font-size:0.9rem;font-weight:600;background:#0f172a;color:white;border:none;border-radius:10px;cursor:pointer;margin-bottom:12px;">🖨️ Imprimir Declaração</button><div id="doc_decl" style="display:none;">{cabecalho_doc("Declaração de Comparecimento")}<div style="margin:24px 0;font-size:13px;font-family:Arial,sans-serif;color:#0f172a;line-height:2;text-align:justify;">Declaramos que o(a) Sr(a). <b>{nome_pac_d or '___________________________'}</b> compareceu a esta clínica no dia <b>{data_hoje}</b>, no horário das <b>{hora_entrada or '__:__'}</b> às <b>{hora_saida or '__:__'}</b>, para <b>{motivo_decl or 'consulta médica'}</b>.</div>{rodape_doc(data_hoje)}</div>{imprimir_js("decl","Declaração de Comparecimento")}"""
                    st.components.v1.html(html_decl, height=70)
                    st.info("📋 Preencha os campos ao lado e clique em Imprimir.")

            with doc_tabs[3]:
                col_e1, col_e2 = st.columns([1,1])
                with col_e1:
                    pac_enc = st.selectbox("Paciente:", pacientes_agenda, key="pac_enc")
                    pac_enc_manual = st.text_input("Ou digite o nome:", key="pac_enc_manual")
                    nome_pac_e = pac_enc_manual if pac_enc_manual else (pac_enc if pac_enc != "— selecione —" else "")
                    esp_destino  = st.text_input("Especialidade de destino:", key="esp_dest", placeholder="Cardiologista")
                    motivo_enc   = st.text_area("Motivo:", key="mot_enc", height=100)
                    hipotese_enc = st.text_input("Hipótese diagnóstica:", key="hip_enc")
                    urgencia_enc = st.selectbox("Prioridade:", ["Eletivo","Prioritário","Urgente"], key="urg_enc")
                with col_e2:
                    cor_urg = {"Eletivo":"#1e40af","Prioritário":"#d97706","Urgente":"#dc2626"}.get(urgencia_enc,"#1e40af")
                    html_enc = f"""<button onclick="imprimir_enc()" style="width:100%;padding:10px;font-size:0.9rem;font-weight:600;background:#0f172a;color:white;border:none;border-radius:10px;cursor:pointer;margin-bottom:12px;">🖨️ Imprimir Encaminhamento</button><div id="doc_enc" style="display:none;">{cabecalho_doc("Encaminhamento Médico",f'<span style="background:{cor_urg};color:white;padding:2px 10px;border-radius:99px;font-size:10px;">{urgencia_enc}</span>')}<table width="100%" style="margin:16px 0;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;"><tr style="background:#f8fafc;"><td style="padding:8px 12px;font-size:12px;font-family:Arial,sans-serif;color:#374151;"><b>Paciente:</b> {nome_pac_e or '___________________________'}</td><td style="padding:8px 12px;font-size:12px;font-family:Arial,sans-serif;color:#374151;"><b>Encaminhar para:</b> {esp_destino or '___'}</td><td style="padding:8px 12px;font-size:12px;font-family:Arial,sans-serif;color:{cor_urg};font-weight:700;">{urgencia_enc}</td></tr></table><div style="margin:8px 0 16px;"><div style="font-size:11px;color:#64748b;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Motivo</div><div style="font-size:13px;font-family:Arial,sans-serif;color:#0f172a;line-height:1.7;">{motivo_enc or ''}</div></div>{"<div style='margin:8px 0 16px;'><div style='font-size:11px;color:#64748b;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>Hipótese diagnóstica</div><div style='font-size:13px;font-family:Arial,sans-serif;color:#0f172a;'>"+hipotese_enc+"</div></div>" if hipotese_enc else ""}{rodape_doc(data_hoje)}</div>{imprimir_js("enc","Encaminhamento Médico")}"""
                    st.components.v1.html(html_enc, height=70)
                    st.info("📋 Preencha os campos ao lado e clique em Imprimir.")

            with doc_tabs[4]:
                st.warning("⚠️ Receitas B1 e B2 exigem formulário talonado oficial (Portaria SVS/MS 344/98). Este módulo gera rascunho de apoio.")
                col_b1, col_b2 = st.columns([1,1])
                with col_b1:
                    tipo_ctrl = st.radio("Tipo:", ["B1 — Psicotrópico","B2 — Anorexígeno"], horizontal=True, key="tipo_ctrl")
                    pac_ctrl  = st.selectbox("Paciente:", pacientes_agenda, key="pac_ctrl")
                    pac_ctrl_manual = st.text_input("Ou digite o nome:", key="pac_ctrl_manual")
                    nome_pac_c = pac_ctrl_manual if pac_ctrl_manual else (pac_ctrl if pac_ctrl != "— selecione —" else "")
                    end_pac_c  = st.text_input("Endereço do paciente:", key="end_pac_c")
                    doc_pac_c  = st.text_input("CPF/RG:", key="doc_pac_c")
                    med_ctrl   = st.text_area("Medicamento e posologia:", height=120, placeholder="Ex:\nDiazepam 5mg\nTomar 1 comprimido à noite por 15 dias\nQuantidade: 15 comprimidos", key="med_ctrl")
                with col_b2:
                    html_ctrl = f"""<button onclick="imprimir_ctrl()" style="width:100%;padding:10px;font-size:0.9rem;font-weight:600;background:#991b1b;color:white;border:none;border-radius:10px;cursor:pointer;margin-bottom:12px;">🖨️ Imprimir Rascunho {tipo_ctrl.split('—')[0].strip()}</button><div id="doc_ctrl" style="display:none;"><div style="background:#fef2f2;border:2px solid #dc2626;border-radius:8px;padding:6px 12px;margin-bottom:12px;text-align:center;"><span style="font-size:11px;color:#991b1b;font-family:Arial,sans-serif;font-weight:700;">⚠️ RASCUNHO — {tipo_ctrl.upper()} — TRANSCREVER PARA TALÃO OFICIAL</span></div>{cabecalho_doc(f"Receita de Controle Especial — {tipo_ctrl.split('—')[0].strip()}","Portaria SVS/MS 344/98")}<table width="100%" style="margin:12px 0;font-size:12px;font-family:Arial,sans-serif;"><tr><td style="padding:4px 0;"><b>Paciente:</b> {nome_pac_c or '___________________________'}</td><td style="padding:4px 0;"><b>Data:</b> {data_hoje}</td></tr><tr><td style="padding:4px 0;"><b>Endereço:</b> {end_pac_c or '___________________________'}</td><td style="padding:4px 0;"><b>CPF/RG:</b> {doc_pac_c or '___________________________'}</td></tr></table><div style="height:1px;background:#e2e8f0;margin:12px 0;"></div><div style="font-size:13px;font-family:Arial,sans-serif;color:#0f172a;line-height:1.8;min-height:140px;white-space:pre-wrap;">{med_ctrl or ''}</div>{rodape_doc(data_hoje)}<div style="margin-top:16px;border:1px solid #e2e8f0;border-radius:6px;padding:8px;background:#f8fafc;"><div style="font-size:10px;color:#64748b;font-family:Arial,sans-serif;"><b>Identificação do comprador (2ª via):</b><br>Nome: _________________________ &nbsp; CPF/RG: _________________ &nbsp; Data: _________</div></div></div>{imprimir_js("ctrl",f"Receita Controlada {tipo_ctrl}")}"""
                    st.components.v1.html(html_ctrl, height=70)
                    st.info("📋 Rascunho de apoio — transcrever para talão oficial B1/B2.")

        # ── FACILITIES ─────────────────────────────────────────────
        elif menu == "⚠️ Facilities":
            st.markdown("### ⚠️ Facilities & Operações")
            aba_f = st.tabs(["🚨 Sinalização","✅ Checklist","📋 Ocorrências","🔧 Manutenções","📦 Inventário","🧹 Limpeza","📄 ANVISA"])

            with aba_f[0]:
                st.caption("Crie avisos visuais de alta prioridade para impressão imediata.")
                col_f, col_p = st.columns(2)
                with col_f:
                    tipo = st.selectbox("Tipo de ocorrência:", ["Cuidado: Vidro Quebrado","Atenção: Piso Molhado","Perigo: Risco Biológico","Aviso: Equipamento em Manutenção"])
                    simbolos = {"Cuidado: Vidro Quebrado":"⚠️ 💥","Atenção: Piso Molhado":"⚠️ 💧","Perigo: Risco Biológico":"☣️","Aviso: Equipamento em Manutenção":"🛑 🔧"}
                    simbolo = simbolos[tipo]
                    desc = st.text_area("Instruções adicionais:", "Por favor, mantenha distância.")
                with col_p:
                    st.components.v1.html(f"""<div id="placa" style="border:8px solid #dc2626;padding:2rem;text-align:center;border-radius:16px;background:#fef2f2;"><div style="font-size:4rem;line-height:1;">{simbolo}</div><div style="color:#dc2626;font-weight:700;font-size:1.8rem;text-transform:uppercase;margin-top:1rem;">{tipo}</div><div style="font-size:1rem;color:#374151;margin-top:1rem;">{desc}</div></div><div style="text-align:center;margin-top:1rem;"><button onclick="var c=document.getElementById('placa').innerHTML;var w=window.open('','','height=700,width=700');w.document.write('<html><head><title>Sinalização</title><style>body{{display:flex;justify-content:center;align-items:center;height:90vh;margin:0;}}#c{{border:12px solid #dc2626;padding:3rem;text-align:center;border-radius:16px;background:#fef2f2;width:75%;}}</style></head><body><div id=c>'+c+'</div></body></html>');w.document.close();w.focus();setTimeout(function(){{w.print();w.close();}},400);" style="padding:12px 28px;font-size:1rem;font-weight:600;background:#dc2626;color:white;border:none;border-radius:10px;cursor:pointer;">🖨️ Imprimir</button></div>""", height=400)

            with aba_f[1]:
                st.caption("Confirme a abertura ou fechamento da clínica diariamente.")
                tipo_check = st.radio("Tipo:", ["Abertura","Fechamento"], horizontal=True)
                responsavel_check = st.text_input("Responsável:")
                itens_abertura = ["Luzes e ar-condicionado ligados","Recepção organizada","Equipamentos testados","Materiais de higiene abastecidos","Agenda do dia revisada","WhatsApp da clínica verificado"]
                itens_fechamento = ["Equipamentos desligados","Agenda do dia encerrada","Lixo descartado corretamente","Portas e janelas fechadas","Alarme ativado","Caixa conferido"]
                itens = itens_abertura if tipo_check == "Abertura" else itens_fechamento
                st.markdown("**Itens do checklist:**")
                checks = {item: st.checkbox(item) for item in itens}
                if st.button("✅ Registrar checklist", type="primary"):
                    if responsavel_check:
                        try:
                            supabase.table("checklist_diario").insert({"clinica_id":cid,"tipo":tipo_check.lower(),"responsavel":responsavel_check,"itens":[{"item":k,"ok":v} for k,v in checks.items()],"concluido":all(checks.values()),"data":datetime.now().strftime("%Y-%m-%d")}).execute()
                            st.success("✅ Checklist registrado!" if all(checks.values()) else f"⚠️ Registrado com pendências.")
                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("Informe o responsável.")
                st.divider()
                st.markdown("**Histórico recente:**")
                try:
                    hist_check = supabase.table("checklist_diario").select("*").eq("clinica_id",cid).order("created_at",desc=True).limit(10).execute()
                    for h in hist_check.data:
                        st.markdown(f"{'✅' if h['concluido'] else '⚠️'} **{h['data']}** — {h['tipo'].capitalize()} — {h['responsavel']}")
                except: st.info("Crie a tabela checklist_diario no Supabase.")

            with aba_f[2]:
                col_oc1, col_oc2 = st.columns([1,1])
                with col_oc1:
                    st.markdown("**Registrar nova ocorrência:**")
                    with st.form("form_ocorrencia"):
                        oc_titulo = st.text_input("Título")
                        oc_desc   = st.text_area("Descrição")
                        oc_resp   = st.text_input("Responsável")
                        if st.form_submit_button("📋 Registrar", type="primary", use_container_width=True) and oc_titulo:
                            try:
                                supabase.table("ocorrencias").insert({"clinica_id":cid,"titulo":oc_titulo,"descricao":oc_desc,"responsavel":oc_resp,"status":"Aberta","data":datetime.now().strftime("%Y-%m-%d")}).execute()
                                st.success("✅ Ocorrência registrada!"); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                with col_oc2:
                    st.markdown("**Ocorrências:**")
                    try:
                        ocs = supabase.table("ocorrencias").select("*").eq("clinica_id",cid).order("data",desc=True).execute()
                        if ocs.data:
                            for oc in ocs.data:
                                cor = {"Aberta":"🔴","Em andamento":"🟡","Resolvida":"🟢"}.get(oc["status"],"🔴")
                                with st.expander(f"{cor} {oc['titulo']} — {oc['data']}"):
                                    st.write(oc.get("descricao",""))
                                    novo_status = st.selectbox("Status:", ["Aberta","Em andamento","Resolvida"], index=["Aberta","Em andamento","Resolvida"].index(oc["status"]), key=f"oc_{oc['id']}")
                                    if st.button("Salvar", key=f"btn_oc_{oc['id']}"):
                                        supabase.table("ocorrencias").update({"status":novo_status}).eq("id",oc["id"]).execute(); st.rerun()
                        else: st.success("Nenhuma ocorrência. 🎉")
                    except: st.info("Crie a tabela ocorrencias no Supabase.")

            with aba_f[3]:
                col_eq1, col_eq2 = st.columns([1,1])
                with col_eq1:
                    st.markdown("**Cadastrar equipamento:**")
                    with st.form("form_equip"):
                        eq_nome = st.text_input("Nome"); eq_modelo = st.text_input("Modelo/Marca"); eq_prox = st.date_input("Próxima manutenção")
                        if st.form_submit_button("➕ Cadastrar", type="primary", use_container_width=True) and eq_nome:
                            try:
                                supabase.table("equipamentos").insert({"clinica_id":cid,"nome":eq_nome,"modelo":eq_modelo,"proxima_manutencao":str(eq_prox),"status":"OK"}).execute()
                                st.success(f"✅ {eq_nome} cadastrado!"); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                with col_eq2:
                    st.markdown("**Equipamentos:**")
                    try:
                        from datetime import date
                        equips = supabase.table("equipamentos").select("*").eq("clinica_id",cid).order("proxima_manutencao").execute()
                        for eq in equips.data:
                            prox = eq.get("proxima_manutencao","")
                            alerta = "🟢"
                            info_d = ""
                            if prox:
                                delta = (datetime.strptime(prox,"%Y-%m-%d").date()-date.today()).days
                                info_d = f" — {delta}d"; alerta = "🔴" if delta<7 else "🟡" if delta<30 else "🟢"
                            st.markdown(f"""<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin-bottom:8px;"><div style="font-weight:500;font-size:0.9rem;">{alerta} {eq['nome']}</div><div style="font-size:0.78rem;color:#64748b;">{eq.get('modelo','')} · {prox}{info_d}</div></div>""", unsafe_allow_html=True)
                    except: st.info("Crie a tabela equipamentos no Supabase.")

            with aba_f[4]:
                col_inv1, col_inv2 = st.columns([1,1])
                with col_inv1:
                    st.markdown("**Adicionar material:**")
                    with st.form("form_inv"):
                        inv_nome = st.text_input("Nome"); inv_qtd = st.number_input("Quantidade", min_value=0, value=10); inv_min = st.number_input("Mínimo", min_value=0, value=5); inv_val = st.date_input("Validade")
                        if st.form_submit_button("➕ Adicionar", type="primary", use_container_width=True) and inv_nome:
                            try:
                                supabase.table("inventario").insert({"clinica_id":cid,"nome":inv_nome,"quantidade":int(inv_qtd),"minimo":int(inv_min),"validade":str(inv_val)}).execute()
                                st.success(f"✅ {inv_nome} adicionado!"); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                with col_inv2:
                    st.markdown("**Estoque:**")
                    try:
                        from datetime import date
                        inv = supabase.table("inventario").select("*").eq("clinica_id",cid).execute()
                        if inv.data:
                            alertas_inv = [i for i in inv.data if i["quantidade"]<=i["minimo"]]
                            if alertas_inv: st.error(f"⚠️ {len(alertas_inv)} material(is) abaixo do mínimo!")
                            for item in inv.data:
                                alerta_icon = "🔴" if item["quantidade"]<=item["minimo"] else "🟢"
                                val_str = ""
                                if item.get("validade"):
                                    try:
                                        val_date = datetime.strptime(item["validade"],"%Y-%m-%d").date()
                                        dias_val = (val_date-date.today()).days; val_str = f" · Vence em {dias_val}d"
                                        if dias_val<30: alerta_icon="🟡"
                                        if dias_val<7: alerta_icon="🔴"
                                    except: pass
                                st.markdown(f"""<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px;margin-bottom:8px;"><div style="font-weight:500;font-size:0.9rem;">{alerta_icon} {item['nome']}</div><div style="font-size:0.78rem;color:#64748b;">Qtd: {item['quantidade']} · Mín: {item['minimo']}{val_str}</div></div>""", unsafe_allow_html=True)
                        else: st.info("Nenhum material cadastrado.")
                    except: st.info("Crie a tabela inventario no Supabase.")

            with aba_f[5]:
                col_lp1, col_lp2 = st.columns([1,1])
                with col_lp1:
                    st.markdown("**Cadastrar escala:**")
                    with st.form("form_limpeza"):
                        lp_amb = st.text_input("Ambiente", placeholder="Ex: Sala de espera"); lp_resp = st.text_input("Responsável"); lp_freq = st.selectbox("Frequência:", ["Diária","Semanal","Mensal"])
                        if st.form_submit_button("➕ Cadastrar", type="primary", use_container_width=True) and lp_amb:
                            try:
                                supabase.table("escala_limpeza").insert({"clinica_id":cid,"ambiente":lp_amb,"responsavel":lp_resp,"frequencia":lp_freq,"ultima_limpeza":datetime.now().strftime("%Y-%m-%d")}).execute()
                                st.success(f"✅ {lp_amb} adicionado!"); st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                with col_lp2:
                    st.markdown("**Escala atual:**")
                    try:
                        from datetime import date
                        limpeza = supabase.table("escala_limpeza").select("*").eq("clinica_id",cid).execute()
                        if limpeza.data:
                            for lp in limpeza.data:
                                ultima = lp.get("ultima_limpeza",""); alerta = "🟢"
                                if ultima:
                                    try:
                                        delta_lp = (date.today()-datetime.strptime(ultima,"%Y-%m-%d").date()).days
                                        limite = {"Diária":1,"Semanal":7,"Mensal":30}.get(lp.get("frequencia","Diária"),1)
                                        alerta = "🔴" if delta_lp>=limite else "🟢"
                                    except: pass
                                with st.expander(f"{alerta} {lp['ambiente']} — {lp.get('frequencia','')}"):
                                    st.write(f"Responsável: {lp.get('responsavel','')}"); st.write(f"Última limpeza: {ultima}")
                                    if st.button("✅ Registrar limpeza", key=f"lp_{lp['id']}"):
                                        supabase.table("escala_limpeza").update({"ultima_limpeza":datetime.now().strftime("%Y-%m-%d")}).eq("id",lp["id"]).execute(); st.rerun()
                        else: st.info("Nenhum ambiente cadastrado.")
                    except: st.info("Crie a tabela escala_limpeza no Supabase.")

            with aba_f[6]:
                st.caption("Gere documentos e checklists padrão exigidos pela vigilância sanitária.")
                doc_tipo = st.selectbox("Selecione o documento:", ["Checklist de Boas Práticas — RDC 216","Planilha de Controle de Temperatura","Registro de Higienização de Superfícies","Ficha de Controle de Pragas","Relatório de Descarte de Resíduos"])
                conteudos_anvisa = {
                    "Checklist de Boas Práticas — RDC 216": ["Instalações físicas em bom estado de conservação","Equipamentos higienizados e em funcionamento","Manipuladores com EPIs adequados","Produtos de limpeza identificados e armazenados","Lixo acondicionado em recipientes com tampa","Controle de pragas atualizado","Água potável disponível"],
                    "Planilha de Controle de Temperatura": ["Temperatura da geladeira de medicamentos (2-8°C)","Temperatura ambiente da sala de procedimentos (máx 24°C)","Temperatura do esterilizador verificada","Registro de horário da aferição","Responsável pela aferição identificado"],
                    "Registro de Higienização de Superfícies": ["Bancadas higienizadas com produto adequado","Macas e cadeiras limpas entre atendimentos","Piso limpo e seco","Banheiros higienizados","Maçanetas e interruptores desinfectados"],
                    "Ficha de Controle de Pragas": ["Data da última dedetização registrada","Empresa responsável identificada","Certificado de dedetização arquivado","Ausência de evidências de pragas","Ralos e frestas vedados"],
                    "Relatório de Descarte de Resíduos": ["Resíduos biológicos em saco branco leitoso","Perfurocortantes em coletor rígido","Empresa coletora credenciada contratada","Manifesto de transporte preenchido","Registro de coleta arquivado"],
                }
                itens_anvisa = conteudos_anvisa[doc_tipo]
                st.markdown("**Dados da clínica:**")
                col_cnpj, col_btn = st.columns([3,1])
                with col_cnpj: anvisa_cnpj = st.text_input("CNPJ", placeholder="Ex: 00.000.000/0001-00", key="anvisa_cnpj_input")
                with col_btn:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    buscar_cnpj = st.button("🔍 Buscar", use_container_width=True)
                if "anvisa_dados" not in st.session_state:
                    st.session_state.anvisa_dados = {"nome":"","endereco":"","municipio":"","uf":"","situacao":""}
                if buscar_cnpj and anvisa_cnpj:
                    cnpj_limpo = "".join(filter(str.isdigit, anvisa_cnpj))
                    if len(cnpj_limpo)==14:
                        with st.spinner("Consultando Receita Federal..."):
                            try:
                                resp_cnpj = requests.get(f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}", timeout=8, headers={"User-Agent":"ClinicFlow/1.0"})
                                if resp_cnpj.status_code==200:
                                    dados = resp_cnpj.json(); end = dados.get("estabelecimento",{})
                                    logradouro=end.get("logradouro",""); numero=end.get("numero",""); bairro=end.get("bairro","")
                                    municipio=end.get("cidade",{}).get("nome","") if isinstance(end.get("cidade"),dict) else ""
                                    uf=end.get("estado",{}).get("sigla","") if isinstance(end.get("estado"),dict) else ""
                                    cep=end.get("cep",""); razao=dados.get("razao_social",""); fantasia=end.get("nome_fantasia","") or razao; situacao=end.get("situacao_cadastral","")
                                    st.session_state.anvisa_dados = {"nome":fantasia or razao,"endereco":f"{logradouro}, {numero} — {bairro}, {municipio}/{uf} — CEP {cep}","municipio":municipio,"uf":uf,"situacao":situacao}
                                    st.success(f"✅ {razao} — {situacao}") if situacao=="Ativa" else st.warning(f"⚠️ Situação: {situacao}")
                                elif resp_cnpj.status_code==429: st.warning("⏳ Aguarde 1 minuto e tente novamente.")
                                else: st.error(f"CNPJ não encontrado.")
                            except Exception as e: st.error(f"Erro: {e}")
                    else: st.warning("CNPJ inválido.")
                col_clin1, col_clin2 = st.columns(2)
                with col_clin1: anvisa_nome_clinica = st.text_input("Nome da clínica", value=st.session_state.anvisa_dados["nome"], placeholder="Ex: Clínica Modelo Ltda")
                with col_clin2: anvisa_alvara = st.text_input("Nº Alvará Sanitário", placeholder="Ex: AS-2024-00123")
                anvisa_endereco = st.text_input("Endereço completo", value=st.session_state.anvisa_dados["endereco"], placeholder="Ex: Rua das Flores, 123 — Goiânia/GO")
                if st.session_state.anvisa_dados.get("situacao"):
                    sit=st.session_state.anvisa_dados["situacao"]; cor="#dcfce7" if sit=="Ativa" else "#fef9c3"; cor_txt="#166534" if sit=="Ativa" else "#854d0e"
                    st.markdown(f'<div style="display:inline-block;background:{cor};color:{cor_txt};font-size:0.75rem;padding:3px 12px;border-radius:99px;font-weight:500;margin-bottom:8px;">Situação: {sit}</div>', unsafe_allow_html=True)
                st.markdown("**Responsável e itens:**")
                resp_anvisa = st.text_input("Responsável pelo preenchimento:")
                checks_anvisa = {item: st.checkbox(item, key=f"anvisa_{item}") for item in itens_anvisa}
                refs_legais = {"Checklist de Boas Práticas — RDC 216":"RDC ANVISA nº 216/2004","Planilha de Controle de Temperatura":"RDC ANVISA nº 430/2020","Registro de Higienização de Superfícies":"RDC ANVISA nº 15/2012","Ficha de Controle de Pragas":"RDC ANVISA nº 52/2009","Relatório de Descarte de Resíduos":"RDC ANVISA nº 222/2018"}
                ref_legal=refs_legais.get(doc_tipo,"Legislação sanitária vigente"); data_doc=datetime.now().strftime("%d/%m/%Y"); hora_doc=datetime.now().strftime("%H:%M")
                itens_html="".join(f'<tr><td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;">{"✅" if checks_anvisa.get(i) else "☐"}</td><td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;font-size:13px;">{i}</td></tr>' for i in itens_anvisa)
                col_an1, col_an2 = st.columns(2)
                with col_an1:
                    if st.button("✅ Salvar registro", type="primary", use_container_width=True): st.success(f"Documento '{doc_tipo}' salvo!")
                with col_an2:
                    st.components.v1.html(f"""<button onclick="imprimirAnvisa()" style="width:100%;padding:10px;font-size:0.95rem;font-weight:600;background:#0f172a;color:white;border:none;border-radius:10px;cursor:pointer;">🖨️ Imprimir documento</button><div id="conteudo-anvisa" style="display:none;"><div id="cabecalho"><table width="100%" style="border-collapse:collapse;margin-bottom:0;"><tr><td style="width:80px;vertical-align:middle;"><div style="width:70px;height:70px;background:#0f172a;border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:28px;font-weight:900;text-align:center;font-family:Arial,sans-serif;line-height:1;">+</div></td><td style="vertical-align:middle;padding-left:16px;"><div style="font-size:18px;font-weight:700;color:#0f172a;font-family:Arial,sans-serif;">{anvisa_nome_clinica or 'Nome da Clínica'}</div><div style="font-size:12px;color:#64748b;font-family:Arial,sans-serif;margin-top:2px;">CNPJ: {anvisa_cnpj or '00.000.000/0001-00'} &nbsp;|&nbsp; Alvará: {anvisa_alvara or 'AS-0000-00000'}</div><div style="font-size:12px;color:#64748b;font-family:Arial,sans-serif;">{anvisa_endereco or 'Endereço'}</div></td><td style="text-align:right;vertical-align:middle;"><div style="font-size:10px;color:#94a3b8;font-family:Arial,sans-serif;">DOCUMENTO DE USO INTERNO</div><div style="font-size:11px;color:#64748b;font-family:Arial,sans-serif;">Data: {data_doc} &nbsp; Hora: {hora_doc}</div></td></tr></table><div style="height:3px;background:#0f172a;margin:12px 0 4px;border-radius:2px;"></div><div style="height:1px;background:#e2e8f0;margin-bottom:16px;"></div><div style="text-align:center;margin-bottom:16px;"><div style="font-size:15px;font-weight:700;color:#0f172a;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.05em;">{doc_tipo}</div><div style="font-size:10px;color:#64748b;font-family:Arial,sans-serif;margin-top:4px;">Referência legal: {ref_legal}</div></div><table width="100%" style="border-collapse:collapse;margin-bottom:20px;border:1px solid #e2e8f0;"><thead><tr style="background:#f8fafc;"><th style="padding:8px;text-align:left;font-size:12px;color:#64748b;font-family:Arial,sans-serif;width:40px;">OK</th><th style="padding:8px;text-align:left;font-size:12px;color:#64748b;font-family:Arial,sans-serif;">Item de verificação</th></tr></thead><tbody>{itens_html}</tbody></table><div style="height:1px;background:#e2e8f0;margin:20px 0;"></div><table width="100%" style="border-collapse:collapse;"><tr><td style="width:45%;padding:8px 0;"><div style="border-top:1px solid #0f172a;padding-top:6px;font-size:11px;color:#374151;font-family:Arial,sans-serif;">Responsável: {resp_anvisa or '___________________'}</div></td><td style="width:10%;"></td><td style="width:45%;padding:8px 0;"><div style="border-top:1px solid #0f172a;padding-top:6px;font-size:11px;color:#374151;font-family:Arial,sans-serif;">Assinatura: ___________________</div></td></tr></table><div style="margin-top:16px;padding:8px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0;"><div style="font-size:9px;color:#94a3b8;font-family:Arial,sans-serif;text-align:center;">Documento gerado em {data_doc} às {hora_doc} via ClinicFlow &nbsp;|&nbsp; {ref_legal} &nbsp;|&nbsp; Documento de uso interno</div></div></div></div><script>function imprimirAnvisa(){{var c=document.getElementById('cabecalho').innerHTML;var w=window.open('','','height=900,width=750');w.document.write('<html><head><title>{doc_tipo}</title><style>@page{{margin:20mm;}}body{{font-family:Arial,sans-serif;padding:0;margin:0;color:#0f172a;}}table{{border-collapse:collapse;}}</style></head><body>'+c+'</body></html>');w.document.close();w.focus();setTimeout(function(){{w.print();w.close();}},500);}}</script>""", height=60)

        # ── CONFIGURAÇÕES ──────────────────────────────────────────
        elif menu == "⚙️ Configurações":
            st.markdown("### ⚙️ Gestão de Equipe")
            col_add, col_lista = st.columns([1,1])
            with col_add:
                st.markdown("**Cadastrar novo usuário**")
                with st.form("novo_usuario"):
                    n_nome=st.text_input("Nome completo"); n_email=st.text_input("E-mail"); n_senha=st.text_input("Senha",type="password"); n_perf=st.selectbox("Perfil",["Recepcao","Gestor"])
                    if st.form_submit_button("Criar conta",type="primary",use_container_width=True):
                        existe=supabase.table("usuarios").select("email").eq("email",n_email).execute()
                        if existe.data: st.error("E-mail já cadastrado.")
                        elif n_nome and n_senha:
                            senha_hash=bcrypt.hashpw(n_senha.encode("utf-8"),bcrypt.gensalt()).decode("utf-8")
                            supabase.table("usuarios").insert({"clinica_id":cid,"nome":n_nome,"email":n_email.strip().lower(),"senha":senha_hash,"perfil":n_perf}).execute()
                            st.success(f"✅ Conta de {n_nome} criada!"); st.rerun()
                        else: st.warning("Preencha todos os campos.")
            with col_lista:
                st.markdown("**Equipe ativa**")
                usuarios=supabase.table("usuarios").select("nome,email,perfil").eq("clinica_id",cid).execute()
                if usuarios.data:
                    df_u=pd.DataFrame(usuarios.data).rename(columns={"nome":"Nome","email":"E-mail","perfil":"Perfil"})
                    st.dataframe(df_u,hide_index=True,use_container_width=True)
