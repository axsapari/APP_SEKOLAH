import streamlit as st
import pandas as pd
from datetime import datetime
import os
import uuid 
import time
import numpy as np

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
        # Status hanya Hafal atau Mengulang
        'Status': status, 
        'Catatan': catatan
    }])

    df_new = pd.concat([df_hafalan, new_hafalan], ignore_index=True)
    
    # Simpan kedua DataFrame
    if save_dataframes(st.session_state.df_murid, df_new):
        st.toast(f"Catatan hafalan Surah **{surah_name}** ayat {ayat_awal}-{ayat_akhir} berhasil ditambahkan.", icon="✅")
        time.sleep(1)
        # st.rerun() # Tidak perlu rerun, toast sudah cukup

def process_ayat_details(student_id, surah_name, ayat_count, status_data, catatan_global):
    """Memproses detail status per ayat dan menambahkannya sebagai catatan hafalan."""
    df_hafalan = st.session_state.df_hafalan.copy()
    
    records_to_add = []
    
    # Kelompokkan ayat-ayat yang berdekatan dengan status yang sama
    current_status = None
    start_ayat = None
    
    for i in range(1, ayat_count + 1):
        status = status_data[f'ayat_{i}']
        
        if status != current_status:
            # Jika status berubah atau ini adalah awal
            if current_status is not None:
                # Simpan blok sebelumnya
                records_to_add.append({
                    'ID_HAFALAN': str(uuid.uuid4()),
                    'ID_MURID': student_id,
                    'Tanggal': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Surah': surah_name,
                    'Ayat_Awal': start_ayat,
                    'Ayat_Akhir': i - 1, # Ayat sebelumnya adalah akhir blok
                    'Status': current_status,
                    'Catatan': catatan_global # Catatan digunakan untuk seluruh blok
                })
            
            # Mulai blok baru
            current_status = status
            start_ayat = i

        # Jika ini adalah ayat terakhir, simpan blok saat ini
        if i == ayat_count:
            if current_status is not None:
                 records_to_add.append({
                    'ID_HAFALAN': str(uuid.uuid4()),
                    'ID_MURID': student_id,
                    'Tanggal': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Surah': surah_name,
                    'Ayat_Awal': start_ayat,
                    'Ayat_Akhir': ayat_count,
                    'Status': current_status,
                    'Catatan': catatan_global
                })


    if not records_to_add:
        st.warning("Tidak ada ayat yang dipilih, atau semua ayat dibiarkan kosong.")
        return

    # Gabungkan catatan baru
    df_new_records = pd.DataFrame(records_to_add)
    df_new = pd.concat([df_hafalan, df_new_records], ignore_index=True)

    # Simpan kedua DataFrame
    if save_dataframes(st.session_state.df_murid, df_new):
        st.success(f"Catatan detail hafalan Surah **{surah_name}** berhasil disimpan.")
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

def show_add_hafalan_form(student_id, student_name):
    """Tampilkan form untuk input hafalan baru dengan detail per ayat."""
    st.header("📝 INPUT HAFALAN DETAIL")
    
    df_hafalan = st.session_state.df_hafalan
    
    # 1. Pilih Surah (di luar form utama untuk kemudahan interaksi)
    selected_surah = st.selectbox("Pilih Surah", SURAH_NAMES, index=SURAH_NAMES.index("An-Nas"), key="surah_select")
            
    # Dapatkan jumlah ayat berdasarkan Surah yang dipilih
    max_ayat = JUZ_AMMA_MAP.get(selected_surah, {}).get('ayat_count', 1)
    
    # Dapatkan riwayat hafalan Surah ini untuk murid yang dipilih
    df_surah_history = df_hafalan[
        (df_hafalan['ID_MURID'] == student_id) & 
        (df_hafalan['Surah'] == selected_surah)
    ].sort_values(by='Tanggal', ascending=False)

    st.markdown(f"**Surah:** {selected_surah} (Total Ayat: {max_ayat})")
    st.markdown("---")
    
    # Inisialisasi status ayat saat ini (Hafal/Mengulang/Kosong)
    current_status = {}
    
    # Perhitungan Status Ayat Saat Ini (berdasarkan catatan terakhir yang 'Hafal')
    # Ayat yang tercatat 'Hafal' dalam riwayat akan di-highlight
    hafal_ayat_set = set()
    
    if not df_surah_history.empty:
        # Hanya perlu memeriksa catatan 'Hafal' terbaru
        df_hafal = df_surah_history[df_surah_history['Status'] == 'Hafal']
        
        for index, row in df_hafal.iterrows():
            # Tambahkan semua ayat dalam rentang yang dicatat 'Hafal'
            hafal_ayat_set.update(range(row['Ayat_Awal'], row['Ayat_Akhir'] + 1))
    
    # Tentukan status default untuk form
    for i in range(1, max_ayat + 1):
        if i in hafal_ayat_set:
            # Jika ayat sudah pernah dicatat 'Hafal', setting defaultnya adalah 'Hafal'
            current_status[f'ayat_{i}'] = 'Hafal'
        else:
            # Jika belum, setting defaultnya adalah 'Mengulang'
            current_status[f'ayat_{i}'] = 'Mengulang'

    
    with st.form("detail_hafalan_form", clear_on_submit=False):
        
        st.markdown("##### Catat Status Hafalan Per Ayat")
        st.caption("Pilih status 'Hafal' atau 'Mengulang' untuk setiap ayat. Status 'Hafal' yang sudah tercatat akan dipertahankan.")
        
        # Buat grid untuk input status
        cols = st.columns(min(max_ayat, 6)) # Maksimal 6 kolom per baris
        status_data = {}
        
        for i in range(1, max_ayat + 1):
            col_index = (i - 1) % len(cols)
            with cols[col_index]:
                # Gunakan key unik
                key = f"status_ayat_{selected_surah}_{i}"
                
                # Cek status sebelumnya untuk default value
                default_status_index = 0 if current_status.get(f'ayat_{i}') == 'Hafal' else 1
                
                status_data[f'ayat_{i}'] = st.radio(
                    f"Ayat {i}", 
                    ['Hafal', 'Mengulang'], 
                    index=default_status_index,
                    key=key, 
                    horizontal=False,
                    # Teks bantuan
                    label_visibility='visible' 
                )

        st.markdown("---")
        catatan_global = st.text_area("Catatan Global (Opsional - Diterapkan ke semua ayat di atas)", key="catatan_global")
        
        submitted = st.form_submit_button("Simpan Catatan Detail Hafalan")

        if submitted:
            process_ayat_details(student_id, selected_surah, max_ayat, status_data, catatan_global)

    # Tampilkan riwayat hafalan
    if not df_surah_history.empty:
        st.subheader(f"Riwayat Hafalan Surah {selected_surah}")
        st.info("Riwayat di bawah ini adalah blok catatan hafalan yang telah disatukan oleh sistem.")
        df_riwayat = df_surah_history[['Tanggal', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan', 'ID_HAFALAN']].copy()
        df_riwayat['Ayat'] = df_riwayat['Ayat_Awal'].astype(str) + '-' + df_riwayat['Ayat_Akhir'].astype(str)
        st.dataframe(df_riwayat[['Tanggal', 'Ayat', 'Status', 'Catatan', 'ID_HAFALAN']], use_container_width=True)


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
        
        # Perhitungan LULUS sekarang menggunakan fungsi yang telah diperbarui
        lulus_count = calculate_lulus_count(df_hafalan, murid_id)
        
        # Surah Tercatat: Surah yang memiliki *setidaknya* satu catatan hafalan
        df_m = df_hafalan[df_hafalan['ID_MURID'] == murid_id]
        surah_done_count = df_m['Surah'].nunique()

        progress_percentage = (lulus_count / len(SURAH_NAMES)) * 100 if len(SURAH_NAMES) > 0 else 0
        
        last_note = "-"
        if not df_m.empty:
            df_m_sorted = df_m.sort_values(by='Tanggal', ascending=False)
            if 'Catatan' in df_m_sorted.columns and not pd.isna(df_m_sorted['Catatan'].iloc[0]):
                 last_note = df_m_sorted['Catatan'].iloc[0] if df_m_sorted['Catatan'].iloc[0] != '' else "-"
        
        report_data.append({
            'Nama Murid': murid['Nama_Murid'],
            'Kelas': murid['Kelas'],
            'NIS': murid['NIS'],
            'Surah Tercatat': f"{surah_done_count} dari {len(SURAH_NAMES)}",
            'Surah Lulus': lulus_count,
            'Progres Lulus (%)': f"{progress_percentage:.1f}%", # Ubah progres berdasarkan Lulus
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
    
    if st.session_state.get('selected_student_id') is None:
        st.warning("Silakan pilih murid terlebih dahulu di bawah menu.")
        return

    student_id = st.session_state.selected_student_id
    student_name = st.session_state.selected_student_name
    
    st.markdown(f"#### Progres {student_name}")
    murid_data = df_murid[df_murid['ID_MURID'] == student_id].iloc[0]
    col_info1, col_info2, col_info3 = st.columns(3)
    col_info1.metric("Kelas", murid_data['Kelas'])
    col_info2.metric("NIS", murid_data['NIS'])
    col_info3.metric("Tanggal Daftar", murid_data['Tanggal_Daftar'].split(' ')[0])

    df_m = df_hafalan[df_hafalan['ID_MURID'] == student_id]
    
    lulus_count = calculate_lulus_count(df_hafalan, student_id)
    surah_total = len(SURAH_NAMES)
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Surah Lulus", f"{lulus_count} / {surah_total}")
    col_stat2.metric("Progres Lulus", f"{round((lulus_count / surah_total) * 100, 1)}%")
    
    sisa = surah_total - lulus_count
    col_stat3.metric("Sisa Surah", f"{sisa} Surah")

    progress_val = (lulus_count / surah_total)
    st.progress(progress_val)
    st.markdown(f"Progres Lulus Total: **{progress_val * 100:.1f}%**")

    st.markdown("##### Riwayat Detail Hafalan")
    if df_m.empty:
        st.info("Murid ini belum memiliki catatan hafalan.")
    else:
        df_riwayat_display = df_m.sort_values(by='Tanggal', ascending=False)
        st.info("Riwayat di bawah ini adalah blok catatan hafalan yang telah disatukan oleh sistem.")
        df_riwayat_display['Ayat'] = df_riwayat_display['Ayat_Awal'].astype(str) + '-' + df_riwayat_display['Ayat_Akhir'].astype(str)

        st.dataframe(df_riwayat_display[['Tanggal', 'Surah', 'Ayat', 'Status', 'Catatan', 'ID_HAFALAN']], use_container_width=True)

        st.markdown("##### Hapus Catatan Hafalan Tertentu")
        hafalan_to_delete = st.selectbox(
            "Pilih ID Catatan Hafalan yang Akan Dihapus",
            ['Pilih ID'] + df_riwayat_display['ID_HAFALAN'].tolist(),
            key="delete_hafalan_id_select"
        )
        
        if hafalan_to_delete != 'Pilih ID':
            if st.button(f"Hapus Catatan ID: {hafalan_to_delete[:8]}...", key="confirm_delete_hafalan"):
                delete_hafalan(hafalan_to_delete)
            


# --- SELEKSI MURID (GLOBAL) ---
def render_student_selection():
    """Tampilkan filter kelas dan pemilihan murid secara global."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("##### Pilih Murid")
    
    df_murid = st.session_state.df_murid

    if df_murid.empty:
        st.sidebar.warning("Data murid kosong.")
        # Reset selection state
        st.session_state.selected_student_id = None
        st.session_state.selected_student_name = None
        return

    # 1. Ambil daftar kelas unik untuk filter
    unique_kelas = sorted(df_murid['Kelas'].unique().tolist())
    kelas_filter = st.sidebar.selectbox(
        "Filter Kelas", 
        ["Semua Kelas"] + unique_kelas, 
        key="kelas_filter_input_sidebar"
    )

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
    
    selected_murid_display = st.sidebar.selectbox(
        "Pilih Murid", 
        murid_options, 
        key="select_student_global"
    )

    # Simpan ID dan Nama ke Session State
    if selected_murid_display == 'Pilih Murid':
        st.session_state.selected_student_id = None
        st.session_state.selected_student_name = None
    else:
        # Ekstrak NIS/ID_MURID dari string yang dipilih
        nis_part = selected_murid_display.split(" - NIS: ")[1].split(" (Kelas: ")[0]
        student_id = nis_part
        student_name = selected_murid_display.split(" - NIS: ")[0]
        
        st.session_state.selected_student_id = student_id
        st.session_state.selected_student_name = student_name
        
        st.sidebar.markdown(f"**Murid Aktif:** {student_name}")
        st.sidebar.markdown(f"**NIS:** {student_id}")

# --- APLIKASI UTAMA ---

def main():
    # Inisialisasi data (membuat file CSV jika belum ada dan memuat ke session state)
    initialize_csv_files()
    load_data_to_session_state()
    
    # Sidebar: Menu Utama
    st.sidebar.title("Menu Aplikasi")
    
    # Ambil data murid untuk statistik sidebar
    df_murid = st.session_state.df_murid
    total_murid = len(df_murid)
    
    # Menampilkan total murid di sidebar
    st.sidebar.metric("Total Murid Terdaftar", total_murid)
    
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
    
    # Sidebar: Seleksi Murid (Global)
    render_student_selection()

    
    st.title("📚 Sistem Pencatatan Hafalan Juz Amma")
    st.markdown("---")

    if menu == "INPUT HAFALAN":
        student_id = st.session_state.get('selected_student_id')
        student_name = st.session_state.get('selected_student_name')
        if student_id:
            show_add_hafalan_form(student_id, student_name)
        else:
            st.warning("Silakan pilih murid terlebih dahulu di menu samping ('Pilih Murid').")

    elif menu == "LAPORAN PROGRES INDIVIDU":
        show_progress_report()
    elif menu == "TABEL RINGKASAN":
        show_report_table()
    elif menu == "MANAJEMEN MURID":
        show_manage_student_form()

if __name__ == "__main__":
    main()
