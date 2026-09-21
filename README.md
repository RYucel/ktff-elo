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

Kazıma ve yayın **ayrı yerlerde** çalışır. Sebebi teknik bir kısıt:
`ktff.org` Cloudflare arkasında ve veri merkezi IP'lerine yönetilen challenge
sunuyor (`cf-mitigated: challenge`). GitHub Actions koşucuları veri merkezinden
çıktığı için siteyi oradan çekmek mümkün değil; bu kısıt dolanılmaz.

```
Yerel makine (Pazartesi 09:00, Görev Zamanlayıcı)
  guncelle.bat
    └─ src/ktff_cek.py ile yeni sonuçları çek
    └─ data/ değiştiyse commit + push
                    ↓
GitHub Actions (data/** push'unda tetiklenir)
    └─ build_dataset -> final_model -> analiz
    └─ site_build -> wrangler deploy
```

Makine o gün kapalıysa sorun olmaz: Görev Zamanlayıcı kaçırılan görevi açılışta
çalıştırır, zincir oradan devam eder.

### Kurulum (bir kez)

```bat
schtasks /create /tn "KTFF ELO haftalik" /tr "E:\Projeler\ktff-elo\guncelle.bat" ^
         /sc weekly /d MON /st 09:00 /f
```

`guncelle.bat` çalıştığı her seferde `guncelle.log` dosyasına yazar.

GitHub deposunda iki secret tanımlı olmalı: `CLOUDFLARE_API_TOKEN` (Workers
dağıtım yetkisi) ve `CLOUDFLARE_ACCOUNT_ID`.

### Kazıyıcıyı elle çalıştırma

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

Siteyi veri değişmeden yeniden yayımlamak için (tasarım değişikliği gibi):
GitHub → Actions → "Model ve yayın" → Run workflow.

## Bilinen veri sorunları

- **2011-13 arşiv tekrarı:** aynı ev-deplasman çifti sezonda ikinci kez listeleniyor
  (70 kayıt). `supheli_tekrar=1` ile işaretli, modele girmiyor.
- **A2 karışması:** aynı gün erken saatli A2 maçları A takım ligine yazılmış; geç
  başlangıç saatli kayıt tutuldu (658 çift).
- **2020-21 sezonu yok** (pandemi), 2019-20 yarıda kesilmiş.
- Kupa, A2 ve U17 müsabakaları kapsam dışı.

Kaynak: Kıbrıs Türk Futbol Federasyonu maç arşivi — ktff.org
