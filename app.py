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
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "➕ Novo Cliente",
        "📝 Registar Visita",
        "📋 Histórico & Clientes",
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
# TAB 4: AGENDA & TO-DO LIST
# ---------------------------------------------------------
with tab4:
    st.subheader("Agenda de Tarefas & Lembretes")

    # Formulário para criar nova tarefa
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
    # Query com JOIN para trazer o nome do restaurante
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

    # Expandível para ver o histórico de tarefas concluídas
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