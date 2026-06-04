import streamlit as st
import pandas as pd
import urllib.parse # Biblioteca nativa para formatar o texto para links da web

st.set_page_config(page_title="Gestor de Agenda Inteligente", layout="centered")

# --- 1. Simulando o nosso Banco de Dados ---
if 'agenda' not in st.session_state:
    st.session_state.agenda = pd.DataFrame({
        'Horário': ['08:00', '09:00', '10:00', '11:00'],
        'Paciente': ['Carlos Silva', 'Ana Oliveira', 'Roberto Souza', 'Fernanda Lima'],
        'Status': ['Confirmado', 'Pendente', 'Confirmado', 'Pendente']
    })

# Agora a fila de espera guarda o nome e o telemóvel (com o código do país e área)
if 'fila_espera' not in st.session_state:
    st.session_state.fila_espera = [
        {'nome': 'Mariana Santos', 'telefone': '5562999998888'},
        {'nome': 'João Pedro', 'telefone': '5562999997777'}
    ]

# Variável para guardar os dados da mensagem atual do WhatsApp
if 'notificacao_pendente' not in st.session_state:
    st.session_state.notificacao_pendente = None

# --- 2. Interface do Sistema ---
st.title("🏥 Recuperador Inteligente de No-Show")
st.write("Gerencie cancelamentos e preencha horários vagos automaticamente através do WhatsApp.")
st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📅 Agenda de Hoje")
    st.dataframe(st.session_state.agenda, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.write("**Simular um Cancelamento:**")
    
    # Dropdown para escolher quem cancelou
    paciente_cancelar = st.selectbox("Selecione o paciente que acabou de cancelar/desmarcar:", st.session_state.agenda['Paciente'])
    
    if st.button("Registrar Cancelamento e Buscar Substituto", type="primary"):
        if len(st.session_state.fila_espera) > 0:
            # 1. Descobre o horário que ficou vago
            horario_vago = st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == paciente_cancelar, 'Horário'].values[0]
            
            # 2. Puxa o primeiro paciente da fila de espera automaticamente
            substituto = st.session_state.fila_espera.pop(0)
            
            # 3. Atualiza a tabela da agenda
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == paciente_cancelar, 'Paciente'] = substituto['nome']
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == substituto['nome'], 'Status'] = 'Avisando Paciente...'
            
            # 4. Cria a mensagem personalizada e formata para o link do WhatsApp
            texto_mensagem = f"Olá {substituto['nome']}, tudo bem? Aqui é da clínica. Uma vaga ficou disponível hoje no horário das {horario_vago}. Teria interesse em confirmar este horário?"
            texto_codificado = urllib.parse.quote(texto_mensagem) # Transforma espaços em %20, etc.
            
            # Link oficial do WhatsApp (wa.me)
            link_final = f"https://wa.me/{substituto['telefone']}?text={texto_codificado}"
            
            # Guarda os dados para exibir o botão de disparo no ecrã
            st.session_state.notificacao_pendente = {
                'nome': substituto['nome'],
                'horario': horario_vago,
                'link': link_final
            }
            st.rerun()
        else:
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == paciente_cancelar, 'Paciente'] = '--- VAGO ---'
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == '--- VAGO ---', 'Status'] = '-'
            st.session_state.notificacao_pendente = None
            st.rerun()

    # O "EFEITO UAU": Se houver uma notificação ativa, exibe o botão do WhatsApp
    if st.session_state.notificacao_pendente:
        st.write("---")
        st.info(f"👉 **Próxima Ação Necessária:** Notificar {st.session_state.notificacao_pendente['nome']} sobre a vaga das {st.session_state.notificacao_pendente['horario']}.")
        
        # Botão especial do Streamlit que abre links externos
        st.link_button(
            label="💬 Enviar Mensagem via WhatsApp Web",
            url=st.session_state.notificacao_pendente['link'],
            use_container_width=True
        )

with col2:
    st.subheader("📋 Fila de Espera")
    if len(st.session_state.fila_espera) > 0:
        for pessoa in st.session_state.fila_espera:
            st.warning(f"**{pessoa['nome']}**\n📞 {pessoa['telefone']}")
    else:
        st.write("Nenhum paciente na fila.")
