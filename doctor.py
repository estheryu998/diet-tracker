import datetime
import random

import pandas as pd
import streamlit as st
from supabase import create_client, Client


# ========= 基础配置 =========
st.set_page_config(
    page_title="生活方式日记 · 医生端 Dashboard",
    page_icon="👩‍⚕️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ========= Supabase 连接 =========
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    service_key = st.secrets["SUPABASE_SERVICE_KEY"]  # service_role key
    return create_client(url, service_key)


supabase = get_supabase()


# ========= 工具函数 =========
def generate_patient_code() -> str:
    """生成类似 P251122001 这样的患者代码。"""
    today = datetime.date.today().strftime("%y%m%d")
    rand = random.randint(100, 999)
    return f"P{today}{rand}"


def fetch_patients() -> pd.DataFrame:
    """读取患者代码列表（patients 表）。"""
    res = (
        supabase.table("patients")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    data = res.data or []
    if not data:
        return pd.DataFrame(columns=["id", "patient_code", "remark", "created_at"])
    return pd.DataFrame(data)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def fetch_daily_records(
    patient_code: str | None = None,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> pd.DataFrame:
    """读取 daily_records 表，可按患者代码和日期范围筛选。"""
    query = supabase.table("daily_records").select("*")

    if patient_code:
        query = query.eq("patient_code", patient_code)

    if start_date:
        query = query.gte("log_date", start_date.isoformat())
    if end_date:
        query = query.lte("log_date", end_date.isoformat())

    res = query.order("log_date", desc=True).execute()
    data = res.data or []
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


# ========= 页面布局 =========
st.title("📊 生活方式日记 · 医生端 Dashboard")

tab_codes, tab_records = st.tabs(["🔑 患者代码管理", "📋 患者记录浏览"])


# ========= Tab 1: 患者代码管理 =========
with tab_codes:
    st.subheader("新建患者代码")

    col1, col2 = st.columns([2, 2])

    with col1:
        remark = st.text_input(
            "备注（可选，例如姓名缩写 / 病案号）",
            placeholder="例如：张三 / AIH / 2025随访",
        )

        if st.button("✨ 生成患者代码并保存", type="primary"):
            code = generate_patient_code()

            insert_data = {
                "patient_code": code,
                "remark": remark or None,
            }
            res = supabase.table("patients").insert(insert_data).execute()

            if res.data:
                st.success(f"已生成并保存患者代码：**{code}**")
                st.info("请将该代码发给对应患者，用于在患者端填写记录。")
            else:
                st.error("保存到数据库时出现问题，请稍后重试。")

    with col2:
        st.markdown("**已创建患者代码**（最近在最上方）：")
        patients_df = fetch_patients()
        if patients_df.empty:
            st.write("暂无患者代码。")
        else:
            st.dataframe(
                patients_df[["patient_code", "remark", "created_at"]],
                use_container_width=True,
                height=260,
            )

            csv_bytes = to_csv_bytes(patients_df)
            st.download_button(
                "⬇️ 下载患者列表（CSV）",
                data=csv_bytes,
                file_name="patients.csv",
                mime="text/csv",
            )

        st.caption("提示：患者代码与 Supabase RLS 配合，可以防止患者误填或看到他人数据。")


# ========= Tab 2: 患者记录浏览 =========
with tab_records:
    st.subheader("患者记录浏览 / 导出")

    patients_df = fetch_patients()
    patient_options = ["全部患者"]
    code_to_remark = {}

    if not patients_df.empty:
        for _, row in patients_df.iterrows():
            code = row["patient_code"]
            remark = row.get("remark") or ""
            label = f"{code}  ({remark})" if remark else code
            patient_options.append(label)
            code_to_remark[label] = code

    col1, col2, col3 = st.columns([2, 1.5, 1.5])

    with col1:
        selected_label = st.selectbox("选择患者（或全部）：", patient_options)
        selected_code = code_to_remark.get(selected_label)

    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=30)

    with col2:
        start_date = st.date_input("开始日期", value=default_start)
    with col3:
        end_date = st.date_input("结束日期", value=today)

    if start_date > end_date:
        st.error("开始日期不能晚于结束日期。")
    else:
        records_df = fetch_daily_records(
            patient_code=selected_code,
            start_date=start_date,
            end_date=end_date,
        )

        if records_df.empty:
            st.warning("当前筛选条件下没有记录。")
        else:
            st.markdown("**记录预览：**")
            # 按日期+患者代码排序
            records_df = records_df.sort_values(
                by=["log_date", "patient_code"], ascending=[False, True]
            )
            st.dataframe(records_df, use_container_width=True, height=400)

            # 导出 CSV
            csv_bytes = to_csv_bytes(records_df)
            st.download_button(
                "⬇️ 下载筛选记录（CSV）",
                data=csv_bytes,
                file_name="daily_records.csv",
                mime="text/csv",
            )

            st.caption(
                "导出的 CSV 可以直接在 Excel / WPS / Numbers 中打开做进一步分析。"
            )

