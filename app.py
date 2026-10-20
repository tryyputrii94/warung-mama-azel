"""
Katalog Harga Toko — Streamlit + Pillow
=======================================
Jalankan:  streamlit run app.py

Ubah NAMA_TOKO, ALAMAT_TOKO, NO_WA, dan data KATALOG di bawah sesuai kebutuhan.

GAMBAR PRODUK
-------------
Taruh foto produk di folder  images/  (satu folder dengan app.py).
Nama file = nama produk dalam huruf kecil, spasi & simbol diganti tanda "-".
Contoh:  "Beras Sumo Merah 5kg"  ->  images/beras-sumo-merah-5kg.jpg
Format yang didukung: .jpg .jpeg .png .webp
Daftar lengkap nama file bisa dilihat dengan membuka web + ?admin=1
(contoh: http://localhost:8501/?admin=1)
Atau tentukan nama file sendiri:  P("Nama Produk", 10_000, gambar="foto-saya.png")
"""

from __future__ import annotations

import base64
import html
import io
import re
import urllib.request
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

# ============================================================================
# 1. KONFIGURASI TOKO
# ============================================================================
NAMA_TOKO = "WARUNG MAMA AZEL"     # <- ganti dengan nama toko Anda
ALAMAT_TOKO = "Xyz charm 11 no 26"
NO_WA = ""                            # opsional, mis. "0812-3456-7890" (kosongkan jika tidak perlu)
CATATAN = "Harga dapat berubah sewaktu-waktu"
ZONA_WAKTU = "Asia/Jakarta"
GAMBAR_DI_POSTER = True               # tampilkan foto produk juga di gambar katalog

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"
EKSTENSI_GAMBAR = (".jpg", ".jpeg", ".png", ".webp")

# Warna dasar tema (hijau segar)
TEMA = {
    "primer": "#0F7B5F",
    "primer_gelap": "#0A4F3D",
    "aksen": "#F6C445",
    "latar": "#EEF4F1",
    "kartu": "#FFFFFF",
    "zebra": "#F3F7F5",
    "teks": "#1E2B28",
    "redup": "#6C7D78",
    "teks_header": "#D4ECE3",
}


# ============================================================================
# 2. DATA PRODUK (dikelompokkan per kategori)
# ============================================================================
def P(nama: str, harga: int, satuan: str = "", gambar: str = "") -> dict:
    """Helper membuat satu item produk.
    gambar: (opsional) nama file di folder images/. Jika kosong, nama file
    ditebak otomatis dari nama produk (lihat slug())."""
    return {"nama": nama, "harga": harga, "satuan": satuan, "gambar": gambar}


KATALOG: dict[str, dict] = {
    "Sembako & Kebutuhan Pokok": {
        "ikon": "🌾",
        "warna": "#0F7B5F",
        "produk": [
            P("Beras Sumo Merah 5kg", 100_000),
            P("Beras Lahap 5kg", 87_000),
            P("Minyak Goreng Rose Brand 2L", 42_000),
            P("Minyak Goreng Sunco 2L", 42_500),
            P("Telur 1kg", 28_000),
            P("Tepung Terigu Segitiga Biru 1kg", 14_500),
            P("Tepung Serbaguna Kobe", 7_000),
            P("Tepung Bakwan Kobe", 7_000),
            P("Garam Dolpin 500gr", 10_000),
            P("Santan Kara", 7_000),
            P("Margarine Blue Band", 8_000),
            P("Margarine Forvita", 6_000),
        ],
    },
    "Bumbu, Kecap & Saos": {
        "ikon": "🧂",
        "warna": "#C9541A",
        "produk": [
            P("Kecap Bango Refill 950gr", 30_000),
            P("Masako Sapi 500gr", 10_000),
            P("Royco Ayam 220gr", 11_000),
            P("Totole Kaldu Jamur", 8_000),
            P("Saori Teriyaki 135ml", 12_000),
            P("Saori Saus Tiram 135ml", 13_000),
            P("Saori Saus Tiram 270ml", 22_000),
            P("Saos Belibis Pedas 135ml", 11_000),
            P("Saos Belibis Ekstra Pedas 235ml", 22_500),
        ],
    },
    "Susu & Minuman": {
        "ikon": "🥛",
        "warna": "#2763A8",
        "produk": [
            P("Susu UHT Ultra Milk 1L", 21_000),
            P("Susu Kental Manis 535gr", 14_000),
            P("Cappuccino Good Day", 3_000, "pcs"),
            P("Teh Sariwangi", 9_000),
            P("Teh Tong Tji", 14_000),
        ],
    },
    "Bumbu Dapur Segar": {
        "ikon": "🧅",
        "warna": "#B8323A",
        "produk": [
            P("Bawang Merah (1/4 kg)", 8_000),
            P("Bawang Putih (1/4 kg)", 9_000),
            P("Cabe (1/4 kg)", 18_000),
        ],
    },
    "Kebersihan Rumah & Laundry": {
        "ikon": "🧽",
        "warna": "#6F3FA0",
        "produk": [
            P("Gentle Gen Botol", 14_000),
            P("Molto 1,5kg", 33_000),
            P("So Klin Lantai Sereh 770ml", 11_000),
            P("Wipol 720gr", 10_000),
        ],
    },
    "Perawatan Diri & Tissue": {
        "ikon": "🧴",
        "warna": "#13877A",
        "produk": [
            P("Sabun Lifebuoy Refill 800gr", 35_000),
            P("Pepsodent 225gr", 17_000),
            P("Tissue Nice", 7_000),
            P("Tissue Paseo", 11_000),
            P("Tissue See U", 11_000),
        ],
    },
}


# ============================================================================
# 3. UTILITAS
# ============================================================================
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def rupiah(n: int) -> str:
    return "Rp " + f"{n:,.0f}".replace(",", ".")


def sekarang() -> datetime:
    try:
        return datetime.now(ZoneInfo(ZONA_WAKTU))
    except Exception:
        return datetime.now()


def tanggal_indo(dt: datetime, pakai_hari: bool = True) -> str:
    teks = f"{dt.day:02d} {BULAN[dt.month - 1]} {dt.year}"
    return f"{HARI[dt.weekday()]}, {teks}" if pakai_hari else teks


def campur_putih(hex_warna: str, porsi_putih: float) -> tuple:
    """Campur warna dengan putih (0 = warna asli, 1 = putih penuh)."""
    r, g, b = ImageColor.getrgb(hex_warna)[:3]
    return tuple(int(c + (255 - c) * porsi_putih) for c in (r, g, b))


# ============================================================================
# 3b. GAMBAR PRODUK (folder images/)
# ============================================================================
def slug(teks: str) -> str:
    """'Beras Sumo Merah 5kg' -> 'beras-sumo-merah-5kg'"""
    return re.sub(r"[^a-z0-9]+", "-", teks.lower()).strip("-")


def nama_file_gambar(p: dict) -> str:
    """Nama file yang diharapkan (tanpa ekstensi jika otomatis)."""
    return p["gambar"] or slug(p["nama"])


def cari_gambar(p: dict) -> Path | None:
    """Cari file gambar produk di folder images/. None jika belum ada."""
    if not IMAGES_DIR.is_dir():
        return None
    if p.get("gambar"):
        f = IMAGES_DIR / p["gambar"]
        return f if f.is_file() else None
    dasar = slug(p["nama"])
    for ext in EKSTENSI_GAMBAR:
        for e in (ext, ext.upper()):
            f = IMAGES_DIR / f"{dasar}{e}"
            if f.is_file():
                return f
    return None


def tanda_gambar() -> str:
    """Sidik isi folder images/ (nama + waktu ubah) agar cache diperbarui
    otomatis saat Anda menambah/mengganti foto."""
    if not IMAGES_DIR.is_dir():
        return ""
    return "|".join(f"{f.name}:{f.stat().st_mtime_ns}"
                    for f in sorted(IMAGES_DIR.iterdir()) if f.is_file())


def muat_thumbnail(path: Path, ukuran: int) -> Image.Image | None:
    """Foto produk dimuat ke kanvas persegi putih (tidak terpotong/gepeng)."""
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGBA")
        kanvas = Image.new("RGBA", (ukuran, ukuran), (255, 255, 255, 255))
        isi = int(ukuran * 0.9)
        im = ImageOps.contain(im, (isi, isi), Image.LANCZOS)
        kanvas.alpha_composite(im, ((ukuran - im.width) // 2, (ukuran - im.height) // 2))
        return kanvas
    except Exception:
        return None


# ============================================================================
# 4. FONT (Poppins dari Google Fonts, dengan fallback otomatis)
# ============================================================================
FONT_DIR = BASE_DIR / "fonts"
POPPINS_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-{}.ttf"
BOBOT = {"regular": "Regular", "medium": "Medium", "semibold": "SemiBold",
         "bold": "Bold", "extrabold": "ExtraBold"}
FALLBACK = {
    "normal": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "arial.ttf",
               "Arial.ttf", "Helvetica.ttc"],
    "tebal": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf",
              "Arial Bold.ttf", "Helvetica.ttc"],
}


@lru_cache(maxsize=None)
def _path_font(bobot: str) -> str | None:
    """Cari font Poppins di folder ./fonts, unduh sekali jika belum ada,
    lalu fallback ke font sistem bila offline."""
    file_lokal = FONT_DIR / f"Poppins-{BOBOT[bobot]}.ttf"
    if not file_lokal.exists():
        try:
            FONT_DIR.mkdir(exist_ok=True)
            with urllib.request.urlopen(POPPINS_URL.format(BOBOT[bobot]), timeout=10) as r:
                data = r.read()
            tmp = file_lokal.with_suffix(".tmp")
            tmp.write_bytes(data)
            ImageFont.truetype(str(tmp), 12)  # validasi file font
            tmp.replace(file_lokal)
        except Exception:
            pass
    if file_lokal.exists():
        return str(file_lokal)

    kelompok = "tebal" if bobot in ("semibold", "bold", "extrabold") else "normal"
    for kandidat in FALLBACK[kelompok]:
        try:
            ImageFont.truetype(kandidat, 12)
            return kandidat
        except OSError:
            continue
    return None


@lru_cache(maxsize=None)
def font(bobot: str, ukuran: int) -> ImageFont.FreeTypeFont:
    path = _path_font(bobot)
    if path:
        return ImageFont.truetype(path, ukuran)
    return ImageFont.load_default(size=ukuran)


def font_muat(draw, teks, bobot, ukuran, lebar_maks, ukuran_min=14):
    """Kecilkan ukuran font sampai teks muat dalam lebar_maks."""
    while ukuran > ukuran_min and draw.textlength(teks, font=font(bobot, ukuran)) > lebar_maks:
        ukuran -= 1
    return font(bobot, ukuran)


def bungkus_teks(draw, teks, fnt, lebar_maks) -> list[str]:
    """Word-wrap sederhana berdasarkan lebar piksel."""
    baris, kini = [], ""
    for kata in teks.split():
        coba = f"{kini} {kata}".strip()
        if not kini or draw.textlength(coba, font=fnt) <= lebar_maks:
            kini = coba
        else:
            baris.append(kini)
            kini = kata
    if kini:
        baris.append(kini)
    return baris or [""]


def gambar_pin(draw, cx, cy, s, warna, warna_lubang):
    """Ikon pin lokasi (digambar manual agar tidak butuh emoji font)."""
    r = s * 0.55
    hy = cy - s * 0.28
    draw.polygon([(cx - r * 0.86, hy + r * 0.5), (cx + r * 0.86, hy + r * 0.5),
                  (cx, cy + s * 0.72)], fill=warna)
    draw.ellipse((cx - r, hy - r, cx + r, hy + r), fill=warna)
    rl = r * 0.42
    draw.ellipse((cx - rl, hy - rl, cx + rl, hy + rl), fill=warna_lubang)


# ============================================================================
# 5. IMAGE GENERATOR — poster vertikal untuk WhatsApp
# ============================================================================
def buat_poster(katalog: dict = KATALOG, kolom: int = 2,
                waktu: datetime | None = None) -> Image.Image:
    waktu = waktu or sekarang()
    t = TEMA
    W, M, GAP = 1080, 44, 24
    besar = kolom == 1

    f = {
        "kat": 30 if besar else 26,
        "jml": 20 if besar else 17,
        "nama": font("bold", 31 if besar else 23),
        "harga": font("extrabold", 32 if besar else 24),
        "unit": font("medium", 22 if besar else 17),
    }
    PAD = 26 if besar else 20
    LINE_H = int(f["nama"].size * 1.4)
    ROW_PAD = 12 if besar else 10
    HEAD_H = 72 if besar else 62
    col_w = (W - 2 * M - (kolom - 1) * GAP) // kolom

    ukur = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    # Kolom foto hanya dipakai jika minimal ada 1 foto di folder images/
    pakai_foto = GAMBAR_DI_POSTER and any(
        cari_gambar(p) for info in katalog.values() for p in info["produk"])
    TH = (84 if besar else 60) if pakai_foto else 0
    GESER = TH + 14 if TH else 0

    # ---- 5a. Ukur tinggi setiap kartu kategori -----------------------------
    blok = []
    for nama_kat, info in katalog.items():
        baris_list, h = [], HEAD_H + 10
        for p in info["produk"]:
            harga_txt = rupiah(p["harga"])
            unit_txt = f"/{p['satuan']}" if p["satuan"] else ""
            lebar_harga = ukur.textlength(harga_txt, font=f["harga"])
            if unit_txt:
                lebar_harga += ukur.textlength(unit_txt, font=f["unit"]) + 5
            lines = bungkus_teks(ukur, p["nama"], f["nama"],
                                 col_w - 2 * PAD - GESER - lebar_harga - 16)
            rh = max(len(lines) * LINE_H, TH) + 2 * ROW_PAD
            baris_list.append((p, lines, rh, harga_txt, unit_txt))
            h += rh
        h += 12
        blok.append({"nama": nama_kat, "info": info, "baris": baris_list, "h": h})

    # ---- 5b. Tata letak masonry (kategori masuk ke kolom terpendek) --------
    HEADER_H, ADDR_TOP, ADDR_H = 300, 232, 132
    y_awal = ADDR_TOP + ADDR_H + 36
    tinggi = [y_awal] * kolom
    posisi = []
    for b in blok:
        c = tinggi.index(min(tinggi))
        posisi.append((b, M + c * (col_w + GAP), tinggi[c]))
        tinggi[c] += b["h"] + GAP
    FOOTER_H = 250 if NO_WA else 220
    H = max(tinggi) - GAP + 44 + FOOTER_H

    img = Image.new("RGBA", (W, H), t["latar"])
    d = ImageDraw.Draw(img)

    # ---- 5c. Header -------------------------------------------------------
    d.rectangle((0, 0, W, HEADER_H), fill=t["primer"])
    dekor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dekor)
    dd.ellipse((W - 330, -190, W + 130, 270), fill=(255, 255, 255, 22))
    dd.ellipse((W - 150, 120, W + 70, 340), fill=(255, 255, 255, 16))
    dd.ellipse((-90, 210, 90, 390), fill=(255, 255, 255, 12))
    img.alpha_composite(dekor)
    d = ImageDraw.Draw(img)

    label = "DAFTAR HARGA TERBARU"
    f_label = font("semibold", 19)
    lw = d.textlength(label, font=f_label)
    d.rounded_rectangle((M, 46, M + lw + 36, 86), radius=20, fill=t["aksen"])
    d.text((M + 18 + lw / 2, 66), label, font=f_label, fill=t["primer_gelap"], anchor="mm")

    f_toko = font_muat(d, NAMA_TOKO, "extrabold", 62, W - 2 * M)
    d.text((M, 140), NAMA_TOKO, font=f_toko, fill="white", anchor="lm")
    d.text((M, 198), f"Update harga: {tanggal_indo(waktu)}",
           font=font("regular", 24), fill=t["teks_header"], anchor="lm")

    # ---- 5d. Bayangan lembut untuk kartu alamat & kartu kategori -----------
    bayangan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bayangan)
    bd.rounded_rectangle((M, ADDR_TOP + 8, W - M, ADDR_TOP + ADDR_H + 8), 26, fill=(10, 50, 40, 55))
    for b, x, y in posisi:
        bd.rounded_rectangle((x, y + 6, x + col_w, y + b["h"] + 6), 22, fill=(10, 50, 40, 38))
    img.alpha_composite(bayangan.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(img)

    # ---- 5e. Kartu alamat (bagian atas) -----------------------------------
    d.rounded_rectangle((M, ADDR_TOP, W - M, ADDR_TOP + ADDR_H), 26, fill=t["kartu"])
    d.rounded_rectangle((M, ADDR_TOP, M + 10, ADDR_TOP + ADDR_H), 5, fill=t["aksen"])
    cy = ADDR_TOP + ADDR_H / 2
    ix = M + 40 + 34
    d.ellipse((ix - 38, cy - 38, ix + 38, cy + 38), fill=t["primer"])
    gambar_pin(d, ix, cy, 40, "white", t["primer"])
    tx = ix + 60
    d.text((tx, cy - 24), "ALAMAT TOKO", font=font("semibold", 19), fill=t["redup"], anchor="lm")
    f_alamat = font_muat(d, ALAMAT_TOKO, "bold", 38, W - M - tx - 30)
    d.text((tx, cy + 16), ALAMAT_TOKO, font=f_alamat, fill=t["teks"], anchor="lm")

    # ---- 5f. Kartu kategori & baris produk --------------------------------
    for b, x, y in posisi:
        warna = b["info"]["warna"]
        d.rounded_rectangle((x, y, x + col_w, y + b["h"]), 22, fill=t["kartu"])
        d.rounded_rectangle((x, y, x + col_w, y + HEAD_H), 22, fill=warna,
                            corners=(True, True, False, False))

        jml_txt = f"{len(b['info']['produk'])} item"
        f_jml = font("medium", f["jml"])
        jw = d.textlength(jml_txt, font=f_jml)
        f_kat = font_muat(d, b["nama"], "bold", f["kat"], col_w - 2 * PAD - jw - 34)
        d.text((x + PAD, y + HEAD_H / 2), b["nama"], font=f_kat, fill="white", anchor="lm")
        d.rounded_rectangle((x + col_w - PAD - jw - 20, y + HEAD_H / 2 - 15,
                             x + col_w - PAD + 2, y + HEAD_H / 2 + 15), 15,
                            fill=campur_putih(warna, 0.22))
        d.text((x + col_w - PAD - 9 - jw / 2, y + HEAD_H / 2), jml_txt,
               font=f_jml, fill="white", anchor="mm")

        ry = y + HEAD_H + 10
        for i, (p, lines, rh, harga_txt, unit_txt) in enumerate(b["baris"]):
            if i % 2 == 1:
                d.rounded_rectangle((x + 10, ry, x + col_w - 10, ry + rh), 12, fill=t["zebra"])

            # Foto produk (atau placeholder huruf awal jika belum ada foto)
            if TH:
                fx, fy_ = int(x + PAD), int(ry + (rh - TH) / 2)
                path = cari_gambar(p)
                thumb = muat_thumbnail(path, TH) if path else None
                if thumb:
                    mask = Image.new("L", (TH, TH), 0)
                    ImageDraw.Draw(mask).rounded_rectangle((0, 0, TH - 1, TH - 1), 12, fill=255)
                    img.paste(thumb.convert("RGB"), (fx, fy_), mask)
                    d.rounded_rectangle((fx, fy_, fx + TH, fy_ + TH), 12,
                                        outline=campur_putih(warna, 0.75), width=2)
                else:
                    d.rounded_rectangle((fx, fy_, fx + TH, fy_ + TH), 12,
                                        fill=campur_putih(warna, 0.86))
                    d.text((fx + TH / 2, fy_ + TH / 2), p["nama"][:1].upper(),
                           font=font("bold", int(TH * 0.45)), fill=warna, anchor="mm")

            tinggi_teks = len(lines) * LINE_H
            atas_teks = ry + ROW_PAD + (rh - 2 * ROW_PAD - tinggi_teks) / 2
            for j, ln in enumerate(lines):
                d.text((x + PAD + GESER, atas_teks + j * LINE_H + LINE_H / 2), ln,
                       font=f["nama"], fill=t["teks"], anchor="lm")
            kanan = x + col_w - PAD
            cyr = atas_teks + LINE_H / 2
            if unit_txt:
                d.text((kanan, cyr + 2), unit_txt, font=f["unit"], fill=t["redup"], anchor="rm")
                kanan -= d.textlength(unit_txt, font=f["unit"]) + 5
            d.text((kanan, cyr), harga_txt, font=f["harga"], fill=warna, anchor="rm")
            ry += rh

    # ---- 5g. Footer (alamat diulang di bawah) -----------------------------
    fy = H - FOOTER_H
    d.rectangle((0, fy, W, H), fill=t["primer_gelap"])
    d.rectangle((0, fy, W, fy + 8), fill=t["aksen"])
    d.text((W / 2, fy + 58), f"Yuk belanja di {NAMA_TOKO}",
           font=font_muat(d, f"Yuk belanja di {NAMA_TOKO}", "medium", 26, W - 2 * M),
           fill=t["teks_header"], anchor="mm")

    f_ft = font_muat(d, ALAMAT_TOKO, "bold", 40, W - 2 * M - 70)
    aw = d.textlength(ALAMAT_TOKO, font=f_ft)
    total_w = 44 + 16 + aw
    sx = (W - total_w) / 2
    gambar_pin(d, sx + 22, fy + 118, 46, t["aksen"], t["primer_gelap"])
    d.text((sx + 60, fy + 118), ALAMAT_TOKO, font=f_ft, fill=t["aksen"], anchor="lm")

    y_info = fy + 172
    if NO_WA:
        d.text((W / 2, y_info), f"WhatsApp: {NO_WA}", font=font("semibold", 24),
               fill="white", anchor="mm")
        y_info += 38
    d.text((W / 2, y_info), f"{CATATAN}  •  Pesan langsung via WhatsApp",
           font=font("regular", 19), fill="#A9CFC2", anchor="mm")

    return img.convert("RGB")


@st.cache_data(show_spinner=False)
def poster_bytes(fmt: str, kolom: int, tanggal_key: str, foto_key: str = "") -> bytes:
    """tanggal_key & foto_key membuat cache diperbarui setiap hari
    dan setiap kali isi folder images/ berubah."""
    img = buat_poster(KATALOG, kolom=kolom)
    buf = io.BytesIO()
    if fmt == "JPG":
        img.save(buf, "JPEG", quality=92, optimize=True, subsampling=0)
    else:
        img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


@st.cache_data(show_spinner=False)
def foto_data_uri(path_str: str, mtime: int) -> str:
    """Thumbnail foto untuk web (base64), di-cache per file + waktu ubah."""
    thumb = muat_thumbnail(Path(path_str), 320)
    if thumb is None:
        return ""
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ============================================================================
# 6. TAMPILAN WEB (STREAMLIT)
# ============================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
.stApp { font-family: 'Poppins', sans-serif; }
.block-container { max-width: 1100px; padding-top: 1.6rem; padding-bottom: 3rem; }
#MainMenu, footer { visibility: hidden; }

.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, #0F7B5F 0%, #0A4F3D 100%);
  color: #fff; border-radius: 26px; padding: 30px 32px 26px; margin-bottom: 18px;
  box-shadow: 0 14px 32px rgba(10, 79, 61, .25);
}
.hero::before, .hero::after {
  content: ""; position: absolute; border-radius: 50%; background: rgba(255,255,255,.09);
}
.hero::before { width: 300px; height: 300px; right: -90px; top: -130px; }
.hero::after  { width: 160px; height: 160px; right: 70px; bottom: -90px; }
.hero-badge {
  display: inline-block; background: #F6C445; color: #0A4F3D; font-weight: 700;
  font-size: .78rem; letter-spacing: .06em; padding: 5px 14px; border-radius: 999px;
}
.hero-title { font-size: 2.3rem; font-weight: 800; margin: 12px 0 4px; line-height: 1.15; color: #fff; }
.hero-date { color: #D4ECE3; font-size: .95rem; }
.hero-addr {
  position: relative; z-index: 1; display: inline-flex; align-items: center; gap: 10px;
  margin-top: 16px; background: #fff; color: #1E2B28; border-radius: 14px;
  padding: 10px 16px; font-weight: 600; box-shadow: 0 6px 16px rgba(0,0,0,.12);
}
.hero-addr small { display: block; color: #6C7D78; font-weight: 500; font-size: .72rem; letter-spacing: .05em; }
.hero-stats { position: relative; z-index: 1; display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.hero-stats span { background: rgba(255,255,255,.14); padding: 5px 12px; border-radius: 999px; font-size: .85rem; }

.kat-head {
  display: flex; align-items: center; gap: 10px; margin: 26px 0 12px;
  background: var(--c); color: #fff; padding: 10px 16px; border-radius: 14px;
}
.kat-head .judul { font-weight: 700; font-size: 1.08rem; flex: 1; }
.kat-head .jml { background: rgba(255,255,255,.22); font-size: .78rem; padding: 3px 10px; border-radius: 999px; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.card {
  background: #fff; border: 1px solid #E3ECE8; border-bottom: 4px solid var(--c);
  border-radius: 16px; overflow: hidden; display: flex; flex-direction: column;
  box-shadow: 0 3px 10px rgba(16, 60, 48, .06); transition: transform .15s, box-shadow .15s;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 10px 22px rgba(16, 60, 48, .12); }
.foto {
  aspect-ratio: 1 / 1; background: #fff; display: flex; align-items: center;
  justify-content: center; border-bottom: 1px solid #EEF3F0;
}
.foto img { width: 100%; height: 100%; object-fit: contain; }
.foto.kosong { background: color-mix(in srgb, var(--c) 10%, #fff); font-size: 2.6rem; }
.info { padding: 11px 14px 13px; display: flex; flex-direction: column;
        justify-content: space-between; flex: 1; gap: 6px; }
.card .nama { color: #14201D; font-weight: 700; font-size: .95rem; line-height: 1.32; }
.card .harga { color: var(--c); font-weight: 800; font-size: 1.15rem; }
.card .harga span { color: #6C7D78; font-weight: 600; font-size: .78rem; margin-left: 2px; }
.dl-title { font-weight: 700; font-size: 1.15rem; margin-bottom: 2px; }

.foot {
  margin-top: 34px; text-align: center; background: #0A4F3D; color: #D4ECE3;
  border-radius: 20px; padding: 22px 18px; border-top: 5px solid #F6C445;
}
.foot b { color: #F6C445; font-size: 1.15rem; }

@media (max-width: 640px) {
  .hero { padding: 22px 20px; border-radius: 20px; }
  .hero-title { font-size: 1.65rem; }
  .grid { grid-template-columns: 1fr 1fr; gap: 9px; }
  .info { padding: 9px 11px 11px; }
  .card .nama { font-size: .86rem; }
  .card .harga { font-size: 1rem; }
}
</style>
"""


def main():
    st.set_page_config(page_title=f"Katalog Harga • {NAMA_TOKO}", page_icon="🛒",
                       layout="wide", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)

    now = sekarang()
    total_produk = sum(len(v["produk"]) for v in KATALOG.values())

    # ---------- Hero ----------
    st.markdown(
        f'<div class="hero">'
        f'<span class="hero-badge">🛒 DAFTAR HARGA TERBARU</span>'
        f'<div class="hero-title">{html.escape(NAMA_TOKO)}</div>'
        f'<div class="hero-date">🗓️ Update: {tanggal_indo(now)}</div>'
        f'<div class="hero-addr">📍<div><small>ALAMAT TOKO</small>{html.escape(ALAMAT_TOKO)}</div></div>'
        f'<div class="hero-stats"><span><b>{total_produk}</b> produk</span>'
        f'<span><b>{len(KATALOG)}</b> kategori</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---------- Mode admin: cek foto produk (buka web + ?admin=1) ----------
    if st.query_params.get("admin") == "1":
        with st.expander("🛠️ Cek foto produk (mode admin)", expanded=True):
            st.caption(f"Simpan foto di folder: {IMAGES_DIR}  —  format .jpg / .jpeg / .png / .webp")
            baris = []
            for kat, info in KATALOG.items():
                for p in info["produk"]:
                    path = cari_gambar(p)
                    nama = nama_file_gambar(p)
                    baris.append({
                        "Status": "✅ Ada" if path else "❌ Belum",
                        "Produk": p["nama"],
                        "Nama file": path.name if path else (nama if p["gambar"] else f"{nama}.jpg"),
                        "Kategori": kat,
                    })
            ada_foto = sum(r["Status"].startswith("✅") for r in baris)
            st.progress(ada_foto / len(baris), text=f"{ada_foto} dari {len(baris)} produk sudah punya foto")
            st.dataframe(baris, hide_index=True, use_container_width=True)

    # ---------- Pencarian & filter ----------
    q = st.text_input("Cari produk", placeholder="🔎  Cari produk... (contoh: minyak, saos, tissue)",
                      label_visibility="collapsed").strip().lower()
    pilihan = st.pills("Kategori", ["Semua"] + list(KATALOG.keys()),
                       default="Semua", label_visibility="collapsed")

    # ---------- Daftar produk per kategori ----------
    def kartu_html(p: dict, info: dict) -> str:
        path = cari_gambar(p)
        uri = foto_data_uri(str(path), path.stat().st_mtime_ns) if path else ""
        if uri:
            foto = f'<div class="foto"><img src="{uri}" alt="{html.escape(p["nama"])}" loading="lazy"></div>'
        else:
            foto = f'<div class="foto kosong">{info["ikon"]}</div>'
        unit = f'<span>/{html.escape(p["satuan"])}</span>' if p["satuan"] else ""
        return (f'<div class="card">{foto}<div class="info">'
                f'<div class="nama">{html.escape(p["nama"])}</div>'
                f'<div class="harga">{rupiah(p["harga"])}{unit}</div></div></div>')

    ada = False
    for kat, info in KATALOG.items():
        if pilihan not in (None, "Semua") and kat != pilihan:
            continue
        items = [p for p in info["produk"] if q in p["nama"].lower()]
        if not items:
            continue
        ada = True
        kartu = "".join(kartu_html(p, info) for p in items)
        st.markdown(
            f'<div style="--c:{info["warna"]}">'
            f'<div class="kat-head"><span>{info["ikon"]}</span>'
            f'<span class="judul">{html.escape(kat)}</span>'
            f'<span class="jml">{len(items)} item</span></div>'
            f'<div class="grid">{kartu}</div></div>',
            unsafe_allow_html=True,
        )

    if not ada:
        st.info("Produk tidak ditemukan. Coba kata kunci lain ya 🙏")

    # ---------- Footer alamat ----------
    wa = f"<br>💬 WhatsApp: {html.escape(NO_WA)}" if NO_WA else ""
    st.markdown(
        f'<div class="foot">Yuk mampir ke {html.escape(NAMA_TOKO)}<br>'
        f'📍 <b>{html.escape(ALAMAT_TOKO)}</b>{wa}<br>'
        f'<small>{html.escape(CATATAN)}</small></div>',
        unsafe_allow_html=True,
    )

    # ---------- Download katalog (paling bawah) ----------
    st.write("")
    with st.container(border=True):
        st.markdown('<div class="dl-title">📥 Download Katalog (Gambar)</div>', unsafe_allow_html=True)
        st.caption("Gambar vertikal siap dibagikan ke WhatsApp — berisi semua produk, harga, dan alamat toko.")
        c1, c2 = st.columns(2)
        tata = c1.radio("Tampilan", ["Ringkas (2 kolom)", "Huruf besar (1 kolom)"],
                        horizontal=True)
        fmt = c2.radio("Format", ["PNG", "JPG"], horizontal=True,
                       help="PNG paling tajam, JPG ukurannya lebih kecil.")
        kolom = 1 if tata.startswith("Huruf") else 2

        with st.spinner("Menyiapkan gambar katalog..."):
            data = poster_bytes(fmt, kolom, now.strftime("%Y-%m-%d"), tanda_gambar())

        nama_file = f"katalog-harga-{now.strftime('%Y%m%d')}.{fmt.lower()}"
        st.download_button(
            "⬇️  Download Katalog", data=data, file_name=nama_file,
            mime="image/png" if fmt == "PNG" else "image/jpeg",
            type="primary", use_container_width=True,
        )
        with st.expander("👀 Lihat pratinjau gambar"):
            st.image(data, use_container_width=True)

if __name__ == "__main__":
    main()