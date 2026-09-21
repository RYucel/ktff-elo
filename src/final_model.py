"""Nihai ELO modeli: reytingler, tahmin kalibrasyonu ve çıktı dosyaları."""
import json, sys, numpy as np, pandas as pd, pathlib
sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin

from dataclasses import replace
from elo import EloParams, run
from tune import ordered_logit_fit, probs, BURN_IN

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = EloParams(k=40, hfa=60, regress=0.25, gd_mode="wfe", tier_gap=120, new_penalty=40)

HUKMEN_DAHIL = True   # 31 hükmen maç normal skor gibi işlenir; False -> modelden tamamen çıkarılır

df = pd.read_csv(ROOT/"out/ktff_maclar.csv", parse_dates=["date"])
df = df[df.supheli_tekrar == 0]
if not HUKMEN_DAHIL:
    df = df[df.hukmen == 0]
matches, hist, final = run(df, P)

# --- tahmin kalibrasyonu: elo farkı -> (ev / beraberlik / deplasman) ---
ev = matches[matches.sezon >= BURN_IN]
y = ev.sonuc.map({"A":0,"D":1,"H":2}).to_numpy()
theta = ordered_logit_fit(ev.elo_diff.to_numpy(), y)
b, c1 = theta[0], theta[1]
c2 = c1 + np.exp(theta[2])
# ev avantajının ELO karşılığı: P(ev)=P(dep) olduğu fark
home_edge = -(c1 + c2) / (2 * b)

Pm = probs(theta, ev.elo_diff.to_numpy())
ll = -np.log(np.clip(Pm[np.arange(len(y)), y], 1e-12, 1)).mean()
acc = (Pm.argmax(1) == y).mean()

# --- çıktılar ---
matches.to_csv(ROOT/"out/ktff_elo_maclar.csv", index=False)
hist.to_csv(ROOT/"out/ktff_elo_tarihce.csv", index=False)

# güncel sezondaki takımlar
son_sezon = df.sezon.max()
aktif = df[df.sezon == son_sezon]
lig_of = {}
for _, r in aktif.iterrows():
    lig_of[r.home] = r.lig; lig_of[r.away] = r.lig
final["lig"] = final.takim.map(lig_of).fillna("Aktif değil")
final["siralama"] = final.elo.rank(ascending=False).astype(int)
final.to_csv(ROOT/"out/ktff_elo_siralama.csv", index=False)

# sezon sonu reytingleri (her sezonun son maçından sonra)
son_kayit = (hist.sort_values("date").groupby(["sezon","takim"]).elo.last().reset_index())
son_kayit.to_csv(ROOT/"out/ktff_elo_sezon_sonu.csv", index=False)

# zirve reytingler
zirve = hist.loc[hist.groupby("takim").elo.idxmax()][["takim","elo","date","sezon"]] \
            .sort_values("elo", ascending=False)
zirve.to_csv(ROOT/"out/ktff_elo_zirve.csv", index=False)

# --- dürüst (zaman-dışı) değerlendirme: 2020-21 ve sonrası test ---
from tune import evaluate, FIT_END
# taban modeller nihai P'den türetilir: yalnız ayırt edici parametre yazılır
hold = {n: evaluate(df, pp) for n, pp in {
    "Gol farkı ağırlıklı (nihai)": P,
    "Klasik ELO (sabit K)":        replace(P, gd_mode="flat", k=48),  # k=48: taramanın en iyi flat değeri
    "Sezon çekmesi yok":           replace(P, regress=0.0),
}.items()}
karsilastirma = pd.DataFrame([{"model": n, "logloss": v["logloss"], "brier": v["brier"],
                               "isabet": v["acc"], "test_mac": v["n_test"]} for n, v in hold.items()])
bs = ev[ev.sezon <= FIT_END].sonuc.value_counts(normalize=True)
pb = np.array([bs.get("A",0), bs.get("D",0), bs.get("H",0)])
yt = ev[ev.sezon > FIT_END].sonuc.map({"A":0,"D":1,"H":2}).to_numpy()
karsilastirma.loc[len(karsilastirma)] = ["Taban oran (referans)",
    float(-np.log(pb[yt]).mean()),
    float(((np.tile(pb,(len(yt),1)) - np.eye(3)[yt])**2).sum(1).mean()),
    float((pb.argmax() == yt).mean()), int(len(yt))]
karsilastirma.to_csv(ROOT/"out/model_karsilastirma.csv", index=False)
print("\n— Zaman-dışı test (2020-21 sonrası) —")
print(karsilastirma.to_string(index=False))

meta = dict(params=P.__dict__, mac_sayisi=int(len(matches)),
            kulup_sayisi=int(final.shape[0]), ilk=str(df.date.min().date()),
            son=str(df.date.max().date()), logit=dict(b=float(b), c1=float(c1), c2=float(c2)),
            ev_avantaji_elo=float(home_edge), logloss_icsel=float(ll), isabet_icsel=float(acc),
            holdout=karsilastirma.to_dict("records"))
(ROOT/"out/model_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(meta, ensure_ascii=False, indent=2))
print("\n— Güncel ELO ilk 15 —")
print(final.head(15).to_string(index=False))
print("\n— Tüm zamanların en yüksek 10 ELO'su —")
print(zirve.head(10).to_string(index=False))
