"""Admin settings: one implementation used by both /commands and buttons.

Buttons start a short text input (context.user_data["admin_input"]); the same
apply_* functions are used by the /set... commands, so the rules (who may
change what, value validation) exist only once.
"""
from collections import namedtuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from configs.app_settings import (PRICE_LABELS, TRIAL_MODES, get_custom_topup_range,
                                  get_global_excluded_profiles, get_max_servers, get_refund_percent,
                                  get_registration_limits, get_role, get_topup_amounts, get_topup_package,
                                  get_trial_balance, get_trial_mode, is_staff, is_superadmin, load_settings,
                                  price_summary, set_custom_topup_range, set_global_excluded_profiles,
                                  set_max_servers, set_price, set_refund_percent, set_registration_limit,
                                  set_role, set_trial_balance, set_trial_mode, update_topup_package)
from configs.navigation import back_keyboard, cancel_keyboard, home_keyboard
from configs.send_message import escape_md

# A result that needs more than text: own keyboard and/or the next photo as QRIS.
AdminReply = namedtuple("AdminReply", "text keyboard qris_upload", defaults=(None, None))

# key -> (prompt shown to the admin, superadmin only?)
# Keys with a parameter are stored as "<key>:<param>" (e.g. "pkg_edit:5000").
ADMIN_INPUTS = {
    "price:testppp": ("Masukkan harga baru *Cek PPPoE* (angka, contoh 125):", True),
    "price:traffic": ("Masukkan harga baru *Monitor Traffic* (angka, contoh 50):", True),
    "price:notify": ("Masukkan harga baru *Notifikasi down* (angka, contoh 250):", True),
    "trial_balance": ("Masukkan nominal saldo trial untuk user baru (angka, 0 = tanpa trial):", True),
    "reg_limit": ("Masukkan batas *pengajuan registrasi per jam* dari semua user (angka, 0 = tanpa batas):", True),
    "reg_cooldown": ("Masukkan *jeda (jam)* sebelum user yang ditolak boleh mengajukan lagi (angka, 0 = tanpa jeda):", True),
    "refund_percent": ("Masukkan *persentase refund* saldo berbayar saat akun dihapus (0–100).\n"
                       "Saldo trial tidak pernah direfund.", True),
    "max_servers": ("Masukkan batas jumlah server per user (angka, minimal 1):", True),
    "pkg_new": ("Masukkan *nominal* paket saldo baru (angka, contoh `3000`).\n"
                "Setelah itu kirim foto QRIS statik untuk nominal tersebut.", True),
    "pkg_edit": ("Masukkan nominal baru untuk paket ini (angka). QRIS paket tidak berubah:", True),
    "custom_range": ("Masukkan batas nominal bebas `min-max`.\nContoh: `10000-1000000`", True),
    "excluded_profiles": ("Masukkan profile PPPoE yang dikecualikan untuk *semua user*, pisahkan koma.\n"
                          "Contoh: `expired,pribadi-home`. Ketik `-` untuk mengosongkan.", True),
    "role": ("Masukkan `<user_id> <operator|admin|user>`\nContoh: `123456789 operator`", True),
    "archive": ("Masukkan User ID yang akan *diarsipkan* (monitoring otomatis berhenti):", False),
    "activate": ("Masukkan User ID yang akan *diaktifkan* kembali:", False),
    "delete_user": ("Masukkan User ID yang akan *dihapus*. Rincian refund ditampilkan sebelum konfirmasi.", True),
}


def _input_spec(key):
    """(prompt, superadmin_only) untuk key, termasuk key berparameter seperti 'pkg_edit:5000'."""
    if key in ADMIN_INPUTS:
        return ADMIN_INPUTS[key]
    base = key.split(":", 1)[0]
    return ADMIN_INPUTS.get(base) if base in {"pkg_edit"} else None


# ---------------------------------------------------------------- shared rules
def _parse_amount(text, minimum=0):
    """Ubah teks angka ('5.000', '5000') menjadi int dan cek nilai minimal."""
    try:
        amount = int(str(text).strip().replace(".", "").replace(",", ""))
    except ValueError:
        raise ValueError("Nominal harus berupa angka.")
    if amount < minimum:
        raise ValueError(f"Nominal minimal {minimum}.")
    return amount


def apply_admin_input(user_id, key, value):
    """Validate and save one setting. Returns text or AdminReply; raises ValueError/PermissionError."""
    spec = _input_spec(key)
    if spec is None:
        raise ValueError("Pengaturan tidak dikenal.")
    needs_superadmin = spec[1]
    if needs_superadmin and not is_superadmin(user_id):
        raise PermissionError("Hanya superadmin yang dapat mengubah pengaturan ini.")
    if not needs_superadmin and not is_staff(user_id):
        raise PermissionError("Hanya admin/operator.")
    value = value.strip()
    if key.startswith("price:"):
        feature = key.split(":", 1)[1]
        amount = _parse_amount(value)
        set_price(feature, amount)
        return f"✅ Harga {PRICE_LABELS[feature]} sekarang Rp{amount:,}."
    if key == "trial_balance":
        amount = _parse_amount(value)
        set_trial_balance(amount)
        return f"✅ Saldo trial user baru: Rp{amount:,}."
    if key in {"reg_limit", "reg_cooldown"}:
        amount = _parse_amount(value)
        set_registration_limit("hourly_limit" if key == "reg_limit" else "reject_cooldown_hours", amount)
        label = "Batas pengajuan per jam" if key == "reg_limit" else "Jeda setelah ditolak (jam)"
        return f"✅ {label}: {amount or 'tanpa batas'}."
    if key == "refund_percent":
        set_refund_percent(_parse_amount(value))
        return f"✅ Refund saldo saat akun dihapus: {get_refund_percent()}% dari saldo berbayar."
    if key == "max_servers":
        amount = _parse_amount(value, minimum=1)
        set_max_servers(amount)
        return f"✅ Batas server per user sekarang {amount}. Server yang sudah ada tidak dihapus."
    if key == "pkg_new":
        amount = _parse_amount(value, minimum=1)
        if get_topup_package(amount):
            raise ValueError(f"Paket Rp{amount:,} sudah ada; pilih paketnya untuk mengganti QRIS.")
        return AdminReply(f"Nominal Rp{amount:,}. Sekarang kirim *foto QRIS statik* untuk paket ini.",
                          cancel_keyboard(), f"new:{amount}")
    if key.startswith("pkg_edit:"):
        old = int(key.split(":", 1)[1])
        amount = _parse_amount(value, minimum=1)
        update_topup_package(old, new_amount=amount)
        return f"✅ Paket Rp{old:,} diubah menjadi Rp{amount:,} (QRIS tetap). Pastikan QRIS statiknya sesuai."
    if key == "custom_range":
        parts = value.replace(" ", "").split("-")
        if len(parts) != 2:
            raise ValueError("Format: min-max, contoh 10000-1000000")
        set_custom_topup_range(_parse_amount(parts[0], 1), _parse_amount(parts[1], 1))
        minimum, maximum = get_custom_topup_range()
        return f"✅ Nominal bebas: Rp{minimum:,}–Rp{maximum:,}."
    if key == "excluded_profiles":
        set_global_excluded_profiles([] if value == "-" else value)
        return "✅ Profile dikecualikan untuk semua user: " + (", ".join(get_global_excluded_profiles()) or "tidak ada")
    if key == "role":
        parts = value.split()
        if len(parts) != 2 or not parts[0].isdigit():
            raise ValueError("Format: <user_id> <operator|admin|user>")
        set_role(int(parts[0]), parts[1].lower())
        return f"✅ Role {parts[0]} sekarang {parts[1].lower()}."
    if key in {"archive", "activate"}:
        from handlers.handler_user import set_user_active
        return set_user_active(value, key == "activate")
    if key == "delete_user":
        from handlers.handler_refund import deletion_notice, refund_quote
        if not value.isdigit():
            raise ValueError("User ID harus angka.")
        quote = refund_quote(value)
        if quote is None:
            raise ValueError(f"User {value} tidak ditemukan.")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑 Ya, hapus user", callback_data=f"users:delete:{value}"),
            InlineKeyboardButton("Batal", callback_data="admin:users")]])
        return AdminReply(f"Hapus user *{escape_md(quote['name'])}* (ID {value})?\n\n{deletion_notice(quote)}\n\n"
                          "User akan diberi tahu beserta rincian refund.", keyboard)
    raise ValueError("Pengaturan tidak dikenal.")


# ---------------------------------------------------------------- button menu
def settings_text(user_id):
    """Ringkasan semua pengaturan saat ini (Markdown)."""
    settings = load_settings()
    minimum, maximum = get_custom_topup_range()
    return (
        "⚙️ *Pengaturan Layanan*\n"
        f"Role Anda: {get_role(user_id)}\n\n"
        f"*Harga*\n{price_summary()}\n\n"
        f"Saldo trial: Rp{get_trial_balance():,} ({TRIAL_MODES[get_trial_mode()].split(' (')[0]})\n"
        f"Refund saldo saat hapus akun: {get_refund_percent()}% dari saldo berbayar\n"
        f"Batas server per user: {get_max_servers()}\n"
        "Paket topup: " + (", ".join(f"Rp{a:,}" for a in get_topup_amounts()) or "-") + "\n"
        f"Nominal bebas: Rp{minimum:,}–Rp{maximum:,}\n"
        "Profile dikecualikan (semua user): " + (escape_md(", ".join(get_global_excluded_profiles())) or "tidak ada") + "\n"
        f"Role admin/operator: {len(settings['roles'])} akun")


def admin_settings_menu(query):
    """Menu ⚙️ Harga & Role; tombol ubah hanya untuk superadmin."""
    rows = []
    if is_superadmin(query.from_user.id):
        rows = [
            [InlineKeyboardButton("💲 Cek PPPoE", callback_data="admin:set:price:testppp"),
             InlineKeyboardButton("💲 Traffic", callback_data="admin:set:price:traffic"),
             InlineKeyboardButton("💲 Notifikasi", callback_data="admin:set:price:notify")],
            [InlineKeyboardButton("💸 Refund %", callback_data="admin:set:refund_percent"),
             InlineKeyboardButton("🖥 Batas Server", callback_data="admin:set:max_servers")],
            [InlineKeyboardButton("💳 Paket & QRIS", callback_data="admin:pkg"),
             InlineKeyboardButton("👥 Profile Global", callback_data="admin:set:excluded_profiles")],
            [InlineKeyboardButton("🛡 Atur Role", callback_data="admin:set:role")],
        ]
    rows.append([InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(settings_text(query.from_user.id), parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(rows))


def trial_menu(query):
    """Menu 🎁 Trial & Registrasi (di 👥 Data User): ketentuan trial dan anti registrasi massal."""
    limits = get_registration_limits()
    mode = get_trial_mode()
    text = (
        "🎁 *Ketentuan Trial & Registrasi*\n"
        f"Saldo trial: *Rp{get_trial_balance():,}*\n"
        f"Mode: *{TRIAL_MODES[mode]}*\n\n"
        "*Aturan tetap (anti akun massal)*\n"
        "• Nomor wajib dibagikan lewat tombol kontak Telegram (milik akun itu sendiri)\n"
        "• Satu trial per nomor telepon dan per akun Telegram, selamanya (tetap tercatat walau akun dihapus)\n"
        "• Nomor yang sudah dipakai akun lain tidak mendapat trial dan ditandai ⚠️\n"
        "• Saldo trial tidak pernah direfund sebagai uang\n\n"
        f"Batas pengajuan per jam: *{limits['hourly_limit'] or 'tanpa batas'}*\n"
        f"Jeda setelah ditolak: *{limits['reject_cooldown_hours'] or 'tanpa jeda'}"
        f"{' jam' if limits['reject_cooldown_hours'] else ''}*")
    rows = []
    if is_superadmin(query.from_user.id):
        rows = [
            [InlineKeyboardButton("🎁 Nominal Trial", callback_data="admin:set:trial_balance")],
            [InlineKeyboardButton(("● " if mode == key else "") + label.split(" (")[0],
                                  callback_data=f"admin:trialmode:{key}") for key, label in TRIAL_MODES.items()],
            [InlineKeyboardButton("⏱ Batas/Jam", callback_data="admin:set:reg_limit"),
             InlineKeyboardButton("⏳ Jeda Ditolak", callback_data="admin:set:reg_cooldown")],
        ]
    rows.append([InlineKeyboardButton("⬅️ Data User", callback_data="admin:users"),
                 InlineKeyboardButton("🏠 Dashboard", callback_data="nav:home")])
    query.answer()
    query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))


def set_trial_mode_callback(query, mode):
    """Tombol admin:trialmode:<manual|auto|off> (superadmin)."""
    if not is_superadmin(query.from_user.id):
        query.answer("Hanya superadmin.", show_alert=True)
        return
    try:
        set_trial_mode(mode)
    except ValueError as exc:
        query.answer(str(exc), show_alert=True)
        return
    trial_menu(query)


def start_admin_input(query, context, key):
    """Buka form untuk satu key ADMIN_INPUTS setelah cek hak akses."""
    spec = _input_spec(key)
    if spec is None:
        query.answer("Pengaturan tidak dikenal.", show_alert=True)
        return
    prompt, needs_superadmin = spec
    allowed = is_superadmin(query.from_user.id) if needs_superadmin else is_staff(query.from_user.id)
    if not allowed:
        query.answer("Akses ditolak.", show_alert=True)
        return
    if key.startswith("pkg_edit:"):
        prompt = f"Paket saat ini: *Rp{int(key.split(':', 1)[1]):,}*.\n" + prompt
    context.user_data["admin_input"] = key
    query.answer()
    query.edit_message_text(prompt + "\n\nKetik /cancel untuk membatalkan.", parse_mode="Markdown",
                            reply_markup=cancel_keyboard())


def handle_admin_input(update, context):
    """Consume the answer to an admin setting prompt. Returns True if consumed."""
    key = context.user_data.get("admin_input")
    if not key:
        return False
    try:
        result = apply_admin_input(update.effective_user.id, key, update.effective_message.text)
    except PermissionError as exc:
        context.user_data.pop("admin_input", None)
        update.effective_message.reply_text(str(exc), reply_markup=home_keyboard())
        return True
    except ValueError as exc:
        update.effective_message.reply_text(f"{exc}\nMasukkan ulang atau /cancel.", reply_markup=cancel_keyboard())
        return True
    context.user_data.pop("admin_input", None)
    if isinstance(result, AdminReply):
        if result.qris_upload:
            context.user_data["qris_upload"] = result.qris_upload
        update.effective_message.reply_text(result.text, parse_mode="Markdown",
                                            reply_markup=result.keyboard or _after_input_keyboard(key))
        return True
    update.effective_message.reply_text(result, reply_markup=_after_input_keyboard(key))
    return True


def _after_input_keyboard(key):
    """After saving, go back to the menu the setting came from."""
    if key in {"archive", "activate", "delete_user"}:
        return back_keyboard("admin:users", "⬅️ Data User")
    if key in {"trial_balance", "reg_limit", "reg_cooldown"}:
        return back_keyboard("admin:trial", "⬅️ Trial & Registrasi")
    if key.startswith("pkg_") or key == "custom_range":
        return back_keyboard("admin:pkg", "⬅️ Paket Saldo")
    return back_keyboard("admin:settings", "⬅️ Pengaturan")


# ---------------------------------------------------------------- /commands
def _run_command(update, key, usage, args):
    """Jalankan apply_admin_input dari /command dan balas hasil/kesalahannya."""
    reply = update.effective_message.reply_text
    if not args:
        reply(usage, reply_markup=home_keyboard())
        return
    try:
        result = apply_admin_input(update.effective_user.id, key, " ".join(args))
        reply(result.text if isinstance(result, AdminReply) else result, reply_markup=home_keyboard())
    except (PermissionError, ValueError) as exc:
        reply(f"{exc}\n{usage}", reply_markup=home_keyboard())


def settings_command(update, context):
    """/settings: tampilkan ringkasan pengaturan + daftar command."""
    update.effective_message.reply_text(
        settings_text(update.effective_user.id) + "\n\nUbah lewat Dashboard Admin (⚙️ Harga & Role, "
        "💳 Paket & QRIS, 👥 Data User → 🎁 Trial & Registrasi), atau:\n"
        "/setprice <testppp|traffic|notify> <nominal>\n/settrial <nominal>\n/setmaxserver <jumlah>\n"
        "/setrole <user\\_id> <operator|admin|user>\n/setqris — QRIS nominal bebas",
        parse_mode="Markdown", reply_markup=home_keyboard())


def set_price_command(update, context):
    """/setprice <fitur> <nominal>."""
    args = context.args or []
    usage = "Gunakan: /setprice <testppp|traffic|notify> <nominal>"
    if len(args) != 2 or args[0] not in PRICE_LABELS:
        update.effective_message.reply_text(usage, reply_markup=home_keyboard())
        return
    _run_command(update, f"price:{args[0]}", usage, args[1:])


def set_role_command(update, context):
    """/setrole <user_id> <role>."""
    _run_command(update, "role", "Gunakan: /setrole <user_id> <operator|admin|user>", context.args or [])


def set_trial_command(update, context):
    """/settrial <nominal>."""
    _run_command(update, "trial_balance", "Gunakan: /settrial <nominal>", context.args or [])


def set_max_server_command(update, context):
    """/setmaxserver <jumlah>."""
    _run_command(update, "max_servers", "Gunakan: /setmaxserver <jumlah>", context.args or [])
