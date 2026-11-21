# Workflow Graphify untuk Pengembangan Hemat Konteks

Graphify menyimpan peta hubungan kode di `graphify-out/graph.json`. Setelah graph tersedia, gunakan query sebelum membuka banyak file satu per satu.

## Saat kode belum berubah

```powershell
graphify query "Bagaimana alur topup saldo dan approval admin?"
graphify query "Apa yang memanggil monitoring traffic?"
graphify path "main()" "check_client_status_and_notify()"
```

Gunakan hasil graph untuk menentukan file mana yang perlu diperiksa. Ini mengurangi pencarian berulang dan konteks yang tidak relevan.

## Setelah kode berubah

```powershell
graphify . --update
```

Perintah ini memperbarui graph secara inkremental. Jika graph belum ada:

```powershell
graphify .
```

## Aturan kerja

1. Jalankan query Graphify untuk pertanyaan alur/relasi kode.
2. Baca source hanya pada file yang dirujuk graph atau diperlukan untuk memperbaiki bug.
3. Setelah perubahan struktur besar, jalankan `graphify . --update`.
4. Jangan commit `graphify-out/` kecuali tim memang ingin membagikan graph tersebut.

## Keterbatasan

Graphify membaca struktur impor, fungsi, dan panggilan. Nilai hard-code, kondisi runtime RouterOS, dan isi JSON tetap harus diverifikasi di source atau lingkungan uji.
