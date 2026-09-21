@echo off
REM KTFF'den yeni sonuclari ceker; degisiklik varsa GitHub'a push eder.
REM Push'u goren GitHub Actions modeli kurar ve siteyi Cloudflare'e yayimlar.
REM
REM Haftalik gorev olarak kaydetmek icin (yonetici gerekmez):
REM   schtasks /create /tn "KTFF ELO haftalik" /tr "E:\Projeler\ktff-elo\guncelle.bat" ^
REM            /sc weekly /d MON /st 09:00 /f

setlocal
cd /d "%~dp0"
set LOG=%~dp0guncelle.log

echo. >> "%LOG%"
echo ===== %date% %time% ===== >> "%LOG%"

python src\ktff_cek.py >> "%LOG%" 2>&1
if errorlevel 1 (
    echo KAZIMA BASARISIZ, cikiliyor. >> "%LOG%"
    exit /b 1
)

git diff --quiet -- data/
if errorlevel 1 (
    echo Yeni mac var, push ediliyor... >> "%LOG%"
    git add data/ >> "%LOG%" 2>&1
    git commit -m "Haftalik guncelleme: yeni KTFF sonuclari" >> "%LOG%" 2>&1
    git push >> "%LOG%" 2>&1
    if errorlevel 1 (
        echo PUSH BASARISIZ. >> "%LOG%"
        exit /b 1
    )
    echo Push tamam. GitHub Actions yayimi devraliyor. >> "%LOG%"
) else (
    echo Yeni mac yok, yapilacak bir sey yok. >> "%LOG%"
)

endlocal
