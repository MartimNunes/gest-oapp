import sqlite3
import pandas as pd
import streamlit as st

# Configuração da página para telemóveis e computadores
st.set_page_config(
    page_title="Gestão de Vinhos & Clientes",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --- CONEXÃO E CRIAÇÃO DA BASE DE DADOS (SQLite) ---
def get_db_connection():
    conn = sqlite3.connect("gestao_vinhos.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de Clientes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_restaurante TEXT NOT NULL,
            responsavel TEXT,
            contacto TEXT,
            cidade TEXT,
            estado TEXT DEFAULT 'Prospeto'
        )
    """
    )

    # Tabela de Interações
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS interacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            data TEXT NOT NULL,
            notas TEXT,
            acordo TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """
    )

    # Tabela de Tarefas / Agenda / To-Do List
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            titulo TEXT NOT NULL,
            data_limite TEXT,
            prioridade TEXT DEFAULT 'Média',
            concluida INTEGER DEFAULT 0,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """
    )

    conn.commit()
    conn.close()


init_db()

# --- INTERFACE PRINCIPAL ---
st.title("🍷 Gestão Diária de Vendas")
st.caption("Registo de visitas, clientes, acordos comerciais e agenda")

# Separadores (Tabs)
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "➕ Novo Cliente",
        "📝 Registar Visita",
        "📋 Clientes & Histórico",
        "✏️ Editar / Gerir Clientes",
        "📅 Agenda / To-Do",
    ]
)

# ---------------------------------------------------------
# TAB 1: ADICIONAR CLIENTE / RESTAURANTE
# ---------------------------------------------------------
with tab1:
    st.subheader("Adicionar Restaurante")

    with st.form("form_novo_cliente", clear_on_submit=True):
        nome = st.text_input("Nome do Restaurante *")
        responsavel = st.text_input("Nome do Responsável / Sommelier")
        col_tel, col_cid = st.columns(2)
        with col_tel:
            contacto = st.text_input("Contacto Telefónico")
        with col_cid:
            cidade = st.text_input("Cidade / Localidade")

        estado = st.selectbox(
            "Estado da Relação Comercial",
            ["Prospeto", "Em Negociação", "Cliente Ativo", "Sem Interesse"],
        )

        submetido = st.form_submit_button("Guardar Restaurante")

        if submetido:
            if not nome.strip():
                st.error("O nome do restaurante é obrigatório!")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO clientes (nome_restaurante, responsavel, contacto, cidade, estado)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (nome, responsavel, contacto, cidade, estado),
                )
                conn.commit()
                conn.close()
                st.success(
                    f"Restaurante **{nome}** adicionado com sucesso!"
                )
                st.rerun()

# ---------------------------------------------------------
# TAB 2: REGISTAR VISITA / INTERAÇÃO / ACORDO
# ---------------------------------------------------------
with tab2:
    st.subheader("Registar Visita ou Acordo")

    conn = get_db_connection()
    clientes_df = pd.read_sql_query(
        "SELECT id, nome_restaurante, cidade FROM clientes", conn
    )
    conn.close()

    if clientes_df.empty:
        st.warning("Adiciona primeiro um restaurante na aba 'Novo Cliente'.")
    else:
        opcoes_clientes = {
            f"{row['nome_restaurante']} ({row['cidade']})": row["id"]
            for _, row in clientes_df.iterrows()
        }

        cliente_selecionado = st.selectbox(
            "Selecionar Restaurante", list(opcoes_clientes.keys())
        )
        cliente_id = opcoes_clientes[cliente_selecionado]

        data_visita = st.date_input("Data da Visita")
        notas = st.text_area(
            "Notas da Reunião",
            placeholder="Ex: Gostou do Vinho Reserva, achou o valor competitivo...",
        )
        acordo = st.text_area(
            "Acordo Fechado / Próximo Passo",
            placeholder="Ex: Venda de 3 caixas fechada. Enviar amostras da colheita especial no dia 15.",
        )

        if st.button("Guardar Interação"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO interacoes (cliente_id, data, notas, acordo)
                VALUES (?, ?, ?, ?)
            """,
                (cliente_id, str(data_visita), notas, acordo),
            )
            conn.commit()
            conn.close()
            st.success("Interação registada com sucesso!")
            st.rerun()

# ---------------------------------------------------------
# TAB 3: CONSULTAR HISTÓRICO E CLIENTES
# ---------------------------------------------------------
with tab3:
    st.subheader("Os Teus Clientes e Histórico")

    conn = get_db_connection()
    df_clientes = pd.read_sql_query("SELECT * FROM clientes", conn)

    if df_clientes.empty:
        st.info("Ainda não tens clientes registados.")
    else:
        st.dataframe(
            df_clientes,
            column_config={
                "id": "ID",
                "nome_restaurante": "Restaurante",
                "responsavel": "Responsável",
                "contacto": "Contacto",
                "cidade": "Cidade",
                "estado": "Estado",
            },
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Histórico Detalhado por Restaurante")

        opcoes_hist = {
            f"{row['nome_restaurante']} ({row['cidade']})": row["id"]
            for _, row in df_clientes.iterrows()
        }
        rest_hist = st.selectbox(
            "Escolhe o restaurante para ver o histórico:",
            list(opcoes_hist.keys()),
            key="sb_hist",
        )

        if rest_hist:
            id_rest = opcoes_hist[rest_hist]
            df_interacoes = pd.read_sql_query(
                f"SELECT data AS Data, notas AS 'Notas da Visita', acordo AS 'Acordo / Resultado' FROM interacoes WHERE cliente_id = {id_rest} ORDER BY id DESC",
                conn,
            )

            if df_interacoes.empty:
                st.write("Sem registos de visitas para este restaurante.")
            else:
                for _, row in df_interacoes.iterrows():
                    with st.expander(f"🗓️ Visita em: {row['Data']}"):
                        st.write(f"**Notas:** {row['Notas da Visita']}")
                        st.write(f"**Acordo/Resultado:** {row['Acordo / Resultado']}")

    conn.close()

# ---------------------------------------------------------
# TAB 4: EDITAR / GERIR CLIENTES
# ---------------------------------------------------------
with tab4:
    st.subheader("Editar Dados do Restaurante")

    conn = get_db_connection()
    df_editar = pd.read_sql_query("SELECT * FROM clientes", conn)

    if df_editar.empty:
        st.info("Ainda não há restaurantes para editar.")
    else:
        dict_clientes = {
            f"{row['nome_restaurante']} ({row['cidade']})": row["id"]
            for _, row in df_editar.iterrows()
        }
        rest_para_editar = st.selectbox(
            "Seleciona o restaurante a alterar/eliminar:",
            list(dict_clientes.keys()),
        )

        id_edit = dict_clientes[rest_para_editar]
        dados_atuais = df_editar[df_editar["id"] == id_edit].iloc[0]

        # Formulário preenchido com os dados atuais
        with st.form("form_editar_cliente"):
            novo_nome = st.text_input(
                "Nome do Restaurante", value=dados_atuais["nome_restaurante"]
            )
            novo_responsavel = st.text_input(
                "Responsável / Sommelier",
                value=dados_atuais["responsavel"] or "",
            )

            col_t, col_c = st.columns(2)
            with col_t:
                novo_contacto = st.text_input(
                    "Contacto", value=dados_atuais["contacto"] or ""
                )
            with col_c:
                nova_cidade = st.text_input(
                    "Cidade", value=dados_atuais["cidade"] or ""
                )

            estados_possiveis = [
                "Prospeto",
                "Em Negociação",
                "Cliente Ativo",
                "Sem Interesse",
            ]
            idx_estado = (
                estados_possiveis.index(dados_atuais["estado"])
                if dados_atuais["estado"] in estados_possiveis
                else 0
            )
            novo_estado = st.selectbox(
                "Estado da Relação", estados_possiveis, index=idx_estado
            )

            col_save, col_del = st.columns([1, 1])
            with col_save:
                btn_atualizar = st.form_submit_button("💾 Guardar Alterações")

        if btn_atualizar:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE clientes 
                SET nome_restaurante = ?, responsavel = ?, contacto = ?, cidade = ?, estado = ?
                WHERE id = ?
            """,
                (
                    novo_nome,
                    novo_responsavel,
                    novo_contacto,
                    nova_cidade,
                    novo_estado,
                    id_edit,
                ),
            )
            conn.commit()
            st.success("Dados atualizados com sucesso!")
            st.rerun()

        st.divider()
        # Zona de Eliminação
        with st.expander("🚨 Zona de Perigo: Eliminar Restaurante"):
            st.warning(
                "Atenção: Ao eliminar um restaurante, as visitas e tarefas associadas também serão apagadas."
            )
            if st.button("❌ Eliminar Este Restaurante Permanentemente"):
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM interacoes WHERE cliente_id = ?", (id_edit,)
                )
                cursor.execute(
                    "DELETE FROM tarefas WHERE cliente_id = ?", (id_edit,)
                )
                cursor.execute("DELETE FROM clientes WHERE id = ?", (id_edit,))
                conn.commit()
                st.success("Restaurante eliminado com sucesso!")
                st.rerun()

    conn.close()

# ---------------------------------------------------------
# TAB 5: AGENDA & TO-DO LIST
# ---------------------------------------------------------
with tab5:
    st.subheader("Agenda de Tarefas & Lembretes")

    with st.form("form_nova_tarefa", clear_on_submit=True):
        st.write("**Criar Novo Lembrete / Tarefa**")
        titulo_tarefa = st.text_input(
            "Descrição da Tarefa *",
            placeholder="Ex: Enviar catálogo em PDF / Ligar para fechar encomenda",
        )

        conn = get_db_connection()
        clientes_df_agenda = pd.read_sql_query(
            "SELECT id, nome_restaurante FROM clientes", conn
        )
        conn.close()

        opcoes_rest_agenda = {"Nenhum / Geral": None}
        if not clientes_df_agenda.empty:
            for _, r in clientes_df_agenda.iterrows():
                opcoes_rest_agenda[r["nome_restaurante"]] = r["id"]

        col_rest, col_data, col_prio = st.columns(3)
        with col_rest:
            rest_assoc = st.selectbox(
                "Restaurante Associado", list(opcoes_rest_agenda.keys())
            )
        with col_data:
            data_limite = st.date_input("Data Limite / Agendamento")
        with col_prio:
            prioridade = st.selectbox(
                "Prioridade",
                ["Alta 🔴", "Média 🟡", "Baixa 🔵"],
                index=1,
            )

        btn_add_tarefa = st.form_submit_button("Adicionar Tarefa")

        if btn_add_tarefa:
            if not titulo_tarefa.strip():
                st.error("A descrição da tarefa é obrigatória!")
            else:
                c_id = opcoes_rest_agenda[rest_assoc]
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO tarefas (cliente_id, titulo, data_limite, prioridade, concluida)
                    VALUES (?, ?, ?, ?, 0)
                """,
                    (c_id, titulo_tarefa, str(data_limite), prioridade),
                )
                conn.commit()
                conn.close()
                st.success("Tarefa adicionada à agenda!")
                st.rerun()

    st.divider()
    st.subheader("As Tuas Tarefas Pendentes")

    conn = get_db_connection()
    query_tarefas = """
        SELECT t.id, t.titulo, t.data_limite, t.prioridade, t.concluida, c.nome_restaurante 
        FROM tarefas t
        LEFT JOIN clientes c ON t.cliente_id = c.id
        WHERE t.concluida = 0
        ORDER BY t.data_limite ASC
    """
    df_tarefas = pd.read_sql_query(query_tarefas, conn)

    if df_tarefas.empty:
        st.success("🎉 Não tens tarefas pendentes na tua agenda!")
    else:
        for _, row in df_tarefas.iterrows():
            col1, col2 = st.columns([4, 1])

            rest_info = (
                f" 🏢 *({row['nome_restaurante']})*"
                if row["nome_restaurante"]
                else ""
            )
            col1.markdown(
                f"**{row['prioridade']}** | 🗓️ **{row['data_limite']}** - {row['titulo']}{rest_info}"
            )

            if col2.button("Concluir ✅", key=f"btn_concluir_{row['id']}"):
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tarefas SET concluida = 1 WHERE id = ?",
                    (row["id"],),
                )
                conn.commit()
                st.rerun()

    with st.expander("Ver Tarefas Concluídas"):
        df_concluidas = pd.read_sql_query(
            "SELECT t.titulo, t.data_limite, c.nome_restaurante FROM tarefas t LEFT JOIN clientes c ON t.cliente_id = c.id WHERE t.concluida = 1 ORDER BY t.id DESC",
            conn,
        )
        if df_concluidas.empty:
            st.write("Nenhuma tarefa concluída recentemente.")
        else:
            for _, r_conc in df_concluidas.iterrows():
                st.text(
                    f"✔ {r_conc['data_limite']} - {r_conc['titulo']} ({r_conc['nome_restaurante'] or 'Geral'})"
                )

    conn.close()
