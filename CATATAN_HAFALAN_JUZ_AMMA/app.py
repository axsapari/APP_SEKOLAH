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
    
    # Generate ID baru
    new_id = df['ID_Murid'].max() + 1 if not df.empty else 1001
    
    # Siapkan data hafalan awal
    initial_status = create_initial_data_structure()
    
    # Buat baris baru
    new_row = pd.DataFrame([{
        'ID_Murid': new_id,
        'Nama_Murid': name,
        'NIS': nis if nis else None,
        'Kelas': kelas,
        'Status_Hafalan': json.dumps(initial_status), # Simpan sebagai string JSON
        'Total_Ayat_Lulus': 0,
        'Update_Terakhir': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    
    # Gabungkan ke DataFrame utama
    df_updated = pd.concat([df, new_row], ignore_index=True)
    
    # Simpan dan update state
    save_data(df_updated)
    st.success(f"✅ Murid **{name}** (ID: {new_id}) berhasil ditambahkan!")

def update_hafalan_status(student_id, surah_name, ayat_lulus):
    """Memperbarui status hafalan untuk surah tertentu dan murid tertentu."""
    df = st.session_state.df
    
    # Cari indeks murid
    idx = df[df['ID_Murid'] == student_id].index
    
    if not idx.empty:
        idx = idx[0]
        
        # Ambil dan parse Status_Hafalan
        status_hafalan_str = df.loc[idx, 'Status_Hafalan']
        status = json.loads(status_hafalan_str)
        
        # Perbarui status untuk surah yang dipilih
        if surah_name in status:
            # Pastikan ayat_lulus adalah list yang valid (seperti [1, 0, 1, ...])
            if len(ayat_lulus) == JUZ_AMMA_MAP[surah_name]:
                status[surah_name] = ayat_lulus
            else:
                st.error(f"Gagal: Jumlah ayat ({len(ayat_lulus)}) tidak cocok dengan total ayat Surah {surah_name} ({JUZ_AMMA_MAP[surah_name]}).")
                return # Hentikan jika validasi gagal

            # Hitung ulang total lulus (untuk efisiensi, hanya untuk surah ini)
            total_lulus_baru = calculate_lulus_count(status)
            
            # Simpan kembali status hafalan sebagai string JSON
            df.loc[idx, 'Status_Hafalan'] = json.dumps(status)
            df.loc[idx, 'Total_Ayat_Lulus'] = total_lulus_baru
            df.loc[idx, 'Update_Terakhir'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Simpan dan update state
            save_data(df)
            
            # Update success message
            st.session_state.last_update_success = f"✅ Catatan hafalan untuk **{df.loc[idx, 'Nama_Murid']}** di **{surah_name}** berhasil diperbarui! Total Lulus: {total_lulus_baru}/{TOTAL_AYAT_JUZ_AMMA}"
            
        else:
            st.error(f"Gagal: Surah {surah_name} tidak ditemukan dalam data master.")
    else:
        st.error(f"Gagal: Murid dengan ID {student_id} tidak ditemukan.")
        
def delete_student(df_original, student_id, student_name):
    """Menghapus baris murid dari DataFrame."""
    df = df_original.copy()
    
    # Filter DataFrame untuk mengecualikan murid yang akan dihapus
    df_updated = df[df['ID_Murid'] != student_id].copy()
    
    # Simpan dan update state
    save_data(df_updated)
    st.success(f"🗑️ Murid **{student_name}** (ID: {student_id}) berhasil dihapus permanen!")
    
    # Hapus state terkait murid yang dihapus
    # PERBAIKAN: Gunakan .pop() untuk menghapus key dengan aman
    st.session_state.pop('selected_student_id', None)
    st.session_state.pop('selected_surah', None)
    
    st.rerun()

# --- FUNGSI TAMPILAN (VIEW) UTAMA ---

def main_app():
    st.title("📝 Pencatatan Hafalan Juz Amma")
    st.subheader(f"Total Murid Terdaftar: **{len(st.session_state.df)}**")
    
    # Tampilkan pesan sukses terakhir jika ada
    if 'last_update_success' in st.session_state:
        st.success(st.session_state.last_update_success)
        del st.session_state.last_update_success # Hapus setelah ditampilkan

    # --- Bagian Input Catatan Hafalan ---
    st.header("1. Input Catatan Hafalan")
    
    col1, col2 = st.columns(2)
    
    df = st.session_state.df
    
    # 1. Pilih Murid
    student_options_map = {}
    if not df.empty:
        for index, row in df.iterrows():
            display_name = f"{row['Nama_Murid']} - Kelas: {row['Kelas']}"
            internal_key = f"{display_name} |ID:{row['ID_Murid']}"
            student_options_map[internal_key] = row['ID_Murid']

    sorted_internal_keys = sorted(student_options_map.keys())
    display_list = ['--- Pilih Murid ---'] + [key.rsplit(' |ID:', 1)[0] for key in sorted_internal_keys]
    
    # --- PERBAIKAN STATE: Lacak perubahan murid ---
    current_selected_student_id = st.session_state.get('selected_student_id')
    
    selected_display_string = col1.selectbox(
        "Pilih Murid", 
        display_list,
        key="student_select",
        index=0
    )
    
    selected_student_id = None
    if selected_display_string != '--- Pilih Murid ---':
        start_of_internal_key = selected_display_string
        found_key = next((key for key in sorted_internal_keys if key.startswith(start_of_internal_key + ' |ID:')), None)
        if found_key:
            selected_student_id = student_options_map[found_key]
    
    # Cek apakah murid berganti
    student_changed = current_selected_student_id != selected_student_id
    st.session_state.selected_student_id = selected_student_id

    # 2. Pilih Surah
    surah_list = ['--- Pilih Surah ---'] + SURAH_NAMES 
    
    # --- PERBAIKAN STATE: Lacak perubahan surah ---
    current_selected_surah = st.session_state.get('selected_surah', surah_list[0])
    
    selected_surah = col2.selectbox(
        "Pilih Surah", 
        surah_list,
        key="surah_select",
        index=surah_list.index(current_selected_surah) if current_selected_surah in surah_list else 0
    )

    # Cek apakah surah berganti
    surah_changed = current_selected_surah != selected_surah
    st.session_state.selected_surah = selected_surah

    # Dapatkan jumlah total ayat untuk surah yang dipilih
    total_ayat_surah = JUZ_AMMA_MAP.get(selected_surah, 0)
    
    # -----------------------------------------------------------
    # START: LOGIKA TAMPILAN DETAIL (PERBAIKAN)
    # -----------------------------------------------------------

    if selected_student_id and selected_surah != '--- Pilih Surah ---':
        
        # --- PERBAIKAN: Bagian Tampilan Detail (di luar form) ---
        st.markdown("---")
        st.subheader(f"Detail Hafalan untuk **{selected_surah}**")
        st.info(f"Surah **{selected_surah}** memiliki total **{total_ayat_surah}** ayat.")
        
        # Ambil data murid saat ini
        student_data = df[df['ID_Murid'] == selected_student_id].iloc[0]
        status_hafalan = json.loads(student_data['Status_Hafalan'])
        
        # Inisialisasi list status ayat (0/1)
        current_ayat_status = status_hafalan.get(selected_surah, [0] * total_ayat_surah)

        if len(current_ayat_status) != total_ayat_surah:
             st.warning(f"Peringatan: Data status ayat tidak valid untuk {selected_surah}. Meregenerasi status awal.")
             current_ayat_status = [0] * total_ayat_surah
        
        # --- PERBAIKAN: Form HANYA berisi input dan tombol ---
        with st.form(key='hafalan_form'):
            st.markdown("#### Status Hafalan Ayat (Centang = Lulus)")
            st.warning("Penting: Ubah status ayat di bawah ini, lalu tekan **Simpan Catatan Hafalan** untuk menyimpan perubahan.")
            
            cols_ayat = st.columns(min(total_ayat_surah, 10))
            new_ayat_status_values = [] # Penampung nilai baru
            
            for i in range(total_ayat_surah):
                # --- PERBAIKAN: Logika State Checkbox ---
                # Key checkbox dibuat sederhana dan di-reset per Surah/Murid
                checkbox_key = f"ayat_status_{i}"
                
                # Jika murid atau surah baru saja diganti,
                # ATAU jika state belum ada,
                # ATUR state checkbox berdasarkan data dari CSV (current_ayat_status).
                if student_changed or surah_changed or checkbox_key not in st.session_state:
                    st.session_state[checkbox_key] = current_ayat_status[i] == 1
                
                # Tampilkan checkbox
                with cols_ayat[i % 10]:
                    # Nilai checkbox (yang mungkin diubah pengguna) disimpan kembali ke session state
                    st.session_state[checkbox_key] = st.checkbox(
                        f"Ayat {i+1}",
                        value=st.session_state[checkbox_key], # State sekarang sudah sinkron
                        key=checkbox_key
                    )
                
                # Kumpulkan nilai 0 atau 1 dari state
                new_ayat_status_values.append(1 if st.session_state[checkbox_key] else 0)

            st.markdown("---")
            col_save, col_reset = st.columns([1, 4])
            
            # Tombol Simpan
            save_button = col_save.form_submit_button(
                label='💾 Simpan Catatan Hafalan', 
                type="primary",
                help="Klik untuk menyimpan status hafalan yang telah diubah."
            )
            
            # Logika Simpan
            if save_button:
                # Cek apakah ada perubahan
                current_bools = [x == 1 for x in current_ayat_status]
                new_bools = [x == 1 for x in new_ayat_status_values]
                
                if new_bools != current_bools:
                    update_hafalan_status(selected_student_id, selected_surah, new_ayat_status_values)
                    # Rerun untuk membersihkan form dan menampilkan pesan sukses
                    st.rerun() 
                else:
                    st.warning("Tidak ada perubahan status hafalan yang dideteksi.")

        # --- PERBAIKAN: Bagian Tampilan Ringkasan (di luar form) ---
        total_lulus_surah = sum(current_ayat_status) # Tampilkan data dari CSV (sebelum disimpan)
        if save_button and new_bools != current_bools: # Jika baru saja disimpan, update tampilan
             total_lulus_surah = sum(new_ayat_status_values)

        st.markdown(f"**Ringkasan:** Murid telah menyelesaikan **{total_lulus_surah}** dari **{total_ayat_surah}** ayat di Surah **{selected_surah}**.")
        st.markdown(f"**Update Data Murid Terakhir:** {student_data['Update_Terakhir']}")
    
    # --- Kondisi Tampilan Info (Tidak berubah) ---
    elif selected_student_id and selected_surah == '--- Pilih Surah ---':
        st.info("Silakan pilih Surah untuk melihat dan mencatat status hafalannya.")
    elif not selected_student_id and selected_surah != '--- Pilih Surah ---':
        st.info("Silakan pilih Murid dan Surah untuk melihat dan mencatat status hafalannya.")
    else:
        st.info("Silakan pilih Murid dan Surah di atas untuk memulai pencatatan.")

    # -----------------------------------------------------------
    # END: LOGIKA TAMPILAN DETAIL
    # -----------------------------------------------------------


    st.markdown("---")
    
    # --- Bagian Manajemen Data (Sidebar atau Bagian Bawah) ---
    st.sidebar.header("Manajemen Data")
    
    # Tab untuk Tambah Murid dan Hapus Murid
    tab_add, tab_delete, tab_summary = st.sidebar.tabs(["➕ Tambah Murid", "❌ Hapus Murid", "📊 Ringkasan"])

    with tab_add:
        st.subheader("Tambah Murid Baru")
        with st.form("add_student_form"):
            new_name = st.text_input("Nama Murid", key="new_student_name")
            new_kelas = st.text_input("Kelas", help="Contoh: VII A", key="new_student_kelas")
            new_nis = st.text_input("NIS (Opsional)", key="new_student_nis")
            
            submitted = st.form_submit_button("Tambah Murid")
            
            if submitted and new_name and new_kelas:
                add_new_student(new_name, new_kelas, new_nis)
                st.rerun()

    with tab_delete:
        st.subheader("Hapus Murid Permanen")
        
        if df.empty:
            st.warning("Tidak ada murid terdaftar untuk dihapus.")
        else:
            # Gunakan map dan list yang sama dengan di main app untuk konsistensi
            internal_delete_map = {
                f"{row['Nama_Murid']} - Kelas: {row['Kelas']} |ID:{row['ID_Murid']}": row['ID_Murid']
                for index, row in df.iterrows()
            }
            sorted_internal_keys = sorted(internal_delete_map.keys())
            
            display_list_delete = ['Pilih Murid yang Akan Dihapus'] + [\
                key.rsplit(' |ID:', 1)[0] for key in sorted_internal_keys\
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

                    st.error(f"Anda yakin ingin menghapus **{student_name_to_delete}** (ID: {student_id_to_delete}) secara permanen?")
                    
                    if st.button(f"✅ KONFIRMASI HAPUS {student_name_to_delete}", key="confirm_delete_button"):
                        delete_student(st.session_state.df.copy(), student_id_to_delete, student_name_to_delete)
                        st.rerun()
                else:
                    st.warning("Peringatan: Murid yang dipilih tidak dapat diidentifikasi. Coba filter ulang.")
                    
    with tab_summary:
        st.subheader("Ringkasan Hafalan")
        if not df.empty:
            # Sort data by total ayat lulus (descending)
            df_sorted = df.sort_values(by='Total_Ayat_Lulus', ascending=False).reset_index(drop=True)
            
            # Format untuk tampilan
            display_df = df_sorted[['Nama_Murid', 'Kelas', 'Total_Ayat_Lulus', 'Update_Terakhir']].copy()
            display_df.rename(columns={
                'Nama_Murid': 'Nama',
                'Kelas': 'Kelas',
                'Total_Ayat_Lulus': 'Total Ayat Lulus',
                'Update_Terakhir': 'Update Terakhir'
            }, inplace=True)
            
            st.dataframe(
                display_df, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Total Ayat Lulus": st.column_config.ProgressColumn(
                        "Total Ayat Lulus",
                        help=f"Total Ayat yang telah dihafal dari {TOTAL_AYAT_JUZ_AMMA} Ayat",
                        min_value=0,
                        max_value=TOTAL_AYAT_JUZ_AMMA,
                        format="%d / %d"
                    )
                }
            )
        else:
            st.info("Belum ada data murid.")


# Jalankan aplikasi utama
if __name__ == "__main__":
    # Inisialisasi database (file CSV kosong) jika belum ada
    if not os.path.exists(DB_FILE):
        initialize_database(DB_FILE)
        
    main_app()

