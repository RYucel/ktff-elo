"""Rapor ve web sayfası için özet analizler."""
import json, sys, numpy as np, pandas as pd, pathlib
sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin

ROOT = pathlib.Path(__file__).resolve().parents[1]
m = pd.read_csv(ROOT/"out/ktff_elo_maclar.csv", parse_dates=["date"])
d = pd.read_csv(ROOT/"out/ktff_maclar.csv", parse_dates=["date"])
d = d[d.supheli_tekrar == 0]
meta = json.loads((ROOT/"out/model_meta.json").read_text(encoding="utf-8"))

# 0) her maçın sonuç olasılıkları (sıralı lojistik) -> beklenen puan için
_b, _c1, _c2 = meta["logit"]["b"], meta["logit"]["c1"], meta["logit"]["c2"]
_z = _b * m.elo_diff.to_numpy()
_pA = 1 / (1 + np.exp(-(_c1 - _z)))
_pD = 1 / (1 + np.exp(-(_c2 - _z))) - _pA
d = d.merge(pd.DataFrame({"match_id": m.match_id, "pH": 1 - _pA - _pD, "pD": _pD, "pA": _pA}),
            on="match_id", how="left")
assert d[["pH", "pD", "pA"]].notna().all().all(), "olasılık eşleşmeyen maç var"

# 1) ev sahibi avantajı
ev = d.sonuc.value_counts(normalize=True)
gol = dict(ev_gol=float(d.hg.mean()), dep_gol=float(d.ag.mean()))
ev_lig = d.groupby("lig").sonuc.value_counts(normalize=True).unstack().round(3)
ev_sezon = d.groupby("sezon").sonuc.value_counts(normalize=True).unstack()["H"].round(3)

# 2) puan cetveli — [takim, O, G, B, M, A, Y, AV, P, xP, sapma]
# Galibiyet 3, beraberlik 1 puan. Sıralama: puan > averaj > atılan gol > isim.
# KTFF'nin ikili averaj ve ceza puanı uygulamaları burada modellenmez.
# xP (beklenen puan) = her maçta 3*P(galibiyet) + 1*P(beraberlik) toplamı.
# Olasılıklar maç ÖNCESİ ELO'dan gelir; sapma = gerçek puan - xP.
def cetvel(g):
    rows = []
    for t in sorted(set(g.home) | set(g.away)):
        h, a = g[g.home == t], g[g.away == t]
        G = int((h.sonuc == "H").sum() + (a.sonuc == "A").sum())
        B = int((h.sonuc == "D").sum() + (a.sonuc == "D").sum())
        M = int((h.sonuc == "A").sum() + (a.sonuc == "H").sum())
        at = int(h.hg.sum() + a.ag.sum())
        ye = int(h.ag.sum() + a.hg.sum())
        P = G*3 + B
        xP = float((h.pH*3 + h.pD).sum() + (a.pA*3 + a.pD).sum())
        rows.append([t, G+B+M, G, B, M, at, ye, at-ye, P, round(xP, 1), round(P - xP, 1)])
    rows.sort(key=lambda r: (-r[8], -r[7], -r[5], r[0]))
    return rows

sezon_sonu = pd.read_csv(ROOT/"out/ktff_elo_sezon_sonu.csv")
sampiyonlar = []
for (s, lg), g in d.groupby(["sezon","lig"]):
    if len(g) < 60:   # yarım kalan / yeni başlamış sezonları atla
        continue
    t = cetvel(g)
    elo_top = (sezon_sonu[(sezon_sonu.sezon == s) & (sezon_sonu.takim.isin([r[0] for r in t]))]
               .sort_values("elo", ascending=False))
    sampiyonlar.append(dict(sezon=s, lig=lg, sampiyon=t[0][0], puan=t[0][8],
                            elo_bir=elo_top.iloc[0].takim if len(elo_top) else None,
                            ayni=bool(len(elo_top) and elo_top.iloc[0].takim == t[0][0])))
sam = pd.DataFrame(sampiyonlar)
sam.to_csv(ROOT/"out/sezon_sampiyonlari.csv", index=False)

# 3) web sayfası için veri paketi
siralama = pd.read_csv(ROOT/"out/ktff_elo_siralama.csv")
zirve = pd.read_csv(ROOT/"out/ktff_elo_zirve.csv")
ss = sezon_sonu.pivot(index="takim", columns="sezon", values="elo").round(1)
pack = dict(
    meta=dict(mac=int(meta["mac_sayisi"]), kulup=int(meta["kulup_sayisi"]),
              ilk=meta["ilk"], son=meta["son"], params=meta["params"],
              logit=meta["logit"], ev_avantaji=round(meta["ev_avantaji_elo"], 1),
              holdout=meta["holdout"]),
    siralama=[dict(takim=r.takim, elo=round(r.elo, 1), lig=r.lig, sira=int(r.siralama))
              for r in siralama.itertuples()],
    zirve=[dict(takim=r.takim, elo=round(r.elo, 1), tarih=str(r.date)[:10], sezon=r.sezon)
           for r in zirve.head(20).itertuples()],
    sezonlar=list(ss.columns),
    tarihce={t: [None if pd.isna(v) else float(v) for v in ss.loc[t]] for t in ss.index},
    sampiyonlar=sam.to_dict("records"),
    ev_avantaji_sezon={k: float(v) for k, v in ev_sezon.items()},
    logolar=json.loads((ROOT/"data/logolar.json").read_text(encoding="utf-8"))
            if (ROOT/"data/logolar.json").exists() else {},
    puan_basliklar=["Kulüp","O","G","B","M","A","Y","Av","P","xP","Sapma"],
    puan_sezon={f"{s}|{lg}": cetvel(g) for (s, lg), g in d.groupby(["sezon","lig"])},
    puan_tum={"Tümü": cetvel(d), "Süper Lig": cetvel(d[d.lig == "Süper Lig"]),
              "1. Lig": cetvel(d[d.lig == "1. Lig"])},
)
(ROOT/"out/web_veri.json").write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")

# 4) sayfadaki gömülü veriyi tazele (sayfa tek dosya, web_veri.json'u dışarıdan okumaz)
sayfa = ROOT/"out/ktff_elo_sayfa.html"
h = sayfa.read_text(encoding="utf-8")
bas = h.index("const DATA = ")
son = h.index("</script>", bas)
sayfa.write_text(h[:bas] + "const DATA = " + json.dumps(pack, ensure_ascii=False)
                 + ";" + chr(10) + h[son:], encoding="utf-8")

print("Ev/Bera/Dep oranı:", ev.round(3).to_dict())
print("Gol ort.:", {k: round(v,2) for k,v in gol.items()})
print(ev_lig.to_string())
print("\nELO 1'i = şampiyon oranı:", round(sam.ayni.mean(), 3), f"({sam.ayni.sum()}/{len(sam)})")
print(sam.tail(10).to_string(index=False))
print("\nweb_veri.json:", (ROOT/"out/web_veri.json").stat().st_size, "bayt")
