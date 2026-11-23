"""RouterOS helpers: connect, PPPoE status, interfaces, and friendly connection errors."""
import platform
import re
import socket
import subprocess

from librouteros import connect

from configs.send_message import escape_md


class RouterError(Exception):
    """Router could not be reached or answered with an error; `kind` says why."""

    def __init__(self, kind, detail=""):
        super().__init__(detail or kind)
        self.kind = kind
        self.detail = detail


def classify_router_error(exc):
    """Map a connect/API exception to login, timeout, refused, host, offline or other."""
    if isinstance(exc, RouterError):
        return exc.kind
    text = str(exc).lower()
    name = type(exc).__name__
    if name in {"TrapError", "MultiTrapError", "FatalError"} and (
            "password" in text or "log in" in text or "login" in text or "not allowed" in text):
        return "login"
    if isinstance(exc, socket.gaierror) or "name or service not known" in text or "getaddrinfo" in text:
        return "host"
    if isinstance(exc, (socket.timeout, TimeoutError)) or "timed out" in text or "timeout" in text:
        return "timeout"
    if isinstance(exc, ConnectionRefusedError) or "refused" in text:
        return "refused"
    if name == "ConnectionClosed" or isinstance(exc, OSError):
        return "offline"
    if name in {"TrapError", "MultiTrapError", "FatalError"}:
        return "login"
    return "other"


DEFAULT_API_PORT = 8728  # RouterOS protocol default (IP > Services > api)
DEFAULT_WWW_PORT = 80  # RouterOS protocol default (IP > Services > www)
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-:]*$")


def split_host_port(address, default_port=DEFAULT_API_PORT):
    """'host', 'host:port' or '[ipv6]:port' -> (host, port); ValueError on a bad port."""
    text = str(address or "").strip()
    if text.startswith("[") and "]" in text:
        host, _, rest = text[1:].partition("]")
        port_text = rest[1:] if rest.startswith(":") else ""
    elif text.count(":") == 1:
        host, port_text = text.split(":")
    else:
        host, port_text = text, ""  # plain host, or a bare IPv6 address
    if not port_text:
        return host, default_port
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise ValueError("Port harus angka 1-65535, contoh `router.ddns.net:8728`.")
    return host, int(port_text)


def validate_address(address):
    """Pesan error bila alamat router tidak valid, None bila valid."""
    try:
        host, _ = split_host_port(address)
    except ValueError as exc:
        return str(exc)
    if not host or not _HOST_RE.match(host):
        return "Alamat tidak valid. Contoh: `103.10.10.1`, `router.ddns.net`, atau `router.ddns.net:8000`."
    return None


def ping_host(host):
    """One ping: True = replied, False = no reply, None = ping not available here."""
    if not host or not _HOST_RE.match(host):
        return False
    windows = platform.system().lower() == "windows"
    command = ["ping", "-n", "1", "-w", "2000", host] if windows else ["ping", "-c", "1", "-W", "2", host]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=6)
    except (OSError, subprocess.SubprocessError):
        return None
    # "TTL=" only appears in a real echo reply ("Destination host unreachable" exits 0 on Windows).
    return result.returncode == 0 and "ttl=" in (result.stdout or "").lower()


_ERROR_TEXTS = {
    "login": ("🔐 Login ke *{name}* gagal: username atau password RouterOS salah, "
              "atau akun tidak punya izin API. (IP dan port sudah benar karena router menjawab.)"),
    "timeout": ("🔴 Server *{name}* tidak merespons (waktu habis). Kemungkinan router mati, listrik/internet "
                "di lokasi putus, IP berubah, atau port API salah."),
    "refused": "🚫 Server *{name}* menolak koneksi API pada port *{port}*.",
    "host": "❓ Alamat *{name}* tidak dikenal. Periksa kembali IP atau hostname/DDNS.",
    "offline": ("🔴 Koneksi ke server *{name}* terputus. Kemungkinan router mati atau jaringan "
                "di lokasi bermasalah."),
    "other": "⚠️ Server *{name}* tidak dapat dihubungi saat ini.",
}

_PORT_HINT = ("Kemungkinan masalah di *port API {port}*: service *api* (IP > Services) mati, port-nya diganti, "
              "belum di-NAT/forward, atau diblokir firewall. Bila port API bukan 8728, tulis alamat dengan port, "
              "contoh `{host}:8000`.")


def diagnose_address(kind, address):
    """Ping the router to tell 'wrong IP / router down' from 'wrong port' (Markdown, or '')."""
    if kind not in {"timeout", "refused", "offline", "other"} or not address:
        return ""
    try:
        host, port = split_host_port(address)
    except ValueError:
        return ""
    hint = _PORT_HINT.format(port=port, host=escape_md(host))
    if kind == "refused":
        # The router itself answered "no", so the address is right.
        return f"📶 Router terjangkau, jadi IP/host sudah benar. {hint}"
    replied = ping_host(host)
    if replied:
        return f"📶 *{escape_md(host)}* membalas ping, jadi IP/host benar dan router hidup. {hint}"
    if replied is False:
        return (f"📵 *{escape_md(host)}* juga tidak membalas ping: kemungkinan router mati, internet/listrik di "
                "lokasi putus, atau IP/host salah. (Abaikan bila ping memang diblokir firewall router.)")
    return ""


def router_error_text(exc, name, address=None):
    """Pesan ramah (Markdown) untuk kegagalan koneksi router, plus diagnosa ping bila `address` diberikan."""
    kind = classify_router_error(exc)
    try:
        port = split_host_port(address)[1] if address else DEFAULT_API_PORT
    except ValueError:
        port = DEFAULT_API_PORT
    text = _ERROR_TEXTS[kind].format(name=escape_md(name or "-"), port=port)
    diagnosis = diagnose_address(kind, address)
    return f"{text}\n{diagnosis}" if diagnosis else text


def connect_router(address, username, password):
    """Connect + login to RouterOS at 'host' or 'host:port'; raise RouterError on failure."""
    try:
        host, port = split_host_port(address)
    except ValueError as exc:
        raise RouterError("host", str(exc)) from exc
    try:
        return connect(username=username, password=password, host=host, port=port)
    except Exception as exc:
        raise RouterError(classify_router_error(exc), str(exc)) from exc


def graph_url(address, interface, www_port=None):
    """URL grafik harian Tools > Graphing; port API di alamat diabaikan, port web dari pengaturan server."""
    host, _ = split_host_port(address)
    if ":" in host:
        host = f"[{host}]"  # IPv6 literal
    port = int(www_port or DEFAULT_WWW_PORT)
    netloc = host if port == DEFAULT_WWW_PORT else f"{host}:{port}"
    return f"http://{netloc}/graphs/iface/{interface}/daily.gif"


# Mencari User PPPOE Down
def get_down_users(connection, excluded_profiles=None):
    """Return [(name, last_logged_out)] for PPP secrets that are not active.

    excluded_profiles comes from configs.app_settings.get_monitoring_config()
    (admin global list + the user's own list); nothing is hard-coded here.
    Raises RouterError when the router stops answering, so callers never
    mistake a dropped connection for "all customers up" (and never charge).
    """
    try:
        secret_data = connection('/ppp/secret/print')
        active_data = connection('/ppp/active/print')
    except Exception as exc:
        raise RouterError(classify_router_error(exc), str(exc)) from exc

    excluded = {str(profile).strip().lower() for profile in (excluded_profiles or []) if str(profile).strip()}
    secret_names = {
        secret['name']: secret.get('last-logged-out', '-')
        for secret in secret_data
        if str(secret.get('profile', '')).strip().lower() not in excluded
    }
    active_names = {active['name'] for active in active_data}
    return [(name, last) for name, last in secret_names.items() if name not in active_names]

# Mencari nama Server
def get_name_server(connection):
    """Nama router dari /system/identity, atau None."""
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
        details = get_interface_details(connection)
        if 'all' in configured:
            return details
        enabled_names = {name for name in configured if name and name != 'all'}
        return [item for item in details if item["name"] in enabled_names]
    except Exception as exc:
        print(f"Gagal mengambil konfigurasi graphing: {exc}")
        return []


def get_interface_details(connection):
    """Return interface name and RouterOS comment for friendly button labels."""
    try:
        return [
            {"name": str(item["name"]), "comment": str(item.get("comment", "")).strip()}
            for item in connection('/interface/print') if item.get("name")
        ]
    except Exception as exc:
        print(f"Gagal mengambil detail interface: {exc}")
        return []
