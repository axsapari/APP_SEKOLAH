import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import plotly.express as px

# Import data master dan fungsi pembantu dari file juz_amma_data.py
from juz_amma_data import (
    JUZ_AMMA_MAP,
    SURAH_NAMES,
    TOTAL_AYAT_JUZ_AMMA,
    initialize_database,
    create_initial_data_structure,
    calculate_lulus_count,
)

# =============================
# KONFIGURASI APLIKASI / FILE
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data_hafalan.csv")
GURU_FILE = os.path.join(BASE_DIR, "guru_list.csv")
LOG_FILE = os.path.join(BASE_DIR, "log_hafalan.csv")
logo_path = os.path.join(BASE_DIR, "logo.png")

if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=120)
else:
    st.sidebar.markdown("**SMP Negeri 9 Banjar**")

# Pastikan file CSV penting tersedia
for filename, header in [
    ("data_hafalan.csv", "ID_Murid,Nama_Murid,Kelas,Status_Hafalan,Total_Ayat_Lulus,Update_Terakhir,Guru_Pencatat"),
    ("guru_list.csv", "Nama_Guru"),
    ("log_hafalan.csv", "Timestamp,ID_Murid,Nama_Murid,Kelas,Surah,Ayat_Dari,Ayat_Sampai,Status,Guru_Pencatat"),
]:
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(header + "\n")
        st.warning(f"File {filename} tidak ditemukan, dibuat otomatis.")

st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "df" not in st.session_state:
    st.session_state.df = initialize_database(DB_FILE)

# =============================
# FUNGSI UTILITAS
# =============================

def load_guru_list(csv_path: str = GURU_FILE):
    default_guru = [
        "Agus Sugiharto Sapari, S.Pd.",
        "Siti Maryam, S.Pd.",
        "Rahmat Hidayat, S.Pd.I.",
        "Nisa Khairun, S.Pd.",
    ]
    if not os.path.exists(csv_path):
        st.warning(f"File '{csv_path}' tidak ditemukan. Membuat file contoh otomatis.")
        pd.DataFrame({"Nama_Guru": default_guru}).to_csv(csv_path, index=False)
        return ["Pilih Guru"] + default_guru

    try:
        df_guru = pd.read_csv(csv_path)
        if "Nama_Guru" not in df_guru.columns:
            return ["Pilih Guru"] + default_guru
        guru_list = ["Pilih Guru"] + df_guru["Nama_Guru"].dropna().astype(str).tolist()
        return guru_list
    except Exception as e:
        st.error(f"Gagal membaca '{csv_path}': {e}")
        return ["Pilih Guru"] + default_guru


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "Guru_Pencatat" not in df.columns:
        df["Guru_Pencatat"] = ""
    if "NIS" not in df.columns:
        df["NIS"] = ""
    if "Total_Ayat_Lulus" not in df.columns:
        df["Total_Ayat_Lulus"] = 0
    if "Update_Terakhir" not in df.columns:
        df["Update_Terakhir"] = ""
    return df


def save_data(df: pd.DataFrame):
    df = ensure_columns(df)
    df.to_csv(DB_FILE, index=False)
    st.session_state.df = df


def add_new_student(name, kelas, nis=""):
    df = ensure_columns(st.session_state.df.copy())
    next_id = df["ID_Murid"].max() + 1 if not df.empty else 1001

    new_data = {
        "ID_Murid": next_id,
        "Nama_Murid": name,
        "NIS": nis,
        "Kelas": kelas,
        "Status_Hafalan": create_initial_data_structure(),
        "Total_Ayat_Lulus": 0,
        "Update_Terakhir": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Guru_Pencatat": "",
    }

    new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    save_data(new_df)
    st.success(f"Murid **{name}** (ID: {next_id}) berhasil ditambahkan ke kelas **{kelas}**.")


def import_students_from_csv(uploaded_file):
    try:
        new_students_df = pd.read_csv(uploaded_file, sep=";")
        REQUIRED_COLS = ["Nama_Murid", "Kelas"]
        if not all(col in new_students_df.columns for col in REQUIRED_COLS):
            st.error("File CSV harus memiliki kolom wajib: Nama_Murid, Kelas")
            return
        new_students_df = new_students_df.dropna(subset=REQUIRED_COLS)
        df = ensure_columns(st.session_state.df.copy())
        current_max_id = df["ID_Murid"].max() if not df.empty else 1000
        num_new = len(new_students_df)
        new_students_df["ID_Murid"] = range(current_max_id + 1, current_max_id + 1 + num_new)
        new_students_df["Status_Hafalan"] = [create_initial_data_structure() for _ in range(num_new)]
        new_students_df["Total_Ayat_Lulus"] = 0
        new_students_df["Update_Terakhir"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_students_df["Guru_Pencatat"] = ""
        if "NIS" not in new_students_df.columns:
            new_students_df["NIS"] = ""
        combined_df = pd.concat([df, new_students_df], ignore_index=True)
        save_data(combined_df)
        st.success(f"{num_new} murid berhasil diimpor!")
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")


def log_setoran(student_row, surah, start_ayat, end_ayat, status_code, guru_pencatat):
    status_label = "Lulus" if status_code == 1 else "Mengulang"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_data = {
        "Timestamp": now,
        "ID_Murid": student_row["ID_Murid"],
        "Nama_Murid": student_row["Nama_Murid"],
        "Kelas": student_row["Kelas"],
        "Surah": surah,
        "Ayat_Dari": start_ayat,
        "Ayat_Sampai": end_ayat,
        "Status": status_label,
        "Guru_Pencatat": guru_pencatat,
    }

    write_header = not os.path.exists(LOG_FILE)
    pd.DataFrame([log_data]).to_csv(LOG_FILE, mode="a", index=False, header=write_header)


def update_hafalan_status(
    df: pd.DataFrame,
    student_id: int,
    surah: str,
    start_ayat: int,
    end_ayat: int,
    status_code: int,
    guru_pencatat: str,
):
    max_ayat = JUZ_AMMA_MAP.get(surah)
    if not max_ayat:
        st.error("Nama surah tidak valid.")
        return df

    idx_list = df[df["ID_Murid"] == student_id].index
    if idx_list.empty:
        st.error("Murid tidak ditemukan.")
        return df
    idx = idx_list[0]

    try:
        status_dict = json.loads(df.loc[idx, "Status_Hafalan"])
    except Exception:
        st.error("Format Status_Hafalan rusak untuk murid ini.")
        return df

    ayat_list = status_dict.get(surah, [])
    for i in range(start_ayat - 1, end_ayat):
        if i < len(ayat_list):
            ayat_list[i] = status_code
    status_dict[surah] = ayat_list

    new_status_json = json.dumps(status_dict)
    df.loc[idx, "Status_Hafalan"] = new_status_json
    df.loc[idx, "Total_Ayat_Lulus"] = calculate_lulus_count(new_status_json)
    df.loc[idx, "Update_Terakhir"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.loc[idx, "Guru_Pencatat"] = guru_pencatat

    student_row = df.loc[df["ID_Murid"] == student_id].iloc[0]
    log_setoran(student_row, surah, start_ayat, end_ayat, status_code, guru_pencatat)

    save_data(df)
    st.success(f"Setoran {surah} ayat {start_ayat}-{end_ayat} dicatat.")
    return df


def delete_student(df, student_id, student_name):
    new_df = df[df["ID_Murid"] != student_id].copy()
    if len(new_df) < len(df):
        save_data(new_df)
        st.success(f"Murid **{student_name}** berhasil dihapus.")
    else:
        st.error("Murid tidak ditemukan.")
    return new_df

# =============================
# SIDEBAR (sudah diperbaiki)
# =============================
def sidebar_controls(df):
    st.sidebar.title("Navigasi")

    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, width=120)
    else:
        st.sidebar.markdown("**SMP Negeri 9 Banjar**")

    menu = st.sidebar.radio(
        "Pilih Tampilan",
        [
            "Pencatatan Hafalan",
            "Rekap Per Surah",
            "Dashboard & Laporan",
            "📜 Riwayat Setoran",
            "📅 Laporan Bulanan",
            "📆 Laporan Tahunan (YTD)",
            "👤 Profil Murid",
            "🏫 Pantauan Kelas",
        ],
    )

    guru_list = load_guru_list()
    selected_guru = st.sidebar.selectbox("Nama Guru Pencatat", guru_list)
    kelas_list = ["Pilih Kelas"] + sorted(df["Kelas"].unique().tolist())
    selected_class = st.sidebar.selectbox("Kelas", kelas_list)

    # administrasi murid
    st.sidebar.markdown("---")
    st.sidebar.title("🛠️ Administrasi Data Murid")
    with st.sidebar.expander("➕ Tambah Murid Baru (Manual)"):
        with st.form("add_student_form"):
            new_name = st.text_input("Nama Lengkap Murid", max_chars=100)
            new_kelas = st.text_input("Kelas (contoh: VII-A, VIII-B)", max_chars=10)
            add_submitted = st.form_submit_button("Simpan Murid Baru")
            if add_submitted and new_name and new_kelas:
                add_new_student(new_name, new_kelas)
                st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        **Aplikasi Hafalan Juz Amma**  
        _SMP Negeri 9 Banjar_  
        Pengembang: **Agus Sugiharto Sapari, S.Pd.**  
        © 2025
        """
    )

    return menu, selected_class, selected_guru


# =============================
# MAIN APP
# =============================
def main_app():
    df = ensure_columns(st.session_state.df.copy())
    menu, selected_class, selected_guru = sidebar_controls(df)
    st.write("App berjalan, menu:", menu)


def show_footer():
    st.markdown(
        """
        <hr style="margin-top: 40px; margin-bottom: 10px;">
        <div style="text-align: center; font-size: 14px; color: #555;">
            <strong>Aplikasi Catatan Hafalan Juz Amma</strong><br>
            SMP Negeri 9 Banjar<br>
            <em>Dikembangkan oleh:</em> Agus Sugiharto Sapari, S.Pd.<br>
            © 2025 SMP Negeri 9 Banjar. Seluruh hak cipta dilindungi.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        initialize_database(DB_FILE)
    main_app()
    show_footer()
