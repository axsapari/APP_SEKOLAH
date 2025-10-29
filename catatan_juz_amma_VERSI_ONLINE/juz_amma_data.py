import pandas as pd
import streamlit as st

# --- Data Master Juz Amma (37 Surah) ---
JUZ_AMMA_MAP = {
    "An-Naba'": {"nomor": 78, "ayat_count": 40},
    "An-Nazi'at": {"nomor": 79, "ayat_count": 46},
    "'Abasa": {"nomor": 80, "ayat_count": 42},
    "At-Takwir": {"nomor": 81, "ayat_count": 29},
    "Al-Infithar": {"nomor": 82, "ayat_count": 19},
    "Al-Muthaffifin": {"nomor": 83, "ayat_count": 36},
    "Al-Insyiqaq": {"nomor": 84, "ayat_count": 25},
    "Al-Buruj": {"nomor": 85, "ayat_count": 22},
    "Ath-Thariq": {"nomor": 86, "ayat_count": 17},
    "Al-A'la": {"nomor": 87, "ayat_count": 19},
    "Al-Ghasyiyah": {"nomor": 88, "ayat_count": 26},
    "Al-Fajr": {"nomor": 89, "ayat_count": 30},
    "Al-Balad": {"nomor": 90, "ayat_count": 20},
    "Asy-Syams": {"nomor": 91, "ayat_count": 15},
    "Al-Lail": {"nomor": 92, "ayat_count": 21},
    "Adh-Dhuha": {"nomor": 93, "ayat_count": 11},
    "Al-Insyirah": {"nomor": 94, "ayat_count": 8},
    "At-Tin": {"nomor": 95, "ayat_count": 8},
    "Al-'Alaq": {"nomor": 96, "ayat_count": 19},
    "Al-Qadr": {"nomor": 97, "ayat_count": 5},
    "Al-Bayyinah": {"nomor": 98, "ayat_count": 8},
    "Az-Zalzalah": {"nomor": 99, "ayat_count": 8},
    "Al-'Adiyat": {"nomor": 100, "ayat_count": 11},
    "Al-Qari'ah": {"nomor": 101, "ayat_count": 11},
    "At-Takatsur": {"nomor": 102, "ayat_count": 8},
    "Al-'Ashr": {"nomor": 103, "ayat_count": 3},
    "Al-Humazah": {"nomor": 104, "ayat_count": 9},
    "Al-Fil": {"nomor": 105, "ayat_count": 5},
    "Quraisy": {"nomor": 106, "ayat_count": 4},
    "Al-Ma'un": {"nomor": 107, "ayat_count": 7},
    "Al-Kautsar": {"nomor": 108, "ayat_count": 3},
    "Al-Kafirun": {"nomor": 109, "ayat_count": 6},
    "An-Nashr": {"nomor": 110, "ayat_count": 3},
    "Al-Lahab": {"nomor": 111, "ayat_count": 5},
    "Al-Ikhlas": {"nomor": 112, "ayat_count": 4},
    "Al-Falaq": {"nomor": 113, "ayat_count": 5},
    "An-Nas": {"nomor": 114, "ayat_count": 6}
}

SURAH_NAMES = list(JUZ_AMMA_MAP.keys())
TOTAL_AYAT_JUZ_AMMA = sum(data['ayat_count'] for data in JUZ_AMMA_MAP.values())

def calculate_lulus_count(df_hafalan, student_id):
    """
    Menghitung jumlah Surah yang status 'Lulus' untuk murid tertentu.
    Jika ada beberapa entri untuk Surah yang sama, hanya dihitung jika 
    setidaknya satu entri memiliki status 'Lulus'.
    """
    if df_hafalan.empty:
        return 0
    
    df_m = df_hafalan[df_hafalan['ID_MURID'] == student_id].copy()
    
    # Filter hanya yang statusnya 'Lulus'
    df_lulus = df_m[df_m['Status'] == 'Lulus']
    
    # Hitung surah unik yang sudah lulus
    lulus_count = df_lulus['Surah'].nunique()
    
    return lulus_count
