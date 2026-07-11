# ---------------------------------------------------------------------------
# Wwise BNK/APK Düzenleyici
# ---------------------------------------------------------------------------
#
# PyInstaller ile EXE oluşturma komutu:
# pyinstaller --noconsole --onefile --icon=simge.ico "WwiseForge.py"
#
# (Not: "simge.ico" dosyasının proje klasöründe olduğundan emin olun.)
# ---------------------------------------------------------------------------

import sys
import struct
import os
import subprocess
import shutil
import tempfile
import binascii
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                               QLineEdit, QComboBox, QMessageBox, QPlainTextEdit,
                               QHeaderView, QAbstractItemView, QGroupBox, QSplitter,
                               QSlider, QStyle, QTreeWidget, QTreeWidgetItem, QMenu,
                               QDialog, QTabWidget, QFormLayout, QSizePolicy, QSpinBox)
from PySide6.QtCore import Qt, QSettings, QUrl, QTime, QSize, QByteArray
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QTextCursor

# ---------------------------------------------------------------------------
# 1. VERİ YAPILARI VE AYRIŞTIRMA MANTIĞI (ARKA UÇ)
# ---------------------------------------------------------------------------

class WemEntry:
    """Bir .wem dosyasının bilgilerini ve verisini tutar."""
    def __init__(self, wem_id: int, offset: int, size: int, data: bytes):
        self.wem_id = wem_id
        self.original_offset = offset 
        self.size = size
        self.data = data
        self.modified = False 

class BnkParser:
    """Wwise .bnk dosyasını okuma, parçalama ve yeniden oluşturma sınıfı."""
    
    def __init__(self, filepath=""):
        self.filepath = filepath
        self.filename = os.path.basename(filepath) if filepath else ""
        self.header_chunk = b"" 
        self.other_chunks_pre_data = [] 
        self.other_chunks_post_data = [] 
        self.wem_list: List[WemEntry] = []
        self.data_chunk_header = b"" 

    def load_bnk(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.wem_list.clear()
        self.other_chunks_pre_data.clear()
        self.other_chunks_post_data.clear()
        
        with open(filepath, 'rb') as f:
            data = f.read()
            
        offset = 0
        file_size = len(data)
        
        didx_chunk = None
        data_chunk_payload = None
        
        # Basit parça ayrıştırma (RIFF biçimi)
        while offset < file_size:
            if offset + 8 > file_size:
                break
                
            chunk_type = data[offset:offset+4]
            chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            chunk_full_data = data[offset : offset + 8 + chunk_size]
            payload = data[offset+8 : offset+8+chunk_size]
            
            if chunk_type == b'BKHD':
                self.header_chunk = chunk_full_data
            elif chunk_type == b'DIDX':
                didx_chunk = payload
            elif chunk_type == b'DATA':
                self.data_chunk_header = data[offset:offset+8]
                data_chunk_payload = payload
            else:
                if data_chunk_payload is None:
                    self.other_chunks_pre_data.append(chunk_full_data)
                else:
                    self.other_chunks_post_data.append(chunk_full_data)
            
            offset += 8 + chunk_size

        if didx_chunk and data_chunk_payload:
            self._parse_wems(didx_chunk, data_chunk_payload)
        else:
            raise ValueError(f"{self.filename}: Geçersiz BNK dosyası veya DIDX/DATA parçası bulunamadı.")

    def _parse_wems(self, didx_payload: bytes, data_payload: bytes):
        num_entries = len(didx_payload) // 12
        for i in range(num_entries):
            entry_data = didx_payload[i*12 : (i+1)*12]
            w_id, w_offset, w_size = struct.unpack('<III', entry_data)
            
            if w_offset + w_size <= len(data_payload):
                wem_data = data_payload[w_offset : w_offset + w_size]
                self.wem_list.append(WemEntry(w_id, w_offset, w_size, wem_data))
            else:
                print(f"Uyarı: WEM kimliği {w_id} sınır dışı veriye işaret ediyor.")

    def replace_wem(self, wem_id: int, new_data: bytes) -> bool:
        for entry in self.wem_list:
            if entry.wem_id == wem_id:
                entry.data = new_data
                entry.size = len(new_data)
                entry.modified = True
                return True
        return False

    def save_bnk(self, output_path: str):
        new_data_payload = bytearray()
        new_didx_payload = bytearray()
        current_offset = 0
        
        for entry in self.wem_list:
            padding = (16 - (len(new_data_payload) % 16)) % 16
            if padding > 0:
                new_data_payload.extend(b'\x00' * padding)
                current_offset += padding
            
            new_didx_payload.extend(struct.pack('<III', entry.wem_id, current_offset, entry.size))
            new_data_payload.extend(entry.data)
            current_offset += entry.size
            
        with open(output_path, 'wb') as f:
            f.write(self.header_chunk)
            f.write(b'DIDX')
            f.write(struct.pack('<I', len(new_didx_payload)))
            f.write(new_didx_payload)
            for chunk in self.other_chunks_pre_data:
                f.write(chunk)
            f.write(b'DATA')
            f.write(struct.pack('<I', len(new_data_payload)))
            f.write(new_data_payload)
            for chunk in self.other_chunks_post_data:
                f.write(chunk)

# ---------------------------------------------------------------------------
# 2. APK ÇIKARICI VE YENİDEN PAKETLEYİCİ
# ---------------------------------------------------------------------------

class ApkExtractor:
    U32 = struct.Struct("<I")
    ENTRY = struct.Struct("<III") 

    @staticmethod
    def align_up(x: int, a: int) -> int:
        if a <= 1: return x
        return ((x + a - 1) // a) * a

    @staticmethod
    def extract_bnks_from_apk(apk_path: str, output_dir: str) -> Tuple[List[str], int]:
        extracted_files = []
        dummy_val = 0
        entries = []
        with open(apk_path, "rb") as f:
            head = f.read(8)
            if len(head) < 8: raise ValueError("Geçersiz APK başlığı.")
            files_count = ApkExtractor.U32.unpack_from(head, 0)[0]
            dummy_val = ApkExtractor.U32.unpack_from(head, 4)[0]
            table_size = files_count * ApkExtractor.ENTRY.size
            table = f.read(table_size)
            if len(table) < table_size: raise ValueError("Dosya tablosu bozuk.")
            off = 0
            for _ in range(files_count):
                file_id, offset, size = ApkExtractor.ENTRY.unpack_from(table, off)
                entries.append({"id": file_id, "offset": offset, "size": size})
                off += ApkExtractor.ENTRY.size

        outp = Path(output_dir)
        outp.mkdir(parents=True, exist_ok=True)
        with open(apk_path, "rb") as f:
            for e in entries:
                f.seek(e["offset"])
                blob = f.read(e["size"])
                name = f"{e['id']:08x}.bnk"
                target_path = outp / name
                target_path.write_bytes(blob)
                extracted_files.append(str(target_path))
        return extracted_files, dummy_val

    @staticmethod
    def repack_from_folder(bnk_dir: str, out_apk_path: str, dummy: int = 0, alignment: int = 4, sort_mode: str = "by_id"):
        bnk_dir = Path(bnk_dir)
        files = []
        for p in bnk_dir.glob("*.bnk"):
            stem = p.stem
            try: fid = int(stem, 16)
            except: continue
            files.append((fid, p, p.stat().st_size))

        if not files: raise ValueError("Klasörde .bnk bulunamadı.")
        if sort_mode == "by_id": files.sort(key=lambda x: x[0])
        else: files.sort(key=lambda x: str(x[1]).lower())

        header_size = 8
        table_size = len(files) * ApkExtractor.ENTRY.size
        data_start = header_size + table_size
        cur = data_start
        items = []
        for fid, path, size in files:
            cur = ApkExtractor.align_up(cur, alignment)
            items.append((fid, cur, size, path))
            cur += size

        with open(out_apk_path, "wb") as f:
            f.write(ApkExtractor.U32.pack(len(files)))
            f.write(ApkExtractor.U32.pack(dummy))
            for fid, off, size, _ in items:
                f.write(ApkExtractor.ENTRY.pack(fid, off, size))
            if f.tell() < data_start: f.write(b"\x00" * (data_start - f.tell()))
            for fid, off, size, path in items:
                if f.tell() < off: f.write(b"\x00" * (off - f.tell()))
                elif f.tell() > off: raise RuntimeError("Hizalama hatası!")
                with open(path, "rb") as bf: f.write(bf.read())
        return len(files), out_apk_path

# ---------------------------------------------------------------------------
# 3. YARDIMCI PENCERELER (GÜNLÜK, ONALTILIK, AYARLAR)
# ---------------------------------------------------------------------------

class LogResultDialog(QDialog):
    def __init__(self, title, log_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlainText(log_text)
        self.txt_log.setStyleSheet("font-family: Consolas; font-size: 10pt;")
        layout.addWidget(self.txt_log)
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class SettingsDialog(QDialog):
    """VGMStream ve yedekleme ayarları için pencere."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.resize(400, 250)
        
        self.settings = QSettings("WwiseForge", "WwiseForge")
        
        layout = QFormLayout(self)
        
        # VGMStream yolu
        self.txt_vgm = QLineEdit()
        self.txt_vgm.setText(self.settings.value("vgmstream_yolu", ""))
        btn_vgm = QPushButton("Seç")
        btn_vgm.clicked.connect(self.select_vgm)
        
        row_vgm = QHBoxLayout()
        row_vgm.addWidget(self.txt_vgm)
        row_vgm.addWidget(btn_vgm)
        layout.addRow("VGMStream CLI:", row_vgm)
        
        # Yedek sayısı
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 50)
        self.spin_count.setValue(int(self.settings.value("yedek_sayisi", 3)))
        layout.addRow("Maks. Yedek Sayısı:", self.spin_count)
        
        # Yedek yaşı
        self.spin_age = QSpinBox()
        self.spin_age.setRange(1, 365)
        self.spin_age.setValue(int(self.settings.value("yedek_yasi", 7)))
        layout.addRow("Maks. Yedek Yaşı (Gün):", self.spin_age)
        
        # Düğmeler
        btn_box = QHBoxLayout()
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.save_settings)
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

    def select_vgm(self):
        path, _ = QFileDialog.getOpenFileName(self, "VGMStream Seç", "", "Çalıştırılabilir dosya (*.exe);;Tüm dosyalar (*)")
        if path: self.txt_vgm.setText(path)

    def save_settings(self):
        self.settings.setValue("vgmstream_yolu", self.txt_vgm.text())
        self.settings.setValue("yedek_sayisi", self.spin_count.value())
        self.settings.setValue("yedek_yasi", self.spin_age.value())
        self.accept()

class HexEditorDialog(QDialog):
    def __init__(self, wem_entry: WemEntry, parent=None):
        super().__init__(parent)
        self.entry = wem_entry
        self.setWindowTitle(f"Onaltılık Düzenleyici - WEM Kimliği: {self.entry.wem_id}")
        self.resize(900, 600)
        self.new_data = None 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        info_lbl = QLabel("Sol: Onaltılık | Sağ: ASCII")
        info_lbl.setStyleSheet("color: gray; font-size: 10px;")
        info_lbl.setMaximumHeight(15)
        layout.addWidget(info_lbl)
        
        splitter = QSplitter(Qt.Horizontal)
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.Monospace)
        
        self.hex_edit = QPlainTextEdit()
        self.hex_edit.setFont(font)
        hex_data = binascii.hexlify(self.entry.data).decode('utf-8').upper()
        formatted_hex = ""
        for i in range(0, len(hex_data), 32): 
            chunk = hex_data[i:i+32]
            spaced_chunk = " ".join(chunk[j:j+2] for j in range(0, len(chunk), 2))
            formatted_hex += spaced_chunk + "\n"
        self.hex_edit.setPlainText(formatted_hex.strip())
        
        self.ascii_edit = QPlainTextEdit()
        self.ascii_edit.setFont(font)
        self.ascii_edit.setReadOnly(True)
        self.ascii_edit.setStyleSheet("background-color: #F5F5F5; color: #333;")
        
        splitter.addWidget(self.hex_edit)
        splitter.addWidget(self.ascii_edit)
        splitter.setStretchFactor(0, 3) 
        splitter.setStretchFactor(1, 1) 
        layout.addWidget(splitter)
        
        self.hex_edit.verticalScrollBar().valueChanged.connect(self.ascii_edit.verticalScrollBar().setValue)
        self.ascii_edit.verticalScrollBar().valueChanged.connect(self.hex_edit.verticalScrollBar().setValue)
        self.hex_edit.textChanged.connect(self.update_ascii_from_hex)
        self.update_ascii_from_hex()
        
        btn_layout = QHBoxLayout()
        self.btn_save_hex = QPushButton("Kaydet ve Çık")
        self.btn_save_hex.clicked.connect(self.save_hex_changes)
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save_hex)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def update_ascii_from_hex(self):
        raw_text = self.hex_edit.toPlainText()
        clean_hex = raw_text.replace(" ", "").replace("\n", "").replace("\r", "").strip()
        if len(clean_hex) % 2 != 0: clean_hex = clean_hex[:-1]
        try:
            data = binascii.unhexlify(clean_hex)
            ascii_lines = []
            chunk_size = 16
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i+chunk_size]
                line_str = ""
                for byte in chunk:
                    if 32 <= byte <= 126: line_str += chr(byte)
                    else: line_str += "."
                ascii_lines.append(line_str)
            vsb = self.ascii_edit.verticalScrollBar()
            old_val = vsb.value()
            self.ascii_edit.setPlainText("\n".join(ascii_lines))
            vsb.setValue(old_val)
        except: pass

    def save_hex_changes(self):
        raw_text = self.hex_edit.toPlainText()
        clean_hex = raw_text.replace(" ", "").replace("\n", "").replace("\r", "").strip()
        try:
            self.new_data = binascii.unhexlify(clean_hex)
            self.accept() 
        except binascii.Error:
            QMessageBox.critical(self, "Hata", "Geçersiz onaltılık biçim!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dönüştürme hatası: {str(e)}")

# ---------------------------------------------------------------------------
# 4. GRAFİK ARAYÜZ ANA PENCERESİ (ÖN YÜZ)
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WwiseForge - Çoklu BNK/APK Düzenleyici")
        self.resize(1100, 900)
        
        # PENCERE VE UYGULAMA İKONU
        self.setWindowIcon(QIcon("simge.ico"))
        
        self.temp_dir = tempfile.mkdtemp(prefix="wwiseforge_")
        self.settings = QSettings("WwiseForge", "WwiseForge")
        
        self.apk_work_dir = None
        self.current_apk_dummy = 0
        self.apk_source_path = None 
        
        self.current_playing_id = None
        self.is_slider_dragged = False
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)
        
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- Üst Panel: Dosya İşlemleri ---
        top_group = QGroupBox("Dosya İşlemleri")
        top_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("Dosya Ekle (BNK/APK)")
        self.btn_load.clicked.connect(self.load_bnk_files)
        
        self.btn_clear_list = QPushButton("Temizle")
        self.btn_clear_list.clicked.connect(self.clear_list)
        
        self.btn_restore = QPushButton("Orijinalleri Geri Yükle")
        self.btn_restore.clicked.connect(self.restore_original)
        self.btn_restore.setEnabled(False)
        
        self.btn_save = QPushButton("BNK Kaydet")
        self.btn_save.clicked.connect(self.save_selected_bnk)
        self.btn_save.setEnabled(False)
        
        self.btn_save_apk = QPushButton("APK Kaydet")
        self.btn_save_apk.setStyleSheet("background-color: #E1BEE7; font-weight: bold;")
        self.btn_save_apk.clicked.connect(self.save_as_apk)
        self.btn_save_apk.setEnabled(False)

        self.btn_settings = QPushButton("Ayarlar")
        self.btn_settings.clicked.connect(self.open_settings)
        
        top_layout.addWidget(self.btn_load)
        top_layout.addWidget(self.btn_clear_list)
        top_layout.addWidget(self.btn_restore)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_settings)
        top_layout.addWidget(self.btn_save)
        top_layout.addWidget(self.btn_save_apk)
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # --- Orta Panel: Filtreleme ve ağaç görünümü ---
        mid_layout = QVBoxLayout()
        
        # Gelişmiş filtre (Tümü seçeneği kaldırıldı)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtre:"))
        
        self.combo_filter_type = QComboBox()
        self.combo_filter_type.addItems([
            "Kimlik İçinde Ara (Ondalık)", 
            "Onaltılık Kimlik İçinde Ara", 
            "Sadece Değişenler", 
            "Sadece Orijinaller", 
            "Boyuta Göre Filtrele"
        ])
        self.combo_filter_type.currentIndexChanged.connect(self.on_filter_type_changed)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Kimlik girin (Örnek: 12345)...") # Varsayılan
        self.txt_search.textChanged.connect(self.filter_tree)
        
        filter_layout.addWidget(self.combo_filter_type)
        filter_layout.addWidget(self.txt_search)
        mid_layout.addLayout(filter_layout)
        
        # Ağaç görünümü
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Dosya / Kimlik", "Boyut", "Durum"])
        self.tree_widget.setColumnWidth(0, 400)
        self.tree_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.itemDoubleClicked.connect(self.play_audio)
        self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.open_context_menu)
        self.tree_widget.setSortingEnabled(True)

        mid_layout.addWidget(self.tree_widget)
        main_layout.addLayout(mid_layout)

        # --- Alt Panel: Gelişmiş oynatıcı ---
        player_group = QGroupBox("Önizleme")
        player_layout = QVBoxLayout()
        
        slider_layout = QHBoxLayout()
        self.lbl_current_time = QLabel("00:00")
        self.lbl_total_time = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        slider_layout.addWidget(self.lbl_current_time)
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.lbl_total_time)
        player_layout.addLayout(slider_layout)
        
        btns_layout = QHBoxLayout()
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_play.clicked.connect(self.play_audio)
        self.btn_play.setEnabled(False)
        self.btn_pause = QPushButton()
        self.btn_pause.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.btn_pause.clicked.connect(self.pause_audio)
        self.btn_pause.setEnabled(False)
        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.btn_stop.clicked.connect(self.stop_audio)
        self.btn_stop.setEnabled(False)
        
        btns_layout.addStretch()
        btns_layout.addWidget(self.btn_play)
        btns_layout.addWidget(self.btn_pause)
        btns_layout.addWidget(self.btn_stop)
        btns_layout.addStretch()
        player_layout.addLayout(btns_layout)
        main_layout.addWidget(player_group)

        # --- En Alt: İşlemler ---
        action_group = QGroupBox("Toplu İşlemler")
        action_layout = QHBoxLayout()
        
        self.btn_replace_single = QPushButton("Seçili WEM'i Değiştir")
        self.btn_replace_single.setStyleSheet("background-color: #BBDEFB; color: black; font-weight: bold;")
        self.btn_replace_single.clicked.connect(self.replace_single_wem)
        self.btn_replace_single.setEnabled(False)
        
        self.btn_batch_replace = QPushButton("Tüm BNK'lerde Toplu Değiştir")
        self.btn_batch_replace.setStyleSheet("background-color: #C8E6C9; color: black; font-weight: bold;")
        self.btn_batch_replace.clicked.connect(self.batch_replace_wems)
        
        self.btn_cue_transfer = QPushButton("Seçili BNK -> CUE Aktarımı")
        self.btn_cue_transfer.setStyleSheet("background-color: #FFECB3; color: black; font-weight: bold;")
        self.btn_cue_transfer.clicked.connect(self.batch_transfer_cue_data)
        self.btn_cue_transfer.setEnabled(False)
        
        action_layout.addWidget(self.btn_replace_single)
        action_layout.addWidget(self.btn_batch_replace)
        action_layout.addWidget(self.btn_cue_transfer)
        action_group.setLayout(action_layout)
        main_layout.addWidget(action_group)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Hazır")

    # -----------------------------------------------------------------------
    # YEDEKLEME ve FİLTRE MANTIĞI
    # -----------------------------------------------------------------------

    def create_backup(self, filepath):
        """Orijinal dosyanın yedeğini alt klasöre oluşturur ve temizler."""
        try:
            folder = os.path.dirname(filepath)
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

            # Zaman damgasıyla yedekle
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{filename}_{timestamp}"
            backup_path = os.path.join(file_backup_dir, backup_name)
            
            shutil.copy2(filepath, backup_path)
            print(f"Yedek alındı: {backup_path}")
            
            # TEMİZLİK
            self.clean_backups(file_backup_dir)
            
        except Exception as e:
            print(f"Yedekleme hatası: {e}")

    def clean_backups(self, backup_dir):
        """Yedekleri sayı ve tarih limitine göre temizler."""
        try:
            max_count = int(self.settings.value("yedek_sayisi", 3))
            max_age_days = int(self.settings.value("yedek_yasi", 7))
            
            files = []
            for f in os.listdir(backup_dir):
                full_path = os.path.join(backup_dir, f)
                if os.path.isfile(full_path):
                    files.append(full_path)
            
            # Tarihe göre sırala (En yeni en başta)
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            now = time.time()
            keep_files = []
            
            # 1. Tarih Kontrolü
            for f in files:
                mtime = os.path.getmtime(f)
                age_days = (now - mtime) / (24 * 3600)
                if age_days > max_age_days:
                    os.remove(f)
                    print(f"Eski yedek silindi: {f}")
                else:
                    keep_files.append(f)
            
            # 2. Sayı Kontrolü
            if len(keep_files) > max_count:
                # En yenileri tut, eskileri sil
                to_delete = keep_files[max_count:]
                for f in to_delete:
                    os.remove(f)
                    print(f"Fazla yedek silindi: {f}")
                    
        except Exception as e:
            print(f"Yedek temizleme hatası: {e}")

    def restore_original(self):
        """Seçili dosyanın en eski yedeğini geri yükler."""
        target_file = None
        items = self.tree_widget.selectedItems()
        if self.apk_source_path:
            target_file = self.apk_source_path
        elif items:
            item = items[0]
            while item.parent(): item = item.parent()
            parser = item.data(0, Qt.UserRole)
            if parser: target_file = parser.filepath

        if not target_file:
            QMessageBox.warning(self, "Uyarı", "Geri yüklenecek dosya belirlenemedi.")
            return

        folder = os.path.dirname(target_file)
        filename_stem = Path(target_file).stem
        # Alt klasörden bul
        backup_dir = os.path.join(folder, ".yedek", f"{filename_stem}_backups")

        if not os.path.exists(backup_dir) or not os.listdir(backup_dir):
            QMessageBox.warning(self, "Hata", "Bu dosya için yedek bulunamadı.")
            return

        # En eski yedeği bul (Orijinal kabul ediyoruz)
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)]
        files.sort(key=lambda x: os.path.getmtime(x)) # En eski en başta
        original_backup = files[0]

        reply = QMessageBox.question(self, "Onay", f"{os.path.basename(target_file)} orijinal haline döndürülecek.\n(Kaynak: {os.path.basename(original_backup)})\nOnaylıyor musunuz?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.stop_audio()
                self.media_player.setSource(QUrl())
                
                shutil.copy2(original_backup, target_file)
                QMessageBox.information(self, "Başarılı", "Dosya geri yüklendi. Liste yenileniyor...")
                
                self.clear_list()
                if target_file.lower().endswith(".apk"):
                    self.process_apk(target_file)
                else:
                    self.process_bnk(target_file)
                    
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Geri yükleme başarısız:\n{str(e)}")

    def on_filter_type_changed(self, index):
        txt = self.combo_filter_type.currentText()
        # Yer tutucu metni güncelle
        if "Kimlik" in txt and "Onaltılık" not in txt:
            self.txt_search.setPlaceholderText("Kimlik girin (Örnek: 12345)...")
        elif "Onaltılık" in txt:
            self.txt_search.setPlaceholderText("Onaltılık kimlik girin (Örnek: 3F2A)...")
        elif "Boyut" in txt:
            self.txt_search.setPlaceholderText("Örn: >500KB, <2MB, =100B")
        else:
            self.txt_search.setPlaceholderText("Filtrelemek için yazın...")
        self.filter_tree(self.txt_search.text())

    def parse_size_filter(self, text):
        text = text.upper().replace(" ", "")
        match = re.match(r"([<>=]+)(\d+)([KMG]?B?)", text)
        if not match: return None
        
        op, val, unit = match.groups()
        val = float(val)
        multiplier = 1
        if "K" in unit: multiplier = 1024
        elif "M" in unit: multiplier = 1024**2
        elif "G" in unit: multiplier = 1024**3
        
        limit_bytes = val * multiplier
        return op, limit_bytes

    def filter_tree(self, text):
        # Dizin eşlemesi: 
        # 0: Kimlik (Ondalık) [Tümü seçeneğinin yerine]
        # 1: Onaltılık kimlik
        # 2: Değişen
        # 3: Orijinal
        # 4: Boyut
        
        filter_type = self.combo_filter_type.currentIndex() 
        search_text = text.strip()
        
        root_count = self.tree_widget.topLevelItemCount()
        
        for i in range(root_count):
            root = self.tree_widget.topLevelItem(i)
            child_count = root.childCount()
            visible_children = 0
            
            for j in range(child_count):
                child = root.child(j)
                entry = child.data(0, Qt.UserRole)
                show = False
                
                if filter_type == 0: # Ondalık kimlik (önceden Tümü)
                    if not search_text: show = True # Boşsa hepsini göster
                    elif search_text in str(entry.wem_id): show = True
                elif filter_type == 1: # Onaltılık kimlik
                    hex_id = f"{entry.wem_id:X}"
                    if not search_text: show = True
                    elif search_text.upper() in hex_id: show = True
                elif filter_type == 2: # Değişen
                    show = entry.modified
                elif filter_type == 3: # Orijinal
                    show = not entry.modified
                elif filter_type == 4: # Boyut
                    if not search_text: show = True
                    else:
                        res = self.parse_size_filter(search_text)
                        if res:
                            op, limit = res
                            if op == ">" and entry.size > limit: show = True
                            elif op == "<" and entry.size < limit: show = True
                            elif op == "=" and entry.size == limit: show = True
                            elif op == ">=" and entry.size >= limit: show = True
                            elif op == "<=" and entry.size <= limit: show = True
                
                child.setHidden(not show)
                if show: visible_children += 1
            
            if visible_children > 0:
                root.setHidden(False)
                root.setExpanded(True)
            else:
                # Kimlik arama kipinde alan boşken kök öğe görünsün
                if filter_type == 0 and not search_text:
                    root.setHidden(False)
                    root.setExpanded(False)
                else:
                    root.setHidden(True)

    # -----------------------------------------------------------------------
    # TEMEL İŞLEVLER
    # -----------------------------------------------------------------------

    def open_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if not item: return
        
        if item.parent():
            menu = QMenu()
            action_hex = QAction("Onaltılık Düzenleyici ile Aç", self)
            action_hex.triggered.connect(lambda: self.open_hex_editor(item))
            menu.addAction(action_hex)
            
            action_export = QAction("WAV Olarak Dışa Aktar", self)
            action_export.triggered.connect(self.export_wav)
            menu.addAction(action_export)
            
            menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def export_wav(self):
        selected_items = self.tree_widget.selectedItems()
        wem_items = [i for i in selected_items if i.parent() is not None]
        if not wem_items: return
        
        vgm_path = self.settings.value("vgmstream_yolu")
        if not vgm_path or not os.path.exists(vgm_path):
            QMessageBox.warning(self, "Hata", "VGMStream yolu ayarlanmamış!")
            return

        save_dir = QFileDialog.getExistingDirectory(self, "Dışa Aktarılacak Klasörü Seç")
        if not save_dir: return
        
        success_count = 0
        error_count = 0
        
        for item in wem_items:
            entry = item.data(0, Qt.UserRole)
            temp_wem = os.path.join(self.temp_dir, f"disa_aktarilan_{entry.wem_id}.wem")
            out_wav = os.path.join(save_dir, f"{entry.wem_id}.wav")
            try:
                with open(temp_wem, 'wb') as f: f.write(entry.data)
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                cmd = [vgm_path, "-o", out_wav, temp_wem]
                res = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
                if res.returncode == 0 and os.path.exists(out_wav): success_count += 1
                else: error_count += 1
                if os.path.exists(temp_wem): os.remove(temp_wem)
            except: error_count += 1
        
        QMessageBox.information(self, "Dışa Aktarma", f"Tamamlandı.\nBaşarılı: {success_count}\nHatalı: {error_count}")

    def open_hex_editor(self, item):
        entry = item.data(0, Qt.UserRole)
        if not entry: return
        dialog = HexEditorDialog(entry, self)
        if dialog.exec():
            if dialog.new_data:
                parent_item = item.parent()
                parser = parent_item.data(0, Qt.UserRole)
                parser.replace_wem(entry.wem_id, dialog.new_data)
                self.update_child_visuals(item, entry)
                parent_item.setText(2, "Değişiklik var")
                wav_path = os.path.join(self.temp_dir, f"{entry.wem_id}.wav")
                if os.path.exists(wav_path):
                    try: os.remove(wav_path)
                    except: pass
                self.status_bar.showMessage(f"Kimlik {entry.wem_id} Onaltılık Düzenleyici ile güncellendi.")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def clear_list(self):
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

    def load_bnk_files(self):
        filter_str = "Wwise Dosyaları (*.bnk *.apk);;Wwise Ses Bankası (*.bnk);;APK Kapsayıcısı (*.apk)"
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Dosya Ekle", "", filter_str)
        if not filepaths: return

        loaded_count = 0
        error_count = 0
        
        for filepath in filepaths:
            try:
                self.create_backup(filepath)
                if filepath.lower().endswith(".apk"):
                    self.process_apk(filepath)
                    loaded_count += 1
                else:
                    self.process_bnk(filepath)
                    loaded_count += 1
            except Exception as e:
                print(f"Hata ({filepath}): {e}")
                error_count += 1
        
        if loaded_count > 0:
            self.btn_restore.setEnabled(True)
        self.status_bar.showMessage(f"{loaded_count} dosya eklendi. {error_count} hata.")

    def process_bnk(self, filepath):
        parser = BnkParser(filepath)
        parser.load_bnk(filepath)
        self.add_bnk_to_tree(parser)

    def process_apk(self, filepath):
        apk_name = os.path.basename(filepath)
        extract_path = os.path.join(self.temp_dir, f"{apk_name}_extracted")
        extracted_bnks, dummy = ApkExtractor.extract_bnks_from_apk(filepath, extract_path)
        
        self.apk_work_dir = extract_path
        self.current_apk_dummy = dummy
        self.apk_source_path = filepath 
        self.btn_save_apk.setEnabled(True)
        
        for bnk_path in extracted_bnks:
            try: self.process_bnk(bnk_path)
            except: pass

    def add_bnk_to_tree(self, parser: BnkParser):
        root = QTreeWidgetItem(self.tree_widget)
        root.setText(0, parser.filename)
        root.setText(1, f"{len(parser.wem_list)} Dosya")
        root.setText(2, "Orijinal")
        root.setData(0, Qt.UserRole, parser)
        font = root.font(0)
        font.setBold(True)
        root.setFont(0, font)
        for entry in parser.wem_list:
            child = QTreeWidgetItem(root)
            self.update_child_visuals(child, entry)
            child.setData(0, Qt.UserRole, entry)
        root.setExpanded(False)

    def update_child_visuals(self, item: QTreeWidgetItem, entry: WemEntry):
        item.setText(0, str(entry.wem_id))
        if entry.size < 1024 * 1024: size_str = f"{entry.size / 1024:.2f} KB"
        else: size_str = f"{entry.size / (1024 * 1024):.2f} MB"
        item.setText(1, size_str)
        if entry.modified:
            item.setText(2, "Değiştirildi")
            for col in range(3):
                item.setBackground(col, QColor("#C8E6C9"))
                item.setForeground(col, QColor(Qt.black))
        else:
            item.setText(2, "Orijinal")
            for col in range(3):
                item.setBackground(col, QBrush()) 
                item.setForeground(col, QBrush())

    def on_selection_changed(self):
        items = self.tree_widget.selectedItems()
        if not items:
            self.set_controls_enabled(False)
            self.btn_save.setEnabled(False)
            self.btn_cue_transfer.setEnabled(False)
            self.btn_save.setText("Seçili BNK'yı Kaydet")
            return
        
        selected_roots = [i for i in items if i.parent() is None]
        if len(selected_roots) > 0:
            self.btn_cue_transfer.setEnabled(True)
            self.set_controls_enabled(False)
            if len(selected_roots) == 1:
                self.btn_save.setEnabled(True)
                self.btn_save.setText(f"'{selected_roots[0].text(0)}' Kaydet")
            else:
                self.btn_save.setEnabled(False) 
                self.btn_save.setText("Seçili BNK'yı Kaydet")
        elif len(items) == 1 and items[0].parent() is not None:
            item = items[0]
            parent = item.parent()
            self.set_controls_enabled(True)
            self.btn_save.setEnabled(True)
            self.btn_cue_transfer.setEnabled(False)
            self.btn_save.setText(f"'{parent.text(0)}' Kaydet")
        else:
            self.set_controls_enabled(False)
            self.btn_save.setEnabled(False)
            self.btn_cue_transfer.setEnabled(False)

    def set_controls_enabled(self, enabled: bool):
        self.btn_play.setEnabled(enabled)
        self.btn_pause.setEnabled(enabled)
        self.btn_stop.setEnabled(enabled)
        self.btn_replace_single.setEnabled(enabled)

    # -----------------------------------------------------------------------
    # OYNATICI VE DÖNÜŞTÜRME
    # -----------------------------------------------------------------------

    def convert_and_load_audio(self, entry: WemEntry) -> bool:
        vgm_path = self.settings.value("vgmstream_yolu")
        if not vgm_path or not os.path.exists(vgm_path):
            QMessageBox.warning(self, "Eksik Ayar", "Lütfen Ayarlar menüsünden 'vgmstream-cli' yolunu seçin.")
            return False
        temp_wem = os.path.join(self.temp_dir, f"{entry.wem_id}.wem")
        temp_wav = os.path.join(self.temp_dir, f"{entry.wem_id}.wav")
        if os.path.exists(temp_wav):
             self.media_player.setSource(QUrl.fromLocalFile(temp_wav))
             return True
        try:
            with open(temp_wem, 'wb') as f: f.write(entry.data)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = [vgm_path, "-o", temp_wav, temp_wem]
            result = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
            if os.path.exists(temp_wem): 
                try: os.remove(temp_wem)
                except: pass
            if result.returncode != 0:
                self.status_bar.showMessage("Ses çözme hatası (VGMStream)")
                return False
            if os.path.exists(temp_wav):
                self.media_player.setSource(QUrl.fromLocalFile(temp_wav))
                return True
            else: return False
        except Exception as e:
            print(f"Hata: {e}")
            return False

    def get_selected_wem_entry_and_item(self):
        items = self.tree_widget.selectedItems()
        if not items: return None, None
        item = items[0]
        if item.parent() is None: return None, None
        entry = item.data(0, Qt.UserRole)
        return entry, item

    def play_audio(self):
        if self.media_player.playbackState() == QMediaPlayer.PausedState:
            self.media_player.play()
            return
        entry, item = self.get_selected_wem_entry_and_item()
        if not entry: return
        if self.current_playing_id == entry.wem_id and self.media_player.source().isValid():
            self.media_player.play()
            return
        self.stop_audio()
        if self.convert_and_load_audio(entry):
            self.current_playing_id = entry.wem_id
            self.media_player.play()
            self.status_bar.showMessage(f"Çalınıyor: {entry.wem_id}")
        else: self.status_bar.showMessage("Dosya oynatılamadı.")

    def pause_audio(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.status_bar.showMessage("Duraklatıldı.")

    def stop_audio(self):
        self.media_player.stop()
        self.status_bar.showMessage("Durduruldu.")
        self.slider.setValue(0)
        self.lbl_current_time.setText("00:00")

    def update_position(self, position):
        if not self.is_slider_dragged: self.slider.setValue(position)
        m = (position // 60000)
        s = (position // 1000) % 60
        self.lbl_current_time.setText(f"{m:02}:{s:02}")

    def update_duration(self, duration):
        self.slider.setRange(0, duration)
        m = (duration // 60000)
        s = (duration // 1000) % 60
        self.lbl_total_time.setText(f"{m:02}:{s:02}")

    def on_slider_pressed(self): self.is_slider_dragged = True
    def on_slider_released(self):
        self.is_slider_dragged = False
        self.media_player.setPosition(self.slider.value())
    def on_slider_moved(self, position):
        m = (position // 60000)
        s = (position // 1000) % 60
        self.lbl_current_time.setText(f"{m:02}:{s:02}")
    def media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.slider.setValue(0)

    # -----------------------------------------------------------------------
    # İŞLEMLER
    # -----------------------------------------------------------------------

    def replace_single_wem(self):
        entry, item = self.get_selected_wem_entry_and_item()
        if not entry: return
        parent_item = item.parent()
        parser = parent_item.data(0, Qt.UserRole)
        filepath, _ = QFileDialog.getOpenFileName(self, "Yeni .wem Seç", "", "WEM (*.wem);;Tüm dosyalar (*)")
        if not filepath: return
        try:
            with open(filepath, 'rb') as f: new_data = f.read()
            parser.replace_wem(entry.wem_id, new_data)
            self.update_child_visuals(item, entry)
            parent_item.setText(2, "Değişiklik var")
            if self.current_playing_id == entry.wem_id:
                self.stop_audio()
                wav_path = os.path.join(self.temp_dir, f"{entry.wem_id}.wav")
                if os.path.exists(wav_path): os.remove(wav_path)
            self.status_bar.showMessage(f"Kimlik {entry.wem_id} değiştirildi.")
        except Exception as e: QMessageBox.critical(self, "Hata", str(e))

    def batch_replace_wems(self):
        if self.tree_widget.topLevelItemCount() == 0:
            QMessageBox.warning(self, "Uyarı", "Listede BNK yok.")
            return
        folder_path = QFileDialog.getExistingDirectory(self, "WEM Klasörü Seç")
        if not folder_path: return
        folder_files = os.listdir(folder_path)
        wem_files = {f: os.path.join(folder_path, f) for f in folder_files if f.lower().endswith('.wem')}
        
        total_success = 0
        total_bnks_touched = 0
        
        root_count = self.tree_widget.topLevelItemCount()
        for i in range(root_count):
            root_item = self.tree_widget.topLevelItem(i)
            parser = root_item.data(0, Qt.UserRole)
            bnk_modified = False
            child_count = root_item.childCount()
            for j in range(child_count):
                child_item = root_item.child(j)
                entry = child_item.data(0, Qt.UserRole)
                target_filename = f"{entry.wem_id}.wem"
                if target_filename in wem_files:
                    try:
                        with open(wem_files[target_filename], 'rb') as f: new_data = f.read()
                        if parser.replace_wem(entry.wem_id, new_data):
                            self.update_child_visuals(child_item, entry)
                            total_success += 1
                            bnk_modified = True
                            wav_path = os.path.join(self.temp_dir, f"{entry.wem_id}.wav")
                            if os.path.exists(wav_path): 
                                try: os.remove(wav_path)
                                except: pass
                    except: pass
            if bnk_modified:
                total_bnks_touched += 1
                root_item.setText(2, "Değişiklik var")
        self.stop_audio()
        QMessageBox.information(self, "Sonuç", f"Değişen: {total_success}\nEtkilenen BNK: {total_bnks_touched}")

    def batch_transfer_cue_data(self):
        selected_items = self.tree_widget.selectedItems()
        root_items = [item for item in selected_items if item.parent() is None]
        if not root_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir BNK seçin.")
            return
        target_path = QFileDialog.getExistingDirectory(self, "Türkçe WEM Klasörü")
        if not target_path: return

        CUE_MARKER = b'cue '
        DATA_MARKER = b'data'
        log_lines = []
        total_success = 0
        
        for root_item in root_items:
            parser = root_item.data(0, Qt.UserRole)
            log_lines.append(f"BNK: {parser.filename}")
            for entry in parser.wem_list:
                # Değişiklik: Artık BNK'nın kendi ikili verisi değil,
                # WEM girdisinin kendi ikili verisi kullanılıyor.
                orig_content = entry.data
                
                # Türkçe klasörde bu kimlikle dosya var mı?
                target_file = os.path.join(target_path, f"{entry.wem_id}.wem")
                if not os.path.exists(target_file): continue
                
                try:
                    # 1. Orijinal veride CUE ve DATA bul
                    cue_start = orig_content.find(CUE_MARKER)
                    data_start_orig = orig_content.rfind(DATA_MARKER)
                    
                    if cue_start == -1 or data_start_orig == -1: 
                        log_lines.append(f"  [ATLANDI] Orijinalde CUE/DATA yok: Kimlik {entry.wem_id}")
                        continue
                    
                    copy_chunk = orig_content[cue_start : data_start_orig + len(DATA_MARKER)]
                    
                    # 2. Hedef dosyayı oku
                    with open(target_file, 'rb') as f: target_content = f.read()
                    
                    if CUE_MARKER in target_content: 
                        log_lines.append(f"  [BİLGİ] Hedefte zaten CUE var: Kimlik {entry.wem_id}")
                        continue
                        
                    data_start_target = target_content.find(DATA_MARKER)
                    if data_start_target == -1: 
                        log_lines.append(f"  [UYARI] Hedef dosyada DATA yok: Kimlik {entry.wem_id}")
                        continue
                    
                    # 3. Veriyi ekle
                    new_content = target_content[:data_start_target] + copy_chunk + target_content[data_start_target + len(DATA_MARKER):]
                    
                    with open(target_file, 'wb') as f: f.write(new_content)
                    
                    total_success += 1
                    log_lines.append(f"  + Güncellendi: {entry.wem_id}.wem")
                    
                except Exception as e:
                    log_lines.append(f"  ! Kimlik {entry.wem_id} için hata: {e}")
        
        log_lines.append(f"\nToplam Güncellenen: {total_success}")
        d = LogResultDialog("Aktarım Sonucu", "\n".join(log_lines), self)
        d.exec()

    def save_selected_bnk(self):
        items = self.tree_widget.selectedItems()
        if not items: return
        item = items[0]
        if item.parent(): root_item = item.parent()
        else: root_item = item
        parser = root_item.data(0, Qt.UserRole)
        save_path, _ = QFileDialog.getSaveFileName(self, "BNK Kaydet", f"duzenlenmis_{parser.filename}", "Wwise Ses Bankası (*.bnk)")
        if save_path:
            try:
                parser.save_bnk(save_path)
                QMessageBox.information(self, "Başarılı", "Kaydedildi.")
            except Exception as e: QMessageBox.critical(self, "Hata", str(e))

    def save_as_apk(self):
        if not self.apk_work_dir or not os.path.exists(self.apk_work_dir):
            QMessageBox.warning(self, "Hata", "APK çalışma klasörü yok!")
            return
        
        # Son hâllerini geçici klasöre yaz
        root_count = self.tree_widget.topLevelItemCount()
        for i in range(root_count):
            item = self.tree_widget.topLevelItem(i)
            parser = item.data(0, Qt.UserRole)
            if self.apk_work_dir in os.path.abspath(parser.filepath):
                try: parser.save_bnk(parser.filepath)
                except: pass

        out_path, _ = QFileDialog.getSaveFileName(self, "APK Kaydet", "duzenlenmis.apk", "APK (*.apk)")
        if out_path:
            try:
                count, _ = ApkExtractor.repack_from_folder(self.apk_work_dir, out_path, self.current_apk_dummy)
                QMessageBox.information(self, "Başarılı", f"APK oluşturuldu! ({count} dosya)")
            except Exception as e: QMessageBox.critical(self, "Hata", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon("simge.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())