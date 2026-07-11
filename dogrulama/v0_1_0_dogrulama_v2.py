import math
import os
import struct
import sys
import tempfile
import traceback
import wave
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

import WwiseForge as uygulama


def denetle(kosul, ileti):
    if not kosul:
        raise AssertionError(ileti)


def wav_uret(frekans=440):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as gecici:
        yol = Path(gecici.name)
    try:
        hiz = 22050
        with wave.open(str(yol), "wb") as dosya:
            dosya.setnchannels(1)
            dosya.setsampwidth(2)
            dosya.setframerate(hiz)
            veri = bytearray()
            for i in range(int(hiz * 0.1)):
                veri.extend(struct.pack("<h", int(8000 * math.sin(2 * math.pi * frekans * i / hiz))))
            dosya.writeframes(bytes(veri))
        return yol.read_bytes()
    finally:
        yol.unlink(missing_ok=True)


def parca(tur, veri):
    return tur + struct.pack("<I", len(veri)) + veri


def bnk_uret(yol, kayitlar):
    veri = bytearray()
    dizin = bytearray()
    for kimlik, wem in kayitlar:
        veri.extend(b"\0" * ((16 - len(veri) % 16) % 16))
        ofset = len(veri)
        dizin.extend(struct.pack("<III", kimlik, ofset, len(wem)))
        veri.extend(wem)
    yol.write_bytes(
        parca(b"BKHD", struct.pack("<II", 134, 0))
        + parca(b"DIDX", bytes(dizin))
        + parca(b"DATA", bytes(veri))
    )


def cekirdek_testleri(calisma):
    birinci = wav_uret(440)
    ikinci = wav_uret(660)
    bnk = calisma / "ornek.bnk"
    bnk_uret(bnk, [(1001, birinci), (2002, ikinci)])

    okuyucu = uygulama.BnkParser(str(bnk))
    okuyucu.load_bnk(str(bnk))
    denetle([x.wem_id for x in okuyucu.wem_list] == [1001, 2002], "WEM kimlikleri listelenemedi.")
    denetle(okuyucu.wem_list[0].data == birinci, "WEM verisi doğru okunamadı.")

    yeni = wav_uret(880)
    denetle(okuyucu.replace_wem(1001, yeni), "WEM değiştirilemedi.")
    kayit = calisma / "kayit.bnk"
    okuyucu.save_bnk(str(kayit))
    yeniden = uygulama.BnkParser(str(kayit))
    yeniden.load_bnk(str(kayit))
    denetle(yeniden.wem_list[0].data == yeni, "Değiştirilen WEM kaydedilemedi.")
    print("[BAŞARILI] BNK açma, WEM listeleme, değiştirme ve kaydetme")

    apk_klasoru = calisma / "apk_kaynagi"
    apk_klasoru.mkdir()
    (apk_klasoru / "00000001.bnk").write_bytes(bnk.read_bytes())
    (apk_klasoru / "0000000a.bnk").write_bytes(kayit.read_bytes())
    apk = calisma / "ornek.apk"
    adet, _ = uygulama.ApkExtractor.repack_from_folder(str(apk_klasoru), str(apk), 0x12345678, 16)
    denetle(adet == 2, "APK paketleme dosya sayısı yanlış.")
    cikti = calisma / "apk_ciktisi"
    dosyalar, dummy = uygulama.ApkExtractor.extract_bnks_from_apk(str(apk), str(cikti))
    denetle(len(dosyalar) == 2, "APK içindeki BNK dosyaları çıkarılamadı.")
    denetle(dummy == 0x12345678, "APK başlık değeri korunmadı.")
    for dosya in dosyalar:
        kontrol = uygulama.BnkParser(dosya)
        kontrol.load_bnk(dosya)
        denetle(len(kontrol.wem_list) == 2, "APK içindeki BNK WEM kayıtları listelenemedi.")
    print("[BAŞARILI] APK açma, BNK çıkarma ve yeniden paketleme")
    return bnk, apk


def ayarlar_testi(calisma):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(calisma / "ayarlar"))
    vgm = calisma / "vgmstream-cli.exe"
    vgm.write_bytes(b"sahte")
    QSettings("WwiseForge", "WwiseForge").clear()

    pencere = uygulama.SettingsDialog()
    pencere.txt_vgm.setText(str(vgm))
    pencere.spin_count.setValue(8)
    pencere.spin_age.setValue(19)
    pencere.save_settings()

    kayit = QSettings("WwiseForge", "WwiseForge")
    kayit.sync()
    denetle(kayit.value("vgmstream_yolu") == str(vgm), "VGMStream yolu kaydedilmedi.")
    denetle(int(kayit.value("yedek_sayisi")) == 8, "Yedek sayısı kaydedilmedi.")
    denetle(int(kayit.value("yedek_yasi")) == 19, "Yedek yaşı kaydedilmedi.")

    yeniden = uygulama.SettingsDialog()
    denetle(yeniden.txt_vgm.text() == str(vgm), "VGMStream yolu yeniden okunamadı.")
    yeniden.close()
    print("[BAŞARILI] Ayarlar ve VGMStream yolu")
    return vgm


class SahteMesajKutusu:
    Ok = 0
    iletiler = []

    @staticmethod
    def information(_ebeveyn, baslik, metin):
        SahteMesajKutusu.iletiler.append((str(baslik), str(metin)))
        return 0

    @staticmethod
    def warning(_ebeveyn, baslik, metin):
        SahteMesajKutusu.iletiler.append((str(baslik), str(metin)))
        return 0

    @staticmethod
    def critical(_ebeveyn, baslik, metin):
        SahteMesajKutusu.iletiler.append((str(baslik), str(metin)))
        return 0


class SahteDosyaPenceresi:
    klasor = ""

    @staticmethod
    def getExistingDirectory(*_args, **_kwargs):
        return SahteDosyaPenceresi.klasor


def arayuz_testleri(calisma, bnk, apk, vgm, qt):
    pencere = uygulama.MainWindow()
    denetle("v0.1.0" in pencere.windowTitle(), "Sürüm başlıkta görünmüyor.")

    pencere.process_bnk(str(bnk))
    denetle(pencere.tree_widget.topLevelItemCount() == 1, "BNK arayüzde açılmadı.")
    kok = pencere.tree_widget.topLevelItem(0)
    denetle(kok.childCount() == 2, "WEM kayıtları arayüzde listelenmedi.")

    pencere.clear_list()
    pencere.process_apk(str(apk))
    denetle(pencere.tree_widget.topLevelItemCount() == 2, "APK içindeki BNK dosyaları arayüzde listelenmedi.")
    denetle(pencere.btn_save_apk.isEnabled(), "APK kaydet düğmesi etkinleşmedi.")

    pencere.clear_list()
    pencere.process_bnk(str(bnk))
    kok = pencere.tree_widget.topLevelItem(0)
    oge = kok.child(0)
    pencere.tree_widget.setCurrentItem(oge)
    oge.setSelected(True)
    qt.processEvents()
    girdi = oge.data(0, Qt.UserRole)

    pencere.settings.setValue("vgmstream_yolu", str(vgm))
    pencere.settings.sync()
    disa_aktarma = calisma / "wav_ciktisi"
    disa_aktarma.mkdir()
    SahteDosyaPenceresi.klasor = str(disa_aktarma)

    asil_run = uygulama.subprocess.run
    asil_mesaj = uygulama.QMessageBox
    asil_dosya = uygulama.QFileDialog
    cagrilar = []

    def sahte_run(komut, capture_output=False, startupinfo=None):
        cagrilar.append(komut)
        denetle(komut[0] == str(vgm) and komut[1] == "-o", "VGMStream komutu yanlış.")
        Path(komut[2]).write_bytes(Path(komut[3]).read_bytes())
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    try:
        uygulama.subprocess.run = sahte_run
        uygulama.QMessageBox = SahteMesajKutusu
        uygulama.QFileDialog = SahteDosyaPenceresi

        denetle(pencere.convert_and_load_audio(girdi), "Ses önizleme dönüşümü başarısız.")
        denetle(pencere.media_player.source().isValid(), "WAV oynatıcıya yüklenmedi.")
        pencere.export_wav()
        denetle((disa_aktarma / f"{girdi.wem_id}.wav").exists(), "WAV dışa aktarılmadı.")
        denetle(any("Başarılı: 1" in metin and "Hatalı: 0" in metin for _, metin in SahteMesajKutusu.iletiler), "Dışa aktarma başarı sonucu yanlış.")
        denetle(len(cagrilar) >= 2, "VGMStream önizleme ve dışa aktarma için çağrılmadı.")

        pencere.settings.setValue("vgmstream_yolu", "")
        pencere.settings.sync()
        denetle(not pencere.convert_and_load_audio(girdi), "Eksik VGMStream yolunda işlem durmadı.")
        denetle(any("vgmstream-cli" in metin for _, metin in SahteMesajKutusu.iletiler), "Eksik yol uyarısı gösterilmedi.")
    finally:
        uygulama.subprocess.run = asil_run
        uygulama.QMessageBox = asil_mesaj
        uygulama.QFileDialog = asil_dosya
        pencere.close()
        qt.processEvents()

    print("[BAŞARILI] Arayüz, VGMStream çağrısı, ses önizleme ve WAV dışa aktarma")


def ana():
    qt = QApplication.instance() or QApplication(sys.argv[:1])
    try:
        with tempfile.TemporaryDirectory(prefix="wwiseforge_test_") as gecici:
            calisma = Path(gecici)
            bnk, apk = cekirdek_testleri(calisma)
            vgm = ayarlar_testi(calisma)
            arayuz_testleri(calisma, bnk, apk, vgm, qt)
        print("[SONUÇ] Tüm kaynak işlev testleri başarılı.")
        return 0
    except Exception:
        print("[SONUÇ] Doğrulama başarısız.")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(ana())
