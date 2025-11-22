import io
import pandas as pd
import streamlit as st
from datetime import date
from supabase import create_client, Client

# ===========================
# 页面设置
# ===========================
st.set_page_config(
    page_title="生活方式日记 · 医生端",
    page_icon="🩺",
    layout="wide",
)

st.title("🩺 生活方式日记 · 医生端 Dashboard")

st.caption("用于管理患者代码、查看各患者的饮食 / 睡眠 / 压力 / 运动 / 体重等记录，并导出数据。")

# ===========================
# Supabase 连接
# ===========================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# 可选：医生端密码（如果在 secrets 里设置了 DOCTOR_PASSWORD，则启用登录）
DOCTOR_PASSWORD = st.secrets.get("DOCTOR_PASSWORD", None)

if DOCTOR_PASSWORD:
    if "doctor_logged_in" not in st.session_state:
        st.session_state["doctor_logged_in"] = False

    if not st.session_state["doctor_logged_in"]:
        st.subheader("🔐 医生端登录")
        pwd = st.text_input("请输入医生端密码：", type="password")
        if st.button("登录"):
            if pwd == DOCTOR_PASSWORD:
                st.session_state["doctor_logged_in"] = True
                st.success("登录成功。")
            else:
                st.error("密码错误，请重试。")
        st.stop()


# ===========================
# 工具函数
# ===========================

def generate_new_patient_code() -> str:
    """自动生成一个新的 patient_code，例如 P250112001"""
    today_str = date.today().strftime("%y%m%d")
    prefix = f"P{today_str}"

    resp = (
        supabase.table("patients")
        .select("patient_code")
        .like("patient_code", f"{prefix}%")
        .order("patient_code", desc=True)
        .limit(1)
        .execute()
    )

    last_suffix = 0
    if resp.data:
        last_code = resp.data[0]["patient_code"]
        try:
            last_suffix = int(last_code[-3:])
        except Exception:
            last_suffix = 0

    new_suffix = last_suffix + 1
    return f"{prefix}{new_suffix:03d}"


def load_patients() -> pd.DataFrame:
    resp = (
        supabase.table("patients")
        .select("id, patient_code, remark, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    df = pd.DataFrame(resp.data or [])
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_localize(None)
    return df


def load_all_daily_records() -> pd.DataFrame:
    resp = (
        supabase.table("daily_records")
        .select("*")
        .order("log_date")
        .execute()
    )
    df = pd.DataFrame(resp.data or [])
    if not df.empty:
        df["log_date"] = pd.to_datetime(df["log_date"]).dt.date
    return df


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer.read()


# ===========================
# 1. 患者代码管理
# ===========================

st.markdown("## 👤 患者代码管理")

col_new, col_list = st.columns([1, 2])

with col_new:
    st.markdown("#### 新建患者代码")
    remark = st.text_input("备注（可选，例如姓名缩写 / 病案号）", key="remark_new")

    if st.button("✨ 生成患者代码并保存", type="primary", use_container_width=True):
        new_code = generate_new_patient_code()
        try:
            res = (
                supabase.table("patients")
                .insert(
                    {
                        "patient_code": new_code,
                        "remark": remark.strip() or None,
                    }
                )
                .execute()
            )
        except Exception as e:
            st.error("生成患者代码失败：")
            st.code(str(e))
        else:
            if res.data:
                st.success(f"已创建患者代码：`{new_code}`")
                st.info("请将该代码发给患者，让 TA 在患者端使用。")
            else:
                st.warning("Supabase 未返回数据，请在表中确认是否写入成功。")

with col_list:
    st.markdown("#### 已有患者列表")
    df_patients = load_patients()
    if df_patients.empty:
        st.info("当前还没有任何患者代码。")
    else:
        st.dataframe(
            df_patients,
            use_container_width=True,
            hide_index=True,
        )

        # 导出患者列表
        col_pc1, col_pc2 = st.columns(2)
        with col_pc1:
            st.download_button(
                "下载患者列表（CSV）",
                data=to_csv_bytes(df_patients),
                file_name="patients_list.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_pc2:
            st.download_button(
                "下载患者列表（Excel）",
                data=to_excel_bytes(df_patients, sheet_name="patients"),
                file_name="patients_list.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

st.markdown("---")

# ===========================
# 2. 生活方式记录浏览 & 导出
# ===========================

st.markdown("## 📊 生活方式记录总览")

df_all = load_all_daily_records()
if df_all.empty:
    st.info("当前还没有任何生活方式记录。")
    st.stop()

# ---- 筛选条件 ----
with st.expander("筛选条件", expanded=True):
    # 患者筛选
    codes = sorted(df_all["patient_code"].dropna().unique().tolist())
    selected_code = st.selectbox(
        "选择患者代码",
        options=["全部患者"] + codes,
    )

    # 日期范围
    min_date = df_all["log_date"].min()
    max_date = df_all["log_date"].max()
    default_range = (min_date, max_date)

    date_range = st.date_input(
        "日期范围",
        value=default_range,
        min_value=min_date,
        max_value=max_date,
    )

# 应用筛选
df_filtered = df_all.copy()

if selected_code != "全部患者":
    df_filtered = df_filtered[df_filtered["patient_code"] == selected_code]

if isinstance(date_range, list) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_range

df_filtered = df_filtered[
    (df_filtered["log_date"] >= start_date)
    & (df_filtered["log_date"] <= end_date)
]

if df_filtered.empty:
    st.warning("在当前筛选条件下没有记录。")
    st.stop()

# ---- 顶部指标卡 ----
st.markdown("### 📌 概览指标")

col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    st.metric("记录条数", len(df_filtered))

with col_b:
    avg_sleep = df_filtered["sleep_hours"].mean()
    st.metric("平均睡眠时长（小时）", f"{avg_sleep:.1f}" if pd.notna(avg_sleep) else "-")

with col_c:
    if "total_kcal" in df_filtered.columns and df_filtered["total_kcal"].notna().any():
        avg_kcal = df_filtered["total_kcal"].mean()
        st.metric("平均总热量（kcal）", f"{avg_kcal:.0f}")
    else:
        st.metric("平均总热量（kcal）", "—")

with col_d:
    if "stress_level" in df_filtered.columns and df_filtered["stress_level"].notna().any():
        avg_stress = df_filtered["stress_level"].mean()
        st.metric("平均压力（1-10）", f"{avg_stress:.1f}")
    else:
        st.metric("平均压力（1-10）", "—")

st.markdown("---")

# ---- 趋势图 ----
st.markdown("### 📈 趋势图")

df_plot = df_filtered.sort_values("log_date").set_index("log_date")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**睡眠 / 睡眠质量 / 压力**")
    cols_sleep = [c for c in ["sleep_hours", "sleep_quality", "stress_level"] if c in df_plot.columns]
    if cols_sleep:
        st.line_chart(df_plot[cols_sleep])
    else:
        st.info("暂无睡眠或压力相关字段。")

with c2:
    st.markdown("**热量 / 运动 / BMI**")
    cols_other = [c for c in ["total_kcal", "sport_minutes", "BMI"] if c in df_plot.columns]
    if cols_other:
        st.line_chart(df_plot[cols_other])
    else:
        st.info("暂无热量 / 运动 / BMI 数据。")

st.markdown("---")

# ---- 明细表 + 导出 ----

st.markdown("### 📋 详细记录表")

cols_show = [
    "log_date",
    "patient_code",
    "breakfast",
    "lunch",
    "dinner",
    "breakfast_kcal",
    "lunch_kcal",
    "dinner_kcal",
    "total_kcal",
    "bowel_count",
    "bowel_status",
    "sleep_hours",
    "sleep_quality",
    "stress_level",
    "sport_minutes",
    "weight",
    "BMI",
]

cols_show = [c for c in cols_show if c in df_filtered.columns]

st.dataframe(
    df_filtered[cols_show].sort_values(["patient_code", "log_date"], ascending=[True, False]),
    use_container_width=True,
)

st.markdown("#### 📤 导出当前筛选结果")

col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    st.download_button(
        "下载筛选结果（CSV）",
        data=to_csv_bytes(df_filtered[cols_show]),
        file_name="daily_records_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_exp2:
    st.download_button(
        "下载筛选结果（Excel）",
        data=to_excel_bytes(df_filtered[cols_show], sheet_name="records"),
        file_name="daily_records_filtered.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )

