from pathlib import Path

SURUM = "0.1.0"
KAYNAK_DOSYASI = Path("WwiseForge.py")
OKUBENI_DOSYASI = Path("README.md")


def zorunlu_degistir(metin: str, eski: str, yeni: str) -> str:
    if eski not in metin:
        raise RuntimeError(f"Beklenen metin bulunamadı: {eski}")
    return metin.replace(eski, yeni, 1)


kaynak = KAYNAK_DOSYASI.read_text(encoding="utf-8")

if "UYGULAMA_SURUMU" not in kaynak:
    kaynak = zorunlu_degistir(
        kaynak,
        "from PySide6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QTextCursor\n",
        "from PySide6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QTextCursor\n\n"
        "UYGULAMA_ADI = \"WwiseForge\"\n"
        f"UYGULAMA_SURUMU = \"{SURUM}\"\n",
    )

kaynak = kaynak.replace(
    '# pyinstaller --noconsole --onefile --icon=simge.ico "WwiseForge.py"',
    f'# python -m PyInstaller --noconfirm --clean --onefile --windowed --name "WwiseForge-v{SURUM}" "WwiseForge.py"',
)
kaynak = kaynak.replace(
    '# (Not: "simge.ico" dosyasının proje klasöründe olduğundan emin olun.)',
    '# İsteğe bağlı uygulama simgesi için "simge.ico" proje klasörüne eklenebilir.',
)
kaynak = zorunlu_degistir(
    kaynak,
    'self.setWindowTitle("WwiseForge - Çoklu BNK/APK Düzenleyici")',
    'self.setWindowTitle(f"{UYGULAMA_ADI} v{UYGULAMA_SURUMU} - Çoklu BNK/APK Düzenleyici")',
)
kaynak = zorunlu_degistir(
    kaynak,
    'self.status_bar.showMessage("Hazır")',
    'self.status_bar.showMessage(f"Hazır — Sürüm {UYGULAMA_SURUMU}")',
)
if "app.setApplicationVersion" not in kaynak:
    kaynak = zorunlu_degistir(
        kaynak,
        '    app = QApplication(sys.argv)\n    app.setStyle("Fusion")',
        '    app = QApplication(sys.argv)\n'
        '    app.setApplicationName(UYGULAMA_ADI)\n'
        '    app.setApplicationVersion(UYGULAMA_SURUMU)\n'
        '    app.setStyle("Fusion")',
    )

KAYNAK_DOSYASI.write_text(kaynak, encoding="utf-8", newline="\n")

okubeni = '# WwiseForge\n\nWwiseForge; Wwise ses bankalarını incelemek, içerdikleri WEM dosyalarını önizlemek ve değiştirmek, özel APK kapsayıcılarını açmak ve yeniden paketlemek için geliştirilen masaüstü uygulamasıdır.\n\nUygulama Python ve PySide6 kullanılarak geliştirilmektedir. Ses çözme ve WAV dışa aktarma işlemleri için VGMStream komut satırı aracı kullanılır.\n\n## Güncel sürüm\n\n**v0.1.0 — İlk test sürümü**\n\nBu sürüm, Windows çalıştırılabilir dosyasıyla düzenli kullanıcı testlerinin başlatılması için hazırlanan ilk sürümdür. Uygulamanın sürüm numarası pencere başlığında ve durum çubuğunda gösterilir.\n\n## Mevcut özellikler\n\n- Bir veya birden fazla BNK dosyasını açma\n- Özel APK kapsayıcılarındaki BNK dosyalarını çıkarma\n- APK içeriğini yeniden paketleme\n- BNK içindeki WEM kayıtlarını listeleme\n- Ondalık veya onaltılık kimliğe göre arama\n- Değiştirilen ve özgün kayıtları filtreleme\n- Dosya boyutuna göre filtreleme\n- Tek bir WEM kaydını değiştirme\n- Bir klasördeki WEM dosyalarıyla toplu değiştirme\n- VGMStream aracılığıyla ses önizleme\n- Seçili kayıtları WAV biçiminde dışa aktarma\n- WEM verisini onaltılık düzenleyiciyle görüntüleme ve değiştirme\n- CUE verisini eşleşen WEM dosyalarına aktarma\n- Tarih ve sayı sınırıyla otomatik yedekleme\n- Yedekten özgün dosyayı geri yükleme\n\n## Windows test sürümü\n\nYeni güncellemeler tamamlandığında GitHub **Sürümler** bölümünde Windows için tek dosyalık çalıştırılabilir çıktı yayımlanır.\n\nYayıma elle eklenen dosyanın adı sürüm numarasını içerir:\n\n```text\nWwiseForge-v0.1.0.exe\n```\n\nGitHub, her sürüm için kaynak kod arşivlerini kendi sistemi tarafından ayrıca gösterebilir. Proje tarafından yayıma eklenen test dosyası yalnızca EXE dosyasıdır.\n\n## Gereksinimler\n\nKaynak koddan çalıştırmak için:\n\n- Python 3.10 veya daha yeni bir sürüm\n- PySide6\n- Ses önizleme ve WAV dışa aktarma için VGMStream komut satırı aracı\n- Tek dosyalık çalıştırılabilir çıktı oluşturmak için PyInstaller\n\nYayımlanan EXE dosyasını çalıştırmak için Python veya PySide6 kurulması gerekmez. Ses önizleme ve WAV dışa aktarma işlemlerinde VGMStream yolu uygulamadaki **Ayarlar** penceresinden seçilmelidir.\n\n## Kaynak koddan çalıştırma\n\n```powershell\npython -m venv .venv\n.venv\\Scripts\\activate\npython -m pip install PySide6\npython WwiseForge.py\n```\n\n## Çalıştırılabilir dosya oluşturma\n\nÖnce gerekli paketler kurulmalıdır:\n\n```powershell\npython -m pip install PySide6 PyInstaller\n```\n\nArdından aşağıdaki komut kullanılabilir:\n\n```powershell\npython -m PyInstaller --noconfirm --clean --onefile --windowed --name "WwiseForge-v0.1.0" WwiseForge.py\n```\n\nİsteğe bağlı bir uygulama simgesi kullanılacaksa `simge.ico` dosyası proje klasörüne eklenebilir.\n\n## Otomatik yayın düzeni\n\nGitHub Actions üzerinde çalışan Windows yayın düzeni şu adımları uygular:\n\n1. Kaynak kodu Windows ortamına alır.\n2. Python, PySide6 ve PyInstaller kurulumunu yapar.\n3. Python sözdizimi denetimini çalıştırır.\n4. Tek dosyalık Windows EXE çıktısını oluşturur.\n5. Türkçe sürüm notlarını hazırlar.\n6. Aynı sürüm daha önce yayımlanmamışsa yeni GitHub sürümünü oluşturur.\n7. Yayıma yalnızca sürümlü EXE dosyasını ekler.\n\nDerleme veya denetim adımlarından biri başarısız olursa sürüm yayımlanmaz.\n\n## Yedekleme\n\nBir BNK veya APK dosyası açıldığında, dosyanın bulunduğu klasörde gizli `.yedek` klasörü oluşturulur. Yedeklerin en fazla kaç adet tutulacağı ve kaç günlük yedeklerin korunacağı **Ayarlar** penceresinden değiştirilebilir.\n\n## Geliştirme düzeni\n\nBu proje GitHub üzerinden geliştirilecektir.\n\n- Yeni bir özellik veya kapsam değişikliği önce kullanıcıyla görüşülecektir.\n- Üzerinde anlaşmaya varılan her çalışma için ayrı bir issue açılacaktır.\n- Issue içinde kapsam, kabul ölçütleri ve test adımları yer alacaktır.\n- Geliştirme sırasında yapılan önemli değişiklikler issue yorumlarıyla kaydedilecektir.\n- Aşamalar sırayla ve ayrı güncellemeler hâlinde uygulanacaktır.\n- İşleme kayıtları, issue metinleri, sürüm notları, hata metinleri, kullanıcı arayüzü yazıları ve geliştirici notları Türkçe olacaktır.\n- Teknik zorunluluklar dışında proje tarafından yazılan insan okunabilir metinlerde İngilizce kullanılmayacaktır.\n- Kullanıcı yayımlanan EXE dosyasını onaylamadan sonraki geliştirme aşamasına geçilmeyecektir.\n- Onaylanmayan bir güncelleme, izlenebilir bir geri alma kaydıyla önceki çalışan sürüme döndürülecektir.\n\nKalıcı çalışma düzeni [Issue #1](https://github.com/apexlions16/WwiseForge/issues/1) içinde takip edilir.\n\n## Planlanan aşamalar\n\n### Aşama 0 — Sürümleme ve Windows EXE yayın altyapısı\n\nDurum: **Kullanıcı testi bekleniyor**\n\nTakip: [Issue #2](https://github.com/apexlions16/WwiseForge/issues/2)\n\nBu aşamada sürüm numarası, otomatik Windows derlemesi, Türkçe sürüm notları ve ilk test sürümü hazırlanmıştır.\n\nSonraki aşama, bu sürüm kullanıcı tarafından test edilip onaylandıktan sonra görüşülerek belirlenecektir.\n\n## Proje durumu\n\nProje erken geliştirme aşamasındadır. Özellikler ve dosya biçimi işlemleri gerçek dosyaların yedekleri üzerinde denenmelidir.\n\n## Lisans\n\nProje için henüz bir lisans belirlenmemiştir.\n'
OKUBENI_DOSYASI.write_text(okubeni, encoding="utf-8", newline="\n")

print(f"Aşama 0 kaynak güncellemesi uygulandı: v{SURUM}")