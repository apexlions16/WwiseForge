import importlib
import math
import os
import struct
import sys
import tempfile
import wave
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

import WwiseForge as uygulama


def dogrula(kosul: bool, ileti: str) -> None:
    if not kosul:
        raise AssertionError(ileti)


def wav_verisi_olustur(frekans: int = 440, sure: float = 0.15) -> bytes:
    gecici = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    gecici.close()
    yol = Path(gecici.name)
    try:
        ornekleme_hizi = 22050
        kare_sayisi = int(ornekleme_hizi * sure)
        with wave.open(str(yol), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(ornekleme_hizi)
            kareler = bytearray()
            for i in range(kare_sayisi):
                deger = int(10000 * math.sin(2 * math.pi * frekans * i / ornekleme_hizi))
                kareler.extend(struct.pack("<h", deger))
            wav.writeframes(bytes(kareler))
        return yol.read_bytes()
    finally:
        yol.unlink(missing_ok=True)


def parca(tur: bytes, veri: bytes) -> bytes:
    return tur + struct.pack("<I", len(veri)) + veri


def bnk_olustur(yol: Path, kayitlar: list[tuple[int, bytes]]) -> None:
    veri = bytearray()
    dizin = bytearray()
    for wem_kimligi, wem_verisi in kayitlar:
        dolgu = (16 - (len(veri) % 16)) % 16
        veri.extend(b"\x00" * dolgu)
        ofset = len(veri)
        dizin.extend(struct.pack("<III", wem_kimligi, ofset, len(wem_verisi)))
        veri.extend(wem_verisi)

    icerik = b"".join(
        [
            parca(b"BKHD", struct.pack("<II", 134, 0)),
            parca(b"DIDX", bytes(dizin)),
            parca(b"DATA", bytes(veri)),
        ]
    )
    yol.write_bytes(icerik)


def bnk_ve_wem_testi(calisma: Path) -> tuple[Path, dict[int, bytes]]:
    kayitlar = {
        1001: wav_verisi_olustur(440),
        2002: wav_verisi_olustur(660),
    }
    bnk_yolu = calisma / "ornek.bnk"
    bnk_olustur(bnk_yolu, list(kayitlar.items()))

    ayrıştırıcı = uygulama.BnkParser(str(bnk_yolu))
    ayrıştırıcı.load_bnk(str(bnk_yolu))

    dogrula(len(ayrıştırıcı.wem_list) == 2, "BNK içindeki WEM kayıtları listelenemedi.")
    dogrula([girdi.wem_id for girdi in ayrıştırıcı.wem_list] == [1001, 2002], "WEM kimlikleri yanlış okundu.")
    dogrula(ayrıştırıcı.wem_list[0].data == kayitlar[1001], "İlk WEM verisi yanlış okundu.")
    dogrula(ayrıştırıcı.wem_list[1].data == kayitlar[2002], "İkinci WEM verisi yanlış okundu.")

    yeni_veri = wav_verisi_olustur(880)
    dogrula(ayrıştırıcı.replace_wem(1001, yeni_veri), "WEM değiştirme işlemi başarısız oldu.")
    dogrula(ayrıştırıcı.wem_list[0].modified, "Değiştirilen WEM işaretlenmedi.")

    kaydedilen = calisma / "kaydedilen.bnk"
    ayrıştırıcı.save_bnk(str(kaydedilen))
    yeniden = uygulama.BnkParser(str(kaydedilen))
    yeniden.load_bnk(str(kaydedilen))
    dogrula(len(yeniden.wem_list) == 2, "Kaydedilen BNK yeniden açılamadı.")
    dogrula(yeniden.wem_list[0].data == yeni_veri, "Değiştirilen WEM kaydedilen BNK içinde korunmadı.")

    print("[BAŞARILI] BNK açma, WEM listeleme, değiştirme ve yeniden kaydetme")
    return bnk_yolu, kayitlar


def apk_testi(calisma: Path, bnk_yolu: Path) -> Path:
    kaynak_klasor = calisma / "apk_kaynagi"
    kaynak_klasor.mkdir()
    birinci = kaynak_klasor / "00000001.bnk"
    ikinci = kaynak_klasor / "0000000a.bnk"
    birinci.write_bytes(bnk_yolu.read_bytes())
    ikinci.write_bytes(bnk_yolu.read_bytes())

    apk_yolu = calisma / "ornek.apk"
    adet, _ = uygulama.ApkExtractor.repack_from_folder(
        str(kaynak_klasor), str(apk_yolu), dummy=0x12345678, alignment=16
    )
    dogrula(adet == 2, "APK yeniden paketleme dosya sayısı yanlış.")
    dogrula(apk_yolu.exists() and apk_yolu.stat().st_size > 0, "APK dosyası oluşturulamadı.")

    cikti_klasoru = calisma / "apk_ciktisi"
    dosyalar, dummy = uygulama.ApkExtractor.extract_bnks_from_apk(str(apk_yolu), str(cikti_klasoru))
    dogrula(dummy == 0x12345678, "APK başlık değeri korunmadı.")
    dogrula(len(dosyalar) == 2, "APK içindeki BNK dosyaları çıkarılamadı.")
    dogrula((cikti_klasoru / "00000001.bnk").read_bytes() == birinci.read_bytes(), "İlk BNK APK içinden bozuk çıkarıldı.")
    dogrula((cikti_klasoru / "0000000a.bnk").read_bytes() == ikinci.read_bytes(), "İkinci BNK APK içinden bozuk çıkarıldı.")

    for dosya in dosyalar:
        ayrıştırıcı = uygulama.BnkParser(dosya)
        ayrıştırıcı.load_bnk(dosya)
        dogrula(len(ayrıştırıcı.wem_list) == 2, "APK içinden çıkan BNK'nin WEM kayıtları listelenemedi.")

    print("[BAŞARILI] APK oluşturma, açma, BNK çıkarma ve yeniden paketleme")
    return apk_yolu


def ayarlar_testi(calisma: Path, qt_uygulamasi: QApplication) -> Path:
    ayar_klasoru = calisma / "ayarlar"
    ayar_klasoru.mkdir()
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(ayar_klasoru))

    sahte_vgm = calisma / "vgmstream-cli.exe"
    sahte_vgm.write_bytes(b"sahte")

    ayarlar = QSettings("WwiseForge", "WwiseForge")
    ayarlar.clear()
    ayarlar.sync()

    pencere = uygulama.SettingsDialog()
    pencere.txt_vgm.setText(str(sahte_vgm))
    pencere.spin_count.setValue(9)
    pencere.spin_age.setValue(21)
    pencere.save_settings()
    qt_uygulamasi.processEvents()

    yeniden = QSettings("WwiseForge", "WwiseForge")
    yeniden.sync()
    dogrula(yeniden.value("vgmstream_yolu") == str(sahte_vgm), "VGMStream yolu ayarlarda kalıcı olmadı.")
    dogrula(int(yeniden.value("yedek_sayisi")) == 9, "Yedek sayısı ayarı kalıcı olmadı.")
    dogrula(int(yeniden.value("yedek_yasi")) == 21, "Yedek yaşı ayarı kalıcı olmadı.")

    ikinci_pencere = uygulama.SettingsDialog()
    dogrula(ikinci_pencere.txt_vgm.text() == str(sahte_vgm), "Ayarlar penceresi VGMStream yolunu yeniden okuyamadı.")
    dogrula(ikinci_pencere.spin_count.value() == 9, "Ayarlar penceresi yedek sayısını yeniden okuyamadı.")
    dogrula(ikinci_pencere.spin_age.value() == 21, "Ayarlar penceresi yedek yaşını yeniden okuyamadı.")
    ikinci_pencere.close()

    print("[BAŞARILI] Ayarlar ve VGMStream yolu kalıcılığı")
    return sahte_vgm


def arayuz_ve_ses_testi(
    calisma: Path,
    qt_uygulamasi: QApplication,
    bnk_yolu: Path,
    apk_yolu: Path,
    sahte_vgm: Path,
) -> None:
    ana_pencere = uygulama.MainWindow()
    dogrula("v0.1.0" in ana_pencere.windowTitle(), "Sürüm numarası pencere başlığında görünmüyor.")

    ana_pencere.process_bnk(str(bnk_yolu))
    dogrula(ana_pencere.tree_widget.topLevelItemCount() == 1, "BNK arayüz ağacına eklenemedi.")
    kok = ana_pencere.tree_widget.topLevelItem(0)
    dogrula(kok.childCount() == 2, "WEM kayıtları arayüz ağacında listelenemedi.")
    dogrula(kok.text(1) == "2 Dosya", "BNK WEM sayısı arayüzde yanlış gösterildi.")

    ana_pencere.clear_list()
    ana_pencere.process_apk(str(apk_yolu))
    dogrula(ana_pencere.tree_widget.topLevelItemCount() == 2, "APK içindeki BNK dosyaları arayüzde listelenemedi.")
    dogrula(ana_pencere.btn_save_apk.isEnabled(), "APK kaydet düğmesi etkinleşmedi.")
    dogrula(ana_pencere.current_apk_dummy == 0x12345678, "APK başlık değeri arayüz akışında korunmadı.")

    ana_pencere.clear_list()
    ana_pencere.process_bnk(str(bnk_yolu))
    kok = ana_pencere.tree_widget.topLevelItem(0)
    wem_ogesi = kok.child(0)
    ana_pencere.tree_widget.setCurrentItem(wem_ogesi)
    wem_ogesi.setSelected(True)
    qt_uygulamasi.processEvents()

    ana_pencere.settings.setValue("vgmstream_yolu", str(sahte_vgm))
    ana_pencere.settings.sync()

    cagrilar: list[list[str]] = []
    asil_calistir = uygulama.subprocess.run
    asil_klasor_sec = uygulama.QFileDialog.getExistingDirectory
    asil_bilgi = uygulama.QMessageBox.information
    asil_uyari = uygulama.QMessageBox.warning
    iletiler: list[str] = []

    def sahte_calistir(komut, capture_output=False, startupinfo=None):
        cagrilar.append([str(deger) for deger in komut])
        dogrula(len(komut) == 4 and komut[1] == "-o", "VGMStream komut satırı yanlış oluşturuldu.")
        cikti = Path(komut[2])
        girdi = Path(komut[3])
        cikti.write_bytes(girdi.read_bytes())
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    try:
        uygulama.subprocess.run = sahte_calistir
        uygulama.QMessageBox.information = staticmethod(
            lambda _ebeveyn, _baslik, metin: iletiler.append(str(metin)) or QMessageBox.Ok
        )
        uygulama.QMessageBox.warning = staticmethod(
            lambda _ebeveyn, _baslik, metin: iletiler.append(str(metin)) or QMessageBox.Ok
        )

        girdi = wem_ogesi.data(0, Qt.UserRole)
        dogrula(ana_pencere.convert_and_load_audio(girdi), "Ses önizleme için WAV dönüşümü başarısız oldu.")
        dogrula(ana_pencere.media_player.source().isValid(), "Dönüştürülen WAV oynatıcıya yüklenemedi.")
        dogrula(cagrilar and cagrilar[-1][0] == str(sahte_vgm), "Ayarlanan VGMStream yolu kullanılmadı.")

        disa_aktarma = calisma / "wav_ciktisi"
        disa_aktarma.mkdir()
        uygulama.QFileDialog.getExistingDirectory = staticmethod(lambda *_args, **_kwargs: str(disa_aktarma))
        ana_pencere.export_wav()
        dogrula((disa_aktarma / f"{girdi.wem_id}.wav").exists(), "WAV dışa aktarma dosyası oluşturulamadı.")
        dogrula(any("Başarılı: 1" in ileti and "Hatalı: 0" in ileti for ileti in iletiler), "WAV dışa aktarma başarı sonucu alınamadı.")

        ana_pencere.settings.setValue("vgmstream_yolu", "")
        ana_pencere.settings.sync()
        dogrula(not ana_pencere.convert_and_load_audio(girdi), "Eksik VGMStream yolunda işlem durdurulmadı.")
        dogrula(any("vgmstream-cli" in ileti for ileti in iletiler), "Eksik VGMStream yolu uyarısı gösterilmedi.")
    finally:
        uygulama.subprocess.run = asil_calistir
        uygulama.QFileDialog.getExistingDirectory = asil_klasor_sec
        uygulama.QMessageBox.information = asil_bilgi
        uygulama.QMessageBox.warning = asil_uyari
        ana_pencere.close()
        qt_uygulamasi.processEvents()

    print("[BAŞARILI] Arayüzde BNK/APK listeleme, VGMStream çağrısı, ses önizleme ve WAV dışa aktarma")


def ana() -> int:
    qt_uygulamasi = QApplication.instance() or QApplication(sys.argv[:1])
    with tempfile.TemporaryDirectory(prefix="wwiseforge_dogrulama_") as gecici:
        calisma = Path(gecici)
        bnk_yolu, _ = bnk_ve_wem_testi(calisma)
        apk_yolu = apk_testi(calisma, bnk_yolu)
        sahte_vgm = ayarlar_testi(calisma, qt_uygulamasi)
        arayuz_ve_ses_testi(calisma, qt_uygulamasi, bnk_yolu, apk_yolu, sahte_vgm)

    print("[SONUÇ] v0.1.0 kaynak işlev doğrulamalarının tamamı başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(ana())
