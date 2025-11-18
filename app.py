# -*- coding: utf-8 -*-
"""
单人生活方式记录工具（高颜值版）
- 患者端：饮食 / 睡眠 / 排便 / 体重输入 + 本周汇总
- 医生端：通过 URL 暗号进入 Dashboard，查看全时段趋势、导出 CSV
- 保留原有 JSON 结构，兼容既有数据
"""

import streamlit as st
import pandas as pd
import json
import os
import datetime as dt
from typing import Dict, Any, Tuple

# ------------------- 基本配置 -------------------
DATA_FILE = "diet_data.json"
DOCTOR_CODE = "masld2025"  # 医生端暗号（?code=masld2025）

BASE_FOOD_DB = {
    "鸡蛋": 78,
    "牛奶": 150,
    "米饭": 200,
    "面包": 80,
    "苹果": 95,
    "香蕉": 100,
    "橙汁": 110,
    "可乐": 140,
    "鸡胸肉": 165,
    "牛肉": 250,
    "蔬菜": 30,
    "酸奶": 120,
}

# ------------------- 工具函数 -------------------
def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_food_db() -> Dict[str, float]:
    custom = st.session_state.get("custom_food_db", {})
    db = BASE_FOOD_DB.copy()
    db.update(custom)
    return db


def parse_meal(desc: str, food_db: Dict[str, float]) -> Tuple[float, str]:
    """
    将 "鸡蛋 2, 牛奶 1" 解析为 (总热量, 细节字符串)
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
    weekday = date.weekday()      # Monday=0
    monday = date - dt.timedelta(days=weekday)
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


# ------------------- 页面设置 & 样式 -------------------
st.set_page_config(
    page_title="饮食 / 睡眠 / 排便 / 体重记录",
    layout="wide"
)

st.markdown("""
<style>
/* 主体宽度和留白 */
.block-container {
    max-width: 1100px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

/* 侧边栏 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
    border-right: 1px solid #e5e7eb;
}

/* 顶部标题 */
h1 {
    font-weight: 700;
    letter-spacing: 0.03em;
}

/* 区块卡片 */
.section-card {
    background-color: #ffffff;
    border-radius: 1.0rem;
    padding: 1.2rem 1.4rem 1.3rem 1.4rem;
    margin-bottom: 1.0rem;
    border: 1px solid #edf2ff;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
}

/* 小卡片（指标） */
.metric-card {
    background-color: #f9fafb;
    border-radius: 0.8rem;
    padding: 0.7rem 0.9rem;
    border: 1px solid #e5e7eb;
}

/* 标签说明 */
.label-muted {
    color: #6b7280;
    font-size: 0.88rem;
}

/* 删除按钮颜色稍柔和 */
.stButton>button[kind="primary"] {
    background-color: #dc2626;
}

/* info / success 提示条 */
.stAlert {
    border-radius: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ------------------- 角色识别：是否医生端 -------------------
query_params = st.query_params
is_doctor = ("code" in query_params and query_params["code"] == DOCTOR_CODE)

# ------------------- 侧边栏 -------------------
with st.sidebar:
    st.markdown("### 🧾 记录入口")
    if is_doctor:
        st.success("当前身份：医生端")
        mode = st.radio("功能", ["每日记录", "本周汇总", "医生端 Dashboard"], index=0)
    else:
        st.info("当前身份：患者/同学端")
        mode = st.radio("功能", ["每日记录", "本周汇总"], index=0)

    with st.expander("🍎 自定义食物热量", expanded=False):
        st.caption("遇到无法识别的食物，可在此添加：名称 + 每份热量。以后输入该名称即可自动计算。")
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

        if st.session_state.get("custom_food_db"):
            custom_items = [
                {"食物": name, "每份热量(kcal)": kcal}
                for name, kcal in st.session_state["custom_food_db"].items()
            ]
            st.table(pd.DataFrame(custom_items))

# ------------------- 加载数据 -------------------
data = load_data()

# =========================================================
#                       每日记录
# =========================================================
if mode == "每日记录":
    st.title("📋 单人生活方式记录工具")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🗓 基本信息")

    today = dt.date.today()
    date = st.date_input("选择日期", value=today)
    date_str = date.isoformat()
    day_data = data.get(date_str, {})

    st.caption("提示：可以选择历史日期进行补录或修改。")

    # 删除当日记录
    if date_str in data:
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            st.write("")
        with col_del2:
            with st.expander("🗑 删除当天记录", expanded=False):
                confirm_del_today = st.checkbox("确认删除该日所有记录", key="confirm_del_today")
                if st.button("删除", key="del_today_btn"):
                    if confirm_del_today:
                        del data[date_str]
                        save_data(data)
                        st.success(f"已删除 {date_str} 的记录。")
                        st.rerun()
                    else:
                        st.warning("请先勾选确认。")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- 三餐记录 ----
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🍽 三餐记录")

    st.markdown(
        '<span class="label-muted">输入示例：<code>鸡蛋 2, 牛奶 1, 米饭 1</code>，中间使用逗号分隔，数字为份数（可不写，默认 1）。</span>',
        unsafe_allow_html=True
    )

    col_b, col_l, col_d = st.columns(3)
    with col_b:
        breakfast_desc = st.text_area(
            "早餐",
            value=day_data.get("breakfast_desc", ""),
            height=100,
            placeholder="例如：鸡蛋 1, 牛奶 1"
        )
    with col_l:
        lunch_desc = st.text_area(
            "午餐",
            value=day_data.get("lunch_desc", ""),
            height=100,
            placeholder="例如：米饭 1, 蔬菜 1, 鸡胸肉 1"
        )
    with col_d:
        dinner_desc = st.text_area(
            "晚餐",
            value=day_data.get("dinner_desc", ""),
            height=100,
            placeholder="例如：米饭 1, 牛肉 1, 蔬菜 1"
        )

    food_db = get_food_db()
    bk_kcal, bk_detail = parse_meal(breakfast_desc, food_db)
    ln_kcal, ln_detail = parse_meal(lunch_desc, food_db)
    dn_kcal, dn_detail = parse_meal(dinner_desc, food_db)
    total_kcal = bk_kcal + ln_kcal + dn_kcal

    st.markdown("#### 🔢 热量估算")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.caption("早餐总热量")
        st.markdown(f"**{bk_kcal:.0f} kcal**")
        if bk_detail:
            st.caption(bk_detail)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.caption("午餐总热量")
        st.markdown(f"**{ln_kcal:.0f} kcal**")
        if ln_detail:
            st.caption(ln_detail)
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.caption("晚餐总热量")
        st.markdown(f"**{dn_kcal:.0f} kcal**")
        if dn_detail:
            st.caption(dn_detail)
        st.markdown('</div>', unsafe_allow_html=True)

    st.success(f"👉 当日总热量约：**{total_kcal:.0f} kcal**")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- 排便、睡眠 ----
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🧠 排便 & 睡眠")

    col_stool, col_sleep = st.columns(2)

    with col_stool:
        st.markdown("##### 🚽 排便情况")
        stool_freq = st.text_input(
            "排便次数（如：0 / 1 / 2）",
            value=day_data.get("stool_freq", "")
        )
        stool_quality = st.text_input(
            "性状（偏干 / 正常 / 偏稀 等）",
            value=day_data.get("stool_quality", "")
        )

    with col_sleep:
        st.markdown("##### 😴 睡眠情况")
        sleep_hours = st.text_input(
            "睡眠时长（小时，如：7.5）",
            value=day_data.get("sleep_hours", "")
        )
        sleep_quality = st.text_input(
            "睡眠质量（好 / 一般 / 差 或 1-5 分）",
            value=day_data.get("sleep_quality", "")
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- 运动 & 情绪 / 体重 BMI ----
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🏃‍♀️ 生活方式与体重")

    col_act, col_wt = st.columns(2)

    with col_act:
        st.markdown("##### 运动与情绪（可选）")
        exercise = st.text_input(
            "运动 / 步数（如：快走30分钟 / 8000步）",
            value=day_data.get("exercise", "")
        )
        mood = st.text_input(
            "情绪 / 压力（可用 1-5 分或文字描述）",
            value=day_data.get("mood", "")
        )

    with col_wt:
        st.markdown("##### ⚖️ 体重与 BMI（建议每周记录一次）")
        wt_col1, wt_col2, wt_col3 = st.columns([1, 1, 1.2])
        with wt_col1:
            weight_kg = st.text_input(
                "体重（kg）",
                value=day_data.get("weight_kg", "")
            )
        with wt_col2:
            height_m = st.text_input(
                "身高（m，例如 1.60）",
                value=day_data.get("height_m", "1.60")
            )

        bmi_value = day_data.get("bmi", "")
        if weight_kg and height_m:
            try:
                w = float(weight_kg)
                h = float(height_m)
                if h > 0:
                    bmi_value = round(w / (h * h), 1)
            except ValueError:
                bmi_value = day_data.get("bmi", "")

        with wt_col3:
            st.markdown("最近 BMI")
            st.markdown(f"### {bmi_value}" if bmi_value != "" else "—")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- 保存按钮 ----
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    if st.button("💾 保存当天数据", use_container_width=True):
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
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
#                       本周汇总
# =========================================================
if mode == "本周汇总":
    st.title("📊 本周汇总")

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

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    if not rows:
        st.warning("本周尚无记录，请先在『每日记录』中填写几天数据。")
    else:
        df = pd.DataFrame(rows).sort_values("日期")
        st.markdown("#### 周度摘要")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="metric-card"><span class="label-muted">本周总能量摄入</span><br><b>{week_total_kcal:.0f} kcal</b></div>',
                unsafe_allow_html=True
            )
        with c2:
            avg_kcal = df["总热量(kcal)"].mean()
            st.markdown(
                f'<div class="metric-card"><span class="label-muted">平均每日能量摄入</span><br><b>{avg_kcal:.0f} kcal/天</b></div>',
                unsafe_allow_html=True
            )

        st.markdown("#### 明细表")
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
        st.markdown("#### 🗑 删除本周某天记录")
        date_options = [r["日期"] for r in rows]
        del_date = st.selectbox("选择要删除的日期", options=date_options)

        confirm_del_week = st.checkbox("确认删除所选日期记录", key="confirm_del_week")
        if st.button("🗑 删除该日期记录", type="primary", key="del_week_btn"):
            if confirm_del_week:
                if del_date in data:
                    del data[del_date]
                    save_data(data)
                    st.success(f"已删除 {del_date} 的记录。")
                    st.rerun()
                else:
                    st.warning("未在数据中找到该日期。")
            else:
                st.warning("请先勾选“确认删除所选日期记录”。")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
#                       医生端 Dashboard
# =========================================================
if is_doctor and mode == "医生端 Dashboard":
    st.title("👨‍⚕️ 医生端 Dashboard")

    if not data:
        st.warning("当前还没有任何记录。")
    else:
        # 整理为 DataFrame
        records = []
        for date_str, d in data.items():
            rec = {"日期": date_str}
            rec.update(d)
            records.append(rec)
        df = pd.DataFrame(records)
        df["日期"] = pd.to_datetime(df["日期"])

        for col in ["kcal_total", "sleep_hours", "stool_freq", "weight_kg", "bmi"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        min_date = df["日期"].min().date()
        max_date = df["日期"].max().date()

        st.caption(f"可用数据时间范围：{min_date} ~ {max_date}")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("起始日期", value=min_date, min_value=min_date, max_value=max_date)
        with col2:
            end_date = st.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)

        if start_date > end_date:
            st.error("起始日期不能晚于结束日期。")
        else:
            mask = (df["日期"].dt.date >= start_date) & (df["日期"].dt.date <= end_date)
            df_sel = df.loc[mask].sort_values("日期")

            if df_sel.empty:
                st.warning("该时间段内没有记录。")
            else:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.subheader("核心指标")

                days = df_sel["日期"].nunique()
                avg_kcal = df_sel["kcal_total"].mean()
                avg_sleep = df_sel["sleep_hours"].mean()
                avg_stool = df_sel["stool_freq"].mean()
                last_weight = df_sel.sort_values("日期")["weight_kg"].dropna().iloc[-1] if df_sel["weight_kg"].notna().any() else None
                last_bmi = df_sel.sort_values("日期")["bmi"].dropna().iloc[-1] if df_sel["bmi"].notna().any() else None

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.caption("记录天数")
                    st.markdown(f"### {days}")
                    st.caption(f"平均能量：{avg_kcal:.0f} kcal/天" if pd.notna(avg_kcal) else "平均能量：NA")
                    st.markdown('</div>', unsafe_allow_html=True)

                with c2:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.caption("睡眠 & 排便")
                    st.markdown(f"平均睡眠：{avg_sleep:.1f} h" if pd.notna(avg_sleep) else "平均睡眠：NA")
                    st.markdown(f"平均排便：{avg_stool:.1f} 次/天" if pd.notna(avg_stool) else "平均排便：NA")
                    st.markdown('</div>', unsafe_allow_html=True)

                with c3:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.caption("最近体重 / BMI")
                    st.markdown(f"体重：{last_weight:.1f} kg" if last_weight is not None else "体重：NA")
                    st.markdown(f"BMI：{last_bmi:.1f}" if last_bmi is not None else "BMI：NA")
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # 趋势图
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.subheader("趋势图")

                ts = df_sel.set_index("日期")

                if "kcal_total" in ts:
                    st.markdown("**每日总热量（kcal）**")
                    st.line_chart(ts[["kcal_total"]].rename(columns={"kcal_total": "总热量(kcal)"}))

                cols_to_plot = []
                if "weight_kg" in ts:
                    cols_to_plot.append("weight_kg")
                if "bmi" in ts:
                    cols_to_plot.append("bmi")
                if cols_to_plot:
                    st.markdown("**体重 / BMI 变化**")
                    st.line_chart(ts[cols_to_plot].rename(columns={"weight_kg": "体重(kg)", "bmi": "BMI"}))

                if "sleep_hours" in ts:
                    st.markdown("**睡眠时长（h）**")
                    st.line_chart(ts[["sleep_hours"]].rename(columns={"sleep_hours": "睡眠时长(h)"}))
                st.markdown('</div>', unsafe_allow_html=True)

                # 明细 + 导出
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.subheader("明细数据（可导出）")

                show_cols = ["日期", "kcal_total", "sleep_hours", "stool_freq", "weight_kg", "bmi",
                             "exercise", "mood"]
                show_cols = [c for c in show_cols if c in df_sel.columns]
                df_show = df_sel[show_cols].copy()
                df_show = df_show.rename(columns={
                    "kcal_total": "总热量(kcal)",
                    "sleep_hours": "睡眠时长(h)",
                    "stool_freq": "排便次数",
                    "weight_kg": "体重(kg)"
                })
                st.dataframe(df_show, use_container_width=True)

                csv_all = df_show.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇️ 导出当前时间段明细为 CSV",
                    data=csv_all,
                    file_name=f"doctor_dashboard_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
                st.markdown('</div>', unsafe_allow_html=True)
