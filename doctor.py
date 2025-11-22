import secrets
import string
from datetime import date, timedelta

import pandas as pd
import altair as alt
import streamlit as st
from supabase import create_client, Client


# ========= 基础配置 =========

st.set_page_config(
    page_title="生活方式记录 · 医生端",
    page_icon="🩺",
    layout="wide",
)

# 连接 Supabase（医生端用 service_role key）
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


supabase = get_supabase()


# ========= 工具函数 =========

def generate_patient_code(length: int = 8) -> str:
    """生成随机患者代码（大写字母 + 数字）"""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@st.cache_data(ttl=30)
def load_patients() -> pd.DataFrame:
    """读取患者列表"""
    res = supabase.table("patients").select("*").order("created_at", desc=False).execute()
    data = res.data or []
    df = pd.DataFrame(data)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


@st.cache_data(ttl=30)
def load_records(
    patient_code: str | None,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """读取 daily_records，按患者和日期筛选"""
    query = (
        supabase.table("daily_records")
        .select("*")
        .order("log_date", desc=False)
    )

    if patient_code and patient_code != "__ALL__":
        query = query.eq("patient_code", patient_code)

    if start_date:
        query = query.gte("log_date", start_date.isoformat())
    if end_date:
        query = query.lte("log_date", end_date.isoformat())

    res = query.execute()
    data = res.data or []
    df = pd.DataFrame(data)
    if not df.empty:
        df["log_date"] = pd.to_datetime(df["log_date"]).dt.date
    return df


def invalidate_cache():
    load_patients.clear()
    load_records.clear()


# ========= 侧边栏：患者管理 =========

st.sidebar.title("🩺 医生端控制台")

st.sidebar.subheader("患者列表 / 管理")

patients_df = load_patients()

col1, col2 = st.sidebar.columns([2, 1])
with col1:
    if st.button("🔄 刷新患者列表", use_container_width=True):
        invalidate_cache()
        patients_df = load_patients()
with col2:
    st.write("")

st.sidebar.caption("说明：患者代码只发给本人用于登录患者端，不含任何姓名等隐私。")

# 新建患者
with st.sidebar.expander("➕ 创建新患者", expanded=False):
    note = st.text_input("备注（例如：AIH-001，方便医生识别）", key="new_patient_note")
    if st.button("生成患者代码", type="primary", use_container_width=True):
        code = generate_patient_code()
        payload = {"patient_code": code, "note": note or None, "active": True}
        res = supabase.table("patients").insert(payload).execute()
        # Supabase Python SDK v2 没有 res.error 属性，这里只简单判断 data
        if res.data:
            st.success(f"已生成患者代码：`{code}`")
            st.caption("请将此代码发给患者，让 Ta 在患者端输入。")
            invalidate_cache()
        else:
            st.error("生成患者代码失败，请稍后重试。")

# 患者选择器
st.sidebar.markdown("---")
st.sidebar.subheader("📌 选择要查看的患者")

patient_options = ["全部患者"]
patient_map = {}  # 用于展示 note
if not patients_df.empty:
    for _, row in patients_df.iterrows():
        label = row["patient_code"]
        if pd.notna(row.get("note")) and row["note"]:
            label += f"（{row['note']}）"
        patient_options.append(label)
        patient_map[label] = row["patient_code"]

selected_label = st.sidebar.selectbox("患者", options=patient_options, index=0)
selected_code = "__ALL__" if selected_label == "全部患者" else patient_map[selected_label]

# 当前选中患者的状态控制
if selected_code != "__ALL__" and not patients_df.empty:
    row = patients_df[patients_df["patient_code"] == selected_code].iloc[0]
    st.sidebar.markdown("### 当前患者信息")
    st.sidebar.code(selected_code)
    if pd.notna(row.get("note")) and row["note"]:
        st.sidebar.text(f"备注：{row['note']}")
    st.sidebar.text(f"创建时间：{row['created_at']:%Y-%m-%d %H:%M}")

    active = bool(row.get("active", True))
    new_active = st.sidebar.toggle("是否启用（可用于暂时停用患者）", value=active)
    if new_active != active:
        supabase.table("patients").update({"active": new_active}).eq(
            "patient_code", selected_code
        ).execute()
        invalidate_cache()
        st.sidebar.success("已更新患者启用状态")


# ========= 主页面：数据视图与可视化 =========

st.title("📊 单人生活方式记录 · 医生端 Dashboard")

# 日期范围
st.markdown("#### 时间范围")
default_end = date.today()
default_start = default_end - timedelta(days=30)
col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("起始日期", value=default_start, format="YYYY-MM-DD")
with col_end:
    end_date = st.date_input("结束日期", value=default_end, format="YYYY-MM-DD")

if start_date > end_date:
    st.error("起始日期不能晚于结束日期。")
    st.stop()

# 读取数据
records_df = load_records(selected_code, start_date, end_date)

if records_df.empty:
    st.warning("当前筛选条件下，没有生活方式记录。")
    st.stop()

# 字段整理
numeric_cols = [
    "sleep_hours",
    "sport_minutes",
    "weight",
    "bmi",
    "bowel_count",
]
for col in numeric_cols:
    if col in records_df.columns:
        records_df[col] = pd.to_numeric(records_df[col], errors="coerce")

st.markdown("### 原始数据")
st.dataframe(records_df.sort_values("log_date", ascending=False), use_container_width=True)

# ========= 可视化 =========

st.markdown("### 趋势图")

chart_tab1, chart_tab2, chart_tab3 = st.tabs(
    ["💤 睡眠与运动", "⚖️ 体重与 BMI", "🚽 排便情况"]
)

with chart_tab1:
    c1_cols = st.columns(2)
    with c1_cols[0]:
        if "sleep_hours" in records_df.columns:
            chart = (
                alt.Chart(records_df)
                .mark_line(point=True)
                .encode(
                    x="log_date:T",
                    y=alt.Y("sleep_hours:Q", title="睡眠时长（小时）"),
                    tooltip=["log_date:T", "sleep_hours:Q", "patient_code:N"],
                    color="patient_code:N" if selected_code == "__ALL__" else alt.value("#4e79a7"),
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("当前没有睡眠时长字段。")

    with c1_cols[1]:
        if "sport_minutes" in records_df.columns:
            chart = (
                alt.Chart(records_df)
                .mark_bar()
                .encode(
                    x="log_date:T",
                    y=alt.Y("sport_minutes:Q", title="运动时长（分钟）"),
                    tooltip=["log_date:T", "sport_minutes:Q", "patient_code:N"],
                    color="patient_code:N" if selected_code == "__ALL__" else alt.value("#f28e2b"),
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("当前没有运动时长字段。")

with chart_tab2:
    if "weight" in records_df.columns:
        chart_w = (
            alt.Chart(records_df)
            .mark_line(point=True)
            .encode(
                x="log_date:T",
                y=alt.Y("weight:Q", title="体重（kg）"),
                tooltip=["log_date:T", "weight:Q", "patient_code:N"],
                color="patient_code:N" if selected_code == "__ALL__" else alt.value("#59a14f"),
            )
            .properties(height=300)
        )
        st.altair_chart(chart_w, use_container_width=True)
    else:
        st.info("当前没有体重字段。")

    if "bmi" in records_df.columns:
        chart_b = (
            alt.Chart(records_df)
            .mark_line(point=True, strokeDash=[4, 2])
            .encode(
                x="log_date:T",
                y=alt.Y("bmi:Q", title="BMI"),
                tooltip=["log_date:T", "bmi:Q", "patient_code:N"],
                color="patient_code:N" if selected_code == "__ALL__" else alt.value("#e15759"),
            )
            .properties(height=300)
        )
        st.altair_chart(chart_b, use_container_width=True)
    else:
        st.info("当前没有 BMI 字段。")

with chart_tab3:
    if "bowel_count" in records_df.columns:
        chart_bc = (
            alt.Chart(records_df)
            .mark_bar()
            .encode(
                x="log_date:T",
                y=alt.Y("bowel_count:Q", title="排便次数"),
                tooltip=[
                    "log_date:T",
                    "bowel_count:Q",
                    "bowel_status:N",
                    "patient_code:N",
                ],
                color="patient_code:N" if selected_code == "__ALL__" else alt.value("#b07aa1"),
            )
            .properties(height=300)
        )
        st.altair_chart(chart_bc, use_container_width=True)
    else:
        st.info("当前没有排便次数字段。")

st.markdown("—— 以上为医生端 Dashboard，用于查看与管理多名患者的生活方式记录 ——")
