"""Penyimpanan di memori. Ganti dengan database tanpa mengubah kelas control."""
from __future__ import annotations

from typing import Dict, List, Optional

from .models import Booking, Penerbangan, Pengguna, StatusBooking


class PenerbanganRepository:
    def __init__(self) -> None:
        self._data: Dict[str, Penerbangan] = {}

    def simpan(self, p: Penerbangan) -> None:
        self._data[p.nomor_penerbangan] = p

    def by_nomor(self, nomor: str) -> Optional[Penerbangan]:
        return self._data.get(nomor)

    def semua(self) -> List[Penerbangan]:
        return list(self._data.values())


class BookingRepository:
    def __init__(self) -> None:
        self._data: Dict[str, Booking] = {}
        self._seq_booking = 0
        self._seq_tiket = 0

    def kode_baru(self) -> str:
        self._seq_booking += 1
        return f"BK{self._seq_booking:06d}"

    def nomor_tiket_baru(self) -> str:
        self._seq_tiket += 1
        return f"TK{self._seq_tiket:06d}"

    def simpan(self, b: Booking) -> None:
        self._data[b.kode_booking_reference] = b

    def by_kode(self, kode: str) -> Optional[Booking]:
        return self._data.get(kode)

    def by_pemesan(self, pengguna: Pengguna) -> List[Booking]:
        return [b for b in self._data.values() if b.pemesan.id_pengguna == pengguna.id_pengguna]

    def by_status(self, status: StatusBooking) -> List[Booking]:
        return [b for b in self._data.values() if b.status == status]

    def semua(self) -> List[Booking]:
        return list(self._data.values())
