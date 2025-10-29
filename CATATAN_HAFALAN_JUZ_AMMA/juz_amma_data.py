import pandas as pd
import json
from datetime import datetime

# --- 1. DATA MASTER SURAH JUZ AMMA ---
# Dictionary berisi Surah dan jumlah ayatnya (untuk validasi dan inisiasi)
JUZ_AMMA_MAP = {
    "An-Naba'": 40, "An-Nazi'at": 46, "'Abasa": 42, "At-Takwir": 29, "Al-Infitar": 19,
    "Al-Mutaffifin": 36, "Al-Insyiqaq": 25, "Al-Buruj": 22, "At-Tariq": 17, "Al-A'la": 19,
    "Al-Gasyiyah": 26, "Al-Fajr": 30, "Al-Balad": 20, "Asy-Syams": 15, "Al-Lail": 21,
    "Ad-Duha": 11, "Al-Insyirah": 8, "At-Tin": 8, "Al-'Alaq": 19, "Al-Qadr": 5,
    "Al-Bayyinah": 8, "Az-Zalzalah": 8, "Al-'Adiyat": 11, "Al-Qari'ah": 11, "At-Takasur": 8,
    "Al-'Asr": 3, "Al-Humazah": 9, "Al-Fil": 5, "Quraisy": 4, "Al-Ma'un": 7,
    "Al-Kausar": 3, "Al-Kafirun": 6, "An-Nasr": 3, "Al-Lahab": 5, "Al-Ikhlas": 4,
    "Al-Falaq": 5, "An-Nas": 6
}
SURAH_NAMES = list(JUZ_AMMA_MAP.keys())
TOTAL_AYAT_JUZ_AMMA = sum(JUZ_AMMA_MAP.values())

# --- 2. FUNGSI PEMBANTU DATA ---

def create_initial_data_structure():
    """
    Membuat struktur data hafalan awal (list berisi 0 untuk setiap ayat).
    0 = Belum Dihafal/Setor
    1 = LULUS
    2 = Mengulang
    """
    initial_status = {}
    for surah, count in JUZ_AMMA_MAP.items():
        # Membuat list dengan panjang sesuai jumlah ayat, diisi dengan 0
        initial_status[surah] = [0] * count
    
    # Mengkonversi ke string JSON agar bisa disimpan dalam satu kolom Pandas/CSV
    return json.dumps(initial_status)

def initialize_database(filepath="data_hafalan.csv"):
    """
    Memeriksa apakah file database sudah ada. Jika belum, membuat file baru
    dengan beberapa data dummy dan struktur kolom yang benar.
    """
    try:
        # Mencoba membaca file
        df = pd.read_csv(filepath)
        print("Database sudah ada, menggunakan file yang sudah ada.")
        
        # Tambahkan kolom yang mungkin hilang jika file lama
        if 'Total_Ayat_Lulus' not in df.columns:
            df['Total_Ayat_Lulus'] = 0
        if 'Update_Terakhir' not in df.columns:
            df['Update_Terakhir'] = ""
            
        return df

    except FileNotFoundError:
        print("Database tidak ditemukan. Membuat file baru.")
        
        # Membuat data frame baru
        data = {
            'ID_Murid': [1001, 1002, 1003],
            'Nama_Murid': ['Ani Purnamasari', 'Budi Santoso', 'Citra Dewi'],
            'Kelas': ['VII-A', 'VII-A', 'VIII-B'],
            'Status_Hafalan': [create_initial_data_structure() for _ in range(3)],
            'Total_Ayat_Lulus': [0, 0, 0],
            'Update_Terakhir': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * 3
        }
        df = pd.DataFrame(data)
        
        # Simpan file CSV
        df.to_csv(filepath, index=False)
        return df

def calculate_lulus_count(status_json):
    """Menghitung total ayat yang LULUS (status = 1) dari JSON status hafalan."""
    try:
        status_dict = json.loads(status_json)
        total_lulus = 0
        for surah_list in status_dict.values():
            total_lulus += surah_list.count(1) # Hanya menghitung status LULUS (1)
        return total_lulus
    except:
        return 0
