import random
import string
from datetime import datetime
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
    # 循环确保不重复（概率很小，但保险一点）
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
    supabase.table("patients").delete().eq("id", patient_id).execute()


def patients_to_csv(patients: list[dict]) -> bytes:
    """导出 CSV（二进制），方便 st.download_button 使用"""
    if not patients:
        return b""
    df = pd.DataFrame(patients)
    # 按你习惯的列顺序
    cols = ["id", "patient_code", "remark", "created_at"]
    df = df[[c for c in cols if c in df.columns]]
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8-sig")  # utf-8 带 BOM，Excel 也能识别中文


# ============ Streamlit UI ============

st.set_page_config(
    page_title="生活方式日记 · 医生端 Dashboard",
    page_icon="🩺",
    layout="wide",
)

st.title("🩺 生活方式日记 · 医生端 Dashboard")

tab_codes, tab_records = st.tabs(["患者代码管理", "（预留）患者记录浏览"])

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
        # 美化显示的列
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
        selected_index = st.selectbox("选择要编辑的患者代码：", range(len(patients)), format_func=lambda i: options[i])
        selected_patient = patients[selected_index]

        new_remark = st.text_input(
            "备注 / 真实姓名：",
            value=selected_patient.get("remark") or "",
            key=f"remark_input_{selected_patient['id']}",
        )

        col_save, col_delete = st.columns(2)
        with col_save:
            if st.button("💾 保存备注", key=f"save_remark_{selected_patient['id']}"):
                update_patient_remark(selected_patient["id"], new_remark.strip())
                st.success("备注已更新。请稍后刷新页面查看最新结果。")

        with col_delete:
            # 删除需要再确认，防止误操作
            if st.button("🗑️ 删除该患者代码", type="secondary"):
                if st.checkbox("我确认要删除该患者代码（不会删除已填写的历史记录）", key="confirm_delete"):
                    delete_patient(selected_patient["id"])
                    st.warning("患者代码已删除。请刷新页面以查看最新列表。")
                else:
                    st.info("请先勾选确认复选框再删除。")


# -------------------------------------------------------------------
# Tab 2 : 患者记录浏览（预留）
# -------------------------------------------------------------------
with tab_records:
    st.info("这里可以以后再扩展：按患者代码 / 日期范围查看饮食、睡眠、排便等记录。当前先专注于患者代码管理。")

