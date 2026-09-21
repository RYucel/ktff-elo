"""out/ çıktılarını Cloudflare'e dağıtılacak site/ klasörüne toplar."""
import shutil, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT, SITE = ROOT/"out", ROOT/"site"
LOGO = ROOT/"assets/logo"

# indirmeye açılan veri setleri
VERI = ["ktff_maclar.csv", "ktff_elo_maclar.csv", "ktff_elo_siralama.csv",
        "ktff_elo_tarihce.csv", "ktff_elo_sezon_sonu.csv", "ktff_elo_zirve.csv",
        "sezon_sampiyonlari.csv", "model_karsilastirma.csv", "parametre_taramasi.csv",
        "model_meta.json"]

# HTML veriyi gömülü taşır; web_veri.json ayrıca yayımlanır ki dışarıdan da kullanılabilsin.
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

# Not: Content-Type buradan geçersiz kılınamaz — Cloudflare onu uzantıdan belirler
# ve üretimde charset eklemez. Kodlama HTML içindeki <meta charset="utf-8"> ile bildirilir.
/index.html
  Cache-Control: public, max-age=0, must-revalidate

/web_veri.json
  Cache-Control: public, max-age=300
  Access-Control-Allow-Origin: *

/veri/*
  Cache-Control: public, max-age=3600
  Access-Control-Allow-Origin: *

/logo/*
  Cache-Control: public, max-age=604800
"""

def build():
    if not (OUT/"ktff_elo_sayfa.html").exists():
        raise SystemExit("out/ktff_elo_sayfa.html yok — önce pipeline'ı çalıştırın.")
    # Klasörü silmiyoruz: `wrangler dev` site/ dizinini izlerken Windows kilitliyor.
    # Üzerine yazıp, artık üretilmeyen dosyaları sonunda temizliyoruz.
    (SITE/"veri").mkdir(parents=True, exist_ok=True)

    yazilan = set()
    def koy(kaynak, hedef):
        shutil.copy2(kaynak, SITE/hedef)
        yazilan.add(hedef)

    koy(OUT/"ktff_elo_sayfa.html", "index.html")
    koy(OUT/"404.html", "404.html")
    koy(OUT/"web_veri.json", "web_veri.json")
    eksik = []
    for ad in VERI:
        kaynak = OUT/ad
        if kaynak.exists():
            koy(kaynak, f"veri/{ad}")
        else:
            eksik.append(ad)
    if LOGO.exists():
        (SITE/"logo").mkdir(exist_ok=True)
        for f in sorted(LOGO.glob("*.webp")):
            koy(f, f"logo/{f.name}")
    (SITE/"_headers").write_text(HEADERS, encoding="utf-8")
    yazilan.add("_headers")

    for f in SITE.rglob("*"):
        if f.is_file() and f.relative_to(SITE).as_posix() not in yazilan:
            f.unlink()
            print("temizlendi:", f.relative_to(SITE).as_posix())

    boyut = sum(f.stat().st_size for f in SITE.rglob("*") if f.is_file())
    print(f"site/ hazır — {sum(1 for f in SITE.rglob('*') if f.is_file())} dosya, {boyut/1024:.0f} KB")
    if eksik:
        print("uyarı, bulunamayan çıktı:", ", ".join(eksik))

if __name__ == "__main__":
    build()
