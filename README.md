# Ruangkerja

Workspace lokal Writer, Spreadsheet, Slides, PDF, dan asisten AI. Host memakai CLI Craft terpisah. Versi `0.3.0-dev.46` menambahkan penyimpanan edit isi DOCX dengan format sumber, edit catatan pembicara PPTX, dan uji koneksi provider AI.

## Jalankan

Perlu Python 3.10 atau lebih baru. Host tidak memerlukan paket Python tambahan.

```sh
python3 host.py
```

Buka [Ruangkerja di perangkat ini](http://127.0.0.1:4173). Gunakan alamat tersebut agar pemeriksaan origin sesuai. Unggahan diproses di direktori sementara dan dibatasi 64 MiB. Halaman juga bisa dibuka sebagai demo statis. Dokumen TXT/MD, paragraf isi DOCX, CSV/TSV, dan teks shape pada PPTX dapat diproses tanpa memasang CLI.

Pasang binary upstream `wordcraft-cli`, `gridcraft-cli`, `deckcraft-cli`, dan `pdfcraft-cli` di `PATH`. Ikuti petunjuk build masing-masing repo pada revisi di [ENGINE_PINS.md](ENGINE_PINS.md). Host membaca status CLI dari `PATH` dan melaporkannya lewat `GET /api/engine/capabilities`.

| Area | Alur yang tersedia | Batas |
| --- | --- | --- |
| Writer | Edit paragraf isi DOCX dan unduh sebagai salinan dengan style serta struktur yang dipertahankan. WordCraft menangani ekstraksi dokumen Office dan ekspor teks ke RTF atau ODT. | Editor DOCX berbasis teks hingga 2.000 paragraf dan 256 KiB. Tabel, header, footer, bidang, dan paragraf dengan objek atau tautan disunting lewat WordCraft. |
| Spreadsheet | Preview 50 × 20, edit sel, statistik lokal dari alamat sumber. GridCraft menambah preview Office, hasil formula, simpan XLSX, dan chart. | CSV/TSV tanpa GridCraft mendukung input literal. XLS/ODS perlu dikonversi ke XLSX untuk penyimpanan edit. |
| Slides | Edit teks shape dan catatan pembicara yang sudah ada. Render dan outline melalui DeckCraft. Outline dapat diunduh sebagai deck baru atau ditambahkan ke salinan PPTX aktif bersama edit teks yang belum disimpan. | Penambahan 1–30 slide menggunakan layout Title and Content dari master slide terakhir. Preview editor dibatasi 40 slide. Edit teks shape dan catatan menggunakan format run pertama setiap paragraf. Pembuatan bagian catatan baru belum tersedia. |
| PDF | PdfCraft CLI menyediakan inspeksi, ekstraksi teks terbatas, render, dan simpan ulang PDF. PDFium opsional menyediakan buka/render PDF berpassword, salinan halaman terpilih hingga 250 halaman, rotasi, dan catatan teks. | Password hanya dipakai di memori. PDF terenkripsi dibuka dalam mode baca saja. OCR dibatasi hingga 30 halaman. Salinan halaman dapat kehilangan bookmark dan formulir tingkat dokumen. |
| Cetak | Dialog cetak browser. | Paket desktop dan pencetakan langsung Windows lewat winprint.rs masih terbuka. |

Pasang dependensi PDFium opsional di environment Python 3.11 atau lebih baru yang menjalankan host:

```sh
python3 -m pip install -r requirements-pdf.txt
```

PdfCraft tetap dipakai untuk PDF tanpa password jika CLI tersedia. PDFium menangani PDF berpassword di dalam proses host tanpa meneruskan password ke baris perintah. Ekstraksi teks dan konteks AI mengikuti izin salin dokumen.

OCR memerlukan `ocrmypdf` dan Tesseract. Pasang model `tesseract-ocr-ind` untuk Bahasa Indonesia pada Debian/Ubuntu, atau model `ind` dari distribusi platform Anda. UI hanya menawarkan Bahasa Indonesia, Inggris, atau gabungan keduanya berdasarkan model `ind` dan `eng` yang terpasang. Hasil diunduh sebagai salinan.

## Provider AI

Atur **Pengaturan provider AI** di UI atau isi `RUANGKERJA_AI_CHAT_COMPLETIONS_URL`, `RUANGKERJA_AI_MODEL`, dan, bila diperlukan, `RUANGKERJA_AI_API_KEY` sebelum menjalankan host. Gunakan endpoint chat-completions lengkap. HTTP diterima untuk loopback dan provider remote memakai HTTPS. Konfigurasi dari UI berlaku selama sesi host. Panel dokumen hanya menyertakan konteks file setelah pengguna memilih dan meninjaunya.

Writer menyediakan review perubahan teks. Spreadsheet menyediakan saran formula, review TSV, dan laporan insight. Slides menyediakan review teks dan outline. Jawaban PDF mencocokkan kutipan dengan teks halaman yang tercantum dalam pratinjau konteks. Katalog tetap memakai status demo ketika provider belum dikonfigurasi. Jawaban muncul bertahap untuk provider yang mengirim Server-Sent Events. Respons JSON utuh tetap bisa ditampilkan jika provider mengembalikannya. Tombol **Hentikan** membatalkan pembacaan di UI. Review, penerapan edit, dan unduhan tersedia setelah respons selesai. Pilih **Uji koneksi** untuk memeriksa konfigurasi yang tersimpan. Host mengirim pesan uji tetap tanpa isi dokumen. Hasil uji berlaku saat itu. Jika URL endpoint diganti, masukkan API key yang sesuai dengan endpoint baru.

### Model lokal dengan Ollama

1. Pasang [Ollama](https://docs.ollama.com/quickstart), jalankan, lalu unduh model lokal pilihan dengan `ollama pull NAMA_MODEL`.
2. Di **Pengaturan provider AI**, masukkan `http://127.0.0.1:11434/v1/chat/completions` dan nama model lokal yang diunduh. Simpan pengaturan.
3. Klik **Uji koneksi**, lalu coba menulis draf dengan Asisten. Lihat [dokumentasi endpoint Ollama](https://docs.ollama.com/api/openai-compatibility) untuk dukungan model dan API.

## Verifikasi dan kompatibilitas

```sh
python3 -m unittest discover -s tests
node --test tests/helpers.test.js
```

Tes DOCX dan PPTX memakai pembaca independen `python-docx` dan `python-pptx`, dan dilewati jika paket terkait tidak terpasang. Tes PDF memakai `requirements-pdf.txt` serta `pypdf` dan `reportlab` untuk membuat serta membaca fixture independen. Revisi upstream dikunci sebagai acuan instalasi. Uji binary Craft nyata, korpus format Office dari aplikasi lain, fidelity layout kustom, serta paket desktop lintas platform masih harus dilengkapi. [Roadmap saat ini](ROADMAP.md) · [Riwayat hingga dev.42](docs/dev42-history.md) mendokumentasikan implementasi sebelumnya.
