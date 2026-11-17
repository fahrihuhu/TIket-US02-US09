"""Web UI Sistem Pemesanan Tiket Pesawat: python3 server.py  ->  http://localhost:8000"""
import json
from datetime import date, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tiket.controls import (BatalkanTiketControl, CariPenerbanganControl, FilterStatusBookingControl,
                            LihatStatusBookingControl, LihatTiketTerpesanControl, OtorisasiTiketControl,
                            PesanTiketControl, ValidasiKodeBookingReferenceControl)
from tiket.errors import DomainError
from tiket.models import Bandara, Maskapai, MemberFrequentTraveller, Penerbangan, Pengguna, StatusBooking
from tiket.repositories import BookingRepository, PenerbanganRepository

# ---- data awal ----
B = {k: Bandara(k, n, c) for k, n, c in [("SUB", "Juanda", "Surabaya"), ("CGK", "Soekarno-Hatta", "Jakarta"),
                                          ("DPS", "Ngurah Rai", "Denpasar"), ("KNO", "Kualanamu", "Medan")]}
GA, JT = Maskapai("GA", "Garuda Indonesia"), Maskapai("JT", "Lion Air")
prepo, brepo = PenerbanganRepository(), BookingRepository()
for no, m, a, t, d, h1, h2, hrg, ks in [
        ("GA300", GA, "SUB", "CGK", 20, 7, 9, 1_200_000, 5), ("JT500", JT, "SUB", "CGK", 20, 9, 11, 800_000, 1),
        ("GA410", GA, "SUB", "DPS", 20, 11, 13, 900_000, 5), ("JT620", JT, "SUB", "KNO", 20, 6, 9, 1_500_000, 4),
        ("GA301", GA, "SUB", "CGK", 21, 8, 10, 1_100_000, 5)]:
    prepo.simpan(Penerbangan(no, m, B[a], B[t], date(2026, 12, d), time(h1), time(h2), hrg, ks))
USERS = {"ani": Pengguna("U1", "Ani", "ani@mail.com"),
         "budi": MemberFrequentTraveller("M1", "Budi", "budi@mail.com")}
cari, pesan, batal = CariPenerbanganControl(prepo), PesanTiketControl(prepo, brepo), BatalkanTiketControl(brepo)
oto = OtorisasiTiketControl(ValidasiKodeBookingReferenceControl(brepo))


def j_flight(p):
    return dict(nomor=p.nomor_penerbangan, maskapai=p.maskapai.nama_maskapai, asal=p.asal.kota, kode_asal=p.asal.kode_bandara,
                tujuan=p.tujuan.kota, kode_tujuan=p.tujuan.kode_bandara, tanggal=str(p.tanggal_berangkat),
                berangkat=f"{p.jam_berangkat:%H:%M}", tiba=f"{p.jam_tiba:%H:%M}", harga=p.harga, kursi=p.kursi_tersedia)


def j_booking(b):
    return dict(kode=b.kode_booking_reference, status=b.status.value, pemesan=b.pemesan.nama, total=b.total_harga,
                tiket=[dict(nomor=t.nomor_tiket, penerbangan=j_flight(t.penerbangan)) for t in b.tiket])


def api(path, q, body):
    g = lambda k, d=None: (q.get(k) or [d])[0]
    if path == "/api/penerbangan":
        tujuan = [t for t in g("tujuan", "").split(",") if t]
        r = cari.cari(tujuan, date.fromisoformat(g("tanggal")))
        return [j_flight(p) for p in r]
    if path == "/api/pesan":
        return j_booking(pesan.pesan(USERS[body["pemesan"]], body["nomor"]))
    if path == "/api/pesanan":
        return [j_booking(b) for b in batal.daftar_pesanan(USERS[g("pemesan")])]
    if path == "/api/batalkan":
        return j_booking(batal.batalkan(USERS[body["pemesan"]], body["kode"]))
    if path == "/api/status":
        s = g("status")
        return [j_booking(b) for b in (FilterStatusBookingControl(brepo).filter(StatusBooking(s)) if s
                                       else LihatStatusBookingControl(brepo).semua())]
    if path == "/api/otorisasi":
        return j_booking(oto.otorisasi(body.get("kode", "")))
    raise KeyError(path)


class H(BaseHTTPRequestHandler):
    def _send(self, code, data, ctype="application/json"):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def _run(self, body):
        u = urlparse(self.path)
        try:
            self._send(200, api(u.path, parse_qs(u.query), body))
        except (DomainError, ValueError) as e:
            self._send(400, {"error": str(e)})
        except KeyError:
            self._send(404, {"error": "tidak ditemukan"})

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._run({})
        self._send(200, (Path(__file__).parent / "static" / "index.html").read_bytes(), "text/html")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self._run(json.loads(self.rfile.read(n) or b"{}"))

    def log_message(self, *a): pass


if __name__ == "__main__":
    print("Buka http://localhost:8000  (Ctrl+C untuk berhenti)")
    ThreadingHTTPServer(("127.0.0.1", 8000), H).serve_forever()
