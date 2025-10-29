import json
import pandas as pd
from datetime import datetime

# --- DATA MASTER JUZ AMMA ---

# Surah dalam Juz Amma (Nama Surah: Jumlah Ayat)
JUZ_AMMA_MAP = {
    "An-Naba'": 40, "An-Naziat": 46, "Abasa": 42, "At-Takwir": 29, 
    "Al-Infitar": 19, "Al-Mutaffifin": 36, "Al-Insyiqaq": 25, "Al-Buruj": 22, 
    "At-Tariq": 17, "Al-A'la": 19, "Al-Ghasyiyah": 26, "Al-Fajr": 30, 
    "Al-Balad": 20, "Asy-Syams": 15, "Al-Lail": 21, "Ad-Duha": 11, 
    "Al-Insyirah": 8, "At-Tin": 8, "Al-Alaq": 19, "Al-Qadr": 5, 
    "Al-Bayyinah": 8, "Az-Zalzalah": 8, "Al-Adiyat": 11, "Al-Qari'ah": 11, 
    "At-Takasur": 8, "Al-Asr": 3, "Al-Humazah": 9, "Al-Fil": 5, 
    "Quraisy": 4, "Al-Ma'un": 7, "Al-Kausar": 3, "Al-Kafirun": 6, 
    "An-Nasr": 3, "Al-Lahab": 5, "Al-Ikhlas": 4, "Al-Falaq": 5, 
    "An-Nas": 6
}

# Daftar nama surah yang berurutan
SURAH_NAMES = list(JUZ_AMMA_MAP.keys())

# Total Ayat dalam Juz Amma
TOTAL_AYAT_JUZ_AMMA = sum(JUZ_AMMA_MAP.values())

# --- FUNGSI PEMBANTU ---

def create_initial_data_structure():
    """Membuat struktur data inisial Status_Hafalan (semua 0: Belum Lulus)"""
    # Status: 0 = Belum, 1 = Lulus, 2 = Mengulang
    status_dict = {}
    for surah, total_ayat in JUZ_AMMA_MAP.items():
        status_dict[surah] = [0] * total_ayat
    return status_dict

def calculate_lulus_count(status_hafalan_json):
    """Menghitung total ayat yang sudah lulus (status 1) dari string JSON."""
    try:
        status_dict = json.loads(status_hafalan_json)
        total_lulus = 0
        for ayat_list in status_dict.values():
            total_lulus += ayat_list.count(1)
        return total_lulus
    except:
        return 0

# FUNGSI CSV LAMA (TIDAK DIGUNAKAN LAGI)
def initialize_database(db_file):
    pass

def save_data(df):
    pass
