import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse

st.set_page_config(page_title="Gestão Clínica Inteligente", layout="wide") # Mudei para 'wide' para o Dashboard ficar mais largo e bonito

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

# --- TELA DE LOGIN ---
if not st.session_state.autenticado:
    # Usando colunas para centralizar o login na tela larga
    col_espaco1, col_login, col_espaco2 = st.columns([1, 2, 1])
    
    with col_login:
        st.title("🔐 Acesso ao Sistema")
        st.write("Utilize os dados de teste para entrar (E-mail: teste@alfa.com | Senha: 123)")
        
        with st.form("login_form"):
            email = st.text_input("E-mail:")
            senha = st.text_input("Senha:", type="password")
            submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)
            
            if submit:
                resposta = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
                
                if len(resposta.data) > 0:
                    usuario = resposta.data[0]
                    st.session_state.autenticado = True
                    st.session_state.clinica_id = usuario['clinica_id']
                    st.session_state.usuario_nome = usuario['nome']
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

# --- SISTEMA PRINCIPAL (PÓS-LOGIN) ---
else:
    with st.sidebar:
        st.write(f"Conectado como: **{st.session_state.usuario_nome}**")
        st.divider()
        if st.button("Sair do Sistema", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.clinica_id = None
            st.rerun()

    st.title("🏥 Painel de Gestão e Recuperação")
    
    # Criando as Abas
    aba_dashboard, aba_agenda = st.tabs(["📊 Dashboard Financeiro", "📅 Gestão de Agenda"])
    
    # ==========================================
    # ABA 1: DASHBOARD FINANCEIRO (Onde o cliente vê o valor)
    # ==========================================
    with aba_dashboard:
        st.subheader("Resumo do Mês (Impacto do Sistema)")
        
        # Métricas de impacto
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric(label="Consultas Agendadas", value="145", delta="12% a mais que mês passado")
        col_m2.metric(label="Taxa de Cancelamento", value="18%", delta="-5% com alertas", delta_color="inverse")
        col_m3.metric(label="Consultas Recuperadas", value="26", delta="Substitutos acionados")
        col_m4.metric(label="Receita Recuperada", value="R$ 3.900,00", delta="+ R$ 450,00 na semana")
        
        st.write("---")
        st.write("📈 **Projeção de Faturamento vs Receita Salva pelo App**")
        
        # Criando um gráfico de barras simulado para impressionar
        dados_grafico = pd.DataFrame({
            "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"],
            "Faturamento Base (R$)": [20000, 22000, 21000, 25000, 28000, 31000],
            "Recuperado pelo App (R$)": [0, 0, 0, 1500, 3200, 3900] # Simulando que o app foi instalado em Abril
        }).set_index("Mês")
        
        st.bar_chart(dados_grafico)
        st.caption("Nota: Estes são dados demonstrativos para apresentação do sistema.")

    # ==========================================
    # ABA 2: GESTÃO DE AGENDA (Onde a recepcionista trabalha)
    # ==========================================
    with aba_agenda:
        # Puxa os dados reais do banco
        resposta_agenda = supabase.table("agenda").select("*").eq("clinica_id", st.session_state.clinica_id).execute()
        agenda_df = pd.DataFrame(resposta_agenda.data)
        
        resposta_fila = supabase.table("fila_espera").select("*").eq("clinica_id", st.session_state.clinica_id).order("posicao").execute()
        fila_lista = resposta_fila.data
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📅 Agenda de Hoje")
            if not agenda_df.empty:
                st.dataframe(agenda_df[['horario', 'paciente_nome', 'status']], use_container_width=True, hide_index=True)
                
                st.write("---")
                paciente_cancelar = st.selectbox("Registrar cancelamento para:", agenda_df['paciente_nome'])
                
                if st.button("Confirmar Cancelamento e Buscar Substituto", type="primary"):
                    if len(fila_lista) > 0:
                        substituto = fila_lista[0]
                        horario_vago = agenda_df.loc[agenda_df['paciente_nome'] == paciente_cancelar, 'horario'].values[0]
                        
                        supabase.table("agenda").delete().eq("paciente_nome", paciente_cancelar).execute()
                        supabase.table("agenda").insert({"clinica_id": st.session_state.clinica_id, "horario": horario_vago, "paciente_nome": substituto['paciente_nome'], "status": "Avisando Paciente..."}).execute()
                        supabase.table("fila_espera").delete().eq("id", substituto['id']).execute()
                        
                        st.success(f"✅ Horário das {horario_vago} repassado para {substituto['paciente_nome']}!")
                        st.rerun()
                    else:
                        st.warning("Fila de espera vazia. O horário ficará vago.")
            else:
                st.write("Não há consultas agendadas.")

        with col2:
            st.subheader("📋 Fila de Espera")
            if len(fila_lista) > 0:
                for pessoa in fila_lista:
                    st.info(f"**{pessoa['paciente_nome']}**\n📞 {pessoa['telefone']}")
            else:
                st.write("Nenhum paciente na fila.")
