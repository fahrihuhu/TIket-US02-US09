"""Antarmuka ke Layanan Email (aktor sekunder). Pada produksi diganti implementasi SMTP/API."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol


class EmailGateway(Protocol):
    def kirim(self, tujuan: str, subjek: str, isi: str) -> None: ...


@dataclass
class Pesan:
    tujuan: str
    subjek: str
    isi: str


class FakeEmailGateway:
    """Menyimpan email di memori; dipakai untuk demo dan pengujian."""

    def __init__(self) -> None:
        self.kotak_keluar: List[Pesan] = []

    def kirim(self, tujuan: str, subjek: str, isi: str) -> None:
        self.kotak_keluar.append(Pesan(tujuan, subjek, isi))
