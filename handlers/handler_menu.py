"""Inline-keyboard navigation for the main customer workflow."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from librouteros import connect

from configs.data_json_user import load_user_data, save_user_data
from configs.mikrotik_function import get_graphing_interfaces
from models.userdata import UserData, user_data_dict
from handlers.handler_monitor_settings import monitoring_callback, monitoring_settings
from handlers.handler_start import run_pppoe_test, begin_custom_server
from handlers.handler_traffic import run_traffic_monitoring
from handlers.handler_wallet import topup_approval_callback, wallet_callback, wallet_menu
from configs.chat_cleanup import schedule_cleanup
from handlers.handler_onboarding import new_user_menu, onboarding_callback
from handlers.handler_server import start_server_wizard
from configs.app_settings import is_staff, is_superadmin
from handlers.handler_all_transaction import check_monthly_user_transactions, check_yearly_user_transactions


def show_menu(update, context):
    if is_staff(update.effective_user.id) and not context.user_data.get("user_testing_mode"):
        _send_admin_dashboard(update, context)
        return
    if str(update.effective_user.id) not in load_user_data():
        new_user_menu(update, context)
        return
    _send_user_dashboard(update, context, testing=context.user_data.get("user_testing_mode", False))


def _send_user_dashboard(update, context, testing=False):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥 Server Saya", callback_data="menu:servers"),
         InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe")],
        [InlineKeyboardButton("🔧 Server Custom", callback_data="srv:custom")],
        [InlineKeyboardButton("📈 Traffic", callback_data="menu:traffic"),
         InlineKeyboardButton("💳 Saldo", callback_data="menu:wallet")],
        [InlineKeyboardButton("⚙️ Monitoring", callback_data="menu:monitor"),
         InlineKeyboardButton("🧹 Chat", callback_data="menu:cleanup")],
        [InlineKeyboardButton("🗑 Hapus Akun", callback_data="onboard:delete_confirm")],
    ])
    title = "🧪 Dashboard User Testing" if testing else "🏠 Dashboard User"
    record = load_user_data().get(str(update.effective_user.id), {})
    balance = int(record.get("saldo", 0))
    message = update.effective_message.reply_text(
        title + f"\nSaldo: Rp{balance:,}\nPilih layanan:", reply_markup=keyboard)
    schedule_cleanup(context, message, record.get("chat_cleanup_minutes", 0))


def _send_admin_dashboard(update, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 User Testing", callback_data="admin:testing"),
         InlineKeyboardButton("💳 QRIS", callback_data="admin:qris")],
        [InlineKeyboardButton("⚙️ Harga & Role", callback_data="admin:settings"),
         InlineKeyboardButton("👥 Data User", callback_data="admin:users")],
        [InlineKeyboardButton("📊 Pendapatan Bulanan", callback_data="admin:monthly"),
         InlineKeyboardButton("📈 Pendapatan Tahunan", callback_data="admin:yearly")],
    ])
    update.effective_message.reply_text("🛡 *Dashboard Admin*\nPilih pengelolaan:", parse_mode="Markdown", reply_markup=keyboard)


def menu_callback(update, context):
    query = update.callback_query
    data = query.data
    if data == "nav:home":
        context.user_data.pop("user_testing_mode", None)
        query.answer()
        show_menu(update, context)
        return
    if data.startswith("admin:"):
        _admin_callback(update, context)
        return
    if data.startswith("onboard:"):
        onboarding_callback(query, context)
        return
    if data.startswith("mon:"):
        monitoring_callback(query)
        return
    if data.startswith("wallet:"):
        wallet_callback(query, context)
        return
    if data.startswith("topup:"):
        topup_approval_callback(query, context)
        return
    if data == "menu:monitor":
        query.answer()
        monitoring_settings(update, context)
        return
    if data == "menu:wallet":
        query.answer()
        wallet_menu(update, context)
        return
    if data == "menu:cleanup":
        query.answer()
        keyboard = InlineKeyboardMarkup([[ 
            InlineKeyboardButton("Nonaktif", callback_data="clean:0"),
            InlineKeyboardButton("1 jam", callback_data="clean:60"),
            InlineKeyboardButton("24 jam", callback_data="clean:1440"),
        ]])
        query.edit_message_text("Hapus otomatis pesan bot baru setelah:", reply_markup=keyboard)
        return
    if data.startswith("clean:"):
        _set_cleanup(query, int(data.split(":", 1)[1]))
        return
    if data == "menu:servers":
        _show_servers(query)
        return
    if data == "menu:pppoe":
        if not _require_connection(query):
            _prompt_server_before_pppoe(query)
            return
        query.answer()
        run_pppoe_test(
            context, query.from_user.id, query.message.chat_id,
            user_data_dict[query.from_user.id])
        return
    if data == "menu:traffic":
        if query.from_user.id in user_data_dict:
            _show_interfaces(query, None)
        else:
            _show_traffic_servers(query)
        return
    if data.startswith("srv:connect:"):
        _connect_server(query, int(data.rsplit(":", 1)[1]))
        return
    if data == "srv:add":
        start_server_wizard(query, context)
        return
    if data == "srv:custom":
        query.answer()
        begin_custom_server(context, query.from_user.id, query.message)
        return
    if data.startswith("tr:server:"):
        _show_interfaces(query, int(data.rsplit(":", 1)[1]))
        return
    if data.startswith("tr:iface:"):
        _, _, server_ref, interface = data.split(":", 3)
        _run_traffic(query, context, server_ref, interface)


def _show_servers(query):
    servers = _servers_for(query.from_user.id)
    if not servers:
        query.answer()
        query.edit_message_text(
            "Belum ada server. Tambahkan server pertama Anda.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Tambah server", callback_data="srv:add")]]))
        return
    keyboard = [[InlineKeyboardButton(f"🔌 {server['name']}", callback_data=f"srv:connect:{index}")]
                for index, server in enumerate(servers)]
    keyboard.append([InlineKeyboardButton("➕ Tambah server", callback_data="srv:add")])
    query.answer()
    query.edit_message_text("Pilih server untuk dihubungkan:", reply_markup=InlineKeyboardMarkup(keyboard))


def _connect_server(query, index):
    servers = _servers_for(query.from_user.id)
    if index >= len(servers):
        query.answer("Server tidak ditemukan.", show_alert=True)
        return
    server = servers[index]
    session = user_data_dict.setdefault(query.from_user.id, UserData())
    session.ip_address = server["ip"]
    session.router_username = server["username"]
    session.router_password = server["password"]
    session.server_name = server["name"]
    query.answer("Server tersambung.")
    query.edit_message_text(
        f"✅ Tersambung ke *{server['name']}*.\nPilih aksi:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe"),
             InlineKeyboardButton("📈 Traffic", callback_data="menu:traffic")],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
        ]))


def _show_traffic_servers(query):
    servers = _servers_for(query.from_user.id)
    if not servers:
        query.answer("Tambahkan server terlebih dahulu.", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton(server["name"], callback_data=f"tr:server:{index}")]
                for index, server in enumerate(servers)]
    query.answer()
    query.edit_message_text("Pilih server untuk mengambil daftar interface:", reply_markup=InlineKeyboardMarkup(keyboard))


def _show_interfaces(query, index):
    if index is None:
        session = user_data_dict.get(query.from_user.id)
        if not session or not session.ip_address:
            _show_traffic_servers(query)
            return
        server = {"ip": session.ip_address, "username": session.router_username,
                  "password": session.router_password}
        server_ref = "current"
    else:
        servers = _servers_for(query.from_user.id)
        if index >= len(servers):
            query.answer("Server tidak ditemukan.", show_alert=True)
            return
        server = servers[index]
        server_ref = str(index)
    try:
        connection = connect(username=server["username"], password=server["password"], host=server["ip"])
        interfaces = get_graphing_interfaces(connection)
    except Exception:
        query.answer("Tidak dapat mengambil interface. Periksa koneksi server.", show_alert=True)
        return
    if not interfaces:
        query.answer("Tidak ada interface yang diaktifkan di Tools > Graphing.", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"tr:iface:{server_ref}:{name}")]
                for name in interfaces[:40]]
    query.answer()
    query.edit_message_text("Pilih interface yang aktif di Tools > Graphing:", reply_markup=InlineKeyboardMarkup(keyboard))


def _run_traffic(query, context, server_ref, interface):
    if server_ref == "current":
        session = user_data_dict.get(query.from_user.id)
        if not session:
            query.answer("Pilih server terlebih dahulu.", show_alert=True)
            return
    else:
        servers = _servers_for(query.from_user.id)
        index = int(server_ref)
        if index >= len(servers):
            query.answer("Server tidak ditemukan.", show_alert=True)
            return
        server = servers[index]
        session = user_data_dict.setdefault(query.from_user.id, UserData())
        session.ip_address = server["ip"]
        session.router_username = server["username"]
        session.router_password = server["password"]
    session.interface = interface
    query.answer("Memproses traffic...")
    run_traffic_monitoring(context, query.from_user.id, query.message.chat_id, session)


def _servers_for(user_id):
    return load_user_data().get(str(user_id), {}).get("servers", [])


def _require_connection(query):
    if query.from_user.id not in user_data_dict:
        return False
    return True


def _prompt_server_before_pppoe(query):
    servers = _servers_for(query.from_user.id)
    if not servers:
        query.answer()
        query.edit_message_text(
            "Sebelum Monitor PPPoE, tambahkan lalu pilih server di Server Saya.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🖥 Server Saya", callback_data="menu:servers")]]))
        return
    keyboard = [[InlineKeyboardButton(server["name"], callback_data=f"srv:connect:{index}")]
                for index, server in enumerate(servers)]
    query.answer()
    query.edit_message_text(
        "⚠️ Pilih server terlebih dahulu di Server Saya, lalu jalankan Monitor PPPoE.",
        reply_markup=InlineKeyboardMarkup(keyboard))


def _set_cleanup(query, minutes):
    users = load_user_data()
    record = users.get(str(query.from_user.id))
    if not record:
        query.answer("Anda belum terdaftar.", show_alert=True)
        return
    record["chat_cleanup_minutes"] = minutes
    save_user_data(users)
    label = "nonaktif" if not minutes else f"{minutes} menit"
    query.answer("Pengaturan disimpan.")
    query.edit_message_text(f"Pembersihan otomatis pesan bot: {label}.")


def _admin_callback(update, context):
    query = update.callback_query
    if not is_staff(query.from_user.id):
        query.answer("Akses admin ditolak.", show_alert=True)
        return
    action = query.data.split(":", 1)[1]
    if action == "testing":
        _ensure_staff_test_record(query.from_user)
        context.user_data["user_testing_mode"] = True
        query.answer("Mode user testing aktif.")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥 Server Saya", callback_data="menu:servers"),
             InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe")],
            [InlineKeyboardButton("🔧 Server Custom", callback_data="srv:custom")],
            [InlineKeyboardButton("📈 Traffic", callback_data="menu:traffic"),
             InlineKeyboardButton("💳 Saldo", callback_data="menu:wallet")],
            [InlineKeyboardButton("🏠 Dashboard Admin", callback_data="nav:home")],
        ])
        query.edit_message_text("🧪 *Dashboard User Testing*", parse_mode="Markdown", reply_markup=keyboard)
        return
    if action == "qris":
        if not is_superadmin(query.from_user.id):
            query.answer("Hanya superadmin.", show_alert=True)
            return
        context.user_data["qris_upload"] = True
        query.answer()
        query.edit_message_text("Kirim foto QRIS berikutnya untuk mengganti QRIS topup.")
        return
    if action == "settings":
        query.answer()
        query.edit_message_text("Pengaturan admin:\n/setprice <fitur> <nominal>\n/settrial <nominal>\n/setrole <id> <operator|admin|user>\n/setqris")
        return
    if action == "users":
        users = load_user_data()
        query.answer()
        query.edit_message_text(f"Total user terdaftar: {len(users)}\nGunakan /useraktif atau /saldouser untuk rincian.")
        return
    if action == "monthly":
        query.answer()
        check_monthly_user_transactions(update, context)
        return
    if action == "yearly":
        query.answer()
        check_yearly_user_transactions(update, context)


def _ensure_staff_test_record(user):
    """Give staff a zero-balance private record for server/UI testing only."""
    users = load_user_data()
    if str(user.id) not in users:
        users[str(user.id)] = {
            "user_id": user.id,
            "username_telegram": user.username or user.full_name,
            "nohp": "-",
            "saldo": 0,
            "servers": [],
            "aktif": True,
            "monitoring": {},
            "monitoring_state": {},
        }
        save_user_data(users)
