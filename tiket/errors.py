"""Pengecualian domain. Setiap kelas mewakili satu skenario alternatif pada user story."""


class DomainError(Exception):
    """Induk semua kesalahan aturan bisnis."""


class PenerbanganTidakDitemukan(DomainError):
    pass


class KursiHabis(DomainError):
    """US-02b: tiket tidak dapat dipesan karena kursi habis."""


class PesananTidakDitemukan(DomainError):
    pass


class PesananTidakDapatDibatalkan(DomainError):
    """US-02c: pesanan sudah dibatalkan sebelumnya."""


class ProfilTidakLengkap(DomainError):
    """US-05c: validasi ditolak karena data profil belum lengkap."""

    def __init__(self):
        super().__init__("data profil tidak lengkap")


class KodeBookingTidakSesuai(DomainError):
    """US-09c: kode booking reference tidak ditemukan."""

    def __init__(self):
        super().__init__("kode booking reference tidak sesuai")
