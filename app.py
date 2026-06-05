if len(resposta.data) > 0:
                    usuario = resposta.data[0]
                    st.session_state.autenticado = True
                    st.session_state.clinica_id = usuario['clinica_id']
                    st.session_state.usuario_nome = usuario['nome']
                    
                    # --- CHAVE MESTRA DO DESENVOLVEDOR ---
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
