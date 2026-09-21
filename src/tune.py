"""Parametre taraması + model doğrulama (log-loss / Brier / isabet)."""
import itertools, sys, numpy as np, pandas as pd, pathlib
sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin

from scipy.optimize import minimize
from elo import EloParams, run

ROOT = pathlib.Path(__file__).resolve().parents[1]
BURN_IN = "2013-2014"      # ilk 2 sezon ısınma, değerlendirmeye girmez
FIT_END = "2019-2020"      # sıralı logit bu sezona kadar eğitilir
def seasons_le(s, ref): return s <= ref

def ordered_logit_fit(x, y):
    """y: 0=deplasman, 1=beraberlik, 2=ev. P(ev) ve P(ev veya beraberlik) eşikli."""
    def nll(th):
        b, c1, c2 = th[0], th[1], th[1] + np.exp(th[2])
        z = b * x
        p_le1 = 1 / (1 + np.exp(-(c2 - z)))   # P(sonuç <= beraberlik)
        p_le0 = 1 / (1 + np.exp(-(c1 - z)))   # P(sonuç == deplasman)
        p = np.where(y == 0, p_le0, np.where(y == 1, p_le1 - p_le0, 1 - p_le1))
        return -np.log(np.clip(p, 1e-12, 1)).sum()
    res = minimize(nll, [0.004, -1.0, 0.0], method="Nelder-Mead",
                   options=dict(maxiter=4000, xatol=1e-8, fatol=1e-8))
    return res.x

def probs(th, x):
    b, c1, c2 = th[0], th[1], th[1] + np.exp(th[2])
    z = b * x
    p_le0 = 1 / (1 + np.exp(-(c1 - z)))
    p_le1 = 1 / (1 + np.exp(-(c2 - z)))
    return np.column_stack([p_le0, p_le1 - p_le0, 1 - p_le1])

def evaluate(df, p: EloParams):
    m, _, _ = run(df, p)
    m = m[m.sezon >= BURN_IN]
    y = m.sonuc.map({"A": 0, "D": 1, "H": 2}).to_numpy()
    x = m.elo_diff.to_numpy()
    fit = m.sezon <= FIT_END
    th = ordered_logit_fit(x[fit], y[fit])
    te = ~fit
    P = probs(th, x[te])
    yt = y[te]
    ll = -np.log(np.clip(P[np.arange(len(yt)), yt], 1e-12, 1)).mean()
    onehot = np.zeros_like(P); onehot[np.arange(len(yt)), yt] = 1
    brier = ((P - onehot) ** 2).sum(1).mean()
    acc = (P.argmax(1) == yt).mean()
    return dict(logloss=ll, brier=brier, acc=acc, n_test=int(te.sum()), theta=th)

if __name__ == "__main__":
    df = pd.read_csv(ROOT / "out/ktff_maclar.csv", parse_dates=["date"])
    df = df[df.supheli_tekrar == 0]

    grid = dict(k=[24, 32, 40, 48, 56, 64, 80], hfa=[0, 20, 40, 60, 80, 100],
                regress=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5], gd_mode=["wfe", "flat"])
    out = []
    for k, hfa, reg, mode in itertools.product(*grid.values()):
        p = EloParams(k=k, hfa=hfa, regress=reg, gd_mode=mode)
        s = evaluate(df, p)
        out.append(dict(k=k, hfa=hfa, regress=reg, gd_mode=mode, **{q: s[q] for q in ("logloss","brier","acc")}))
    res = pd.DataFrame(out).sort_values("logloss")
    res.to_csv(ROOT / "out/parametre_taramasi.csv", index=False)
    print(res.head(12).to_string(index=False))
    print("\nEn iyi klasik (flat):")
    print(res[res.gd_mode == "flat"].head(3).to_string(index=False))

    # temel karşılaştırmalar
    m, _, _ = run(df, EloParams())
    m = m[m.sezon >= BURN_IN]
    y = m.sonuc.map({"A":0,"D":1,"H":2}).to_numpy()
    te = (m.sezon > FIT_END).to_numpy(); fitm = ~te
    base = np.bincount(y[fitm], minlength=3) / fitm.sum()
    P = np.tile(base, (te.sum(), 1)); yt = y[te]
    print("\nTemel (sabit taban oran) log-loss: %.4f  isabet: %.3f"
          % (-np.log(P[np.arange(len(yt)), yt]).mean(), (P.argmax(1)==yt).mean()))
    print("Taban oranlar (ev/bera/dep):", np.round(base[::-1], 3))
