"""Sesi router yang sedang dipakai tiap user (hanya di memori, hilang saat bot restart)."""


class UserData:
    """Router aktif satu user: Server Saya yang dipilih atau Server Custom."""

    def __init__(self):
        self.ip_address = None
        self.router_username = None
        self.router_password = None
        self.interface = None
        self.server_name = None  # name of the saved server; None for Server Custom
        self.www_port = None  # web (www) port for traffic graphs; None = 80

user_data_dict = {}  # telegram user_id -> UserData