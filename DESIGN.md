# KKTC Futbol ELO — Tasarım Sistemi

Kıbrıs Türk futbolunun 15 sezonluk maç arşivinden kurulan bir ELO reyting sitesi.
Karakter: **veri-önce, Material 3 tabanlı analitik panel**. Amaç bir istatistik
ürünü gibi okunmak: yoğun tablolar, net hiyerarşi, ölçülü renk.

> Bu doküman Stitch'te üretilen `assets/5341426322706988792` tasarım sistemiyle
> hizalıdır (proje `163718223381576546`). Önceki editoryal/kağıt dili
> (Archivo + IBM Plex, gölgesiz paneller) terk edilmiştir.

## Renk — Material 3

Tek kaynak renk toprak kırmızısı `#7d1017`. Aksan **vurgu** içindir: aktif çip,
navigasyon seçimi, lider satır, güç çubuğu, lig rozeti.

| Token | Açık | Koyu | Kullanım |
|---|---|---|---|
| `ground` | `#f8faf4` | `#111411` | sayfa zemini |
| `surface` | `#ffffff` | `#191c19` | panel, kart, tablo |
| `surface-2` | `#e1e3dd` | `#2e312d` | çip zemini, çubuk yatağı |
| `surface-3` | `#edefe9` | `#23261f` | tablo başlığı, satır vurgusu |
| `ink` | `#191c19` | `#e1e3dd` | ana metin |
| `ink-2` | `#58413f` | `#d0c4c2` | ikincil metin |
| `ink-3` | `#8b716f` | `#a68d8b` | etiket, üst başlık |
| `accent` | `#7d1017` | `#ffb3ae` | vurgu |
| `accent-soft` | `#ffdad7` | `#5f1214` | aksan zemini (rozet) |
| `on-accent` | `#ffffff` | `#410004` | aksan üstü metin |
| `good` | `#194725` | `#a0d3a5` | olumlu sapma |
| `bad` | `#ba1a1a` | `#ffb4ab` | olumsuz sapma, hata |

Grafik seri renkleri (en fazla beş kulüp): `#2a78d6` `#eb6834` `#1baf7a`
`#eda100` `#e87ba4`.

Açık ve koyu tema eşit vatandaştır; ikisi de sistem tercihini izler, başlıktaki
tek düğme ile elle değiştirilebilir. Koyu temada gölgeler daha koyu ve serttir.

## Tipografi

- **Başlık — Plus Jakarta Sans.** H1 `clamp(30px,6vw,40px)` 800,
  H2 22px 700, H3 16px 700. `letter-spacing:-.02em`.
- **Gövde — Plus Jakarta Sans.** 14px / 1.45.
- **Sayı — JetBrains Mono** 13px 600, `font-variant-numeric: tabular-nums`.
  Bu kural pazarlık konusu değil: ELO puanları, skorlar ve puan cetveli sütunları
  hizalanmadığında tablo okunmaz olur.
- **Etiket (tablo başlığı, üst başlık, form etiketi) — JetBrains Mono**
  11px 700, `letter-spacing:.08em`, büyük harf.
- **Metrik (istatistik kutusu) — Plus Jakarta Sans** 32px 800.

## Şekil, gölge, yoğunluk

- Yarıçap: panel/kart 8px, çip ve form alanı 4px, rozet 12px.
- Yükseklik **gölge ile** verilir, kenarlıkla değil:
  `--shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04)`.
  Navigasyon için daha yayvan `--shadow-nav`.
- Tablo satır dolgusu 10px. Yoğunluk önemli: bir cetvelin 16 satırı kaydırmadan
  görünmeli. Satır ayracı ince ve `surface-3` tonunda; `:hover` satırı boyar.
- Açıklama metni en fazla 56 karakter genişliğinde. Sayfa 1080px ile sınırlı.

## Bileşenler

- **Çip (filtre).** Dolu `surface-2` zemin, 4px köşe, kenarlıksız. Seçiliyken
  aksan zemin + `on-accent` metin + gölge, `aria-pressed` ile.
- **Yapışkan navigasyon.** Aksan renkli ikon karesi + marka, yanında bölüm
  bağlantıları. Görünen bölümün bağlantısı `IntersectionObserver` ile aksan
  zeminle işaretlenir.
- **İstatistik kartı.** Gölgeli beyaz kart: 32px metrik + mono büyük harf etiket.
- **Veri tablosu.** `surface-3` zeminli başlık satırı, sıra numarası, ad, sağa
  yaslı mono sayı sütunları. İlk satır (`tr.top`) aksanla işaretlenir.
- **Güç çubuğu.** 6px ince yatay çubuk, tablonun son sütunu; liderlerde aksan.
- **Lig rozeti.** Dolu zeminli mono etiket; Süper Lig `accent-soft`, 1. Lig nötr.
- **Olasılık şeridi.** Üç parçalı yatay bant (ev / beraberlik / deplasman).
- **İkon — Material Symbols Outlined.** Yalnız bölüm başlıklarında ve navigasyon
  markasında; tablo içinde dekoratif ikon kullanılmaz.
- **Kulüp logosu.** Kulüp adının solunda 22px, `object-fit:contain`, 4px köşe,
  `surface-2` zeminli. Ad sütununda kimliği hızlı taramaya yarar, dekorasyon
  değildir — bu yüzden yalnız kulüp adının geçtiği sütunda kullanılır.
  Logosu olmayan kulüpte aynı boyutta boş yer tutucu kalır ki satırlar arası
  hizalama bozulmasın. Logolar `assets/logo/` altında kendi sunucumuzdan
  servis edilir, KTFF'ye sıcak bağlantı yapılmaz.

## İçerik kuralları

- Dil Türkçe. Sayılar Türkçe biçimli: `1.705,4` — binlik nokta, ondalık virgül.
- Her bölüm başlığının altında bir cümlelik bağlam notu olur; sayı tek başına
  bırakılmaz.
- **Gösterilen her sayı veriden üretilir.** Uydurulmuş metrik (simüle edilmemiş
  olasılık, sahte sürüm/güncelleme damgası, elde olmayan kulüp bilgisi) sayfaya
  girmez. Veri sınırları ve model varsayımları açıkça yazılır.

## Ekranlar

Tek sayfa, dikey akış: başlık → yapışkan navigasyon → istatistik kartları →
güncel güç sıralaması → puan cetvelleri → ELO evrimi grafiği → maç tahmini →
zirve reytingler + model karnesi → yöntem notları.
