import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict


KLASOR_TANIMLARI: Dict[str, str] = {
    "gecici": "gecici",
    "yedek": "yedekler",
    "cikti": "ciktilar",
    "wav": "wav_ciktilari",
}


def uygulama_kok_dizini() -> Path:
    """Taşınabilir EXE için EXE dizinini, kaynak çalıştırmada proje dizinini döndürür."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class KlasorYoneticisi:
    """QSettings uyumlu bir nesne üzerinden çalışma klasörlerini yönetir."""

    def __init__(self, settings, kok_dizin: Path | None = None):
        self.settings = settings
        self.kok_dizin = Path(kok_dizin or uygulama_kok_dizini()).resolve()

    @staticmethod
    def ayar_anahtari(tur: str) -> str:
        if tur not in KLASOR_TANIMLARI:
            raise KeyError(f"Bilinmeyen klasör türü: {tur}")
        return f"{tur}_klasoru"

    def varsayilan_yol(self, tur: str) -> Path:
        if tur not in KLASOR_TANIMLARI:
            raise KeyError(f"Bilinmeyen klasör türü: {tur}")
        return (self.kok_dizin / KLASOR_TANIMLARI[tur]).resolve()

    def yol(self, tur: str, olustur: bool = True) -> Path:
        anahtar = self.ayar_anahtari(tur)
        kayitli = self.settings.value(anahtar, "")
        yol = Path(str(kayitli)).expanduser() if kayitli else self.varsayilan_yol(tur)
        if not yol.is_absolute():
            yol = (self.kok_dizin / yol).resolve()
        else:
            yol = yol.resolve()
        if olustur:
            self.dogrula_ve_hazirla(yol)
        return yol

    def ayarla(self, tur: str, yol: str | Path) -> Path:
        hedef = Path(yol).expanduser()
        if not hedef.is_absolute():
            hedef = (self.kok_dizin / hedef).resolve()
        else:
            hedef = hedef.resolve()
        self.dogrula_ve_hazirla(hedef)
        self.settings.setValue(self.ayar_anahtari(tur), str(hedef))
        if hasattr(self.settings, "sync"):
            self.settings.sync()
        return hedef

    def varsayilana_don(self, tur: str) -> Path:
        anahtar = self.ayar_anahtari(tur)
        if hasattr(self.settings, "remove"):
            self.settings.remove(anahtar)
        else:
            self.settings.setValue(anahtar, "")
        if hasattr(self.settings, "sync"):
            self.settings.sync()
        hedef = self.varsayilan_yol(tur)
        self.dogrula_ve_hazirla(hedef)
        return hedef

    @staticmethod
    def dogrula_ve_hazirla(yol: str | Path) -> Path:
        hedef = Path(yol)
        try:
            hedef.mkdir(parents=True, exist_ok=True)
            if not hedef.is_dir():
                raise NotADirectoryError(str(hedef))
            deneme = tempfile.NamedTemporaryFile(
                prefix="wwiseforge_yazma_deneyi_",
                dir=str(hedef),
                delete=False,
            )
            deneme_yolu = Path(deneme.name)
            deneme.close()
            deneme_yolu.unlink(missing_ok=True)
        except Exception as exc:
            raise OSError(f"Klasör kullanılamıyor veya yazılabilir değil: {hedef}\n{exc}") from exc
        return hedef

    def oturum_klasoru(self) -> Path:
        kok = self.yol("gecici")
        zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
        hedef = kok / f"oturum_{zaman}_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        hedef.mkdir(parents=True, exist_ok=False)
        return hedef

    def klasoru_ac(self, tur: str) -> Path:
        hedef = self.yol(tur)
        try:
            if os.name == "nt":
                os.startfile(str(hedef))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(hedef)])
            else:
                subprocess.Popen(["xdg-open", str(hedef)])
        except Exception as exc:
            raise OSError(f"Klasör açılamadı: {hedef}\n{exc}") from exc
        return hedef
