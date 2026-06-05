import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time
import requests

# Configuração da página para expansão total
st.set_page_config(page_title="Gestão Clínica", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOMIZAÇÃO CSS PARA FORÇAR VISIBILIDADE ---
st.markdown("""
<style>
    /* Força a sidebar a ficar sempre visível e com destaque */
    [data-testid="stSidebar"] {
        min-width: 300px;
        background-color: #f0f2f6;
        border-right: 2px solid #dc3545;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- DISPARO WHATSAPP ---
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

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("🔐 Login Clínica")
    email = st.text_input("E-mail:")
    senha = st.text_input("Senha:", type="password")
    
    if st.button("Entrar no Sistema"):
        # Normalização para evitar erros de digitação
        e_limpo = str(email).strip().lower()
        
        # Simulação de verificação (Substituir pela consulta real ao Supabase)
        if e_limpo == "teste@alfa.com":
            st.session_state.autenticado = True
            st.session_state.perfil = "Gestor"
            st.session_state.usuario_nome = "Administrador"
            st.session_state.clinica_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
            st.rerun()
        else:
            st.error("E-mail ou senha incorretos.")

# --- SISTEMA INTERNO ---
else:
    with st.sidebar:
        st.header(f"Olá, {st.session_state.usuario_nome}")
        st.write(f"Perfil: **{st.session_state.perfil}**")
        
        # Opções fixas baseadas no perfil
        if st.session_state.perfil == "Gestor":
            menu = ["📊 Dashboard", "📅 Agenda", "⚠️ Facilities", "⚙️ Configurações"]
        else:
            menu = ["📅 Agenda", "⚠️ Facilities"]
            
        selecao = st.radio("Navegar para:", menu)
        
        st.divider()
        if st.button("Sair do Sistema"):
            st.session_state.autenticado = False
            st.rerun()

    # --- PÁGINAS ---
    if selecao == "📊 Dashboard":
        st.header("📊 Dashboard Financeiro")
        st.metric("Receita Recuperada", "R$ 3.900,00", "+500")
        
    elif selecao == "📅 Agenda":
        st.header("📅 Gestão de Agenda")
        # Coloca aqui a lógica da tabela de agenda
        st.write("Lista de consultas do dia...")
        
    elif selecao == "⚠️ Facilities":
        st.header("⚠️ Gestão de Sinais")
        # Coloca aqui a lógica de imprimir placas
        
    elif selecao == "⚙️ Configurações":
        st.header("⚙️ Configurações de Equipe")
        # Coloca aqui a lógica de usuários
