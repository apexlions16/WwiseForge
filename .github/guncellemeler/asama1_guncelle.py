from pathlib import Path
import re


KAYNAK = Path("WwiseForge.py")
OKUBENI = Path("README.md")


def degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    adet = metin.count(eski)
    if adet != 1:
        raise RuntimeError(f"{ad}: beklenen metin sayısı 1, bulunan {adet}")
    return metin.replace(eski, yeni, 1)


def desen_degistir(metin: str, desen: str, yeni: str, ad: str) -> str:
    sonuc, adet = re.subn(desen, yeni, metin, count=1, flags=re.S)
    if adet != 1:
        raise RuntimeError(f"{ad}: desen bulunamadı veya birden fazla eşleşti")
    return sonuc


kaynak = KAYNAK.read_text(encoding="utf-8")

kaynak = degistir(
    kaynak,
    '# python -m PyInstaller --noconfirm --clean --onefile --windowed --name "WwiseForge-v0.1.0" "WwiseForge.py"',
    '# python -m PyInstaller --noconfirm --clean --onefile --windowed --name "WwiseForge-v0.2.0" "WwiseForge.py"',
    "PyInstaller sürümü",
)
kaynak = degistir(kaynak, 'UYGULAMA_SURUMU = "0.1.0"', 'UYGULAMA_SURUMU = "0.2.0"', "uygulama sürümü")
kaynak = degistir(
    kaynak,
    'from PySide6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QTextCursor',
    'from PySide6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QTextCursor, QDesktopServices\n\nfrom wwiseforge_yollar import KlasorYoneticisi',
    "klasör yöneticisi içe aktarımı",
)

kaynak = degistir(
    kaynak,
    '''class WemEntry:
    """Bir .wem dosyasının bilgilerini ve verisini tutar."""
    def __init__(self, wem_id: int, offset: int, size: int, data: bytes):
        self.wem_id = wem_id
        self.original_offset = offset 
        self.size = size
        self.data = data
        self.modified = False 
''',
    '''class WemEntry:
    """Bir .wem dosyasının bilgilerini, güncel verisini ve özgün durumunu tutar."""
    def __init__(self, wem_id: int, offset: int, size: int, data: bytes):
        self.wem_id = wem_id
        self.original_offset = offset
        self.data = bytes(data)
        self.original_data = bytes(data)
        self.size = len(self.data)
        self.modified = False

    def veriyi_degistir(self, yeni_veri: bytes):
        self.data = bytes(yeni_veri)
        self.size = len(self.data)
        self.modified = self.data != self.original_data

    def ozgun_haline_don(self):
        self.data = bytes(self.original_data)
        self.size = len(self.data)
        self.modified = False

    def mevcut_hali_kabul_et(self):
        self.original_data = bytes(self.data)
        self.size = len(self.data)
        self.modified = False
''',
    "WEM özgün veri takibi",
)

kaynak = degistir(
    kaynak,
    '''    def replace_wem(self, wem_id: int, new_data: bytes) -> bool:
        for entry in self.wem_list:
            if entry.wem_id == wem_id:
                entry.data = new_data
                entry.size = len(new_data)
                entry.modified = True
                return True
        return False

    def save_bnk(self, output_path: str):
''',
    '''    def replace_wem(self, wem_id: int, new_data: bytes) -> bool:
        for entry in self.wem_list:
            if entry.wem_id == wem_id:
                entry.veriyi_degistir(new_data)
                return True
        return False

    def degisen_sayisi(self) -> int:
        return sum(1 for entry in self.wem_list if entry.modified)

    def degisiklik_var_mi(self) -> bool:
        return self.degisen_sayisi() > 0

    def wem_geri_al(self, wem_id: int) -> bool:
        for entry in self.wem_list:
            if entry.wem_id == wem_id and entry.modified:
                entry.ozgun_haline_don()
                return True
        return False

    def tumunu_geri_al(self) -> int:
        adet = 0
        for entry in self.wem_list:
            if entry.modified:
                entry.ozgun_haline_don()
                adet += 1
        return adet

    def mevcut_hali_kabul_et(self):
        for entry in self.wem_list:
            entry.mevcut_hali_kabul_et()

    def save_bnk(self, output_path: str):
''',
    "BNK geri alma yöntemleri",
)

ayarlar = '''class SettingsDialog(QDialog):
    """VGMStream, yedekleme ve kullanıcı klasörleri için ayar penceresi."""

    KLASOR_ETIKETLERI = {
        "gecici": "Geçici çalışma klasörü",
        "yedek": "Yedek klasörü",
        "cikti": "Varsayılan çıktı klasörü",
        "wav": "WAV dışa aktarma klasörü",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.resize(820, 430)
        self.settings = QSettings("WwiseForge", "WwiseForge")
        self.klasor_yoneticisi = KlasorYoneticisi(self.settings)
        self.klasor_edits = {}

        ana_layout = QVBoxLayout(self)
        sekmeler = QTabWidget()
        ana_layout.addWidget(sekmeler)

        genel = QWidget()
        genel_form = QFormLayout(genel)
        self.txt_vgm = QLineEdit()
        self.txt_vgm.setText(self.settings.value("vgmstream_yolu", ""))
        btn_vgm = QPushButton("Seç")
        btn_vgm.clicked.connect(self.select_vgm)
        vgm_satiri = QHBoxLayout()
        vgm_satiri.addWidget(self.txt_vgm)
        vgm_satiri.addWidget(btn_vgm)
        genel_form.addRow("VGMStream CLI:", vgm_satiri)

        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 50)
        self.spin_count.setValue(int(self.settings.value("yedek_sayisi", 3)))
        genel_form.addRow("Maks. Yedek Sayısı:", self.spin_count)

        self.spin_age = QSpinBox()
        self.spin_age.setRange(1, 365)
        self.spin_age.setValue(int(self.settings.value("yedek_yasi", 7)))
        genel_form.addRow("Maks. Yedek Yaşı (Gün):", self.spin_age)
        sekmeler.addTab(genel, "Genel")

        klasorler = QWidget()
        klasor_form = QFormLayout(klasorler)
        bilgi = QLabel(
            "Varsayılan klasörler EXE dosyasının bulunduğu dizinin altında oluşturulur. "
            "Kaynak koddan çalıştırmada proje dizini kullanılır."
        )
        bilgi.setWordWrap(True)
        klasor_form.addRow(bilgi)

        for tur, etiket in self.KLASOR_ETIKETLERI.items():
            edit = QLineEdit(str(self.klasor_yoneticisi.yol(tur)))
            self.klasor_edits[tur] = edit
            satir = QHBoxLayout()
            satir.addWidget(edit)
            btn_sec = QPushButton("Seç")
            btn_sec.clicked.connect(lambda _=False, t=tur: self.klasor_sec(t))
            btn_ac = QPushButton("Aç")
            btn_ac.clicked.connect(lambda _=False, t=tur: self.klasor_ac(t))
            btn_varsayilan = QPushButton("Varsayılan")
            btn_varsayilan.clicked.connect(lambda _=False, t=tur: self.klasor_varsayilan(t))
            satir.addWidget(btn_sec)
            satir.addWidget(btn_ac)
            satir.addWidget(btn_varsayilan)
            klasor_form.addRow(f"{etiket}:", satir)
        sekmeler.addTab(klasorler, "Klasörler")

        dugmeler = QHBoxLayout()
        dugmeler.addStretch()
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.save_settings)
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        dugmeler.addWidget(btn_save)
        dugmeler.addWidget(btn_cancel)
        ana_layout.addLayout(dugmeler)

    def select_vgm(self):
        baslangic = self.txt_vgm.text() or str(self.klasor_yoneticisi.kok_dizin)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "VGMStream Seç",
            baslangic,
            "Çalıştırılabilir dosya (*.exe);;Tüm dosyalar (*)",
        )
        if path:
            self.txt_vgm.setText(path)

    def klasor_sec(self, tur: str):
        mevcut = self.klasor_edits[tur].text() or str(self.klasor_yoneticisi.varsayilan_yol(tur))
        secilen = QFileDialog.getExistingDirectory(self, "Klasör Seç", mevcut)
        if secilen:
            self.klasor_edits[tur].setText(secilen)

    def klasor_ac(self, tur: str):
        try:
            hedef = KlasorYoneticisi.dogrula_ve_hazirla(self.klasor_edits[tur].text())
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(hedef))):
                raise OSError("Dosya yöneticisi isteği kabul etmedi.")
        except Exception as exc:
            QMessageBox.critical(self, "Klasör Açılamadı", str(exc))

    def klasor_varsayilan(self, tur: str):
        self.klasor_edits[tur].setText(str(self.klasor_yoneticisi.varsayilan_yol(tur)))

    def save_settings(self):
        try:
            yeni_yollar = {}
            for tur, edit in self.klasor_edits.items():
                metin = edit.text().strip()
                hedef = metin or str(self.klasor_yoneticisi.varsayilan_yol(tur))
                yeni_yollar[tur] = KlasorYoneticisi.dogrula_ve_hazirla(hedef)

            self.settings.setValue("vgmstream_yolu", self.txt_vgm.text().strip())
            self.settings.setValue("yedek_sayisi", self.spin_count.value())
            self.settings.setValue("yedek_yasi", self.spin_age.value())
            for tur, hedef in yeni_yollar.items():
                self.klasor_yoneticisi.ayarla(tur, hedef)
            self.settings.sync()
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Ayarlar Kaydedilemedi", str(exc))

class HexEditorDialog(QDialog):'''
kaynak = desen_degistir(
    kaynak,
    r'class SettingsDialog\(QDialog\):.*?class HexEditorDialog\(QDialog\):',
    ayarlar,
    "Ayarlar penceresi",
)

kaynak = degistir(
    kaynak,
    '''        self.temp_dir = tempfile.mkdtemp(prefix="wwiseforge_")
        self.settings = QSettings("WwiseForge", "WwiseForge")
''',
    '''        self.settings = QSettings("WwiseForge", "WwiseForge")
        self.klasor_yoneticisi = KlasorYoneticisi(self.settings)
        self.temp_dir = str(self.klasor_yoneticisi.oturum_klasoru())
''',
    "oturum klasörü",
)

kaynak = degistir(
    kaynak,
    '        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)\n',
    '        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)\n        self.tree_widget.itemSelectionChanged.connect(self.update_revert_buttons)\n',
    "geri alma düğmesi seçimi",
)

kaynak = degistir(
    kaynak,
    '''        self.btn_cue_transfer.clicked.connect(self.batch_transfer_cue_data)
        self.btn_cue_transfer.setEnabled(False)
        
        action_layout.addWidget(self.btn_replace_single)
        action_layout.addWidget(self.btn_batch_replace)
        action_layout.addWidget(self.btn_cue_transfer)
''',
    '''        self.btn_cue_transfer.clicked.connect(self.batch_transfer_cue_data)
        self.btn_cue_transfer.setEnabled(False)

        self.btn_revert_wem = QPushButton("Seçili WEM'i Geri Al")
        self.btn_revert_wem.clicked.connect(self.revert_selected_wem)
        self.btn_revert_wem.setEnabled(False)

        self.btn_revert_bnk = QPushButton("BNK Değişikliklerini Geri Al")
        self.btn_revert_bnk.clicked.connect(self.revert_selected_bnk)
        self.btn_revert_bnk.setEnabled(False)

        self.btn_revert_all = QPushButton("Tüm Değişiklikleri Geri Al")
        self.btn_revert_all.clicked.connect(self.revert_all_changes)
        self.btn_revert_all.setEnabled(False)
        
        action_layout.addWidget(self.btn_replace_single)
        action_layout.addWidget(self.btn_batch_replace)
        action_layout.addWidget(self.btn_cue_transfer)
        action_layout.addWidget(self.btn_revert_wem)
        action_layout.addWidget(self.btn_revert_bnk)
        action_layout.addWidget(self.btn_revert_all)
''',
    "geri alma düğmeleri",
)

kaynak = degistir(
    kaynak,
    '''        self.status_bar = self.statusBar()
        self.status_bar.showMessage(f"Hazır — Sürüm {UYGULAMA_SURUMU}")
''',
    '''        self.status_bar = self.statusBar()
        self.lbl_change_summary = QLabel("Değişiklik yok")
        self.status_bar.addPermanentWidget(self.lbl_change_summary)
        self.status_bar.showMessage(f"Hazır — Sürüm {UYGULAMA_SURUMU}")
        self.update_change_status()
''',
    "değişiklik özeti",
)

kaynak = degistir(
    kaynak,
    '''            folder = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            filename_stem = Path(filepath).stem
            
            # Alt klasör: .yedek/dosya_adi_yedekleri/
            backup_root = os.path.join(folder, ".yedek")
            if not os.path.exists(backup_root):
                os.makedirs(backup_root)
                if os.name == 'nt': subprocess.check_call(["attrib", "+H", backup_root])
                
            file_backup_dir = os.path.join(backup_root, f"{filename_stem}_backups")
            if not os.path.exists(file_backup_dir):
                os.makedirs(file_backup_dir)
''',
    '''            filename = os.path.basename(filepath)
            filename_stem = Path(filepath).stem
            backup_root = self.klasor_yoneticisi.yol("yedek")
            file_backup_dir = str(backup_root / f"{filename_stem}_yedekleri")
            os.makedirs(file_backup_dir, exist_ok=True)
''',
    "yedek klasörü",
)

kaynak = degistir(
    kaynak,
    '''        folder = os.path.dirname(target_file)
        filename_stem = Path(target_file).stem
        # Alt klasörden bul
        backup_dir = os.path.join(folder, ".yedek", f"{filename_stem}_backups")
''',
    '''        filename_stem = Path(target_file).stem
        backup_dir = str(self.klasor_yoneticisi.yol("yedek") / f"{filename_stem}_yedekleri")
''',
    "yedekten geri yükleme yolu",
)
kaynak = degistir(kaynak, '                self.clear_list()\n', '                self.clear_list(zorla=True)\n', "zorunlu liste temizleme")

kaynak = degistir(
    kaynak,
    '''            action_export = QAction("WAV Olarak Dışa Aktar", self)
            action_export.triggered.connect(self.export_wav)
            menu.addAction(action_export)
            
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))
''',
    '''            action_export = QAction("WAV Olarak Dışa Aktar", self)
            action_export.triggered.connect(self.export_wav)
            menu.addAction(action_export)

            entry = item.data(0, Qt.UserRole)
            if entry and entry.modified:
                action_revert = QAction("Bu WEM Değişikliğini Geri Al", self)
                action_revert.triggered.connect(lambda: self.revert_wem_item(item))
                menu.addAction(action_revert)
            
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))
''',
    "bağlam menüsü geri alma",
)

kaynak = degistir(
    kaynak,
    '        save_dir = QFileDialog.getExistingDirectory(self, "Dışa Aktarılacak Klasörü Seç")\n',
    '        save_dir = QFileDialog.getExistingDirectory(self, "Dışa Aktarılacak Klasörü Seç", str(self.klasor_yoneticisi.yol("wav")))\n',
    "WAV klasörü",
)

kaynak = degistir(
    kaynak,
    '                self.status_bar.showMessage(f"Kimlik {entry.wem_id} Onaltılık Düzenleyici ile güncellendi.")\n',
    '                self.status_bar.showMessage(f"Kimlik {entry.wem_id} Onaltılık Düzenleyici ile güncellendi.")\n                self.update_change_status()\n',
    "onaltılık değişiklik takibi",
)

kaynak = desen_degistir(
    kaynak,
    r'    def open_settings\(self\):.*?    def load_bnk_files\(self\):',
    '''    def open_settings(self):
        eski_temp = self.temp_dir
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.klasor_yoneticisi = KlasorYoneticisi(self.settings)
            self.stop_audio()
            self.temp_dir = str(self.klasor_yoneticisi.oturum_klasoru())
            try:
                shutil.rmtree(eski_temp, ignore_errors=True)
            except Exception:
                pass
            self.status_bar.showMessage("Klasör ayarları uygulandı.")

    def clear_list(self, checked=False, zorla=False):
        if not zorla and self.has_unsaved_changes():
            if not self.confirm_discard_changes("listeyi temizlemek"):
                return
        self.tree_widget.clear()
        self.stop_audio()
        self.btn_save.setEnabled(False)
        self.btn_cue_transfer.setEnabled(False)
        self.apk_work_dir = None
        self.current_apk_dummy = 0
        self.apk_source_path = None
        self.btn_save_apk.setEnabled(False)
        self.btn_restore.setEnabled(False)
        self.status_bar.showMessage("Liste temizlendi.")
        self.update_change_status()

    def load_bnk_files(self):''',
    "ayar ve liste temizleme",
)

kaynak = degistir(
    kaynak,
    '''        for entry in parser.wem_list:
            child = QTreeWidgetItem(root)
            self.update_child_visuals(child, entry)
            child.setData(0, Qt.UserRole, entry)
        root.setExpanded(False)
''',
    '''        for entry in parser.wem_list:
            child = QTreeWidgetItem(root)
            self.update_child_visuals(child, entry)
            child.setData(0, Qt.UserRole, entry)
        root.setExpanded(False)
        self.update_change_status()
''',
    "BNK ekleme özeti",
)

kaynak = degistir(
    kaynak,
    '''            self.status_bar.showMessage(f"Kimlik {entry.wem_id} değiştirildi.")
        except Exception as e: QMessageBox.critical(self, "Hata", str(e))
''',
    '''            self.status_bar.showMessage(f"Kimlik {entry.wem_id} değiştirildi.")
            self.update_change_status()
        except Exception as e: QMessageBox.critical(self, "Hata", str(e))
''',
    "tekli değişiklik takibi",
)

kaynak = degistir(
    kaynak,
    '''        self.stop_audio()
        QMessageBox.information(self, "Sonuç", f"Değişen: {total_success}\nEtkilenen BNK: {total_bnks_touched}")
''',
    '''        self.stop_audio()
        self.update_change_status()
        QMessageBox.information(self, "Sonuç", f"Değişen: {total_success}\nEtkilenen BNK: {total_bnks_touched}")
''',
    "toplu değişiklik takibi",
)

son_blok = '''    def save_selected_bnk(self):
        items = self.tree_widget.selectedItems()
        if not items:
            return
        item = items[0]
        root_item = item.parent() if item.parent() else item
        parser = root_item.data(0, Qt.UserRole)
        varsayilan = self.klasor_yoneticisi.yol("cikti") / f"duzenlenmis_{parser.filename}"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "BNK Kaydet",
            str(varsayilan),
            "Wwise Ses Bankası (*.bnk)",
        )
        if not save_path:
            return
        try:
            apk_ici = bool(self.apk_work_dir and self.apk_work_dir in os.path.abspath(parser.filepath))
            rapor = self.guvenli_bnk_kaydet(parser, Path(save_path), mevcut_hali_kabul_et=not apk_ici)
            self.refresh_root_visuals(root_item)
            self.update_change_status()
            LogResultDialog("BNK Kayıt Raporu", rapor, self).exec()
        except Exception as exc:
            QMessageBox.critical(self, "Kayıt Başarısız", str(exc))

    def save_as_apk(self):
        if not self.apk_work_dir or not os.path.exists(self.apk_work_dir):
            QMessageBox.warning(self, "Hata", "APK çalışma klasörü yok!")
            return
        varsayilan = self.klasor_yoneticisi.yol("cikti") / "duzenlenmis.apk"
        out_path, _ = QFileDialog.getSaveFileName(self, "APK Kaydet", str(varsayilan), "APK (*.apk)")
        if not out_path:
            return
        try:
            rapor = self.guvenli_apk_kaydet(Path(out_path))
            for i in range(self.tree_widget.topLevelItemCount()):
                self.refresh_root_visuals(self.tree_widget.topLevelItem(i))
            self.update_change_status()
            LogResultDialog("APK Kayıt Raporu", rapor, self).exec()
        except Exception as exc:
            QMessageBox.critical(self, "APK Kayıt Başarısız", str(exc))

    def iter_root_items(self):
        for i in range(self.tree_widget.topLevelItemCount()):
            yield self.tree_widget.topLevelItem(i)

    def has_unsaved_changes(self) -> bool:
        return any(root.data(0, Qt.UserRole).degisiklik_var_mi() for root in self.iter_root_items())

    def change_summary(self):
        bnk_sayisi = 0
        wem_sayisi = 0
        for root in self.iter_root_items():
            parser = root.data(0, Qt.UserRole)
            adet = parser.degisen_sayisi()
            if adet:
                bnk_sayisi += 1
                wem_sayisi += adet
        return bnk_sayisi, wem_sayisi

    def update_change_status(self):
        bnk_sayisi, wem_sayisi = self.change_summary()
        isaret = " *" if wem_sayisi else ""
        self.setWindowTitle(
            f"{UYGULAMA_ADI} v{UYGULAMA_SURUMU} - Çoklu BNK/APK Düzenleyici{isaret}"
        )
        if hasattr(self, "lbl_change_summary"):
            if wem_sayisi:
                self.lbl_change_summary.setText(f"{bnk_sayisi} BNK, {wem_sayisi} WEM değiştirildi")
            else:
                self.lbl_change_summary.setText("Değişiklik yok")
        self.update_revert_buttons()

    def update_revert_buttons(self):
        if not hasattr(self, "btn_revert_all"):
            return
        items = self.tree_widget.selectedItems()
        entry_degismis = False
        parser_degismis = False
        if len(items) == 1:
            item = items[0]
            root = item.parent() if item.parent() else item
            parser = root.data(0, Qt.UserRole)
            parser_degismis = bool(parser and parser.degisiklik_var_mi())
            if item.parent():
                entry = item.data(0, Qt.UserRole)
                entry_degismis = bool(entry and entry.modified)
        self.btn_revert_wem.setEnabled(entry_degismis)
        self.btn_revert_bnk.setEnabled(parser_degismis)
        self.btn_revert_all.setEnabled(self.has_unsaved_changes())

    def confirm_discard_changes(self, eylem: str) -> bool:
        yanit = QMessageBox.question(
            self,
            "Kaydedilmemiş Değişiklikler",
            f"Kaydedilmemiş değişiklikler var. {eylem.capitalize()} bu değişiklikleri kaybettirecek.\n\nDevam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return yanit == QMessageBox.Yes

    def revert_wem_item(self, item):
        if not item or not item.parent():
            return
        entry = item.data(0, Qt.UserRole)
        root = item.parent()
        parser = root.data(0, Qt.UserRole)
        if parser.wem_geri_al(entry.wem_id):
            self.stop_audio()
            wav_path = Path(self.temp_dir) / f"{entry.wem_id}.wav"
            wav_path.unlink(missing_ok=True)
            self.update_child_visuals(item, entry)
            self.refresh_root_visuals(root)
            self.update_change_status()
            self.status_bar.showMessage(f"Kimlik {entry.wem_id} özgün hâline döndürüldü.")

    def revert_selected_wem(self):
        items = self.tree_widget.selectedItems()
        if len(items) == 1 and items[0].parent():
            self.revert_wem_item(items[0])

    def revert_selected_bnk(self):
        items = self.tree_widget.selectedItems()
        if not items:
            return
        root = items[0].parent() if items[0].parent() else items[0]
        parser = root.data(0, Qt.UserRole)
        if not parser or not parser.degisiklik_var_mi():
            return
        if QMessageBox.question(
            self,
            "BNK Değişikliklerini Geri Al",
            f"{parser.filename} içindeki {parser.degisen_sayisi()} değişiklik geri alınsın mı?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        adet = parser.tumunu_geri_al()
        self.refresh_root_visuals(root)
        self.update_change_status()
        self.status_bar.showMessage(f"{adet} WEM değişikliği geri alındı.")

    def revert_all_changes(self):
        bnk_sayisi, wem_sayisi = self.change_summary()
        if not wem_sayisi:
            return
        if QMessageBox.question(
            self,
            "Tüm Değişiklikleri Geri Al",
            f"{bnk_sayisi} BNK içindeki toplam {wem_sayisi} WEM değişikliği geri alınsın mı?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        for root in self.iter_root_items():
            root.data(0, Qt.UserRole).tumunu_geri_al()
            self.refresh_root_visuals(root)
        self.update_change_status()
        self.status_bar.showMessage("Tüm değişiklikler geri alındı.")

    def refresh_root_visuals(self, root):
        parser = root.data(0, Qt.UserRole)
        root.setText(0, parser.filename)
        root.setText(1, f"{len(parser.wem_list)} Dosya")
        root.setText(2, "Değişiklik var" if parser.degisiklik_var_mi() else "Orijinal")
        for i in range(root.childCount()):
            child = root.child(i)
            self.update_child_visuals(child, child.data(0, Qt.UserRole))

    @staticmethod
    def dogrula_bnk(parser: BnkParser, yol: Path):
        kontrol = BnkParser()
        kontrol.load_bnk(str(yol))
        beklenen = [(entry.wem_id, bytes(entry.data)) for entry in parser.wem_list]
        gercek = [(entry.wem_id, bytes(entry.data)) for entry in kontrol.wem_list]
        if beklenen != gercek:
            raise ValueError("BNK doğrulaması başarısız: WEM kimlikleri veya verileri eşleşmiyor.")
        return kontrol

    @staticmethod
    def atomik_yayinla(dogrulanmis_yol: Path, hedef_yol: Path):
        hedef_yol.parent.mkdir(parents=True, exist_ok=True)
        gecici_hedef = hedef_yol.parent / f".{hedef_yol.name}.wwiseforge_yaziliyor"
        try:
            shutil.copy2(dogrulanmis_yol, gecici_hedef)
            os.replace(gecici_hedef, hedef_yol)
        finally:
            gecici_hedef.unlink(missing_ok=True)

    def guvenli_bnk_kaydet(self, parser: BnkParser, hedef: Path, mevcut_hali_kabul_et=True) -> str:
        degisen = parser.degisen_sayisi()
        eski_boyut = hedef.stat().st_size if hedef.exists() else 0
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="bnk_dogrulama_",
                suffix=".bnk",
                dir=self.temp_dir,
                delete=False,
            ) as gecici:
                temp_path = Path(gecici.name)
            parser.save_bnk(str(temp_path))
            self.dogrula_bnk(parser, temp_path)
            self.atomik_yayinla(temp_path, hedef)
            if mevcut_hali_kabul_et:
                parser.mevcut_hali_kabul_et()
            yeni_boyut = hedef.stat().st_size
            return "\n".join([
                "Kayıt tamamlandı.",
                "",
                f"Dosya: {hedef}",
                f"WEM sayısı: {len(parser.wem_list)}",
                f"Kaydedilen değişiklik: {degisen}",
                f"Eski boyut: {eski_boyut} bayt",
                f"Yeni boyut: {yeni_boyut} bayt",
                "Doğrulama: Başarılı",
            ])
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

    def guvenli_apk_kaydet(self, hedef: Path) -> str:
        ilgili_parserlar = []
        degisen = 0
        for root in self.iter_root_items():
            parser = root.data(0, Qt.UserRole)
            if self.apk_work_dir in os.path.abspath(parser.filepath):
                parser.save_bnk(parser.filepath)
                ilgili_parserlar.append(parser)
                degisen += parser.degisen_sayisi()
        if not ilgili_parserlar:
            raise ValueError("APK içinde kaydedilecek BNK bulunamadı.")

        temp_apk = Path(self.temp_dir) / f"apk_dogrulama_{time.time_ns()}.apk"
        kontrol_dir = Path(self.temp_dir) / f"apk_kontrol_{time.time_ns()}"
        eski_boyut = hedef.stat().st_size if hedef.exists() else 0
        try:
            count, _ = ApkExtractor.repack_from_folder(
                self.apk_work_dir,
                str(temp_apk),
                self.current_apk_dummy,
            )
            cikartilan, dummy = ApkExtractor.extract_bnks_from_apk(str(temp_apk), str(kontrol_dir))
            if count != len(cikartilan) or dummy != self.current_apk_dummy:
                raise ValueError("APK doğrulaması başarısız: dosya sayısı veya başlık değeri eşleşmiyor.")
            for bnk_yolu in cikartilan:
                kontrol = BnkParser()
                kontrol.load_bnk(bnk_yolu)
            self.atomik_yayinla(temp_apk, hedef)
            for parser in ilgili_parserlar:
                parser.mevcut_hali_kabul_et()
            return "\n".join([
                "APK kaydı tamamlandı.",
                "",
                f"Dosya: {hedef}",
                f"BNK sayısı: {count}",
                f"Kaydedilen WEM değişikliği: {degisen}",
                f"Eski boyut: {eski_boyut} bayt",
                f"Yeni boyut: {hedef.stat().st_size} bayt",
                "Doğrulama: Başarılı",
            ])
        finally:
            temp_apk.unlink(missing_ok=True)
            shutil.rmtree(kontrol_dir, ignore_errors=True)

    def closeEvent(self, event):
        if self.has_unsaved_changes() and not self.confirm_discard_changes("uygulamadan çıkmak"):
            event.ignore()
            return
        self.stop_audio()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        event.accept()
'''

kaynak = desen_degistir(
    kaynak,
    r'    def save_selected_bnk\(self\):.*?(?=if __name__ == "__main__":)',
    son_blok + "\n",
    "güvenli kayıt ve geri alma yöntemleri",
)

KAYNAK.write_text(kaynak, encoding="utf-8")

okubeni = OKUBENI.read_text(encoding="utf-8")
okubeni = degistir(okubeni, "**v0.1.0 — İlk test sürümü**", "**v0.2.0 — Güvenli düzenleme ve klasör yönetimi**", "README sürümü")
okubeni = degistir(
    okubeni,
    "Bu sürüm, Windows çalıştırılabilir dosyasıyla düzenli kullanıcı testlerinin başlatılması için hazırlanan ilk sürümdür. Uygulamanın sürüm numarası pencere başlığında ve durum çubuğunda gösterilir.",
    "Bu sürüm; kaydedilmemiş değişiklik takibi, WEM ve BNK geri alma, doğrulanmış güvenli kayıt ve kullanıcı tarafından seçilebilen çalışma klasörlerini ekler.",
    "README sürüm açıklaması",
)
okubeni = degistir(okubeni, "WwiseForge-v0.1.0.exe", "WwiseForge-v0.2.0.exe", "README EXE adı")
okubeni = degistir(okubeni, '--name "WwiseForge-v0.1.0"', '--name "WwiseForge-v0.2.0"', "README PyInstaller adı")
okubeni = degistir(
    okubeni,
    "- Yedekten özgün dosyayı geri yükleme\n",
    "- Yedekten özgün dosyayı geri yükleme\n- Kaydedilmemiş değişiklik sayacı ve kapanış uyarısı\n- Seçili WEM, seçili BNK veya tüm değişiklikleri geri alma\n- BNK ve APK çıktısını yeniden açarak doğrulayan güvenli kayıt\n- Geçici, yedek, çıktı ve WAV klasörlerini kullanıcı tarafından seçme\n",
    "README özellikleri",
)
okubeni = desen_degistir(
    okubeni,
    r'## Yedekleme\n\n.*?\n\n## Geliştirme düzeni',
    '''## Çalışma klasörleri ve yedekleme

Varsayılan klasörler, taşınabilir EXE dosyasının bulunduğu dizinin altında oluşturulur. Kaynak koddan çalıştırmada proje dizini kullanılır:

- `gecici`
- `yedekler`
- `ciktilar`
- `wav_ciktilari`

Kullanıcı bu dört yolu **Ayarlar > Klasörler** bölümünden ayrı ayrı değiştirebilir, varsayılana döndürebilir ve dosya yöneticisinde açabilir. Yedeklerin en fazla kaç adet tutulacağı ve kaç günlük yedeklerin korunacağı Genel sekmesinden ayarlanır.

## Güvenli düzenleme

WwiseForge, değiştirilmiş WEM kayıtlarını bellekte özgün verileriyle birlikte tutar. Seçili WEM, seçili BNK veya tüm açık dosyalardaki değişiklikler kaydetmeden geri alınabilir. BNK ve APK çıktıları önce seçilen geçici klasörde oluşturulur, yeniden açılıp doğrulanır ve yalnızca doğrulama başarılıysa hedef dosyaya aktarılır.

## Geliştirme düzeni''',
    "README klasör ve güvenlik bölümü",
)
okubeni = desen_degistir(
    okubeni,
    r'### Aşama 0 — Sürümleme ve Windows EXE yayın altyapısı\n\n.*?Sonraki aşama, bu sürüm kullanıcı tarafından test edilip onaylandıktan sonra görüşülerek belirlenecektir\.',
    '''### Aşama 0 — Sürümleme ve Windows EXE yayın altyapısı

Durum: **Tamamlandı**

Takip: [Issue #2](https://github.com/apexlions16/WwiseForge/issues/2)

Bu aşamada sürüm numarası, otomatik Windows derlemesi, Türkçe sürüm notları ve ilk test sürümü hazırlanmıştır.

### Aşama 1 — Güvenli düzenleme ve kullanıcı klasörleri

Durum: **Geliştiriliyor**

Takip: [Issue #5](https://github.com/apexlions16/WwiseForge/issues/5)

Bu aşama kaydedilmemiş değişiklik takibini, geri alma işlemlerini, doğrulanmış güvenli kaydı ve kullanıcı tarafından yönetilen geçici/yedek/çıktı klasörlerini kapsar.''',
    "README aşamalar",
)
OKUBENI.write_text(okubeni, encoding="utf-8")

print("Aşama 1 kaynak ve README güncellemesi uygulandı.")
