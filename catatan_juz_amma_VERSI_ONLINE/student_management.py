import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid
from io import StringIO

# --- KONFIGURASI FILE CSV ---
MURID_CSV = "data_murid.csv"
HAFALAN_CSV = "data_hafalan.csv"

# --- STRUKTUR WAJIB ---
COLUMNS_MURID = ['ID_MURID', 'Tanggal_Daftar', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali']
COLUMNS_HAFALAN = ['ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']
REQUIRED_UPLOAD_COLUMNS = ['Nama_Murid', 'Kelas', 'NIS'] # Kolom wajib di file CSV upload

# --- FUNGSI I/O DATA ---

def initialize_csv_files():
    """Membuat file CSV kosong jika belum ada."""
    if not os.path.exists(MURID_CSV):
        df_murid = pd.DataFrame(columns=COLUMNS_MURID)
        df_murid.to_csv(MURID_CSV, index=False)
    
    if not os.path.exists(HAFALAN_CSV):
        df_hafalan = pd.DataFrame(columns=COLUMNS_HAFALAN)
        df_hafalan.to_csv(HAFALAN_CSV, index=False)

def load_data_to_session_state():
    """Memuat data dari CSV ke Streamlit Session State."""
    if 'df_murid' not in st.session_state:
        try:
            st.session_state.df_murid = pd.read_csv(MURID_CSV)
        except Exception:
            st.session_state.df_murid = pd.DataFrame(columns=COLUMNS_MURID)

    if 'df_hafalan' not in st.session_state:
        try:
            st.session_state.df_hafalan = pd.read_csv(HAFALAN_CSV)
            # Pastikan kolom Ayat_Awal dan Ayat_Akhir adalah integer
            st.session_state.df_hafalan['Ayat_Awal'] = st.session_state.df_hafalan['Ayat_Awal'].fillna(0).astype(int)
            st.session_state.df_hafalan['Ayat_Akhir'] = st.session_state.df_hafalan['Ayat_Akhir'].fillna(0).astype(int)
            
        except Exception:
            st.session_state.df_hafalan = pd.DataFrame(columns=COLUMNS_HAFALAN)

def save_dataframes(df_murid, df_hafalan):
    """Menyimpan kedua DataFrame ke CSV dan memperbarui session state."""
    try:
        df_murid.to_csv(MURID_CSV, index=False)
        df_hafalan.to_csv(HAFALAN_CSV, index=False)
        
        st.session_state.df_murid = df_murid
        st.session_state.df_hafalan = df_hafalan
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke CSV: {e}")
        return False

# --- FUNGSI MANAJEMEN MURID ---

def add_new_student(df_murid_copy, nama, kelas, nis, nama_wali="", kontak_wali=""):
    """Menambahkan baris murid baru ke DataFrame."""
    
    # Cek duplikasi NIS
    if nis in df_murid_copy['NIS'].astype(str).values:
        st.error(f"Gagal: NIS **{nis}** sudah terdaftar.")
        return False
        
    new_student = pd.DataFrame([{
        'ID_MURID': str(uuid.uuid4()),
        'Tanggal_Daftar': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Nama_Murid': nama.strip(),
        'Kelas': kelas.strip(),
        'NIS': str(nis).strip(),
        'Nama_Wali': nama_wali.strip(),
        'Kontak_Wali': kontak_wali.strip()
    }])

    df_new = pd.concat([df_murid_copy, new_student], ignore_index=True)
    
    if save_dataframes(df_new, st.session_state.df_hafalan):
        st.toast(f"Murid **{nama}** berhasil ditambahkan!", icon="🎉")
        return True
    return False

def delete_student(df_murid_copy, df_hafalan_copy, student_id, student_name):
    """Menghapus murid dan semua catatan hafalannya."""
    df_murid_new = df_murid_copy[df_murid_copy['ID_MURID'] != student_id]
    df_hafalan_new = df_hafalan_copy[df_hafalan_copy['ID_MURID'] != student_id]
    
    if save_dataframes(df_murid_new, df_hafalan_new):
        st.success(f"Murid **{student_name}** dan semua catatannya berhasil dihapus.")
        return True
    return False

def upload_students_csv(uploaded_file, df_murid_current):
    """
    Memproses file CSV yang diunggah, mencoba mendeteksi pemisah (koma atau titik koma),
    dan menambahkan murid baru jika tidak ada duplikasi NIS.
    """
    try:
        # Membaca isi file yang diunggah
        file_content = uploaded_file.getvalue().decode("utf-8")
        
        # Mencoba deteksi pemisah
        separators = [',', ';']
        df_uploaded = None
        delimiter_used = None

        for sep in separators:
            try:
                # Gunakan StringIO untuk membaca konten string sebagai file
                df_test = pd.read_csv(StringIO(file_content), sep=sep, dtype={'NIS': str})
                
                # Cek apakah kolom wajib ada
                if all(col in df_test.columns for col in REQUIRED_UPLOAD_COLUMNS):
                    df_uploaded = df_test
                    delimiter_used = sep
                    break # Berhasil, keluar dari loop
                
            except Exception:
                continue # Coba pemisah berikutnya
        
        if df_uploaded is None:
            # Gagal mendeteksi pemisah atau kolom tidak lengkap
            st.error(f"Gagal: Kolom wajib tidak ditemukan. Pastikan CSV memiliki kolom: {', '.join(REQUIRED_UPLOAD_COLUMNS)} dan menggunakan pemisah koma (,) atau titik koma (;).")
            return

        # 1. Bersihkan data yang diunggah dan pastikan kolom string
        df_uploaded = df_uploaded[REQUIRED_UPLOAD_COLUMNS + [col for col in ['Nama_Wali', 'Kontak_Wali'] if col in df_uploaded.columns]].copy()
        
        # Tambahkan kolom opsional jika tidak ada
        if 'Nama_Wali' not in df_uploaded.columns: df_uploaded['Nama_Wali'] = ''
        if 'Kontak_Wali' not in df_uploaded.columns: df_uploaded['Kontak_Wali'] = ''

        # Konversi NIS ke string untuk perbandingan yang konsisten
        df_uploaded['NIS'] = df_uploaded['NIS'].astype(str).str.strip()
        df_murid_current['NIS'] = df_murid_current['NIS'].astype(str).str.strip()

        # 2. Identifikasi NIS yang sudah ada
        existing_nises = set(df_murid_current['NIS'].unique())
        
        # 3. Filter data yang akan ditambahkan (hanya yang NIS-nya unik)
        df_to_add = df_uploaded[~df_uploaded['NIS'].isin(existing_nises)].copy()
        
        if df_to_add.empty:
            st.warning("Semua murid dalam file CSV sudah terdaftar atau terdapat duplikasi NIS. Tidak ada murid baru yang ditambahkan.")
            return

        # 4. Tambahkan kolom wajib lainnya
        df_to_add['ID_MURID'] = [str(uuid.uuid4()) for _ in range(len(df_to_add))]
        df_to_add['Tanggal_Daftar'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 5. Gabungkan DataFrame
        # Pastikan urutan kolom sesuai dengan COLUMNS_MURID sebelum concat
        df_to_add = df_to_add[COLUMNS_MURID]
        df_new = pd.concat([df_murid_current, df_to_add], ignore_index=True)
        
        if save_dataframes(df_new, st.session_state.df_hafalan):
            st.success(f"Berhasil menambahkan **{len(df_to_add)}** murid baru (menggunakan pemisah: '{delimiter_used}'). Murid dengan NIS yang sudah ada diabaikan.")
            st.info(f"Total Murid Sekarang: {len(df_new)}")
            st.rerun()
            
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {e}")
        st.stop()
