# Data master surah-surah Juz Amma (Surah 78 - 114)
JUZ_AMMA_MAP = {
    "An-Naba'": {"surah_number": 78, "ayat_count": 40},
    "An-Nazi'at": {"surah_number": 79, "ayat_count": 46},
    "'Abasa": {"surah_number": 80, "ayat_count": 42},
    "At-Takwir": {"surah_number": 81, "ayat_count": 29},
    "Al-Infitar": {"surah_number": 82, "ayat_count": 19},
    "Al-Mutaffifin": {"surah_number": 83, "ayat_count": 36},
    "Al-Insyiqaq": {"surah_number": 84, "ayat_count": 25},
    "Al-Buruj": {"surah_number": 85, "ayat_count": 22},
    "At-Tariq": {"surah_number": 86, "ayat_count": 17},
    "Al-A'la": {"surah_number": 87, "ayat_count": 19},
    "Al-Gasyiyah": {"surah_number": 88, "ayat_count": 26},
    "Al-Fajr": {"surah_number": 89, "ayat_count": 30},
    "Al-Balad": {"surah_number": 90, "ayat_count": 20},
    "Asy-Syams": {"surah_number": 91, "ayat_count": 15},
    "Al-Lail": {"surah_number": 92, "ayat_count": 21},
    "Ad-Duha": {"surah_number": 93, "ayat_count": 11},
    "Al-Insyirah": {"surah_number": 94, "ayat_count": 8},
    "At-Tin": {"surah_number": 95, "ayat_count": 8},
    "Al-'Alaq": {"surah_number": 96, "ayat_count": 19},
    "Al-Qadr": {"surah_number": 97, "ayat_count": 5},
    "Al-Bayyinah": {"surah_number": 98, "ayat_count": 8},
    "Az-Zalzalah": {"surah_number": 99, "ayat_count": 8},
    "Al-'Adiyat": {"surah_number": 100, "ayat_count": 11},
    "Al-Qari'ah": {"surah_number": 101, "ayat_count": 11},
    "At-Takasur": {"surah_number": 102, "ayat_count": 8},
    "Al-'Asr": {"surah_number": 103, "ayat_count": 3},
    "Al-Humazah": {"surah_number": 104, "ayat_count": 9},
    "Al-Fil": {"surah_number": 105, "ayat_count": 5},
    "Quraisy": {"surah_number": 106, "ayat_count": 4},
    "Al-Ma'un": {"surah_number": 107, "ayat_count": 7},
    "Al-Kausar": {"surah_number": 108, "ayat_count": 3},
    "Al-Kafirun": {"surah_number": 109, "ayat_count": 6},
    "An-Nasr": {"surah_number": 110, "ayat_count": 3},
    "Al-Lahab": {"surah_number": 111, "ayat_count": 5},
    "Al-Ikhlas": {"surah_number": 112, "ayat_count": 4},
    "Al-Falaq": {"surah_number": 113, "ayat_count": 5},
    "An-Nas": {"surah_number": 114, "ayat_count": 6},
}

# Daftar nama surah yang berurutan
SURAH_NAMES = list(JUZ_AMMA_MAP.keys())

# Hitung total ayat Juz Amma
TOTAL_AYAT_JUZ_AMMA = sum(data['ayat_count'] for data in JUZ_AMMA_MAP.values())

def calculate_lulus_count(df_hafalan, student_id):
    """Menghitung jumlah surah yang statusnya 'Lulus' untuk seorang murid."""
    if df_hafalan.empty:
        return 0
        
    df_student = df_hafalan[df_hafalan['ID_MURID'] == student_id]
    if df_student.empty:
        return 0

    lulus_count = df_student[df_student['Status'] == 'Lulus']['Surah'].nunique()
    return lulus_count

# Catatan: Fungsi initialize_database, create_initial_data_structure, dll.
# yang berhubungan dengan I/O database (CSV) dipindahkan ke student_management.py
# agar kode utama lebih fokus pada tampilan aplikasi.
