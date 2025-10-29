import streamlit as st
import pandas as pd
import json
from datetime import datetime
import time

# Import data master dan fungsi pembantu dari file juz_amma_data.py
# PASTIKAN FILE juz_amma_data.py ADA DI FOLDER YANG SAMA
from juz_amma_data import JUZ_AMMA_MAP, SURAH_NAMES, TOTAL_AYAT_JUZ_AMMA, create_initial_data_structure, calculate_lulus_count

# --- KONFIGURASI APLIKASI ---
# ID Sheet tidak perlu di sini, akan diatur di Streamlit Secrets
st.set_page_config(
    page_title="Pencatatan Hafalan Juz Amma Online", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNGSI UTILITY KONEKSI GOOGLE SHEETS ---

# Gunakan cache untuk mengurangi pembacaan dari Google Sheets
@st.cache_data(ttl=300) # Data di-cache selama 5 menit (300 detik)
def get_all_students_from_gheets():
    """Mengambil semua data murid dari Google Sheets."""
    try:
        # Koneksi ke Google Sheets (nama koneksi di secrets.toml harus 'gsheets')
        conn = st.connection("gsheets", type="streamlit")
        
        # Baca data dari Sheet "Murid" (atau Sheet1)
        df = conn.read(worksheet="Murid", usecols=list(range(7)), ttl=5) 
        
        # Bersihkan data: ubah ID_Murid ke integer dan hapus baris kosong
        df = df.dropna(subset=['Nama_Murid', 'Kelas'])
        if df.empty:
            return pd.DataFrame(columns=['ID_Murid', 'Nama_Murid', 'NIS', 'Kelas', 'Status_Hafalan', 'Total_Ayat_Lulus', 'Update_Terakhir'])
        
        df['ID_Murid'] = pd.to_numeric(df['ID_Murid'], errors='coerce').fillna(0).astype(int)
        df.set_index('ID_Murid', inplace=True)
        return df

    except Exception as e:
        st.error(f"Gagal memuat data dari Google Sheets. Pastikan koneksi dan Secrets sudah diatur: {e}")
        return pd.DataFrame()

# Fungsi untuk menulis ke Google Sheets
def write_to_gheets(df):
    """Menulis seluruh DataFrame ke Google Sheets."""
    try:
        conn = st.connection("gsheets", type="streamlit")
        # Reset index agar ID_Murid kembali menjadi kolom
        conn.write(df.reset_index(), worksheet="Murid") 
        get_all_students_from_gheets.clear() # Kosongkan cache
        return True
    except Exception as e:
        st.error(f"Gagal menulis data ke Google Sheets: {e}")
        return False

def get_next_student_id(df):
    """Mencari ID Murid tertinggi + 1."""
    if df.empty:
        return 1001
    # max() digunakan pada index DataFrame (yaitu ID_Murid)
    return df.index.max() + 1 

# --- FUNGSI LOGIKA UTAMA (Diadaptasi untuk Google Sheets) ---

def add_new_student(df, name, kelas, nis=""):
    """Menambahkan murid baru ke DataFrame dan menyimpannya."""
    next_id = get_next_student_id(df)
    
    new_data = {
        'ID_Murid': next_id,
        'Nama_Murid': name,
        'NIS': nis, 
        'Kelas': kelas,
        'Status_Hafalan': json.dumps(create_initial_data_structure()), 
        'Total_Ayat_Lulus': 0,
        'Update_Terakhir': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Tambahkan ke DataFrame yang sudah ada
    new_df = pd.concat([df.reset_index(), pd.DataFrame([new_data])], ignore_index=True)
    new_df.set_index('ID_Murid', inplace=True)
    
    if write_to_gheets(new_df):
        st.success(f"Murid **{name}** (ID: {next_id}) berhasil ditambahkan ke kelas **{kelas}**.")
    else:
        st.error("Penambahan murid gagal.")

def update_hafalan_status_gheets(df, student_id, surah, start_ayat, end_ayat, status):
    """Memperbarui status hafalan di DataFrame dan menyimpannya ke Sheets."""
    
    try:
        student_row = df.loc[student_id].copy() # Ambil data murid
    except KeyError:
        st.error("Murid tidak ditemukan di database.")
        return

    # 1. Validasi Input dan Rentang Ayat
    max_ayat = JUZ_AMMA_MAP.get(surah)
    if not max_ayat or not (1 <= start_ayat <= max_ayat) or not (1 <= end_ayat <= max_ayat) or (start_ayat > end_ayat):
        st.error("Rentang ayat tidak valid.")
        return

    # 2. Muat status hafalan
    current_status_json = student_row['Status_Hafalan']
    status_dict = json.loads(current_status_json)
    ayat_list = status_dict.get(surah, [0] * max_ayat) # Pastikan list memiliki panjang yang benar
    
    # 3. Perbarui status ayat
    for i in range(start_ayat - 1, end_ayat):
        if i < len(ayat_list):
            ayat_list[i] = status
    status_dict[surah] = ayat_list
    
    # 4. Hitung ulang total lulus
    new_status_json = json.dumps(status_dict)
    new_total_lulus = calculate_lulus_count(new_status_json)

    # 5. Perbarui DataFrame lokal
    df.loc[student_id, 'Status_Hafalan'] = new_status_json
    df.loc[student_id, 'Total_Ayat_Lulus'] = new_total_lulus
    df.loc[student_id, 'Update_Terakhir'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 6. Simpan ke Google Sheets
    if write_to_gheets(df):
        st.success(f"Berhasil mencatat setoran **{surah}** ayat **{start_ayat} - {end_ayat}** dengan status {'LULUS' if status == 1 else 'MENGULANG'} di Cloud.")
    else:
        st.error("Pembaruan hafalan gagal disimpan ke Sheets.")

def delete_student_gheets(df, student_id, student_name):
    """Menghapus murid dari DataFrame dan menyimpannya ke Sheets."""
    initial_len = len(df)
    
    # Hapus murid dari DataFrame
    new_df = df[df.index != student_id].copy()
    
    if len(new_df) < initial_len:
        if write_to_gheets(new_df):
            st.success(f"Murid **{student_name}** (ID: {student_id}) berhasil dihapus permanen dari Google Sheets.")
        else:
            st.error("Gagal menghapus murid dari Sheets.")
    else:
        st.error(f"Gagal menghapus. Murid dengan ID {student_id} tidak ditemukan.")

def import_students_from_csv_gheets(df, uploaded_file):
    """Memproses file CSV yang diunggah dan menyimpannya ke Google Sheets."""
    try:
        new_students_df = pd.read_csv(uploaded_file, sep=';') 
        REQUIRED_COLS = ['Nama_Murid', 'Kelas']
        
        if not all(col in new_students_df.columns for col in REQUIRED_COLS):
            st.error(f"File CSV harus memiliki kolom wajib: {', '.join(REQUIRED_COLS)}. Kolom yang ditemukan: {new_students_df.columns.tolist()}")
            st.info("Pastikan CSV Anda menggunakan titik koma (;) sebagai pemisah.")
            return

        new_students_df = new_students_df.dropna(subset=REQUIRED_COLS)
        if new_students_df.empty:
            st.warning("Tidak ada data murid yang valid ditemukan di file CSV.")
            return

        current_max_id = get_next_student_id(df) - 1
        num_new_students = len(new_students_df)
        
        # 1. Buat ID Murid baru secara berurutan
        new_students_df['ID_Murid'] = range(int(current_max_id) + 1, int(current_max_id) + 1 + num_new_students)
        
        # 2. Siapkan data Status Hafalan
        new_students_df['Status_Hafalan'] = [json.dumps(create_initial_data_structure()) for _ in range(num_new_students)]
        new_students_df['Total_Ayat_Lulus'] = 0
        new_students_df['Update_Terakhir'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3. Gabungkan dengan data yang sudah ada
        combined_df = pd.concat([df.reset_index(), new_students_df], ignore_index=True)
        combined_df.set_index('ID_Murid', inplace=True)
        
        # 4. Simpan ke Google Sheets
        if write_to_gheets(combined_df):
            st.success(f"🎉 **{num_new_students}** murid berhasil diimpor ke Google Sheets!")
        else:
            st.error("Gagal menyimpan data impor ke Sheets.")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses file: {e}")
        st.warning("Pastikan file CSV memiliki format yang benar dan pemisah (;) yang sesuai.")


# --- APLIKASI STREAMLIT UTAMA ---

def main_app():
    # Ambil data terbaru dari Google Sheets (atau cache)
    df = get_all_students_from_gheets()
    
    if df.empty:
        st.warning("Database murid kosong atau gagal terhubung ke Google Sheets. Silakan cek koneksi internet dan **Kontrol Administrasi Guru** di sidebar untuk menambahkan murid.")
        df_for_sidebar = pd.DataFrame()
    else:
        df_for_sidebar = df
    
    st.title("📝 Aplikasi Pencatatan Hafalan Juz Amma Online")
    st.subheader("Didukung Google Sheets (Database Real-time)")
    
    # --- SIDEBAR (NAVIGASI & FILTER UTAMA) ---
    st.sidebar.title("Navigasi & Input Murid")
    
    menu = st.sidebar.radio("Pilih Tampilan", ["Pencatatan Hafalan", "Dashboard & Laporan"])

    # Mendapatkan daftar unik kelas
    kelas_list = ['Pilih Kelas'] + sorted(df_for_sidebar['Kelas'].unique().tolist())
    selected_class = st.sidebar.selectbox("1. Pilih Kelas", kelas_list)
    
    selected_student_id = None
    selected_student_name = ""
    selected_student_row = None

    if selected_class != 'Pilih Kelas' and not df_for_sidebar.empty:
        # Filter murid berdasarkan kelas
        class_df = df_for_sidebar[df_for_sidebar['Kelas'] == selected_class]
        
        # Buat dictionary nama:ID untuk pemilihan yang ramah pengguna
        student_map = {f"{row['Nama_Murid']} (ID: {row.name})": row.name 
                       for index, row in class_df.iterrows()} # row.name adalah index ID_Murid
        student_display_list = ['Pilih Murid'] + list(student_map.keys())
        
        selected_student_display = st.sidebar.selectbox("2. Pilih Murid", student_display_list)
        
        if selected_student_display != 'Pilih Murid':
            selected_student_id = student_map[selected_student_display]
            selected_student_name = selected_student_display.split(' (ID:')[0]
            try:
                selected_student_row = df_for_sidebar.loc[selected_student_id]
            except KeyError:
                st.error("Error: Data murid tidak ditemukan di DataFrame.")


    # --- TAMPILAN UTAMA ---

    if menu == "Pencatatan Hafalan":
        
        st.header(f"Setoran untuk: {selected_student_name if selected_student_name else '---'}")
        
        if selected_student_id and selected_student_row is not None:
            
            student_row = selected_student_row
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
                        
                        STATUS_LABELS = {
                            0: "⚫ Belum",
                            1: "🟢 Lulus",
                            2: "🟠 Mengulang"
                        }
                        
                        num_columns = 5
                        cols = st.columns(num_columns)
                        
                        for i, status in enumerate(ayat_list):
                            ayat_num = i + 1
                            col_index = i % num_columns
                            label = STATUS_LABELS.get(status, "❓ Error")
                            
                            cols[col_index].markdown(f"**Ayat {ayat_num}**: {label}")
                            
                    except Exception as e:
                        st.error(f"Gagal memuat riwayat hafalan: {e}")
                
                st.markdown("---") 

                col3, col4 = st.columns(2)
                with col3:
                    start_ayat = st.number_input("Dari Ayat Ke-", min_value=1, max_value=max_ayat_current, value=1, key="start_ayat")
                
                with col4:
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

                submitted = st.form_submit_button("✅ Simpan Catatan (Online)")

                if submitted:
                    # Update data melalui fungsi Google Sheets
                    update_hafalan_status_gheets(
                        df.copy(), # Kirim salinan DataFrame untuk operasi yang aman
                        selected_student_id, 
                        surah_to_setor, 
                        start_ayat, 
                        end_ayat, 
                        status_code
                    )
                    time.sleep(1) # Beri waktu untuk sinkronisasi
                    st.rerun() 
        else:
             st.warning("Mohon pilih Kelas dan Murid di sidebar untuk memulai pencatatan.")


    # --- TAMPILAN DASHBOARD & LAPORAN ---
    elif menu == "Dashboard & Laporan":
        st.header("📊 Dashboard & Laporan Progres Kelas (Real-time)")
        
        if selected_class != 'Pilih Kelas' and not df.empty:
            # LEADERBOARD / Papan Peringkat
            st.subheader(f"Papan Peringkat Kelas {selected_class}")
            
            leaderboard_df = df[df['Kelas'] == selected_class].sort_values(
                by='Total_Ayat_Lulus', 
                ascending=False
            ).reset_index(drop=False) # Keep ID_Murid as a column
            
            leaderboard_df.index = leaderboard_df.index + 1
            
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
                        
                        if total_ayat_surah > 0:
                            progress = lulus_count / total_ayat_surah
                            st.progress(progress, text=f"**{surah}** | Lulus: {lulus_count}/{total_ayat_surah} | Mengulang: {mengulang_count} | Belum: {belum_count}")
        else:
            st.info("Pilih Kelas di sidebar untuk melihat dashboard dan laporan.")

    # --- BAGIAN KONTROL GURU (DIPINDAHKAN KE BAWAH DI SIDEBAR) ---
    st.sidebar.markdown("---")
    st.sidebar.title("🛠️ Kontrol Administrasi Guru")
    st.sidebar.caption("Kelola data murid (tambah, impor, hapus).")

    # 1. TAMBAH MURID BARU (Manual)
    with st.sidebar.expander("➕ Tambah Murid Baru (Manual)"):
        with st.form("add_student_form"):
            new_name = st.text_input("Nama Lengkap Murid", max_chars=100)
            new_nis = st.text_input("Nomor Induk Siswa (NIS)", max_chars=20, value="")
            
            existing_classes = sorted(df['Kelas'].unique().tolist()) if not df.empty else []
            new_kelas = st.text_input("Kelas (Contoh: VII-A, VIII-B)", max_chars=10, value=existing_classes[0] if existing_classes else 'VII-A')
            
            add_submitted = st.form_submit_button("Simpan Murid Baru ke Sheets")
            
            if add_submitted:
                if new_name and new_kelas:
                    add_new_student(df.copy(), new_name, new_kelas, new_nis) 
                    time.sleep(1) 
                    st.rerun() 
                else:
                    st.error("Nama dan Kelas tidak boleh kosong.")
    
    # 2. IMPOR MASSAL DATA (CSV)
    with st.sidebar.expander("⬆️ Impor Massal Data (CSV)"):
        st.markdown("**Kolom wajib:** `Nama_Murid`, `Kelas`. Pemisah: `;`")
        st.markdown("Unggah file CSV Anda.")
        uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"], key="csv_uploader")
        
        if uploaded_file is not None:
            if st.button("Proses Impor Data ke Sheets"):
                import_students_from_csv_gheets(df.copy(), uploaded_file)
                time.sleep(1) 
                st.rerun() 
                
    # 3. HAPUS MURID BARU (Permanen)
    with st.sidebar.expander("🗑️ Hapus Murid"):
        st.warning("PERINGATAN: Penghapusan bersifat permanen dari Google Sheets.")
        
        delete_df = df 
        
        existing_classes_delete = sorted(delete_df['Kelas'].unique().tolist()) if not delete_df.empty else []
        delete_class_filter = st.selectbox(
            "Filter Berdasarkan Kelas",
            ['Semua Kelas'] + existing_classes_delete,
            key="delete_class_filter"
        )
        
        filtered_delete_df = delete_df
        if delete_class_filter != 'Semua Kelas':
            filtered_delete_df = delete_df[delete_df['Kelas'] == delete_class_filter]

        internal_delete_map = {}
        for row_id, row in filtered_delete_df.iterrows():
            internal_key = f"{row['Nama_Murid']} - Kelas: {row['Kelas']} |ID:{row_id}"
            internal_delete_map[internal_key] = row_id 

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
            
            start_of_internal_key = selected_display_string
            found_key = next((key for key in sorted_internal_keys if key.startswith(start_of_internal_key + ' |ID:')), None)
            
            if found_key:
                student_id_to_delete = internal_delete_map[found_key]
                student_name_to_delete = selected_display_string.split(' - Kelas:')[0] 

                st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (ID: {student_id_to_delete}) secara permanen dari Sheets?")
                
                if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
                    delete_student_gheets(df.copy(), student_id_to_delete, student_name_to_delete)
                    time.sleep(1) 
                    st.rerun()
            else:
                st.warning("Peringatan: Murid yang dipilih tidak dapat diidentifikasi. Coba filter ulang.")
                
    
if __name__ == "__main__":
    main_app()
