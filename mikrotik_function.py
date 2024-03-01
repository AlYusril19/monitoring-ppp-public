from librouteros import connect

def get_down_users(connection):
    try:
        # Menggunakan fungsi '/ppp/secret/print' untuk mendapatkan semua pengguna
        secret_data = connection('/ppp/secret/print')
        active_data = connection('/ppp/active/print')

        secret_names = set(secret['name'] for secret in secret_data if secret.get('profile') not in {'expired', 'pribadi-home'})
        active_names = set(active['name'] for active in active_data)

        down_users = secret_names - active_names

        return list(down_users)
    except Exception as e:
        print(f"Error getting down users: {str(e)}")
        return []

def get_name_server(connection):
    try:
        # Mendapatkan data server dari /system/identity/print
        nama_server_data = connection('/system/identity/print')
        # Memeriksa apakah ada data server yang diterima
        if nama_server_data:
            for nama_s in nama_server_data:
                nama_server = nama_s['name']

            # Mengembalikan nilai nama_server jika ada
            return (nama_server)
        else:
            print("Data server tidak ditemukan.")
            return None
    
    except Exception as e:
        # Menangkap dan mencetak pesan kesalahan
        print(f"Gagal mendapatkan data server: {str(e)}")
        return None
