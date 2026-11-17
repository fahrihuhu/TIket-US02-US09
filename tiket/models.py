"""Kelas entitas, mengikuti Domain Model sistem pemesanan tiket pesawat."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
from typing import List, Optional


class StatusBooking(Enum):
    BOOKED = "Booked"
    WAITING_FOR_PAYMENT = "Waiting for Payment"
    CONFIRMED = "Confirmed"
    CANCELLED = "Cancelled"


@dataclass
class Pengguna:
    id_pengguna: str
    nama: str
    email: str
    no_telepon: str = ""


@dataclass
class MemberFrequentTraveller(Pengguna):
    """Spesialisasi Pengguna (generalization pada domain model)."""
    nomor_member: str = ""
    no_identitas: str = ""
    tanggal_lahir: Optional[date] = None
    alamat: str = ""

    @property
    def profil_lengkap(self) -> bool:
        """Atribut turunan /profilLengkap."""
        return all([self.nomor_member, self.no_identitas, self.tanggal_lahir, self.alamat])


@dataclass
class ManajerTravel:
    id_manajer: str
    nama: str
    email: str


@dataclass
class Maskapai:
    kode_maskapai: str
    nama_maskapai: str


@dataclass
class Bandara:
    kode_bandara: str
    nama_bandara: str
    kota: str


@dataclass
class Penerbangan:
    nomor_penerbangan: str
    maskapai: Maskapai
    asal: Bandara
    tujuan: Bandara
    tanggal_berangkat: date
    jam_berangkat: time
    jam_tiba: time
    harga: int
    kursi_tersedia: int


@dataclass
class Tiket:
    nomor_tiket: str
    nama_penumpang: str
    penerbangan: Penerbangan
    harga: int
    status_validasi: bool = False
    e_tiket: str = ""


@dataclass
class Booking:
    kode_booking_reference: str
    pemesan: Pengguna
    tiket: List[Tiket]
    status: StatusBooking
    tanggal_booking: date
    dibuat_oleh: Optional[ManajerTravel] = None  # terisi bila dipesankan Manajer Travel (US-08)

    @property
    def total_harga(self) -> int:
        return sum(t.harga for t in self.tiket)
