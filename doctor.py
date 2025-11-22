import random
import string
from datetime import datetime, date, timedelta
from io import StringIO

import pandas as pd
import streamlit as st
from supabase import create_client, Client

# ============ Supabase 连接（使用 service key，只放在医生端） ============
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ============ 工具函数 ============

def generate_patient_code() -> str:
    """生成类似 P251122XYZ 的患者代码：P + yymmdd + 随机三位"""
    today = datetime.utcnow().strftime("%y%m%d")
    suffix = "".join(random.choices(string.digits, k=3))
    return f"P{today}{suffix}"


def get_patients():
    """获取 patients 表，按创建时间倒序（最近在上面）"""
    res = supabase.table("patients").select("*").order("created_at", desc=True).execute()
    return res.data or []


def create_patient(remark: str):
    """生成一个新的 patient_code 并保存到 patients 表"""
    # 保险一点，确保不重复
    while True:
        code = generate_patient_code()
        exists = (
            supabase.table("patients")
            .select("id")
            .eq("patient_code", code)
            .execute()
            .data
        )
        if not exists:
            break

    payload = {"patient_code": code, "remark": remark}
    supabase.table("patients").insert(payload).execute()
    return code


def update_patient_remark(patient_id: int, remark: str):
    supabase.table("patients").update({"remark": remark}).eq("id", patient_id).execute()


def delete_patient(patient_id: int):
    """只删除 patients 表记录，不删除 daily_records 里的历史数据"""
    supabase.table("patients").delete().eq("id", patient_id).execute()


def patients_to_csv(patients: list[dict]) -> bytes:
    """导出 CSV（二进制），方便 st.download_button 使用"""
    if not patients:
        return b""
    df = pd.DataFrame(patients)
    cols = ["id", "patient_code", "remark", "created_at"]
    df = df[[c for c in cols if c in df.columns]]
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8-sig")  # Excel 也能识别中文


def get_daily_records(patient_code: str, start: date | None, end: date | None):
    """按患者代码 + 日期范围获取 daily_records"""
    query = (
        supabase.table("daily_records")
        .select("*")
        .eq("patient_code", patient_code)
    )
    if start:
        query = query.gte("log_date", start.isoformat())
    if end:
        query = query.lte("log_date", end.isoformat())
    res = query.order("log_date", desc=False).execute()
    return res.data or []


# ============ Streamlit UI ============

st.set_page_config(
    page_title="生活方式日记 · 医生端 Dashboard",
    page_icon="🩺",
    layout="wide",
)

st.title("🩺 生活方式日记 · 医生端 Dashboard")

tab_codes, tab_records = st.tabs(["患者代码管理", "患者记录浏览"])

# -------------------------------------------------------------------
# Tab 1 : 患者代码管理
# -------------------------------------------------------------------
with tab_codes:
    st.subheader("🧾 新建患者代码")

    remark_input = st.text_input(
        "备注（可选，例如：张三 / AIH / 2025随访）",
        placeholder="例如：张三 / AIH / 随访2025",
    )

    col_btn, col_msg = st.columns([1, 3])
    with col_btn:
        if st.button("✨ 生成患者代码并保存", type="primary"):
            new_code = create_patient(remark_input.strip())
            st.success(f"已生成并保存患者代码：**{new_code}**，请发给患者在患者端使用。")

    st.divider()

    st.subheader("📋 已创建患者代码（最近在最上面）")
    patients = get_patients()

    if not patients:
        st.info("目前还没有创建任何患者代码。")
    else:
        df_patients = pd.DataFrame(patients)
        show_cols = ["id", "patient_code", "remark", "created_at"]
        df_show = df_patients[show_cols]
        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
        )

        # 导出 CSV
        csv_bytes = patients_to_csv(patients)
        st.download_button(
            "⬇️ 下载患者列表（CSV）",
            data=csv_bytes,
            file_name="patients.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.subheader("✏️ 编辑患者备注 / 真实姓名")

        # 选择一个患者
        options = [
            f"{row['patient_code']}  |  {row.get('remark') or '（无备注）'}"
            for row in patients
        ]
        selected_index = st.selectbox(
            "选择要编辑的患者代码：",
            range(len(patients)),
            format_func=lambda i: options[i],
        )
        selected_patient = patients[selected_index]

        selected_patient_code = st.selectbox(
    "选择已有患者代码",
    patients_df["patient_code"] if not patients_df.empty else [],
)

new_remark = st.text_input("备注内容（患者真实姓名等）")

if st.button("保存备注", disabled=patients_df.empty):
    try:
        update_patient_remark(selected_patient_code, new_remark.strip())
        st.success("已保存备注")
    except Exception as e:
        st.error(f"保存备注失败：{e}")


        with col_delete:
            if st.button("🗑️ 删除该患者代码", type="secondary"):
                if st.checkbox(
                    "我确认要删除该患者代码（不会删除已填写的历史记录）",
                    key="confirm_delete",
                ):
                    delete_patient(selected_patient["id"])
                    st.warning("患者代码已删除。请刷新页面以查看最新列表。")
                else:
                    st.info("请先勾选上面的确认复选框再进行删除。")


# -------------------------------------------------------------------
# Tab 2 : 患者记录浏览
# -------------------------------------------------------------------
with tab_records:
    st.subheader("📊 按患者代码 / 日期范围查看记录")

    patients = get_patients()
    if not patients:
        st.info("目前还没有任何患者代码，请先在『患者代码管理』里创建。")
    else:
        # 选择患者代码
        options = [
            f"{row['patient_code']}  |  {row.get('remark') or '（无备注）'}"
            for row in patients
        ]
        idx = st.selectbox(
            "选择患者代码：",
            range(len(patients)),
            format_func=lambda i: options[i],
        )
        selected_patient = patients[idx]
        selected_code = selected_patient["patient_code"]

        # 日期范围（默认最近 14 天）
        today = date.today()
        default_start = today - timedelta(days=14)
        date_range = st.date_input(
            "选择日期范围：",
            value=(default_start, today),
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = date_range
            end_date = date_range

        if st.button("🔍 加载记录", type="primary"):
            records = get_daily_records(selected_code, start_date, end_date)

            if not records:
                st.info("该患者在所选日期范围内暂无记录。")
            else:
                df = pd.DataFrame(records)

                # 转成日期类型 & 排序
                if "log_date" in df.columns:
                    df["log_date"] = pd.to_datetime(df["log_date"]).dt.date
                    df = df.sort_values("log_date")

                st.markdown("#### 📄 详细记录列表")
                st.dataframe(df, use_container_width=True, hide_index=True)

                # 方便画图：以 log_date 为索引
                if "log_date" in df.columns:
                    df_plot = df.set_index("log_date")
                else:
                    df_plot = df.copy()

                st.markdown("#### 📈 关键指标趋势")

                # 能画什么画什么，字段不存在就跳过
                if "total_kcal" in df_plot.columns:
                    st.line_chart(
                        df_plot["total_kcal"],
                        height=200,
                    )
                    st.caption("每日总热量（kcal）")

                cols1 = st.columns(2)

                with cols1[0]:
                    if "sleep_hours" in df_plot.columns:
                        st.line_chart(df_plot["sleep_hours"], height=200)
                        st.caption("睡眠时长（小时）")

                    if "bowel_count" in df_plot.columns:
                        st.line_chart(df_plot["bowel_count"], height=200)
                        st.caption("排便次数")

                with cols1[1]:
                    if "sleep_quality" in df_plot.columns:
                        st.line_chart(df_plot["sleep_quality"], height=200)
                        st.caption("睡眠质量（1–10）")

                    if "stress_level" in df_plot.columns:
                        st.line_chart(df_plot["stress_level"], height=200)
                        st.caption("压力（1–10）")

                cols2 = st.columns(2)
                with cols2[0]:
                    if "sport_minutes" in df_plot.columns:
                        st.line_chart(df_plot["sport_minutes"], height=200)
                        st.caption("运动时长（分钟）")

                with cols2[1]:
                    if "weight" in df_plot.columns:
                        st.line_chart(df_plot["weight"], height=200)
                        st.caption("体重（kg）")

                    if "BMI" in df_plot.columns:
                        st.line_chart(df_plot["BMI"], height=200)
                        st.caption("BMI")

                st.success("记录和曲线已加载完毕。")


