import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time
import os
import uuid # Diperlukan untuk ID unik murid/hafalan

# Import data master dan fungsi pembantu dari file juz_amma_data.py
# PASTIKAN FILE juz_amma_data.py ADA DI FOLDER YANG SAMA
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, create_initial_data_structure, calculate_lulus_count

# --- KONFIGURASI APLIKASI ---
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma Online (CSV Lokal)", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KONSTANTA FILE LOKAL ---
# File CSV yang akan disimpan di repositori GitHub
FILE_MURID = "data_murid.csv"
FILE_HAFALAN = "data_hafalan.csv"

# --- FUNGSI UTILITY MANAJEMEN FILE CSV ---

def initialize_csv_files():
    """Membuat file CSV kosong jika belum ada. Dipanggil saat aplikasi mulai."""
    
    # 1. Inisialisasi data_murid.csv
    if not os.path.exists(FILE_MURID) or os.stat(FILE_MURID).st_size == 0:
        df_murid_init = pd.DataFrame(columns=[
            'ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Foto_Murid'
        ])
        df_murid_init.to_csv(FILE_MURID, index=False)
        st.info(f"File **{FILE_MURID}** baru telah dibuat di repositori.")

    # 2. Inisialisasi data_hafalan.csv
    if not os.path.exists(FILE_HAFALAN) or os.stat(FILE_HAFALAN).st_size == 0:
        df_hafalan_init = pd.DataFrame(columns=[
            'ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan'
        ])
        df_hafalan_init.to_csv(FILE_HAFALAN, index=False)
        st.info(f"File **{FILE_HAFALAN}** baru telah dibuat di repositori.")

# Panggil inisialisasi di awal
# initialize_csv_files() # Dipanggil di main()

def write_csv_data(df, file_name, mode='a', header=False):
    """Menulis DataFrame ke file CSV."""
    try:
        # Menulis data ke file. Jika mode='w', overwrite seluruh file.
        df.to_csv(file_name, mode=mode, header=header, index=False) 
        
        # Hapus cache data setelah update
        st.cache_data.clear()
        
        return True
    
    except Exception as e:
        st.error(f"Gagal menulis data ke file {file_name}. Error: {e}")
        return False

# --- FUNGSI PENGAMBILAN DATA (DARI CSV LOKAL) ---

# Menggunakan TTL=3 agar perubahan file lokal cepat terdeteksi dan di-rerun
@st.cache_data(ttl=3) 
def get_all_students_from_csv():
    """Mengambil semua data murid dari file CSV lokal (menggantikan GSheets)."""
    try:
        df = pd.read_csv(FILE_MURID)
        
        # Membersihkan dan validasi kolom
        required_cols = ['ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Foto_Murid']
        if not all(col in df.columns for col in required_cols):
             st.warning(f"Kolom wajib di file {FILE_MURID} tidak lengkap. Menggunakan DataFrame kosong.")
             return pd.DataFrame(columns=required_cols)
             
        df['ID_MURID'] = df['ID_MURID'].astype(str)
        df = df.dropna(subset=['ID_MURID']).drop_duplicates(subset=['ID_MURID'])
        df = df[df['ID_MURID'] != 'ID_MURID'] # Hapus baris header jika terbawa
        return df.reset_index(drop=True)

    except FileNotFoundError:
        st.warning(f"File {FILE_MURID} belum ada. Membuat DataFrame kosong.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Gagal mengambil data murid dari CSV. Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3)
def get_all_hafalans_from_csv(df_murid):
    """Mengambil semua data hafalan dari file CSV lokal (menggantikan GSheets)."""
    try:
        df_hafalan = pd.read_csv(FILE_HAFALAN)
        
        # Membersihkan dan validasi kolom
        required_cols = ['ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']
        if not all(col in df_hafalan.columns for col in required_cols):
             st.warning(f"Kolom wajib di file {FILE_HAFALAN} tidak lengkap. Menggunakan DataFrame kosong.")
             return pd.DataFrame(columns=required_cols)
        
        df_hafalan['ID_MURID'] = df_hafalan['ID_MURID'].astype(str)
        df_hafalan = df_hafalan.dropna(subset=['ID_HAFALAN']).drop_duplicates(subset=['ID_HAFALAN'])
        df_hafalan = df_hafalan[df_hafalan['ID_HAFALAN'] != 'ID_HAFALAN']
        
        # Konversi Tanggal agar bisa diurutkan
        df_hafalan['Tanggal'] = pd.to_datetime(df_hafalan['Tanggal'], errors='coerce')
        df_hafalan = df_hafalan.dropna(subset=['Tanggal'])
        
        return df_hafalan.reset_index(drop=True)
    
    except FileNotFoundError:
        st.warning(f"File {FILE_HAFALAN} belum ada. Membuat DataFrame kosong.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Gagal mengambil data hafalan dari CSV. Error: {e}")
        return pd.DataFrame()

# --- FUNGSI UPDATE/WRITE DATA (CSV) ---

def add_student_csv(df_murid, nama, kelas, nis, nama_wali, kontak_wali):
    """Menambahkan murid baru ke DataFrame dan file CSV."""
    
    new_id = str(uuid.uuid4())
    
    new_student = pd.DataFrame([{
        'ID_MURID': new_id,
        'Nama_Murid': nama,
        'Kelas': kelas,
        'NIS': nis,
        'Nama_Wali': nama_wali,
        'Kontak_Wali': kontak_wali,
        'Foto_Murid': ''
    }])
    
    # Update ke file CSV (append mode, tanpa header)
    if write_csv_data(new_student, FILE_MURID, mode='a', header=False):
        st.success(f"Murid {nama} berhasil ditambahkan dengan ID: {new_id}")
        st.experimental_rerun()

def delete_student_csv(df_murid, student_id, student_name):
    """Menghapus murid dari file CSV (dan menghapus data hafalannya juga)."""
    
    try:
        # 1. Hapus Murid
        df_new_murid = df_murid[df_murid['ID_MURID'] != student_id]
        if not write_csv_data(df_new_murid, FILE_MURID, mode='w', header=True):
            raise Exception("Gagal menulis ulang file Murid.")
            
        # 2. Hapus Data Hafalan terkait
        # Ambil data hafalan terbaru
        df_hafalan = get_all_hafalans_from_csv(df_murid)
        df_new_hafalan = df_hafalan[df_hafalan['ID_MURID'] != student_id]
        if not write_csv_data(df_new_hafalan, FILE_HAFALAN, mode='w', header=True):
            # Rollback murid (opsional tapi baik)
            df_murid.to_csv(FILE_MURID, mode='w', header=True)
            raise Exception("Gagal menulis ulang file Hafalan.")
            
        st.success(f"Murid {student_name} (ID: {student_id}) berhasil dihapus beserta semua data hafalannya.")
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"Gagal menghapus murid dari file CSV. Error: {e}")

def add_hafalan_csv(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan):
    """Menambahkan catatan hafalan baru ke file CSV."""
    
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
    
    # Update ke file CSV (append mode, tanpa header)
    if write_csv_data(new_hafalan, FILE_HAFALAN, mode='a', header=False):
        st.success(f"Catatan hafalan {surah_name} berhasil ditambahkan.")
        st.experimental_rerun()


# --- FUNGSI DISPLAY ---

def show_main_dashboard(df_murid, df_hafalan):
    """Menampilkan dashboard utama."""
    
    st.title("📚 Dashboard Hafalan Juz Amma")
    
    # Tambahkan tombol untuk mengunduh data (penting untuk CSV lokal)
    st.markdown("---")
    st.subheader("Data Lokal (CSV)")
    st.info("Data disimpan langsung di file **data_murid.csv** dan **data_hafalan.csv** di repositori Anda.")
    
    col_dl1, col_dl2 = st.columns(2)
    
    csv_murid = df_murid.to_csv(index=False).encode('utf-8')
    col_dl1.download_button(
        label="📥 Unduh Data Murid (CSV)",
        data=csv_murid,
        file_name='data_murid_export.csv',
        mime='text/csv',
    )
    
    csv_hafalan = df_hafalan.to_csv(index=False).encode('utf-8')
    col_dl2.download_button(
        label="📥 Unduh Data Hafalan (CSV)",
        data=csv_hafalan,
        file_name='data_hafalan_export.csv',
        mime='text/csv',
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
        
        # Gabungkan data murid dan hafalan untuk menghitung progress per murid
        progress_data = []
        for index, murid in df_murid.iterrows():
            id_murid = murid['ID_MURID']
            nama_murid = murid['Nama_Murid']
            kelas = murid['Kelas']
            
            # Filter hafalan untuk murid ini
            murid_hafalans = df_hafalan_valid[df_hafalan_valid['ID_MURID'] == id_murid]
            
            # Hitung total ayat yang sudah lulus
            ayat_lulus = calculate_lulus_count(murid_hafalans)
            
            # Hitung persentase
            persentase = (ayat_lulus / TOTAL_AYAT_JUZ_AMMA) * 100
            
            progress_data.append({
                'Nama Murid': nama_murid,
                'Kelas': kelas,
                'Ayat Lulus': ayat_lulus,
                'Persentase': f"{persentase:.1f}%",
                'Progress Bar': persentase # Untuk kolom visual
            })

        df_progress = pd.DataFrame(progress_data)
        
        # Tampilkan tabel dengan kolom visual
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
def show_add_hafalan_form(df_murid):
    """Menampilkan form untuk mencatat hafalan baru (Dummy dengan CSV logic)."""
    
    murid_options = df_murid[['Nama_Murid', 'Kelas', 'ID_MURID']].apply(
        lambda x: f"{x['Nama_Murid']} - Kelas: {x['Kelas']} |ID:{x['ID_MURID']}", axis=1).tolist()
    
    selected_murid_display = st.selectbox("Pilih Murid", ["Pilih Murid..."] + murid_options)
    
    if selected_murid_display != "Pilih Murid...":
        student_id = selected_murid_display.split('|ID:')[1]
        
        st.markdown(f"**Murid Terpilih:** {selected_murid_display.split(' |ID:')[0]}")
        
        col_s, col_e = st.columns(2)
        surah_name = col_s.selectbox("Surah", SURAH_NAMES)
        
        max_ayat = JUZ_AMMA_MAP.get(surah_name, {}).get('ayat_count', 1)
        
        ayat_awal = col_s.number_input("Ayat Awal", min_value=1, max_value=max_ayat, value=1, key="ayat_awal_input")
        ayat_akhir = col_e.number_input("Ayat Akhir", min_value=ayat_awal, max_value=max_ayat, value=ayat_awal, key="ayat_akhir_input")
        status = col_e.selectbox("Status", ["LULUS", "MENGULANG", "MENGULANG (LALAI)"])
        
        catatan = st.text_area("Catatan Tambahan (Opsional)")
        
        if st.button("Simpan Catatan Hafalan", key="save_hafalan_button"):
            if ayat_awal > ayat_akhir:
                 st.error("Ayat Awal tidak boleh lebih besar dari Ayat Akhir.")
            else:
                add_hafalan_csv(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan)

# --- FORM TAMBAH MURID ---
def show_add_student_form(df_murid):
    """Menampilkan form untuk menambah murid baru (Dummy dengan CSV logic)."""
    st.subheader("Form Tambah Murid Baru")
    
    with st.form("form_add_student"):
        nama = st.text_input("Nama Murid *")
        kelas = st.text_input("Kelas (Contoh: VII A) *")
        nis = st.text_input("NIS *")
        st.caption("Bidang bertanda * wajib diisi.")
        
        col_wali, col_kontak = st.columns(2)
        nama_wali = col_wali.text_input("Nama Wali")
        kontak_wali = col_kontak.text_input("Kontak Wali (WA/Telp)")
        
        submitted = st.form_submit_button("Tambahkan Murid")
        
        if submitted:
            if nama and kelas and nis:
                # Cek duplikasi NIS
                if nis in df_murid['NIS'].values:
                    st.error(f"NIS {nis} sudah terdaftar. Gunakan NIS lain.")
                else:
                    add_student_csv(df_murid.copy(), nama, kelas, nis, nama_wali, kontak_wali)
            else:
                st.error("Nama, Kelas, dan NIS wajib diisi.")

# --- FORM HAPUS MURID ---
def show_delete_student_form(df_murid):
    """Menampilkan form untuk menghapus murid (Dummy dengan CSV logic)."""
    st.subheader("Form Hapus Murid")
    
    df = df_murid.sort_values(by=['Kelas', 'Nama_Murid'])
    
    # Buat peta dari string tampilan unik ke ID internal
    internal_delete_map = {
        f"{row['Nama_Murid']} - Kelas: {row['Kelas']} |ID:{row['ID_MURID']}": row['ID_MURID'] 
        for index, row in df.iterrows()
    }
    
    sorted_internal_keys = sorted(internal_delete_map.keys())
    
    display_list_delete = ['Pilih Murid yang Akan Dihapus'] + sorted_internal_keys
    
    selected_display_string = st.selectbox(
        "Pilih Murid yang Akan Dihapus (Pilih dengan Hati-hati, Aksi ini Permanen)", 
        display_list_delete,
        key="delete_student_select"
    )
    
    student_id_to_delete = None
    student_name_to_delete = None

    if selected_display_string != 'Pilih Murid yang Akan Dihapus':
        
        # Dapatkan ID dari map
        student_id_to_delete = internal_delete_map.get(selected_display_string)
        # Ambil nama dari string tampilan
        student_name_to_delete = selected_display_string.split(' - Kelas:')[0] 

        st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (ID: {student_id_to_delete}) secara permanen dari data?")
        
        if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
            delete_student_csv(df.copy(), student_id_to_delete, student_name_to_delete)
            time.sleep(1) 

# --- EKSEKUSI UTAMA APLIKASI ---

def main():
    
    # 0. Inisialisasi file CSV
    initialize_csv_files()

    # 1. Ambil Data Murid (dari CSV)
    df_murid = get_all_students_from_csv()
    
    # 2. Ambil Data Hafalan (dari CSV)
    df_hafalan = get_all_hafalans_from_csv(df_murid)
    
    # Logic Sidebar dan Tabs
    st.sidebar.title("Navigasi")
    
    tab_list = ["Dashboard", "Input Hafalan", "Manajemen Murid"]
    selected_tab = st.sidebar.radio("Pilih Halaman", tab_list)

    if selected_tab == "Dashboard":
        if not df_murid.empty:
            show_main_dashboard(df_murid, df_hafalan)
        else:
            st.info("Tidak ada data murid yang dimuat. Silakan ke halaman 'Manajemen Murid' untuk menambahkan data.")
            
    elif selected_tab == "Input Hafalan":
        st.header("📝 Catat Hafalan Baru")
        if df_murid.empty:
            st.warning("Tidak ada data murid. Harap tambahkan murid di tab Manajemen Murid terlebih dahulu.")
        else:
            show_add_hafalan_form(df_murid)
            
    elif selected_tab == "Manajemen Murid":
        st.header("👤 Manajemen Data Murid")
        
        # Sub-tab untuk Tambah/Hapus
        sub_tab = st.radio("Aksi", ["Tambah Murid", "Hapus Murid"], horizontal=True)
        
        if sub_tab == "Tambah Murid":
            show_add_student_form(df_murid)
            
        elif sub_tab == "Hapus Murid":
            if df_murid.empty:
                 st.info("Tidak ada murid yang bisa dihapus.")
            else:
                show_delete_student_form(df_murid)

if __name__ == '__main__':
    main()
