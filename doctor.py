import streamlit as st
from datetime import date
from supabase import create_client, Client
import pandas as pd

# ========= 读取 Supabase 配置 =========
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="医生端 · 生活方式队列 Dashboard",
    layout="wide"
)

# ========= 简单密码保护 =========
st.title("🩺 医生端 · 生活方式队列 Dashboard")

pwd = st.text_input("请输入医生访问密码", type="password")

if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    if pwd:
        if "DOCTOR_PASSWORD" not in st.secrets:
            st.error("未配置 DOCTOR_PASSWORD，请先在 Streamlit Secrets 中设置。")
            st.stop()
        if pwd == st.secrets["DOCTOR_PASSWORD"]:
            st.session_state.authed = True
            st.success("已通过身份验证")
        else:
            st.error("密码错误")
            st.stop()
    else:
        st.info("请输入访问密码后查看数据")
        st.stop()

# ========= 工具函数 =========
@st.cache_data(ttl=60)
def load_all_records():
    """从 Supabase 拉取全部记录，返回 DataFrame"""
    res = (
        supabase.table("daily_records")
        .select("*")
        .order("log_date", desc=False)
        .execute()
    )
    data = res.data or []
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)

    # 转换日期类型
    if "log_date" in df.columns:
        df["log_date"] = pd.to_datetime(df["log_date"]).dt.date
    return df


# ========= 读取数据 =========
df = load_all_records()

if df.empty:
    st.warning("当前 Supabase 表 daily_records 中还没有任何数据。")
    st.stop()

# ========= 侧边栏筛选 =========
st.sidebar.header("筛选条件")

# 患者列表
patient_list = sorted(df["patient_code"].dropna().unique())
patient_options = ["全部患者"] + patient_list
selected_patient = st.sidebar.selectbox("选择患者", patient_options)

# 日期范围
min_date = df["log_date"].min()
max_date = df["log_date"].max()

date_range = st.sidebar.date_input(
    "日期范围",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) or isinstance(date_range, list):
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

# 应用筛选
df_filtered = df.copy()

if selected_patient != "全部患者":
    df_filtered = df_filtered[df_filtered["patient_code"] == selected_patient]

df_filtered = df_filtered[
    (df_filtered["log_date"] >= start_date) &
    (df_filtered["log_date"] <= end_date)
]

if df_filtered.empty:
    st.warning("当前筛选条件下没有记录。")
    st.stop()

# ========= 顶部 KPI =========
st.subheader("📈 总览指标")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("记录条数", len(df_filtered))

with col2:
    if "weight" in df_filtered.columns:
        st.metric("平均体重 (kg)", f"{df_filtered['weight'].mean():.1f}")
    else:
        st.metric("平均体重 (kg)", "-")

with col3:
    if "BMI" in df_filtered.columns:
        st.metric("平均 BMI", f"{df_filtered['BMI'].mean():.1f}")
    else:
        st.metric("平均 BMI", "-")

with col4:
    if "bowel_count" in df_filtered.columns:
        st.metric("平均排便次数/日", f"{df_filtered['bowel_count'].mean():.2f}")
    else:
        st.metric("平均排便次数/日", "-")

st.markdown("---")

# ========= 时间序列图 =========
st.subheader("📉 时间序列趋势")

ts_cols = st.multiselect(
    "选择需要展示的指标（折线图）",
    options=[c for c in [
        "weight", "BMI", "sleep_hours", "bowel_count", "sport_minutes"
    ] if c in df_filtered.columns],
    default=[c for c in ["weight", "BMI"] if c in df_filtered.columns]
)

if ts_cols:
    df_plot = df_filtered.sort_values("log_date")
    df_plot = df_plot[["log_date"] + ts_cols].set_index("log_date")

    st.line_chart(df_plot, use_container_width=True)
else:
    st.info("请选择至少一个指标进行趋势展示")

st.markdown("---")

# ========= 明细表 & 导出 =========
st.subheader("📄 明细数据")

# 排序让最近日期在前
df_view = df_filtered.sort_values(["patient_code", "log_date"], ascending=[True, False])

st.dataframe(df_view, use_container_width=True)

csv = df_view.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ 导出当前筛选结果为 CSV",
    data=csv,
    file_name="diet_tracker_filtered.csv",
    mime="text/csv",
)
