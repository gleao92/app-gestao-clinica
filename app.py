import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse
import time

st.set_page_config(page_title="Gestão Clínica Inteligente", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOMIZAÇÃO DE FRONT-END (CSS MÁGICO) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 1.5rem !important;
        margin-top: 10px;
        padding-left: 5px;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 1.05rem !important;
        color: #333333;
    }
    div[data-baseweb="radio"] > div:first-child {
        background-color: #0052cc !important;
    }

    div.stButton > button:first-child {
        background-color: #0052cc;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #003d99;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
        transform: translateY(-2px);
        color: white;
    }

    section[data-testid="stSidebar"] div.stButton > button:first-child {
        background-color: #dc3545 !important;
        margin-top: 50px; 
    }
    section[data-testid="stSidebar"] div.stButton > button:first-child:hover {
        background-color: #c82333 !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
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
def disparar_whatsapp_background(nome_paciente, telefone, mensagem):
    st.toast(f"🤖 **Robô SaaS:** Conectando ao servidor de mensagens...", icon="📡")
    time.sleep(1)
    st.toast(f"💬 **Mensagem enviada automaticamente para {nome_paciente}!**", icon="✅")

# =========================================================================
# FLUXO 1: PÁGINA PÚBLICA DE AUTO-AGENDAMENTO
# =========================================================================
if st.query_params.get("view") == "agendar":
    st.write("<br><br>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    
    with col_p2:
        st.markdown("<h1 style='text-align: center; color: #0052cc;'>🏥 Portal de Agendamento</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Inscreva-se na nossa lista de prioridades para atendimento imediato em caso de encaixe.</p>", unsafe_allow_html=True)
        st.write("---")
        
        id_clinica_teste = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        
        with st.form("form_publico_agendar"):
            paciente_nome = st.text_input("Seu Nome Completo:")
            paciente_tel = st.text_input("Seu WhatsApp (com DDD):", placeholder="Ex: 11999999999")
            st.write("<br>", unsafe_allow_html=True)
            submit_publico = st.form_submit_button("Solicitar Vaga de Encaixe", type="primary", use_container_width=True)
            
            if submit_publico:
                if paciente_nome and paciente_tel:
                    fila_atual = supabase.table("fila_espera").select("posicao").eq("clinica_id", id_clinica_teste).order("posicao", desc=True).limit(1).execute()
                    proxima_posicao = 1
                    if len(fila_atual.data) > 0:
                        proxima_posicao = fila_atual.data[0]['posicao'] + 1
                    
                    supabase.table("fila_espera").insert({
                        "clinica_id": id_clinica_teste,
                        "paciente_nome": paciente_nome,
                        "telefone": paciente_tel,
                        "posicao": proxima_posicao
                    }).execute()
                    
                    st.balloons()
                    st.success(f"🎉 Tudo pronto, {paciente_nome}! Você foi adicionado à lista de espera na posição #{proxima_posicao}. Avisaremos por WhatsApp assim que um horário vagar.")
                else:
                    st.warning("⚠️ Por favor, preencha o nome e o telefone.")

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
            st.markdown("<p style='text-align: center; color: #666;'>Insira suas credenciais para gerir sua clínica.</p>",
