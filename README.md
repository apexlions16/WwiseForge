# WwiseForge

WwiseForge; Wwise ses bankalarını incelemek, içerdikleri WEM dosyalarını önizlemek ve değiştirmek, özel APK kapsayıcılarını açmak ve yeniden paketlemek için geliştirilen masaüstü uygulamasıdır.

Uygulama Python ve PySide6 kullanılarak geliştirilmektedir. Ses çözme ve WAV dışa aktarma işlemleri için VGMStream komut satırı aracı kullanılır.

## Mevcut özellikler

- Bir veya birden fazla BNK dosyasını açma
- Özel APK kapsayıcılarındaki BNK dosyalarını çıkarma
- APK içeriğini yeniden paketleme
- BNK içindeki WEM kayıtlarını listeleme
- Ondalık veya onaltılık kimliğe göre arama
- Değiştirilen ve özgün kayıtları filtreleme
- Dosya boyutuna göre filtreleme
- Tek bir WEM kaydını değiştirme
- Bir klasördeki WEM dosyalarıyla toplu değiştirme
- VGMStream aracılığıyla ses önizleme
- Seçili kayıtları WAV biçiminde dışa aktarma
- WEM verisini onaltılık düzenleyiciyle görüntüleme ve değiştirme
- CUE verisini eşleşen WEM dosyalarına aktarma
- Tarih ve sayı sınırıyla otomatik yedekleme
- Yedekten özgün dosyayı geri yükleme

## Gereksinimler

- Python 3.10 veya daha yeni bir sürüm
- PySide6
- Ses önizleme ve WAV dışa aktarma için VGMStream komut satırı aracı
- Tek dosyalık çalıştırılabilir çıktı oluşturmak için isteğe bağlı olarak PyInstaller

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install PySide6
python WwiseForge.py
```

VGMStream aracının yolu uygulama içindeki **Ayarlar** penceresinden seçilmelidir.

## Çalıştırılabilir dosya oluşturma

Önce PyInstaller kurulmalıdır:

```powershell
python -m pip install pyinstaller
```

Ardından aşağıdaki komut kullanılabilir:

```powershell
pyinstaller --noconsole --onefile --icon=simge.ico WwiseForge.py
```

`simge.ico` dosyası proje klasöründe bulunmalıdır.

## Yedekleme

Bir BNK veya APK dosyası açıldığında, dosyanın bulunduğu klasörde gizli `.yedek` klasörü oluşturulur. Yedeklerin en fazla kaç adet tutulacağı ve kaç günlük yedeklerin korunacağı **Ayarlar** penceresinden değiştirilebilir.

## Geliştirme düzeni

Bu proje GitHub üzerinden geliştirilecektir.

- Yeni bir özellik veya kapsam değişikliği önce görüşülecektir.
- Üzerinde anlaşmaya varılan çalışma, planlanan aşama olarak bu dosyaya eklenecektir.
- Aşamalar sırayla ve ayrı güncellemeler hâlinde uygulanacaktır.
- Commit mesajları, açıklamalar, hata metinleri, kullanıcı arayüzü yazıları ve geliştirici notları Türkçe olacaktır.
- Teknik zorunluluklar dışında proje tarafından yazılan insan okunabilir metinlerde İngilizce kullanılmayacaktır.

## Planlanan aşamalar

Henüz üzerinde anlaşmaya varılmış yeni bir geliştirme aşaması yoktur. Yeni aşamalar görüşülüp onaylandıktan sonra bu bölüme eklenecektir.

## Proje durumu

Proje erken geliştirme aşamasındadır. Özellikler ve dosya biçimi işlemleri gerçek dosyaların yedekleri üzerinde denenmelidir.

## Lisans

Proje için henüz bir lisans belirlenmemiştir.
