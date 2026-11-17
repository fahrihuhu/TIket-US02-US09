import unittest
from datetime import date, time

from tiket.controls import (BandingkanPenerbanganControl, BatalkanTiketControl, CariPenerbanganControl,
                            FilterStatusBookingControl, LihatStatusBookingControl, LihatTiketTerpesanControl,
                            OtorisasiTiketControl, PerbaruiProfilControl, PesanTiketControl,
                            PesanTiketPengunjungControl, ValidasiKodeBookingReferenceControl, ValidasiTiketControl)
from tiket.email import FakeEmailGateway
from tiket.errors import (KodeBookingTidakSesuai, KursiHabis, PesananTidakDapatDibatalkan,
                          PesananTidakDitemukan, ProfilTidakLengkap)
from tiket.models import (Bandara, ManajerTravel, Maskapai, MemberFrequentTraveller, Penerbangan, Pengguna,
                          StatusBooking)
from tiket.repositories import BookingRepository, PenerbanganRepository

TGL = date(2026, 12, 20)


class Dasar(unittest.TestCase):
    def setUp(self):
        sub, cgk, dps, kno = (Bandara("SUB", "Juanda", "Surabaya"), Bandara("CGK", "Soekarno-Hatta", "Jakarta"),
                              Bandara("DPS", "Ngurah Rai", "Denpasar"), Bandara("KNO", "Kualanamu", "Medan"))
        ga, jt = Maskapai("GA", "Garuda Indonesia"), Maskapai("JT", "Lion Air")
        self.prepo, self.brepo = PenerbanganRepository(), BookingRepository()
        for p in [Penerbangan("GA300", ga, sub, cgk, TGL, time(7), time(8, 30), 1_200_000, 2),
                  Penerbangan("JT500", jt, sub, cgk, TGL, time(9), time(10, 30), 800_000, 1),
                  Penerbangan("GA410", ga, sub, dps, TGL, time(11), time(13), 900_000, 5),
                  Penerbangan("JT900", jt, cgk, kno, TGL, time(6), time(9), 1_000_000, 5)]:
            self.prepo.simpan(p)
        self.pesan = PesanTiketControl(self.prepo, self.brepo)
        self.ani = Pengguna("U1", "Ani", "ani@mail.com")
        self.member = MemberFrequentTraveller("M1", "Budi", "budi@mail.com")
        self.manajer = ManajerTravel("MG1", "Citra", "citra@travel.com")


class TestPencarian(Dasar):
    def test_cari_satu_tujuan(self):
        hasil = CariPenerbanganControl(self.prepo).cari("CGK", TGL)
        self.assertEqual([p.nomor_penerbangan for p in hasil], ["GA300", "JT500"])

    def test_cari_multi_tujuan(self):
        hasil = CariPenerbanganControl(self.prepo).cari(["CGK", "DPS"], TGL)
        self.assertEqual({p.nomor_penerbangan for p in hasil}, {"GA300", "JT500", "GA410"})

    def test_tidak_ada_hasil(self):
        self.assertEqual(CariPenerbanganControl(self.prepo).cari("KNO", date(2027, 1, 1)), [])

    def test_multi_destinasi_filter_asal_dan_jam(self):
        c = CariPenerbanganControl(self.prepo)
        self.assertEqual([p.nomor_penerbangan for p in c.cari_multi_destinasi(TGL, "SUB", ["CGK", "DPS", "KNO"])],
                         ["GA300", "JT500", "GA410"])
        self.assertEqual([p.nomor_penerbangan for p in c.cari_multi_destinasi(TGL, "SUB", ["CGK"], time(8))],
                         ["JT500"])

    def test_bandingkan(self):
        semua = CariPenerbanganControl(self.prepo).cari("CGK", TGL)
        r = BandingkanPenerbanganControl().bandingkan(semua)
        self.assertEqual(r["jumlah_penerbangan"], 2)
        self.assertEqual(r["termurah"].nomor_penerbangan, "JT500")
        self.assertEqual(r["selisih_harga"], 400_000)


class TestPemesanan(Dasar):
    def test_pesan_membuat_booking_booked_dan_mengurangi_kursi(self):
        b = self.pesan.pesan(self.ani, "GA300")
        self.assertEqual(b.status, StatusBooking.BOOKED)
        self.assertEqual(b.total_harga, 1_200_000)
        self.assertEqual(self.prepo.by_nomor("GA300").kursi_tersedia, 1)

    def test_kursi_habis(self):
        self.pesan.pesan(self.ani, "JT500")
        with self.assertRaises(KursiHabis):
            self.pesan.pesan(self.member, "JT500")

    def test_batalkan_mengembalikan_kursi(self):
        b = self.pesan.pesan(self.ani, "GA300")
        BatalkanTiketControl(self.brepo).batalkan(self.ani, b.kode_booking_reference)
        self.assertEqual(b.status, StatusBooking.CANCELLED)
        self.assertEqual(self.prepo.by_nomor("GA300").kursi_tersedia, 2)

    def test_batalkan_dua_kali_ditolak(self):
        c = BatalkanTiketControl(self.brepo)
        b = self.pesan.pesan(self.ani, "GA300")
        c.batalkan(self.ani, b.kode_booking_reference)
        with self.assertRaises(PesananTidakDapatDibatalkan):
            c.batalkan(self.ani, b.kode_booking_reference)

    def test_batalkan_pesanan_orang_lain_ditolak(self):
        b = self.pesan.pesan(self.ani, "GA300")
        with self.assertRaises(PesananTidakDitemukan):
            BatalkanTiketControl(self.brepo).batalkan(self.member, b.kode_booking_reference)


class TestProfilDanValidasi(Dasar):
    def test_validasi_ditolak_bila_profil_tidak_lengkap(self):
        t = self.pesan.pesan(self.member, "GA300").tiket[0]
        with self.assertRaises(ProfilTidakLengkap) as cm:
            ValidasiTiketControl().validasi(self.member, t)
        self.assertEqual(str(cm.exception), "data profil tidak lengkap")
        self.assertFalse(t.status_validasi)

    def test_validasi_berhasil_setelah_profil_dilengkapi(self):
        PerbaruiProfilControl().perbarui(self.member, nomor_member="FT-001", no_identitas="3578xxxx",
                                         tanggal_lahir=date(2000, 1, 1), alamat="Surabaya")
        t = self.pesan.pesan(self.member, "GA300").tiket[0]
        self.assertTrue(ValidasiTiketControl().validasi(self.member, t).status_validasi)

    def test_perbarui_atribut_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            PerbaruiProfilControl().perbarui(self.member, saldo=1)


class TestManajerTravel(Dasar):
    def test_status_dan_filter(self):
        a = self.pesan.pesan(self.ani, "GA300")
        self.pesan.pesan(self.member, "GA410")
        BatalkanTiketControl(self.brepo).batalkan(self.ani, a.kode_booking_reference)
        self.assertEqual(len(LihatStatusBookingControl(self.brepo).semua()), 2)
        f = FilterStatusBookingControl(self.brepo)
        self.assertEqual(len(f.filter(StatusBooking.CANCELLED)), 1)
        self.assertEqual(len(f.filter(StatusBooking.BOOKED)), 1)
        self.assertEqual(f.filter(StatusBooking.CONFIRMED), [])

    def test_pesan_untuk_pengunjung_mengirim_etiket(self):
        email = FakeEmailGateway()
        b = PesanTiketPengunjungControl(self.pesan, email).pesan(self.manajer, self.ani, "GA410")
        self.assertIs(b.dibuat_oleh, self.manajer)
        self.assertEqual(b.pemesan, self.ani)
        self.assertEqual(len(email.kotak_keluar), 1)
        self.assertEqual(email.kotak_keluar[0].tujuan, "ani@mail.com")
        self.assertIn(b.tiket[0].e_tiket, email.kotak_keluar[0].isi)

    def test_pengunjung_melihat_tiket_tanpa_yang_dibatalkan(self):
        a = self.pesan.pesan(self.ani, "GA300")
        self.pesan.pesan(self.ani, "GA410")
        BatalkanTiketControl(self.brepo).batalkan(self.ani, a.kode_booking_reference)
        tiket = LihatTiketTerpesanControl(self.brepo).lihat(self.ani)
        self.assertEqual([t.penerbangan.nomor_penerbangan for t in tiket], ["GA410"])

    def test_otorisasi_kode_benar_dan_salah(self):
        b = self.pesan.pesan(self.ani, "GA300")
        c = OtorisasiTiketControl(ValidasiKodeBookingReferenceControl(self.brepo))
        self.assertIs(c.otorisasi(b.kode_booking_reference), b)
        with self.assertRaises(KodeBookingTidakSesuai) as cm:
            c.otorisasi("XXX")
        self.assertEqual(str(cm.exception), "kode booking reference tidak sesuai")
        with self.assertRaises(KodeBookingTidakSesuai):
            c.otorisasi("")


if __name__ == "__main__":
    unittest.main()
