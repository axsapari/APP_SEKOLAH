import pandas as pd

# Data master Surah Juz Amma (contoh)
JUZ_AMMA_MAP = {
    "An-Naba'": {'ayat_count': 40},
    "An-Nazi'at": {'ayat_count': 46},
    "Abasa": {'ayat_count': 42},
    "At-Takwir": {'ayat_count': 29},
    "Al-Infitar": {'ayat_count': 19},
    "Al-Mutaffifin": {'ayat_count': 36},
    "Al-Insyiqaq": {'ayat_count': 25},
    "Al-Buruj": {'ayat_count': 22},
    "At-Tariq": {'ayat_count': 17},
    "Al-A'la": {'ayat_count': 19},
    "Al-Gasyiyah": {'ayat_count': 26},
    "Al-Fajr": {'ayat_count': 30},
    "Al-Balad": {'ayat_count': 20},
    "Asy-Syams": {'ayat_count': 15},
    "Al-Lail": {'ayat_count': 21},
    "Ad-Duha": {'ayat_count': 11},
    "Al-Insyirah": {'ayat_count': 8},
    "At-Tin": {'ayat_count': 8},
    "Al-'Alaq": {'ayat_count': 19},
    "Al-Qadr": {'ayat_count': 5},
    "Al-Bayyinah": {'ayat_count': 8},
    "Az-Zalzalah": {'ayat_count': 8},
    "Al-'Adiyat": {'ayat_count': 11},
    "Al-Qari'ah": {'ayat_count': 11},
    "At-Takasur": {'ayat_count': 8},
    "Al-'Asr": {'ayat_count': 3},
    "Al-Humazah": {'ayat_count': 9},
    "Al-Fil": {'ayat_count': 5},
    "Quraisy": {'ayat_count': 4},
    "Al-Ma'un": {'ayat_count': 7},
    "Al-Kausar": {'ayat_count': 3},
    "Al-Kafirun": {'ayat_count': 6},
    "An-Nasr": {'ayat_count': 3},
    "Al-Lahab": {'ayat_count': 5},
    "Al-Ikhlas": {'ayat_count': 4},
    "Al-Falaq": {'ayat_count': 5},
    "An-Nas": {'ayat_count': 6}
}

SURAH_NAMES = list(JUZ_AMMA_MAP.keys())
TOTAL_AYAT_JUZ_AMMA = sum(data['ayat_count'] for data in JUZ_AMMA_MAP.values()) # Total: 548 ayat

# --- FUNGSI PEMBANTU ---

def calculate_lulus_count(df_hafalan):
    """
    Menghitung total jumlah ayat yang sudah LULUS, 
    mempertimbangkan rentang Ayat_Awal dan Ayat_Akhir.
    """
    if df_hafalan.empty:
        return 0
    
    # Filter hanya status 'LULUS'
    df_lulus = df_hafalan[df_hafalan['Status'] == 'LULUS'].copy()
    
    total_lulus = 0
    # Iterasi melalui setiap catatan hafalan yang LULUS
    for index, row in df_lulus.iterrows():
        # Hitung jumlah ayat dalam rentang
        count = int(row['Ayat_Akhir']) - int(row['Ayat_Awal']) + 1
        total_lulus += count
        
    return total_lulus
