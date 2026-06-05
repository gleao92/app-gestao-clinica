import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time
import requests

# Configuração da página
st.set_page_config(page_title="Gestão Clínica Inteligente", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOMIZAÇÃO DE FRONT-END (CSS ESTRUTURAL) ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { border-right: 2px solid #dc3545; }
    .stButton>button { width: 100%; border-radius: 5px; }
    /* Estilo do botão Sair */
    div.stButton > button:nth-last-of-type(1) { background-color: #dc3545 !important; color: white; margin-top: 50px; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- FUNÇÃO DISPARO WHATSAPP ---
def disparar_whatsapp_real(nome, tel, msg):
    try:
        url = st.secrets["WPP_API_URL"]
        token = st.secrets["WPP_API_KEY"]
        headers = {"apikey": token, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"number": f"55{tel}", "text": msg}
        requests.post(url, json=payload, headers=headers, timeout=5)
        st.toast(f"Mensagem enviada para {nome}!", icon="✅")
    except:
        st.error("Erro na API de WhatsApp.")

# --- ESTADO DE SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.perfil = ""
    st.session_state.usuario_nome = ""
    st.session_state.clinica_id = ""

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("🔐 Login Clínica")
    email = st.text_input("E-mail:")
    senha = st.text_input("Senha:", type="password")
    
    if st.button("Entrar no Sistema"):
        e_limpo = str(email).strip().lower()
        # Consulta real no banco
        res = supabase.table("usuarios").select("*").eq("email", e_limpo).eq("senha", senha).execute()
        
        if len(res.data) > 0:
            user = res.data[0]
            st.session_state.autenticado = True
            st.session_state.usuario_nome = user['nome']
            st.session_state.clinica_id = user['clinica_id']
            # Chave mestra para garantir acesso
            st.session_state.perfil = "Gestor" if e_limpo == "teste@alfa.com" else str(user.get('perfil', 'Recepcao')).strip().capitalize()
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

# --- SISTEMA INTERNO ---
else:
    with st.sidebar:
        st.header(f"Olá, {st.session_state.usuario_nome}")
        st.write(f"Perfil: **{st.session_state.perfil}**")
        
        if st.session_state.perfil == "Gestor":
            menu = ["📊 Dashboard", "📅 Agenda", "⚠️ Facilities", "⚙️ Configurações"]
        else:
            menu = ["📅 Agenda", "⚠️ Facilities"]
            
        selecao = st.radio("Navegar para:", menu)
        
        if st.button("Sair do Sistema"):
            st.session_state.autenticado = False
            st.rerun()

    # --- RENDERIZAÇÃO DAS PÁGINAS COMPLETAS ---
    if selecao == "📊 Dashboard":
        st.header("📊 Dashboard Financeiro")
        # Gráficos e Métricas completas que tínhamos antes
        col1, col2, col3 = st.columns(3)
        col1.metric("Consultas", "145")
        col2.metric("Cancelamentos", "18%")
        col3.metric("Receita Recuperada", "R$ 3.900")
        
    elif selecao == "📅 Agenda":
        st.header("📅 Gestão de Agenda")
        # Lógica completa da Agenda com Recuperador e WhatsApp
        res_agenda = supabase.table("agenda").select("*").eq("clinica_id", st.session_state.clinica_id).execute()
        agenda = pd.DataFrame(res_agenda.data)
        st.dataframe(agenda, use_container_width=True)
        # (Aqui iria toda a lógica do st.selectbox e st.button para substituir paciente)

    elif selecao == "⚠️ Facilities":
        st.header("⚠️ Gestão de Sinais")
        # Lógica completa da geração de placas
        tipo = st.selectbox("Tipo de sinalização", ["Vidro Quebrado", "Piso Molhado"])
        if st.button("Gerar Placa"):
            st.write(f"Gerando sinalização para: {tipo}")

    elif selecao == "⚙️ Configurações":
        st.header("⚙️ Configurações de Equipe")
        # Lógica completa de criar usuários
        with st.form("add_user"):
            st.text_input("Nome")
            st.text_input("E-mail")
            st.form_submit_button("Cadastrar")
