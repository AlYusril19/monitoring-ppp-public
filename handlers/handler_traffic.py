from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import is_staff
from configs.billing import charge_user
from configs.data_json_user import get_registered_username, load_user_data, save_user_data
from configs.format_rupiah import format_rupiah
from configs.mikrotik_function import DEFAULT_WWW_PORT, graph_url
from configs.navigation import (cancel_keyboard, dashboard_row, home_keyboard, session_action_keyboard,
                                topup_keyboard)
from configs.chat_tracker import in_background, keep_messages
from configs.get_current_time import get_current_time
from configs.send_message import bot_log, chat_log, escape_md, fetch_image, send_message
from models.userdata import user_data_dict


def monitoring_command_handler(update, context):
    """/traffic: kirim grafik untuk interface yang sudah dipilih lewat tombol."""
    user_id = update.effective_user.id
    user_data = user_data_dict.get(user_id)

    if str(user_id) not in load_user_data() and not is_staff(user_id):
        update.effective_message.reply_text("Anda belum terdaftar, silahkan /start untuk mengajukan registrasi.",
                                            reply_markup=home_keyboard())
        return
    if user_data is None or user_data.interface is None:
        update.effective_message.reply_text("Pilih server dan interface dari tombol 📈 Monitor Traffic di Dashboard.",
                                            reply_markup=home_keyboard())
        return
    in_background(run_traffic_monitoring, context, user_id, update.effective_chat.id, user_data)


def run_traffic_monitoring(context, user_id, chat_id, user_data):
    """Fetch the RouterOS graph first; charge only when the image was retrieved."""
    username_telegram = escape_md(get_registered_username(user_id))
    interface = user_data.interface
    bot = context.bot
    waiting = send_message(bot, chat_id, "⏳ Mengambil grafik...")

    www_port = getattr(user_data, "www_port", None) or DEFAULT_WWW_PORT
    image = fetch_image(graph_url(user_data.ip_address, interface, www_port))
    if image is None:
        try:
            waiting.delete()
        except Exception:
            pass
        # The interface list came from the API, so Graphing is on; the web (www) side is the problem.
        send_message(
            bot, chat_id,
            f"🖼 Grafik *{escape_md(interface)}* tidak dapat diambil dari web router (port *{www_port}*).\n"
            "Daftar interface sudah muncul, berarti Tools > Graphing aktif. Kemungkinan penyebab:\n"
            "• Port *www* router (IP > Services > www) bukan 80 atau di-NAT ke port lain → tekan 🌐 Atur Port Web\n"
            "• Service *www* dimatikan\n"
            "• *Allow Address* di Tools > Graphing > Interface Rules tidak mengizinkan IP bot (isi `0.0.0.0/0`)\n"
            "• Grafik baru dibuat; tunggu ±5 menit setelah Graphing diaktifkan\n\n"
            "💰 Saldo tidak dipotong.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Atur Port Web", callback_data="tr:www"),
                 InlineKeyboardButton("🔁 Coba Lagi", callback_data="tr:retry")],
                dashboard_row()]))
        return

    success, start_cost, remaining = charge_user(user_id, "traffic")
    if not success:
        send_message(bot, chat_id, "Mohon maaf saldo anda tidak mencukupi, silahkan melakukan topup saldo",
                     reply_markup=topup_keyboard())
        return

    server = getattr(user_data, "server_name", None) or user_data.ip_address
    caption = f"📈 Traffic {interface} · {server}\n🕒 {get_current_time()}\nBiaya: Rp{start_cost}"
    with keep_messages():  # the graph stays in the chat as a log
        bot.send_photo(chat_id=chat_id, photo=image, caption=caption)
    try:
        bot.delete_message(chat_id=waiting.chat_id, message_id=waiting.message_id)
    except Exception:
        pass
    send_message(bot_log, chat_log, f"user *{username_telegram}* Monitoring LB {escape_md(interface)}\n"
                                    f"Sisa saldo User {format_rupiah(remaining or 0)}")
    user_data.interface = None
    bot.send_message(chat_id=chat_id, text="Pilih aksi berikutnya:", reply_markup=session_action_keyboard())


def _stored_server_index(user_id, session):
    """Index Server Saya yang sedang dipakai sesi (cocok nama + alamat), atau None."""
    for index, server in enumerate(load_user_data().get(str(user_id), {}).get("servers", [])):
        if server.get("name") == session.server_name and server.get("ip") == session.ip_address:
            return index
    return None


def begin_www_port(query, context, index=None):
    """Tombol 🌐 Atur Port Web: form port service www untuk grafik (index = Server Saya, None = sesi aktif)."""
    user_id = query.from_user.id
    session = user_data_dict.get(user_id)
    if index is None:
        if not session or not session.ip_address:
            query.answer("Pilih server terlebih dahulu.", show_alert=True)
            return
        name, port = session.server_name or session.ip_address, getattr(session, "www_port", None)
    else:
        servers = load_user_data().get(str(user_id), {}).get("servers", [])
        if index >= len(servers):
            query.answer("Server tidak ditemukan.", show_alert=True)
            return
        name, port = servers[index]["name"], servers[index].get("www_port")
    context.user_data["www_port_input"] = {"index": index}
    query.answer()
    query.edit_message_text(
        f"🌐 *Port Web* · *{escape_md(name)}*\n"
        "Grafik traffic diambil dari service *www* router (IP > Services > www). "
        "Masukkan port-nya, mis. `8080` (port publik bila di-NAT).\n\n"
        f"Saat ini: *{port or DEFAULT_WWW_PORT}*. Ketik `80` untuk kembali ke default.",
        parse_mode="Markdown", reply_markup=cancel_keyboard())


def handle_www_port_input(update, context):
    """Form port web: simpan ke Server Saya (bila tersimpan) dan ke sesi aktif."""
    state = context.user_data.get("www_port_input")
    if state is None:
        return False
    text = update.effective_message.text.strip()
    if not text.isdigit() or not 1 <= int(text) <= 65535:
        update.effective_message.reply_text("Port harus angka 1-65535. Masukkan ulang atau /cancel.",
                                            reply_markup=cancel_keyboard())
        return True
    port = int(text)
    user_id = update.effective_user.id
    session = user_data_dict.get(user_id)
    index = state.get("index")
    if index is None and session:
        index = _stored_server_index(user_id, session)  # None for Server Custom (session only)
    users = load_user_data()
    servers = users.get(str(user_id), {}).get("servers", [])
    if index is not None and index < len(servers):
        if port == DEFAULT_WWW_PORT:
            servers[index].pop("www_port", None)
        else:
            servers[index]["www_port"] = port
        save_user_data(users)
        if session and session.server_name == servers[index].get("name"):
            session.www_port = port
    elif session:
        session.www_port = port
    context.user_data.pop("www_port_input", None)
    rows = []
    if session and session.interface:
        rows.append([InlineKeyboardButton("🔁 Coba Ambil Grafik", callback_data="tr:retry")])
    rows.append(dashboard_row())
    update.effective_message.reply_text(f"✅ Port web disimpan: {port}.", reply_markup=InlineKeyboardMarkup(rows))
    return True


def retry_traffic(query, context):
    """Tombol 🔁 Coba Lagi: ambil ulang grafik interface terakhir."""
    session = user_data_dict.get(query.from_user.id)
    if not session or not session.ip_address or not session.interface:
        query.answer("Pilih server dan interface lagi dari 📈 Monitor Traffic.", show_alert=True)
        return
    query.answer("Memproses traffic...")
    in_background(run_traffic_monitoring, context, query.from_user.id, query.message.chat_id, session)
