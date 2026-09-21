# KKTC Futbol ELO

KTFF arşivindeki AKSA Süper Lig ve 1. Lig sonuçlarından kurulan, gol farkı ağırlıklı
ortak ELO reyting sistemi. 2011-12 → 2026-27, 5.962 maç, 54 kulüp.

Analiz bulguları ve yöntem tartışması için **`RAPOR.md`**.

## Kurulum

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma

Betikler proje kökünü kendileri bulur; `src/` içinden çalıştırın:

```bash
cd src
python build_dataset.py   # data/ ham veri -> out/ktff_maclar.csv   (temizlik + bayraklar)
python tune.py            # 420 parametre kombinasyonu, zaman-dışı test  (~35 sn)
python final_model.py     # nihai reytingler + tahmin kalibrasyonu
python analiz.py          # özet tablolar + puan cetvelleri -> web_veri.json + sayfa
```

`build_dataset.py` ve `final_model.py` yeter; `tune.py` yalnızca parametre seçimini
yeniden doğrulamak için gerekli.

## Yayına alma (Cloudflare)

Site, sunucu kodu olmayan statik bir Workers dağıtımıdır: tek HTML dosyası + veri
setleri. `site/` klasörü `out/` çıktılarından üretilir, elle düzenlenmez.

```bash
npm install            # yalnız wrangler
npm run veri           # pipeline: build_dataset -> final_model -> analiz
npm run build          # out/ -> site/
npm run dev            # yerel önizleme (wrangler dev)
npm run deploy         # Cloudflare'e yayımla
```

İlk yayından önce `npx wrangler login` ile hesabı bağlayın. Yapılandırma
`wrangler.jsonc` içinde; `main` yoktur, çünkü çalışan bir Worker kodu yok —
istekleri doğrudan varlık katmanı karşılar.

| Yol | İçerik |
|---|---|
| `/` | İnteraktif sayfa (`out/ktff_elo_sayfa.html`) |
| `/web_veri.json` | Sayfanın veri paketi, CORS açık |
| `/veri/*.csv` | Üretilen tüm veri setleri, CORS açık |

Önbellek ve güvenlik başlıkları `site/_headers` ile verilir (HTML her istekte
doğrulanır, veri dosyaları 1 saat önbelleklenir). `Content-Type` buradan
değiştirilemez — Cloudflare onu uzantıdan belirler; kodlama HTML içindeki
`<meta charset="utf-8">` ile bildirilir.

## Haftalık otomatik güncelleme

`.github/workflows/haftalik.yml` her pazartesi 06:00 UTC'de (KKTC 09:00) çalışır,
elle de tetiklenebilir. Akış: KTFF'den yeni sonuçları çek → değişiklik yoksa dur →
modeli yeniden kur → siteyi yayımla → yeni maçları depoya işle.

Kazıyıcı ayrıca tek başına çalıştırılabilir:

```bash
python src/ktff_cek.py --kuru     # yazmadan ne ekleneceğini göster
python src/ktff_cek.py            # data/matches_raw.csv'ye ekle
python src/ktff_cek.py --sayfa 4  # daha geriye git (sezon başı toparlama)
```

Yalnızca güncel sezon yarışmaları taranır: `competition=60` (Süper Lig) ve
`62` (1. Lig). Maçlar `mac_id` ile tekilleştirilir, aynı maç iki kez eklenmez.
Yeni bir kulüp görülürse `teams_raw.txt` **sonuna** eklenir (indeks sırası
korunur) ve günlükte uyarı basılır — sponsorlu bir isim varyantıysa
`build_dataset.py` içindeki `ALIAS` sözlüğüne elle eklemek gerekir.

İş akışının çalışması için depoda iki secret tanımlı olmalı:
`CLOUDFLARE_API_TOKEN` (Workers dağıtım yetkisi) ve `CLOUDFLARE_ACCOUNT_ID`.

## Klasörler

```
raw/        KTFF'den kazınan ham satırlar (chunk0 takım sözlüğünü de içerir)
data/       matches_raw.csv (6.032 satır) + teams_raw.txt (59 etiket)
src/        pipeline (ktff_cek.py kazıyıcı, site_build.py yayın derleyicisi dahil)
out/        üretilen veri setleri, model çıktıları ve web sayfası
site/       Cloudflare'e dağıtılan klasör (src/site_build.py üretir, elle dokunma)
```

### out/ içindekiler

| Dosya | İçerik |
|---|---|
| `ktff_maclar.csv` | Temiz maç veri seti — tarih, sezon, lig, takımlar, skor, `hukmen`, `supheli_tekrar`, KTFF bağlantısı |
| `ktff_elo_maclar.csv` | Her maç için maç öncesi/sonrası ELO, ELO farkı, beklenen skor |
| `ktff_elo_siralama.csv` | Güncel sıralama (takım, ELO, lig, sıra) |
| `ktff_elo_tarihce.csv` | Her maçtan sonraki tüm reyting noktaları (grafikler için) |
| `ktff_elo_sezon_sonu.csv` | Sezon sonu reytingleri |
| `ktff_elo_zirve.csv` | Kulüp bazında tüm zamanların zirvesi |
| `sezon_sampiyonlari.csv` | Şampiyon vs. sezon sonu ELO lideri |
| `model_karsilastirma.csv` | Zaman-dışı test metrikleri |
| `parametre_taramasi.csv` | 420 kombinasyonun tam sonucu |
| `model_meta.json` | Nihai parametreler + lojistik kalibrasyon katsayıları |
| `web_veri.json` | Web sayfasının veri paketi (sıralama, tarihçe, puan cetvelleri) |
| `ktff_elo_sayfa.html` | İnteraktif sayfa; veri `const DATA` olarak gömülüdür, `analiz.py` her koşuda tazeler |

## Model özeti

```
R' = R + K · G · (S − B)       B = 1 / (1 + 10^(−(R_ev + H − R_dep)/400))
K = 40 · H = 60 · G = 1 / 1,5 / (11+fark)/8
sezon başı ortalamaya çekme %25 · lig başlangıç farkı 120 · yeni kulüp: lig ort. − 40
```

Modelin tüm sabitleri `src/elo.py` içindeki `EloParams` alanlarıdır (taban 1500,
ölçek 400 ve gol farkı merdiveni dahil); motor kodun içinde gömülü sayı tutmaz.
Varsayılanlar nihai modele eşittir, nihai değerler `src/final_model.py` başındaki
tek `EloParams(...)` satırında açıkça yazılıdır; karşılaştırma tablosunun taban
modelleri de bu satırdan `replace(...)` ile türetilir. Tahmin katmanı ayrıdır: ELO farkını
(ev / beraberlik / deplasman) olasılıklarına çeviren sıralı lojistik model,
katsayıları `model_meta.json` içinde.

**Zaman-dışı test (2020-21 sonrası, 2.401 maç):** log-loss 0,959 · Brier 0,568 ·
isabet %55,1 (taban oran: 1,050 / %45,2).

## Veriyi güncellemek

`raw/` içindeki satırlar `https://ktff.org/bilgi-bankasi/maclar?page=N&competition=C`
sayfalarından `a.match-fixture-card` kartları okunarak üretildi (competition: Süper Lig
1 ve 60, 1. Lig 61 ve 62). Yeni sonuçlar için aynı sayfaların son birkaçını çekip
`data/matches_raw.csv` sonuna eklemek ve pipeline'ı yeniden çalıştırmak yeterli;
format `lig,YYYYMMDD,HHMM,mac_id,ev_idx,dep_idx,ev_gol,dep_gol,hukmen`
(takım indeksleri `data/teams_raw.txt` satır sırasıdır, 0'dan başlar).

Eklerken:

- `lig` metin değil sayıdır: `1` = Süper Lig, `2` = 1. Lig. Başka değer sessizce `NaN` olur.
- `mac_id` benzersiz olmalı; hem sıralama eşitlik bozucusu hem de KTFF bağlantısının kaynağı.
- Satır sırası önemsiz — `build_dataset.py` tarihe göre yeniden sıralar.
- Yeni kulüp `teams_raw.txt` **sonuna** eklenir; araya girmek mevcut tüm indeksleri kaydırır.
  İsim sponsorlu bir varyantsa `build_dataset.py` içindeki `ALIAS` sözlüğüne de yazılmalı,
  yoksa ayrı kulüp sayılır.
- Aynı sezon+lig içinde tekrar eden (ev, deplasman) çifti otomatik `supheli_tekrar=1`
  işaretlenir ve **modelden sessizce çıkarılır** — çift devreli lig varsayımı.
- Hükmen maçlar varsayılan olarak normal skor gibi işlenir; `final_model.py` içindeki
  `HUKMEN_DAHIL = False` ile tamamen dışlanabilir.
- Betikler `src/` içinden çalıştırılmalı (`from elo import ...`); sıra
  `build_dataset.py` → `final_model.py` → `analiz.py`, ardından yayın için
  `site_build.py`.

## Bilinen veri sorunları

- **2011-13 arşiv tekrarı:** aynı ev-deplasman çifti sezonda ikinci kez listeleniyor
  (70 kayıt). `supheli_tekrar=1` ile işaretli, modele girmiyor.
- **A2 karışması:** aynı gün erken saatli A2 maçları A takım ligine yazılmış; geç
  başlangıç saatli kayıt tutuldu (658 çift).
- **2020-21 sezonu yok** (pandemi), 2019-20 yarıda kesilmiş.
- Kupa, A2 ve U17 müsabakaları kapsam dışı.

Kaynak: Kıbrıs Türk Futbol Federasyonu maç arşivi — ktff.org
