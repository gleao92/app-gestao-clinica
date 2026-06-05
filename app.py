import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse

st.set_page_config(page_title="Gestão Clínica Inteligente", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOMIZAÇÃO DE FRONT-END (CSS MÁGICO) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
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

    div[data-testid="stAlert"] {
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #f0f6ff;
        border-bottom: 3px solid #0052cc !important;
        color: #0052cc;
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

# --- ESTADO DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.clinica_id = None
    st.session_state.usuario_nome = ""
    st.session_state.perfil = ""

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    st.write("<br><br><br>", unsafe_allow_html=True)
    col_espaco1, col_login, col_espaco2 = st.columns([1, 2, 1])
    
    with col_login:
        st.markdown("<h1 style='text-align: center; color: #0052cc;'>Acesso ao Sistema</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Insira suas credenciais para gerir sua clínica.</p>", unsafe_allow_html=True)
        st.write("---")
        
        with st.form("login_form"):
            email = st.text_input("E-mail:")
            senha = st.text_input("Senha:", type="password")
            st.write("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Acessar Painel", type="primary", use_container_width=True)
            
            if submit:
                resposta = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
                
                if len(resposta.data) > 0:
                    usuario = resposta.data[0]
                    st.session_state.autenticado = True
                    st.session_state.clinica_id = usuario['clinica_id']
                    st.session_state.usuario_nome = usuario['nome']
                    
                    # LÓGICA À PROVA DE BALAS: Limpa espaços e força a primeira letra maiúscula
                    perfil_db = usuario.get('perfil')
                    if perfil_db:
                        st.session_state.perfil = str(perfil_db).strip().capitalize()
                    else:
                        st.session_state.perfil = 'Recepcao'
                        
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

# --- SISTEMA PRINCIPAL (PÓS-LOGIN) ---
else:
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2966/2966327.png", width=60)
        st.markdown(f"<h3>Olá, {st.session_state.usuario_nome}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; margin-top:-15px;'>Perfil: {st.session_state.perfil}</p>", unsafe_allow_html=True)
        st.divider()
        if st.button("Sair do Sistema", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.clinica_id = None
            st.session_state.usuario_nome = ""
            st.session_state.perfil = ""
            st.rerun()

    st.markdown("<h2 style='color: #333;'>🏥 Painel de Gestão Inteligente</h2>", unsafe_allow_html=True)
    
    # LÓGICA DE CONTROLE DE ACESSO
    if st.session_state.perfil == 'Gestor':
        abas_lista = ["📊 Dashboard Financeiro", "📅 Gestão de Agenda", "⚠️ Facilities", "⚙️ Configurações"]
        abas = st.tabs(abas_lista)
        aba_dashboard, aba_agenda, aba_facilities, aba_config = abas[0], abas[1], abas[2], abas[3]
    else:
        abas_lista = ["📅 Gestão de Agenda", "⚠️ Facilities"]
        abas = st.tabs(abas_lista)
        aba_agenda, aba_facilities = abas[0], abas[1]

    # === ABA: DASHBOARD FINANCEIRO (SÓ GESTOR VÊ) ===
    if st.session_state.perfil == 'Gestor':
        with aba_dashboard:
            st.subheader("Resumo do Mês (Impacto do Sistema)")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric(label="Consultas Agendadas", value="145", delta="12% a mais")
            col_m2.metric(label="Taxa de Cancelamento", value="18%", delta="-5% com alertas", delta_color="inverse")
            col_m3.metric(label="Consultas Recuperadas", value="26", delta="Substitutos acionados")
            col_m4.metric(label="Receita Recuperada", value="R$ 3.900,00", delta="+ R$ 450,00 na semana")
            st.write("---")
            st.write("📈 **Projeção de Faturamento vs Receita Salva pelo App**")
            dados_grafico = pd.DataFrame({
                "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"],
                "Faturamento Base (R$)": [20000, 22000, 21000, 25000, 28000, 31000],
                "Recuperado pelo App (R$)": [0, 0, 0, 1500, 3200, 3900]
            }).set_index("Mês")
            st.bar_chart(dados_grafico)

    # === ABA: GESTÃO DE AGENDA (TODOS VEEM) ===
    with aba_agenda:
        resposta_agenda = supabase.table("agenda").select("*").eq("clinica_id", st.session_state.clinica_id).execute()
        agenda_df = pd.DataFrame(resposta_agenda.data)
        resposta_fila = supabase.table("fila_espera").select("*").eq("clinica_id", st.session_state.clinica_id).order("posicao").execute()
        fila_lista = resposta_fila.data
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### 📅 Agenda de Hoje")
            if not agenda_df.empty:
                st.write("---")
                c_h, c_n, c_s, c
