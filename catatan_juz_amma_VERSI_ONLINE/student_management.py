import pandas as pd
import streamlit as st
import os
import uuid
from datetime import datetime
import time
import io

# --- Konfigurasi File ---
MURID_CSV = "data_murid.csv"
HAFALAN_CSV = "data_hafalan.csv"

def initialize_csv_files():
    """Memastikan file CSV database ada dan inisialisasi DataFrame jika tidak ada."""
    
    # 1. File Murid
    if not os.path.exists(MURID_CSV):
        df_murid = pd.DataFrame(columns=[
            'ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Tanggal_Daftar'
        ])
        df_murid.to_csv(MURID_CSV, index=False)
    
    # 2. File Hafalan
    if not os.path.exists(HAFALAN_CSV):
        df_hafalan = pd.DataFrame(columns=[
            'ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan'
        ])
        df_hafalan.to_csv(HAFALAN_CSV, index=False)

def load_data_to_session_state():
    """Memuat data dari CSV ke Streamlit Session State."""
    if 'df_murid' not in st.session_state:
        st.session_state.df_murid = pd.read_csv(MURID_CSV)
    
    if 'df_hafalan' not in st.session_state:
        st.session_state.df_hafalan = pd.read_csv(HAFALAN_CSV)

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

def add_new_student(df_murid_copy, nama, kelas, nis, nama_wali, kontak_wali):
    """Menambahkan murid baru."""
    # Cek duplikasi NIS
    if nis in df_murid_copy['NIS'].tolist():
        st.error(f"NIS **{nis}** sudah terdaftar. Gunakan NIS lain atau periksa data murid yang ada.")
        return

    new_student = pd.DataFrame([{
        'ID_MURID': nis, # Menggunakan NIS sebagai ID unik
        'Nama_Murid': nama,
        'Kelas': kelas,
        'NIS': nis,
        'Nama_Wali': nama_wali,
        'Kontak_Wali': kontak_wali,
        'Tanggal_Daftar': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }])

    df_new = pd.concat([df_murid_copy, new_student], ignore_index=True)
    
    if save_dataframes(df_new, st.session_state.df_hafalan):
        st.success(f"Murid **{nama}** (NIS: {nis}) berhasil ditambahkan.")
        time.sleep(1)
        st.rerun()

def delete_student(df_murid_copy, df_hafalan_copy, student_id, student_name):
    """Menghapus murid dan semua catatan hafalannya."""
    
    # 1. Hapus Murid dari df_murid
    df_murid_new = df_murid_copy[df_murid_copy['ID_MURID'] != student_id]
    
    # 2. Hapus Catatan Hafalan dari df_hafalan
    df_hafalan_new = df_hafalan_copy[df_hafalan_copy['ID_MURID'] != student_id]
    
    if save_dataframes(df_murid_new, df_hafalan_new):
        st.success(f"Murid **{student_name}** dan semua catatannya berhasil dihapus.")
        time.sleep(1)
        st.rerun()

def upload_students_csv(uploaded_file, df_murid_copy):
    """Memproses dan menambahkan murid dari file CSV yang diunggah."""
    try:
        # Tentukan separator (coba semicolon, lalu koma)
        uploaded_file.seek(0)
        file_content = uploaded_file.read().decode("utf-8")
        
        # Coba baca dengan semicolon (;)
        try:
            df_upload = pd.read_csv(io.StringIO(file_content), sep=';')
        except:
             # Coba baca dengan koma (,)
            df_upload = pd.read_csv(io.StringIO(file_content), sep=',')
            
        required_cols = ['Nama_Murid', 'Kelas', 'NIS']
        if not all(col in df_upload.columns for col in required_cols):
            st.error(f"Kolom wajib tidak ditemukan. Pastikan CSV memiliki kolom: {', '.join(required_cols)}")
            return
        
        df_upload['ID_MURID'] = df_upload['NIS'] # Gunakan NIS sebagai ID
        df_upload['Tanggal_Daftar'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Tambahkan kolom opsional jika tidak ada
        if 'Nama_Wali' not in df_upload.columns:
            df_upload['Nama_Wali'] = ""
        if 'Kontak_Wali' not in df_upload.columns:
            df_upload['Kontak_Wali'] = ""
            
        # Hapus duplikasi NIS dari file upload (hanya ambil baris pertama)
        df_upload_unique = df_upload.drop_duplicates(subset=['NIS'], keep='first')
        
        # Cek NIS yang sudah ada di database
        existing_nis = set(df_murid_copy['NIS'].tolist())
        new_students = df_upload_unique[~df_upload_unique['NIS'].isin(existing_nis)].copy()

        if new_students.empty:
            st.warning("Tidak ada murid baru yang ditambahkan (semua NIS sudah ada atau file kosong).")
            return

        # Pastikan kolom sesuai urutan
        new_students = new_students[[
            'ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Tanggal_Daftar'
        ]]

        # Gabungkan
        df_new = pd.concat([df_murid_copy, new_students], ignore_index=True)

        if save_dataframes(df_new, st.session_state.df_hafalan):
            st.success(f"Berhasil menambahkan {len(new_students)} murid baru dari CSV.")
            st.warning(f"{len(df_upload_unique) - len(new_students)} murid di CSV dilewati karena NIS sudah terdaftar.")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file CSV: {e}. Pastikan format file sudah benar.")
