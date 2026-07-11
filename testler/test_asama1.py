import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONUTF8", "1")

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from wwiseforge_yollar import KlasorYoneticisi


class SahteAyarlar:
    def __init__(self):
        self.veriler = {}

    def value(self, anahtar, varsayilan=""):
        return self.veriler.get(anahtar, varsayilan)

    def setValue(self, anahtar, deger):
        self.veriler[anahtar] = deger

    def remove(self, anahtar):
        self.veriler.pop(anahtar, None)

    def sync(self):
        pass


def parca(ad: bytes, veri: bytes) -> bytes:
    return ad + struct.pack("<I", len(veri)) + veri


def bnk_olustur(yol: Path, kayitlar):
    veri = bytearray()
    didx = bytearray()
    for kimlik, icerik in kayitlar:
        dolgu = (16 - (len(veri) % 16)) % 16
        veri.extend(b"\x00" * dolgu)
        didx.extend(struct.pack("<III", kimlik, len(veri), len(icerik)))
        veri.extend(icerik)
    yol.write_bytes(
        parca(b"BKHD", struct.pack("<IIII", 1, 0, 0, 0))
        + parca(b"DIDX", bytes(didx))
        + parca(b"DATA", bytes(veri))
    )


class Asama1Testleri(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uygulama = QApplication.instance() or QApplication([])
        import WwiseForge
        cls.modul = WwiseForge

    def setUp(self):
        self.gecici = Path(tempfile.mkdtemp(prefix="wwiseforge_asama1_test_"))
        self.ayarlar = QSettings("WwiseForge", "WwiseForge")
        self.ayarlar.clear()
        self.ayarlar.setValue("gecici_klasoru", str(self.gecici / "gecici"))
        self.ayarlar.setValue("yedek_klasoru", str(self.gecici / "yedekler"))
        self.ayarlar.setValue("cikti_klasoru", str(self.gecici / "ciktilar"))
        self.ayarlar.setValue("wav_klasoru", str(self.gecici / "wav_ciktilari"))
        self.ayarlar.sync()

    def tearDown(self):
        self.ayarlar.clear()
        self.ayarlar.sync()
        shutil.rmtree(self.gecici, ignore_errors=True)

    def test_klasor_varsayilanlari_ve_ozel_yollar(self):
        sahte = SahteAyarlar()
        yonetici = KlasorYoneticisi(sahte, self.gecici)
        self.assertEqual(yonetici.varsayilan_yol("gecici"), self.gecici / "gecici")
        self.assertEqual(yonetici.varsayilan_yol("yedek"), self.gecici / "yedekler")
        self.assertEqual(yonetici.varsayilan_yol("cikti"), self.gecici / "ciktilar")
        self.assertEqual(yonetici.varsayilan_yol("wav"), self.gecici / "wav_ciktilari")

        ozel = self.gecici / "benim_gecici_klasorum"
        self.assertEqual(yonetici.ayarla("gecici", ozel), ozel)
        self.assertEqual(yonetici.yol("gecici"), ozel)
        self.assertTrue(ozel.is_dir())

        oturum = yonetici.oturum_klasoru()
        self.assertTrue(oturum.is_dir())
        self.assertEqual(oturum.parent, ozel)

        varsayilan = yonetici.varsayilana_don("gecici")
        self.assertEqual(varsayilan, self.gecici / "gecici")
        self.assertEqual(yonetici.yol("gecici"), varsayilan)

    def test_wem_ve_bnk_geri_alma(self):
        bnk_yolu = self.gecici / "ornek.bnk"
        bnk_olustur(bnk_yolu, [(101, b"birinci"), (202, b"ikinci")])
        parser = self.modul.BnkParser()
        parser.load_bnk(str(bnk_yolu))

        self.assertEqual(len(parser.wem_list), 2)
        self.assertFalse(parser.degisiklik_var_mi())
        parser.replace_wem(101, b"degismis")
        self.assertEqual(parser.degisen_sayisi(), 1)
        self.assertTrue(parser.wem_geri_al(101))
        self.assertEqual(parser.wem_list[0].data, b"birinci")
        self.assertFalse(parser.degisiklik_var_mi())

        parser.replace_wem(101, b"a")
        parser.replace_wem(202, b"b")
        self.assertEqual(parser.tumunu_geri_al(), 2)
        self.assertEqual([e.data for e in parser.wem_list], [b"birinci", b"ikinci"])

    def test_guvenli_bnk_kaydi_ve_degisim_gostergesi(self):
        bnk_yolu = self.gecici / "girdi.bnk"
        bnk_olustur(bnk_yolu, [(11, b"ses-a"), (22, b"ses-b")])

        pencere = self.modul.MainWindow()
        try:
            pencere.process_bnk(str(bnk_yolu))
            root = pencere.tree_widget.topLevelItem(0)
            parser = root.data(0, self.modul.Qt.UserRole)
            parser.replace_wem(11, b"yeni-ses-a")
            pencere.refresh_root_visuals(root)
            pencere.update_change_status()

            self.assertIn("*", pencere.windowTitle())
            self.assertIn("1 WEM", pencere.lbl_change_summary.text())

            hedef = self.gecici / "ciktilar" / "guvenli.bnk"
            rapor = pencere.guvenli_bnk_kaydet(parser, hedef)
            self.assertTrue(hedef.exists())
            self.assertIn("Doğrulama: Başarılı", rapor)
            self.assertFalse(parser.degisiklik_var_mi())

            kontrol = self.modul.BnkParser()
            kontrol.load_bnk(str(hedef))
            self.assertEqual(kontrol.wem_list[0].data, b"yeni-ses-a")
        finally:
            pencere.clear_list(zorla=True)
            shutil.rmtree(pencere.temp_dir, ignore_errors=True)
            pencere.close()

    def test_guvenli_apk_kaydi(self):
        kaynak_klasor = self.gecici / "apk_kaynak"
        kaynak_klasor.mkdir()
        bnk_olustur(kaynak_klasor / "00000001.bnk", [(1, b"ilk")])
        bnk_olustur(kaynak_klasor / "00000002.bnk", [(2, b"ikinci")])
        apk_yolu = self.gecici / "ornek.apk"
        self.modul.ApkExtractor.repack_from_folder(str(kaynak_klasor), str(apk_yolu), dummy=77)

        pencere = self.modul.MainWindow()
        try:
            pencere.process_apk(str(apk_yolu))
            self.assertEqual(pencere.tree_widget.topLevelItemCount(), 2)
            root = pencere.tree_widget.topLevelItem(0)
            parser = root.data(0, self.modul.Qt.UserRole)
            parser.replace_wem(parser.wem_list[0].wem_id, b"apk-yeni")
            pencere.refresh_root_visuals(root)
            pencere.update_change_status()

            hedef = self.gecici / "ciktilar" / "guvenli.apk"
            rapor = pencere.guvenli_apk_kaydet(hedef)
            self.assertTrue(hedef.exists())
            self.assertIn("Doğrulama: Başarılı", rapor)

            cikartma = self.gecici / "apk_kontrol"
            bnks, dummy = self.modul.ApkExtractor.extract_bnks_from_apk(str(hedef), str(cikartma))
            self.assertEqual(dummy, 77)
            self.assertEqual(len(bnks), 2)
            for yol in bnks:
                kontrol = self.modul.BnkParser()
                kontrol.load_bnk(yol)
                self.assertGreaterEqual(len(kontrol.wem_list), 1)
        finally:
            pencere.clear_list(zorla=True)
            shutil.rmtree(pencere.temp_dir, ignore_errors=True)
            pencere.close()

    def test_ayarlar_penceresi_klasorleri_gosteriyor(self):
        dialog = self.modul.SettingsDialog()
        try:
            self.assertEqual(set(dialog.klasor_edits), {"gecici", "yedek", "cikti", "wav"})
            self.assertEqual(Path(dialog.klasor_edits["gecici"].text()), self.gecici / "gecici")
            self.assertEqual(Path(dialog.klasor_edits["yedek"].text()), self.gecici / "yedekler")
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
