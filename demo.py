"""Demo alur utama: python3 demo.py"""
from datetime import date, time

from tiket.controls import *
from tiket.email import FakeEmailGateway
from tiket.errors import DomainError
from tiket.models import Bandara, ManajerTravel, Maskapai, MemberFrequentTraveller, Penerbangan, Pengguna, StatusBooking
from tiket.repositories import BookingRepository, PenerbanganRepository


def rp(x): return f"Rp{x:,}".replace(",", ".")


def judul(t): print(f"\n=== {t} ===")


# --- data awal ---
tgl = date(2026, 12, 20)
sub, cgk, dps = Bandara("SUB", "Juanda", "Surabaya"), Bandara("CGK", "Soekarno-Hatta", "Jakarta"), Bandara("DPS", "Ngurah Rai", "Denpasar")
ga, jt = Maskapai("GA", "Garuda Indonesia"), Maskapai("JT", "Lion Air")
prepo, brepo = PenerbanganRepository(), BookingRepository()
for p in [Penerbangan("GA300", ga, sub, cgk, tgl, time(7), time(8, 30), 1_200_000, 5),
          Penerbangan("JT500", jt, sub, cgk, tgl, time(9), time(10, 30), 800_000, 1),
          Penerbangan("GA410", ga, sub, dps, tgl, time(11), time(13), 900_000, 5)]:
    prepo.simpan(p)
ani, budi = Pengguna("U1", "Ani", "ani@mail.com"), MemberFrequentTraveller("M1", "Budi", "budi@mail.com")
citra = ManajerTravel("MG1", "Citra", "citra@travel.com")
cari, pesan, email = CariPenerbanganControl(prepo), PesanTiketControl(prepo, brepo), FakeEmailGateway()

judul("US-02a/US-03: cari penerbangan (multi-tujuan CGK + DPS)")
hasil = cari.cari(["CGK", "DPS"], tgl)
for p in hasil:
    print(f"{p.nomor_penerbangan} {p.maskapai.nama_maskapai:16} {p.asal.kota}->{p.tujuan.kota} {p.jam_berangkat:%H:%M} {rp(p.harga)}")

judul("US-06: bandingkan")
r = BandingkanPenerbanganControl().bandingkan(hasil)
print("jumlah:", r["jumlah_penerbangan"], "| termurah:", r["termurah"].nomor_penerbangan, "| selisih:", rp(r["selisih_harga"]))

judul("US-02b/c: pesan lalu batalkan")
b = pesan.pesan(ani, "GA300")
print("booking", b.kode_booking_reference, b.status.value, rp(b.total_harga))
BatalkanTiketControl(brepo).batalkan(ani, b.kode_booking_reference)
print("setelah dibatalkan:", b.status.value, "| kursi GA300:", prepo.by_nomor("GA300").kursi_tersedia)

judul("US-02b alternatif: kursi habis")
pesan.pesan(ani, "JT500")
try:
    pesan.pesan(budi, "JT500")
except DomainError as e:
    print("ditolak:", e)

judul("US-05: validasi tiket member")
tiket = pesan.pesan(budi, "GA410").tiket[0]
try:
    ValidasiTiketControl().validasi(budi, tiket)
except DomainError as e:
    print("ditolak:", e)
PerbaruiProfilControl().perbarui(budi, nomor_member="FT-001", no_identitas="3578xxxx", tanggal_lahir=date(2000, 1, 1), alamat="Surabaya")
print("tervalidasi:", ValidasiTiketControl().validasi(budi, tiket).status_validasi)

judul("US-08: manajer memesankan tiket + kirim e-tiket")
bk = PesanTiketPengunjungControl(pesan, email).pesan(citra, ani, "GA410")
print("booking", bk.kode_booking_reference, "| email ke:", email.kotak_keluar[-1].tujuan)
print("tiket Ani:", [t.nomor_tiket for t in LihatTiketTerpesanControl(brepo).lihat(ani)])

judul("US-07: status booking")
for s in StatusBooking:
    print(f"{s.value:20}", len(FilterStatusBookingControl(brepo).filter(s)))

judul("US-09: otorisasi kode booking")
oto = OtorisasiTiketControl(ValidasiKodeBookingReferenceControl(brepo))
print(oto.otorisasi(bk.kode_booking_reference).status.value)
try:
    oto.otorisasi("SALAH")
except DomainError as e:
    print("ditolak:", e)
