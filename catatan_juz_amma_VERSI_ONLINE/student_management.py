import streamlit as st
import pandas as pd
import os
import uuid 
from datetime import datetime

# --- Nama File CSV ---
MURID_CSV = "data_murid.csv"
HAFALAN_CSV = "data_hafalan.csv"

# --- Struktur Kolom ---
COLUMNS_MURID = ['ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Tanggal_Daftar']
COLUMNS_HAFALAN = ['ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']

# --- FUNGSI UTILITY DASAR ---

def load_csv(filepath, columns):
    """Memuat DataFrame dari CSV, mengisi data yang hilang, dan memastikan kolom ada."""
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        # Pastikan semua kolom yang diperlukan ada
        for col in columns:
            if col not in df.columns:
                df[col] = ''
        return df[columns]
    return pd.DataFrame(columns=columns)

def initialize_csv_files():
    """Membuat file CSV kosong jika belum ada dan memuat data ke session state."""
    # 1. Inisialisasi data murid
    if not os.path.exists(MURID_CSV):
        df_murid = pd.DataFrame(columns=COLUMNS_MURID)
        df_murid.to_csv(MURID_CSV, index=False)
        
    # 2. Inisialisasi data hafalan
    if not os.path.exists(HAFALAN_CSV):
        df_hafalan = pd.DataFrame(columns=COLUMNS_HAFALAN)
        df_hafalan.to_csv(HAFALAN_CSV, index=False)

def load_data_to_session_state():
    """Memuat data dari CSV ke Streamlit Session State."""
    if 'df_murid' not in st.session_state:
        st.session_state.df_murid = load_csv(MURID_CSV, COLUMNS_MURID)
        
    if 'df_hafalan' not in st.session_state:
        st.session_state.df_hafalan = load_csv(HAFALAN_CSV, COLUMNS_HAFALAN)

def save_dataframes(df_murid, df_hafalan):
    """Menyimpan kedua DataFrame ke file CSV dan memperbarui session state."""
    try:
        df_murid.to_csv(MURID_CSV, index=False)
        df_hafalan.to_csv(HAFALAN_CSV, index=False)
        st.session_state.df_murid = df_murid
        st.session_state.df_hafalan = df_hafalan
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")
        return False

# --- FUNGSI UTILITY MANAJEMEN MURID ---

def add_new_student(df_murid_copy, nama, kelas, nis, nama_wali, kontak_wali):
    """
    Menambahkan murid baru. Menggunakan NIS sebagai ID_MURID (lebih pendek).
    """
    # 1. Gunakan NIS sebagai ID_MURID (lebih pendek dan unik)
    student_id = str(nis).strip()

    # 2. Cek duplikasi NIS (ID_MURID)
    if student_id in df_murid_copy['ID_MURID'].values:
        st.warning(f"Murid dengan NIS/ID **{student_id}** sudah terdaftar. Gagal menambahkan murid.")
        return

    # 3. Buat DataFrame baru
    new_student = pd.DataFrame([{
        'ID_MURID': student_id,
        'Nama_Murid': nama.strip(),
        'Kelas': kelas.strip(),
        'NIS': student_id, # NIS dan ID_MURID sama
        'Nama_Wali': nama_wali.strip(),
        'Kontak_Wali': kontak_wali.strip(),
        'Tanggal_Daftar': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }])

    # 4. Gabungkan dan simpan
    df_new = pd.concat([df_murid_copy, new_student], ignore_index=True)
    if save_dataframes(df_new, st.session_state.df_hafalan):
        st.success(f"Murid **{nama.strip()}** (ID: {student_id}) berhasil ditambahkan.")
        st.rerun() # Gunakan st.rerun()

def delete_student(df_murid_copy, df_hafalan_copy, student_id, student_name):
    """Menghapus murid dan semua catatan hafalannya."""
    
    # Hapus dari data murid
    df_murid_new = df_murid_copy[df_murid_copy['ID_MURID'] != student_id]
    
    # Hapus catatan hafalan terkait
    df_hafalan_new = df_hafalan_copy[df_hafalan_copy['ID_MURID'] != student_id]
    
    if save_dataframes(df_murid_new, df_hafalan_new):
        st.success(f"Murid **{student_name}** dan semua catatan hafalannya berhasil dihapus.")
        st.rerun() # Gunakan st.rerun()

def upload_students_csv(uploaded_file, df_murid_copy):
    """
    Memproses file CSV yang diunggah untuk menambahkan murid secara massal.
    Menggunakan NIS sebagai ID_MURID.
    """
    # Kolom wajib
    required_cols = ['Nama_Murid', 'Kelas', 'NIS']
    df_upload = None
    delimiter = ';' # Delimiter default (titik koma)

    try:
        # Coba baca dengan delimiter default (titik koma)
        uploaded_file.seek(0)
        df_upload = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
        
        # Bersihkan nama kolom
        df_upload.columns = [col.strip().replace(' ', '_').replace('.', '').replace('-', '_') for col in df_upload.columns]
        
        # Jika kolom yang dibutuhkan tidak terdeteksi, coba dengan koma
        if not all(col in df_upload.columns for col in required_cols):
            # Reset pointer file sebelum membaca lagi
            uploaded_file.seek(0)
            
            # Coba baca dengan koma
            df_upload = pd.read_csv(uploaded_file, sep=',', encoding='utf-8-sig')
            delimiter = ',' # Delimiter yang terdeteksi
            
            # Bersihkan nama kolom lagi
            df_upload.columns = [col.strip().replace(' ', '_').replace('.', '').replace('-', '_') for col in df_upload.columns]

    except Exception as e:
        # Jika pembacaan gagal total
        st.error(f"Gagal memproses file CSV: {e}")
        return

    # Mapping nama kolom yang dibersihkan kembali ke nama standar
    df_upload.rename(columns={
        'Nama_Murid': 'Nama_Murid', 
        'NamaMurid': 'Nama_Murid',
        'Kelas': 'Kelas', 
        'NIS': 'NIS',
        'NamaWali': 'Nama_Wali',
        'KontakWali': 'Kontak_Wali'
    }, inplace=True, errors='ignore')
    
    # --- Validasi Kolom Akhir ---
    missing_cols = [col for col in required_cols if col not in df_upload.columns]
    
    if missing_cols:
        st.error(f"File CSV harus memiliki kolom wajib: {', '.join(required_cols)}. Kolom hilang: {', '.join(missing_cols)}.")
        st.info(f"Kolom yang terdeteksi di file Anda setelah pembersihan (Delimiter: {delimiter}): {list(df_upload.columns)}")
        st.warning("Pastikan file Anda menggunakan pemisah **koma (`,`)** atau **titik koma (`;`)** dan judul kolomnya persis `Nama_Murid`, `Kelas`, dan `NIS`.")
        return
    
    # Tambahkan kolom opsional jika tidak ada
    for col in ['Nama_Wali', 'Kontak_Wali']:
        if col not in df_upload.columns:
            df_upload[col] = ''
            
    # 2. Cleaning dan ID Assignment (NIS sebagai ID_MURID)
    # Pastikan NIS tidak kosong
    df_upload = df_upload.dropna(subset=['NIS']).copy()
    df_upload['ID_MURID'] = df_upload['NIS'].astype(str).str.strip()
    df_upload['Tanggal_Daftar'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 3. Validasi ID (NIS)
    df_upload = df_upload[df_upload['ID_MURID'] != ''].copy()
    
    # 4. Filter duplikat (cek terhadap data yang sudah ada)
    existing_ids = set(df_murid_copy['ID_MURID'].astype(str).values)
    new_students = df_upload[~df_upload['ID_MURID'].astype(str).isin(existing_ids)].copy()
    
    duplicates_count = len(df_upload) - len(new_students)
    
    if new_students.empty:
        if duplicates_count > 0:
            st.warning(f"Semua ({duplicates_count}) murid di file yang diunggah sudah ada (NIS duplikat). Tidak ada data baru yang ditambahkan.")
        else:
                st.error("Tidak ada data murid baru yang valid dalam file yang diunggah.")
        return

    # 5. Gabungkan dan simpan
    # Pastikan kolom sesuai dengan COLUMNS_MURID
    df_new_students_filtered = new_students[COLUMNS_MURID]
    df_combined = pd.concat([df_murid_copy, df_new_students_filtered], ignore_index=True)
    
    if save_dataframes(df_combined, st.session_state.df_hafalan):
        success_msg = f"✅ Berhasil menambahkan **{len(new_students)}** murid baru."
        if duplicates_count > 0:
            success_msg += f" ({duplicates_count} murid dilewati karena NIS/ID duplikat)."
        
        st.success(success_msg)
        st.rerun()
