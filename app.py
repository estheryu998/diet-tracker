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
st.subheader("🍱 三餐记录")

# 为了在点击按钮后保留上次估算结果，用 session_state 存一下
for key in ["breakfast_kcal", "lunch_kcal", "dinner_kcal"]:
    if key not in st.session_state:
        st.session_state[key] = 0

# 早餐
st.markdown("**早餐**")
b1, b2 = st.columns([2, 1])
with b1:
    breakfast = st.text_area(
        "早餐内容描述",
        placeholder="例如：泡菜牛肉定食，一小碗米饭，一杯牛奶",
        height=60,
        key="breakfast_text",
        label_visibility="collapsed",  # 不重复显示标签
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

# 今日总热量
total_kcal = breakfast_kcal + lunch_kcal + dinner_kcal
st.metric("今日总热量（估算）", f"{total_kcal} kcal")
st.markdown("---")


    # 一些常见菜品的估算热量（大致值，方便使用时慢慢补充）
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
    # 你可以慢慢往里加：比如你常见的日式定食、韩式套餐、外卖品种等
}

def estimate_meal_kcal(meal_text: str) -> int:
    """
    根据菜名字符串粗略估算热量：
    - 如果包含“泡菜牛肉定食”这种完整词，给出对应热量；
    - 如果包含多个已知菜名，会累加；
    - 如果一个都没匹配到，返回 0，让患者自己填。
    """
    text = meal_text.strip()
    if not text:
        return 0

    total = 0
    for name, kcal in DISH_KCAL.items():
        if name in text:
            total += kcal

    return total

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

if st.button("提交今天的记录", type="primary"):
    code = patient_code.strip()
    if not code:
        st.error("请先填写患者代码（向医生索取）。")
        st.stop()

    # ✅ 1. 先去 patients 表检查这个代码是否存在
    check = (
        supabase.table("patients")
        .select("id")
        .eq("patient_code", code)
        .limit(1)
        .execute()
    )
    if not check.data:
        st.error("患者代码不存在，请确认后再填写。如有疑问请联系医生。")
        st.stop()

    # ✅ 2. 通过校验后再构造 data 写入 daily_records
    data = {
        "log_date": log_date.isoformat(),
        "patient_code": code,
        # … 其他字段 …
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
            st.warning("好像没有返回数据，请稍后在医生端确认是否写入成功。")
