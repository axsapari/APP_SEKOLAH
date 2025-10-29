import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time
from streamlit.runtime.scriptrunner import get_script_run_ctx
import uuid

# Import data master dan fungsi pembantu dari file juz_amma_data.py
# PASTIKAN FILE juz_amma_data.py ADA DI FOLDER YANG SAMA
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, create_initial_data_structure, calculate_lulus_count

# --- KONFIGURASI APLIKASI ---
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma Online", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KONSTANTA SHEETS ---
# Pastikan nama sheet (tab di Google Sheet) ini benar-benar ada dan sama persis.
SHEET_MURID = "Murid" 
SHEET_HAFALAN = "CatatanHafalan"

# --- FUNGSI UTILITY KONEKSI GOOGLE SHEETS ---

# Gunakan cache untuk mengurangi pembacaan dari Google Sheets
@st.cache_data(ttl=300) # Data di-cache selama 5 menit (300 detik)
def get_all_students_from_gheets():
    """Mengambil semua data murid dari Google Sheets."""
    try:
        # Koneksi ke Google Sheets (nama koneksi di secrets.toml harus 'gsheets')
        # MENGHAPUS parameter type="streamlit" agar Streamlit menggunakan konektor bawaan
        conn = st.connection("gsheets")
        
        # Baca data dari Sheet "Murid"
        # usecols=list(range(7)) diasumsikan untuk kolom A sampai G
        df = conn.read(worksheet=SHEET_MURID, usecols=list(range(7)), ttl=5) 

        # Pastikan kolom yang diperlukan ada
        required_cols = ['ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Foto_Murid']
        if not all(col in df.columns for col in required_cols):
             st.error("Error: Kolom wajib di Sheet Murid tidak ditemukan. Pastikan ada ID_MURID, Nama_Murid, Kelas, NIS, Nama_Wali, Kontak_Wali, Foto_Murid.")
             return pd.DataFrame()

        # Membersihkan data
        df['ID_MURID'] = df['ID_MURID'].astype(str)
        df = df.dropna(subset=['ID_MURID']).drop_duplicates(subset=['ID_MURID'])
        df = df[df['ID_MURID'] != 'ID_MURID'] # Hapus baris header jika terbawa
        
        return df

    except Exception as e:
        # Menampilkan pesan error yang lebih jelas di aplikasi
        st.error(f"Gagal mengambil data murid dari Google Sheets. Error: {e}")
        st.caption("Pastikan: 1. `secrets.toml` benar. 2. Service Account diundang sebagai EDITOR. 3. Nama sheet/tab adalah 'Murid'.")
        return pd.DataFrame()

@st.cache_data(ttl=300) # Data di-cache selama 5 menit
def get_all_hafalans_from_gheets(df_murid):
    """Mengambil semua data hafalan dari Google Sheets."""
    if df_murid.empty:
        return pd.DataFrame()
        
    try:
        # Koneksi ulang (tanpa parameter type)
        conn = st.connection("gsheets")

        # Baca data dari Sheet "CatatanHafalan"
        df_hafalan = conn.read(worksheet=SHEET_HAFALAN, ttl=5)
        
        # Pastikan kolom yang diperlukan ada
        required_cols = ['ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']
        if not all(col in df_hafalan.columns for col in required_cols):
             st.error("Error: Kolom wajib di Sheet CatatanHafalan tidak ditemukan. Pastikan ada ID_HAFALAN, ID_MURID, Tanggal, Surah, Ayat_Awal, Ayat_Akhir, Status, Catatan.")
             return pd.DataFrame()
        
        # Membersihkan data
        df_hafalan['ID_MURID'] = df_hafalan['ID_MURID'].astype(str)
        df_hafalan = df_hafalan.dropna(subset=['ID_HAFALAN']).drop_duplicates(subset=['ID_HAFALAN'])
        df_hafalan = df_hafalan[df_hafalan['ID_HAFALAN'] != 'ID_HAFALAN'] # Hapus baris header jika terbawa
        
        return df_hafalan
    
    except Exception as e:
        st.error(f"Gagal mengambil data hafalan dari Google Sheets. Error: {e}")
        st.caption("Pastikan: 1. `secrets.toml` benar. 2. Service Account diundang sebagai EDITOR. 3. Nama sheet/tab adalah 'CatatanHafalan'.")
        return pd.DataFrame()

# --- FUNGSI UPDATE/WRITE DATA ---

def update_gheets_data(new_df, worksheet_name, unique_col='ID_MURID', delete_existing=False):
    """
    Menulis DataFrame baru ke Google Sheets.
    Jika delete_existing=True, sheet dihapus dan diganti.
    Jika False, mencoba melakukan update (tidak disarankan untuk konektor ini kecuali add_rows).
    """
    try:
        conn = st.connection("gsheets")
        
        if delete_existing:
            # Hapus dan Tulis Ulang (Hanya boleh digunakan untuk overwrite penuh)
            conn.clear(worksheet=worksheet_name)
            conn.write(new_df, worksheet=worksheet_name, header=True)
            st.success(f"Data di sheet '{worksheet_name}' berhasil diperbarui.")
        else:
            # Metode add_rows digunakan untuk menambahkan baris baru ke akhir sheet
            conn.add_rows(new_df, worksheet=worksheet_name)
            st.success(f"Berhasil menambahkan data ke sheet '{worksheet_name}'.")

        # Hapus cache data setelah update
        st.cache_data.clear()
        
        return True
    
    except Exception as e:
        st.error(f"Gagal memperbarui/menulis data ke Google Sheets. Error: {e}")
        return False

# --- LOGIKA APLIKASI ---

def add_student_gheets(df_murid, nama, kelas, nis, nama_wali, kontak_wali):
    """Menambahkan murid baru ke DataFrame dan Google Sheets."""
    
    # Membuat ID Murid unik
    # Menggunakan UUID4 untuk ID yang benar-benar unik dan tidak rentan duplikasi
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
    
    # Update ke Google Sheets
    if update_gheets_data(new_student, SHEET_MURID, delete_existing=False):
        st.success(f"Murid {nama} berhasil ditambahkan dengan ID: {new_id}")
        st.experimental_rerun()

def delete_student_gheets(df_murid, student_id, student_name):
    """Menghapus murid dari Google Sheets."""
    
    try:
        conn = st.connection("gsheets")

        # 1. Hapus dari Sheet Murid
        # Hanya ambil baris yang ID_MURID-nya TIDAK sama dengan yang akan dihapus
        df_new_murid = df_murid[df_murid['ID_MURID'] != student_id]
        
        # 2. Tulis ulang Sheet Murid (cara termudah untuk menghapus baris)
        conn.clear(worksheet=SHEET_MURID)
        conn.write(df_new_murid, worksheet=SHEET_MURID, header=True)
        
        # 3. Hapus data hafalan terkait (TIDAK implementasi penuh di sini karena membutuhkan penghapusan baris)
        # Untuk kasus ini, kita biarkan data hafalan di CatatanHafalan, tapi tidak akan muncul di dashboard.
        
        st.success(f"Murid {student_name} (ID: {student_id}) berhasil dihapus.")
        st.cache_data.clear()
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"Gagal menghapus murid dari Google Sheets. Error: {e}")

def add_hafalan_gheets(student_id, surah_name, ayat_awal, ayat_akhir, status, catatan):
    """Menambahkan catatan hafalan baru ke Google Sheets."""
    
    # Membuat ID Hafalan unik
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
    
    # Update ke Google Sheets (add_rows)
    if update_gheets_data(new_hafalan, SHEET_HAFALAN, delete_existing=False):
        st.success(f"Catatan hafalan {surah_name} berhasil ditambahkan.")
        st.experimental_rerun()


# --- FUNGSI DISPLAY ---

# (Fungsi-fungsi display lainnya tidak saya sentuh karena fokus pada koneksi)

# ... (Kode display murid, display hafalan, dan display dashboard lainnya tetap sama) ...

def show_main_dashboard(df_murid, df_hafalan):
    """Menampilkan dashboard utama."""
    
    st.title("📚 Dashboard Hafalan Juz Amma")
    
    # ... (Sisa kode dashboard tetap sama) ...

    col1_dash, col2_dash, col3_dash = st.columns([1,1,1])
    
    total_murid = len(df_murid)
    if total_murid > 0:
        total_hafalan = len(df_hafalan)
        
        # Hitung Rata-Rata Ayat Dikuasai
        total_ayat_dikuasai = df_hafalan[df_hafalan['Status'] == 'LULUS']['Ayat_Akhir'].sum() - df_hafalan[df_hafalan['Status'] == 'LULUS']['Ayat_Awal'].sum() + df_hafalan[df_hafalan['Status'] == 'LULUS'].shape[0]
        avg_ayat = total_ayat_dikuasai / total_murid if total_murid > 0 else 0
        
        col1_dash.metric("Total Murid", total_murid)
        col2_dash.metric("Total Catatan Hafalan", total_hafalan)
        col3_dash.metric("Rata-Rata Ayat Dikuasai / Murid", f"{avg_ayat: .2f} Ayat")
        
        # Grafik
        df_hafalan_valid = df_hafalan[df_hafalan['ID_MURID'].isin(df_murid['ID_MURID'])]
        
        # ... (Sisa kode grafik tetap sama) ...


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
    # Cek apakah secrets terisi
    if not st.secrets.get("connections", {}).get("gsheets", {}).get("private_key"):
        st.error("❗ **SECRETS BELUM LENGKAP**")
        st.warning("Silakan isi `private_key` di `secrets.toml` pada Streamlit Cloud Anda.")
        st.stop()
    
    # 1. Ambil Data Murid
    df_murid = get_all_students_from_gheets()
    
    if df_murid.empty:
        # Jika df_murid kosong karena error atau sheet kosong
        st.warning("Data Murid tidak ditemukan atau gagal dimuat.")
        # Lanjutkan untuk menampilkan form agar user bisa menambahkan murid pertama
        
    # 2. Ambil Data Hafalan (Hanya jika df_murid tidak kosong, untuk mencegah error)
    df_hafalan = get_all_hafalans_from_gheets(df_murid)
    
    # Sisa logika aplikasi (sidebar, tabs, dll.)
    
    # ... (Logika sidebar dan tab tetap sama) ...

    # Menampilkan konten berdasarkan tab yang dipilih
    # ... (Logika tab tetap sama) ...
    
    if not df_murid.empty:
        # Pastikan data ada sebelum menjalankan dashboard
        show_main_dashboard(df_murid, df_hafalan)

    # ... (Sisa kode main() tetap sama) ...
    
    # Tempatkan semua fungsi display yang ada di app.py Anda di sini (saya hanya tinggalkan struktur utama)
    
    # --- STRUKTUR ASLI APP.PY ANDA BERLANJUT DI SINI ---
    # *Karena Anda tidak mengirimkan seluruh kode app.py, saya hanya bisa fokus pada bagian koneksi.*
    # *Saya berasumsi semua logika lainnya (tab, sidebar, form, dll.) ada di bawah ini.*

# --- MEMULAI APLIKASI ---
# if __name__ == '__main__':
#     main() 

# Karena Streamlit menjalankan file dari atas, panggil main() di akhir file

# ... (Bagian akhir file Anda) ...
    
    
# --- REVISI EKSEKUSI UTAMA (Mengikuti pola Streamlit) ---

# st.session_state dan semua logika harus dipanggil langsung, bukan di dalam if __name__ == '__main__':

# 1. Panggil main() di sini
main()

# 2. Sisanya (Sidebar dan Tab) harus ada di luar fungsi untuk dijalankan oleh Streamlit

# (Catatan: Karena saya tidak melihat seluruh kode app.py Anda, saya hanya merevisi fungsi get_all_students_from_gheets dan get_all_hafalans_from_gheets)

# --- END OF FILE REVISION ---
