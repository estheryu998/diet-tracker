import datetime
from typing import Optional

import pandas as pd
import streamlit as st
from supabase import Client, create_client


# ========= Supabase 连接 =========
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


supabase = get_supabase_client()


# ========= 数据库操作 =========
def insert_daily_record(data: dict) -> Optional[str]:
    """
    向 daily_records 表插入一条记录。
    返回错误信息字符串（如果有），正常则返回 None。
    """
    try:
        response = supabase.table("daily_records").insert(data).execute()
        if response.error:
            return str(response.error)
        return None
    except Exception as e:
        return str(e)


def load_patient_history(patient_code: str) -> pd.DataFrame:
    """
    查询某个 patient_code 的全部记录，按日期排序。
    """
    try:
        res = (
            supabase.table("daily_records")
            .select("*")
            .eq("patient_code", patient_code)
            .order("log_date", desc=False)
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ========= 页面配置 =========
st.set_page_config(
    page_title="单人生活方式记录工具（患者端）",
    page_icon="📝",
    layout="wide",
)


st.title("📝 单人生活方式记录工具（患者端）")
st.caption("用于肥胖 / 脂肪肝患者的饮食、排便、睡眠、运动、体重等日常记录。")


# ========= 基本信息 =========
st.subheader("👤 基本信息")

col_code, col_date = st.columns([2, 1])

with col_code:
    patient_code = st.text_input(
        "患者代码 / 昵称",
        placeholder="例如：A001，或任意你记得住的代号",
        help="用于在医生端汇总时区分不同患者。不要填写真实姓名或手机号。",
    )

with col_date:
    log_date = st.date_input(
        "记录日期",
        value=datetime.date.today(),
        help="默认是今天，如需补记可自行修改。",
    )

st.markdown("---")

# ========= 三餐记录 =========
st.subheader("🍽️ 三餐记录")

st.markdown(
    "输入示例：`鸡蛋 2，牛奶 1，米饭 1`。可以写得尽量自然，后续可以再精细化。"
)

b_col1, b_col2, b_col3 = st.columns(3)
with b_col1:
    breakfast = st.text_area("早餐", height=80, placeholder="例如：燕麦粥 1，鸡蛋 1，牛奶 1")
with b_col2:
    lunch = st.text_area("午餐", height=80, placeholder="例如：米饭 1，小炒肉 1，青菜 1")
with b_col3:
    dinner = st.text_area("晚餐", height=80, placeholder="例如：米饭 0.5，鱼 1，蔬菜 2")

st.markdown("---")

# ========= 排便与睡眠 =========
st.subheader("🚻 排便与睡眠")

c1, c2, c3 = st.columns([1, 2, 1])

with c1:
    bowel_count = st.number_input(
        "排便次数 / 天",
        min_value=0,
        max_value=10,
        value=1,
        step=1,
    )

with c2:
    bowel_status = st.text_input(
        "排便形态（可选）",
        placeholder="例如：偏干、偏稀、带黏液等，如无可留空",
        help="此项完全可选，用于更细致了解肠道情况。",
    )

with c3:
    sleep_hours = st.number_input(
        "昨晚睡眠时长（小时）",
        min_value=0.0,
        max_value=24.0,
        value=7.0,
        step=0.5,
    )

st.markdown("---")

# ========= 运动与体重、BMI =========
st.subheader("🏃‍♀️ 运动与 BMI")

c4, c5, c6 = st.columns([1, 1, 1])

with c4:
    sport_minutes = st.number_input(
        "今天运动时长（分钟，可填 0）",
        min_value=0,
        max_value=600,
        value=0,
        step=5,
    )

with c5:
    height_cm = st.number_input(
        "身高（cm）",
        min_value=100.0,
        max_value=250.0,
        value=165.0,
        step=0.5,
        help="用于自动计算 BMI，一般只需首次填写，之后保持不变即可。",
    )

with c6:
    weight = st.number_input(
        "体重（kg）",
        min_value=30.0,
        max_value=200.0,
        value=60.0,
        step=0.1,
    )

# 自动计算 BMI
if height_cm > 0:
    bmi_value = weight / ((height_cm / 100) ** 2)
else:
    bmi_value = 0.0

st.metric("自动计算 BMI（kg/m²）", f"{bmi_value:.1f}")

st.markdown("---")

# ========= 提交按钮 =========
st.subheader("✅ 提交记录")

if st.button("提交今天的记录", type="primary", use_container_width=True):
    # 基础校验：必须有 patient_code
    if not patient_code.strip():
        st.error("请先填写『患者代码 / 昵称』，以便后续区分不同记录。")
    else:
        data = {
            "patient_code": patient_code.strip(),
            "log_date": str(log_date),  # date -> string
            "breakfast": breakfast.strip() or None,
            "lunch": lunch.strip() or None,
            "dinner": dinner.strip() or None,
            "bowel_count": int(bowel_count),
            # 可选字段：为空就存 None
            "bowel_status": bowel_status.strip() or None,
            "sleep_hours": float(sleep_hours),
            "sport_minutes": int(sport_minutes),
            "weight": float(weight),
            "BMI": float(round(bmi_value, 2)),
        }

        error_msg = insert_daily_record(data)
        if error_msg is None:
            st.success("✅ 记录已成功保存！")
        else:
            st.error("保存过程中出现错误：")
            st.code(error_msg, language="text")

# ========= 历史记录预览 =========
st.markdown("---")
st.subheader("📊 本人历史记录（仅自己可见，按患者代码区分）")

if patient_code.strip():
    df_history = load_patient_history(patient_code.strip())
    if df_history.empty:
        st.info("当前患者代码下还没有任何记录。提交一条新记录后即可在此查看。")
    else:
        # 简单按日期和体重 / BMI 展示
        show_cols = [
            "log_date",
            "breakfast",
            "lunch",
            "dinner",
            "bowel_count",
            "bowel_status",
            "sleep_hours",
            "sport_minutes",
            "weight",
            "BMI",
        ]
        existing_cols = [c for c in show_cols if c in df_history.columns]
        st.dataframe(
            df_history[existing_cols].sort_values("log_date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("填写『患者代码 / 昵称』后，可以在这里看到自己的历史记录。")
