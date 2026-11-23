"""Uji regresi alur utama bot. Jalankan lewat: python tests/run_regresi.py

Setiap uji mencetak PASS/FAIL. Tambahkan uji baru di bagian paling bawah
setiap kali menambah fitur (lihat docs/PANDUAN-PENGEMBANGAN.md §7).
"""
import os
import sys

if os.environ.get("SKYTAMA_TEST_SANDBOX") != "1":
    sys.exit("Jalankan lewat: python tests/run_regresi.py (agar data asli tidak tersentuh)")

os.environ.update(TELEGRAM_BOT_TOKEN="test", ALLOWED_ADMIN_IDS="1", TELEGRAM_BOT_LOG_TOKEN="test",
                  LOG_USER_ID="9", APP_VERSION="2.2.1", APP_NAME="bot test")

import telegram  # tiruan dari tests/stubs
from librouteros import ROUTER
from telegram import LIVE, Msg

from configs import chat_tracker

chat_tracker.SYNCHRONOUS = True  # background work (deletes, router checks, logs) runs inline in tests
from configs.app_settings import load_settings
from configs.data_json_user import load_app_info, load_user_data, save_app_info, save_user_data
from configs.send_message import bot
from handlers import check_client_status_and_notify as job
from handlers.handler_command_redirect import cancel_command
from handlers.handler_input import handle_input
from handlers.handler_menu import menu_callback, show_menu
from handlers.handler_version import version_text
from handlers.handler_wallet import capture_payment_proof
from handlers.handler_onboarding import handle_contact
from configs import mikrotik_function
from handlers import handler_traffic

PING = {"reply": True}
mikrotik_function.ping_host = lambda host: PING["reply"]
IMAGES = {"ok": False, "urls": []}


def _fake_fetch_image(url, timeout=15):
    IMAGES["urls"].append(url)
    return b"GIF" if IMAGES["ok"] else None


handler_traffic.fetch_image = _fake_fetch_image

SUPERADMIN, USER, LOG_CHAT = 1, 42, 9
FAILED = []


# ---------------------------------------------------------------- alat bantu
def check(condition, label):
    print(("PASS " if condition else "FAIL ") + label)
    if not condition:
        FAILED.append(label)


class _User:
    def __init__(self, uid):
        self.id = uid
        self.username = f"user_{uid}"
        self.full_name = "Tester"


class _Query:
    def __init__(self, uid, message, data):
        self.from_user = _User(uid)
        self.message = message
        self.data = data

    def answer(self, *args, **kwargs):
        pass

    def edit_message_text(self, text, **kwargs):
        return bot.edit_message_text(chat_id=self.message.chat_id, message_id=self.message.message_id,
                                     text=text, **kwargs)

    def edit_message_caption(self, **kwargs):
        pass


class _Update:
    def __init__(self, uid, message=None, query=None):
        self.message = message
        self.callback_query = query
        self.effective_user = _User(uid)
        self.effective_chat = telegram.Chat(uid)
        self.effective_message = message or query.message


_CONTEXTS = {}


class _Context:
    def __init__(self, uid, args=None):
        self.bot = bot
        self.user_data = _CONTEXTS.setdefault(uid, {})
        self.args = args or []
        self.job_queue = type("JobQueue", (), {"run_once": lambda *a, **k: None})()


def _dispatch(uid, update, handler, args=None):
    """Meniru urutan main.py: chat_tracker (group -1) → handler → chat_tracker (group 1)."""
    context = _Context(uid, args)
    chat_tracker.before_update(update, context)
    handler(update, context)
    chat_tracker.after_update(update, context)


def say(uid, text):
    """User mengetik teks/command."""
    message = Msg(uid, text)
    handler = cancel_command if text == "/cancel" else show_menu if text.startswith("/") else handle_input
    _dispatch(uid, _Update(uid, message=message), handler)


def press(uid, data):
    """User menekan tombol pada pesan terakhir di chat-nya."""
    message = Msg.__new__(Msg)
    message.chat_id, message.chat, message.text, message.photo = uid, telegram.Chat(uid), "", None
    message.message_id = max(LIVE.get(uid, {0: ""}))
    _dispatch(uid, _Update(uid, query=_Query(uid, message, data)), menu_callback)


def send_photo(uid):
    message = Msg(uid, "[foto]")
    message.photo = [type("Photo", (), {"file_id": "FILE123"})()]
    _dispatch(uid, _Update(uid, message=message), capture_payment_proof)


def send_contact(uid, phone, owner=None):
    """User membagikan kontak lewat tombol 📱 Kirim Nomor Saya (owner = pemilik kontak)."""
    message = Msg(uid, "[kontak]")
    message.contact = type("Contact", (), {"user_id": owner or uid, "phone_number": phone})()
    _dispatch(uid, _Update(uid, message=message), handle_contact)


def last(uid):
    return [text for chat, text in telegram.SENT if chat == uid][-1]


def monitoring_tick(down):
    """Satu putaran scheduler dengan `down` pelanggan down."""
    ROUTER["down"] = down
    users = load_user_data()
    users[str(USER)].setdefault("monitoring_state", {})["last_check_at"] = "2000-01-01 00:00:00"
    save_user_data(users)
    job.check_client_status_and_notify(type("JobContext", (), {"bot": bot})())


def saldo():
    return load_user_data()[str(USER)]["saldo"]


# ---------------------------------------------------------------- uji
# Registrasi
say(USER, "/start")
press(USER, "onboard:register")
say(USER, "08123456789")
check(not load_app_info().get("registration_requests"), "nomor yang diketik tidak diterima (wajib tombol kontak)")
send_contact(USER, "+628123456789", owner=777)
check(not load_app_info().get("registration_requests"), "kontak milik orang lain ditolak")
press(USER, "onboard:register")
send_contact(USER, "+628123456789")
request_id = list(load_app_info()["registration_requests"])[0]
press(SUPERADMIN, f"reg:trial:{request_id}")
check(saldo() == 5000, "registrasi disetujui dengan saldo trial default")

# Pengaturan admin
press(SUPERADMIN, "admin:settings")
press(SUPERADMIN, "admin:set:max_servers")
say(SUPERADMIN, "2")
check(load_settings()["max_servers"] == 2, "superadmin mengubah batas server lewat tombol")

# Server Saya & batas server
for name in ("A", "B"):
    press(USER, "srv:add")
    for text in (name, "10.0.0.1", "readonly", "rahasia"):
        say(USER, text)
check(len(load_user_data()[str(USER)]["servers"]) == 2, "tambah 2 server lewat form")
press(USER, "srv:add")
check("Batas server tercapai" in last(USER), "server ke-3 ditolak (batas 2)")

# Chat ringkas
say(USER, "/menu")
check(len(LIVE[USER]) == 2, "setelah /menu hanya tersisa dashboard + pesan approval registrasi")

# Cek PPPoE manual
ROUTER["down"] = 1
press(USER, "srv:connect:0")
press(USER, "menu:pppoe")
logs = [text for text in LIVE[USER].values() if "Cek PPPoE" in text]
check(bool(logs) and "pel\\_0000" in logs[-1], "cek manual: 1 down tampil namanya dan tersimpan sebagai log")
ROUTER["down"] = 400
press(USER, "menu:pppoe")
check(any("[FILE" in text for text in LIVE[USER].values()), "400 down dikirim sebagai 1 pesan + lampiran .txt")

# Monitoring otomatis 2 tahap (2 server tersimpan → 2 notifikasi)
users = load_user_data()
users[str(USER)]["monitoring"] = {"warning_threshold": 2, "critical_threshold": 4}
save_user_data(users)
before = saldo()
monitoring_tick(1)
monitoring_tick(2)
check(before - saldo() == 2 * 250, "⚠️ tahap 1 memotong biaya notifikasi per server")
after_stage1 = saldo()
monitoring_tick(4)
check(saldo() == after_stage1, "🚨 eskalasi dalam jeda alert gratis")
monitoring_tick(0)
check(any("pulih" in text for text in LIVE[USER].values()), "pesan pulih saat di bawah ambang")
ROUTER["fail"] = True
monitoring_tick(1)
count = len(telegram.SENT)
monitoring_tick(1)
ROUTER["fail"] = False
check(len(telegram.SENT) == count, "router tidak terhubung: peringatan hanya sekali")
check(any("Server tidak dapat dihubungi" in text and "tidak merespons" in text and "Saldo tidak dipotong" in text
          for chat, text in telegram.SENT if chat == USER), "monitoring: router down diberi pesan jelas")
before = saldo()
monitoring_tick(1)
check(saldo() == before and "kembali terhubung" in last(USER), "monitoring: pesan saat router terhubung kembali")
ROUTER["query_fail"] = True
monitoring_tick(10)
ROUTER["query_fail"] = False
check(saldo() == before and not any("pulih" in text for text in telegram.SENT[-2:]),
      "monitoring: router putus di tengah cek tidak dianggap pulih dan tidak dipotong")
monitoring_tick(0)

# Koneksi router gagal: pesan jelas & saldo tidak dipotong
before = saldo()
ROUTER["fail"] = "timeout"
press(USER, "menu:pppoe")
check(saldo() == before and "tidak merespons" in last(USER) and "Saldo tidak dipotong" in last(USER),
      "cek PPPoE saat router down: pesan jelas, saldo tidak dipotong")
ROUTER["fail"] = False
ROUTER["query_fail"] = True
press(USER, "menu:pppoe")
ROUTER["query_fail"] = False
check(saldo() == before and "UP Semua" not in last(USER), "cek PPPoE terputus di tengah: tanpa biaya")
servers_before = load_user_data()[str(USER)]["servers"]
ROUTER["fail"] = "login"
press(USER, "srv:edit:0")
for text in ("A", "10.0.0.1", "salah", "salah"):
    say(USER, text)
check("Login ke" in last(USER) and "belum disimpan" in last(USER)
      and load_user_data()[str(USER)]["servers"] == servers_before,
      "tambah/edit server: username/password salah ditolak, tidak disimpan")
ROUTER["fail"] = "refused"
press(USER, "srv:edit:0")
for text in ("A2", "10.0.0.1", "readonly", "rahasia"):
    say(USER, text)
check("menolak koneksi API" in last(USER), "tambah/edit server: API mati diberi tahu")
press(USER, "srv:forcesave")
check(load_user_data()[str(USER)]["servers"][0]["name"] == "A2", "server tetap bisa disimpan tanpa cek")
ROUTER["fail"] = "host"
press(USER, "srv:custom")
for text in ("router.salah", "readonly", "rahasia"):
    say(USER, text)
check("tidak dikenal" in last(USER) and "belum tersambung" in last(USER), "server custom: alamat salah diberi tahu")
ROUTER["fail"] = False
press(USER, "srv:edit:0")
for text in ("A", "10.0.0.1", "readonly", "rahasia"):
    say(USER, text)
check("Koneksi berhasil" in last(USER), "tambah/edit server: koneksi diuji sebelum disimpan")
press(USER, "srv:connect:0")

# Alamat dengan port API & DDNS, diagnosa ping
press(USER, "srv:edit:0")
say(USER, "A")
say(USER, "router.ddns.net:99999")
check("Port harus" in last(USER), "port API di luar 1-65535 ditolak")
ROUTER["fail"] = "timeout"
PING["reply"] = True
for text in ("router.ddns.net:8000", "readonly", "rahasia"):
    say(USER, text)
check(ROUTER["last"].get("host") == "router.ddns.net" and ROUTER["last"].get("port") == 8000,
      "alamat host:port dipakai sebagai host + port API")
check("membalas ping" in last(USER) and "port API 8000" in last(USER),
      "gagal login tapi ping membalas: diarahkan ke masalah port/API")
press(USER, "srv:edit:0")
PING["reply"] = False
for text in ("A", "router.ddns.net", "readonly", "rahasia"):
    say(USER, text)
check("tidak membalas ping" in last(USER), "ping tidak membalas: diarahkan ke router mati / IP salah")
ROUTER["fail"] = "refused"
press(USER, "srv:edit:0")
for text in ("A", "router.ddns.net", "readonly", "rahasia"):
    say(USER, text)
check("Router terjangkau" in last(USER), "koneksi ditolak: IP benar, masalah di port API")
ROUTER["fail"] = False
PING["reply"] = True
press(USER, "srv:edit:0")
for text in ("A", "router.ddns.net:8000", "readonly", "rahasia"):
    say(USER, text)
check(load_user_data()[str(USER)]["servers"][0]["ip"] == "router.ddns.net:8000", "server DDNS + port tersimpan")

# Monitor Traffic: Graphing kosong, port web, grafik gagal
ROUTER["graphing"] = False
press(USER, "tr:server:0")
check("Graphing di router masih kosong" in last(USER) and "/tool graphing interface add" in last(USER),
      "Graphing kosong: panduan konfigurasi tampil")
ROUTER["graphing"] = True
press(USER, "tr:server:0")
before = saldo()
press(USER, "tr:iface:0:ether1")
check(saldo() == before and "port *80*" in last(USER) and "Graphing aktif" in last(USER),
      "grafik gagal: petunjuk port web, saldo tidak dipotong")
check(IMAGES["urls"][-1] == "http://router.ddns.net/graphs/iface/ether1/daily.gif",
      "URL grafik memakai host tanpa port API")
press(USER, "tr:www")
say(USER, "70000")
check("Port harus" in last(USER), "port web tidak valid ditolak")
say(USER, "8080")
check(load_user_data()[str(USER)]["servers"][0].get("www_port") == 8080, "port web tersimpan di Server Saya")
IMAGES["ok"] = True
press(USER, "tr:retry")
check(IMAGES["urls"][-1].startswith("http://router.ddns.net:8080/") and saldo() < before,
      "coba lagi memakai port web baru dan saldo dipotong saat berhasil")
press(USER, "srv:edit:0")
for text in ("A", "router.ddns.net:8000", "readonly", "rahasia"):
    say(USER, text)
check(load_user_data()[str(USER)]["servers"][0].get("www_port") == 8080, "edit server tidak menghapus port web")
press(USER, "srv:manage:0")
check("8080" in last(USER), "⚙️ Kelola menampilkan port web")
IMAGES["ok"] = False
ROUTER["graphing"] = False
press(USER, "srv:connect:0")

# Topup QRIS & saldo manual
app_info = load_app_info()
app_info.setdefault("settings", {})["qris_file_id"] = "QRIS"
save_app_info(app_info)
press(USER, "nav:home")
press(USER, "menu:wallet")
press(USER, "wallet:amount:5000")
send_photo(USER)
topup_id = [k for k, v in load_app_info()["topup_requests"].items() if v["status"] == "pending"][0]
press(SUPERADMIN, f"topup:approve:{topup_id}")
check("(ID 42)" in last(SUPERADMIN), "approval topup menampilkan nama + ID user")
press(SUPERADMIN, "admin:manualtopup")
say(SUPERADMIN, str(USER))
say(SUPERADMIN, "1000")
check("ID: 42" in last(LOG_CHAT), "saldo manual tercatat di chat log admin")

# Info, biaya, versi
press(USER, "menu:info")
check("Rincian Biaya" not in "".join(LIVE[USER].values()), "/info user tidak menampilkan rincian biaya")
press(USER, "menu:biaya")
check("Rincian Biaya" in last(USER), "tombol 💸 Biaya menampilkan rincian biaya")
check("2.3.0" not in version_text(False) and "belum dirilis" in version_text(True),
      "update yang belum dirilis tersembunyi dari user, terlihat admin")

# Form & teks bebas
press(USER, "mon:input:warning_threshold")
say(USER, "/cancel")
check("monitoring_input_field" not in _CONTEXTS[USER], "/cancel menutup form")
count = len(telegram.SENT)
say(USER, "halo")
check(len(telegram.SENT) == count, "teks bebas tanpa form tidak dibalas")

# Bersihkan chat
press(USER, "menu:cleanup")
press(USER, "clean:all")
check(len(LIVE[USER]) == 1, "🗑 Bersihkan semua chat menyisakan 1 pesan konfirmasi")

# ---------------------------------------------------------------- keamanan akses admin
from datetime import datetime, timedelta

from configs.access import staff_only
from configs.app_settings import get_topup_package, get_trial_mode, in_quiet_hours, parse_quiet_hours
from handlers.handler_admin_settings import settings_command

notify_price = load_settings()["prices"]["notify"]
press(USER, "admin:set:price:notify")
say(USER, "1")
check(load_settings()["prices"]["notify"] == notify_price and "admin_input" not in _CONTEXTS[USER],
      "user tidak bisa membuka form admin lewat callback palsu")
count = len(telegram.SENT)
press(USER, "reg:view:palsu")
press(USER, "users:balances")
check(not any("Saldo semua user" in text for _, text in telegram.SENT[count:]), "user tidak bisa melihat data user")
check(any("Akses admin ditolak" in text for chat, text in telegram.SENT if chat == LOG_CHAT),
      "percobaan akses admin dicatat di chat log")
_dispatch(USER, _Update(USER, message=Msg(USER, "/settings")), staff_only(settings_command))
check("tidak tersedia" in last(USER), "command admin ditolak untuk user")
GUEST = 55
count = len(telegram.SENT)
press(GUEST, "menu:servers")
check(len(telegram.SENT) == count, "akun belum terdaftar tidak bisa membuka menu user")

# ---------------------------------------------------------------- anti registrasi massal & trial
OTHER, REJECTED, LATE = 43, 44, 56
press(OTHER, "onboard:register")
send_contact(OTHER, "08123456789")  # nomor yang sama dengan USER
other_request = [k for k, v in load_app_info()["registration_requests"].items() if v["user_id"] == OTHER][0]
check(bool(load_app_info()["registration_requests"][other_request]["trial_block_reason"]),
      "nomor yang sudah dipakai ditandai tidak layak trial")
press(SUPERADMIN, f"reg:trial:{other_request}")
check(load_user_data()[str(OTHER)]["saldo"] == 0, "akun kedua dengan nomor sama tidak mendapat trial")
press(REJECTED, "onboard:register")
send_contact(REJECTED, "0811111111")
rejected_request = [k for k, v in load_app_info()["registration_requests"].items() if v["user_id"] == REJECTED][0]
press(SUPERADMIN, f"reg:reject:{rejected_request}")
press(REJECTED, "onboard:register")
check("Coba lagi dalam" in last(REJECTED) and "onboarding_step" not in _CONTEXTS[REJECTED],
      "user yang ditolak harus menunggu jeda")
press(SUPERADMIN, "admin:trial")
check("Ketentuan Trial" in last(SUPERADMIN), "menu 🎁 Trial & Registrasi tampil")
press(SUPERADMIN, "admin:set:reg_limit")
say(SUPERADMIN, "3")
press(LATE, "onboard:register")
check("ramai" in last(LATE), "batas pengajuan registrasi per jam")
press(SUPERADMIN, "admin:set:reg_limit")
say(SUPERADMIN, "10")
press(SUPERADMIN, "admin:trialmode:auto")
check(get_trial_mode() == "auto", "mode trial diubah dari menu admin")
press(SUPERADMIN, "admin:trialmode:manual")

# ---------------------------------------------------------------- paket saldo + QRIS statik
press(SUPERADMIN, "admin:pkg")
press(SUPERADMIN, "admin:set:pkg_new")
say(SUPERADMIN, "3000")
send_photo(SUPERADMIN)
check((get_topup_package(3000) or {}).get("qris_file_id") == "FILE123", "admin menambah paket Rp3.000 + QRIS")
press(SUPERADMIN, "admin:set:pkg_edit:3000")
say(SUPERADMIN, "3500")
check(bool(get_topup_package(3500)) and get_topup_package(3000) is None, "admin mengubah nominal paket")
press(SUPERADMIN, "admin:pkg:del:3500")
check(get_topup_package(3500) is None, "admin menghapus paket")
press(USER, "admin:pkg:del:5000")
check(get_topup_package(5000) is not None, "user tidak bisa menghapus paket")

# ---------------------------------------------------------------- nominal bebas + QRIS umum
press(SUPERADMIN, "admin:qris")
send_photo(SUPERADMIN)
press(USER, "nav:home")
press(USER, "menu:wallet")
press(USER, "wallet:custom")
say(USER, "500")
check("Nominal harus" in last(USER), "nominal bebas di bawah batas ditolak")
say(USER, "15000")
check("[FOTO]" in last(USER) and "15,000" in last(USER), "nominal bebas menampilkan QRIS umum")
send_photo(USER)
custom = [v for v in load_app_info()["topup_requests"].values() if v.get("source") == "custom"]
check(bool(custom) and custom[0]["amount"] == 15000, "bukti transfer nominal bebas masuk antrian")

# ---------------------------------------------------------------- jam senyap notifikasi
quiet = parse_quiet_hours("22:00-06:00")
check(in_quiet_hours(quiet, datetime(2026, 1, 1, 23, 30)) and in_quiet_hours(quiet, datetime(2026, 1, 1, 5, 59))
      and not in_quiet_hours(quiet, datetime(2026, 1, 1, 6, 0)), "jam senyap melewati tengah malam")
press(USER, "mon:quiet")
say(USER, "25:00-06:00")
check("Format jam senyap" in last(USER), "format jam senyap yang salah ditolak")
now = datetime.now(job.TIMEZONE)
say(USER, f"{(now - timedelta(hours=1)):%H:%M}-{(now + timedelta(hours=1)):%H:%M}")
check(bool(load_user_data()[str(USER)]["monitoring"].get("quiet_hours")), "jam senyap disimpan")
check("Pengaturan Monitoring" in last(USER) and "Jam senyap: *" in last(USER) and "Cek router setiap" in last(USER),
      "setelah input monitoring, ringkasan pengaturan terbaru langsung tampil")
before = saldo()
count = sum(1 for chat, _ in telegram.SENT if chat == USER)
monitoring_tick(10)
check(saldo() == before and sum(1 for chat, _ in telegram.SENT if chat == USER) == count,
      "jam senyap: tanpa notifikasi dan tanpa potong saldo")
press(USER, "mon:quiet")
say(USER, "-")
check("quiet_hours" not in load_user_data()[str(USER)]["monitoring"], "jam senyap dinonaktifkan")

# ---------------------------------------------------------------- hapus user + refund
press(SUPERADMIN, "admin:set:delete_user")
say(SUPERADMIN, str(OTHER))
check("Hapus user" in last(SUPERADMIN), "admin melihat rincian refund sebelum menghapus user")
press(SUPERADMIN, f"users:delete:{OTHER}")
check(str(OTHER) not in load_user_data() and "dihapus oleh admin" in last(OTHER),
      "admin menghapus user dan user diberi tahu")
press(SUPERADMIN, "admin:settings")
press(SUPERADMIN, "admin:set:refund_percent")
say(SUPERADMIN, "50")
expected = max(0, saldo() - 5000) * 50 // 100
press(USER, "onboard:delete_confirm")
check("Refund uang" in last(USER), "hapus akun menampilkan pemberitahuan refund")
press(USER, "onboard:delete_now")
check(str(USER) not in load_user_data(), "akun user terhapus")
refunds = load_app_info().get("refund_requests", {})
refund_id = next(iter(refunds), None)
check(bool(refund_id) and expected > 0 and refunds[refund_id]["amount"] == expected,
      "refund = 50% saldo berbayar (saldo trial tidak direfund)")
check(all(v["status"] != "pending" for v in load_app_info()["topup_requests"].values() if v["user_id"] == USER),
      "topup yang menunggu dibatalkan saat akun dihapus")
press(SUPERADMIN, f"refund:paid:{refund_id}")
check("telah dikirim" in last(USER), "user diberi tahu refund sudah dibayar")
press(USER, "onboard:register")
send_contact(USER, "+628123456789")
again = [k for k, v in load_app_info()["registration_requests"].items()
         if v["user_id"] == USER and v["status"] == "pending"][0]
press(SUPERADMIN, f"reg:trial:{again}")
check(saldo() == 0, "daftar ulang setelah hapus akun tidak mendapat trial lagi")

# ---------------------------------------------------------------- kecepatan & keamanan data multi-thread
import threading
import time

from configs.billing import charge_user
from configs.app_settings import get_price


def _wait_for(condition, seconds=5):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


chat_tracker.SYNCHRONOUS = False
ROUTER["delay"] = 1.0
press(SUPERADMIN, "srv:custom")
for text in ("10.9.9.9", "readonly", "rahasia"):
    say(SUPERADMIN, text)
check(_wait_for(lambda: "tersambung untuk sesi ini" in last(SUPERADMIN)), "server custom diuji di latar belakang")
started = time.time()
press(SUPERADMIN, "menu:pppoe")
blocked = time.time() - started
press(USER, "nav:home")  # another user is served while the router check is still running
check(blocked < 0.5, f"router lambat tidak menahan dispatcher ({blocked:.2f} dtk)")
check(_wait_for(lambda: any("Cek PPPoE" in text for chat, text in telegram.SENT if chat == SUPERADMIN)),
      "hasil cek PPPoE di latar belakang tetap terkirim")
ROUTER["delay"] = 0
count = len(LIVE.get(USER, {}))
press(USER, "menu:servers")
check(_wait_for(lambda: len(LIVE.get(USER, {})) <= count), "pesan lama dihapus di latar belakang")
chat_tracker.SYNCHRONOUS = True

users = load_user_data()
users[str(USER)]["saldo"] = 100000
save_user_data(users)
threads = [threading.Thread(target=charge_user, args=(USER, "testppp")) for _ in range(20)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
check(saldo() == 100000 - 20 * get_price("testppp"), "potong saldo bersamaan dari banyak thread tidak hilang")
check(len([t for t in load_user_data()[str(USER)]["transactions"] if t["type"] == "testppp"]) >= 20,
      "riwayat transaksi bersamaan tercatat semua")

print(f"\n{'SEMUA LULUS' if not FAILED else f'{len(FAILED)} GAGAL'}")
sys.exit(1 if FAILED else 0)
