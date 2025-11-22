import math
from datetime import date

import streamlit as st
from supabase import create_client, Client

# --------------------------- 基础配置 ---------------------------

st.set_page_config(
    page_title="生活方式日记",
    page_icon="📒",
    layout="centered",
)

st.title("📒 生活方式日记")

st.caption(
    "请根据实际情况填写今天的饮食、排便、睡眠、压力、运动及体重、身高信息。\n"
    "体重 / 身高建议一周记录一次，其余每天一次。"
)

# 从 Streamlit Secrets 里读取 Supabase 配置（患者端只用 anon key）
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ------------------------ 简单菜品热量字典 ------------------------

DISH_KCAL = {
    "泡菜牛肉定食": 750,
    "牛肉饭": 650,
    "咖喱牛肉饭": 800,
    "盖浇饭": 700,
    "炒饭": 650,
    "麻辣香锅": 900,
    "沙拉": 150,
    "鸡胸肉": 200,
    "煎鸡胸肉": 250,
    "米饭": 150,   # 一小碗
    "面条": 400,
    "包子": 120,   # 一个
    "馒头": 110,
    "汉堡": 500,
    "薯条": 350,
    "牛奶": 120,   # 一杯
    "酸奶": 100,
    # 可以根据日常饮食慢慢往这里补充
}


def estimate_meal_kcal(meal_text: str) -> int:
    """
    根据文本粗略估算一餐热量：
    - 只要包含字典中的菜名，就累加对应热量；
    - 一个都没匹配到时返回 0，由患者手动填写。
    """
    text = meal_text.strip()
    if not text:
        return 0

    total = 0
    for name, kcal in DISH_KCAL.items():
        if name in text:
            total += kcal

    return total


# 为了在点击按钮后保留估算结果，用 session_state 记录
for key in ["breakfast_kcal", "lunch_kcal", "dinner_kcal"]:
    if key not in st.session_state:
        st.session_state[key] = 0

# ------------------------ 基本信息：日期 & 患者代码 ------------------------

with st.container():
    col_date, col_code = st.columns(2)
    with col_date:
        log_date = st.date_input("记录日期", value=date.today())
    with col_code:
        patient_code = st.text_input(
            "填写代码",
            placeholder="请向医生索取，例如：A001 / 患者001",
        )
    st.caption("请务必确认自己的代码填写正确，以免影响其他数据。")

# ----------------------------- 三餐记录 -----------------------------

st.subheader("🍱 三餐记录")

# 早餐
st.markdown("**早餐**")
b1, b2 = st.columns([2, 1])
with b1:
    breakfast = st.text_area(
        "早餐内容描述",
        placeholder="例如：泡菜牛肉定食，一小碗米饭，一杯牛奶",
        height=60,
        key="breakfast_text",
        label_visibility="collapsed",
    )
with b2:
    if st.button("自动估算早餐热量", key="btn_breakfast"):
        st.session_state["breakfast_kcal"] = estimate_meal_kcal(breakfast)
    breakfast_kcal = st.number_input(
        "早餐估算热量 (kcal)",
        min_value=0,
        max_value=5000,
        value=int(st.session_state["breakfast_kcal"]),
        step=10,
    )

st.markdown("---")

# 午餐
st.markdown("**午餐**")
l1, l2 = st.columns([2, 1])
with l1:
    lunch = st.text_area(
        "午餐内容描述",
        placeholder="例如：咖喱牛肉饭，一杯酸奶",
        height=60,
        key="lunch_text",
        label_visibility="collapsed",
    )
with l2:
    if st.button("自动估算午餐热量", key="btn_lunch"):
        st.session_state["lunch_kcal"] = estimate_meal_kcal(lunch)
    lunch_kcal = st.number_input(
        "午餐估算热量 (kcal)",
        min_value=0,
        max_value=5000,
        value=int(st.session_state["lunch_kcal"]),
        step=10,
    )

st.markdown("---")

# 晚餐
st.markdown("**晚餐**")
d1, d2 = st.columns([2, 1])
with d1:
    dinner = st.text_area(
        "晚餐内容描述",
        placeholder="例如：少油少盐的炒菜 + 米饭",
        height=60,
        key="dinner_text",
        label_visibility="collapsed",
    )
with d2:
    if st.button("自动估算晚餐热量", key="btn_dinner"):
        st.session_state["dinner_kcal"] = estimate_meal_kcal(dinner)
    dinner_kcal = st.number_input(
        "晚餐估算热量 (kcal)",
        min_value=0,
        max_value=5000,
        value=int(st.session_state["dinner_kcal"]),
        step=10,
    )

# 今日总热量（会存进数据库）
total_kcal = breakfast_kcal + lunch_kcal + dinner_kcal
st.metric("今日总热量（估算）", f"{total_kcal} kcal")

st.markdown("---")

# ------------------------------ 排便情况 ------------------------------

st.subheader("🚽 排便情况")

col_bc, col_bs = st.columns(2)
with col_bc:
    bowel_count = st.number_input(
        "排便次数（次）",
        min_value=0,
        max_value=20,
        step=1,
        value=0,
    )
with col_bs:
    bowel_status = st.text_input(
        "排便形态（可选）",
        placeholder="例如：Bristol 3-4，便形正常，无明显不适",
    )

# ---------------------------- 睡眠与压力 ----------------------------

st.subheader("😴 睡眠与压力")

col_sh, col_sq, col_stress = st.columns([1, 1, 1])
with col_sh:
    sleep_hours = st.number_input(
        "睡眠时长（小时）",
        min_value=0.0,
        max_value=24.0,
        step=0.5,
        value=8.0,
    )

with col_sq:
    sleep_quality = st.slider(
        "睡眠质量（1-10）",
        min_value=1,
        max_value=10,
        value=7,
    )

with col_stress:
    stress_level = st.slider(
        "压力水平（1-10）",
        min_value=1,
        max_value=10,
        value=5,
    )

# ------------------------------ 运动情况 ------------------------------

st.subheader("🏃 运动情况")

sport_minutes = st.number_input(
    "运动时间（分钟）",
    min_value=0,
    max_value=600,
    step=5,
    value=0,
)

# ------------------------- 体重 · 身高 · BMI -------------------------

st.subheader("⚖️ 体重 · 身高 · BMI")
st.caption("体重和身高建议一周记录一次即可。")

col_w, col_h, col_bmi = st.columns(3)
with col_w:
    weight = st.number_input(
        "体重（kg）",
        min_value=0.0,
        max_value=500.0,
        step=0.1,
        value=0.0,
    )

with col_h:
    height_cm = st.number_input(
        "身高（cm）",
        min_value=0.0,
        max_value=250.0,
        step=0.5,
        value=0.0,
    )

# 计算 BMI
if weight > 0 and height_cm > 0:
    bmi_value = weight / math.pow(height_cm / 100.0, 2)
else:
    bmi_value = 0.0

with col_bmi:
    st.number_input(
        "BMI（自动计算）",
        value=float(round(bmi_value, 2)) if bmi_value > 0 else 0.0,
        disabled=True,
    )

# ----------------------------- 提交按钮 -----------------------------

st.markdown("---")

if st.button("✅ 提交今天的记录", type="primary"):
    code = patient_code.strip()

    if not code:
        st.error("请先填写患者代码（向医生索取）。")
        st.stop()

    # 1) 先检查患者代码是否存在于 patients 表中，防止填错污染别人
    try:
        check = (
            supabase.table("patients")
            .select("id")
            .eq("patient_code", code)
            .limit(1)
            .execute()
        )
    except Exception as e:
        st.error("验证患者代码时出错，请稍后再试或联系医生。")
        st.code(str(e))
        st.stop()

    if not check.data:
        st.error("患者代码不存在，请确认后再填写。如有疑问请联系医生。")
        st.stop()

    # 2) 通过校验后，准备写入 daily_records
    data = {
        "log_date": log_date.isoformat(),
        "patient_code": code,
        "breakfast": breakfast.strip() or None,
        "lunch": lunch.strip() or None,
        "dinner": dinner.strip() or None,
        "breakfast_kcal": int(breakfast_kcal) if breakfast_kcal > 0 else None,
        "lunch_kcal": int(lunch_kcal) if lunch_kcal > 0 else None,
        "dinner_kcal": int(dinner_kcal) if dinner_kcal > 0 else None,
        "total_kcal": int(total_kcal) if total_kcal > 0 else None,
        "bowel_count": int(bowel_count),
        "bowel_status": bowel_status.strip() or None,
        "sleep_hours": float(sleep_hours),
        "sleep_quality": int(sleep_quality),
        "stress_level": int(stress_level),
        "sport_minutes": int(sport_minutes),
        "weight": float(weight) if weight > 0 else None,
        "BMI": float(round(bmi_value, 2)) if bmi_value > 0 else None,
    }

    try:
        res = supabase.table("daily_records").insert(data).execute()
    except Exception as e:
        st.error("保存过程中出现错误：")
        st.code(str(e))
    else:
        if getattr(res, "data", None):
            st.success("已成功提交今天的记录，感谢你的配合！")
        else:
            st.warning("已尝试提交，但未收到返回数据，可稍后让医生在后台确认。")


