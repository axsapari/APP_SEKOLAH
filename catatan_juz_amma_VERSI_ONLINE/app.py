import streamlit as st
import pandas as pd
from datetime import datetime
import os
import uuid 
import time
import io

# Import data master dari juz_amma_data.py
# PASTIKAN FILE juz_amma_data.py ADA DI FOLDER YANG SAMA
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, calculate_lulus_count

# Import fungsi I/O dan manajemen dari student_management.py
# PASTIKAN FILE student_management.py ADA DI FOLDER YANG SAMA
from student_management import (
    initialize_csv_files, 
    load_data_to_session_state, 
    save_dataframes, 
    add_new_student, 
    delete_student, 
    upload_students_csv
)

# --- KONFIGURASI APLIKASI ---
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNGSI LOGIKA HAFALAN ---

def add_new_hafalan(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan):
    """Menambahkan catatan hafalan baru ke DataFrame."""
    df_hafalan = st.session_state.df_hafalan.copy()

    new_hafalan = pd.DataFrame([{
        'ID_HAFALAN': str(uuid.uuid4()),
        'ID_MURID': student_id,
        'Tanggal': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Surah': surah_name,
        'Ayat_Awal': ayat_awal,
        'Ayat_Akhir': ayat_akhir,
        'Status': status,
        'Catatan': catatan
    }])

    df_new = pd.concat([df_hafalan, new_hafalan], ignore_index=True)
    
    # Simpan kedua DataFrame
    if save_dataframes(st.session_state.df_murid, df_new):
        st.success(f"Catatan hafalan Surah **{surah_name}** berhasil ditambahkan.")
        time.sleep(1)
        st.rerun()

def delete_hafalan(hafalan_id):
    """Menghapus catatan hafalan berdasarkan ID."""
    df_hafalan_copy = st.session_state.df_hafalan.copy()
    df_hafalan_new = df_hafalan_copy[df_hafalan_copy['ID_HAFALAN'] != hafalan_id]
    
    if save_dataframes(st.session_state.df_murid, df_hafalan_new):
        st.success(f"Catatan hafalan berhasil dihapus.")
        st.rerun()

# --- FUNGSI TAMPILAN (VIEW) ---

def show_add_hafalan_form():
    """Tampilkan form untuk input hafalan baru."""
    st.header("📝 INPUT HAFALAN")
    
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan

    if df_murid.empty:
        st.warning("Data murid kosong. Silakan tambahkan murid di menu 'MANAJEMEN MURID'.")
        return

    # 1. Ambil daftar kelas unik untuk filter
    unique_kelas = sorted(df_murid['Kelas'].unique().tolist())
    kelas_filter = st.selectbox("Filter Siswa Berdasarkan Kelas", ["Semua Kelas"] + unique_kelas, key="kelas_filter_input")

    # 2. Filter murid berdasarkan kelas
    if kelas_filter != "Semua Kelas":
        df_filtered = df_murid[df_murid['Kelas'] == kelas_filter]
    else:
        df_filtered = df_murid
        
    # 3. Buat daftar murid untuk selectbox (Nama - NIS)
    murid_options = ['Pilih Murid'] + sorted([
        f"{row['Nama_Murid']} - NIS: {row['NIS']} (Kelas: {row['Kelas']})"
        for index, row in df_filtered.iterrows()
    ])
    
    selected_murid_display = st.selectbox("Pilih Murid", murid_options, key="select_student_hafalan")

    # Cek apakah murid valid dipilih
    if selected_murid_display == 'Pilih Murid':
        student_id = None
        student_name = None
    else:
        # Ekstrak NIS/ID_MURID dari string yang dipilih
        nis_part = selected_murid_display.split(" - NIS: ")[1].split(" (Kelas: ")[0]
        student_id = nis_part
        student_name = selected_murid_display.split(" - NIS: ")[0]


    with st.form("hafalan_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            surah_name = st.selectbox("Surah", SURAH_NAMES, index=0, key="surah_select")
            
        # Dapatkan jumlah ayat berdasarkan Surah yang dipilih
        max_ayat = JUZ_AMMA_MAP.get(surah_name, {}).get('ayat_count', 1)

        with col2:
            ayat_awal = st.number_input("Ayat Awal", min_value=1, max_value=max_ayat, value=1, key="ayat_awal")
        
        with col3:
            ayat_akhir = st.number_input("Ayat Akhir", min_value=ayat_awal, max_value=max_ayat, value=max_ayat, key="ayat_akhir")
            
        status = st.radio("Status Hafalan", ['Hafal', 'Mengulang', 'Lulus'], index=0, horizontal=True)
        catatan = st.text_area("Catatan Guru (Opsional)", "")
        
        submitted = st.form_submit_button("Simpan Catatan Hafalan")

        if submitted:
            if student_id:
                if ayat_awal > ayat_akhir:
                    st.error("Ayat Awal tidak boleh lebih besar dari Ayat Akhir.")
                else:
                    add_new_hafalan(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan)
            else:
                st.error("Silakan pilih murid terlebih dahulu.")

    # Tampilkan catatan hafalan terakhir murid yang dipilih
    if student_id and not df_hafalan.empty:
        st.subheader(f"Riwayat Hafalan {student_name}")
        df_riwayat = df_hafalan[df_hafalan['ID_MURID'] == student_id].sort_values(by='Tanggal', ascending=False)
        st.dataframe(df_riwayat[['Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']], use_container_width=True)

def show_manage_student_form():
    """Tampilkan form untuk menambahkan/menghapus murid (via input atau CSV) dengan tata letak kolom."""
    st.header("➕ MANAJEMEN MURID") 
    
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan

    # Tata letak tab sesuai permintaan
    tab1, tab2, tab3 = st.tabs(["Tambah Murid Baru", "Upload CSV Murid", "Hapus Murid"])

    # === TAB 1: TAMBAH MURID BARU (Menggunakan kolom) ===
    with tab1:
        st.markdown("##### Input Murid Satuan")
        with st.form("add_student_form", clear_on_submit=True):
            
            # Kolom 1 dan Kolom 2
            col_a, col_b = st.columns(2)
            with col_a:
                nama = st.text_input("Nama Murid*", key="nama_murid_input")
                kelas = st.text_input("Kelas*", help="Contoh: VII A, VIII B, IX C", key="kelas_input")
            
            with col_b:
                nis = st.text_input("NIS/Nomor Induk Siswa*", key="nis_input")
                nama_wali = st.text_input("Nama Wali", key="nama_wali_input")

            # Input di bawah kolom
            kontak_wali = st.text_input("Kontak Wali (Telp/WA)", key="kontak_wali_input")
            
            if st.form_submit_button("Tambahkan Murid"):
                if nama and kelas and nis:
                    add_new_student(df_murid.copy(), nama, kelas, nis, nama_wali, kontak_wali)
                else:
                    st.error("Nama Murid, Kelas, dan NIS wajib diisi.")

    # === TAB 2: UPLOAD CSV MURID ===
    with tab2:
        st.markdown("##### Upload Murid Massal via CSV")
        st.info("File CSV harus menggunakan pemisah **titik koma (;) atau koma (,)** dan memiliki kolom wajib: `Nama_Murid`, `Kelas`, `NIS`.")
        uploaded_file = st.file_uploader("Pilih file CSV Murid", type=['csv'], key="csv_uploader")
        
        if uploaded_file:
            if st.button("Proses dan Tambahkan Murid dari CSV", key="upload_csv_button"):
                upload_students_csv(uploaded_file, df_murid.copy())
    
    # === TAB 3: HAPUS MURID ===
    with tab3:
        st.markdown("##### Hapus Murid")
        if df_murid.empty:
            st.warning("Tidak ada murid yang terdaftar.")
            return

        unique_kelas = sorted(df_murid['Kelas'].unique().tolist())
        kelas_filter_del = st.selectbox("Filter Siswa Berdasarkan Kelas (Hapus)", ["Semua Kelas"] + unique_kelas, key="kelas_filter_delete")

        if kelas_filter_del != "Semua Kelas":
            df_filtered_del = df_murid[df_murid['Kelas'] == kelas_filter_del]
        else:
            df_filtered_del = df_murid
            
        murid_options_del = ['Pilih Murid yang Akan Dihapus'] + sorted([
            f"{row['Nama_Murid']} - Kelas: {row['Kelas']} - NIS: {row['NIS']}"
            for index, row in df_filtered_del.iterrows()
        ])
        
        selected_display_string = st.selectbox(
            "Pilih Murid yang Akan Dihapus", 
            murid_options_del,
            key="delete_student_select"
        )
        
        student_id_to_delete = None
        student_name_to_delete = None

        if selected_display_string != 'Pilih Murid yang Akan Dihapus':
            try:
                # Ekstrak NIS/ID_MURID
                nis_part = selected_display_string.split(" - NIS: ")[1]
                student_id_to_delete = nis_part
                student_name_to_delete = selected_display_string.split(' - Kelas:')[0] 
                
                st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (NIS: {student_id_to_delete}) secara permanen? Semua catatan hafalannya akan ikut terhapus!")
                
                if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
                    delete_student(df_murid.copy(), df_hafalan.copy(), student_id_to_delete, student_name_to_delete)
                    time.sleep(1) 
                    st.rerun()
            except IndexError:
                st.warning("Peringatan: Murid yang dipilih memiliki format data yang tidak lengkap.")


def show_report_table():
    """Tampilkan ringkasan data hafalan dalam bentuk tabel."""
    st.header("📋 TABEL RINGKASAN") # Nama disesuaikan
    
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan

    if df_murid.empty:
        st.warning("Data murid kosong. Tidak ada laporan yang ditampilkan.")
        return

    report_data = []
    
    for index, murid in df_murid.iterrows():
        murid_id = murid['ID_MURID']
        df_m = df_hafalan[df_hafalan['ID_MURID'] == murid_id]
        surah_done_count = df_m['Surah'].nunique()
        lulus_count = calculate_lulus_count(df_hafalan, murid_id)
        progress_percentage = (surah_done_count / len(SURAH_NAMES)) * 100 if len(SURAH_NAMES) > 0 else 0
        
        last_note = "-"
        if not df_m.empty:
            df_m_sorted = df_m.sort_values(by='Tanggal', ascending=False)
            # Pastikan kolom 'Catatan' ada dan baris pertama tidak kosong
            if 'Catatan' in df_m_sorted.columns and not pd.isna(df_m_sorted['Catatan'].iloc[0]):
                 last_note = df_m_sorted['Catatan'].iloc[0] if df_m_sorted['Catatan'].iloc[0] != '' else "-"
        
        report_data.append({
            'Nama Murid': murid['Nama_Murid'],
            'Kelas': murid['Kelas'],
            'NIS': murid['NIS'],
            'Surah Selesai': f"{surah_done_count} dari {len(SURAH_NAMES)}",
            'Surah Lulus': lulus_count,
            'Progres (%)': f"{progress_percentage:.1f}%",
            'Catatan Terakhir': last_note
        })

    df_report = pd.DataFrame(report_data)
    
    unique_kelas = sorted(df_report['Kelas'].unique().tolist())
    kelas_filter_report = st.selectbox("Filter Laporan Berdasarkan Kelas", ["Semua Kelas"] + unique_kelas, key="kelas_filter_report")

    if kelas_filter_report != "Semua Kelas":
        df_display = df_report[df_report['Kelas'] == kelas_filter_report]
    else:
        df_display = df_report

    df_display = df_display.sort_values(by='Kelas')
    st.dataframe(df_display, use_container_width=True)

    st.download_button(
        label="Download Laporan (CSV)",
        data=df_report.to_csv(index=False).encode('utf-8'),
        file_name='laporan_hafalan_juz_amma.csv',
        mime='text/csv',
    )


def show_progress_report():
    """Tampilkan visualisasi dan detail progres per murid."""
    st.header("🧑‍🎓 LAPORAN PROGRES INDIVIDU") # Nama disesuaikan
    
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan
    
    if df_murid.empty:
        st.warning("Data murid kosong. Tidak ada laporan yang ditampilkan.")
        return

    murid_options = ['Pilih Murid'] + sorted([
        f"{row['Nama_Murid']} - NIS: {row['NIS']} (Kelas: {row['Kelas']})"
        for index, row in df_murid.iterrows()
    ])
    
    selected_murid_display = st.selectbox("Pilih Murid untuk Dilihat Progresnya", murid_options, key="select_student_report")

    if selected_murid_display == 'Pilih Murid':
        return

    nis_part = selected_murid_display.split(" - NIS: ")[1].split(" (Kelas: ")[0]
    student_id = nis_part
    student_name = selected_murid_display.split(" - NIS: ")[0]
    
    st.markdown(f"#### Progres {student_name}")
    murid_data = df_murid[df_murid['ID_MURID'] == student_id].iloc[0]
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.metric("Kelas", murid_data['Kelas'])
    col_info2.metric("NIS", murid_data['NIS'])
    col_info3.metric("Tanggal Daftar", murid_data['Tanggal_Daftar'].split(' ')[0])

    df_m = df_hafalan[df_hafalan['ID_MURID'] == student_id]
    
    lulus_count = calculate_lulus_count(df_hafalan, student_id)
    surah_done_count = df_m['Surah'].nunique()
    surah_total = len(SURAH_NAMES)
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Surah Tercatat", f"{surah_done_count} / {surah_total}")
    col_stat2.metric("Status Lulus", f"{lulus_count} Surah")
    
    sisa = surah_total - surah_done_count
    col_stat3.metric("Sisa Surah", f"{sisa} Surah")

    progress_val = (surah_done_count / surah_total)
    st.progress(progress_val)
    st.markdown(f"Progres total: **{progress_val * 100:.1f}%**")

    st.markdown("##### Riwayat Detail Hafalan")
    if df_m.empty:
        st.info("Murid ini belum memiliki catatan hafalan.")
    else:
        df_riwayat_display = df_m.sort_values(by='Tanggal', ascending=False)
        st.dataframe(df_riwayat_display[['Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan', 'ID_HAFALAN']], use_container_width=True)

        st.markdown("##### Hapus Catatan Hafalan Tertentu")
        hafalan_to_delete = st.selectbox(
            "Pilih ID Catatan Hafalan yang Akan Dihapus",
            ['Pilih ID'] + df_riwayat_display['ID_HAFALAN'].tolist(),
            key="delete_hafalan_id_select"
        )
        
        if hafalan_to_delete != 'Pilih ID':
            if st.button(f"Hapus Catatan ID: {hafalan_to_delete[:8]}...", key="confirm_delete_hafalan"):
                delete_hafalan(hafalan_to_delete)
            


# --- APLIKASI UTAMA ---

def main():
    # Inisialisasi data (membuat file CSV jika belum ada dan memuat ke session state)
    initialize_csv_files()
    load_data_to_session_state()
    
    # Sidebar
    st.sidebar.title("Menu Aplikasi")
    st.sidebar.markdown("---")
    
    # Ambil data murid untuk statistik sidebar
    df_murid = st.session_state.df_murid
    total_murid = len(df_murid)
    
    # Menampilkan total murid di sidebar
    st.sidebar.metric("Total Murid Terdaftar", total_murid)
    
    # FIX: Hapus argumen 'icons' untuk mengatasi TypeError
    menu = st.sidebar.radio(
        "Pilih Halaman",
        [
            "INPUT HAFALAN", 
            "LAPORAN PROGRES INDIVIDU", 
            "TABEL RINGKASAN", 
            "MANAJEMEN MURID"
        ],
        key="main_menu_radio"
    )
    
    st.title("📚 Sistem Pencatatan Hafalan Juz Amma")
    st.markdown("---")

    if menu == "INPUT HAFALAN":
        show_add_hafalan_form()
    elif menu == "LAPORAN PROGRES INDIVIDU":
        show_progress_report()
    elif menu == "TABEL RINGKASAN":
        show_report_table()
    elif menu == "MANAJEMEN MURID":
        show_manage_student_form()

if __name__ == "__main__":
    main()
