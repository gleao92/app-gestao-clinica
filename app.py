import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Gestão Clínica Inteligente", layout="wide")

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

    st.title("🏥 Painel de Gestão e Segurança")
    
    # Criando as 3 Abas
    aba_dashboard, aba_agenda, aba_facilities = st.tabs([
        "📊 Dashboard Financeiro", 
        "📅 Gestão de Agenda", 
        "⚠️ Facilities e Segurança"
    ])
    
    # === ABA 1: DASHBOARD FINANCEIRO ===
    with aba_dashboard:
        st.subheader("Resumo do Mês (Impacto do Sistema)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric(label="Consultas Agendadas", value="145", delta="12% a mais que mês passado")
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

    # === ABA 2: GESTÃO DE AGENDA ===
    with aba_agenda:
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
                        st.success(f"✅ Horário repassado para {substituto['paciente_nome']}!")
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

    # === ABA 3: FACILITIES E SEGURANÇA ===
    with aba_facilities:
        st.subheader("Gerador de Sinalização de Emergência")
        st.write("Crie avisos visuais de alta prioridade para impressão imediata, garantindo a segurança dos pacientes.")
        
        col_form, col_preview = st.columns([1, 1])
        
        with col_form:
            tipo_alerta = st.selectbox("Selecione o tipo de ocorrência:", [
                "Cuidado: Vidro Quebrado",
                "Atenção: Piso Molhado",
                "Perigo: Risco Biológico",
                "Aviso: Equipamento em Manutenção"
            ])
            
            # Mapeamento de símbolos automáticos para cada situação
            simbolos = {
                "Cuidado: Vidro Quebrado": "⚠️ 💥",
                "Atenção: Piso Molhado": "⚠️ 💧",
                "Perigo: Risco Biológico": "☣️ 🩸",
                "Aviso: Equipamento em Manutenção": "🛑 🔧"
            }
            simbolo_escolhido = simbolos[tipo_alerta]
            
            descricao_alerta = st.text_area("Instruções Adicionais (Opcional):", "Por favor, mantenha a distância. A equipe de manutenção já foi acionada para resolver a situação.")
            
        with col_preview:
            st.write("**Pré-visualização para Impressão:**")
            # Usando HTML/CSS para criar uma placa com design de alerta
            st.markdown(f"""
            <div style="border: 6px solid #d9534f; padding: 40px; text-align: center; border-radius: 12px; background-color: #fdf2f2;">
                <h1 style="font-size: 70px; margin: 0; color: #d9534f;">{simbolo_escolhido}</h1>
                <h1 style="color: #d9534f; font-family: 'Arial Black', sans-serif; font-size: 40px; text-transform: uppercase;">{tipo_alerta}</h1>
                <p style="font-size: 24px; font-weight: bold; color: #333; margin-top: 20px;">{descricao_alerta}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info("💡 **Dica de Uso:** Pressione **Ctrl + P** no teclado para imprimir esta placa em tamanho A4 e afixar imediatamente no local do incidente.")
