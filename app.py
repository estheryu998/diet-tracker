import datetime
import streamlit as st
from supabase import create_client

# ================== Supabase 初始化（患者端用 anon key） ==================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ================== 页面配置 ==================
st.set_page_config(
    page_title="生活方式记录工具",
    layout="centered",
)

st.title("📘 生活方式记录工具")

# 顶部基本信息
with st.container():
    col_date, col_code = st.columns(2)
    with col_date:
        log_date = st.date_input("记录日期", value=datetime.date.today())
    with col_code:
        patient_code = st.text_input("患者代码", help="医生给你的编号，用于区分不同患者")

# ================== 饮食记录 ==================
st.markdown("### 🍽 三餐记录")

col_b, col_l, col_d = st.columns(3)
with col_b:
    breakfast = st.text_area("早餐", placeholder="例如：粥、鸡蛋、牛奶……")
with col_l:
    lunch = st.text_area("午餐", placeholder="例如：米饭、蔬菜、肉类……")
with col_d:
    dinner = st.text_area("晚餐", placeholder="例如：面条、水果等……")

# ================== 排便与睡眠 ==================
st.markdown("### 🌙 睡眠与排便")

col_sleep, col_bowel_cnt, col_bowel_status = st.columns([1, 1, 2])
with col_sleep:
    sleep_hours = st.number_input("睡眠时长（小时）", min_value=0.0, max_value=24.0, step=0.5, value=8.0)
with col_bowel_cnt:
    bowel_count = st.number_input("排便次数", min_value=0, max_value=20, step=1, value=1)
with col_bowel_status:
    bowel_status = st.text_input("排便形态（可选）", placeholder="可写软硬度、是否费力等，也可以留空")

# ================== 运动与体重 BMI ==================
st.markdown("### 🏃‍♀️ 运动 · 体重 · BMI")

col_sport, col_height, col_weight, col_bmi = st.columns([1, 1, 1, 1])

with col_sport:
    sport_minutes = st.number_input("运动时长（分钟）", min_value=0, max_value=1000, step=10, value=0)

with col_height:
    height_cm = st.number_input("身高（cm）", min_value=0.0, max_value=250.0, step=0.5, value=0.0)

with col_weight:
    weight = st.number_input("体重（kg）", min_value=0.0, max_value=300.0, step=0.1, value=60.0)

# BMI 自动计算
if height_cm > 0 and weight > 0:
    bmi_value = round(weight / ((height_cm / 100) ** 2), 2)
else:
    bmi_value = 0.0

with col_bmi:
    st.number_input("BMI（自动计算）", value=bmi_value, disabled=True)

# ================== 提交记录 ==================
st.markdown("---")
st.subheader("✅ 提交今日记录")

if st.button("提交今日的记录"):
    # 基本校验：患者代码 + 日期 为必填
    if not patient_code.strip():
        st.error("请先填写『患者代码』。")
    else:
        record = {
            "patient_code": patient_code.strip(),
            "log_date": log_date.isoformat(),
            "breakfast": breakfast.strip(),
            "lunch": lunch.strip(),
            "dinner": dinner.strip(),
            "bowel_count": int(bowel_count),
            "bowel_status": bowel_status.strip() or None,  # 可为空
            "sleep_hours": float(sleep_hours),
            "sport_minutes": int(sport_minutes),
            "weight": float(weight),
            "BMI": float(bmi_value),
        }

        try:
            res = supabase.table("daily_records").insert(record).execute()
            if isinstance(res.data, list) and len(res.data) > 0:
                st.success("记录已成功保存，感谢填写！")
            else:
                st.warning("已提交，但返回数据为空，如有疑问请让医生在医生端确认。")
        except Exception as e:
            st.error("保存过程中出现错误，请稍后重试或联系医生。")
            st.write(str(e))

# ================== 本周小结（按患者代码） ==================
st.markdown("---")
st.markdown("### 📊 本周统计（仅自己可见）")

if patient_code.strip():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)

    try:
        query = (
            supabase.table("daily_records")
            .select("*")
            .eq("patient_code", patient_code.strip())
            .gte("log_date", monday.isoformat())
            .lte("log_date", sunday.isoformat())
            .order("log_date", desc=False)
        )
        weekly_res = query.execute()
        weekly_data = weekly_res.data or []

        if weekly_data:
            import pandas as pd

            df_week = pd.DataFrame(weekly_data)
            # 只显示关键列
            show_cols = [
                "log_date",
                "sleep_hours",
                "bowel_count",
                "sport_minutes",
                "weight",
                "BMI",
            ]
            show_cols = [c for c in show_cols if c in df_week.columns]
            st.dataframe(df_week[show_cols], use_container_width=True)
        else:
            st.info("本周暂时还没有记录，可以从今天开始坚持填写。")
    except Exception:
        st.info("暂时无法获取本周统计，但记录已正常保存。")
else:
    st.caption("填写患者代码后，可以看到自己本周的简单统计。")
