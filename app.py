# -*- coding: utf-8 -*-
"""
单人生活方式记录工具（Supabase 多用户版）

- 患者端：通过“患者编号”登录，填写饮食 / 睡眠 / 排便 / 体重 / 运动
- 本周汇总：自动汇总周一到周日的数据，计算总热量、平均睡眠等
- 医生端：通过暗号进入 Dashboard，按患者编号查看所有记录、导出 CSV
- 数据存储：Supabase 表 daily_records（每行=某患者某一天的记录）

注意：
1. 需要在 requirements.txt 中至少包含：
   streamlit
   supabase-py
   pandas

2. 需要在 Streamlit Secrets 中配置：
   SUPABASE_URL, SUPABASE_ANON_KEY, （可选）DOCTOR_CODE
"""

import os
import datetime as dt
from typing import Dict, Any, Optional, List

import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ------------------- 基本配置 -------------------

st.set_page_config(
    page_title="单人生活方式记录工具",
    page_icon="🩺",
    layout="wide",
)

# 从 secrets 读取 Supabase 配置
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
DOCTOR_CODE = st.secrets.get("DOCTOR_CODE", "doctor2025")  # 可在 secrets 中覆盖

@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = get_supabase_client()


# 一个简单的内置食物热量表（kcal/份），后面可扩展
FOOD_DB: Dict[str, float] = {
    "鸡蛋": 78,
    "牛奶": 110,
    "燕麦": 150,
    "米饭": 220,
    "馒头": 220,
    "面包": 260,
    "苹果": 52,
    "香蕉": 89,
    "西兰花": 35,
    "鸡胸肉": 165,
    "牛肉": 250,
    "三文鱼": 208,
    "酸奶": 80,
    "坚果": 580,
}


# ------------------- 计算热量的工具函数 -------------------

def parse_meal_text(meal_text: str) -> List[str]:
    """
    用户输入格式示例：
        鸡蛋 2, 牛奶 1, 米饭 0.5
    返回 ["鸡蛋 2", "牛奶 1", "米饭 0.5"] 这种段落，便于进一步解析。
    """
    if not meal_text:
        return []
    parts = [p.strip() for p in meal_text.replace("，", ",").split(",") if p.strip()]
    return parts


def calc_meal_kcal(meal_text: str) -> (float, str):
    """
    解析一餐的文本，返回（总 kcal, 详情文字）。
    若食物不在字典中，则 kcal 记为 0，并在详情中标明“未知(0kcal)（可在左侧添加）”
    """
    segments = parse_meal_text(meal_text)
    total = 0.0
    detail_list = []

    for seg in segments:
        segs = seg.split()
        if not segs:
            continue
        name = segs[0]
        qty = 1.0
        if len(segs) > 1:
            try:
                qty = float(segs[1])
            except ValueError:
                qty = 1.0

        kcal_per = FOOD_DB.get(name)
        if kcal_per is None:
            kcal = 0.0
            detail_list.append(f"{name}×{qty} = 未知(0kcal)（可在左侧自定义）")
        else:
            kcal = kcal_per * qty
            detail_list.append(f"{name}×{qty} ≈ {kcal:.0f} kcal")

        total += kcal

    detail_text = "；".join(detail_list) if detail_list else "未记录"
    return total, detail_text


def calc_bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    if not weight_kg or not height_cm:
        return None
    h_m = height_cm / 100.0
    if h_m <= 0:
        return None
    return weight_kg / (h_m ** 2)


# ------------------- Supabase 操作函数 -------------------

def load_daily_record(patient_code: str, date: dt.date) -> Optional[Dict[str, Any]]:
    """从 Supabase 读取某患者某天的记录。"""
    response = (
        supabase.table("daily_records")
        .select("*")
        .eq("patient_code", patient_code)
        .eq("log_date", date.isoformat())
        .execute()
    )
    data = response.data
    if data:
        return data[0]
    return None


def upsert_daily_record(payload: Dict[str, Any]) -> None:
    """
    如果已有记录则 update，否则 insert。
    根据 patient_code + log_date 查找。
    """
    patient_code = payload["patient_code"]
    log_date = payload["log_date"]

    existing = load_daily_record(patient_code, log_date)
    if existing:
        supabase.table("daily_records").update(payload).eq("id", existing["id"]).execute()
    else:
        supabase.table("daily_records").insert(payload).execute()


def query_week_records(patient_code: str, week_start: dt.date, week_end: dt.date) -> pd.DataFrame:
    resp = (
        supabase.table("daily_records")
        .select("*")
        .eq("patient_code", patient_code)
        .gte("log_date", week_start.isoformat())
        .lte("log_date", week_end.isoformat())
        .order("log_date")
        .execute()
    )
    df = pd.DataFrame(resp.data or [])
    return df


def query_all_patients() -> pd.DataFrame:
    resp = supabase.table("daily_records").select("*").order("log_date").execute()
    df = pd.DataFrame(resp.data or [])
    return df


# ------------------- 患者端 UI -------------------

def patient_view():
    st.markdown("## 👤 患者端 · 生活方式每日记录")

    # 患者编号（只做区分用，不需要实名）
    patient_code = st.text_input(
        "患者编号（建议使用你和医生约定的 6~10 位代号，如 A001 或 YY2025）",
        help="同一个编号会自动归为一位患者，因此不要随意告诉别人。",
    ).strip()

    if not patient_code:
        st.info("请先输入患者编号。")
        return

    # 日期选择
    today = dt.date.today()
    col_date, col_height = st.columns([2, 1])
    with col_date:
        log_date = st.date_input("记录日期", value=today)
    with col_height:
        height_cm = st.number_input("身高（cm，用于计算 BMI，可选）", min_value=80.0, max_value=250.0, value=160.0)

    # 读取已有记录，做预填
    existing = load_daily_record(patient_code, log_date)
    default = existing or {}

    st.markdown("### 🍽 三餐记录（输入示例：`鸡蛋 1, 牛奶 1, 米饭 0.5`）")
    col_b, col_l, col_d = st.columns(3)
    with col_b:
        breakfast = st.text_area("早餐", value=default.get("breakfast", ""), height=80)
    with col_l:
        lunch = st.text_area("午餐", value=default.get("lunch", ""), height=80)
    with col_d:
        dinner = st.text_area("晚餐", value=default.get("dinner", ""), height=80)

    # 计算三餐热量
    b_kcal, b_detail = calc_meal_kcal(breakfast)
    l_kcal, l_detail = calc_meal_kcal(lunch)
    d_kcal, d_detail = calc_meal_kcal(dinner)
    total_kcal = b_kcal + l_kcal + d_kcal

    with st.expander("查看热量估算详情", expanded=True):
        st.write(f"早餐：{b_detail}，合计约 **{b_kcal:.0f} kcal**")
        st.write(f"午餐：{l_detail}，合计约 **{l_kcal:.0f} kcal**")
        st.write(f"晚餐：{d_detail}，合计约 **{d_kcal:.0f} kcal**")
        st.success(f"👉 今日总能量摄入估计约：**{total_kcal:.0f} kcal**（仅供参考）")

    st.markdown("### 🚻 排便情况")
    col_stool1, col_stool2 = st.columns(2)
    with col_stool1:
        stool_times = st.number_input(
            "排便次数（次/天）", min_value=0, max_value=10, step=1, value=int(default.get("stool_times") or 0)
        )
    with col_stool2:
        stool_note = st.text_input(
            "排便情况备注（如：正常 / 稀 / 便秘等）", value=default.get("stool_note", "")
        )

    st.markdown("### 😴 睡眠情况")
    col_sleep1, col_sleep2 = st.columns(2)
    with col_sleep1:
        sleep_hours = st.number_input(
            "睡眠时长（小时）",
            min_value=0.0,
            max_value=24.0,
            step=0.5,
            value=float(default.get("sleep_hours") or 8.0),
        )
    with col_sleep2:
        sleep_quality = st.selectbox(
            "睡眠质量",
            ["很好", "一般", "较差"],
            index=["很好", "一般", "较差"].index(default.get("sleep_quality", "一般"))
            if default.get("sleep_quality") in ["很好", "一般", "较差"]
            else 1,
        )

    st.markdown("### 🏃‍♀️ 运动 / 活动（可选）")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        activity_minutes = st.number_input(
            "中等及以上强度活动时间（分钟）",
            min_value=0,
            max_value=600,
            step=10,
            value=int(default.get("activity_minutes") or 0),
        )
    with col_act2:
        activity_intensity = st.selectbox(
            "总体活动强度",
            ["很少", "中等", "较多"],
            index=["很少", "中等", "较多"].index(default.get("activity_intensity", "很少"))
            if default.get("activity_intensity") in ["很少", "中等", "较多"]
            else 0,
        )

    st.markdown("### ⚖ 体重 & BMI（建议每周至少记录 1 次）")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        weight_kg = st.number_input(
            "体重（kg）", min_value=0.0, max_value=300.0, step=0.1, value=float(default.get("weight_kg") or 0.0)
        )
    with col_w2:
        bmi_val = calc_bmi(weight_kg if weight_kg > 0 else None, height_cm)
        if bmi_val:
            st.metric("自动计算 BMI", f"{bmi_val:.1f}")
        else:
            st.write("输入体重和身高后可自动计算 BMI")
        bmi = bmi_val or float(default.get("bmi") or 0.0)

    # 保存按钮
    if st.button("💾 保存今日记录", use_container_width=True, type="primary"):
        payload = {
            "patient_code": patient_code,
            "log_date": log_date,
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "stool_times": int(stool_times),
            "stool_note": stool_note,
            "sleep_hours": float(sleep_hours),
            "sleep_quality": sleep_quality,
            "activity_minutes": int(activity_minutes),
            "activity_intensity": activity_intensity,
            "weight_kg": float(weight_kg) if weight_kg else None,
            "bmi": float(bmi) if bmi else None,
            "total_kcal": float(total_kcal),
        }
        upsert_daily_record(payload)
        st.success("✅ 已保存到云端（Supabase）。")

    st.markdown("---")
    st.markdown("### 📅 本周汇总（根据当前选择日期所在周）")

    week_start = log_date - dt.timedelta(days=log_date.weekday())  # 周一
    week_end = week_start + dt.timedelta(days=6)  # 周日

    df_week = query_week_records(patient_code, week_start, week_end)
    if df_week.empty:
        st.info("本周尚无记录。")
        return

    df_display = df_week[["log_date", "total_kcal", "sleep_hours", "stool_times", "weight_kg", "bmi"]].copy()
    df_display = df_display.rename(
        columns={
            "log_date": "日期",
            "total_kcal": "总热量(kcal)",
            "sleep_hours": "睡眠时长(h)",
            "stool_times": "排便(次)",
            "weight_kg": "体重(kg)",
            "bmi": "BMI",
        }
    )
    st.dataframe(df_display, use_container_width=True)

    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.metric("本周总能量摄入", f"{df_week['total_kcal'].sum():.0f} kcal")
    with col_sum2:
        st.metric("平均睡眠时长", f"{df_week['sleep_hours'].mean():.1f} h")
    with col_sum3:
        valid_weight = df_week["weight_kg"].dropna()
        if not valid_weight.empty:
            st.metric("本周体重范围", f"{valid_weight.min():.1f} - {valid_weight.max():.1f} kg")


# ------------------- 医生端 Dashboard -------------------

def doctor_view():
    st.markdown("## 🩺 医生端 Dashboard")

    code = st.text_input("请输入医生访问暗号", type="password")
    if not code:
        st.info("输入暗号后可查看 Dashboard。")
        return
    if code != DOCTOR_CODE:
        st.error("暗号错误。")
        return

    st.success("已通过验证。")

    df_all = query_all_patients()
    if df_all.empty:
        st.info("目前数据库中还没有任何记录。")
        return

    # 把日期列转为真正的 date 类型
    if "log_date" in df_all.columns:
        df_all["log_date"] = pd.to_datetime(df_all["log_date"]).dt.date

    patient_list = sorted(df_all["patient_code"].dropna().unique().tolist())
    col_top1, col_top2 = st.columns([2, 3])
    with col_top1:
        patient = st.selectbox("选择患者编号", options=patient_list)
    with col_top2:
        date_range = st.date_input(
            "选择时间范围",
            value=(df_all["log_date"].min(), df_all["log_date"].max()),
        )

    if not isinstance(date_range, (list, tuple)) or len(date_range) != 2:
        st.warning("请选择起止日期。")
        return

    start_date, end_date = date_range
    mask = (
        (df_all["patient_code"] == patient)
        & (df_all["log_date"] >= start_date)
        & (df_all["log_date"] <= end_date)
    )
    df = df_all.loc[mask].copy()
    if df.empty:
        st.info("所选患者在该时间范围内暂无数据。")
        return

    st.markdown(f"### 📈 患者 {patient} 在 {start_date} ~ {end_date} 的记录")

    # 简单趋势图
    cols_plot = st.columns(3)
    with cols_plot[0]:
        if df["total_kcal"].notna().any():
            st.line_chart(df.set_index("log_date")["total_kcal"], height=200)
            st.caption("每日总热量摄入变化")
    with cols_plot[1]:
        if df["sleep_hours"].notna().any():
            st.line_chart(df.set_index("log_date")["sleep_hours"], height=200)
            st.caption("睡眠时长变化")
    with cols_plot[2]:
        valid_weight = df["weight_kg"].dropna()
        if not valid_weight.empty:
            st.line_chart(df.set_index("log_date")["weight_kg"], height=200)
            st.caption("体重变化")

    # 统计摘要
    st.markdown("#### 📊 统计摘要")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("平均每日总热量", f"{df['total_kcal'].mean():.0f} kcal")
    with col_m2:
        st.metric("平均睡眠时长", f"{df['sleep_hours'].mean():.1f} h")
    with col_m3:
        st.metric("平均排便次数", f"{df['stool_times'].mean():.1f} 次/天")

    st.markdown("#### 🧾 原始明细")
    df_display = df[
        [
            "log_date",
            "breakfast",
            "lunch",
            "dinner",
            "total_kcal",
            "sleep_hours",
            "sleep_quality",
            "stool_times",
            "stool_note",
            "activity_minutes",
            "activity_intensity",
            "weight_kg",
            "bmi",
        ]
    ].copy()
    df_display = df_display.rename(
        columns={
            "log_date": "日期",
            "breakfast": "早餐",
            "lunch": "午餐",
            "dinner": "晚餐",
            "total_kcal": "总热量(kcal)",
            "sleep_hours": "睡眠(h)",
            "sleep_quality": "睡眠质量",
            "stool_times": "排便(次)",
            "stool_note": "排便备注",
            "activity_minutes": "活动(分钟)",
            "activity_intensity": "活动强度",
            "weight_kg": "体重(kg)",
            "bmi": "BMI",
        }
    )

    st.dataframe(df_display, use_container_width=True)

    # 导出 CSV
    csv = df_display.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 导出为 CSV（方便做进一步统计或导入 R / Python）",
        data=csv,
        file_name=f"{patient}_{start_date}_{end_date}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ------------------- 页面主入口 -------------------

def main():
    st.title("📋 单人生活方式记录工具（Supabase 多用户版）")

    mode = st.sidebar.radio(
        "选择角色",
        ["患者端", "医生端 Dashboard"],
        help="患者端用于日常填写；医生端通过暗号进入，查看所有记录。",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**数据说明**")
    st.sidebar.caption(
        "所有数据加密存储在 Supabase，仅通过患者编号关联，不记录真实姓名。"
    )

    if mode == "患者端":
        patient_view()
    else:
        doctor_view()


if __name__ == "__main__":
    main()

