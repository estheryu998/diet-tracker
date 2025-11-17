# -*- coding: utf-8 -*-
"""
肥胖 / 脂肪肝 单人生活方式记录工具（Streamlit 版）

功能：
- 按日期记录：三餐、排便、睡眠、运动、情绪、体重
- 三餐文本自动估算热量
- 记录体重 + 身高，自动计算 BMI
- 按当前所在周（周一～周日）展示本周汇总 + 简单曲线图
- 所有数据保存在当前目录的 diet_data.json 中
"""

import streamlit as st
import pandas as pd
import json
import os
import datetime as dt
from typing import Tuple, Dict, Any

DATA_FILE = "diet_data.json"

# ===== 1. 食物-热量数据库（每份粗略估算，可按需要扩展/修改） =====
FOOD_DB = {
    "鸡蛋": 78,      # 1个
    "牛奶": 150,     # 1杯 250ml
    "米饭": 200,     # 1小碗
    "面包": 80,      # 1片
    "苹果": 95,
    "香蕉": 100,
    "橙汁": 110,
    "可乐": 140,
    "鸡胸肉": 165,   # 100g
    "牛肉": 250,     # 100g
    "蔬菜": 30,      # 1份
    "酸奶": 120
}


# ===== 2. 工具函数 =====
def load_data() -> Dict[str, Any]:
    """从 JSON 文件加载数据，没有则返回空字典。"""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # 文件损坏等情况，避免程序崩溃
        return {}


def save_data(data: Dict[str, Any]) -> None:
    """把数据保存到 JSON 文件。"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_meal(desc: str) -> Tuple[float, str]:
    """
    将“鸡蛋 2, 牛奶 1, 米饭 1”解析为 (总热量, 细节字符串)
    """
    if not desc or not desc.strip():
        return 0.0, ""

    parts = desc.split(",")
    total_kcal = 0.0
    detail_list = []

    for raw in parts:
        item = raw.strip()
        if not item:
            continue
        segs = item.split()
        name = segs[0]
        qty = 1.0
        if len(segs) > 1:
            try:
                qty = float(segs[1])
            except ValueError:
                qty = 1.0

        kcal_per = FOOD_DB.get(name)
        if kcal_per is None:
            detail_list.append(f"{name}x{qty}=未知(0kcal)")
            kcal = 0.0
        else:
            kcal = kcal_per * qty
            detail_list.append(f"{name}x{qty}={kcal:.0f}kcal")

        total_kcal += kcal

    return total_kcal, "; ".join(detail_list)


def get_week_range(date: dt.date) -> Tuple[dt.date, dt.date]:
    """
    给定一个日期，返回该周（周一~周日）的 (monday, sunday)
    Python: Monday=0 ... Sunday=6
    """
    weekday = date.weekday()          # Monday=0
    monday = date - dt.timedelta(days=weekday)
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


# ===== 3. Streamlit 页面设置 =====
st.set_page_config(
    page_title="饮食 / 睡眠 / 排便 / 体重记录",
    layout="centered"
)

st.title("📋 单人生活方式记录工具")
st.caption("用于肥胖 / 脂肪肝患者的饮食-睡眠-排便-体重记录原型，可扩展为 cohort 工具。")

mode = st.sidebar.radio("选择功能", ["每日记录", "本周汇总"])

data = load_data()   # 顶层结构：{ date_str: {...}, ... }


# ===== 4. 每日记录页面 =====
if mode == "每日记录":
    st.subheader("🗓 每日记录")

    # ---- 日期选择 ----
    today = dt.date.today()
    date = st.date_input("选择日期", value=today)
    date_str = date.isoformat()

    day_data = data.get(date_str, {})

    # ---- 三餐记录 ----
    st.markdown("### 🍽 三餐记录")
    st.info("输入示例：`鸡蛋 2, 牛奶 1, 米饭 1`，中间用逗号分隔，数字为份数（可不写，默认 1）。")

    col_b, col_l, col_d = st.columns(3)

    with col_b:
        breakfast_desc = st.text_area(
            "早餐",
            value=day_data.get("breakfast_desc", ""),
            height=100
        )
    with col_l:
        lunch_desc = st.text_area(
            "午餐",
            value=day_data.get("lunch_desc", ""),
            height=100
        )
    with col_d:
        dinner_desc = st.text_area(
            "晚餐",
            value=day_data.get("dinner_desc", ""),
            height=100
        )

    # 直接根据当前输入实时计算热量（不需要按钮，简单稳妥）
    bk_kcal, bk_detail = parse_meal(breakfast_desc)
    ln_kcal, ln_detail = parse_meal(lunch_desc)
    dn_kcal, dn_detail = parse_meal(dinner_desc)
    total_kcal = bk_kcal + ln_kcal + dn_kcal

    st.markdown("#### 🔢 热量估算")
    st.write(f"**早餐**：约 {bk_kcal:.0f} kcal")
    if bk_detail:
        st.caption(bk_detail)

    st.write(f"**午餐**：约 {ln_kcal:.0f} kcal")
    if ln_detail:
        st.caption(ln_detail)

    st.write(f"**晚餐**：约 {dn_kcal:.0f} kcal")
    if dn_detail:
        st.caption(dn_detail)

    st.success(f"👉 当日总热量约：**{total_kcal:.0f} kcal**")

    # ---- 排便 ----
    st.markdown("### 🚽 排便情况")
    stool_col1, stool_col2 = st.columns(2)
    with stool_col1:
        stool_freq = st.text_input(
            "排便次数（如：0 / 1 / 2）",
            value=day_data.get("stool_freq", "")
        )
    with stool_col2:
        stool_quality = st.text_input(
            "性状（偏干 / 正常 / 偏稀 或 1-5分）",
            value=day_data.get("stool_quality", "")
        )

    # ---- 睡眠 ----
    st.markdown("### 😴 睡眠情况")
    sleep_col1, sleep_col2 = st.columns(2)
    with sleep_col1:
        sleep_hours = st.text_input(
            "睡眠时长（小时，如：7.5）",
            value=day_data.get("sleep_hours", "")
        )
    with sleep_col2:
        sleep_quality = st.text_input(
            "睡眠质量（1-5 或 好 / 一般 / 差）",
            value=day_data.get("sleep_quality", "")
        )

    # ---- 运动 & 情绪 ----
    st.markdown("### 🏃‍♀️ 运动与情绪（可选）")
    act_col1, act_col2 = st.columns(2)
    with act_col1:
        exercise = st.text_input(
            "运动/步数（如：快走30分钟 / 8000步）",
            value=day_data.get("exercise", "")
        )
    with act_col2:
        mood = st.text_input(
            "情绪 / 压力（1-5 或简单描述）",
            value=day_data.get("mood", "")
        )

    # ---- 体重 & BMI ----
    st.markdown("### ⚖️ 体重与 BMI（建议每周记录一次）")
    # 体重信息放在每日里，方便你日后需要时做纵向分析
    wt_col1, wt_col2, wt_col3 = st.columns(3)

    with wt_col1:
        weight_kg = st.text_input(
            "体重（kg）",
            value=day_data.get("weight_kg", "")
        )
    with wt_col2:
        height_m = st.text_input(
            "身高（m，如：1.60）",
            value=day_data.get("height_m", "1.60")
        )

    bmi_value = ""
    if weight_kg and height_m:
        try:
            w = float(weight_kg)
            h = float(height_m)
            if h > 0:
                bmi_value = round(w / (h * h), 1)
        except ValueError:
            bmi_value = ""

    with wt_col3:
        st.write(f"BMI：**{bmi_value}**" if bmi_value != "" else "BMI：")

    # ---- 保存按钮 ----
    if st.button("💾 保存当天数据"):
        data[date_str] = {
            "breakfast_desc": breakfast_desc,
            "lunch_desc": lunch_desc,
            "dinner_desc": dinner_desc,
            "kcal_total": total_kcal,
            "stool_freq": stool_freq,
            "stool_quality": stool_quality,
            "sleep_hours": sleep_hours,
            "sleep_quality": sleep_quality,
            "exercise": exercise,
            "mood": mood,
            "weight_kg": weight_kg,
            "height_m": height_m,
            "bmi": bmi_value
        }
        save_data(data)
        st.success("✅ 已保存！")


# ===== 5. 本周汇总页面 =====
if mode == "本周汇总":
    st.subheader("📆 本周汇总（按当前日期所在周）")

    today = dt.date.today()
    monday, sunday = get_week_range(today)
    st.caption(f"本周范围：{monday.isoformat()} ~ {sunday.isoformat()}")

    rows = []
    week_total_kcal = 0.0

    for date_str, day_data in data.items():
        try:
            d = dt.date.fromisoformat(date_str)
        except ValueError:
            # 非日期键（理论上不会出现），忽略
            continue

        if not (monday <= d <= sunday):
            continue

        total_kcal = float(day_data.get("kcal_total", 0.0))
        week_total_kcal += total_kcal

        rows.append({
            "日期": date_str,
            "总热量(kcal)": round(total_kcal, 0),
            "睡眠时长(h)": day_data.get("sleep_hours", ""),
            "排便次数": day_data.get("stool_freq", ""),
            "体重(kg)": day_data.get("weight_kg", ""),
            "BMI": day_data.get("bmi", ""),
        })

    if not rows:
        st.warning("本周尚无记录，请先在『每日记录』中填写几天数据。")
    else:
        df = pd.DataFrame(rows).sort_values("日期")
        st.write(f"本周总能量摄入约：**{week_total_kcal:.0f} kcal**")
        st.dataframe(df, use_container_width=True)

        # 简单画出本周每日总热量折线
        if "总热量(kcal)" in df.columns:
            chart_df = df[["日期", "总热量(kcal)"]].set_index("日期")
            st.line_chart(chart_df)

        # 导出为 CSV，方便你后续做统计分析
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ 导出本周数据为 CSV",
            data=csv_bytes,
            file_name=f"week_{monday.isoformat()}_{sunday.isoformat()}.csv",
            mime="text/csv"
        )
