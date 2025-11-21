
import streamlit as st
from datetime import date, datetime
from supabase import create_client, Client
import pandas as pd
import os

# ====== 读取 Streamlit Secrets 中的 Supabase 密钥 ======
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="个人生活方式记录工具", layout="wide")

# ====================== 函数区 ======================

def insert_daily_record(data: dict):
    """写入一条记录到 Supabase"""
    response = supabase.table("daily_records").insert(data).execute()
    return response


def load_patient_records(code: str):
    """按 patient_code 读取记录"""
    response = (
        supabase.table("daily_records")
        .select("*")
        .eq("patient_code", code)
        .order("log_date", desc=False)
        .execute()
    )
    return response.data


# ====================== 页面布局 ======================

st.title("📘 单人生活方式记录工具（多用户版）")

st.info("每个用户输入自己的 **患者码（patient_code）** 才能记录，也不会看到别人数据。")

# ---------------- 输入患者码 ----------------
patient_code = st.text_input("请输入你的患者识别码（例如：A001、B002 等）", max_chars=20)

if not patient_code:
    st.warning("请输入患者码才能继续")
    st.stop()

st.success(f"当前患者码：**{patient_code}**")

# ---------------- 输入日期 ----------------
log_date = st.date_input("记录日期", value=date.today())

# ---------------- 三餐 ----------------
st.subheader("🍽️ 三餐记录")
col1, col2, col3 = st.columns(3)

with col1:
    breakfast = st.text_area("早餐内容")
with col2:
    lunch = st.text_area("午餐内容")
with col3:
    dinner = st.text_area("晚餐内容")

# ---------------- 排便 ----------------
st.subheader("🚽 排便情况")
bowel_count = st.number_input("排便次数", min_value=0, max_value=10, step=1)
bowel_status = st.text_input("排便形态（可选）")

# ---------------- 睡眠 ----------------
st.subheader("😴 睡眠情况")
sleep_hours = st.number_input("睡眠时长（小时）", min_value=0.0, max_value=24.0, step=0.5)

# ---------------- 运动 ----------------
st.subheader("🏃 运动情况（分钟）")
sport_minutes = st.number_input("运动时长（分钟）", min_value=0, max_value=500, step=5)

# ---------------- 体重 BMI ----------------
st.subheader("⚖️ 体重与 BMI")
colw1, colw2 = st.columns(2)

with colw1:
    weight = st.number_input("体重（kg）", min_value=0.0, max_value=500.0, step=0.1)

with colw2:
    BMI = st.number_input("BMI", min_value=0.0, max_value=80.0, step=0.1)

# ====================== 按钮：提交 ======================

if st.button("📥 提交今日记录"):
    data = {
        "patient_code": patient_code,
        "log_date": str(log_date),
        "breakfast": breakfast,
        "lunch": lunch,
        "dinner": dinner,
        "bowel_count": bowel_count,
        "bowel_status": bowel_status,
        "sleep_hours": sleep_hours,
        "sport_minutes": sport_minutes,
        "weight": weight,
        "BMI": BMI,
        "created_at": datetime.utcnow().isoformat()
    }

    res = insert_daily_record(data)
    st.success("已成功记录！")
    st.balloons()

# ====================== 历史记录展示 ======================
st.subheader("📊 查看你的历史记录")

records = load_patient_records(patient_code)

if records:
    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True)
else:
    st.info("暂无历史记录")

