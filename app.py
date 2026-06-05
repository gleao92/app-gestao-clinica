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
    
    /* Estilo Premium para os Botões Padrões (Azul) */
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

    /* ESTILO ESPECÍFICO: Botão de Sair no Menu Lateral (Vermelho) */
    section[data-testid="stSidebar"] div.stButton > button:first-child {
        background-color: #dc3545 !important;
        margin-top: 50px; /* Empurra um pouco mais para baixo */
    }
    section[data-testid="stSidebar"] div.stButton > button:first-child:hover {
        background-color: #c82333 !important;
    }

    /* Estilo das caixas de alerta */
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
                    
                    if email == "teste@alfa.com":
                        st.session_state.perfil = "Gestor"
                    else:
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
    # ==========================================
    # MENU LATERAL (SIDEBAR)
    # ==========================================
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2966/2966327.png", width=60)
        st.markdown(f"<h3>Olá, {st.session_state.usuario_nome}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: gray; margin-top:-15px;'>Perfil: {st.session_state.perfil}</p>", unsafe_allow_html=True)
        st.divider()
        
        # Define as opções do menu dependendo do Perfil
        if st.session_state.perfil == 'Gestor':
            opcoes_menu = ["📊 Dashboard Financeiro", "📅 Gestão de Agenda", "⚠️ Facilities", "⚙️ Configurações"]
        else:
            opcoes_menu = ["📅 Gestão de Agenda", "⚠️ Facilities"]
            
        # O novo Menu Vertical
        st.markdown("**Navegação**")
        menu_selecionado = st.radio("", opcoes_menu, label_visibility="collapsed")
        
        # Quebras de linha para empurrar o botão vermelho para o fundo da tela
        st.write("<br><br><br><br><br><br>", unsafe_allow_html=True)
        
        # Botão de Sair do Sistema (Ficará vermelho por causa do CSS lá no topo)
        if st.button("Sair do Sistema", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.clinica_id = None
            st.session_state.usuario_nome = ""
            st.session_state.perfil = ""
            st.rerun()

    # ==========================================
    # ÁREA CENTRAL (CONTEÚDO DAS TELAS)
    # ==========================================
    st.markdown("<h2 style='color: #333;'>🏥 Painel de Gestão Inteligente</h2>", unsafe_allow_html=True)
    st.write("---")

    # === TELA 1: DASHBOARD FINANCEIRO ===
    if menu_selecionado == "📊 Dashboard Financeiro":
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

    # === TELA 2: GESTÃO DE AGENDA ===
    elif menu_selecionado == "📅 Gestão de Agenda":
        resposta_agenda = supabase.table("agenda").select("*").eq("clinica_id", st.session_state.clinica_id).execute()
        agenda_df = pd.DataFrame(resposta_agenda.data)
        
        resposta_fila = supabase.table("fila_espera").select("*").eq("clinica_id", st.session_state.clinica_id).order("posicao").execute()
        fila_lista = resposta_fila.data
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### 📅 Agenda de Hoje")
            if not agenda_df.empty:
                st.write("---")
                c_h, c_n, c_s, c_a = st.columns([1, 2, 1.5, 1.5])
                c_h.write("**Horário**")
                c_n.write("**Paciente**")
                c_s.write("**Status**")
                c_a.write("**Ação Rápida**")
                st.write("---")
                
                for index, row in agenda_df.iterrows():
                    c_horario, c_nome, c_status, c_acao = st.columns([1, 2, 1.5, 1.5])
                    c_horario.write(row['horario'])
                    c_nome.write(row['paciente_nome'])
                    
                    if row['status'] == 'Confirmado':
                        c_status.markdown("🟢 Confirmado")
                    else:
                        c_status.markdown("🟡 Pendente")
                    
                    mensagem_zap = f"Olá {row['paciente_nome']}, somos da Clínica. Podemos confirmar sua consulta de hoje às {row['horario']}?"
                    texto_codificado = urllib.parse.quote(mensagem_zap)
                    link_wpp = f"https://wa.me/5511999999999?text={texto_codificado}" 
                    
                    c_acao.markdown(f'<a href="{link_wpp}" target="_blank" style="text-decoration: none; background-color: #25D366; color: white; padding: 8px 15px; border-radius: 5px; font-weight: bold; font-size: 13px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">💬 Contatar</a>', unsafe_allow_html=True)
                
                st.write("---")
                st.markdown("### 🔁 Recuperador de Vagas")
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
            st.markdown("### 📋 Fila de Espera")
            if len(fila_lista) > 0:
                for pessoa in fila_lista:
                    st.info(f"👤 **{pessoa['paciente_nome']}**\n\n📞 {pessoa['telefone']}")
            else:
                st.write("Nenhum paciente na fila.")

    # === TELA 3: FACILITIES E SEGURANÇA ===
    elif menu_selecionado == "⚠️ Facilities":
        st.subheader("Gerador de Sinalização de Emergência")
        st.write("Crie avisos visuais de alta prioridade para impressão imediata.")
        
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
            descricao_alerta = st.text_area("Instruções Adicionais (Opcional):", "Por favor, mantenha a distância. A equipe de manutenção já foi acionada.")
            
        with col_preview:
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

    # === TELA 4: CONFIGURAÇÕES E EQUIPE ===
    elif menu_selecionado == "⚙️ Configurações":
        st.subheader("👥 Gestão de Equipe e Acessos")
        col_add, col_lista = st.columns([1, 1])
        
        with col_add:
            st.markdown("**Cadastrar Novo Usuário**")
            with st.form("form_novo_usuario"):
                novo_nome = st.text_input("Nome Completo")
                novo_email = st.text_input("E-mail de Acesso")
                nova_senha = st.text_input("Senha", type="password")
                novo_perfil = st.selectbox("Nível de Acesso da Conta", ["Recepcao", "Gestor"])
                
                submit_usuario = st.form_submit_button("Criar Conta", type="primary", use_container_width=True)
                
                if submit_usuario:
                    busca_email = supabase.table("usuarios").select("email").eq("email", novo_email).execute()
                    if len(busca_email.data) > 0:
                        st.error("❌ Este e-mail já existe no sistema.")
                    elif novo_nome and novo_senha:
                        supabase.table("usuarios").insert({
                            "clinica_id": st.session_state.clinica_id,
                            "nome": novo_nome,
                            "email": novo_email,
                            "senha": nova_senha,
                            "perfil": novo_perfil
                        }).execute()
                        st.success(f"✅ Conta de '{novo_nome}' criada com sucesso!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Preencha todos os campos antes de salvar.")
                        
        with col_lista:
            st.markdown("**Equipe Ativa**")
            usuarios_da_clinica = supabase.table("usuarios").select("nome, email, perfil").eq("clinica_id", st.session_state.clinica_id).execute()
            
            if len(usuarios_da_clinica.data) > 0:
                df_usuarios = pd.DataFrame(usuarios_da_clinica.data).rename(columns={"nome": "Nome", "email": "E-mail", "perfil": "Perfil"})
                st.dataframe(df_usuarios, hide_index=True, use_container_width=True)
