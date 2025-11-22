import random
from datetime import datetime, date, timedelta

import pandas as pd
import altair as alt
import streamlit as st
from supabase import create_client, Client


# ---------------------- 基础配置 ---------------------- #

st.set_page_config(
    page_title="生活方式日记 · 医生端 Dashboard",
    page_icon="🩺",
    layout="wide",
)

st.title("🧑‍⚕️ 生活方式日记 · 医生端 Dashboard")
st.caption(
    "用于管理患者代码、查看患者的饮食 / 睡眠 / 排便 / 压力 / 运动 / 体重等记录。\n"
    "⚠ 本页面仅供医生使用，请不要分享给患者。"
)


@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


supabase = get_supabase_client()


# ---------------------- 工具函数 ---------------------- #


def generate_patient_code() -> str:
    """生成形如 PYYMMDDXXX 的患者代码。"""
    today = datetime.utcnow().strftime("%y%m%d")
    suffix = random.randint(100, 999)
    return f"P{today}{suffix}"


def load_patients(limit: int = 200) -> pd.DataFrame:
    """读取最近创建的患者代码列表。"""
    try:
        res = (
            supabase.table("patients")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = res.data or []
    except Exception as e:
        st.error(f"读取患者列表失败：{e}")
        data = []

    df = pd.DataFrame(data)
    # 统一列名，避免 KeyError
    if "patient_code" not in df.columns:
        df["patient_code"] = None
    if "remark" not in df.columns:
        df["remark"] = None
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def insert_patient(patient_code: str, remark: str | None = None) -> bool:
    """插入一条新的患者记录。"""
    payload = {"patient_code": patient_code, "remark": remark or None}
    try:
        supabase.table("patients").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"保存患者代码失败：{e}")
        return False


def update_patient_remark(patient_code: str, new_remark: str | None) -> bool:
    """根据 patient_code 更新备注。"""
    try:
        (
            supabase.table("patients")
            .update({"remark": new_remark or None})
            .eq("patient_code", patient_code)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"更新备注失败：{e}")
        return False


def delete_patient(patient_code: str) -> bool:
    """删除一个患者代码（谨慎使用）。"""
    try:
        (
            supabase.table("patients")
            .delete()
            .eq("patient_code", patient_code)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"删除患者代码失败：{e}")
        return False


def load_patient_records(
    patient_code: str, start_date: date, end_date: date
) -> pd.DataFrame:
    """从 daily_records 读取某个患者在日期范围内的记录。"""
    try:
        res = (
            supabase.table("daily_records")
            .select("*")
            .eq("patient_code", patient_code)
            .gte("log_date", start_date.isoformat())
            .lte("log_date", end_date.isoformat())
            .order("log_date", desc=False)
            .execute()
        )
        data = res.data or []
    except Exception as e:
        st.error(f"读取患者记录失败：{e}")
        data = []

    df = pd.DataFrame(data)

    if df.empty:
        return df

    # 处理日期列
    if "log_date" in df.columns:
        df["log_date"] = pd.to_datetime(df["log_date"])

    # 尝试统一一些常见字段名
    if "BMI" in df.columns and "bmi" not in df.columns:
        df["bmi"] = df["BMI"]
    if "total_calories" in df.columns and "total_kcal" not in df.columns:
        df["total_kcal"] = df["total_calories"]
    if "pressure_score" in df.columns and "stress_level" not in df.columns:
        df["stress_level"] = df["pressure_score"]

    return df


# ---------------------- 页面结构 ---------------------- #

tab_codes, tab_records = st.tabs(["🧾 患者代码管理", "📊 患者记录浏览"])


# ======================================================
# Tab 1: 患者代码管理
# ======================================================
with tab_codes:
    st.subheader("新建患者代码")

    remark_input = st.text_input(
        "备注（可选，例如：张三 / AIH / 2025 随访）",
        placeholder="建议填写患者真实姓名 + 疾病 / 项目名称，便于区分",
    )

    if st.button("✨ 生成患者代码并保存", type="primary"):
        # 循环生成，避免偶然重复（极小概率）
        max_try = 5
        success = False
        last_code = None
        for _ in range(max_try):
            code = generate_patient_code()
            last_code = code
            # 简单检查是否已存在
            df_exist = load_patients(limit=1000)
            if not df_exist.empty and code in df_exist["patient_code"].tolist():
                continue
            if insert_patient(code, remark_input.strip() or None):
                success = True
                break

        if success:
            st.success(f"已生成并保存患者代码：`{last_code}`")
            st.info("请将该代码发给对应受试者，在患者端填写使用。")
        else:
            st.error("多次尝试仍未成功生成代码，请稍后重试。")

    st.markdown("---")
    st.subheader("已创建患者代码（最近在最上面）")

    patients_df = load_patients(limit=500)
    if patients_df.empty:
        st.warning("当前还没有患者代码。")
    else:
        show_cols = [c for c in ["patient_code", "remark", "created_at"] if c in patients_df.columns]
        st.dataframe(
            patients_df[show_cols],
            use_container_width=True,
            hide_index=True,
        )

        # 下载 CSV
        csv_bytes = patients_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 下载患者列表（CSV）",
            data=csv_bytes,
            file_name=f"patients_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.subheader("编辑患者备注 / 真实姓名")

    if patients_df.empty:
        st.info("暂无患者代码，无法编辑备注。")
    else:
        # 生成下拉标签：Pxxxxxx - 备注
        patients_df["label"] = patients_df.apply(
            lambda r: f"{r['patient_code']} - {r['remark']}" if r.get("remark") else r["patient_code"],
            axis=1,
        )

        selected_label = st.selectbox(
            "选择要编辑的患者代码",
            patients_df["label"],
        )

        # 反查 patient_code
        selected_row = patients_df[patients_df["label"] == selected_label].iloc[0]
        selected_patient_code = selected_row["patient_code"]
        current_remark = selected_row.get("remark") or ""

        new_remark = st.text_input(
            "备注内容（患者真实姓名等，可修改）",
            value=current_remark,
        )

        col_save, col_del = st.columns(2)

        with col_save:
            if st.button("💾 保存备注", type="primary"):
                if update_patient_remark(selected_patient_code, new_remark.strip() or None):
                    st.success("备注已保存。请刷新页面或重新打开查看最新列表。")

        with col_del:
            with st.expander("⚠️ 删除当前患者代码（高级操作，谨慎使用）"):
                confirm = st.checkbox("我确认要删除该患者代码以及其在 patients 表中的记录。")
                if st.button("🗑️ 删除该患者代码", disabled=not confirm):
                    if delete_patient(selected_patient_code):
                        st.success("已删除该患者代码（daily_records 中的数据不会自动删除）。")
                    else:
                        st.error("删除失败，请稍后重试。")


# ======================================================
# Tab 2: 患者记录浏览
# ======================================================
with tab_records:
    st.subheader("选择患者与时间范围")

    patients_df2 = load_patients(limit=1000)
    if patients_df2.empty:
        st.warning("当前没有患者代码，请先在『患者代码管理』中创建。")
    else:
        patients_df2["label"] = patients_df2.apply(
            lambda r: f"{r['patient_code']} - {r['remark']}" if r.get("remark") else r["patient_code"],
            axis=1,
        )

        selected_label2 = st.selectbox(
            "选择患者代码",
            patients_df2["label"],
            key="records_patient_select",
        )
        selected_row2 = patients_df2[patients_df2["label"] == selected_label2].iloc[0]
        patient_code_for_view = selected_row2["patient_code"]

        col_start, col_end = st.columns(2)
        default_end = date.today()
        default_start = default_end - timedelta(days=14)

        with col_start:
            start_date = st.date_input("起始日期", value=default_start)
        with col_end:
            end_date = st.date_input("结束日期", value=default_end)

        if start_date > end_date:
            st.error("起始日期不能晚于结束日期。")
        else:
            st.markdown("---")
            st.subheader(f"📄 患者 `{patient_code_for_view}` 的记录")

            df_records = load_patient_records(patient_code_for_view, start_date, end_date)

            if df_records.empty:
                st.info("该时间段内没有记录。")
            else:
                # 展示原始表
                st.dataframe(df_records, use_container_width=True)

                # 下面画各种曲线
                st.markdown("### 📈 趋势图")

                # 确保有 log_date 列
                if "log_date" not in df_records.columns:
                    st.warning("记录中缺少 log_date 字段，无法绘制趋势图。")
                else:
                    # 体重
                    if "weight" in df_records.columns:
                        chart_weight = (
                            alt.Chart(df_records)
                            .mark_line(point=True)
                            .encode(
                                x="log_date:T",
                                y=alt.Y("weight:Q", title="体重 (kg)"),
                            )
                            .properties(title="体重变化")
                        )
                        st.altair_chart(chart_weight, use_container_width=True)

                    # BMI
                    if "bmi" in df_records.columns:
                        chart_bmi = (
                            alt.Chart(df_records)
                            .mark_line(point=True, color="#E76F51")
                            .encode(
                                x="log_date:T",
                                y=alt.Y("bmi:Q", title="BMI"),
                            )
                            .properties(title="BMI 变化")
                        )
                        st.altair_chart(chart_bmi, use_container_width=True)

                    # 总卡路里
                    if "total_kcal" in df_records.columns:
                        chart_kcal = (
                            alt.Chart(df_records)
                            .mark_line(point=True, color="#2A9D8F")
                            .encode(
                                x="log_date:T",
                                y=alt.Y("total_kcal:Q", title="每日总卡路里 (kcal)"),
                            )
                            .properties(title="每日总卡路里")
                        )
                        st.altair_chart(chart_kcal, use_container_width=True)

                    # 睡眠 & 压力
                    if "sleep_hours" in df_records.columns or "stress_level" in df_records.columns:
                        base = alt.Chart(df_records).encode(x="log_date:T")

                        layers = []
                        if "sleep_hours" in df_records.columns:
                            layers.append(
                                base.mark_line(point=True, color="#264653").encode(
                                    y=alt.Y("sleep_hours:Q", title="睡眠时长 (h)")
                                )
                            )
                        if "stress_level" in df_records.columns:
                            layers.append(
                                base.mark_line(point=True, color="#E9C46A").encode(
                                    y=alt.Y("stress_level:Q", title="压力 / 睡眠质量评分")
                                )
                            )
                        if layers:
                            chart_sleep_stress = alt.layer(*layers).resolve_scale(y="independent")
                            chart_sleep_stress = chart_sleep_stress.properties(title="睡眠 & 压力 / 睡眠质量")
                            st.altair_chart(chart_sleep_stress, use_container_width=True)

                    # 运动
                    if "sport_minutes" in df_records.columns:
                        chart_sport = (
                            alt.Chart(df_records)
                            .mark_bar()
                            .encode(
                                x="log_date:T",
                                y=alt.Y("sport_minutes:Q", title="运动时长 (min)"),
                            )
                            .properties(title="运动时长")
                        )
                        st.altair_chart(chart_sport, use_container_width=True)

                    # 排便次数
                    if "bowel_count" in df_records.columns:
                        chart_bowel = (
                            alt.Chart(df_records)
                            .mark_bar(color="#F4A261")
                            .encode(
                                x="log_date:T",
                                y=alt.Y("bowel_count:Q", title="排便次数"),
                            )
                            .properties(title="排便次数")
                        )
                        st.altair_chart(chart_bowel, use_container_width=True)

                # 再给一个导出记录按钮
                st.markdown("### ⬇️ 导出当前时间段记录")
                records_csv = df_records.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "下载记录（CSV）",
                    data=records_csv,
                    file_name=f"records_{patient_code_for_view}_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )
