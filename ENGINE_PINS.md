# Revisi engine

Host memanggil executable berikut lewat `PATH`. Instal dari revisi tetap dan ikuti prasyarat build upstream. Contoh WordCraft: `cargo install --git https://github.com/storytold/wordcraft --rev 22a73d9f2d10de6ee52780ab4a6019b864d9c598 --locked wordcraft-cli`. Jika engine memerlukan build workspace, checkout revisinya lalu jalankan `cargo build --locked --release -p <nama-cli>` dari repo engine.

| Engine | Revisi | Integrasi |
| --- | --- | --- |
| [WordCraft](https://github.com/storytold/wordcraft) | `22a73d9f2d10de6ee52780ab4a6019b864d9c598` | `wordcraft-cli text` dan `convert` |
| [GridCraft](https://github.com/storytold/gridcraft) | `bea2191b354270d06048d1a6cbc14b5690ea0f40` | `gridcraft-cli info`, `run`, dan `convert` |
| [DeckCraft](https://github.com/storytold/deckcraft) | `4aec38a2bceac18ee9c67b80b834441a69cc81ae` | `deckcraft-cli render` dan `convert` |
| [PdfCraft](https://github.com/storytold/pdfcraft) | `2251a75cc85d7da786a7bf5d910fbd7e0bfa0039` | `pdfcraft-cli info`, `text`, `render`, dan `edit` |
| [craft-libs](https://github.com/storytold/craft-libs) | `93dac78c93a7f1fd66e2022edeb089233b1dc45a` pada WordCraft | Dependensi transitif; setiap workspace upstream menentukan pin paketnya sendiri. |
| [winprint.rs](https://github.com/storytold/winprint.rs) | `f084d353f53b5a890041725e86744bdff92447ef` | Acuan adapter printer Windows yang masih terbuka. |

Repo ini tidak menyertakan binary upstream. Saat mendistribusikan paket yang menyertakannya, sertakan lisensi dan notice dari setiap revisi beserta dependensinya.
