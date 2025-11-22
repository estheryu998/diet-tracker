import streamlit as st
import datetime
from supabase import create_client

# ===========================
# Supabase 初始化（患者端）
# ===========================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ===========================
# 基础设置
# ===========================
st.set_page_config(
    page_title="生活方式日记（患者端）",
    layout="centered"
)

st.title("📒 生活方式日记（患者端）")

st.caption(
    "请根据实际情况填写，体重 / 身高建议一周记录一次，当天未测可以留空。"
)

# ===========================
# 表单开始
# ===========================
with st.form("daily_form"):

    # --- 日期 & 患者代码 ---
    col_date, col_code = st.columns(2)
    with col_date:
        log_date = st.date_input("🗓 记录日期", value=datetime.date.today())
    with col_code:
        patient_code = st.text_input("患者代码", placeholder="例如：A001 / 张三001")

    # ===========================
    # 1. 三餐记录
    # ===========================
    st.markdown("### 🍽 三餐记录")

    breakfast = st.text_area("早餐", placeholder="例如：燕麦 + 鸡蛋 + 牛奶")
    lunch = st.text_area("午餐", placeholder="例如：米饭 + 鱼 + 青菜")
    dinner = st.text_area("晚餐", placeholder="例如：少油少盐，清淡为主")

    # ===========================
    # 2. 排便情况（单独一块）
    # ===========================
    st.markdown("### 🚻 排便情况")

    bowel_count = st.number_input(
        "排便次数（次）",
        min_value=0,
        max_value=10,
        value=0,
        step=1,
    )
    bowel_status = st.text_input(
        "排便形态（可选）",
        placeholder="例如：Bristol 3–4，偏干 / 稀，带不适等"
    )

    # ===========================
    # 3. 睡眠 & 压力
    # ===========================
    st.markdown("### 😴 睡眠与压力")

    c1, c2, c3 = st.columns(3)
    with c1:
        sleep_hours = st.number_input(
            "睡眠时长（小时）",
            min_value=0.0,
            max_value=24.0,
            value=8.0,
            step=0.5,
        )
    with c2:
        sleep_quality = st.slider(
            "睡眠质量（1–10）",
            min_value=1,
            max_value=10,
            value=7,
        )
    with c3:
        stress_level = st.slider(
            "压力水平（1–10）",
            min_value=1,
            max_value=10,
            value=5,
        )

    # ===========================
    # 4. 运动
    # ===========================
    st.markdown("### 🏃‍♀️ 运动情况")

    sport_minutes = st.number_input(
        "运动时间（分钟）",
        min_value=0,
        max_value=600,
        value=0,
        step=10,
    )

    # ===========================
    # 5. 体重 · 身高 · BMI
    # ===========================
    st.markdown("### ⚖️ 体重 · 身高 · BMI")
    st.caption("体重 / 身高建议每周记录一次，当天未测可以留空。")

    col_w, col_h, col_b = st.columns(3)

    with col_w:
        raw_weight = st.number_input(
            "体重（kg，可选）",
            min_value=0.0,
            max_value=300.0,
            value=0.0,
            step=0.1,
        )

    with col_h:
        raw_height_cm = st.number_input(
            "身高（cm，可选）",
            min_value=0.0,
            max_value=250.0,
            value=0.0,
            step=0.5,
        )

    # 转换为 None 或有效值
    weight = None if raw_weight == 0 else float(raw_weight)
    height = None if raw_height_cm == 0 else float(raw_height_cm)

    # 计算 BMI
    bmi_value = None
    if weight is not None and height is not None and height > 0:
        height_m = height / 100.0
        bmi_value = round(weight / (height_m ** 2), 2)

    with col_b:
        if bmi_value is not None:
            st.metric("自动计算 BMI", f"{bmi_value:.2f}")
        else:
            st.metric("自动计算 BMI", "—")

    # ===========================
    # 提交按钮
    # ===========================
    submitted = st.form_submit_button("✅ 提交今天的记录")

# ===========================
# 保存逻辑
# ===========================
def insert_daily_record(payload: dict):
    response = supabase.table("daily_records").insert(payload).execute()
    # Supabase-py v2: APIResponse 有 status_code / data
    status = getattr(response, "status_code", None)
    if status is not None and status >= 400:
        raise RuntimeError(f"Supabase insert failed (status {status})")
    return response

if submitted:
    if not patient_code.strip():
        st.error("请填写患者代码。")
    else:
        data = {
            "log_date": log_date.isoformat(),
            "patient_code": patient_code.strip(),
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "bowel_count": int(bowel_count),
            "bowel_status": bowel_status or None,
            "sleep_hours": float(sleep_hours),
            "sleep_quality": int(sleep_quality),
            "stress_level": int(stress_level),
            "sport_minutes": int(sport_minutes),
            "weight": weight,          # 可能为 None
            "height": height,          # 可能为 None（cm）
            "BMI": bmi_value,          # 可能为 None
        }

        try:
            insert_daily_record(data)
        except Exception as e:
            st.error("保存过程中出现错误：")
            st.code(str(e))
        else:
            st.success("已成功提交今天的记录，感谢配合！")
