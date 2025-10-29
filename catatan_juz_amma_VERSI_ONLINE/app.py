import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time
import os
import uuid 
import inspect 

# --- PASTIKAN SEMUA FILE INI ADA DI FOLDER YANG SAMA ---
# 1. juz_amma_data.py: Berisi JUZ_AMMA_MAP, SURAH_NAMES, dll.
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, calculate_lulus_count

# 2. student_management.py: Berisi fungsi-fungsi CRUD CSV dan inisialisasi file.
from student_management import (
    initialize_csv_files, 
    load_data_to_session_state, 
    add_new_student, 
    delete_student, 
    upload_students_csv,
    save_dataframes
)
# --------------------------------------------------------

# --- KONFIGURASI APLIKASI ---
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma Online (CSV Lokal)", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNGSI TAMBAHAN KHUSUS HAFALAN (WRITE) ---

def add_hafalan(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan):
    """Menambahkan catatan hafalan baru ke DataFrame dan file CSV."""
    
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan
    
    # ID Hafalan tetap menggunakan UUID karena tidak perlu pendek dan harus unik global
    new_id_hafalan = str(uuid.uuid4())
    
    new_hafalan = pd.DataFrame([{
        'ID_HAFALAN': new_id_hafalan,
        'ID_MURID': student_id,
        'Tanggal': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Surah': surah_name,
        'Ayat_Awal': ayat_awal,
        'Ayat_Akhir': ayat_akhir,
        'Status': status,
        'Catatan': catatan
    }])
    
    df_new_hafalan = pd.concat([df_hafalan, new_hafalan], ignore_index=True)

    # Simpan kedua DataFrame
    if save_dataframes(df_murid, df_new_hafalan):
        # Ambil nama murid untuk pesan sukses
        student_row = df_murid[df_murid['ID_MURID'] == student_id]
        nama_murid = student_row['Nama_Murid'].iloc[0] if not student_row.empty else "Murid Tidak Dikenal"
        
        st.success(f"Catatan hafalan **{surah_name}** untuk **{nama_murid}** (NIS: {student_id}) berhasil ditambahkan.")
        st.rerun() # Menggunakan st.rerun()


# --- FUNGSI DISPLAY ---

def show_main_dashboard(df_murid, df_hafalan):
    """Menampilkan dashboard utama."""
    
    st.title("📚 Dashboard Hafalan Juz Amma")
    
    # Tombol Unduh Data
    st.markdown("---")
    st.subheader("Data Lokal (CSV)")
    st.info("Data disimpan di file **data_murid.csv** dan **data_hafalan.csv** di folder aplikasi Anda. Pastikan file ini tidak hilang!")
    
    col_dl1, col_dl2 = st.columns(2)
    
    # Membuat tombol download untuk data murid
    csv_murid = df_murid.to_csv(index=False).encode('utf-8')
    col_dl1.download_button(
        label="📥 Unduh Data Murid (CSV)",
        data=csv_murid,
        file_name='data_murid_export.csv',
        mime='text/csv',
        key="dl_murid"
    )
    
    # Membuat tombol download untuk data hafalan
    csv_hafalan = df_hafalan.to_csv(index=False).encode('utf-8')
    col_dl2.download_button(
        label="📥 Unduh Data Hafalan (CSV)",
        data=csv_hafalan,
        file_name='data_hafalan_export.csv',
        mime='text/csv',
        key="dl_hafalan"
    )
    st.markdown("---")
    
    # Pastikan data siswa yang ditampilkan hanya yang memiliki ID valid
    valid_murid_ids = df_murid['ID_MURID'].unique()
    df_hafalan_valid = df_hafalan[df_hafalan['ID_MURID'].isin(valid_murid_ids)]
    
    col1_dash, col2_dash, col3_dash = st.columns([1,1,1])
    
    total_murid = len(df_murid)
    if total_murid > 0:
        total_hafalan = len(df_hafalan_valid)
        
        # Hitung Rata-Rata Ayat Dikuasai
        df_lulus = df_hafalan_valid[df_hafalan_valid['Status'] == 'LULUS'].copy()
        total_ayat_dikuasai = calculate_lulus_count(df_lulus)
        
        avg_ayat = total_ayat_dikuasai / total_murid if total_murid > 0 else 0
        
        col1_dash.metric("Total Murid", total_murid)
        col2_dash.metric("Total Catatan Hafalan", total_hafalan)
        col3_dash.metric("Rata-Rata Ayat Dikuasai / Murid", f"{avg_ayat: .2f} Ayat")
        
        # --- TABEL PROGRESS MURID ---
        st.subheader("Progress Hafalan Murid")
        
        progress_data = []
        for index, murid in df_murid.iterrows():
            id_murid = murid['ID_MURID']
            nama_murid = murid['Nama_Murid']
            kelas = murid['Kelas']
            
            murid_hafalans = df_hafalan_valid[df_hafalan_valid['ID_MURID'] == id_murid]
            ayat_lulus = calculate_lulus_count(murid_hafalans)
            persentase = (ayat_lulus / TOTAL_AYAT_JUZ_AMMA) * 100
            
            progress_data.append({
                'Nama Murid': nama_murid,
                'Kelas': kelas,
                'Ayat Lulus': ayat_lulus,
                'Persentase': f"{persentase:.1f}%",
                'Progress Bar': persentase
            })

        df_progress = pd.DataFrame(progress_data)
        
        st.dataframe(
            df_progress.sort_values(by='Ayat Lulus', ascending=False),
            column_config={
                "Ayat Lulus": st.column_config.NumberColumn(
                    "Ayat Lulus",
                    help="Total jumlah ayat yang sudah dinyatakan LULUS.",
                    format="%d",
                ),
                "Progress Bar": st.column_config.ProgressColumn(
                    "Progress Juz Amma",
                    help="Persentase ayat yang sudah LULUS dari total 548 ayat.",
                    format="%f",
                    min_value=0,
                    max_value=100,
                )
            },
            hide_index=True
        )
        
    else:
        st.info("Tidak ada data murid yang dimuat.")

# --- FORM INPUT HAFALAN ---
def show_add_hafalan_form():
    """Menampilkan form untuk mencatat hafalan baru, dengan filter kelas."""
    df_murid = st.session_state.df_murid.copy()
    
    st.header("📝 Catat Hafalan Baru")
    
    # 1. FILTER KELAS (BARU)
    all_classes = sorted(df_murid['Kelas'].unique())
    selected_class = st.selectbox("Filter Kelas", ["Semua Kelas"] + all_classes, key="class_filter_hafalan")
    
    # Filter DataFrame berdasarkan kelas yang dipilih
    if selected_class != "Semua Kelas":
        df_filtered = df_murid[df_murid['Kelas'] == selected_class].copy()
    else:
        df_filtered = df_murid.copy()

    if df_filtered.empty:
        st.warning(f"Tidak ada murid di {'kelas ini' if selected_class != 'Semua Kelas' else 'aplikasi Anda'} yang bisa dipilih.")
        return

    # Menggabungkan Nama, Kelas, dan NIS/ID untuk tampilan
    df_filtered = df_filtered.sort_values(by='Nama_Murid')
    murid_options = df_filtered[['Nama_Murid', 'Kelas', 'ID_MURID', 'NIS']].apply(
        lambda x: f"{x['Nama_Murid']} - Kelas: {x['Kelas']} (NIS: {x['NIS']}) |ID:{x['ID_MURID']}", axis=1).tolist()
    
    # Selector Murid
    selected_murid_display = st.selectbox("Pilih Murid", ["Pilih Murid..."] + murid_options, key="murid_picker")
    
    if selected_murid_display != "Pilih Murid...":
        # Ekstraksi ID Murid (yang sekarang adalah NIS)
        try:
            # ID Murid (NIS) ada setelah |ID:
            student_id = selected_murid_display.split('|ID:')[1]
            st.markdown(f"**Murid Terpilih:** {selected_murid_display.split(' |ID:')[0]}")
        except IndexError:
             st.error("Format data ID murid tidak valid. Harap periksa data_murid.csv.")
             return


        # --- Input Hafalan ---
        col_s, col_e = st.columns(2)
        surah_name = col_s.selectbox("Surah", SURAH_NAMES, key="surah_select")
        
        # Pengecekan keamanan ganda untuk JUZ_AMMA_MAP
        if isinstance(JUZ_AMMA_MAP, dict):
            surah_data = JUZ_AMMA_MAP.get(surah_name, {})
            max_ayat = surah_data.get('ayat_count', 1) 
        else:
            max_ayat = 1
            st.warning("Peringatan: Data master Surah tidak dapat diakses.")
        
        # Tampilkan rentang ayat (informasi)
        st.caption(f"Rentang Ayat Tersedia untuk Surah {surah_name}: 1 sampai {max_ayat}")

        # Input Ayat
        ayat_awal = col_s.number_input("Ayat Awal", min_value=1, max_value=max_ayat, value=1, key="ayat_awal_input")
        # Sesuaikan min_value Ayat Akhir berdasarkan Ayat Awal yang dipilih
        ayat_akhir = col_e.number_input("Ayat Akhir", min_value=ayat_awal, max_value=max_ayat, value=ayat_awal, key="ayat_akhir_input")
        status = col_e.selectbox("Status", ["LULUS", "MENGULANG", "MENGULANG (LALAI)"], key="status_select")
        
        catatan = st.text_area("Catatan Tambahan (Opsional)")
        
        if st.button("Simpan Catatan Hafalan", key="save_hafalan_button"):
            if ayat_awal > ayat_akhir:
                 st.error("Ayat Awal tidak boleh lebih besar dari Ayat Akhir.")
            else:
                add_hafalan(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan)

# --- FORM MANAJEMEN MURID ---
def show_manage_student_form():
    """Menampilkan form untuk tambah, upload, dan hapus murid, dengan filter kelas."""
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan
    
    st.header("👤 Manajemen Data Murid")
    
    # Tabs / Radio Button
    sub_tab = st.radio("Pilih Aksi", ["Tambah Murid Manual", "Upload Data CSV", "Hapus Murid"], horizontal=True)
    
    if sub_tab == "Tambah Murid Manual":
        st.subheader("➕ Tambah Murid Baru")
        with st.form("form_add_student"):
            # NIS dijadikan ID Murid, sehingga ID_MURID lebih pendek
            nama = st.text_input("Nama Murid *")
            kelas = st.text_input("Kelas (Contoh: VII A) *")
            nis = st.text_input("NIS (Nomor Induk Siswa - WAJIB DIISI dan UNIK) *")
            st.caption("Bidang bertanda * wajib diisi. NIS akan digunakan sebagai ID Murid.")
            
            col_wali, col_kontak = st.columns(2)
            nama_wali = col_wali.text_input("Nama Wali (Opsional)")
            kontak_wali = col_kontak.text_input("Kontak Wali (Opsional)")
            
            submitted = st.form_submit_button("Tambahkan Murid")
            
            if submitted:
                if nama and kelas and nis:
                    add_new_student(df_murid.copy(), nama, kelas, nis, nama_wali, kontak_wali)
                else:
                    st.error("Nama, Kelas, dan NIS wajib diisi.")

    elif sub_tab == "Upload Data CSV":
        st.subheader("⬆️ Upload Data Siswa (Massal)")
        st.info("Gunakan format CSV dengan kolom wajib: **Nama_Murid**, **Kelas**, **NIS**. Kolom **Nama_Wali** dan **Kontak_Wali** bersifat opsional. Kolom **NIS** akan digunakan sebagai ID murid.")
        
        uploaded_file = st.file_uploader("Pilih file CSV Murid", type=['csv'])
        
        if uploaded_file is not None:
            if st.button("Proses Upload Data", key="process_upload"):
                 upload_students_csv(uploaded_file, df_murid.copy())
            
    elif sub_tab == "Hapus Murid":
        st.subheader("🗑️ Hapus Murid")
        
        if df_murid.empty:
             st.info("Tidak ada murid yang bisa dihapus.")
             return
             
        # 1. FILTER KELAS untuk Hapus Murid (BARU)
        all_classes = sorted(df_murid['Kelas'].unique())
        selected_class_del = st.selectbox("Filter Kelas", ["Semua Kelas"] + all_classes, key="class_filter_delete")
        
        # Filter DataFrame berdasarkan kelas yang dipilih
        if selected_class_del != "Semua Kelas":
            df_filtered = df_murid[df_murid['Kelas'] == selected_class_del].copy()
        else:
            df_filtered = df_murid.copy()

        if df_filtered.empty:
            st.warning(f"Tidak ada murid di {'kelas ini' if selected_class_del != 'Semua Kelas' else 'aplikasi Anda'} yang bisa dihapus.")
            return

        # Sortir untuk tampilan yang lebih baik
        df_filtered = df_filtered.sort_values(by=['Kelas', 'Nama_Murid'])
        
        # Buat peta unik untuk selector (menggunakan NIS sebagai ID)
        internal_delete_map = {
            f"{row['Nama_Murid']} - Kelas: {row['Kelas']} (NIS: {row['NIS']}) |ID:{row['ID_MURID']}": row['ID_MURID'] 
            for index, row in df_filtered.iterrows()
        }
        sorted_internal_keys = sorted(internal_delete_map.keys())
        # Tampilkan Nama, Kelas, dan NIS (tapi sembunyikan |ID:...)
        display_list_delete = ['Pilih Murid yang Akan Dihapus'] + [
            key.rsplit(' |ID:', 1)[0] for key in sorted_internal_keys
        ]
        
        selected_display_string = st.selectbox(
            "Pilih Murid yang Akan Dihapus (Aksi ini Permanen)", 
            display_list_delete,
            key="delete_student_select"
        )
        
        if selected_display_string != 'Pilih Murid yang Akan Dihapus':
            # Cari ID (NIS) yang sesuai dari key internal
            start_of_internal_key = selected_display_string
            found_key = next((key for key in sorted_internal_keys if key.startswith(start_of_internal_key + ' |ID:')), None)
            
            if found_key:
                student_id_to_delete = internal_delete_map[found_key] # ID_MURID adalah NIS
                student_name_to_delete = selected_display_string.split(' - Kelas:')[0] # Ambil nama
            
                st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (NIS: {student_id_to_delete}) secara permanen? Semua data hafalannya akan ikut terhapus!")
                
                if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
                    delete_student(df_murid.copy(), df_hafalan.copy(), student_id_to_delete, student_name_to_delete)
                    time.sleep(1) 
            else:
                 st.warning("Peringatan: Murid yang dipilih tidak dapat diidentifikasi.")


# --- EKSEKUSI UTAMA APLIKASI ---

def main():
    
    # 1. Inisialisasi file CSV (membuat file kosong jika belum ada)
    initialize_csv_files()

    # 2. Memuat data dari CSV ke Streamlit Session State
    load_data_to_session_state()

    # 3. Ambil data dari session state
    df_murid = st.session_state.df_murid
    df_hafalan = st.session_state.df_hafalan
    
    # 4. Logic Sidebar dan Tabs
    st.sidebar.title("Navigasi")
    
    tab_list = ["Dashboard", "Input Hafalan", "Manajemen Murid"]
    selected_tab = st.sidebar.radio("Pilih Halaman", tab_list)

    if selected_tab == "Dashboard":
        # Tampilkan dashboard hanya jika df_murid tidak kosong
        if not df_murid.empty:
            show_main_dashboard(df_murid, df_hafalan)
        else:
            st.info("Tidak ada data murid yang dimuat. Silakan ke halaman 'Manajemen Murid' untuk menambahkan data.")
            
    elif selected_tab == "Input Hafalan":
        if df_murid.empty:
            st.warning("Tidak ada data murid. Harap tambahkan murid di tab Manajemen Murid terlebih dahulu.")
        else:
            show_add_hafalan_form() 
            
    elif selected_tab == "Manajemen Murid":
        show_manage_student_form() 

if __name__ == '__main__':
    main()
