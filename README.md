# Sistem Pemesanan Tiket Pesawat (US-02 s.d. US-09)

Python 3, tanpa dependensi.

    python3 demo.py                              # demo alur utama
    python3 server.py                            # UI web di http://localhost:8000
    python3 -m unittest discover -s . -t . -v    # pengujian

| Konseptual | Kode |
|---|---|
| Domain model | `tiket/models.py` |
| Control (robustness diagram) | `tiket/controls.py` |
| Entity + penyimpanan | `tiket/repositories.py` (di memori) |
| Layanan Email | `tiket/email.py` |
| Alternatif flow (`alt`) | `tiket/errors.py` |

Peran di UI: Ani (Pengguna), Budi (Member), Citra (Manajer Travel).
