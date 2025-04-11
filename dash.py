import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard Parceiros Seazone", layout="wide", page_icon="📊")

# Carregar os dados
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("Base.xlsx")
        
        # Pré-processamento
        df["Taxa Conversão"] = (df["Quantidade de indicações que foram fechadas"] / 
                               df["Quantidade de indicações de proprietários"]).fillna(0)
        
        df["Taxa Qualificação"] = (df["Quantidade de indicações que foram qualificadas"] / 
                                  df["Quantidade de indicações de proprietários"]).fillna(0)
        
        df["Data de último contato"] = pd.to_datetime(df["Data de último contato"])
        df["Dias sem contato"] = (pd.to_datetime("today") - df["Data de último contato"]).dt.days
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

df = load_data()

# Verificação se os dados foram carregados
if df.empty:
    st.stop()

# Sidebar com filtros
st.sidebar.header("🔍 Filtros")

# Filtros dinâmicos que só aparecem se a coluna existir
filtros = {}
if 'Cidade' in df.columns:
    filtros['Cidade'] = st.sidebar.multiselect(
        "Cidade", 
        options=df["Cidade"].unique(), 
        default=df["Cidade"].unique()
    )

if 'Canal de aquisição' in df.columns:
    filtros['Canal de aquisição'] = st.sidebar.multiselect(
        "Canal de Aquisição", 
        options=df["Canal de aquisição"].unique(), 
        default=df["Canal de aquisição"].unique()
    )

if 'Tipo de parceiro' in df.columns:
    filtros['Tipo de parceiro'] = st.sidebar.multiselect(
        "Tipo de Parceiro", 
        options=df["Tipo de parceiro"].unique(), 
        default=df["Tipo de parceiro"].unique()
    )

if 'Status da parceria' in df.columns:
    filtros['Status da parceria'] = st.sidebar.multiselect(
        "Status da Parceria", 
        options=df["Status da parceria"].unique(), 
        default=df["Status da parceria"].unique()
    )

# Aplicar filtros
filtro = df.copy()
for col, valores in filtros.items():
    if valores and col in filtro.columns:
        filtro = filtro[filtro[col].isin(valores)]

# Layout principal
st.title("📊 Dashboard de Performance de Parceiros - Seazone")
st.markdown("""
**Objetivo:** Otimizar a aquisição de imóveis por meio de parcerias com imobiliárias locais, 
identificando os melhores parceiros e canais de aquisição.
""")

# Métricas principais
st.subheader("📈 Métricas Gerais")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Parceiros", filtro.shape[0])
col2.metric("Taxa Média de Conversão", f"{filtro['Taxa Conversão'].mean():.1%}")
col3.metric("Taxa Média de Qualificação", f"{filtro['Taxa Qualificação'].mean():.1%}")
col4.metric("NPS Médio", f"{filtro['NPS da última interação'].mean():.1f}" if 'NPS da última interação' in filtro.columns else "N/D")

# Seção 1: Ranking de Parceiros
st.subheader("🏆 Ranking dos Melhores Parceiros por Taxa de Conversão")
st.markdown("""
**Análise:** Identifica quais parceiros têm o melhor desempenho em converter indicações em fechamentos.
A taxa é calculada como: (Indicações Fechadas / Indicações Recebidas).
""")

top_parceiros = filtro.sort_values("Taxa Conversão", ascending=False).head(10)
fig1 = px.bar(
    top_parceiros,
    x="Nome do Parceiro",
    y="Taxa Conversão",
    color="Taxa Conversão",
    text_auto=".1%",
    color_continuous_scale="Blues",
    labels={"Taxa Conversão": "Taxa de Conversão (%)"},
    height=400
)
fig1.update_layout(yaxis_tickformat=".0%")
st.plotly_chart(fig1, use_container_width=True)

# Seção 2: Canais de Aquisição
st.subheader("🛒 Desempenho por Canal de Aquisição")
st.markdown("""
**Análise:** Compara a eficiência dos diferentes canais de aquisição de parceiros.
O melhor canal é aquele com maior taxa média de conversão.
""")

if 'Canal de aquisição' in filtro.columns:
    canal_conv = filtro.groupby("Canal de aquisição").agg({
        "Taxa Conversão": "mean",
        "Nome do Parceiro": "count"
    }).rename(columns={
        "Taxa Conversão": "Taxa Média de Conversão",
        "Nome do Parceiro": "Quantidade de Parceiros"
    }).sort_values("Taxa Média de Conversão", ascending=False).reset_index()

    fig2 = px.bar(
        canal_conv,
        x="Canal de aquisição",
        y="Taxa Média de Conversão",
        color="Taxa Média de Conversão",
        text_auto=".1%",
        color_continuous_scale="Greens",
        labels={"Taxa Média de Conversão": "Taxa de Conversão (%)"},
        height=400
    )
    fig2.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig2, use_container_width=True)
    
    melhor_canal = canal_conv.iloc[0]
    st.success(f"✅ **Melhor canal de aquisição:** {melhor_canal['Canal de aquisição']} "
              f"com taxa de conversão de {melhor_canal['Taxa Média de Conversão']:.1%}")
else:
    st.warning("Dados sobre canais de aquisição não disponíveis")

# Seção 3: Risco de Churn (ATUALIZADA)
st.subheader("⚠️ Parceiros com Risco de Churn")
st.markdown("""
**Critérios de identificação:**
- Parceria inativa
- NPS da última interação baixo (<30)
- Mais de 60 dias sem contato
- Taxa de conversão abaixo de 20%
""")

if all(col in filtro.columns for col in ["Status da parceria", "NPS da última interação", "Dias sem contato", "Taxa Conversão"]):
    filtro["Risco Churn"] = (
        (filtro["Status da parceria"] == "Inativo") |
        (filtro["NPS da última interação"] < 30) |
        (filtro["Dias sem contato"] > 60) |
        (filtro["Taxa Conversão"] < 0.2)
    )
    
    risco_churn = filtro[filtro["Risco Churn"]].sort_values("Dias sem contato", ascending=False)
    
    if not risco_churn.empty:
        fig3 = px.scatter(
            risco_churn,
            x="Dias sem contato",
            y="NPS da última interação",
            size="Quantidade de indicações de proprietários",
            color="Taxa Conversão",
            hover_name="Nome do Parceiro",
            color_continuous_scale="Reds",
            labels={
                "Dias sem contato": "Dias Sem Contato",
                "NPS da última interação": "NPS (0-100)",
                "Taxa Conversão": "Taxa de Conversão"
            },
            height=500
        )
        fig3.update_layout(yaxis_range=[0,100])
        st.plotly_chart(fig3, use_container_width=True)
        
        st.warning(f"🚨 **Total de parceiros em risco:** {risco_churn.shape[0]}")
        st.dataframe(risco_churn[["Nome do Parceiro", "Cidade", "Status da parceria", 
                                 "Dias sem contato", "NPS da última interação", "Taxa Conversão"]].sort_values("Dias sem contato", ascending=False))
    else:
        st.success("🎉 Nenhum parceiro identificado com risco de churn!")
else:
    st.error("Dados incompletos para análise de risco de churn")

# Seção 4: Perfil Ideal do Parceiro
st.subheader("💎 Perfil Ideal do Parceiro")
st.markdown("""
**Características identificadas na base:**
""")

if not filtro.empty:
    perfil_ideal = {
        "Taxa de Conversão": f"> {filtro['Taxa Conversão'].quantile(0.75):.1%}",
        "NPS da última interação": f"> {filtro['NPS da última interação'].quantile(0.75):.1f}" if 'NPS da última interação' in filtro.columns else "N/D",
        "Frequência de Indicação": "Ativos nos últimos 30 dias",
        "Canal de Aquisição": melhor_canal['Canal de aquisição'] if 'Canal de aquisição' in filtro.columns else "N/D"
    }
    
    st.table(pd.DataFrame.from_dict(perfil_ideal, orient='index', columns=["Valor Ideal"]))
    
    st.markdown("""
    **Ações recomendadas:**
    1. Focar aquisição no canal de melhor performance
    2. Criar programa de incentivos para parceiros com características ideais
    3. Desenvolver plano de retenção para parceiros em risco
    """)
else:
    st.warning("Não há dados suficientes para determinar o perfil ideal")

# Tabela completa (opcional)
expander = st.expander("🔍 Visualizar todos os dados filtrados")
with expander:
    st.dataframe(filtro.sort_values("Taxa Conversão", ascending=False))