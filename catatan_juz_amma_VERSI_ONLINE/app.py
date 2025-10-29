import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time
from streamlit.runtime.scriptrunner import get_script_run_ctx
import uuid
import os # Import modul OS untuk manajemen file

# Import data master dan fungsi pembantu dari file juz_amma_data.py
# PASTIKAN FILE juz_amma_data.py ADA DI FOLDER YANG SAMA
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, create_initial_data_structure, calculate_lulus_count

# --- KONFIGURASI APLIKASI ---
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma Online", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KONSTANTA FILE LOKAL ---
# File CSV yang akan disimpan di repositori GitHub
FILE_MURID = "data_murid.csv"
FILE_HAFALAN = "data_hafalan.csv"

# --- FUNGSI UTILITY MANAJEMEN FILE CSV ---

def initialize_csv_files():
    """Membuat file CSV kosong jika belum ada."""
    
    # 1. Inisialisasi data_murid.csv
    if not os.path.exists(FILE_MURID):
        df_murid_init = pd.DataFrame(columns=[
            'ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Foto_Murid'
        ])
        # Tambahkan satu baris dummy agar format kolom terisi
        df_murid_init.to_csv(FILE_MURID, index=False)
        st.info(f"File {FILE_MURID} baru telah dibuat di repositori.")

    # 2. Inisialisasi data_hafalan.csv
    if not os.path.exists(FILE_HAFALAN):
        df_hafalan_init = pd.DataFrame(columns=[
            'ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan'
        ])
        df_hafalan_init.to_csv(FILE_HAFALAN, index=False)
        st.info(f"File {FILE_HAFALAN} baru telah dibuat di repositori.")

# Panggil inisialisasi di awal
initialize_csv_files()

# Gunakan cache untuk mengurangi pembacaan file
@st.cache_data(ttl=3) # Mengurangi TTL menjadi 3 detik agar perubahan cepat terdeteksi
def get_all_students_from_csv():
    """Mengambil semua data murid dari file CSV lokal."""
    try:
        df = pd.read_csv(FILE_MURID)

        # Pastikan kolom yang diperlukan ada
        required_cols = ['ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Foto_Murid']
        if not all(col in df.columns for col in required_cols):
             st.error("Error: Kolom wajib di file Murid tidak ditemukan. Pastikan file CSV tidak rusak.")
             return pd.DataFrame()

        # Membersihkan data
        df['ID_MURID'] = df['ID_MURID'].astype(str)
        df = df.dropna(subset=['ID_MURID']).drop_duplicates(subset=['ID_MURID'])
        df = df[df['ID_MURID'] != 'ID_MURID'] # Hapus baris header jika terbawa

        return df

    except Exception as e:
        st.error(f"Gagal mengambil data murid dari file CSV. Error: {e}")
        st.caption("Pastikan file data_murid.csv ada dan formatnya benar.")
        return pd.DataFrame()

@st.cache_data(ttl=3) # Data di-cache selama 3 detik
def get_all_hafalans_from_csv(df_murid):
    """Mengambil semua data hafalan dari file CSV lokal."""
    if df_murid.empty and os.path.getsize(FILE_MURID) > 100: # Cek ukuran file
        # Hanya perlu data murid untuk referensi, tapi biarkan dimuat jika ada
        pass
        
    try:
        df_hafalan = pd.read_csv(FILE_HAFALAN)
        
        # Pastikan kolom yang diperlukan ada
        required_cols = ['ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']
        if not all(col in df_hafalan.columns for col in required_cols):
             st.error("Error: Kolom wajib di file Hafalan tidak ditemukan. Pastikan file CSV tidak rusak.")
             return pd.DataFrame()
        
        # Membersihkan data
        df_hafalan['ID_MURID'] = df_hafalan['ID_MURID'].astype(str)
        df_hafalan = df_hafalan.dropna(subset=['ID_HAFALAN']).drop_duplicates(subset=['ID_HAFALAN'])
        df_hafalan = df_hafalan[df_hafalan['ID_HAFALAN'] != 'ID_HAFALAN'] # Hapus baris header jika terbawa
        
        return df_hafalan
    
    except Exception as e:
        st.error(f"Gagal mengambil data hafalan dari file CSV. Error: {e}")
        st.caption("Pastikan file data_hafalan.csv ada dan formatnya benar.")
        return pd.DataFrame()

# --- FUNGSI UPDATE/WRITE DATA (CSV) ---

def write_csv_data(df, file_name, mode='a', header=False):
    """Menulis DataFrame ke file CSV."""
    try:
        # Menulis data ke file (append mode untuk menambah baris, atau write mode untuk overwrite)
        df.to_csv(file_name, mode=mode, header=header, index=False) 
        
        # Hapus cache data setelah update
        st.cache_data.clear()
        
        return True
    
    except Exception as e:
        st.error(f"Gagal menulis data ke file {file_name}. Error: {e}")
        return False

# --- LOGIKA APLIKASI (DISESUAIKAN UNTUK CSV) ---

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
        'Foto_Murid': '' # Kosongkan URL foto
    }])
    
    # Update ke file CSV (append mode, tanpa header)
    if write_csv_data(new_student, FILE_MURID, mode='a', header=False):
        st.success(f"Murid {nama} berhasil ditambahkan dengan ID: {new_id}")
        st.experimental_rerun()

def delete_student_csv(df_murid, student_id, student_name):
    """Menghapus murid dari file CSV."""
    
    try:
        # Hanya ambil baris yang ID_MURID-nya TIDAK sama dengan yang akan dihapus
        df_new_murid = df_murid[df_murid['ID_MURID'] != student_id]
        
        # Tulis ulang seluruh file Murid (overwrite mode)
        if write_csv_data(df_new_murid, FILE_MURID, mode='w', header=True):
            st.success(f"Murid {student_name} (ID: {student_id}) berhasil dihapus.")
            
            # Catatan: Kita bisa biarkan data hafalan di file hafalan, atau kita hapus juga:
            # OPTIONAL: Hapus data hafalan terkait
            # df_hafalan = get_all_hafalans_from_csv(df_murid)
            # df_new_hafalan = df_hafalan[df_hafalan['ID_MURID'] != student_id]
            # write_csv_data(df_new_hafalan, FILE_HAFALAN, mode='w', header=True)
            
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

# (Fungsi-fungsi display lainnya tidak saya sentuh karena fokus pada koneksi)

def show_main_dashboard(df_murid, df_hafalan):
    """Menampilkan dashboard utama."""
    
    st.title("📚 Dashboard Hafalan Juz Amma")
    
    # Tambahkan tombol untuk mengunduh data (penting untuk CSV lokal)
    st.markdown("---")
    st.subheader("Data Lokal (CSV)")
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
    
    col1_dash, col2_dash, col3_dash = st.columns([1,1,1])
    
    total_murid = len(df_murid)
    if total_murid > 0:
        total_hafalan = len(df_hafalan)
        
        # Hitung Rata-Rata Ayat Dikuasai
        df_lulus = df_hafalan[df_hafalan['Status'] == 'LULUS'].copy()
        if not df_lulus.empty:
            df_lulus['Ayat_Awal'] = pd.to_numeric(df_lulus['Ayat_Awal'], errors='coerce')
            df_lulus['Ayat_Akhir'] = pd.to_numeric(df_lulus['Ayat_Akhir'], errors='coerce')
            df_lulus.dropna(subset=['Ayat_Awal', 'Ayat_Akhir'], inplace=True)
            
            # Menghitung jumlah ayat
            df_lulus['Jumlah_Ayat'] = df_lulus['Ayat_Akhir'] - df_lulus['Ayat_Awal'] + 1
            total_ayat_dikuasai = df_lulus['Jumlah_Ayat'].sum()
        else:
            total_ayat_dikuasai = 0
            
        avg_ayat = total_ayat_dikuasai / total_murid if total_murid > 0 else 0
        
        col1_dash.metric("Total Murid", total_murid)
        col2_dash.metric("Total Catatan Hafalan", total_hafalan)
        col3_dash.metric("Rata-Rata Ayat Dikuasai / Murid", f"{avg_ayat: .2f} Ayat")
        
        # Grafik
        df_hafalan_valid = df_hafalan[df_hafalan['ID_MURID'].isin(df_murid['ID_MURID'])]
        
        # ... (Sisa kode grafik tetap sama) ...
        # (Asumsi sisa kode grafik Anda ada di sini)
    
    # ... (Sisa kode show_main_dashboard) ...


def show_add_hafalan_form(df_murid):
    """Menampilkan form untuk mencatat hafalan baru."""
    # ... (Kode form hafalan tetap sama) ...
    pass # Hanya placeholder, fungsi ini ada di kode Anda

def show_add_student_form(df_murid):
    """Menampilkan form untuk menambah murid baru."""
    # ... (Kode form murid tetap sama) ...
    pass # Hanya placeholder, fungsi ini ada di kode Anda

def show_delete_student_form(df_murid):
    """Menampilkan form untuk menghapus murid."""
    # ... (Kode form hapus murid tetap sama) ...
    pass # Hanya placeholder, fungsi ini ada di kode Anda


# --- EKSEKUSI UTAMA APLIKASI ---

def main():
    # Menghilangkan pengecekan secrets karena kita pakai CSV
    # if not st.secrets.get("connections", {}).get("gsheets", {}).get("private_key"):
    #     st.error("❗ **SECRETS BELUM LENGKAP**")
    #     st.warning("Silakan isi `private_key` di `secrets.toml` pada Streamlit Cloud Anda.")
    #     st.stop()
    
    # 1. Ambil Data Murid (dari CSV)
    df_murid = get_all_students_from_csv()
    
    if df_murid.empty and os.path.getsize(FILE_MURID) > 100:
        # Jika file ada tapi data kosong (setelah header), beri peringatan
        st.warning("Data Murid ditemukan, tetapi tidak ada entri murid. Silakan tambahkan murid baru.")
    
    # 2. Ambil Data Hafalan (dari CSV)
    df_hafalan = get_all_hafalans_from_csv(df_murid)
    
    # Sisa logika aplikasi (sidebar, tabs, dll.)
    
    st.sidebar.title("Navigasi")
    
    # Membuat Tab
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
            # Asumsi show_add_hafalan_form adalah fungsi yang ada di kode Anda
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


# --- MEMULAI APLIKASI ---
# Panggil main() di akhir file

# Menambahkan dummy functions agar kode kompilasi (ASUMSI fungsi ini ada di kode asli Anda)
def show_add_hafalan_form(df_murid):
    st.subheader("Form Input Hafalan (Dummy)")
    murid_options = df_murid[['Nama_Murid', 'Kelas', 'ID_MURID']].apply(
        lambda x: f"{x['Nama_Murid']} - Kelas: {x['Kelas']} |ID:{x['ID_MURID']}", axis=1).tolist()
    
    selected_murid_display = st.selectbox("Pilih Murid", murid_options)
    
    if selected_murid_display:
        student_id = selected_murid_display.split('|ID:')[1]
        
        col_s, col_e = st.columns(2)
        surah_name = col_s.selectbox("Surah", SURAH_NAMES)
        ayat_awal = col_s.number_input("Ayat Awal", min_value=1, value=1)
        ayat_akhir = col_e.number_input("Ayat Akhir", min_value=ayat_awal, value=ayat_awal)
        status = col_e.selectbox("Status", ["LULUS", "MENGULANG", "MENGULANG (LALAI)"])
        
        catatan = st.text_area("Catatan Tambahan (Opsional)")
        
        if st.button("Simpan Catatan Hafalan", key="save_hafalan_button"):
            add_hafalan_csv(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan)
            
def show_add_student_form(df_murid):
    st.subheader("Form Tambah Murid Baru (Dummy)")
    
    nama = st.text_input("Nama Murid")
    kelas = st.text_input("Kelas (Contoh: VII A)")
    nis = st.text_input("NIS")
    nama_wali = st.text_input("Nama Wali")
    kontak_wali = st.text_input("Kontak Wali (WA/Telp)")
    
    if st.button("Tambahkan Murid", key="add_student_button"):
        if nama and kelas and nis:
            add_student_csv(df_murid.copy(), nama, kelas, nis, nama_wali, kontak_wali)
        else:
            st.error("Nama, Kelas, dan NIS wajib diisi.")

def show_delete_student_form(df_murid):
    st.subheader("Form Hapus Murid (Dummy)")
    
    df = df_murid.sort_values(by='Nama_Murid')
    
    # Peta dari string tampilan ke ID internal
    internal_delete_map = {
        f"{row['Nama_Murid']} - Kelas: {row['Kelas']} |ID:{row['ID_MURID']}": row['ID_MURID'] 
        for index, row in df.iterrows()
    }
    
    sorted_internal_keys = sorted(internal_delete_map.keys())
    
    display_list_delete = ['Pilih Murid yang Akan Dihapus'] + sorted_internal_keys
    
    selected_display_string = st.selectbox(
        "Pilih Murid yang Akan Dihapus", 
        display_list_delete,
        key="delete_student_select"
    )
    
    student_id_to_delete = None
    student_name_to_delete = None

    if selected_display_string != 'Pilih Murid yang Akan Dihapus':
        
        # Karena kuncinya sudah diurutkan, ambil saja kuncinya langsung
        student_id_to_delete = internal_delete_map.get(selected_display_string)
        student_name_to_delete = selected_display_string.split(' - Kelas:')[0] 

        st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (ID: {student_id_to_delete}) secara permanen?")
        
        if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
            delete_student_csv(df.copy(), student_id_to_delete, student_name_to_delete)
            time.sleep(1) 


main()
