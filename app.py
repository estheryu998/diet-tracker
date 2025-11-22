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

# ======================
# 简单中文/英文食物热量表（kcal / 份）
# ======================
FOOD_CALORIE_DB = {
    # 基础食物
    "鸡蛋": 80,
    "煎蛋": 120,
    "水煮蛋": 80,
    "荷包蛋": 100,
    "蛋黄": 55,
    "蛋白": 20,

    "米饭": 230,      # 一碗
    "粥": 150,        # 一碗
    "馒头": 240,      # 一个
    "面条": 300,      # 一碗
    "炒面": 450,      # 一份
    "面包": 260,      # 两片

    "牛肉": 250,      # 一小份
    "猪肉": 260,
    "鸡肉": 220,
    "鱼": 200,
    "三文鱼": 250,

    "蔬菜": 50,       # 一份
    "沙拉": 150,      # 带少量调料
    "水果": 60,       # 一份
    "苹果": 80,
    "香蕉": 100,
    "酸奶": 120,      # 一杯

    # 套餐 / 菜名示例
    "泡菜牛肉定食": 750,
    "牛肉盖饭": 700,
    "咖喱鸡饭": 800,
    "盖浇饭": 650,
    "汉堡": 500,
    "薯条": 350,
    "披萨": 280,     # 一块

    # 一些英文兜底
    "egg": 80,
    "rice": 230,
    "beef": 250,
    "pork": 260,
    "chicken": 220,
    "salad": 150,
    "yogurt": 120,
}


def estimate_calories(meal_text: str) -> int:
    """
    根据简单的关键字 + 数量 来估算卡路里。
    支持「2个鸡蛋」「一碗米饭」「泡菜牛肉定食」这种写法。
    一份记录里出现多种食物时会自动累加。
    """
    if not meal_text:
        return 0

    text = meal_text.lower().replace(" ", "")
    total = 0

    for name, kcal in FOOD_CALORIE_DB.items():
        if name in text:
            # 匹配前面的数量，如：2个鸡蛋 / 1份泡菜牛肉定食
            pattern = rf"(\d+)\s*(个|份|块|只|碗|盘|杯)?{re.escape(name)}"
            m = re.search(pattern, text)
            if m:
                qty = int(m.group(1))
            else:
                qty = 1

            total += qty * kcal

    return int(total)
# ------------------------ 基本信息：日期 & 患者代码 ------------------------

with st.container():
    col_date, col_code = st.columns(2)
    with col_date:
        log_date = st.date_input("记录日期", value=date.today())
    with col_code:
        patient_code = st.text_input(
            "填写代码",
            placeholder="由管理者提供，例如：A001",
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
    # 改成真正“可选”的下拉菜单
    bowel_options = [
        "不填写",
        "Bristol 1：块状硬便",
        "Bristol 2：结块便",
        "Bristol 3：稍成形",
        "Bristol 4：条状软便（理想）",
        "Bristol 5：软团便",
        "Bristol 6：糊状便",
        "Bristol 7：水样便",
        "其他",
    ]
    bowel_status_display = st.selectbox(
        "排便形态（可选）",
        options=bowel_options,
        index=0,
        help="如果不想填写可以保持“ 不填写 ”。",
    )
    bowel_status = None if bowel_status_display == "不填写" else bowel_status_display
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





