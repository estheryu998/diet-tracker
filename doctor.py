import streamlit as st
from supabase import create_client

# ========== 读取 Secrets ==========
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
DOCTOR_PASSWORD = st.secrets["DOCTOR_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

st.set_page_config(page_title="医生端 · 饮食与健康记录", layout="wide")

# ========== 登录 ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 医生端登录")
    pwd = st.text_input("请输入医生密码：", type="password")

    if st.button("登录"):
        if pwd == DOCTOR_PASSWORD:
            st.session_state.logged_in = True
            st.success("登录成功！")
        else:
            st.error("密码错误，请重试。")
    st.stop()

# ========== 主界面 ==========
st.title("🩺 医生端 · 用户记录管理")

st.markdown("可以按患者编号筛选、编辑、删除记录")

# 筛选条
patient_filter = st.text_input("按 patient_code 搜索（可选）：")

query = supabase.table("daily_records").select("*").order("created_at", desc=True)
if patient_filter.strip() != "":
    query = query.ilike("patient_code", f"%{patient_filter}%")

response = query.execute()
records = response.data

if not records:
    st.info("暂无记录")
    st.stop()

import pandas as pd
df = pd.DataFrame(records)

# 显示表格
st.dataframe(df, use_container_width=True)

# 选择要编辑的记录
st.subheader("✏️ 编辑 / 删除记录")

selected_id = st.selectbox("选择记录 ID：", df["id"])

if selected_id:
    row = df[df["id"] == selected_id].iloc[0]

    with st.form("edit_form"):
        breakfast = st.text_input("早餐", row["breakfast"])
        lunch = st.text_input("午餐", row["lunch"])
        bowel_status = st.text_input("排便形态", row["bowel_status"] or "")
        weight = st.number_input("体重", value=float(row["weight"] or 0))
        BMI = st.number_input("BMI", value=float(row["BMI"] or 0))

        submitted = st.form_submit_button("保存修改")
        if submitted:
            update = {
                "breakfast": breakfast,
                "lunch": lunch,
                "bowel_status": bowel_status,
                "weight": weight,
                "BMI": BMI,
            }
            supabase.table("daily_records").update(update).eq("id", selected_id).execute()
            st.success("修改已保存！请刷新页面查看")
    
    # 删除功能
    if st.button("❌ 删除该记录"):
        supabase.table("daily_records").delete().eq("id", selected_id).execute()
        st.warning("记录已删除，请刷新查看。")
