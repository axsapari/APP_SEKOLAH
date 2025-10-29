import pandas as pd
import streamlit as st
import os
import uuid
from datetime import datetime

# --- KONSTANTA FILE LOKAL ---
FILE_MURID = "data_murid.csv"
FILE_HAFALAN = "data_hafalan.csv"

# --- STRUKTUR DATA WAJIB ---
STUDENT_COLS = ['ID_MURID', 'Nama_Murid', 'Kelas', 'NIS', 'Nama_Wali', 'Kontak_Wali', 'Foto_Murid']
HAFALAN_COLS = ['ID_HAFALAN', 'ID_MURID', 'Tanggal', 'Surah', 'Ayat_Awal', 'Ayat_Akhir', 'Status', 'Catatan']

def initialize_csv_files():
    """Memastikan file CSV untuk Murid dan Hafalan ada dengan header yang benar."""
    
    if not os.path.exists(FILE_MURID) or os.stat(FILE_MURID).st_size == 0:
        pd.DataFrame(columns=STUDENT_COLS).to_csv(FILE_MURID, index=False)
        st.info(f"File **{FILE_MURID}** baru telah dibuat.")

    if not os.path.exists(FILE_HAFALAN) or os.stat(FILE_HAFALAN).st_size == 0:
        pd.DataFrame(columns=HAFALAN_COLS).to_csv(FILE_HAFALAN, index=False)
        st.info(f"File **{FILE_HAFALAN}** baru telah dibuat.")
    
    # Setelah inisialisasi, paksa pemuatan ulang
    load_data_to_session_state()
    st.cache_data.clear() # Hapus cache data
    
def load_data_to_session_state():
    """Memuat data CSV ke Streamlit session state."""
    
    # Gunakan st.cache_data agar cepat dan tidak perlu dibaca terus-menerus
    @st.cache_data(ttl=3) 
    def load_cached_data():
        try:
            df_murid = pd.read_csv(FILE_MURID)
            # Membersihkan dan validasi
            if 'ID_MURID' in df_murid.columns:
                df_murid['ID_MURID'] = df_murid['ID_MURID'].astype(str)
                df_murid = df_murid.dropna(subset=['ID_MURID']).drop_duplicates(subset=['ID_MURID']).reset_index(drop=True)
            else:
                 df_murid = pd.DataFrame(columns=STUDENT_COLS)
                 
            df_hafalan = pd.read_csv(FILE_HAFALAN)
            if 'ID_HAFALAN' in df_hafalan.columns:
                df_hafalan['ID_HAFALAN'] = df_hafalan['ID_HAFALAN'].astype(str)
                df_hafalan['Tanggal'] = pd.to_datetime(df_hafalan['Tanggal'], errors='coerce')
                df_hafalan = df_hafalan.dropna(subset=['ID_HAFALAN', 'Tanggal']).drop_duplicates(subset=['ID_HAFALAN']).reset_index(drop=True)
            else:
                 df_hafalan = pd.DataFrame(columns=HAFALAN_COLS)
            
            return df_murid, df_hafalan
        
        except (FileNotFoundError, pd.errors.EmptyDataError):
             # Jika file kosong atau tidak ditemukan, kembalikan DataFrame kosong dengan header
             return pd.DataFrame(columns=STUDENT_COLS), pd.DataFrame(columns=HAFALAN_COLS)
        except Exception as e:
            st.error(f"Gagal memuat data dari CSV: {e}")
            return pd.DataFrame(columns=STUDENT_COLS), pd.DataFrame(columns=HAFALAN_COLS)

    df_murid, df_hafalan = load_cached_data()
    st.session_state['df_murid'] = df_murid
    st.session_state['df_hafalan'] = df_hafalan
    
def save_dataframes(df_murid, df_hafalan):
    """Menyimpan kedua DataFrame ke file CSV dan memperbarui session state."""
    try:
        df_murid.to_csv(FILE_MURID, index=False)
        df_hafalan.to_csv(FILE_HAFALAN, index=False)
        st.session_state['df_murid'] = df_murid
        st.session_state['df_hafalan'] = df_hafalan
        st.cache_data.clear() # Hapus cache setelah menyimpan
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke CSV: {e}")
        return False
        
# --- FUNGSI UTAMA MANAJEMEN SISWA ---

def add_new_student(df_murid, nama, kelas, nis, nama_wali="", kontak_wali=""):
    """Menambahkan baris murid baru ke DataFrame."""
    
    # Cek duplikasi NIS
    if not df_murid.empty and nis in df_murid['NIS'].values:
        st.error(f"NIS **{nis}** sudah terdaftar.")
        return False

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
    
    df_new_murid = pd.concat([df_murid, new_student], ignore_index=True)
    
    if save_dataframes(df_new_murid, st.session_state.df_hafalan):
        st.success(f"Murid **{nama}** berhasil ditambahkan.")
        st.experimental_rerun()
        return True
    return False

def delete_student(df_murid, df_hafalan, student_id, student_name):
    """Menghapus murid dan semua catatan hafalannya."""
    
    # Hapus Murid
    df_new_murid = df_murid[df_murid['ID_MURID'] != student_id]
    
    # Hapus Catatan Hafalan
    df_new_hafalan = df_hafalan[df_hafalan['ID_MURID'] != student_id]
    
    if save_dataframes(df_new_murid, df_new_hafalan):
        st.success(f"Murid **{student_name}** dan semua data hafalannya berhasil dihapus.")
        st.experimental_rerun()
        return True
    return False

def upload_students_csv(uploaded_file, df_current_murid):
    """Memproses file CSV yang diunggah dan menggabungkannya dengan data murid yang ada."""
    
    # 1. Baca File yang diupload
    try:
        # Asumsikan file upload menggunakan delimiter koma (,) standar
        df_uploaded = pd.read_csv(uploaded_file)
    except Exception as e:
         try:
            # Coba dengan delimiter semicolon (;) jika koma gagal (karena data siswaup.csv menggunakan ;)
            df_uploaded = pd.read_csv(uploaded_file, sep=';')
         except Exception:
            st.error("Gagal membaca file CSV. Pastikan formatnya benar (gunakan koma atau titik koma sebagai pemisah).")
            return

    # 2. Validasi Kolom
    required_upload_cols = ['Nama_Murid', 'Kelas', 'NIS']
    if not all(col in df_uploaded.columns for col in required_upload_cols):
        st.error(f"CSV harus memiliki kolom: {', '.join(required_upload_cols)}")
        return

    # 3. Proses Penambahan ID dan Kolom Default
    new_students_list = []
    nis_set = set(df_current_murid['NIS'].astype(str).tolist())
    duplicates_count = 0
    
    for index, row in df_uploaded.iterrows():
        nis = str(row['NIS']).strip()
        
        # Cek duplikasi NIS dengan data yang sudah ada
        if nis in nis_set:
            duplicates_count += 1
            continue

        # Tambahkan ke set NIS baru untuk menghindari duplikasi dalam file upload itu sendiri
        nis_set.add(nis)
        
        new_row = {
            'ID_MURID': str(uuid.uuid4()),
            'Nama_Murid': str(row['Nama_Murid']).strip(),
            'Kelas': str(row['Kelas']).strip(),
            'NIS': nis,
            'Nama_Wali': str(row.get('Nama_Wali', '')).strip(), # Ambil jika ada, jika tidak, kosong
            'Kontak_Wali': str(row.get('Kontak_Wali', '')).strip(),
            'Foto_Murid': ''
        }
        new_students_list.append(new_row)

    if not new_students_list:
        if duplicates_count > 0:
            st.warning(f"Tidak ada murid baru ditambahkan. Ditemukan {duplicates_count} NIS yang sudah terdaftar.")
        else:
            st.error("Tidak ada data murid yang valid untuk ditambahkan.")
        return

    df_new_students = pd.DataFrame(new_students_list)
    
    # 4. Gabungkan dan Simpan
    df_combined = pd.concat([df_current_murid, df_new_students], ignore_index=True)
    
    if save_dataframes(df_combined, st.session_state.df_hafalan):
        st.success(f"✅ Berhasil mengunggah **{len(df_new_students)}** murid baru.")
        if duplicates_count > 0:
            st.warning(f"⚠️ {duplicates_count} murid dilewati karena NIS sudah terdaftar.")
        st.experimental_rerun()
