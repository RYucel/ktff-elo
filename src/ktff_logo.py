"""KTFF maç sayfalarından kulüp logolarını toplar ve assets/logo/ altına indirir.

Logolar maç sayfasının kahraman bölümünden alınır; taraflar `match-hero__side--home`
ve `--away` ile işaretli olduğu için eşleştirme konuma göre yapılır. Böylece sponsorlu
isim varyantları (China Bazaar Gençlik Gücü vb.) sorun çıkarmaz — hangi maçta kimin
ev sahibi olduğunu zaten kendi veri setimizden biliyoruz.

Bir kez çalıştırmak yeterlidir; sonuçlar depoya işlenir.

    python src/ktff_logo.py            # eksik logoları topla
    python src/ktff_logo.py --yenile   # hepsini yeniden indir
"""
import argparse, json, pathlib, re, sys, time, unicodedata
import pandas as pd, requests

sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGO_DIZIN = ROOT/"assets/logo"
ESLEME = ROOT/"data/logolar.json"
MAC_URL = "https://ktff.org/maclar/{mac_id}"
BASLIK = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}
BEKLE = 1.5

TARAF = re.compile(
    r'match-hero__side--(?P<taraf>home|away)".*?'
    r'<img\s+src="(?P<url>https://ktff\.org/storage/uploads/clubs/[^"]+)"', re.S)

TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def slug(ad):
    s = ad.translate(TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-zA-Z0-9]+", "-", s)).strip("-").lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yenile", action="store_true", help="mevcut logoları da yeniden indir")
    args = ap.parse_args()

    d = pd.read_csv(ROOT/"out/ktff_maclar.csv", parse_dates=["date"])
    kulupler = sorted(set(d.home) | set(d.away))
    LOGO_DIZIN.mkdir(parents=True, exist_ok=True)
    esleme = {} if args.yenile else (json.loads(ESLEME.read_text(encoding="utf-8"))
                                     if ESLEME.exists() else {})

    eksik = [k for k in kulupler if k not in esleme]
    print(f"kulüp: {len(kulupler)} · logosu var: {len(esleme)} · aranacak: {len(eksik)}")

    oturum = requests.Session()
    oturum.headers.update(BASLIK)
    bulunamadi = []

    for kulup in eksik:
        if kulup in esleme:      # araya giren bir maçtan zaten yakalanmış olabilir
            continue
        maclar = d[(d.home == kulup) | (d.away == kulup)].sort_values("date", ascending=False)
        yakalandi = False
        for mac in maclar.head(3).itertuples():      # en yeni üç maçı dene
            try:
                r = oturum.get(MAC_URL.format(mac_id=mac.match_id), timeout=30)
                r.raise_for_status()
                r.encoding = "utf-8"
            except requests.RequestException as e:
                print(f"  ! {kulup}: maç {mac.match_id} alınamadı ({e})")
                time.sleep(BEKLE)
                continue
            taraflar = {m["taraf"]: m["url"] for m in TARAF.finditer(r.text)}
            for taraf, ad in (("home", mac.home), ("away", mac.away)):
                if taraf in taraflar and ad not in esleme:
                    esleme[ad] = taraflar[taraf]
            time.sleep(BEKLE)
            if kulup in esleme:
                yakalandi = True
                break
        if not yakalandi:
            bulunamadi.append(kulup)
            print(f"  ? {kulup}: logo bulunamadı")

    # dosyaları indir
    indirilen = 0
    dosyalar = {}
    for kulup, url in sorted(esleme.items()):
        ad = f"{slug(kulup)}.webp"
        hedef = LOGO_DIZIN/ad
        dosyalar[kulup] = ad
        if hedef.exists() and not args.yenile:
            continue
        try:
            r = oturum.get(url, timeout=30)
            r.raise_for_status()
            hedef.write_bytes(r.content)
            indirilen += 1
            time.sleep(0.4)
        except requests.RequestException as e:
            print(f"  ! {kulup}: logo indirilemedi ({e})")
            dosyalar.pop(kulup, None)

    ESLEME.write_text(json.dumps(dosyalar, ensure_ascii=False, indent=2, sort_keys=True),
                      encoding="utf-8")
    boyut = sum(f.stat().st_size for f in LOGO_DIZIN.glob("*.webp"))
    print(f"\nlogo: {len(dosyalar)}/{len(kulupler)} kulüp · bu turda indirilen: {indirilen} · "
          f"toplam {boyut/1024:.0f} KB")
    if bulunamadi:
        print("logosuz kulüpler:", ", ".join(bulunamadi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
