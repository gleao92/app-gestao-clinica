import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time
import requests

st.set_page_config(
    page_title="Gestão Clínica Inteligente", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CUSTOMIZAÇÃO DE FRONT-END (CSS MÁGICO COM DESTAQUE VERMELHO) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Destaque a setinha e borda do menu lateral */
    section[data-testid="stSidebar"] {
        border-right: 3px solid #dc3545 !important;
        background-color: #f9f9f9;
    }
    
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 1.5rem !important;
        margin-top: 10px;
        padding-left: 5px;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 1.05rem !important;
        color: #333333;
    }
    
    /* Mudar a cor da bolinha selecionada para Vermelho */
    div[data-baseweb="radio"] > div:first-child {
        background-color: #dc3545 !important;
    }

    div.stButton > button:first-child {
        background-color: #0052cc;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* Botão de Sair em Vermelho */
    section[data-testid="stSidebar"] div.stButton > button:first-child {
        background-color: #dc3545 !important;
        margin-top: 50px; 
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O BANCO DE DADOS ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- FUNÇÃO DO ROBÔ DE WHATSAPP (RODA EM SEGUNDO PLANO) ---
def disparar_whatsapp_real(nome_paciente, telefone, mensagem):
    try:
        url_gateway = st.secrets["WPP_API_URL"]
        token_gateway = st.secrets.get("WPP_API_KEY", "")
        numero_limpo = "".join(filter(str.isdigit, str(telefone)))
        if not numero_limpo.startswith("55") and len(numero_limpo) >= 10:
            numero_limpo = "55" + numero_limpo
        headers = {"Content-Type": "application/json", "apikey": token_gateway, "Authorization": f"Bearer {token_gateway}"}
        payload = {"number": numero_limpo, "phone": numero_limpo, "message": mensagem, "text": mensagem}
        st.toast("📡 Robô SaaS: Enviando notificação automática...", icon="🤖")
        requests.post(url_gateway, json=payload, headers=headers, timeout=8)
        st.toast(f"💬 WhatsApp enviado para {nome_paciente}!", icon="✅")
    except Exception as e:
        st.toast(f"❌ Falha no motor de WhatsApp", icon="💥")

# =========================================================================
# FLUXO 1: PÁGINA PÚBLICA DE AUTO-AGENDAMENTO
# =========================================================================
if st.query_params.get("view") == "agendar":
    st.write("<br><br>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        st.markdown("<h1 style='text-align: center; color: #0052cc;'>🏥 Portal de Agendamento</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Inscreva-se na nossa lista de prioridades.</p>", unsafe_allow_html=True)
        st.write("---")
        id_clinica_teste = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        with st.form("form_publico_agendar"):
            paciente_nome = st.text_input("Seu Nome Completo:")
            paciente_tel = st.text_input("Seu WhatsApp (com DDD):", placeholder="Ex: 11999999999")
            submit_publico = st.form_submit_button("Solicitar Vaga de Encaixe", type="primary", use_container_width=True)
            if submit_publico:
                if paciente_nome and paciente_tel:
                    fila_atual = supabase.table("fila_espera").select("posicao").eq("clinica_id", id_clinica_teste).order("posicao", desc=True).limit(1).execute()
                    proxima_posicao = 1
                    if len(fila_atual.data) > 0: proxima_posicao = fila_atual.data[0]['posicao'] + 1
                    supabase.table("fila_espera").insert({"clinica_id": id_clinica_teste, "paciente_nome": paciente_nome, "telefone": paciente_tel, "posicao": proxima_posicao}).execute()
                    st.balloons()
                    st.success(f"🎉 Tudo pronto! Posição na fila: #{proxima_posicao}.")
                else: st.warning("⚠️ Preencha nome e telefone.")

# =========================================================================
# FLUXO 2: SISTEMA INTERNO DA CLÍNICA
# =========================================================================
else:
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.clinica_id = None
        st.session_state.usuario_nome = ""
        st.session_state.perfil = ""

    if not st.session_state.autenticado:
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_espaco1, col_login, col_espaco2 = st.columns([1, 2, 1])
        with col_login:
            st.markdown("<h1 style='text-align: center; color: #0052cc;'>Acesso ao Sistema</h1>", unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("E-mail:")
                senha = st.text_input("Senha:", type="password")
                submit = st.form_submit_button("Acessar Painel", type="primary", use_container_width=True)
                if submit:
                    email_limpo = email.strip().lower()
                    resposta = supabase.table("usuarios").select("*").eq("email", email_limpo).eq("senha", senha).execute()
                    if len(resposta.data) > 0:
                        usuario = resposta.data[0]
                        st.session_state.autenticado = True
                        st.session_state.clinica_id = usuario['clinica_id']
                        st.session_state.usuario_nome = usuario['nome']
                        st.session_state.perfil = "Gestor" if email_limpo == "teste@alfa.com" else str(usuario.get('perfil', 'Recepcao')).strip().capitalize()
                        st.rerun()
                    else: st.error("E-mail ou senha incorretos.")

    else:
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/2966/2966327.png", width=60)
            st.markdown(f"<h3>Olá, {st.session_state.usuario_nome}</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: gray; margin-top:-15px;'>Perfil: {st.session_state.perfil}</p>", unsafe_allow_html=True)
            st.divider()
            opcoes_menu = ["📊 Dashboard Financeiro", "📅 Gestão de Agenda", "⚠️ Facilities", "⚙️ Configurações"] if st.session_state.perfil == 'Gestor' else ["📅 Gestão de Agenda", "⚠️ Facilities"]
            st.markdown("**Navegação**")
            menu_selecionado = st.radio("", opcoes_menu, label_visibility="collapsed")
            st.write("<br><br><br><br><br><br>", unsafe_allow_html=True)
            if st.button("Sair do Sistema", use_container_width=True):
                st.session_state.autenticado = False; st.rerun()

        st.markdown("<h2 style='color: #333;'>🏥 Painel de Gestão Inteligente</h2>", unsafe_allow_html=True)
        st.write("---")

        if menu_selecionado == "📊 Dashboard Financeiro":
            st.subheader("Resumo do Mês (Impacto do Sistema)")
            # [Lógica Dashboard omitida para brevidade]
        
        elif menu_selecionado == "📅 Gestão de Agenda":
            # ... (Lógica de Agenda conforme anterior)
            st.markdown("### 📅 Agenda de Hoje")
            # ... resto do código da agenda ...

        elif menu_selecionado == "⚠️ Facilities":
            st.subheader("Gerador de Sinalização de Emergência")
            # ... resto do código Facilities ...

        elif menu_selecionado == "⚙️ Configurações":
            st.subheader("👥 Gestão de Equipe e Acessos")
            # ... resto do código Configurações ...
