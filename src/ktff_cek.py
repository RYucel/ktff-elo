"""KTFF arşivinden yeni maç sonuçlarını çekip data/matches_raw.csv'ye ekler.

Güncel sezon yarışma kimlikleri: 60 (Süper Lig), 62 (1. Lig).
Tarihsel kimlikler 1 ve 61'dir; haftalık güncelleme için gerekmezler.

    python src/ktff_cek.py            # çek ve yaz
    python src/ktff_cek.py --kuru     # yazmadan ne ekleneceğini göster
    python src/ktff_cek.py --sayfa 3  # yarışma başına 3 sayfa tara
"""
import argparse, html, pathlib, re, sys, time
import requests

sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAKIMLAR = ROOT/"data/teams_raw.txt"
MACLAR = ROOT/"data/matches_raw.csv"

URL = "https://ktff.org/bilgi-bankasi/maclar?page={sayfa}&competition={yarisma}"
YARISMALAR = {60: 1, 62: 2}          # KTFF yarışma kimliği -> bizim lig kodu (1/2)
BASLIK = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}
BEKLE = 1.5                           # sayfalar arası saniye; siteye nazik davran

KART = re.compile(
    r'<a\s+class="match-fixture-card"\s+href="[^"]*?/maclar/(?P<id>\d+)".*?'
    r'__league">(?P<lig>[^<]*)<.*?'
    r'<span>\s*(?P<tarih>\d{2}\.\d{2}\.\d{4})\s*·\s*(?P<saat>\d{2}:\d{2})\s*</span>.*?'
    r'__team">\s*(?P<ev>[^<]*?)\s*</div>.*?'
    r'__score">\s*(?P<skor>[^<]*?)\s*</div>.*?'
    r'__status">\s*(?P<durum>[^<]*?)\s*</div>.*?'
    r'__team--away">\s*(?P<dep>[^<]*?)\s*</div>',
    re.S)
SKOR = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def temiz(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def sayfa_cek(yarisma, sayfa):
    r = requests.get(URL.format(sayfa=sayfa, yarisma=yarisma), headers=BASLIK, timeout=30)
    if r.status_code != 200:
        # Teşhis: ktff.org Cloudflare arkasında; veri merkezi IP'leri engellenebiliyor.
        print(f"HTTP {r.status_code} — yarışma {yarisma}, sayfa {sayfa}", file=sys.stderr)
        for h in ("server", "cf-ray", "cf-mitigated", "retry-after"):
            if h in r.headers:
                print(f"  {h}: {r.headers[h]}", file=sys.stderr)
        govde = re.sub(r"<[^>]+>", " ", r.text[:1500])
        print("  gövde:", re.sub(r"\s+", " ", govde).strip()[:300], file=sys.stderr)
        r.raise_for_status()
    r.encoding = "utf-8"
    return r.text


def kartlari_ayikla(metin, lig_kodu):
    """Oynanmış maçları (lig, tarih, saat, id, ev, dep, evgol, depgol, hukmen) olarak döndürür."""
    cikti = []
    for k in KART.finditer(metin):
        skor = SKOR.match(temiz(k["skor"]))
        if not skor:
            continue                        # henüz oynanmamış / skoru yok
        g, a, y = k["tarih"].split(".")
        durum = temiz(k["durum"])
        cikti.append(dict(
            lig=lig_kodu, tarih=f"{y}{a}{g}", saat=k["saat"].replace(":", ""),
            mac_id=int(k["id"]), ev=temiz(k["ev"]), dep=temiz(k["dep"]),
            eg=int(skor[1]), dg=int(skor[2]),
            hukmen=0 if durum == "Maç Sonucu" else 1, durum=durum))
    return cikti


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuru", action="store_true", help="dosyaya yazma, sadece raporla")
    ap.add_argument("--sayfa", type=int, default=2, help="yarışma başına taranacak sayfa (varsayılan 2)")
    args = ap.parse_args()

    takimlar = [l.strip() for l in TAKIMLAR.read_text(encoding="utf-8").splitlines() if l.strip()]
    indeks = {ad: i for i, ad in enumerate(takimlar)}
    mevcut_satir = [l for l in MACLAR.read_text(encoding="utf-8").splitlines() if l.strip()]
    bilinen = {int(l.split(",")[3]) for l in mevcut_satir}

    toplandi, durumlar = {}, {}
    for yarisma, lig in YARISMALAR.items():
        for sayfa in range(1, args.sayfa + 1):
            for m in kartlari_ayikla(sayfa_cek(yarisma, sayfa), lig):
                toplandi[m["mac_id"]] = m
                durumlar[m["durum"]] = durumlar.get(m["durum"], 0) + 1
            time.sleep(BEKLE)

    yeni = [m for i, m in sorted(toplandi.items()) if i not in bilinen]
    print(f"çekilen: {len(toplandi)} maç · zaten kayıtlı: {len(toplandi)-len(yeni)} · yeni: {len(yeni)}")
    if durumlar:
        print("durumlar:", ", ".join(f"{k}={v}" for k, v in sorted(durumlar.items())))
    if not yeni:
        return 0

    # yeni kulüpler teams_raw.txt sonuna eklenir; indeks sırası asla bozulmaz
    eklenen_takim = []
    for m in yeni:
        for ad in (m["ev"], m["dep"]):
            if ad not in indeks:
                indeks[ad] = len(takimlar)
                takimlar.append(ad)
                eklenen_takim.append(ad)

    satirlar = [f'{m["lig"]},{m["tarih"]},{m["saat"]},{m["mac_id"]},'
                f'{indeks[m["ev"]]},{indeks[m["dep"]]},{m["eg"]},{m["dg"]},{m["hukmen"]}'
                for m in yeni]

    for m, s in zip(yeni, satirlar):
        print(f'  + {m["tarih"]} {m["ev"]} {m["eg"]}-{m["dg"]} {m["dep"]}'
              f'{"  [HÜKMEN]" if m["hukmen"] else ""}')
        print(f'    {s}')
    if eklenen_takim:
        print("YENİ KULÜP:", ", ".join(eklenen_takim))
        print("  -> sponsorlu bir isim varyantıysa build_dataset.py içindeki ALIAS sözlüğüne ekleyin")

    if args.kuru:
        print("\n--kuru: hiçbir şey yazılmadı")
        return 0

    MACLAR.write_text("\n".join(mevcut_satir + satirlar) + "\n", encoding="utf-8")
    if eklenen_takim:
        TAKIMLAR.write_text("\n".join(takimlar) + "\n", encoding="utf-8")
    print(f"\n{len(satirlar)} satır eklendi -> data/matches_raw.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
