import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestor de Agenda Inteligente", layout="centered")

# --- 1. Simulando nosso Banco de Dados ---
# Usamos o session_state para a agenda não resetar quando a tela atualizar
if 'agenda' not in st.session_state:
    st.session_state.agenda = pd.DataFrame({
        'Horário': ['08:00', '09:00', '10:00', '11:00'],
        'Paciente': ['Carlos Silva', 'Ana Oliveira', 'Roberto Souza', 'Fernanda Lima'],
        'Status': ['Confirmado', 'Pendente', 'Confirmado', 'Pendente']
    })

if 'fila_espera' not in st.session_state:
    st.session_state.fila_espera = ['Mariana Santos (Urgência)', 'João Pedro (Rotina)']

# --- 2. Interface do Sistema ---
st.title("🏥 Recuperador Inteligente de No-Show")
st.write("Gerencie cancelamentos e preencha horários vagos automaticamente.")
st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📅 Agenda de Hoje")
    
    # Mostra a agenda atual
    st.dataframe(st.session_state.agenda, use_container_width=True, hide_index=True)
    
    st.write("---")
    st.write("**Simular um Cancelamento:**")
    
    # Dropdown para escolher quem cancelou
    paciente_cancelar = st.selectbox("Selecione o paciente que acabou de cancelar/desmarcar:", st.session_state.agenda['Paciente'])
    
    # O MOTOR INTELIGENTE: Botão de ação
    if st.button("Registrar Cancelamento e Buscar Substituto", type="primary"):
        if len(st.session_state.fila_espera) > 0:
            # Descobre o horário que ficou vago
            horario_vago = st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == paciente_cancelar, 'Horário'].values[0]
            
            # Puxa o primeiro da fila de espera
            novo_paciente = st.session_state.fila_espera.pop(0)
            
            # Atualiza a agenda com o novo paciente
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == paciente_cancelar, 'Paciente'] = novo_paciente
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == novo_paciente, 'Status'] = 'Enviando WhatsApp...'
            
            st.success(f"✅ Cancelamento registrado! O horário das {horario_vago} foi repassado automaticamente para {novo_paciente}.")
            st.rerun() # Atualiza a tela para mostrar a nova tabela
        else:
            st.warning("Cancelamento registrado, mas a fila de espera está vazia. O horário ficará vago.")
            # Apenas remove o paciente
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == paciente_cancelar, 'Paciente'] = '--- VAGO ---'
            st.session_state.agenda.loc[st.session_state.agenda['Paciente'] == '--- VAGO ---', 'Status'] = '-'
            st.rerun()

with col2:
    st.subheader("📋 Fila de Espera")
    if len(st.session_state.fila_espera) > 0:
        for pessoa in st.session_state.fila_espera:
            st.info(pessoa)
    else:
        st.write("A fila de espera está vazia no momento.")