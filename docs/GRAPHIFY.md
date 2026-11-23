# Bekerja dengan Graphify

Graphify memetakan hubungan kode (impor, fungsi, panggilan) sehingga pertanyaan seperti "siapa yang memanggil X?" atau "bagaimana alur Y?" bisa dijawab tanpa membuka file satu per satu — hemat waktu dan hemat konteks untuk AI agent.

Project ini punya **dua** graph:

| | Graph lokal (CLI) | Graph cloud (MCP Graphify) |
|---|---|---|
| Lokasi | `graphify-out/graph.json` (tidak di-commit) | Index repo `AlYusril19/monitoring-ppp-public`, branch `master` |
| Diperbarui | `graphify . --update` | Otomatis setelah `git push` |
| Dipakai oleh | Anda / agent di komputer ini | Claude & agent yang terhubung ke Graphify |
| Catatan | Selalu sesuai kode lokal | Paket Free: dokumen hanya `README.md` yang diindeks; kode diindeks penuh |

## 1. Siklus kerja

```text
sebelum mengubah  → graphify query / path       (tahu file mana yang terlibat)
mengubah kode     → buka hanya file yang dirujuk graph
sesudah mengubah  → graphify . --update          (graph lokal)
                    git push                     (graph cloud)
```

## 2. Perintah dasar (lokal)

```powershell
graphify .                      # bangun graph pertama kali
graphify . --update             # perbarui setelah kode berubah
graphify query "<pertanyaan>"   # tanya bebas
graphify path "<A>" "<B>"       # jalur panggilan dari A ke B
```

## 3. Query siap pakai

Pakai nama fungsi persis (lihat [`REFERENSI-MODUL.md`](REFERENSI-MODUL.md)) agar node yang tepat ditemukan.

**Routing**
```powershell
graphify query "Fungsi apa saja yang dipanggil menu_callback dan berdasarkan prefix apa?"
graphify query "Form apa saja yang ada di WIZARDS pada handle_input?"
graphify query "Fungsi apa yang dibuka handler_command_redirect lewat QueryFromMessage?"
```

**Pengaturan admin**
```powershell
graphify query "Siapa saja yang memanggil apply_admin_input dan get_server_limit?"
graphify query "Bagaimana DEFAULT_SETTINGS dipakai load_settings dan get_monitoring_config?"
```

**Saldo & billing**
```powershell
graphify query "Siapa saja yang memanggil charge_user?"
graphify path "capture_payment_proof" "add_transaction"
graphify query "Bagaimana alur topup: wallet_callback, capture_payment_proof, topup_approval_callback?"
```

**Monitoring**
```powershell
graphify path "main" "check_client_status_and_notify"
graphify query "Bagaimana alert_level, alert_stage, dan alert_window_start menentukan notifikasi otomatis?"
graphify query "Siapa yang memanggil send_down_report?"
```

**Chat ringkas**
```powershell
graphify query "Bagaimana before_update, after_update, dan keep_messages di chat_tracker bekerja?"
graphify query "Fungsi mana yang memakai keep_messages?"
```

**Analisis dampak sebelum refactor**
```powershell
graphify query "Apa saja yang bergantung pada load_user_data dan save_user_data?"
graphify query "Fungsi mana yang tidak dipanggil dari mana pun?"
```

## 4. Graph cloud (MCP)

Di Claude/agent dengan konektor Graphify: repository `AlYusril19/monitoring-ppp-public`. Alat yang berguna:
`graphify_find` (definisi), `graphify_callers` (pemanggil), `graphify_impact` (dampak perubahan), `query_graph` (pertanyaan bebas), `graphify_file_neighbors` (ketergantungan file).

Hasil cloud mencantumkan `commitSha`. Bila berbeda dengan `git rev-parse HEAD` lokal, baca file yang berubah sejak commit itu secara langsung.

## 5. Aturan

1. Pertanyaan alur/relasi → tanya graph dulu.
2. Baca source hanya untuk file yang dirujuk graph atau yang akan diubah.
3. Setelah menambah/memindah file, fungsi, atau impor → `graphify . --update`.
4. Jangan edit `graphify-out/` manual dan jangan commit (sudah di `.gitignore`).

## 6. Yang tidak terlihat di graph

- **`callback_data`**: tombol → handler lewat `data == "..."` / `startswith` di `menu_callback`, bukan panggilan fungsi → pakai [`ALUR-FITUR.md` §2](ALUR-FITUR.md#2-tombol-callback_data).
- **`COMMANDS` di `main.py`**: pemetaan command → fungsi berupa dict → [`ALUR-FITUR.md` §1](ALUR-FITUR.md#1-command).
- **Handler group** -1/1 (`chat_tracker`) berjalan untuk setiap update tanpa panggilan eksplisit.
- Isi JSON & nilai default → [`DATA.md`](DATA.md); perilaku RouterOS → uji di router.
