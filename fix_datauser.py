# Utilitas migrasi data warisan 2.1.2; tetap kompatibel dengan versi 2.2.0.
# hapus setelah digunakan

import json

USER_DATA_FILE = "datauser.json"  # ganti sesuai lokasi file kamu

def fix_user_data():
    try:
        with open(USER_DATA_FILE, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ File tidak ditemukan atau format JSON tidak valid.")
        return

    updated = False
    for uid, user in data.items():
        if "aktif" not in user:
            user["aktif"] = True
            updated = True
            print(f"✅ Menambahkan 'aktif': true ke user ID {uid}")

    if updated:
        with open(USER_DATA_FILE, "w") as file:
            json.dump(data, file, indent=4)
        print("🎉 Data berhasil diperbarui dan disimpan.")
    else:
        print("📦 Semua user sudah memiliki field 'aktif'. Tidak ada perubahan.")

if __name__ == "__main__":
    fix_user_data()
