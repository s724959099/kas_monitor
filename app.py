import plotly.express as px
import streamlit as st
from update_data import read_symbols, write_symbols, read_pickle_file

# 确保这是第一个 Streamlit 命令
st.set_page_config(layout="wide")

# 自定义 CSS 可以放在这里
st.markdown(
    """
<style>
    .reportview-container .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Create Streamlit application
st.title("KAS Golden Dog")

# Initialize session state
if "symbols" not in st.session_state:
    st.session_state.symbols = read_symbols()

# Input box for adding new token
new_symbol = st.text_input("Add new token")
if st.button("Add Token"):
    if new_symbol and new_symbol.upper() not in st.session_state.symbols:
        st.session_state.symbols.append(new_symbol.upper())
        write_symbols(st.session_state.symbols)
        st.success(f"Token '{new_symbol}' has been added")

selected_symbol = st.selectbox(
    "Select token to display",
    options=st.session_state.symbols,
    index=0,  # Default to the first token in the list
)

df = read_pickle_file(f"{selected_symbol}.pkl")

if not df.empty:
    st.text(f"Last updated: {df['timestamp'].max()}")

    # 創建並顯示折線圖
    col1, col2 = st.columns(2)
    for idx, i in enumerate(range(5, 51, 5)):
        column_name = f"top{i}_total_percentage"
        fig = px.line(
            df,
            x="timestamp",
            y=column_name,
            title=f"Top {i} Holders Percentage Over Time for {selected_symbol}",
        )
        fig.update_layout(legend_title_text="Holder Group", height=300, width=400)

        if idx % 2 == 0:
            with col1:
                st.plotly_chart(fig, use_container_width=True)
        else:
            with col2:
                st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No data available for this token yet.")

# 創建並啟動後台線程
