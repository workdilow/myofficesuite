# Roadmap Ruangkerja

Status berikut berlaku untuk repo GitHub mulai `0.3.0-dev.44`. Riwayat fitur workspace Rust tersedia di [changelog hingga dev.42](docs/dev42-history.md).

| Prioritas | Status dan kriteria selesai |
| --- | --- |
| Streaming AI | Tersedia di panel dokumen dan katalog untuk provider chat-completions SSE. Tes loopback memastikan potongan dikirim sebelum stream berakhir, health tetap bisa diakses, dan respons terputus atau terkena batas token tidak bisa diterapkan. Masih perlu uji dengan provider nyata dan browser. |
| Pemulihan backend Rust | Integrasi saat ini memakai host Python untuk memanggil CLI Craft. Source `crates/` dan `vendor/` proyek lokal masih diperlukan untuk memulihkan adapter Rust dan menguji kompatibilitasnya. |
| Kompatibilitas dokumen | Uji round-trip dengan binary Craft yang dipin dan corpus DOCX/XLSX/PPTX/PDF yang memiliki izin pakai. Ukur pemformatan, media, formula, tema, dan catatan pembicara. |
| PDF | Pencocokan kutipan AI terhadap teks halaman dalam konteks yang disetujui tersedia. Kesesuaian makna klaim tetap terbuka. Verifikasi pembukaan PDF terenkripsi dan render berbasis password tanpa menyimpan kredensial. Uji OCR bahasa Indonesia, lalu lanjutkan anotasi dan manipulasi halaman. |
| Editor dan desktop | Tingkatkan fidelity Writer, objek dan catatan Slides, installer desktop, pemilih file native, dan cetak Windows lewat winprint.rs. |
| Runtime AI lokal | Sediakan pemasangan dan pengujian model lokal, serta status provider yang bisa diverifikasi dari UI. |
