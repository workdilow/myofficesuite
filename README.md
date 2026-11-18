# Ruangkerja

Workspace lokal Writer, Spreadsheet, Slides, PDF, dan asisten AI. Versi `0.3.0-dev.43` membangun ulang host dari snapshot UI dev.42 dengan CLI Craft yang terpisah.

## Jalankan

Perlu Python 3.10 atau lebih baru. Host tidak memerlukan paket Python tambahan.

```sh
python3 host.py
```

Buka [Ruangkerja di perangkat ini](http://127.0.0.1:4173). Gunakan alamat tersebut agar pemeriksaan origin sesuai. Unggahan diproses di direktori sementara dan dibatasi 64 MiB. Halaman juga bisa dibuka sebagai demo statis. Dokumen TXT/MD, CSV/TSV, dan teks shape pada PPTX dapat diproses tanpa memasang CLI.

Pasang binary upstream `wordcraft-cli`, `gridcraft-cli`, `deckcraft-cli`, dan `pdfcraft-cli` di `PATH`. Ikuti petunjuk build masing-masing repo pada revisi di [ENGINE_PINS.md](ENGINE_PINS.md). Host membaca status CLI dari `PATH` dan melaporkannya lewat `GET /api/engine/capabilities`.

| Area | Alur yang tersedia | Batas |
| --- | --- | --- |
| Writer | Buka, edit, dan unduh teks. WordCraft mengekstrak teks format Office dan membuat dokumen baru dari teks hasil edit. | Ekspor berbasis teks. DOC perlu dikonversi ke DOCX sebelum disimpan. |
| Spreadsheet | Preview 50 × 20, edit sel, statistik lokal dari alamat sumber. GridCraft menambah preview Office, hasil formula, simpan XLSX, dan chart. | CSV/TSV tanpa GridCraft mendukung input literal. XLS/ODS perlu dikonversi ke XLSX untuk penyimpanan edit. |
| Slides | Preview/edit teks shape, render dan outline dengan DeckCraft. Outline dapat diunduh sebagai deck baru atau ditambahkan ke salinan PPTX aktif bersama edit teks yang belum disimpan. | Penambahan 1–30 slide menggunakan layout Title and Content dari master slide terakhir. Preview editor dibatasi 40 slide dan edit teks menggunakan format run pertama setiap paragraf. |
| PDF | PdfCraft CLI menyediakan inspeksi, ekstraksi teks terbatas, render halaman, dan simpan salinan PDF tanpa password. | OCR opsional lewat OCRmyPDF hingga 30 halaman. PDF terenkripsi belum tersedia. |
| Cetak | Dialog cetak browser. | Paket desktop dan pencetakan langsung Windows lewat winprint.rs masih terbuka. |

OCR opsional memerlukan `ocrmypdf` beserta Tesseract dan model bahasa Inggris bawaan. Hasil diunduh sebagai salinan.

## Provider AI

Atur **Pengaturan provider AI** di UI atau isi `RUANGKERJA_AI_CHAT_COMPLETIONS_URL`, `RUANGKERJA_AI_MODEL`, dan, bila diperlukan, `RUANGKERJA_AI_API_KEY` sebelum menjalankan host. Gunakan endpoint chat-completions lengkap. HTTP diterima untuk loopback dan provider remote memakai HTTPS. Konfigurasi dari UI berlaku selama sesi host. Panel dokumen hanya menyertakan konteks file setelah pengguna memilih dan meninjaunya.

Writer menyediakan review perubahan teks. Spreadsheet menyediakan saran formula, review TSV, dan laporan insight. Slides menyediakan review teks dan outline. Katalog tetap memakai status demo ketika provider belum dikonfigurasi. Streaming dan pemasangan runtime/model AI lokal masih terbuka.

## Verifikasi dan kompatibilitas

```sh
python3 -m unittest discover -s tests
node --test tests/helpers.test.js
```

Tes PPTX dengan pembaca independen memakai paket opsional `python-pptx` dan dilewati jika paket tidak terpasang. Revisi upstream dikunci sebagai acuan instalasi. Uji binary Craft nyata, korpus format Office dari aplikasi lain, fidelity layout kustom, serta paket desktop lintas platform masih harus dilengkapi. [Riwayat hingga dev.42](docs/dev42-history.md) mendokumentasikan implementasi sebelumnya.
