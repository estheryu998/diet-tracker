import datetime
import math
import streamlit as st
from supabase import create_client, Client

# -----------------------------
# Supabase 客户端（从 secrets 读取）
# -----------------------------
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


supabase = get_supabase_client()

# -----------------------------
# 写入数据库的封装
# -----------------------------
def insert_daily_record(data: dict):
    """
    向 Supabase 的 daily_records 表插入一条记录。
    使用 Supabase v2 API：response.data / response.count / response.status_code
    """
    try:
        response = supabase.table("daily_records").insert(data).execute()

        # 正常情况下，插入成功会返回新插入的行数据
        if response.data is None:
            # 常见原因：RLS 拒绝了这条 insert
            return False, "插入失败：Supabase 未返回数据（可能被 Row Level Security 拒绝）"

        return True, response.data

    except Exception as e:
        # 把异常信息返回给前端展示
        return False, str(e)


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="单人生活方式记录工具（Supabase 版）", page_icon="📋", layout="wide")

st.title("📋 单人生活方式记录工具（Supabase 版）")
st.write("用于记录饮食 / 睡眠 / 排便 / 运动 / 体重等信息，多用户通过 **患者代码** 区分。")

# --------- 患者代码 & 日期 ---------
st.markdown("### 🧑‍⚕️ 基本信息")

col_code, col_date = st.columns(2)
with col_code:
    patient_code = st.text_input(
        "患者代码（必填，用于区分不同填写者）",
        placeholder="例如：P001、A01 等",
    )

with col_date:
    today = datetime.date.today()
    log_date = st.date_input("记录日期", value=today, format="YYYY-MM-DD")

st.divider()

# --------- 三餐记录 ---------
st.markdown("### 🍽️ 三餐记录")

b_col1, b_col2, b_col3 = st.columns(3)
with b_col1:
    breakfast = st.text_area("早餐", placeholder="例如：鸡蛋 1，牛奶 200ml，面包 1 片")
with b_col2:
    lunch = st.text_area("午餐", placeholder="例如：米饭 1 碗，鸡胸肉 100g，蔬菜")
with b_col3:
    dinner = st.text_area("晚餐", placeholder="例如：粥 1 碗，小菜")

# --------- 排便 & 睡眠 ---------
st.markdown("### 🚽 排便 & 😴 睡眠")

c1, c2, c3 = st.columns(3)
with c1:
    bowel_count = st.number_input(
        "排便次数（次 / 天）",
        min_value=0,
        max_value=10,
        step=1,
        value=0,
    )
with c2:
    # 真正的“可选”字段：不做必填校验，允许空字符串
    bowel_status = st.text_input(
        "排便形态（可选）",
        placeholder="例如：偏干、偏稀、 Bristol 3-4 等，留空表示不记录",
    )
with c3:
    sleep_hours = st.number_input(
        "睡眠时长（小时）",
        min_value=0.0,
        max_value=24.0,
        step=0.5,
        value=8.0,
    )

# --------- 运动 & 体重 / BMI ---------
st.markdown("### 🏃‍♀️ 运动与 ⚖️ 体重 / BMI")

w1, w2, w3 = st.columns(3)
with w1:
    sport_minutes = st.number_input(
        "运动时长（分钟）",
        min_value=0,
        max_value=600,
        step=10,
        value=0,
    )

with w2:
    weight = st.number_input(
        "体重（kg）",
        min_value=0.0,
        max_value=300.0,
        step=0.1,
        value=60.0,
        format="%.2f",
    )

with w3:
    height_cm = st.number_input(
        "身高（cm，仅用于计算 BMI，不会写入数据库）",
        min_value=0.0,
        max_value=250.0,
        step=0.5,
        value=160.0,
        format="%.1f",
    )

# 计算 BMI
bmi_value = None
if height_cm > 0 and weight > 0:
    height_m = height_cm / 100.0
    bmi_value = round(weight / (height_m * height_m), 2)
else:
    bmi_value = 0.0

st.metric("当前 BMI（根据身高 & 体重自动计算）", f"{bmi_value:.2f}")

st.divider()

# -----------------------------
# 提交
# -----------------------------
st.markdown("### ✅ 提交记录")

if st.button("提交今天的记录", type="primary", use_container_width=True):
    # 简单必填校验
    if not patient_code.strip():
        st.error("请填写患者代码（用于区分不同填写者）。")
    else:
        # 处理可选字段：空字符串 -> None，避免数据库里到处是 ""。
        bowel_status_clean = bowel_status.strip() or None

        data = {
            "log_date": log_date.isoformat(),     # date -> string
            "patient_code": patient_code.strip(),
            "breakfast": breakfast.strip() or None,
            "lunch": lunch.strip() or None,
            "dinner": dinner.strip() or None,
            "bowel_count": int(bowel_count) if bowel_count is not None else None,
            "bowel_status": bowel_status_clean,
            "sleep_hours": float(sleep_hours) if sleep_hours is not None else None,
            "sport_minutes": int(sport_minutes) if sport_minutes is not None else None,
            "weight": float(weight) if weight is not None else None,
            "BMI": float(bmi_value) if not math.isnan(bmi_value) else None,
            # created_at 由数据库默认值生成即可
        }

        with st.spinner("正在保存到 Supabase..."):
            success, message = insert_daily_record(data)

        if success:
            st.success("记录已成功保存！👍")
            st.json(message)  # 调试用：可以看到 Supabase 返回的新记录
        else:
            st.error("保存过程中出现错误：")
            st.code(str(message))
