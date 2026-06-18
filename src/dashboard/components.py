import streamlit as st
import polars as pl
from src.dashboard.config import carregar_notas_maos, salvar_nota_mao

def render_hand_notes_editor(df_polars: pl.DataFrame, editor_key: str, custom_column_config: dict):
    """
    Renderiza um st.data_editor para avaliar mãos (Hero/Villain) com persistência automática no arquivo JSON.
    
    Args:
        df_polars: O DataFrame Polars contendo no mínimo a coluna 'hand_id' para servir de âncora.
        editor_key: Uma chave única para o st.data_editor (Streamlit UI key).
        custom_column_config: Dicionário contendo as configurações de coluna para o Streamlit.
    """
    if df_polars.height == 0:
        return
        
    notas_maos = carregar_notas_maos()
    
    # 1. Conversão e Injeção de Estado Baseado no Arquivo Físico
    df_pd = df_polars.to_pandas()
    df_pd["Avaliação"] = df_pd["hand_id"].apply(lambda x: notas_maos.get(x, {}).get("flag", "❔ Pendente"))
    df_pd["Anotações"] = df_pd["hand_id"].apply(lambda x: notas_maos.get(x, {}).get("nota", ""))

    # 2. Configurações base das colunas injetadas
    base_config = {
        "Avaliação": st.column_config.SelectboxColumn(
            "Avaliação",
            options=["❔ Pendente", "✅ Acerto (Cooler)", "❌ Erro (Value Owned)"],
            required=True
        ),
        "Anotações": st.column_config.TextColumn("Anotações")
    }
    
    # Mescla configurações base com as customizadas (prioridade para as customizadas se sobrescreverem)
    final_config = {**base_config, **custom_column_config}

    # 3. Renderização
    edited_df = st.data_editor(
        df_pd,
        column_config=final_config,
        hide_index=True,
        use_container_width=True,
        key=editor_key
    )

    # 4. Sincronização Bidirecional (Persistência)
    for _, row in edited_df.iterrows():
        h_id = row["hand_id"]
        nova_nota = row["Anotações"]
        nova_flag = row["Avaliação"]
        old_data = notas_maos.get(h_id, {"nota": "", "flag": "❔ Pendente"})
        
        if nova_nota != old_data["nota"] or nova_flag != old_data["flag"]:
            salvar_nota_mao(h_id, nova_nota, nova_flag)
            # Atualiza o dicionário em memória para outras instâncias na mesma renderização
            notas_maos[h_id] = {"nota": nova_nota, "flag": nova_flag} 

