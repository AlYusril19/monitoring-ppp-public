"""Inline-keyboard navigation for the main customer workflow."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.data_json_user import load_user_data, save_user_data
from configs.mikrotik_function import (DEFAULT_WWW_PORT, RouterError, connect_router, get_graphing_interfaces,
                                       router_error_text)
from models.userdata import UserData, user_data_dict
from handlers.handler_monitor_settings import monitoring_callback, monitoring_settings
from handlers.handler_start import run_pppoe_test, begin_custom_server
from handlers.handler_traffic import begin_www_port, retry_traffic, run_traffic_monitoring
from handlers.handler_wallet import (begin_manual_topup, begin_qris_upload, package_callback, packages_menu,
                                    pending_topups_menu, topup_approval_callback, topup_queue_callback,
                                    wallet_callback, wallet_menu)
from handlers.handler_refund import pending_refunds_menu, refund_callback
from configs.access import callback_allowed
from configs.chat_cleanup import schedule_cleanup
from configs.chat_tracker import in_background
from handlers.handler_onboarding import (new_user_menu, onboarding_callback,
                                         pending_registrations_menu,
                                         registration_approval_callback,
                                         registration_queue_callback)
from handlers.handler_server import force_save_server, start_edit_server_wizard, start_server_wizard
from handlers.handler_admin_settings import admin_settings_menu, set_trial_mode_callback, start_admin_input, trial_menu
from handlers.handler_user import users_callback, users_menu
from handlers.handler_transaction import check_monthly_transactions, check_yearly_transactions
from configs.app_settings import get_server_limit, is_staff
from handlers.handler_all_transaction import check_monthly_user_transactions, check_yearly_user_transactions
from handlers.handler_info import infolengkap_command_handler, notify_command_handler
from handlers.handler_biaya import biaya_fitur
from handlers.handler_version import version_command_handler
from configs.navigation import (back_keyboard, cancel_keyboard, clear_pending_inputs, dashboard_row,
                               home_keyboard, wizard_keyboard)
from configs.chat_tracker import clear_chat, track_message
from configs.send_message import escape_md


def show_menu(update, context):
    # One-time removal of an old "Reply to ..." bar (no-op once done for this chat).
    """/start, /menu, tombol Dashboard: dashboard sesuai peran, atau tombol registrasi."""
    from handlers.send_startup_message import clear_reply_interface
    clear_reply_interface(context.bot, {update.effective_user.id})
    staff = is_staff(update.effective_user.id)
    if not staff:
        # A former staff member must not keep the User Testing shortcut back to admin.
        context.user_data.pop("user_testing_mode", None)
    if staff and not context.user_data.get("user_testing_mode"):
        _send_admin_dashboard(update, context)
        return
    if str(update.effective_user.id) not in load_user_data():
        new_user_menu(update, context)
        return
    _send_user_dashboard(update, context, testing=staff and context.user_data.get("user_testing_mode", False))


def _user_dashboard_keyboard(user_id, testing=False):
    """Single source for the user dashboard.

    User Testing (admin) uses exactly the same buttons as a real user, plus one
    row to return to the admin dashboard, so testing reflects production.
    """
    keyboard_rows = [
        [InlineKeyboardButton("🖥 Server Saya", callback_data="menu:servers"),
         InlineKeyboardButton("🔧 Server Custom", callback_data="srv:custom")],
        [InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe"),
         InlineKeyboardButton("📈 Monitor Traffic", callback_data="menu:traffic")],
        [InlineKeyboardButton("💳 Saldo", callback_data="menu:wallet"),
         InlineKeyboardButton("⚙️ Monitoring", callback_data="menu:monitor")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="menu:info"),
         InlineKeyboardButton("🔔 Info Notify", callback_data="menu:notify")],
        [InlineKeyboardButton("🧹 Chat", callback_data="menu:cleanup")],
        [InlineKeyboardButton("🗑 Hapus Akun", callback_data="onboard:delete_confirm")],
    ]
    session = user_data_dict.get(user_id)
    if session and session.ip_address:
        keyboard_rows.insert(-1, [InlineKeyboardButton("🔒 Logout Router", callback_data="nav:logout")])
    if testing:
        keyboard_rows.append([InlineKeyboardButton("🛡 Kembali ke Dashboard Admin", callback_data="admin:exittesting")])
    return InlineKeyboardMarkup(keyboard_rows)


def _send_user_dashboard(update, context, testing=False):
    """Kirim dashboard user (juga dipakai User Testing)."""
    keyboard = _user_dashboard_keyboard(update.effective_user.id, testing)
    title = "🧪 Dashboard User Testing" if testing else "🏠 Dashboard User"
    record = load_user_data().get(str(update.effective_user.id), {})
    balance = int(record.get("saldo", 0))
    message = update.effective_message.reply_text(
        title + f"\nSaldo: Rp{balance:,}\nPilih layanan:", reply_markup=keyboard)
    schedule_cleanup(context, message, record.get("chat_cleanup_minutes", 0))


def _send_admin_dashboard(update, context):
    """Kirim dashboard admin."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 User Testing", callback_data="admin:testing"),
         InlineKeyboardButton("💳 Paket & QRIS", callback_data="admin:pkg")],
        [InlineKeyboardButton("⚙️ Harga & Role", callback_data="admin:settings"),
         InlineKeyboardButton("👥 Data User", callback_data="admin:users")],
        [InlineKeyboardButton("📥 Antrian Registrasi", callback_data="admin:registrations"),
         InlineKeyboardButton("⏳ Antrian Topup", callback_data="admin:topups")],
        [InlineKeyboardButton("➕ Tambah Saldo", callback_data="admin:manualtopup"),
         InlineKeyboardButton("💸 Antrian Refund", callback_data="admin:refunds")],
        [InlineKeyboardButton("📊 Pendapatan Bulanan", callback_data="admin:monthly"),
         InlineKeyboardButton("📈 Pendapatan Tahunan", callback_data="admin:yearly")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="menu:info"),
         InlineKeyboardButton("🔔 Info Notify", callback_data="menu:notify")],
    ])
    update.effective_message.reply_text("🛡 *Dashboard Admin*\nPilih pengelolaan:", parse_mode="Markdown", reply_markup=keyboard)


def menu_callback(update, context):
    """Router SEMUA tombol inline berdasarkan prefix callback_data (lihat docs/ALUR-FITUR.md §2)."""
    query = update.callback_query
    data = query.data or ""
    # Central access check: staff-only prefixes and unregistered accounts (configs/access.py).
    if not callback_allowed(query):
        return
    if data == "nav:home":
        # Stay in User Testing until the admin explicitly exits it.
        query.answer()
        show_menu(update, context)
        return
    if data == "nav:logout":
        user_data_dict.pop(query.from_user.id, None)
        query.answer("Logout router berhasil.")
        query.edit_message_text(
            "✅ Login router dibersihkan untuk sesi ini.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")]]))
        return
    if data.startswith("input:"):
        _input_wizard_callback(query, context)
        return
    if data.startswith("admin:"):
        _admin_callback(update, context)
        return
    if data.startswith("users:"):
        users_callback(update, context)
        return
    if data.startswith("hist:"):
        query.answer()
        if data == "hist:monthly":
            check_monthly_transactions(update, context)
        else:
            check_yearly_transactions(update, context)
        return
    if data.startswith("onboard:"):
        onboarding_callback(query, context)
        return
    if data.startswith("reg:"):
        if data.startswith("reg:view:"):
            registration_queue_callback(query, context)
        else:
            registration_approval_callback(query, context)
        return
    if data.startswith("mon:"):
        monitoring_callback(query, context)
        return
    if data.startswith("wallet:"):
        wallet_callback(query, context)
        return
    if data.startswith("refund:"):
        refund_callback(query, context)
        return
    if data.startswith("topup:"):
        if data.startswith("topup:view:"):
            topup_queue_callback(query, context)
        else:
            topup_approval_callback(query, context)
        return
    if data == "menu:monitor":
        query.answer()
        monitoring_settings(update, context)
        return
    if data == "menu:info":
        query.answer()
        infolengkap_command_handler(update, context)
        return
    if data == "menu:notify":
        query.answer()
        notify_command_handler(update, context)
        return
    if data == "menu:version":
        query.answer()
        version_command_handler(update, context)
        return
    if data == "menu:biaya":
        query.answer()
        biaya_fitur(update, context)
        return
    if data == "menu:wallet":
        query.answer()
        wallet_menu(update, context)
        return
    if data == "menu:cleanup":
        query.answer()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Bersihkan semua chat", callback_data="clean:all")],
            [InlineKeyboardButton("Nonaktif", callback_data="clean:0"),
             InlineKeyboardButton("1 jam", callback_data="clean:60"),
             InlineKeyboardButton("24 jam", callback_data="clean:1440")],
            dashboard_row()])
        query.edit_message_text(
            "🧹 *Chat*\n"
            "Balasan bot otomatis terhapus saat Anda menekan tombol berikutnya; hasil monitoring tetap disimpan.\n\n"
            "🗑 *Bersihkan semua chat*: hapus semua pesan, termasuk hasil monitoring (maks. 48 jam terakhir).\n"
            "Atau hapus otomatis menu dashboard setelah:",
            parse_mode="Markdown", reply_markup=keyboard)
        return
    if data == "clean:all":
        query.answer("Membersihkan chat...")
        removed = clear_chat(context.bot, query.message.chat_id)
        done = context.bot.send_message(chat_id=query.message.chat_id,
                                        text=f"🧹 Chat dibersihkan ({removed} pesan).", reply_markup=home_keyboard())
        track_message(done)
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
        # Router work runs off the dispatcher so a slow router never blocks other users.
        in_background(run_pppoe_test, context, query.from_user.id, query.message.chat_id,
                      user_data_dict[query.from_user.id])
        return
    if data == "menu:traffic":
        if query.from_user.id in user_data_dict:
            in_background(_show_interfaces, query, None)
        else:
            _show_traffic_servers(query)
        return
    if data.startswith("srv:connect:"):
        _connect_server(query, int(data.rsplit(":", 1)[1]))
        return
    if data.startswith("srv:manage:"):
        _show_server_manage(query, int(data.rsplit(":", 1)[1]))
        return
    if data.startswith("srv:edit:"):
        start_edit_server_wizard(query, context, int(data.rsplit(":", 1)[1]))
        return
    if data.startswith("srv:deleteask:"):
        _ask_delete_server(query, int(data.rsplit(":", 1)[1]))
        return
    if data.startswith("srv:deleteconfirm:"):
        _delete_server(query, int(data.rsplit(":", 1)[1]))
        return
    if data == "srv:forcesave":
        force_save_server(query, context)
        return
    if data == "srv:add":
        start_server_wizard(query, context)
        return
    if data == "srv:custom":
        query.answer()
        begin_custom_server(context, query.from_user.id, query.message)
        return
    if data == "tr:www" or data.startswith("tr:www:"):
        begin_www_port(query, context, int(data.rsplit(":", 1)[1]) if data.startswith("tr:www:") else None)
        return
    if data == "tr:retry":
        retry_traffic(query, context)
        return
    if data == "tr:servers":
        _show_traffic_servers(query)
        return
    if data.startswith("tr:server:"):
        in_background(_show_interfaces, query, int(data.rsplit(":", 1)[1]))
        return
    if data.startswith("tr:iface:"):
        _, _, server_ref, interface = data.split(":", 3)
        _run_traffic(query, context, server_ref, interface)


def _show_servers(query):
    """Menu Server Saya: daftar server, Kelola, Tambah (n/batas)."""
    servers = _servers_for(query.from_user.id)
    limit = get_server_limit(query.from_user.id)
    if not servers:
        query.answer()
        query.edit_message_text(
            f"Belum ada server (0/{limit}). Tambahkan server pertama Anda.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Tambah server", callback_data="srv:add")],
                                               dashboard_row()]))
        return
    keyboard = [[InlineKeyboardButton(f"🔌 {server['name']}", callback_data=f"srv:connect:{index}"),
                 InlineKeyboardButton("⚙️ Kelola", callback_data=f"srv:manage:{index}")]
                for index, server in enumerate(servers)]
    keyboard.append([InlineKeyboardButton("➕ Tambah server", callback_data="srv:add")])
    keyboard.append(dashboard_row())
    query.answer()
    query.edit_message_text(f"Server Saya ({len(servers)}/{limit}). Pilih server untuk dihubungkan:",
                            reply_markup=InlineKeyboardMarkup(keyboard))


def _show_server_manage(query, index):
    """Menu Kelola satu server: edit / hapus."""
    servers = _servers_for(query.from_user.id)
    if index >= len(servers):
        query.answer("Server tidak ditemukan.", show_alert=True)
        return
    server = servers[index]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Server", callback_data=f"srv:edit:{index}"),
         InlineKeyboardButton("🗑 Hapus Server", callback_data=f"srv:deleteask:{index}")],
        [InlineKeyboardButton(f"🌐 Port Web ({server.get('www_port') or DEFAULT_WWW_PORT})",
                              callback_data=f"tr:www:{index}")],
        [InlineKeyboardButton("⬅️ Daftar Server", callback_data="menu:servers")],
    ])
    query.answer()
    query.edit_message_text(
        f"Kelola server *{escape_md(server['name'])}*\nAlamat (API): `{server['ip']}`\n"
        f"Port web (grafik traffic): `{server.get('www_port') or DEFAULT_WWW_PORT}`\nPilih tindakan:",
        parse_mode="Markdown", reply_markup=keyboard)


def _delete_server(query, index):
    """Hapus server dari datauser dan putuskan sesi bila sedang dipakai."""
    users = load_user_data()
    record = users.get(str(query.from_user.id), {})
    servers = record.get("servers", [])
    if index >= len(servers):
        query.answer("Server tidak ditemukan.", show_alert=True)
        return
    name = servers.pop(index).get("name", "-")
    save_user_data(users)
    session = user_data_dict.get(query.from_user.id)
    if session and getattr(session, "server_name", None) == name:
        user_data_dict.pop(query.from_user.id, None)
    query.answer("Server dihapus.")
    query.edit_message_text(f"✅ Server *{escape_md(name)}* telah dihapus.", parse_mode="Markdown",
                            reply_markup=back_keyboard("menu:servers", "⬅️ Server Saya"))


def _ask_delete_server(query, index):
    """Konfirmasi hapus server."""
    servers = _servers_for(query.from_user.id)
    if index >= len(servers):
        query.answer("Server tidak ditemukan.", show_alert=True)
        return
    query.answer()
    query.edit_message_text(
        f"Hapus server *{escape_md(servers[index]['name'])}*? Tindakan ini tidak dapat dibatalkan.",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Ya, hapus", callback_data=f"srv:deleteconfirm:{index}"),
            InlineKeyboardButton("Batal", callback_data=f"srv:manage:{index}"),
        ]]))


def _connect_server(query, index):
    """Pakai server tersimpan sebagai sesi router aktif."""
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
    session.www_port = server.get("www_port")
    query.answer("Server tersambung.")
    query.edit_message_text(
        f"✅ Tersambung ke *{escape_md(server['name'])}*.\nPilih aksi:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📡 Monitor PPPoE", callback_data="menu:pppoe"),
             InlineKeyboardButton("📈 Monitor Traffic", callback_data="menu:traffic")],
            [InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")],
        ]))


def _show_traffic_servers(query):
    """Pilih server untuk Monitor Traffic."""
    servers = _servers_for(query.from_user.id)
    if not servers:
        query.answer("Tambahkan server terlebih dahulu.", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton(server["name"], callback_data=f"tr:server:{index}")]
                for index, server in enumerate(servers)]
    keyboard.append(dashboard_row())
    query.answer()
    query.edit_message_text("Pilih server untuk mengambil daftar interface:", reply_markup=InlineKeyboardMarkup(keyboard))


GRAPHING_GUIDE = (
    "📭 *Tools > Graphing di router masih kosong*, jadi belum ada interface yang bisa ditampilkan.\n\n"
    "Aktifkan dulu lewat Winbox:\n"
    "1. Buka *Tools > Graphing* → tab *Interface Rules* → tombol *+*\n"
    "2. *Interface*: `all` (atau pilih interface tertentu)\n"
    "3. *Allow Address*: `0.0.0.0/0` (atau IP publik bot)\n"
    "4. Centang *Store on Disk* → *OK*\n"
    "5. Pastikan *IP > Services > www* aktif (port default 80)\n\n"
    "Atau lewat Terminal:\n"
    "`/tool graphing interface add interface=all allow-address=0.0.0.0/0 store-on-disk=yes`\n\n"
    "Grafik mulai terisi ±5 menit setelah diaktifkan. Lalu buka lagi 📈 Monitor Traffic."
)


def _show_interfaces(query, index):
    """Daftar interface yang aktif di Tools > Graphing router."""
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
        connection = connect_router(server["ip"], server["username"], server["password"])
        interfaces = get_graphing_interfaces(connection)
    except RouterError as exc:
        query.answer()
        query.edit_message_text(f"{router_error_text(exc, server.get('name') or server['ip'], server['ip'])}\nSaldo tidak dipotong.",
                                parse_mode="Markdown", reply_markup=back_keyboard("tr:servers", "🖥 Ganti server"))
        return
    if not interfaces:
        query.answer()
        query.edit_message_text(GRAPHING_GUIDE, parse_mode="Markdown",
                                reply_markup=back_keyboard("tr:servers", "🖥 Ganti server"))
        return
    keyboard = [[InlineKeyboardButton(
        f"{item['name']} — {item['comment']}" if item.get("comment") else item["name"],
        callback_data=f"tr:iface:{server_ref}:{item['name']}")]
                for item in interfaces[:40]]
    keyboard.append([InlineKeyboardButton("🖥 Ganti server", callback_data="tr:servers")] + dashboard_row())
    query.answer()
    query.edit_message_text("Pilih interface yang aktif di Tools > Graphing:", reply_markup=InlineKeyboardMarkup(keyboard))


def _run_traffic(query, context, server_ref, interface):
    """Set interface pilihan lalu jalankan run_traffic_monitoring."""
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
        session.server_name = server["name"]
        session.www_port = server.get("www_port")
    session.interface = interface
    query.answer("Memproses traffic...")
    in_background(run_traffic_monitoring, context, query.from_user.id, query.message.chat_id, session)


def _servers_for(user_id):
    """Daftar Server Saya milik user."""
    return load_user_data().get(str(user_id), {}).get("servers", [])


def _require_connection(query):
    """True bila user sudah punya sesi router."""
    session = user_data_dict.get(query.from_user.id)
    # A session cleared after a failed login has no IP: ask for a server again.
    return bool(session and session.ip_address)


def _prompt_server_before_pppoe(query):
    """Minta user memilih server sebelum Monitor PPPoE."""
    servers = _servers_for(query.from_user.id)
    if not servers:
        query.answer()
        query.edit_message_text(
            "Sebelum Monitor PPPoE, tambahkan lalu pilih server di Server Saya.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🖥 Server Saya", callback_data="menu:servers")],
                                               dashboard_row()]))
        return
    keyboard = [[InlineKeyboardButton(server["name"], callback_data=f"srv:connect:{index}")]
                for index, server in enumerate(servers)]
    keyboard.append(dashboard_row())
    query.answer()
    query.edit_message_text(
        "⚠️ Pilih server terlebih dahulu di Server Saya, lalu jalankan Monitor PPPoE.",
        reply_markup=InlineKeyboardMarkup(keyboard))


def _set_cleanup(query, minutes):
    """Simpan pilihan hapus-otomatis dashboard (menit)."""
    users = load_user_data()
    record = users.get(str(query.from_user.id))
    if not record:
        query.answer("Anda belum terdaftar.", show_alert=True)
        return
    record["chat_cleanup_minutes"] = minutes
    save_user_data(users)
    label = "nonaktif" if not minutes else f"{minutes} menit"
    query.answer("Pengaturan disimpan.")
    query.edit_message_text(f"Pembersihan otomatis pesan bot: {label}.", reply_markup=home_keyboard())


def _admin_callback(update, context):
    """Router tombol admin:* (cek is_staff dulu)."""
    query = update.callback_query
    if not is_staff(query.from_user.id):
        query.answer("Akses admin ditolak.", show_alert=True)
        return
    action = query.data.split(":", 1)[1]
    if action == "testing":
        _ensure_staff_test_record(query.from_user)
        context.user_data["user_testing_mode"] = True
        query.answer("Mode user testing aktif.")
        _send_user_dashboard(update, context, testing=True)
        return
    if action == "exittesting":
        context.user_data.pop("user_testing_mode", None)
        query.answer("Keluar dari mode user testing.")
        _send_admin_dashboard(update, context)
        return
    if action == "qris":
        begin_qris_upload(query, context)
        return
    if action == "pkg":
        packages_menu(query)
        return
    if action.startswith("pkg:"):
        package_callback(query, context, action)
        return
    if action == "refunds":
        pending_refunds_menu(query)
        return
    if action == "trial":
        trial_menu(query)
        return
    if action.startswith("trialmode:"):
        set_trial_mode_callback(query, action.split(":", 1)[1])
        return
    if action == "settings":
        admin_settings_menu(query)
        return
    if action.startswith("set:"):
        start_admin_input(query, context, action.split(":", 1)[1])
        return
    if action == "users":
        users_menu(query)
        return
    if action == "registrations":
        pending_registrations_menu(query)
        return
    if action == "topups":
        pending_topups_menu(query)
        return
    if action == "manualtopup":
        begin_manual_topup(query, context)
        return
    if action == "manualcancel":
        clear_pending_inputs(context)
        query.answer("Tambah saldo dibatalkan.")
        query.edit_message_text("Tambah saldo dibatalkan.", reply_markup=home_keyboard())
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
            "account_type": "admin",
        }
        save_user_data(users)


def _input_wizard_callback(query, context):
    """Tombol ✖️ Batal / ↩️ Reset di form."""
    parts = query.data.split(":")
    if parts[1] == "cancel":
        if context.user_data.get("onboarding_step"):
            from handlers.handler_onboarding import remove_reply_keyboard
            remove_reply_keyboard(context.bot, query.message.chat_id)
        clear_pending_inputs(context)
        query.answer("Input dibatalkan.")
        query.edit_message_text("Input dibatalkan.", reply_markup=home_keyboard())
        return
    kind = parts[2]
    context.user_data.pop("server_unverified", None)
    query.answer("Input diulang.")
    if kind == "stored":
        context.user_data.pop("custom_server_wizard", None)
        context.user_data["server_wizard"] = {"step": "name"}
        query.edit_message_text("Nama server apa yang ingin disimpan?", reply_markup=wizard_keyboard("stored"))
    else:
        context.user_data.pop("server_wizard", None)
        context.user_data["custom_server_wizard"] = {"step": "ip"}
        query.edit_message_text(
            "Masukkan IP atau hostname/DDNS MikroTik (port API lain: `host:port`). Data ini hanya dipakai untuk sesi saat ini dan tidak disimpan.",
            reply_markup=wizard_keyboard("custom"))
