import math
import re
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
# 单位：大致每“份”的热量，实际只是粗略估算
DISH_KCAL = {
    # 主食
    "米饭": 150,      # 一小碗
    "稀饭": 80,
    "面条": 400,      # 一碗
    "馒头": 110,      # 一个
    "包子": 120,      # 一个
    "面包": 250,      # 一片 / 一小块
    "汉堡": 500,
    "披萨": 300,      # 一小块

    # 肉类 / 蛋类
    "鸡蛋": 80,       # 一个
    "煎蛋": 120,
    "荷包蛋": 120,
    "水煮蛋": 80,
    "鸡胸肉": 200,    # 一小块
    "煎鸡胸肉": 250,
    "牛肉": 200,      # 一小份
    "排骨": 250,
    "鸡腿": 220,
    "鱼": 200,        # 一小份
    "虾": 150,        # 一小份

    # 套餐 / 混合类
    "泡菜牛肉定食": 750,
    "牛肉饭": 650,
    "咖喱牛肉饭": 800,
    "盖浇饭": 700,
    "炒饭": 650,
    "麻辣香锅": 900,

    # 蔬菜 / 水果
    "沙拉": 150,
    "炒青菜": 80,
    "苹果": 80,
    "香蕉": 100,

    # 饮品 / 乳制品
    "牛奶": 120,      # 一杯
    "豆浆": 100,
    "酸奶": 100,
    "可乐": 140,      # 一罐
    "果汁": 150,      # 一杯
}


def _estimate_dish(text: str, dish: str, base_kcal: int) -> int:
    """
    估算某个 dish 在文本中的热量：
    - 支持 “2个鸡蛋 / 2份鸡蛋 / 2碗米饭 / 2杯牛奶” 这种写法；
    - 没有写数量时，且出现了 dish 字样，则按 1 份计算；
    - 可以出现多次，例如 “早上1个鸡蛋，中午2个鸡蛋”。
    """
    total = 0

    # 1) 匹配带数字的写法，如 2个鸡蛋 / 2份鸡蛋 / 2碗米饭 / 2杯牛奶
    pattern = rf"(\d+)\s*(个|份|碗|杯)?\s*{re.escape(dish)}"
    for m in re.finditer(pattern, text):
        qty = int(m.group(1))
        total += qty * base_kcal

    # 2) 如果完全没数字，只是单独提到很多次，如 “鸡蛋 鸡蛋”
    #    那就按照 text.count(dish) 份数估算
    #    但要避免和上面的重复计算：只在“未匹配到数字形式”时再算
    if total == 0:
        count_plain = text.count(dish)
        if count_plain > 0:
            total += count_plain * base_kcal

    return total


def estimate_meal_kcal(meal_text: str) -> int:
    """
    根据文本粗略估算一餐热量：
    - 逐个菜名查看是否在文本中出现；
    - 支持“2个鸡蛋 / 2碗米饭”这种乘法；
    - 一个都没匹配到时返回 0，由患者手动填写。
    """
    text = meal_text.strip()
    if not text:
        return 0

    total = 0
    for name, kcal in DISH_KCAL.items():
        if name in text:
            total += _estimate_dish(text, name, kcal)

    return total


# 为了在点击按钮后保留估算结果，用 session_state 记录
for key in ["breakfast_kcal", "lunch_kcal", "dinner_kcal"]:
    if key not in st.session_state:
        st.session_state[key] = 0

# ------------------------ 基本信息：日期 & 记录代码 ------------------------

with st.container():
    col_date, col_code = st.columns(2)
    with col_date:
        log_date = st.date_input("记录日期", value=date.today())
    with col_code:
        patient_code = st.text_input(
            "记录代码",
            placeholder="请向管理者索取，例如：A001",
        )
    st.caption("请务必确认记录代码填写正确，以免影响他人数据。")

# ----------------------------- 三餐记录 -----------------------------

st.subheader("🍱 三餐记录")

# 早餐
st.markdown("**早餐**")
b1, b2 = st.columns([2, 1])
with b1:
    breakfast = st.text_area(
        "早餐内容描述",
        placeholder="例如：2个鸡蛋，一小碗米饭，一杯牛奶",
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
    bowel_options = [
        "未选择",
        "Bristol 1：颗粒状便，极度便秘",
        "Bristol 2：香肠形但表面有结块，明显便秘",
        "Bristol 3：香肠形但表面有轻微裂纹，偏干",
        "Bristol 4：光滑柔软的香肠形，正常",
        "Bristol 5：软块状，容易排出",
        "Bristol 6：糊状、较松散，腹泻前兆",
        "Bristol 7：完全水样，明显腹泻",
    ]

    bowel_choice = st.selectbox(
        "排便形态（可选）",
        bowel_options,
        index=0,
    )

# 如“未选择”则允许用户额外补充输入
custom_bowel_text = st.text_input(
    "如需补充说明（可选）",
    placeholder="例如：轻微腹胀、排便费力、颜色偏深等",
)

# 最终写入数据库的字段
bowel_status = None
if bowel_choice != "未选择":
    bowel_status = bowel_choice
if custom_bowel_text.strip():
    if bowel_status:
        bowel_status += f"；{custom_bowel_text.strip()}"
    else:
        bowel_status = custom_bowel_text.strip()


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
        st.error("请先填写记录代码（向医生索取）。")
        st.stop()

    # 1) 先检查代码是否存在于 patients 表中，防止填错污染别人
    try:
        check = (
            supabase.table("patients")
            .select("id")
            .eq("patient_code", code)
            .limit(1)
            .execute()
        )
    except Exception as e:
        st.error("验证记录代码时出错，请稍后再试或联系医生。")
        st.code(str(e))
        st.stop()

    if not check.data:
        st.error("记录代码不存在，请确认后再填写。如有疑问请联系医生。")
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

