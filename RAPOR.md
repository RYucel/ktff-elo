# KKTC Futbol ELO — Analiz Raporu

**Kapsam:** AKSA Süper Lig + AKSA 1. Lig · 2011-12 → 2026-27 (20 Eylül 2026'ya kadar)
**Kaynak:** Kıbrıs Türk Futbol Federasyonu maç arşivi (ktff.org/bilgi-bankasi/maclar)
**Veri:** 6.032 maç kaydı, temizlik sonrası **5.962 maç**, **54 kulüp**, 15 sezon

---

## 1. Veri toplama ve temizlik

KTFF arşivi sayfa sayfa gezilerek dört yarışma kimliği (Süper Lig: 1 ve 60, 1. Lig: 61 ve 62) altındaki 349 liste sayfası okundu. A2, U17 ve kupa müsabakaları kapsam dışı bırakıldı.

Ham kayıtlarda üç sorun çıktı ve üçü de belgelendi:

| Sorun | Bulgu | Yapılan |
|---|---|---|
| Aynı gün iki kez listelenen eşleşme | 658 çift, hepsi 2011–2013 arası; erken saatli olan A2 maçı | Geç başlangıç saatli (A takım) kayıt tutuldu |
| Aynı sezonda ikinci kez görünen ev-deplasman çifti | 70 kayıt, yine 2011–13 | `supheli_tekrar=1` işaretlendi, modele girmedi |
| Oynanmamış/tatil edilmiş maçlar | 188 kayıt | Çıkarıldı (hükmen sonuçlar tutuldu) |

Kulüp adları sponsor ekleri ayıklanarak birleştirildi: *Yonpaş Dumlupınar → Dumlupınar*, *GAÜ Çetinkaya → Çetinkaya*, *China Bazaar Gençlik Gücü → Gençlik Gücü*, *DND/Pera L. Gençler Birliği → L. Gençler Birliği*, *Çello Dikmen Gücü → Dikmen Gücü*, *Yeni Mesarya Türkmenköy → Türkmenköy*, *German Gold Akova Vuda → Akova Vuda*.

**Sezon bütünlüğü kontrolü:** 14 takımlı sezonlarda takım başına 26, 16 takımlı sezonlarda 30 maç beklenir; temizlik sonrası tablo bu yapıya oturuyor. 2020-21 sezonu arşivde yok (pandemi), 2019-20 yarıda kesilmiş (211/240 maç). 2016-17'de 1. Lig 10 takımla oynanmış (90 maç).

---

## 2. Model

Her maçta ev sahibinin reytingi şöyle güncellenir:

```
R' = R + K · G · (S − B)          B = 1 / (1 + 10^(−(R_ev + H − R_dep)/400))
```

| Parametre | Değer | Gerekçe |
|---|---|---|
| `K` | 40 | Parametre taramasında en iyi; sezon başına ~30 maç olan kısa ligde hızlı uyum gerekiyor |
| `G` (gol farkı çarpanı) | 1 / 1,5 / (11+fark)/8 | World Football Elo standardı; farkı 3+ olan maçlar daha ağır |
| `H` (ev avantajı) | 60 | Veriden ölçülen +57,5'e yuvarlanmış |
| Sezon başı ortalamaya çekme | %25 | Kadro değişimini hesaba katar |
| Süper Lig / 1. Lig başlangıç farkı | 120 puan | Sonraki tüm fark sonuçlardan gelir |
| Lige yeni giren kulüp | Lig ortalaması − 40 | Yeni kulübün sahte yüksek başlamasını engeller |

Reytingler **iki lig için ortaktır**: terfi eden kulüp puanını yanında taşır, küme düşen kaybetmez. Bu, ligler arası karşılaştırmayı mümkün kılan tercihtir.

Tahmin katmanı ayrıdır: ELO farkı → (ev / beraberlik / deplasman) dönüşümü, 2013-14 sonrası maçlara uydurulan **sıralı lojistik** modelle yapılır. Bu sayede beraberlik oranı zorlanmadan, veriden öğrenilir.

---

## 3. Model doğrulaması

2013-14 öncesi ısınma dışı bırakıldı, model 2019-20'ye kadar kalibre edildi, **2020-21 sonrası 2.401 maçta test edildi** (zaman-dışı, sızıntısız):

| Model | Log-loss ↓ | Brier ↓ | İsabet ↑ |
|---|---|---|---|
| **Gol farkı ağırlıklı (nihai)** | **0,959** | **0,568** | **%55,1** |
| Sezon çekmesi yok | 0,962 | 0,570 | %54,8 |
| Klasik ELO (sabit K) | 0,964 | 0,572 | %54,2 |
| Taban oran (referans) | 1,050 | 0,635 | %45,2 |

Gol farkı ağırlığı klasik ELO'ya kıyasla log-loss'u 0,005 iyileştiriyor — küçük ama tutarlı bir kazanç; 2.401 maçta hep aynı yönde. Asıl fark taban orana karşı: model, sonucu tahmin etmede rastgeleden **10 puan** daha isabetli.

420 parametre kombinasyonu denendi (`out/parametre_taramasi.csv`). Sonuçlar `K` etrafında duyarlı, ev avantajı katsayısına karşı neredeyse **düz** — çünkü ev avantajı tahmin katmanında zaten ayrıca öğreniliyor.

---

## 4. Bulgular

### Ev sahibi avantajı: +57,5 ELO

Ev sahibi maçların **%45,9'unu** kazanıyor, **%20,6'sı** berabere bitiyor, **%33,5'i** deplasmana gidiyor. Ev sahibi ortalama 1,82, deplasman 1,48 gol atıyor. ELO cinsinden bu **+57,5 puanlık** bir avantaj — Avrupa liglerinin tipik 60-70 bandının hafif altında. 2011-16 ile son beş sezon arasında anlamlı bir değişim yok (%46,0 → %45,1).

### Beraberlik oranı düşük

%20,6 beraberlik, Avrupa ortalamasının (~%25) belirgin altında; maç başına 3,30 gol (Süper Lig'de 3,42) ile birlikte okununca tablo net: KKTC ligleri **yüksek skorlu ve sonuç odaklı**. Modelin sıralı lojistik katmanı bunu kendiliğinden yakalıyor.

### Tüm zamanların zirvesi

| # | Kulüp | Sezon | Zirve ELO |
|---|---|---|---|
| 1 | **Mağusa Türk Gücü** | 2023-24 | **1.895,9** |
| 2 | Cihangir GSK | 2023-24 | 1.837,6 |
| 3 | Çetinkaya TSK | 2012-13 | 1.823,7 |
| 4 | Yenicami AK | 2014-15 | 1.812,7 |
| 5 | Doğan Türk Birliği | 2024-25 | 1.794,3 |

Mağusa Türk Gücü'nün 2021-24 arası üst üste üç şampiyonluğu, 15 yılın en baskın dönemi. Nisan 2024'teki 1.895,9 puanı, o anki lig ortalamasının ~390 puan üstündeydi — tarafsız sahada ortalama bir Süper Lig takımına karşı **%91** kazanma beklentisi.

### ELO lideri ne sıklıkla şampiyon oluyor?

Tamamlanan 28 lig sezonunun **18'inde (%64)** sezon sonu ELO lideri aynı zamanda şampiyon. Süper Lig'de uyum daha yüksek (10/14), 1. Lig'de daha düşük (8/14) — alt ligde kadro oynaklığı ve daha az maç, puan tablosu ile güç arasındaki ayrışmayı büyütüyor.

En çarpıcı ayrışma **2025-26 Süper Lig**: şampiyon Cihangir GSK (73 puan) oldu ama sezon sonu ELO lideri Gençlik Gücü TSK'ydı — model, Gençlik Gücü'nün gol farkı üstünlüğünü puan tablosundan daha ağır tartıyor.

### Ligler arası gerçek fark

2025-26 sezon sonunda Süper Lig ortalaması **1.506**, 1. Lig ortalaması **1.405** — yaklaşık **102 puan**. Modele 120 puanlık başlangıç farkı verilmişti; 15 sezonun sonunda sonuçların kendisi bu farkı 102'ye getirdi. Yani başlangıç varsayımı gerçeğe yakınmış, ama lig arası uçurum sanılandan biraz dar: iyi bir 1. Lig takımı, zayıf bir Süper Lig takımından güçlü.

### En büyük sezonluk sıçrama ve çöküş

| Yön | Kulüp | Sezon | Değişim |
|---|---|---|---|
| ↑ | Türk Ocağı Limasol SK | 2024-25 | +398 |
| ↑ | Yeniboğaziçi DSK | 2024-25 | +276 |
| ↓ | Ozanköy SK | 2019-20 | −487 |
| ↓ | Çanakkale TSK | 2024-25 | −434 |

### Modelin en çok şaşırdığı maçlar

| Tarih | Maç | Skor | ELO farkı |
|---|---|---|---|
| 19.04.2012 | Gençlik Gücü – Çanakkale | 1-2 | 486 |
| 26.01.2025 | Değirmenlik – Yenicami | 0-3 | 445 |
| 22.02.2026 | Gençlik Gücü – Mesarya | 1-3 | 406 |
| 29.12.2023 | Mağusa Türk Gücü – Yenicami | 1-3 | 400 |

---

## 5. Güncel sıralama (20 Eylül 2026)

| # | Kulüp | Lig | ELO |
|---|---|---|---|
| 1 | Gençlik Gücü TSK | Süper Lig | 1.705,4 |
| 2 | Doğan Türk Birliği | Süper Lig | 1.692,8 |
| 3 | Cihangir GSK | Süper Lig | 1.687,2 |
| 4 | Mağusa Türk Gücü | Süper Lig | 1.631,1 |
| 5 | Değirmenlik SK | Süper Lig | 1.612,4 |
| 6 | Aslanköy GSD | Süper Lig | 1.537,9 |
| 7 | Dumlupınar TSK | Süper Lig | 1.512,1 |
| 8 | L. Gençler Birliği SK | 1. Lig | 1.501,1 |

Zirvede 18 puanlık üç kulüp var — 2026-27'nin başında şampiyonluk yarışı 15 yılın en sıkı açılışını yapıyor. L. Gençler Birliği, 1. Lig'den yedi Süper Lig takımını geçiyor.

---

## 6. Dosyalar

Klasör yapısı ve her dosyanın içeriği için `README.md`. Pipeline `src/` içinde sırayla
çalıştırılır: `build_dataset.py` → `tune.py` → `final_model.py` → `analiz.py`.
İnteraktif sayfanın kaynağı `out/ktff_elo_sayfa.html`.

## 7. Sonraki adımlar (öneri)

- **Haftalık otomatik güncelleme:** sezon sürüyor; KTFF sayfasından yeni sonuçları çekip reytingleri tazeleyen zamanlanmış görev kurulabilir.
- **Kupa ve A2 verisi:** kupa maçlarını düşük ağırlıkla dahil etmek, sezon arası boşlukları doldurur.
- **Gol bazlı model:** ELO'nun yanına Poisson/Dixon-Coles kurup skor dağılımı tahmini; log-loss'u bir miktar daha düşürmesi beklenir.
- **Ev sahibi bazında ayrıştırma:** bazı sahalarda avantaj belirgin şekilde yüksek olabilir; stadyum verisi arşivde mevcut.
