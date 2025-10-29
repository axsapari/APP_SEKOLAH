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
        # Tidak perlu sleep, langsung rerun
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
    """Tampilkan form untuk input hafalan baru (rentang ayat) dan visualisasi riwayat per ayat."""
    st.header("📝 INPUT HAFALAN")
    
    df_hafalan = st.session_state.df_hafalan
    
    # 1. Pilih Surah (di luar form utama untuk kemudahan interaksi)
    selected_surah = st.selectbox("Pilih Surah", SURAH_NAMES, index=SURAH_NAMES.index("An-Nas"), key="surah_select")
            
    # Dapatkan jumlah ayat berdasarkan Surah yang dipilih
    max_ayat = JUZ_AMMA_MAP.get(selected_surah, {}).get('ayat_count', 1)
    
    st.markdown(f"**Surah:** {selected_surah} (Total Ayat: {max_ayat})")
    
    # --- FORM INPUT RENTANG AYAT ---
    with st.form("rentang_hafalan_form", clear_on_submit=True):
        st.markdown("##### Catat Rentang Ayat")
        
        col_input1, col_input2, col_input3 = st.columns([1, 1, 2])
        
        with col_input1:
            ayat_awal = st.number_input(
                "Dari Ayat Ke-", 
                min_value=1, 
                max_value=max_ayat, 
                value=1, 
                key="ayat_awal_input"
            )
        
        with col_input2:
            ayat_akhir = st.number_input(
                "Sampai Ayat Ke-", 
                min_value=1, 
                max_value=max_ayat, 
                value=max_ayat, 
                key="ayat_akhir_input"
            )

        with col_input3:
            # Status hanya Hafal dan Mengulang (tidak ada Lulus)
            status = st.radio(
                "Status",
                ['Hafal', 'Mengulang'],
                index=0,
                key="status_radio_input",
                horizontal=True
            )
            
        catatan = st.text_area("Catatan (Opsional)", key="catatan_input")
        
        submitted = st.form_submit_button("Simpan Catatan Hafalan")

        if submitted:
            if ayat_awal > ayat_akhir:
                st.error("Ayat Awal tidak boleh lebih besar dari Ayat Akhir.")
            elif ayat_awal < 1 or ayat_akhir > max_ayat:
                st.error(f"Rentang ayat harus antara 1 sampai {max_ayat}.")
            else:
                add_new_hafalan(student_id, selected_surah, ayat_awal, ayat_akhir, status, catatan)

    st.markdown("---")

    # --- VISUALISASI RIWAYAT PER AYAT (Sesuai Gambar Lampiran) ---
    st.subheader("Visualisasi Progres Ayat")
    
    # Dapatkan riwayat hafalan Surah ini untuk murid yang dipilih
    df_surah_history = df_hafalan[
        (df_hafalan['ID_MURID'] == student_id) & 
        (df_hafalan['Surah'] == selected_surah)
    ].sort_values(by='Tanggal', ascending=False)
    
    # 1. Tentukan status LULUS (Hafal) untuk setiap ayat
    ayat_status = {}
    # Default semua ayat dianggap 'Belum Hafal'
    for i in range(1, max_ayat + 1):
        ayat_status[i] = {'status': 'Belum Hafal', 'color': 'gray', 'hafal_date': '-'}
        
    # Hanya perlu memeriksa catatan 'Hafal' terbaru
    df_hafal = df_surah_history[df_surah_history['Status'] == 'Hafal'].sort_values(by='Tanggal', ascending=True)
    
    # Iterasi dari tanggal terlama ke terbaru untuk mendapatkan tanggal 'Hafal' terakhir
    for index, row in df_hafal.iterrows():
        for i in range(row['Ayat_Awal'], row['Ayat_Akhir'] + 1):
            if i in ayat_status:
                ayat_status[i]['status'] = 'Hafal'
                ayat_status[i]['color'] = 'green'
                ayat_status[i]['hafal_date'] = row['Tanggal'].split(' ')[0] # Ambil tanggal saja
                
    # 2. Tentukan ayat yang pernah 'Mengulang'
    df_mengulang = df_surah_history[df_surah_history['Status'] == 'Mengulang']
    for index, row in df_mengulang.iterrows():
        for i in range(row['Ayat_Awal'], row['Ayat_Akhir'] + 1):
            # Jika ayat sudah Hafal, jangan diubah
            if ayat_status[i]['status'] != 'Hafal':
                ayat_status[i]['status'] = 'Mengulang'
                ayat_status[i]['color'] = 'orange'
                
    # 3. Tampilkan Visualisasi
    # Buat string HTML/Markdown untuk visualisasi grid
    html_content = ""
    ayat_per_row = 10 # 10 ayat per baris
    
    for i in range(1, max_ayat + 1):
        status_info = ayat_status[i]
        
        if (i - 1) % ayat_per_row == 0:
            # Mulai baris baru
            if i > 1:
                html_content += "</div>"
            html_content += "<div style='display: flex; flex-wrap: wrap; margin-bottom: 5px;'>"
            
        color = status_info['color']
        tooltip = f"Ayat {i}: {status_info['status']}"
        
        # Style kotak ayat
        box_style = f"background-color: {color}; color: white; border-radius: 4px; padding: 5px; margin: 2px; width: 40px; text-align: center; font-size: 14px; cursor: pointer; position: relative;"
        
        # Tooltip detail
        tooltip_content = f"Tanggal Hafal Terakhir: {status_info['hafal_date']}" if status_info['status'] == 'Hafal' else f"Status: {status_info['status']}"
        
        html_content += f"""
        <div style="{box_style}" title="{tooltip} - {tooltip_content}">
            {i}
        </div>
        """
        
    # Tutup div baris terakhir
    if max_ayat > 0:
        html_content += "</div>"
        
    # Tampilkan di Streamlit
    st.markdown(html_content, unsafe_allow_html=True)
    
    st.caption("Warna: 🟢 Hafal | 🟠 Mengulang | ⚪ Belum Dicatat/Belum Hafal (Klik kotak untuk detail status)")
    st.markdown("---")

    # Tampilkan riwayat hafalan (tabel)
    if not df_surah_history.empty:
        st.subheader(f"Riwayat Catatan Hafalan Surah {selected_surah} (Tabel)")
        df_riwayat = df_surah_history[['Tanggal', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan', 'ID_HAFALAN']].copy()
        df_riwayat['Rentang Ayat'] = df_riwayat['Ayat_Awal'].astype(str) + '-' + df_riwayat['Ayat_Akhir'].astype(str)
        
        st.dataframe(
            df_riwayat[['Tanggal', 'Rentang Ayat', 'Status', 'Catatan', 'ID_HAFALAN']], 
            use_container_width=True,
            hide_index=True
        )


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
                    # Fungsi add_new_student dipanggil dengan df_murid.copy()
                    add_new_student(st.session_state.df_murid.copy(), nama, kelas, nis, nama_wali, kontak_wali)
                else:
                    st.error("Nama Murid, Kelas, dan NIS wajib diisi.")

    # === TAB 2: UPLOAD CSV MURID ===
    with tab2:
        st.markdown("##### Upload Murid Massal via CSV")
        st.info("File CSV harus memiliki kolom wajib: `Nama_Murid`, `Kelas`, `NIS`. Mendukung pemisah koma (,) atau titik koma (;).")
        uploaded_file = st.file_uploader("Pilih file CSV Murid", type=['csv'], key="csv_uploader")
        
        if uploaded_file:
            if st.button("Proses dan Tambahkan Murid dari CSV", key="upload_csv_button"):
                # Fungsi upload_students_csv dipanggil dengan df_murid.copy()
                upload_students_csv(uploaded_file, st.session_state.df_murid.copy())
    
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
                # Ekstrak NIS yang digunakan sebagai kunci unik
                # Gunakan regex-like split untuk amankan ekstraksi
                nis_part_raw = selected_display_string.split(" - NIS: ")
                if len(nis_part_raw) > 1:
                    nis_part = nis_part_raw[1].split(" (Kelas: ")[0]
                else:
                    st.warning("Format display murid tidak sesuai ekspektasi.")
                    return

                # Pastikan NIS ada dalam DataFrame sebelum mencoba .iloc[0]
                if nis_part in df_filtered_del['NIS'].astype(str).values:
                    # Ambil ID_MURID berdasarkan NIS yang ditemukan
                    student_row = df_filtered_del[df_filtered_del['NIS'].astype(str) == nis_part].iloc[0]
                    student_id_to_delete = student_row['ID_MURID']
                    student_name_to_delete = student_row['Nama_Murid']
                    
                    st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (NIS: {nis_part}) secara permanen? Semua catatan hafalannya akan ikut terhapus!")
                    
                    if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
                        # Panggil fungsi delete_student
                        if delete_student(st.session_state.df_murid.copy(), st.session_state.df_hafalan.copy(), student_id_to_delete, student_name_to_delete):
                            # Jika berhasil dihapus, force rerun
                            st.rerun()
                else:
                    st.warning("Peringatan: NIS murid tidak ditemukan dalam filter saat ini.")
            
            except Exception as e:
                 st.error(f"Peringatan: Terjadi kesalahan saat mencoba mengidentifikasi murid. {e}")


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
            if 'Catatan' in df_m_sorted.columns:
                 # Ambil catatan dari baris pertama yang mungkin bukan string kosong
                 for note in df_m_sorted['Catatan']:
                     if pd.notna(note) and note.strip() != '':
                         last_note = note
                         break
                 
        
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
    try:
        murid_data = df_murid[df_murid['ID_MURID'] == student_id].iloc[0]
        col_info1, col_info2, col_info3 = st.columns(3)
        col_info1.metric("Kelas", murid_data['Kelas'])
        col_info2.metric("NIS", murid_data['NIS'])
        col_info3.metric("Tanggal Daftar", murid_data['Tanggal_Daftar'].split(' ')[0])
    except:
        st.error("Data murid tidak ditemukan.")
        return


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
        st.info("Riwayat di bawah ini adalah blok catatan hafalan.")
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
        try:
            nis_part_raw = selected_murid_display.split(" - NIS: ")
            if len(nis_part_raw) > 1:
                nis_part = nis_part_raw[1].split(" (Kelas: ")[0]
            else:
                st.sidebar.warning("Format display murid tidak sesuai ekspektasi.")
                return

            # Cek di DataFrame
            student_row = df_filtered[df_filtered['NIS'].astype(str) == nis_part].iloc[0]
            
            student_id = student_row['ID_MURID']
            student_name = student_row['Nama_Murid']
            
            st.session_state.selected_student_id = student_id
            st.session_state.selected_student_name = student_name
            
            st.sidebar.markdown(f"**Murid Aktif:** {student_name}")
            st.sidebar.markdown(f"**NIS:** {nis_part}")
        except IndexError:
             st.sidebar.error("Gagal memilih murid. Data murid mungkin tidak lengkap atau NIS tidak ditemukan.")
        except Exception as e:
             st.sidebar.error(f"Gagal memilih murid: {e}")


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
