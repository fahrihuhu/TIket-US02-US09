"""Kelas control: satu kelas per control pada robustness diagram."""
from __future__ import annotations

from collections import Counter
from datetime import date, time
from typing import Dict, Iterable, List, Optional, Union

from .email import EmailGateway
from .errors import (KodeBookingTidakSesuai, KursiHabis, PenerbanganTidakDitemukan,
                     PesananTidakDapatDibatalkan, PesananTidakDitemukan, ProfilTidakLengkap)
from .models import (Booking, ManajerTravel, MemberFrequentTraveller, Penerbangan, Pengguna,
                     StatusBooking, Tiket)
from .repositories import BookingRepository, PenerbanganRepository

Tujuan = Union[str, Iterable[str]]


# ---------- Pencarian (US-02a, US-03, US-04, US-06, US-08a) ----------
class CariPenerbanganControl:
    """UC-01 Cari Jadwal Penerbangan, UC-02 Multi-Tujuan, UC-05 Multi-Destinasi (filter)."""

    def __init__(self, penerbangan_repo: PenerbanganRepository) -> None:
        self._repo = penerbangan_repo

    def cari(self, tujuan: Tujuan, tanggal: date) -> List[Penerbangan]:
        """Satu tujuan (kode bandara) atau beberapa tujuan sekaligus."""
        kode = {tujuan} if isinstance(tujuan, str) else set(tujuan)
        hasil = [p for p in self._repo.semua()
                 if p.tujuan.kode_bandara in kode and p.tanggal_berangkat == tanggal]
        return sorted(hasil, key=lambda p: (p.jam_berangkat, p.harga))

    def cari_multi_destinasi(self, tanggal: date, asal: str, tujuan: Tujuan,
                             jam_dari: Optional[time] = None) -> List[Penerbangan]:
        """Filter tanggal, lokasi keberangkatan, tujuan, dan (opsional) jam keberangkatan."""
        hasil = [p for p in self.cari(tujuan, tanggal) if p.asal.kode_bandara == asal]
        if jam_dari is not None:
            hasil = [p for p in hasil if p.jam_berangkat >= jam_dari]
        return hasil


class CariTiketControl(CariPenerbanganControl):
    """UC-12 Cari Tiket untuk Pengunjung (dipakai Manajer Travel)."""


class BandingkanPenerbanganControl:
    """UC-06 Bandingkan harga dan jumlah penerbangan."""

    def bandingkan(self, pilihan: List[Penerbangan]) -> Dict:
        if not pilihan:
            raise ValueError("pilihan penerbangan kosong")
        termurah = min(pilihan, key=lambda p: p.harga)
        termahal = max(pilihan, key=lambda p: p.harga)
        return {
            "jumlah_penerbangan": len(pilihan),
            "per_maskapai": dict(Counter(p.maskapai.nama_maskapai for p in pilihan)),
            "termurah": termurah,
            "termahal": termahal,
            "selisih_harga": termahal.harga - termurah.harga,
        }


# ---------- Pemesanan & pembatalan (US-02b, US-02c) ----------
class PesanTiketControl:
    """UC-03 Pesan Tiket."""

    def __init__(self, penerbangan_repo: PenerbanganRepository, booking_repo: BookingRepository) -> None:
        self._penerbangan = penerbangan_repo
        self._booking = booking_repo

    def pesan(self, pemesan: Pengguna, nomor_penerbangan: str,
              nama_penumpang: Optional[str] = None,
              dibuat_oleh: Optional[ManajerTravel] = None) -> Booking:
        p = self._penerbangan.by_nomor(nomor_penerbangan)
        if p is None:
            raise PenerbanganTidakDitemukan(nomor_penerbangan)
        if p.kursi_tersedia <= 0:
            raise KursiHabis(f"kursi {nomor_penerbangan} habis")
        p.kursi_tersedia -= 1
        nomor = self._booking.nomor_tiket_baru()
        tiket = Tiket(nomor, nama_penumpang or pemesan.nama, p, p.harga, e_tiket=f"ETIKET-{nomor}")
        booking = Booking(self._booking.kode_baru(), pemesan, [tiket], StatusBooking.BOOKED,
                          date.today(), dibuat_oleh)
        self._booking.simpan(booking)
        return booking


class BatalkanTiketControl:
    """UC-04 Batalkan Tiket."""

    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking = booking_repo

    def daftar_pesanan(self, pengguna: Pengguna) -> List[Booking]:
        return self._booking.by_pemesan(pengguna)

    def batalkan(self, pengguna: Pengguna, kode: str) -> Booking:
        b = self._booking.by_kode(kode)
        if b is None or b.pemesan.id_pengguna != pengguna.id_pengguna:
            raise PesananTidakDitemukan(kode)
        if b.status == StatusBooking.CANCELLED:
            raise PesananTidakDapatDibatalkan(kode)
        b.status = StatusBooking.CANCELLED
        for t in b.tiket:
            t.penerbangan.kursi_tersedia += 1  # kursi dikembalikan
        self._booking.simpan(b)
        return b


# ---------- Profil & validasi tiket (US-05) ----------
class PerbaruiProfilControl:
    """UC-07 Perbarui Data Profil."""
    _BOLEH = {"nama", "email", "no_telepon", "nomor_member", "no_identitas", "tanggal_lahir", "alamat"}

    def perbarui(self, member: MemberFrequentTraveller, **data) -> MemberFrequentTraveller:
        tidak_dikenal = set(data) - self._BOLEH
        if tidak_dikenal:
            raise ValueError(f"atribut tidak dikenal: {sorted(tidak_dikenal)}")
        for k, v in data.items():
            setattr(member, k, v)
        return member


class PeriksaKelengkapanProfilControl:
    """UC-09 Periksa Kelengkapan Data Profil."""

    def periksa(self, member: MemberFrequentTraveller) -> bool:
        return member.profil_lengkap


class ValidasiTiketControl:
    """UC-08 Validasi Tiket."""

    def __init__(self, periksa: Optional[PeriksaKelengkapanProfilControl] = None) -> None:
        self._periksa = periksa or PeriksaKelengkapanProfilControl()

    def validasi(self, member: MemberFrequentTraveller, tiket: Tiket) -> Tiket:
        if not self._periksa.periksa(member):
            raise ProfilTidakLengkap()
        tiket.status_validasi = True
        return tiket


# ---------- Manajer Travel (US-07, US-08, US-09) ----------
class LihatStatusBookingControl:
    """UC-10 Lihat Status Booking."""

    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking = booking_repo

    def semua(self) -> List[Booking]:
        return self._booking.semua()


class FilterStatusBookingControl:
    """UC-11 Filter Status Booking."""

    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking = booking_repo

    def filter(self, status: StatusBooking) -> List[Booking]:
        return self._booking.by_status(status)


class PesanTiketPengunjungControl:
    """UC-13 Pesan Tiket atas Nama Pengunjung, termasuk UC-14 Kirim E-Tiket."""

    def __init__(self, pesan: PesanTiketControl, email: EmailGateway) -> None:
        self._pesan = pesan
        self._email = email

    def pesan(self, manajer: ManajerTravel, pengunjung: Pengguna, nomor_penerbangan: str) -> Booking:
        booking = self._pesan.pesan(pengunjung, nomor_penerbangan, dibuat_oleh=manajer)
        for t in booking.tiket:
            self._email.kirim(
                pengunjung.email,
                f"E-Tiket {booking.kode_booking_reference}",
                f"Halo {t.nama_penumpang}, e-tiket Anda: {t.e_tiket} "
                f"({t.penerbangan.nomor_penerbangan}, {t.penerbangan.tanggal_berangkat}).",
            )
        return booking


class LihatTiketTerpesanControl:
    """UC-15 Lihat Tiket Terpesan (tiket pada booking yang tidak dibatalkan)."""

    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking = booking_repo

    def lihat(self, pengguna: Pengguna) -> List[Tiket]:
        return [t for b in self._booking.by_pemesan(pengguna)
                if b.status != StatusBooking.CANCELLED for t in b.tiket]


class ValidasiKodeBookingReferenceControl:
    """UC-17 Validasi Kode Booking Reference."""

    def __init__(self, booking_repo: BookingRepository) -> None:
        self._booking = booking_repo

    def validasi(self, kode: str) -> Booking:
        b = self._booking.by_kode(kode.strip()) if kode else None
        if b is None:
            raise KodeBookingTidakSesuai()
        return b


class OtorisasiTiketControl:
    """UC-16 Otorisasi Tiket dengan kode booking reference; mengembalikan booking beserta statusnya."""

    def __init__(self, validasi_kode: ValidasiKodeBookingReferenceControl) -> None:
        self._validasi = validasi_kode

    def otorisasi(self, kode: str) -> Booking:
        return self._validasi.validasi(kode)
