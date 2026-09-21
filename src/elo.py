"""KTFF ELO motoru: gol farkı ağırlıklı, ev avantajlı, sezon başı ortalamaya çekmeli."""
from dataclasses import dataclass
import numpy as np, pandas as pd

@dataclass
class EloParams:
    """Modelin TEK parametre kaynağı. Varsayılanlar = final_model.py'nin kullandığı nihai model."""
    k: float = 40.0          # temel K katsayısı
    hfa: float = 60.0        # ev sahibi avantajı (ELO puanı)
    gd_mode: str = "wfe"     # "wfe" (gol farkı ağırlıklı) | "flat" (klasik)
    regress: float = 0.25    # sezon başı ortalamaya çekme oranı (0 = yok)
    tier_gap: float = 120.0  # Süper Lig - 1. Lig arası varsayılan fark
    new_penalty: float = 40.0  # lige yeni giren kulüp, lig ortalamasının bu kadar altında başlar
    base: float = 1500.0     # ligler arası orta nokta (taban reyting)
    scale: float = 400.0     # beklenen skor lojistiğinin ELO ölçeği
    gd_two: float = 1.5      # 2 gol farkı çarpanı
    gd_num: float = 11.0     # 3+ gol farkı çarpanı = (gd_num + fark) / gd_den
    gd_den: float = 8.0

def gd_multiplier(gd: int, p: EloParams) -> float:
    gd = abs(gd)
    if p.gd_mode == "flat" or gd <= 1:
        return 1.0
    if gd == 2:
        return p.gd_two
    return (p.gd_num + gd) / p.gd_den

def expected(dr: float, scale: float = EloParams.scale) -> float:
    return 1.0 / (1.0 + 10 ** (-dr / scale))

def run(df: pd.DataFrame, p: EloParams):
    """Kronolojik ELO. Her maç için maç ÖNCESİ reytingleri de döndürür."""
    df = df.sort_values(["date", "match_id"]).reset_index(drop=True)
    r: dict[str, float] = {}
    seen_season: dict[str, str] = {}
    rows, history = [], []
    prev_season = None

    for m in df.itertuples(index=False):
        sezon, lig = m.sezon, m.lig
        if sezon != prev_season:
            if prev_season is not None and p.regress > 0:
                mean = np.mean(list(r.values()))
                for t in r:
                    r[t] = mean + (1 - p.regress) * (r[t] - mean)
            prev_season = sezon

        tier_base = p.base + (p.tier_gap / 2 if lig == "Süper Lig" else -p.tier_gap / 2)
        for t in (m.home, m.away):
            if t not in r:
                same = [v for k, v in r.items() if seen_season.get(k) == sezon]
                anchor = np.mean(same) if same else tier_base
                r[t] = anchor - p.new_penalty
            seen_season[t] = sezon

        rh, ra = r[m.home], r[m.away]
        dr = rh + p.hfa - ra
        we = expected(dr, p.scale)
        w = 1.0 if m.hg > m.ag else (0.5 if m.hg == m.ag else 0.0)
        g = gd_multiplier(m.hg - m.ag, p)
        delta = p.k * g * (w - we)
        r[m.home] = rh + delta
        r[m.away] = ra - delta

        rows.append(dict(match_id=m.match_id, date=m.date, sezon=sezon, lig=lig,
                         home=m.home, away=m.away, hg=m.hg, ag=m.ag, sonuc=m.sonuc,
                         elo_home_pre=rh, elo_away_pre=ra, elo_diff=rh - ra,
                         elo_diff_hfa=dr, p_exp_home=we,
                         elo_home_post=r[m.home], elo_away_post=r[m.away]))
        history.append((m.date, sezon, m.home, r[m.home]))
        history.append((m.date, sezon, m.away, r[m.away]))

    matches = pd.DataFrame(rows)
    hist = pd.DataFrame(history, columns=["date", "sezon", "takim", "elo"])
    final = (pd.Series(r).sort_values(ascending=False).rename("elo")
             .rename_axis("takim").reset_index())
    return matches, hist, final
