"""KTFF Süper Lig + 1.Lig maç veri setini kanonik CSV'ye çevirir."""
import sys, pandas as pd, pathlib
sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 konsolunda Türkçe çıktı çökmesin


ROOT = pathlib.Path(__file__).resolve().parents[1]
teams = [l.strip() for l in (ROOT/"data/teams_raw.txt").read_text(encoding="utf-8").splitlines() if l.strip()]

# Sponsor adı / yazım farkı birleştirmeleri (aynı kulüp, farklı etiket)
ALIAS = {
    "Yonpaş Dumlupınar TSK": "Dumlupınar TSK",
    "GAÜ Çetinkaya TSK": "Çetinkaya TSK",
    "China Bazaar Gençlik Gücü TSK": "Gençlik Gücü TSK",
    "Değirmenlik Spor Kulübü": "Değirmenlik SK",
    "German Gold Akova Vuda TÇBSK": "Akova Vuda TÇBSK",
    "DND L. Gençler Birliği SK": "L. Gençler Birliği SK",
    "Pera L. Gençler Birliği SK": "L. Gençler Birliği SK",
    "Çello Dikmen Gücü SK": "Dikmen Gücü SK",
    "Yeni Mesarya Türkmenköy ASK": "Türkmenköy ASK",
}
canon = [ALIAS.get(t, t) for t in teams]

df = pd.read_csv(ROOT/"data/matches_raw.csv", header=None,
                 names=["lig","date","time","match_id","h","a","hg","ag","hukmen"])
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
df["home"] = df["h"].map(lambda i: canon[i])
df["away"] = df["a"].map(lambda i: canon[i])
df["lig"] = df["lig"].map({1: "Süper Lig", 2: "1. Lig"})

# Sezon: Ağustos-Aralık -> o yıl başlar, Ocak-Temmuz -> önceki yıl
start = df["date"].dt.year - (df["date"].dt.month < 8).astype(int)
df["sezon"] = start.astype(str) + "-" + (start + 1).astype(str)
df["url"] = "https://ktff.org/maclar/" + df["match_id"].astype(str)
df["sonuc"] = df.apply(lambda r: "H" if r.hg > r.ag else ("A" if r.hg < r.ag else "D"), axis=1)

df = df.sort_values(["date", "match_id"]).reset_index(drop=True)
# Çift devreli ligde her (ev, deplasman) çifti sezonda bir kez oynanır.
# 2011-13 kayıtlarında aynı çift ikinci kez görünüyor (KTFF arşiv hatası) -> işaretle.
df["supheli_tekrar"] = df.duplicated(["sezon","lig","home","away"], keep="first").astype(int)
out = df[["date","sezon","lig","home","away","hg","ag","sonuc","hukmen","supheli_tekrar","match_id","url"]]
out.to_csv(ROOT/"out/ktff_maclar.csv", index=False, encoding="utf-8")

print("maç:", len(out), "| kulüp:", len(set(out.home) | set(out.away)))
print("sezon:", out.sezon.min(), "->", out.sezon.max())
print(out.groupby("lig").size().to_string())
# tutarlılık: sezon-lig başına maç ve takım sayısı
chk = out.groupby(["sezon","lig"]).agg(mac=("home","size"),
        takim=("home", lambda s: len(set(s))))
print(chk.to_string())
