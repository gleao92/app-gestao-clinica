import streamlit as st
import pandas as pd
from supabase import create_client, Client
import urllib.parse

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
        # O TEXTO DE TESTE FOI REMOVIDO DAQUI PARA UM VISUAL MAIS PROFISSIONAL
        
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

    st.title("🏥 Painel de Gestão Inteligente")
    
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

    # === ABA 2: GESTÃO DE AGENDA (COM AUTOMAÇÃO WHATSAPP) ===
    with aba_agenda:
        resposta_agenda = supabase.table("agenda").select("*").eq("clinica_id", st.session_state.clinica_id).execute()
        agenda_df = pd.DataFrame(resposta_agenda.data)
        
        resposta_fila = supabase.table("fila_espera").select("*").eq("clinica_id", st.session_state.clinica_id).order("posicao").execute()
        fila_lista = resposta_fila.data
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("📅 Agenda de Hoje")
            if not agenda_df.empty:
                st.write("---")
                # Cabeçalho da lista
                c_h, c_n, c_s, c_a = st.columns([1, 2, 1.5, 1.5])
                c_h.write("**Horário**")
                c_n.write("**Paciente**")
                c_s.write("**Status**")
                c_a.write("**Ação Rápida**")
                st.write("---")
                
                # Linhas da agenda com botão dinâmico
                for index, row in agenda_df.iterrows():
                    c_horario, c_nome, c_status, c_acao = st.columns([1, 2, 1.5, 1.5])
                    c_horario.write(row['horario'])
                    c_nome.write(row['paciente_nome'])
                    
                    if row['status'] == 'Confirmado':
                        c_status.markdown("🟢 Confirmado")
                    else:
                        c_status.markdown("🟡 Pendente")
                    
                    # Motor do WhatsApp (Cria mensagem pré-preenchida)
                    mensagem_zap = f"Olá {row['paciente_nome']}, somos da Clínica. Podemos confirmar sua consulta de hoje às {row['horario']}?"
                    texto_codificado = urllib.parse.quote(mensagem_zap)
                    link_wpp = f"https://wa.me/5511999999999?text={texto_codificado}" # Número de teste
                    
                    c_acao.markdown(f'<a href="{link_wpp}" target="_blank" style="text-decoration: none; background-color: #25D366; color: white; padding: 6px 15px; border-radius: 5px; font-weight: bold; font-size: 13px;">💬 Contatar</a>', unsafe_allow_html=True)
                
                st.write("---")
                st.subheader("🔁 Recuperador de Vagas")
                paciente_cancelar = st.selectbox("Registrar cancelamento e repassar horário de:", agenda_df['paciente_nome'])
                
                if st.button("Substituir Paciente Automaticamente", type="primary"):
                    if len(fila_lista) > 0:
                        substituto = fila_lista[0]
                        horario_vago = agenda_df.loc[agenda_df['paciente_nome'] == paciente_cancelar, 'horario'].values[0]
                        
                        supabase.table("agenda").delete().eq("paciente_nome", paciente_cancelar).execute()
                        supabase.table("agenda").insert({"clinica_id": st.session_state.clinica_id, "horario": horario_vago, "paciente_nome": substituto['paciente_nome'], "status": "Pendente"}).execute()
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
            
            simbolos = {
                "Cuidado: Vidro Quebrado": "⚠️ 💥",
                "Atenção: Piso Molhado": "⚠️ 💧",
                "Perigo: Risco Biológico": "☣️ 🩸",
                "Aviso: Equipamento em Manutenção": "🛑 🔧"
            }
            simbolo_escolhido = simbolos[tipo_alerta]
            
            descricao_alerta = st.text_area("Instruções Adicionais (Opcional):", "Por favor, mantenha a distância. A equipe de manutenção já foi acionada para resolver a situação.")
            
        with col_preview:
            st.write("**Pré-visualização e Impressão:**")
            
            html_impressao = f"""
            <div id="placa" style="border: 10px solid #d9534f; padding: 30px; text-align: center; border-radius: 15px; background-color: #fdf2f2; font-family: 'Arial', sans-serif;">
                <div style="font-size: 70px; margin: 0; line-height: 1;">{simbolo_escolhido}</div>
                <div style="color: #d9534f; font-weight: 900; font-size: 35px; text-transform: uppercase; margin-top: 15px;">{tipo_alerta}</div>
                <div style="font-size: 20px; font-weight: bold; color: #333; margin-top: 25px;">{descricao_alerta}</div>
            </div>
            
            <div style="text-align: center; margin-top: 25px;">
                <button onclick="imprimirPlaca()" style="padding: 15px 30px; font-size: 18px; font-weight: bold; background-color: #d9534f; color: white; border: none; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                    🖨️ CLIQUE AQUI PARA IMPRIMIR
                </button>
            </div>

            <script>
            function imprimirPlaca() {{
                var conteudo = document.getElementById('placa').innerHTML;
                var janela = window.open('', '', 'height=800,width=800');
                janela.document.write('<html><head><title>Imprimir Sinalização</title>');
                janela.document.write('<style>');
                janela.document.write('body {{ display: flex; justify-content: center; align-items: center; height: 90vh; margin: 0; font-family: sans-serif; }}');
                janela.document.write('#container {{ border: 15px solid #d9534f; padding: 60px; text-align: center; border-radius: 20px; background-color: #fdf2f2; width: 80%; }}');
                janela.document.write('</style></head><body>');
                janela.document.write('<div id="container">' + conteudo + '</div>');
                janela.document.write('</body></html>');
                janela.document.close();
                janela.focus();
                setTimeout(function() {{ janela.print(); janela.close(); }}, 500);
            }}
            </script>
            """
            st.components.v1.html(html_impressao, height=450)
