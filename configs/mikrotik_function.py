# Mencari User PPPOE Down
def get_down_users(connection):
    try:
        # Menggunakan fungsi '/ppp/secret/print' untuk mendapatkan semua pengguna
        secret_data = connection('/ppp/secret/print')
        active_data = connection('/ppp/active/print')

        secret_names = {secret['name']: secret['last-logged-out'] for secret in secret_data if secret.get('profile') not in {'expired', 'pribadi-home'}}
        active_names = {active['name']: active['uptime'] for active in active_data}

        down_users = []

        # Mencari pengguna yang terdaftar tetapi tidak aktif
        for name, last_logged_out in secret_names.items():
            if name not in active_names:
                down_users.append((name, last_logged_out))

        return down_users
    except Exception as e:
        print(f"Error getting down users: {str(e)}")
        return []

# Mencari nama Server
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
    
# Mengambil Data Traffic Interface
def get_interfaces(connection):
    try:
        # Mendapatkan data server dari /system/identity/print
        interface_list = connection('/interface/print')
        # Memeriksa apakah ada data server yang diterima
        if interface_list:
            return [item["name"] for item in interface_list if item.get("name")]
        print("Data interface tidak ditemukan.")
        return []
    except Exception as e:
        print(f"Gagal mendapatkan data interface: {str(e)}")
        return []


def get_graphing_interfaces(connection):
    """Return only interfaces enabled in RouterOS Tools > Graphing.

    An enabled ``interface=all`` entry deliberately expands to all RouterOS
    interfaces. Without that entry, only explicitly configured graphing
    interfaces are offered to the user.
    """
    try:
        graphing = connection('/tool/graphing/interface/print')
        enabled = [item for item in graphing
                   if str(item.get('disabled', False)).lower() not in {'true', 'yes', '1'}]
        configured = [str(item.get('interface', '')) for item in enabled]
        if 'all' in configured:
            return get_interfaces(connection)
        return [name for name in configured if name and name != 'all']
    except Exception as exc:
        print(f"Gagal mengambil konfigurasi graphing: {exc}")
        return []
# Compatibility for integrations that imported the old singular function.
get_interface = get_interfaces
