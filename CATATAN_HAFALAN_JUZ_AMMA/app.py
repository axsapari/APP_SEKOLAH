import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# Import data master dan fungsi pembantu dari file juz_amma_data.py
# PASTIKAN FILE juz_amma_data.py ADA DI FOLDER YANG SAMA
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, initialize_database, create_initial_data_structure, calculate_lulus_count

# --- KONFIGURASI APLIKASI ---
DB_FILE = "data_hafalan.csv" # Nama file database
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Memuat dan menyimpan data di Streamlit Session State agar tidak hilang saat interaksi
if 'df' not in st.session_state:
    st.session_state.df = initialize_database(DB_FILE)

# --- FUNGSI LOGIKA UTAMA ---

def save_data(df):
    """Menyimpan DataFrame ke file CSV (database) dan memperbarui session state."""
    df.to_csv(DB_FILE, index=False)
    st.session_state.df = df # Pastikan session state selalu diperbarui

def add_new_student(name, kelas, nis=""):
    """Menambahkan baris murid baru ke DataFrame."""
    df = st.session_state.df
    
    # 1. Tentukan ID Murid baru
    next_id = df['ID_Murid'].max() + 1 if not df.empty else 1001
    
    # 2. Buat data murid baru
    new_data = {
        'ID_Murid': next_id,
        'Nama_Murid': name,
        'NIS': nis, 
        'Kelas': kelas,
        'Status_Hafalan': create_initial_data_structure(), # Inisiasi status 0 untuk semua ayat
        'Total_Ayat_Lulus': 0,
        'Update_Terakhir': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 3. Tambahkan ke DataFrame
    new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    
    # 4. Simpan dan perbarui state
    save_data(new_df)
    st.success(f"Murid **{name}** (ID: {next_id}) berhasil ditambahkan ke kelas **{kelas}**.")

def import_students_from_csv(uploaded_file):
    """Memproses file CSV yang diunggah dan menggabungkannya ke database."""
    try:
        # PERBAIKAN: Menggunakan sep=';' untuk membaca CSV dengan pemisah titik koma
        new_students_df = pd.read_csv(uploaded_file, sep=';') 
        
        # Validasi kolom wajib 
        REQUIRED_COLS = ['Nama_Murid', 'Kelas']
        if not all(col in new_students_df.columns for col in REQUIRED_COLS):
            st.error(f"File CSV harus memiliki kolom wajib: {', '.join(REQUIRED_COLS)}. Kolom yang ditemukan: {new_students_df.columns.tolist()}")
            st.info("Pastikan CSV Anda menggunakan titik koma (;) sebagai pemisah.")
            return
        
        # Hapus baris kosong
        new_students_df = new_students_df.dropna(subset=REQUIRED_COLS)
        
        if new_students_df.empty:
            st.warning("Tidak ada data murid yang valid ditemukan di file CSV.")
            return

        df = st.session_state.df
        current_max_id = df['ID_Murid'].max() if not df.empty else 1000
        
        num_new_students = len(new_students_df)
        
        # 1. Buat ID Murid baru secara berurutan
        new_ids = range(int(current_max_id) + 1, int(current_max_id) + 1 + num_new_students)
        new_students_df['ID_Murid'] = new_ids
        
        # 2. Tambahkan kolom status hafalan inisial
        new_students_df['Status_Hafalan'] = [create_initial_data_structure() for _ in range(num_new_students)]
        new_students_df['Total_Ayat_Lulus'] = 0
        new_students_df['Update_Terakhir'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 3. Gabungkan dengan data yang sudah ada
        combined_df = pd.concat([df, new_students_df], ignore_index=True)
        
        # 4. Optional: Atur ulang urutan kolom jika NIS baru ditambahkan
        if 'NIS' in combined_df.columns and 'NIS' not in df.columns.tolist():
            cols = combined_df.columns.tolist()
            try:
                cols.remove('NIS')
                nama_murid_index = cols.index('Nama_Murid')
                cols.insert(nama_murid_index + 1, 'NIS')
            except ValueError:
                pass 
            combined_df = combined_df[cols]

        # 5. Simpan dan perbarui state
        save_data(combined_df)
        st.success(f"🎉 **{num_new_students}** murid berhasil diimpor!")
        st.info("Silakan cek di menu 'Pencatatan Hafalan' atau 'Dashboard' untuk melihat data baru.")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {e}")
        st.warning("Pastikan file Anda berformat CSV dan memiliki kolom 'Nama_Murid' dan 'Kelas', serta menggunakan titik koma (;) sebagai pemisah.")


def update_hafalan_status(df, student_id, surah, start_ayat, end_ayat, status):
    """
    Memperbarui status hafalan per ayat untuk murid tertentu.
    status: 1 (Lulus) atau 2 (Mengulang)
    """
    
    # 1. Validasi Input
    max_ayat = JUZ_AMMA_MAP.get(surah)
    if not max_ayat:
        st.error("Nama surah tidak valid.")
        return df

    if not (1 <= start_ayat <= max_ayat) or not (1 <= end_ayat <= max_ayat) or (start_ayat > end_ayat):
        st.error(f"Rentang ayat tidak valid. Surah {surah} hanya memiliki 1 sampai {max_ayat} ayat.")
        return df

    # 2. Ambil data murid
    idx_list = df[df['ID_Murid'] == student_id].index
    if idx_list.empty:
        st.error("Murid tidak ditemukan.")
        return df
        
    idx = idx_list[0]
    
    # 3. Muat status hafalan (dari JSON string ke Python dict)
    current_status_json = df.loc[idx, 'Status_Hafalan']
    try:
        status_dict = json.loads(current_status_json)
    except:
        st.error("Kesalahan format data Status_Hafalan.")
        return df

    # 4. Perbarui status ayat
    ayat_list = status_dict.get(surah, [])
    
    # Pandas/Python menggunakan 0-indexing
    for i in range(start_ayat - 1, end_ayat):
        if i < len(ayat_list):
            ayat_list[i] = status
    
    status_dict[surah] = ayat_list
    
    # 5. Simpan kembali (dari Python dict ke JSON string)
    new_status_json = json.dumps(status_dict)
    
    # 6. Perbarui DataFrame
    df.loc[idx, 'Status_Hafalan'] = new_status_json
    df.loc[idx, 'Total_Ayat_Lulus'] = calculate_lulus_count(new_status_json)
    df.loc[idx, 'Update_Terakhir'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    save_data(df) # Simpan ke CSV dan perbarui session state
    st.success(f"Berhasil mencatat setoran **{surah}** ayat **{start_ayat} - {end_ayat}** dengan status {'LULUS' if status == 1 else 'MENGULANG'}.")
    return df

def delete_student(df, student_id, student_name):
    """Menghapus murid berdasarkan ID dari DataFrame."""
    initial_len = len(df)
    
    # Filter out the student to be deleted
    new_df = df[df['ID_Murid'] != student_id].copy()
    
    if len(new_df) < initial_len:
        save_data(new_df)
        st.success(f"Murid **{student_name}** (ID: {student_id}) berhasil dihapus dari database.")
    else:
        st.error(f"Gagal menghapus. Murid dengan ID {student_id} tidak ditemukan.")
    return new_df


# --- APLIKASI STREAMLIT UTAMA ---

def main_app():
    df = st.session_state.df 
    
    st.title("📝 Aplikasi Pencatatan Hafalan Juz Amma")
    st.subheader("Hanya untuk Guru: Input Setoran Ayat")
    
    # --- SIDEBAR (NAVIGASI & FILTER UTAMA) ---
    st.sidebar.title("Navigasi & Input Murid")
    
    menu = st.sidebar.radio("Pilih Tampilan", ["Pencatatan Hafalan", "Dashboard & Laporan"])

    # Mendapatkan daftar unik kelas
    kelas_list = ['Pilih Kelas'] + sorted(df['Kelas'].unique().tolist())
    selected_class = st.sidebar.selectbox("1. Pilih Kelas", kelas_list)
    
    selected_student_id = None
    selected_student_name = ""
    selected_student_row = None

    if selected_class != 'Pilih Kelas':
        # Filter murid berdasarkan kelas
        class_df = df[df['Kelas'] == selected_class]
        
        # Buat dictionary nama:ID untuk pemilihan yang ramah pengguna (ID tetap terlihat di sini untuk keamanan data)
        student_map = {f"{row['Nama_Murid']} (ID: {row['ID_Murid']})": row['ID_Murid'] 
                       for index, row in class_df.iterrows()}
        student_display_list = ['Pilih Murid'] + list(student_map.keys())
        
        selected_student_display = st.sidebar.selectbox("2. Pilih Murid", student_display_list)
        
        if selected_student_display != 'Pilih Murid':
            selected_student_id = student_map[selected_student_display]
            selected_student_name = selected_student_display.split(' (ID:')[0]
            selected_student_row = df[df['ID_Murid'] == selected_student_id].iloc[0]


    # --- TAMPILAN UTAMA ---

    if menu == "Pencatatan Hafalan":
        
        st.header(f"Setoran untuk: {selected_student_name if selected_student_name else '---'}")
        
        if selected_student_id:
            # Tampilkan Ringkasan Progres Murid yang dipilih
            student_row = selected_student_row
            
            # Persentase Lulus
            progress_percent = int((student_row['Total_Ayat_Lulus'] / TOTAL_AYAT_JUZ_AMMA) * 100)
            
            st.info(f"""
            **Total Ayat Lulus:** {student_row['Total_Ayat_Lulus']} dari {TOTAL_AYAT_JUZ_AMMA} ayat. 
            **Progres:** {progress_percent}%
            **Terakhir Diperbarui:** {student_row['Update_Terakhir']}
            """)

            st.markdown("---")
            st.subheader("Formulir Pencatatan (Per Ayat)")

            # FORMULIR INPUT GURU
            with st.form("setoran_form"):
                
                col_surah, col_ayat_info = st.columns([3, 1])
                
                with col_surah:
                    surah_to_setor = st.selectbox("Surah yang Disetorkan", SURAH_NAMES, key="surah_select")
                
                max_ayat_current = JUZ_AMMA_MAP.get(surah_to_setor, 1)

                with col_ayat_info:
                    st.caption(f"Jumlah Ayat: **{max_ayat_current}**")
                
                
                # --- TAMPILAN RIWAYAT STATUS AYAT ---
                if selected_student_row is not None:
                    try:
                        status_dict = json.loads(selected_student_row['Status_Hafalan'])
                        ayat_list = status_dict.get(surah_to_setor, [])
                        
                        st.markdown(f"**Riwayat Status Ayat Surah {surah_to_setor}:**")
                        
                        # Definisikan warna dan label status
                        STATUS_LABELS = {
                            0: "⚫ Belum",
                            1: "🟢 Lulus",
                            2: "🟠 Mengulang"
                        }
                        
                        # Tampilkan status dalam 5 kolom
                        num_columns = 5
                        cols = st.columns(num_columns)
                        
                        for i, status in enumerate(ayat_list):
                            ayat_num = i + 1
                            col_index = i % num_columns
                            label = STATUS_LABELS.get(status, "❓ Error")
                            
                            cols[col_index].markdown(f"**Ayat {ayat_num}**: {label}")
                            
                    except Exception as e:
                        st.error(f"Gagal memuat riwayat hafalan: {e}")
                
                st.markdown("---") # Garis pemisah antara riwayat dan input baru

                col3, col4 = st.columns(2)
                with col3:
                    start_ayat = st.number_input("Dari Ayat Ke-", min_value=1, max_value=max_ayat_current, value=1, key="start_ayat")
                
                with col4:
                    # Pastikan nilai default end_ayat minimal sama dengan start_ayat
                    default_end = min(max_ayat_current, max(start_ayat, st.session_state.get('end_ayat_val', start_ayat)))
                    end_ayat = st.number_input("Sampai Ayat Ke-", min_value=start_ayat, max_value=max_ayat_current, value=default_end, key="end_ayat")
                    st.session_state.end_ayat_val = end_ayat 

                setoran_status = st.radio(
                    "Hasil Setoran:",
                    options=["Lulus", "Mengulang"],
                    index=0, 
                    horizontal=True
                )
                
                status_code = 1 if setoran_status == "Lulus" else 2

                submitted = st.form_submit_button("✅ Simpan Catatan")

                if submitted:
                    # Update data melalui fungsi
                    update_hafalan_status(
                        st.session_state.df.copy(), 
                        selected_student_id, 
                        surah_to_setor, 
                        start_ayat, 
                        end_ayat, 
                        status_code
                    )
                    st.rerun() 
        else:
             st.warning("Mohon pilih Kelas dan Murid di sidebar untuk memulai pencatatan.")


    # --- TAMPILAN DASHBOARD & LAPORAN ---
    elif menu == "Dashboard & Laporan":
        st.header("📊 Dashboard & Laporan Progres Kelas")
        
        if selected_class != 'Pilih Kelas':
            # LEADERBOARD / Papan Peringkat
            st.subheader(f"Papan Peringkat Kelas {selected_class}")
            
            # Ambil data terbaru dari session state
            df_current = st.session_state.df
            
            # Sortir data berdasarkan Total_Ayat_Lulus
            leaderboard_df = df_current[df_current['Kelas'] == selected_class].sort_values(
                by='Total_Ayat_Lulus', 
                ascending=False
            ).reset_index(drop=True)
            
            leaderboard_df.index = leaderboard_df.index + 1
            
            # Tampilkan kolom yang relevan
            display_cols = ['Nama_Murid']
            if 'NIS' in leaderboard_df.columns:
                display_cols.append('NIS')
            display_cols.extend(['Kelas', 'Total_Ayat_Lulus', 'Update_Terakhir', 'ID_Murid'])
            
            column_mapping = {
                'Nama_Murid': 'Murid',
                'Total_Ayat_Lulus': 'Total Ayat Lulus',
                'Update_Terakhir': 'Update Terakhir',
                'ID_Murid': 'ID'
            }
            if 'NIS' in leaderboard_df.columns:
                column_mapping['NIS'] = 'NIS'

            st.dataframe(
                leaderboard_df[display_cols].rename(columns=column_mapping),
                use_container_width=True
            )
            
            st.markdown("---")
            
            # PROGRESS DETAIL INDIVIDU 
            st.subheader("Detail Progres Murid Per Surah")
            
            for index, row in leaderboard_df.iterrows():
                with st.expander(f"⭐ {row['Nama_Murid']} - Total Lulus: {row['Total_Ayat_Lulus']} Ayat"):
                    status_dict = json.loads(row['Status_Hafalan'])
                    
                    for surah, ayat_list in status_dict.items():
                        total_ayat_surah = JUZ_AMMA_MAP[surah]
                        lulus_count = ayat_list.count(1)
                        mengulang_count = ayat_list.count(2)
                        belum_count = total_ayat_surah - lulus_count - mengulang_count
                        
                        # Tampilkan progres bar surah
                        if total_ayat_surah > 0:
                            progress = lulus_count / total_ayat_surah
                            st.progress(progress, text=f"**{surah}** | Lulus: {lulus_count}/{total_ayat_surah} | Mengulang: {mengulang_count} | Belum: {belum_count}")
        else:
            st.info("Pilih Kelas di sidebar untuk melihat dashboard dan laporan.")

    # --- BAGIAN KONTROL GURU (DIPINDAHKAN KE BAWAH DI SIDEBAR) ---
    st.sidebar.markdown("---")
    st.sidebar.title("🛠️ Kontrol Administrasi Guru")
    st.sidebar.caption("Gunakan bagian ini untuk mengelola data murid (tambah, impor, hapus).")

    # 1. TAMBAH MURID BARU (Manual)
    with st.sidebar.expander("➕ Tambah Murid Baru (Manual)"):
        with st.form("add_student_form"):
            new_name = st.text_input("Nama Lengkap Murid", max_chars=100)
            new_nis = st.text_input("Nomor Induk Siswa (NIS)", max_chars=20, value="")
            
            existing_classes = sorted(df['Kelas'].unique().tolist()) if not df.empty else []
            new_kelas = st.text_input("Kelas (Contoh: VII-A, VIII-B)", max_chars=10, value=existing_classes[0] if existing_classes else 'VII-A')
            
            add_submitted = st.form_submit_button("Simpan Murid Baru")
            
            if add_submitted:
                if new_name and new_kelas:
                    add_new_student(new_name, new_kelas, new_nis) 
                    st.rerun() # Menggunakan st.rerun()
                else:
                    st.error("Nama dan Kelas tidak boleh kosong.")
    
    # 2. IMPOR MASSAL DATA (CSV)
    with st.sidebar.expander("⬆️ Impor Massal Data (CSV)"):
        st.markdown("**Kolom wajib:** `Nama_Murid`, `Kelas`.")
        st.markdown("**Kolom tambahan opsional:** `NIS` (Nomor Induk Siswa).")
        st.markdown("Unggah file CSV Anda.")
        uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"], key="csv_uploader")
        
        if uploaded_file is not None:
            if st.button("Proses Impor Data"):
                import_students_from_csv(uploaded_file)
                st.rerun() # Menggunakan st.rerun()
                
    # 3. HAPUS MURID BARU (Permanen)
    with st.sidebar.expander("🗑️ Hapus Murid"):
        st.warning("PERINGATAN: Penghapusan bersifat permanen dan tidak dapat dibatalkan.")
        
        delete_df = st.session_state.df # Get current state of DF
        
        # --- Class Filter for Deletion ---
        existing_classes_delete = sorted(delete_df['Kelas'].unique().tolist()) if not delete_df.empty else []
        delete_class_filter = st.selectbox(
            "Filter Berdasarkan Kelas",
            ['Semua Kelas'] + existing_classes_delete,
            key="delete_class_filter"
        )
        
        # Filter Data
        filtered_delete_df = delete_df
        if delete_class_filter != 'Semua Kelas':
            # Gunakan .copy() untuk menghindari SettingWithCopyWarning
            filtered_delete_df = delete_df[delete_df['Kelas'] == delete_class_filter].copy()

        # Create Map (Display String -> ID). ID is NOT visible in the string, using Name - Kelas instead.
        
        internal_delete_map = {}
        for index, row in filtered_delete_df.iterrows():
            # Create a robust internal key including ID for uniqueness
            internal_key = f"{row['Nama_Murid']} - Kelas: {row['Kelas']} |ID:{row['ID_Murid']}"
            internal_delete_map[internal_key] = row['ID_Murid']

        # List for display in selectbox (User sees this - NO ID)
        # Sort the keys first (by name-class), then strip the internal ID tag for display.
        sorted_internal_keys = sorted(internal_delete_map.keys())
        display_list_delete = ['Pilih Murid yang Akan Dihapus'] + [
            key.rsplit(' |ID:', 1)[0] for key in sorted_internal_keys
        ]
        
        selected_display_string = st.selectbox(
            "Pilih Murid yang Akan Dihapus", 
            display_list_delete,
            key="delete_student_select"
        )
        
        student_id_to_delete = None
        student_name_to_delete = None

        if selected_display_string != 'Pilih Murid yang Akan Dihapus':
            
            # Reconstruct the expected start of the internal key (Name - Kelas: [Kelas])
            start_of_internal_key = selected_display_string
            
            # Find the full unique internal key from the sorted list
            # Cari kunci internal yang dimulai dengan string yang dipilih + tag |ID: 
            found_key = next((key for key in sorted_internal_keys if key.startswith(start_of_internal_key + ' |ID:')), None)
            
            if found_key:
                student_id_to_delete = internal_delete_map[found_key]
                # Name is the part before " - Kelas:"
                student_name_to_delete = selected_display_string.split(' - Kelas:')[0] 

                # Confirmation logic using the extracted details
                st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (ID: {student_id_to_delete}) secara permanen?")
                
                # Confirmation button
                if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
                    delete_student(st.session_state.df.copy(), student_id_to_delete, student_name_to_delete)
                    st.rerun()
            else:
                st.warning("Peringatan: Murid yang dipilih tidak dapat diidentifikasi. Coba filter ulang.")
                
    
    # Jalankan aplikasi utama
if __name__ == "__main__":
    # Inisialisasi database (file CSV kosong) jika belum ada
    if not os.path.exists(DB_FILE):
        initialize_database(DB_FILE)
    
    main_app()
