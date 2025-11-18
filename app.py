# -*- coding: utf-8 -*-
"""
单人生活方式记录工具（支持自定义食物热量 + 删除记录）
"""

import streamlit as st
import pandas as pd
import json
import os
import datetime as dt
from typing import Tuple, Dict, Any

DATA_FILE = "diet_data.json"

# ===== 1. 基础食物-热量数据库（每份粗略估算，可按需要扩展/修改） =====
BASE_FOOD_DB = {
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


# ===== 工具函数 =====
def load_data() -> Dict[str, Any]:
    """从 JSON 文件加载数据，没有则返回空字典。"""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data: Dict[str, Any]) -> None:
    """把数据保存到 JSON 文件。"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_food_db() -> Dict[str, float]:
    """
    合并基础食物表 + 用户自定义食物表
    优先使用用户自定义的值。
    """
    custom = st.session_state.get("custom_food_db", {})
    db = BASE_FOOD_DB.copy()
    db.update(custom)
    return db


def parse_meal(desc: str, food_db: Dict[str, float]) -> Tuple[float, str]:
    """
    将“鸡蛋 2, 牛奶 1, 米饭 1”解析为 (总热量, 细节字符串)
    使用传入的 food_db（包含基础+自定义）。
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

        kcal_per = food_db.get(name)
        if kcal_per is None:
            detail_list.append(f"{name}x{qty}=未知(0kcal)（可在左侧添加）")
            kcal = 0.0
        else:
            kcal = kcal_per * qty
            detail_list.append(f"{name}x{qty}={kcal:.0f}kcal")

        total_kcal += kcal

    return total_kcal, "; ".join(detail_list)


def get_week_range(date: dt.date):
    weekday = date.weekday()          # Monday=0
    monday = date - dt.timedelta(days=weekday)
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


# ===== 页面设置 =====
st.set_page_config(
    page_title="饮食 / 睡眠 / 排便 / 体重记录",
    layout="centered"
)

st.title("📋 单人生活方式记录工具")

# ---- 侧边栏：功能选择 + 自定义食物热量 ----
mode = st.sidebar.radio("选择功能", ["每日记录", "本周汇总"])

with st.sidebar.expander("🍎 自定义食物热量", expanded=False):
    st.caption("遇到无法识别的食物，在这里添加一次，以后输入该名称即可自动计算。")
    new_food_name = st.text_input("食物名称（例如：蛋糕）", key="new_food_name")
    new_food_kcal = st.number_input(
        "每份热量（kcal）", min_value=0, max_value=2000,
        value=100, step=10, key="new_food_kcal"
    )
    if st.button("添加 / 更新食物", key="add_food_btn"):
        if new_food_name.strip():
            st.session_state.setdefault("custom_food_db", {})
            st.session_state["custom_food_db"][new_food_name.strip()] = float(new_food_kcal)
            st.success(f"已保存：{new_food_name.strip()} = {float(new_food_kcal):.0f} kcal/份")
        else:
            st.warning("请先填写食物名称。")

    # 显示当前自定义食物表
    if st.session_state.get("custom_food_db"):
        custom_items = [
            {"食物": name, "每份热量(kcal)": kcal}
            for name, kcal in st.session_state["custom_food_db"].items()
        ]
        st.table(pd.DataFrame(custom_items))

data = load_data()


# ===== 每日记录 =====
if mode == "每日记录":
    st.subheader("🗓 每日记录")

    today = dt.date.today()
    date = st.date_input("选择日期", value=today)
    date_str = date.isoformat()

    day_data = data.get(date_str, {})

    # --- 删除当日记录按钮 ---
    if date_str in data:
        with st.expander("🗑 删除本日记录", expanded=False):
            st.info("已存在该日期的记录，如需删除请勾选确认再点击按钮。")
            confirm_del_today = st.checkbox("确认删除本日全部记录", key="confirm_del_today")
            if st.button("🗑 删除本日记录", type="primary", key="del_today_btn"):
                if confirm_del_today:
                    del data[date_str]
                    save_data(data)
                    st.success(f"已删除 {date_str} 的全部记录。")
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()
                else:
                    st.warning("请先勾选“确认删除本日全部记录”。")

    # 三餐
    st.markdown("### 🍽 三餐记录")
    st.info("输入示例：`鸡蛋 2, 牛奶 1, 米饭 1`。遇到新食物，可先在左侧“自定义食物热量”中添加。")

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

    # 计算热量（使用合并后的食物表）
    food_db = get_food_db()
    bk_kcal, bk_detail = parse_meal(breakfast_desc, food_db)
    ln_kcal, ln_detail = parse_meal(lunch_desc, food_db)
    dn_kcal, dn_detail = parse_meal(dinner_desc, food_db)
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

    # 排便
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

    # 睡眠
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

    # 运动 & 情绪
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

    # 体重 & BMI
    st.markdown("### ⚖️ 体重与 BMI（建议每周记录一次）")
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


# ===== 本周汇总 =====
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

        if "总热量(kcal)" in df.columns:
            chart_df = df[["日期", "总热量(kcal)"]].set_index("日期")
            st.line_chart(chart_df)

        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ 导出本周数据为 CSV",
            data=csv_bytes,
            file_name=f"week_{monday.isoformat()}_{sunday.isoformat()}.csv",
            mime="text/csv"
        )

        st.markdown("---")
        st.markdown("### 🗑 删除本周某天记录")
        date_options = [r["日期"] for r in rows]
        del_date = st.selectbox("选择要删除的日期", options=date_options)

        confirm_del_week = st.checkbox("确认删除所选日期记录", key="confirm_del_week")
        if st.button("🗑 删除该日期记录", type="primary", key="del_week_btn"):
            if confirm_del_week:
                if del_date in data:
                    del data[del_date]
                    save_data(data)
                    st.success(f"已删除 {del_date} 的记录。")
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()
                else:
                    st.warning("未在数据中找到该日期。")
            else:
                st.warning("请先勾选“确认删除所选日期记录”。")
