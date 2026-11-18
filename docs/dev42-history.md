# Changelog

Semua perubahan penting Ruangkerja dicatat di sini. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) dengan nomor versi `MAJOR.MINOR.PATCH`.

## [Unreleased]

### Known limitations

- OCR PDF tersedia melalui engine PdfCraft, tetapi memerlukan model OCR lokal yang disiapkan terpisah; manipulasi PDF/dokumen, edit gambar AI, scan kamera, QR, dan cloud restore/version history masih memerlukan engine atau layanan lain.
- Tanpa konfigurasi provider, output AI memakai template demo dan bukan hasil model AI.
- AI streaming, file picker native, lisensi penuh, corpus berkas nyata, printer native/perangkat, editor Office umum, dan layanan cloud belum tersedia. Cetak browser tersedia; gateway AI teks dapat dipakai setelah endpoint provider dikonfigurasi melalui environment atau UI sesi host.

## [0.3.0-dev.42] - 2026-11-18

### Changed

- Review Writer untuk dokumen panjang kini memakai anchor paragraf unik dan LCS berbatas agar perubahan lokal yang berjauhan tetap dapat ditinjau terpisah tanpa alokasi matriks untuk seluruh dokumen.
- Rentang panjang yang tidak memiliki paragraf jangkar tetap dikelompokkan sebagai satu saran agar penyisipan/penghapusan tidak salah disejajarkan.

## [0.3.0-dev.41] - 2026-11-18

### Added

- UI pengaturan endpoint chat-completions dan model AI; API key dikirim ke host loopback, ditahan hanya di memori proses, tidak dikembalikan dalam respons, dan dapat dihapus atau dikembalikan ke konfigurasi environment.
- Perubahan konfigurasi memerlukan origin aplikasi lokal. Endpoint remote wajib HTTPS; HTTP hanya diterima untuk host loopback.

## [0.3.0-dev.40] - 2026-11-18

### Changed

- Statistik Spreadsheet lokal menafsirkan angka literal menurut locale Indonesia (`1.234,50`, `1.234`, dan `2,5`), mencatat konvensi tersebut di UI dan capability catalog, serta menjaga hasil formula pada format numerik GridCraft yang kanonis.
- Parsing statistik menerima nilai akuntansi negatif dalam tanda kurung dan format campuran yang tervalidasi; pemisah kelompok yang tidak valid tetap diklasifikasikan sebagai teks.

## [0.3.0-dev.39] - 2026-11-18

### Added

- PDF berpassword meminta password lokal hingga tiga kali; password hanya berada di memori UI dan dikirim ke host loopback untuk ekstraksi teks dan render halaman.
- Adapter membedakan password yang diminta dan password salah. Tes membuat PDF terenkripsi, memverifikasi kedua error, lalu membuktikan teks dan render hanya tersedia dengan password benar.

### Safety

- OCR untuk PDF berpassword disembunyikan/dinonaktifkan sampai PdfCraft membuktikan searchable copy mempertahankan perlindungan sumber.

## [0.3.0-dev.37] - 2026-11-18

### Added

- Statistik Spreadsheet lokal untuk rentang preview hingga 1.000 sel: jumlah, rata-rata, median, minimum, dan maksimum dihitung dari input angka literal, dengan alamat sumber yang dapat diperiksa dan laporan teks yang dapat diunduh.
- Statistik secara eksplisit menghitung formula, teks, dan sel kosong terpisah; formula dikecualikan karena nilai cache dapat usang, dan input angka memakai sintaks titik desimal.
- Fungsi statistik memiliki tes terpisah dan capability catalog mencatat ketersediaan serta kebijakan formulanya.

## [0.3.0-dev.38] - 2026-11-18

### Changed

- Statistik lokal kini meminta GridCraft menghitung ulang edit aktif pada salinan workbook sementara, lalu memasukkan hasil formula numerik ke metrik tanpa mengubah file sumber.
- Adapter mengembalikan nilai kalkulasi mentah selain teks tampak, dan tes membuktikan formula berubah dari 5 menjadi 8 pada salinan sementara sementara sumber tetap 5.

## [0.3.0-dev.36] - 2026-11-18

### Fixed

- Memperbaiki handler review Writer yang masih menunjuk UI lama sehingga saran per paragraf dapat dipasang tanpa mencari kontrol yang sudah dihapus.
- Menambahkan pemeriksaan host untuk JavaScript review Writer yang disajikan pada `/writer_review.js`.

## [0.3.0-dev.35] - 2026-11-18

### Added

- Review Writer membagi saran rewrite, proofreading, dan terjemahan per paragraf; pengguna memilih perubahan mana yang diterapkan, dan paragraf lain dipertahankan.
- Diff paragraf memakai LCS untuk menyelaraskan bagian yang tidak berubah, serta menguji replace/insert/delete dan seleksi parsial.
- Task Writer menolak konteks terpotong sebelum meminta saran yang dapat diterapkan; dokumen di atas 250 paragraf memakai satu bagian review penuh.

## [0.3.0-dev.34] - 2026-11-18

### Added

- Asisten Spreadsheet memiliki task khusus untuk tren dan ringkasan data; konteks berisi alamat sel serta nilai tampak formula untuk rentang hingga 200 sel.
- Insight dapat ditinjau/diedit dan diunduh sebagai laporan teks tanpa mengubah workbook; unduhan ditolak bila worksheet/rentang berubah setelah analisis dibuat.

## [0.3.0-dev.33] - 2026-11-18

### Fixed

- Pembersihan Spreadsheet AI sekarang meminta rentang eksplisit bila rentang preview lebih dari 200 sel, mengirim TSV lengkap yang sama dengan pratinjau, dan menolak sel yang berisi tab/baris baru agar bentuk tabel tidak bergeser.
- Ukuran permintaan dibatasi sebelum dikirim agar konteks rentang tetap berada di bawah batas gateway 32 KiB.

## [0.3.0-dev.32] - 2026-11-18

### Added

- Writer memiliki task kontekstual terpisah untuk proofreading/revisi, ringkasan, dan terjemahan dengan pilihan bahasa tujuan; task terdaftar pada endpoint capability.
- Proofreading dan terjemahan dapat ditinjau lalu diterapkan; ringkasan dapat diedit dan diunduh tanpa mengubah dokumen sumber.
- Task Writer yang membaca dokumen mewajibkan persetujuan konteks, dan penerapan/unduh menolak hasil jika teks berubah setelah permintaan AI dikirim.

## [0.3.0-dev.31] - 2026-11-18

### Added

- Endpoint `GET /api/engine/capabilities` menyediakan kontrak JSON berversi untuk format, operasi, batas engine, status kemampuan AI, dan tools browser.
- Tes host memverifikasi operasi dan batas yang dinyatakan, termasuk chart GridCraft, batas preview, OCR PDF, streaming, dan pemrosesan gambar AI.

## [0.3.0-dev.30] - 2026-11-18

### Added

- Pembersihan data Spreadsheet AI memakai konteks opt-in dan menampilkan TSV untuk ditinjau atau diedit sebelum diterapkan.
- Penerapan pembersihan dibatasi pada preview GridCraft 50 baris × 20 kolom, mensyaratkan ukuran tetap, menjaga input rumus persis, menolak saran stale, dan masuk sebagai satu langkah undo.

### Known limitations

- Pembersihan hanya mencakup rentang preview yang dibatasi engine; pemilihan rentang penuh, insight statistik terstruktur, dan operasi chart interaktif belum tersedia.

## [0.3.0-dev.29] - 2026-11-18

### Added

- Asisten spreadsheet memakai konteks worksheet hanya setelah opt-in dan dapat menyarankan rumus untuk sel aktif.
- Saran rumus dapat ditinjau atau diedit sebelum diterapkan; penerapan memakai jalur perubahan sel GridCraft yang sudah ada dan tetap menunggu disimpan.
- Rewrite AI untuk objek teks slide aktif dapat ditinjau atau diedit sebelum diterapkan melalui antrean perubahan DeckCraft.
- Undo/redo tersedia untuk perubahan teks Writer, sel Spreadsheet, dan objek teks Slides, dengan riwayat maksimal 100 keadaan.
- Spesifikasi corpus round-trip format Office ditambahkan di `CORPUS.md`, termasuk manifest lisensi, pemeriksaan semantik, dan syarat gate.
- Isi konteks dokumen yang akan dikirim ke provider AI kini dapat diperiksa setelah opt-in; jika konten berubah sejak pratinjau, aplikasi memperbarui pratinjau dan menunggu kiriman ulang.
- Endpoint OCR PdfCraft membuat searchable PDF sebagai unduhan baru; model disediakan terpisah dan sumber tetap utuh.
- Jawaban asisten PDF harus memakai kutipan verbatim dari halaman yang dirujuk, satu bukti per bullet; host menolak kutipan yang tidak ada pada teks halaman itu.
- Outline presentasi yang dibuat AI dengan konteks opt-in dapat ditinjau/diedit dan diekspor menjadi PPTX baru melalui importer Markdown DeckCraft.

### Verified

- Pemeriksaan versi ini mencakup syntax JavaScript, format Rust, build workspace, dan seluruh tes workspace.

## [0.3.0-dev.22] - 2026-11-18

### Fixed

- Batasi render pratinjau worksheet GridCraft pada 100.000 sel terpakai sebelum menghasilkan HTML, selain batas 8 MiB respons host.

### Verified

- Metadata worksheet mengembalikan judul chart dan hasil renderer memuat SVG chart yang disimpan dalam workbook.

## [0.3.0-dev.21] - 2026-11-18

### Added

- Preview worksheet penuh melalui renderer HTML GridCraft, termasuk chart inline SVG, dalam iframe sandbox dengan kebijakan CSP ketat.

### Known limitations

- Preview lengkap dibatasi 8 MiB hasil HTML dan hanya tersedia setelah pengguna membukanya dari panel worksheet.

## [0.3.0-dev.20] - 2026-11-18

### Added

- Buat chart column, bar, line, pie, doughnut, area, atau scatter dari rentang data terpilih ke worksheet GridCraft dan unduh workbook hasil sebagai salinan.

### Known limitations

- Chart dibuat dari dialog rentang/jenis/judul dan disimpan ke workbook, tetapi belum ditampilkan sebagai objek interaktif di preview Ruangkerja.

## [0.3.0-dev.19] - 2026-11-18

### Fixed

- Jalankan `formulas.calculateNow` di GridCraft sebelum menyimpan atau menampilkan preview agar perubahan input memperbarui nilai formula yang bergantung padanya.

### Verified

- Tes adapter mengubah input `A1` dan memastikan formula `=SUM(A1:A2)` pada `A3` berubah dari 5 menjadi 8 setelah simpan dan preview.

## [0.3.0-dev.18] - 2026-11-18

### Added

- Muat ulang preview sheet aktif setelah penyimpanan agar nilai hasil formula menampilkan kalkulasi GridCraft terbaru.

### Known limitations

- Nilai formula baru diperbarui setelah simpan; kalkulasi langsung saat mengetik dan format numerik lengkap belum tersedia.

## [0.3.0-dev.17] - 2026-11-18

### Added

- Tombol cetak untuk tampilan Writer, sheet aktif, dan slide aktif melalui dialog cetak browser; PDF lokal membuka file utuh di viewer PDF sistem untuk dicetak.

### Known limitations

- Cetak memakai fasilitas browser/OS, bukan adapter printer langsung. Layout Office dan cetak fisik belum diverifikasi pada perangkat.

## [0.3.0-dev.16] - 2026-11-18

### Added

- Formula bar spreadsheet untuk melihat dan mengedit input/rumus sel terpilih; perubahan tetap masuk ke antrean simpan sheet yang benar.

### Known limitations

- Formula bar mengubah input sel, tetapi preview belum menghitung ulang hasil formula dan belum menampilkan format numerik lengkap.

## [0.3.0-dev.15] - 2026-11-18

### Added

- Validasi host untuk rujukan `[Hal. N]` dari asisten PDF. Host menolak jawaban yang merujuk halaman tanpa teks hasil ekstraksi, nomor halaman yang tidak ada, atau jawaban berbasis sumber tanpa rujukan.

### Known limitations

- Pemeriksaan memastikan halaman ada dan memiliki teks, tetapi belum membuktikan bahwa teks halaman benar-benar mendukung setiap klaim.

## [0.3.0-dev.14] - 2026-11-18

### Added

- Navigasi antar-worksheet pada spreadsheet dan penyimpanan perubahan yang ditautkan ke sheet tempat sel diedit.

### Known limitations

- Spreadsheet masih menampilkan preview maksimal 50 × 20 sel; formula bar, format sel, chart, dan editor workbook penuh belum tersedia.

## [0.3.0-dev.13] - 2026-11-18

### Added

- Peringatan sebelum menutup tab, berpindah editor, membuka file lain, atau meninggalkan workbench ketika ada perubahan yang belum disimpan.

## [0.3.0-dev.12] - 2026-11-18

### Added

- Alur tinjau saran AI untuk revisi Writer: dengan konteks dokumen yang dipilih, pengguna dapat membandingkan teks saat ini, mengedit saran, lalu menerapkannya sebagai perubahan belum disimpan sebelum menyimpan file.

### Known limitations

- Penerapan saran AI saat ini hanya mendukung teks isi Writer dan meminta pengguna meninjau seluruh teks; diff per kalimat, undo/redo, dan penerapan terstruktur untuk sel spreadsheet atau objek slide belum tersedia.

## [0.3.0-dev.11] - 2026-11-18

### Added

- Buka PPTX lokal melalui DeckCraft, tampilkan daftar slide dan hasil render PNG, serta edit teks objek pada panel.
- Simpan perubahan teks sebagai salinan PPTX melalui DeckCraft sambil mempertahankan gaya paragraf/run pertama pada shape yang diedit.
- Panel asisten dapat memakai teks PPTX terbuka setelah pengguna memilih opsi konteks, untuk tanya-jawab dan saran presentasi.

### Known limitations

- Editor belum mendukung pemilihan/penataan objek visual, animasi, catatan pembicara, atau format slide penuh; kesetiaan dokumen kompleks perlu diuji dengan corpus PowerPoint nyata.
- Preview shell membatasi 100 slide dan 200 shape teks per slide. Teks multi-paragraf yang diedit memakai gaya paragraf pertama.

## [0.3.0-dev.10] - 2026-11-18

### Added

- Beri penanda halaman pada teks PDF yang diekstrak dan arahkan asisten PDF untuk menjawab berdasarkan teks sumber serta menyertakan rujukan `[Hal. N]`.
- Jaga pemotongan konteks PDF AI di batas halaman agar rujukan tidak kehilangan label sumber.

### Known limitations

- Rujukan dihasilkan model berdasarkan instruksi prompt; host belum memverifikasi bahwa halaman yang dirujuk benar-benar mendukung klaim.

## [0.3.0-dev.9] - 2026-11-18

### Added

- Render halaman PDF dengan PdfCraft sebagai PNG di pratinjau lokal, dengan navigasi halaman dasar.
- Tampilkan teks hasil ekstraksi dalam panel yang dapat dibuka di bawah halaman.

### Known limitations

- OCR, anotasi/edit PDF, password untuk PDF terenkripsi, dan sitasi halaman dari jawaban AI belum tersedia.

## [0.3.0-dev.8] - 2026-11-18

### Added

- Buka PDF lokal melalui PdfCraft, ekstrak teks urutan-baca dari hingga 50 halaman, dan tampilkan sebagai pratinjau baca-saja.
- Izinkan panel AI memakai teks PDF yang diekstrak setelah pengguna mencentang opsi konteks dokumen.

### Known limitations

- Ini pratinjau teks, bukan viewer halaman PDF; halaman scan tanpa text layer membutuhkan OCR dan tidak menghasilkan teks.
- PDF terenkripsi belum meminta password; ekstraksi dibatasi 50 halaman dan 250 KB teks, serta belum menampilkan rujukan halaman untuk jawaban AI.

## [0.3.0-dev.7] - 2026-11-18

### Added

- Buka XLS/XLSX/ODS/CSV/TSV melalui GridCraft dan tampilkan preview sheet aktif maksimal 50 × 20 sel.
- Edit sel inline dan simpan hanya sel yang berubah melalui satu sesi GridCraft.
- CSV/TSV bisa disimpan langsung dengan file handle browser; workbook Office diunduh sebagai salinan.
- AI Writer panel dapat menggunakan nilai rentang spreadsheet setelah pengguna memilih opsi konteks.

### Known limitations

- Editor menampilkan sheet aktif saja; navigasi sheet, formula bar, format sel, chart, dan workbook multi-sheet belum ada.
- Preview membatasi area ke 50 baris dan 20 kolom pertama dari rentang terpakai.
- Workbook Office diunduh sebagai salinan sampai kesetiaan round-trip diuji terhadap corpus.

## [0.3.0-dev.6] - 2026-11-18

### Added

- Panel asisten Writer mengirim permintaan ke provider AI yang dikonfigurasi.
- Opsi konteks eksplisit; isi file hanya ikut permintaan ketika pengguna mencentang “Sertakan isi dokumen dalam permintaan”.
- Prompt sistem memperlakukan konten file sebagai data tidak tepercaya, bukan instruksi, dan meminta model tidak mengarang rujukan.
- Batas gabungan prompt dan konteks 32 KiB.

### Known limitations

- Jawaban AI berupa teks untuk ditinjau; belum ada diff/aplikasi langsung ke dokumen atau streaming.
- Konteks yang dikirim saat ini hanya teks isi Writer yang sudah dibuka.

## [0.3.0-dev.5] - 2026-11-18

### Added

- Alur buka dokumen Writer lokal dengan isi TXT/MD dari browser dan isi DOC/DOCX/RTF/ODT dari WordCraft.
- Editor teks isi dengan status perubahan dan tombol simpan; TXT/MD dapat ditulis kembali lewat file handle browser.
- Simpan format Office sebagai salinan unduhan agar file asal tetap aman selama pemformatan belum dipertahankan.
- Pesan yang menjelaskan batas tata letak dan pemformatan DOCX saat mengedit teks isi.

### Known limitations

- Format dokumen Office dibaca dan ditulis ulang sebagai teks isi; styling, tabel, gambar, header/footer, dan layout tidak dipertahankan.
- Dialog sistem bergantung pada API browser; selain TXT/MD, penyimpanan adalah unduhan salinan.

## [0.3.0-dev.4] - 2026-11-18

### Added

- Gateway AI di host lokal untuk endpoint chat-completions kompatibel; model, URL, dan kunci diatur melalui environment host.
- Tools outline, brainstorming, draf dokumen, slide outline, materi belajar, flashcards, kuis, panduan belajar, dan terjemahan dapat memanggil provider yang dipilih.
- Status AI terhubung di katalog; tanpa konfigurasi fitur tetap diberi label demo.
- Batas input AI 32 KiB dan penanganan error provider tanpa mengembalikan detail internal provider.

### Known limitations

- Provider harus mendukung skema chat-completions dan dikonfigurasi administrator perangkat.
- AI menghasilkan teks untuk ditinjau; belum mengubah langsung dokumen, membuat file PPTX, streaming, atau menerima konteks file otomatis.
- Belum ada keychain OS atau UI pengaturan provider.

## [0.3.0-dev.3] - 2026-11-18

### Added

- Host HTTP Rust loopback yang menyajikan UI dan memanggil WordCraft, GridCraft, DeckCraft, serta PdfCraft di perangkat lokal.
- Tools UI untuk ekstrak/ganti teks, ubah sel spreadsheet, round-trip presentasi, dan buka/simpan PDF.
- Batas unggahan 64 MiB, respons unduhan, pesan kegagalan, serta validasi nama file.
- Petunjuk menjalankan host dan status platform yang diperbarui.

### Known limitations

- Host bukan paket desktop terpasang dan belum memakai dialog file native.
- Tools WordCraft masih berupa operasi teks; editing dokumen berformat, formula/charts penuh, dan PDF editing belum tersedia.
- AI tools tetap berupa demo template; model/provider belum disambungkan.
- Belum ada corpus file Office nyata, audit lisensi lengkap, uji printer, atau distribusi.

## [0.3.0-dev.2] - 2026-11-18

### Added

- Adaptor headless byte-oriented untuk WordCraft, GridCraft, DeckCraft, dan PdfCraft dengan source revision dikunci.
- Vendor patches PdfCraft yang diperlukan agar dependency render cocok, beserta lockfile Cargo untuk graph gabungan.
- Keputusan Linux desktop sebagai target awal, daftar pin, dan kriteria penerimaan platform.
- Round-trip test TXT, DOCX, CSV, XLSX, dan PPTX serta smoke test PDF.

### Known limitations

- Adaptor PDF masih feature-gated (`pdf-engine`) dan saat ini hanya menguji open/save.
- Uji kompatibilitas hanya mencakup fixture kecil; belum ada corpus DOCX/XLSX/PPTX/PDF dari aplikasi Office.
- Shell desktop, file picker lokal, koneksi UI, integrasi AI, serta pencetakan belum dibangun pada versi ini.

## [0.3.0-dev.1] - 2026-11-18

### Added

- Workspace Rust awal, adaptor WordCraft, pin sumber engine, dan keputusan target platform Linux.

## [0.2.0-dev.1] - 2026-11-18

### Added

- Katalog “Temukan tools” dengan tab AI Tools dan Other Tools serta kategori yang mengikuti referensi pengguna.
- Dialog tool yang menunjukkan status demo lokal atau kebutuhan engine sebelum menjalankan fitur.
- Demo lokal untuk outline, brainstorming, dokumen, slide, flashcard, kuis, panduan belajar, dan terjemahan placeholder.
- Text-to-speech memakai fitur suara browser.
- Kompresi dan konversi format gambar di browser.

## [0.1.0] - 2026-11-18

Versi awal MVP antarmuka lokal.

### Added

- Workspace terpadu dengan pintasan Writer, Spreadsheet, Presentation, dan PDF.
- Pencarian, daftar file terbaru, pembuatan dokumen contoh, dan penyimpanan metadata di browser.
- Editor demo untuk teks dan sel spreadsheet, serta pratinjau presentasi dan PDF.
- Panel AI demo lokal dengan contoh alur drafting, ringkasan, outline, dan bantuan formula.
- Dokumen rancangan integrasi engine dan tahapan pengembangan.

### Known limitations

- Engine dokumen dari repositori rujukan belum diintegrasikan.
- Unggah file belum membaca atau menyimpan konten file.
- AI belum terhubung ke model/provider; hasil hanya contoh lokal.
- Belum ada penyimpanan cloud, kolaborasi, ekspor format Office, atau release desktop.

## Cara memperbarui changelog

- Tambahkan perubahan yang sudah selesai ke bagian versi berikutnya di atas.
- Kelompokkan sebagai `Added`, `Changed`, `Fixed`, `Removed`, atau `Known limitations`.
- Saat rilis, pindahkan catatan ke judul versi dan tanggal, lalu samakan nomor pada file `VERSION`.
- Jangan masukkan pekerjaan yang baru direncanakan sebagai perubahan yang sudah dirilis; catat rencana di [ROADMAP.md](ROADMAP.md).
