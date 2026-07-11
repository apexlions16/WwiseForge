# WwiseForge

WwiseForge; Wwise ses bankalarını incelemek, içerdikleri WEM dosyalarını önizlemek ve değiştirmek, özel APK kapsayıcılarını açmak ve yeniden paketlemek için geliştirilen masaüstü uygulamasıdır.

Uygulama Python ve PySide6 kullanılarak geliştirilmektedir. Ses çözme ve WAV dışa aktarma işlemleri için VGMStream komut satırı aracı kullanılır.

## Güncel sürüm

**v0.1.0 — İlk test sürümü**

Bu sürüm, Windows çalıştırılabilir dosyasıyla düzenli kullanıcı testlerinin başlatılması için hazırlanan ilk sürümdür. Uygulamanın sürüm numarası pencere başlığında ve durum çubuğunda gösterilir.

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

## Windows test sürümü

Yeni güncellemeler tamamlandığında GitHub **Sürümler** bölümünde Windows için tek dosyalık çalıştırılabilir çıktı yayımlanır.

Yayıma elle eklenen dosyanın adı sürüm numarasını içerir:

```text
WwiseForge-v0.1.0.exe
```

GitHub, her sürüm için kaynak kod arşivlerini kendi sistemi tarafından ayrıca gösterebilir. Proje tarafından yayıma eklenen test dosyası yalnızca EXE dosyasıdır.

## Gereksinimler

Kaynak koddan çalıştırmak için:

- Python 3.10 veya daha yeni bir sürüm
- PySide6
- Ses önizleme ve WAV dışa aktarma için VGMStream komut satırı aracı
- Tek dosyalık çalıştırılabilir çıktı oluşturmak için PyInstaller

Yayımlanan EXE dosyasını çalıştırmak için Python veya PySide6 kurulması gerekmez. Ses önizleme ve WAV dışa aktarma işlemlerinde VGMStream yolu uygulamadaki **Ayarlar** penceresinden seçilmelidir.

## Kaynak koddan çalıştırma

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install PySide6
python WwiseForge.py
```

## Çalıştırılabilir dosya oluşturma

Önce gerekli paketler kurulmalıdır:

```powershell
python -m pip install PySide6 PyInstaller
```

Ardından aşağıdaki komut kullanılabilir:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "WwiseForge-v0.1.0" WwiseForge.py
```

İsteğe bağlı bir uygulama simgesi kullanılacaksa `simge.ico` dosyası proje klasörüne eklenebilir.

## Otomatik yayın düzeni

GitHub Actions üzerinde çalışan Windows yayın düzeni şu adımları uygular:

1. Kaynak kodu Windows ortamına alır.
2. Python, PySide6 ve PyInstaller kurulumunu yapar.
3. Python sözdizimi denetimini çalıştırır.
4. Tek dosyalık Windows EXE çıktısını oluşturur.
5. Türkçe sürüm notlarını hazırlar.
6. Aynı sürüm daha önce yayımlanmamışsa yeni GitHub sürümünü oluşturur.
7. Yayıma yalnızca sürümlü EXE dosyasını ekler.

Derleme veya denetim adımlarından biri başarısız olursa sürüm yayımlanmaz.

## Yedekleme

Bir BNK veya APK dosyası açıldığında, dosyanın bulunduğu klasörde gizli `.yedek` klasörü oluşturulur. Yedeklerin en fazla kaç adet tutulacağı ve kaç günlük yedeklerin korunacağı **Ayarlar** penceresinden değiştirilebilir.

## Geliştirme düzeni

Bu proje GitHub üzerinden geliştirilecektir.

- Yeni bir özellik veya kapsam değişikliği önce kullanıcıyla görüşülecektir.
- Üzerinde anlaşmaya varılan her çalışma için ayrı bir issue açılacaktır.
- Issue içinde kapsam, kabul ölçütleri ve test adımları yer alacaktır.
- Geliştirme sırasında yapılan önemli değişiklikler issue yorumlarıyla kaydedilecektir.
- Aşamalar sırayla ve ayrı güncellemeler hâlinde uygulanacaktır.
- İşleme kayıtları, issue metinleri, sürüm notları, hata metinleri, kullanıcı arayüzü yazıları ve geliştirici notları Türkçe olacaktır.
- Teknik zorunluluklar dışında proje tarafından yazılan insan okunabilir metinlerde İngilizce kullanılmayacaktır.
- Kullanıcı yayımlanan EXE dosyasını onaylamadan sonraki geliştirme aşamasına geçilmeyecektir.
- Onaylanmayan bir güncelleme, izlenebilir bir geri alma kaydıyla önceki çalışan sürüme döndürülecektir.

Kalıcı çalışma düzeni [Issue #1](https://github.com/apexlions16/WwiseForge/issues/1) içinde takip edilir.

## Planlanan aşamalar

### Aşama 0 — Sürümleme ve Windows EXE yayın altyapısı

Durum: **Kullanıcı testi bekleniyor**

Takip: [Issue #2](https://github.com/apexlions16/WwiseForge/issues/2)

Bu aşamada sürüm numarası, otomatik Windows derlemesi, Türkçe sürüm notları ve ilk test sürümü hazırlanmıştır.

Sonraki aşama, bu sürüm kullanıcı tarafından test edilip onaylandıktan sonra görüşülerek belirlenecektir.

## Proje durumu

Proje erken geliştirme aşamasındadır. Özellikler ve dosya biçimi işlemleri gerçek dosyaların yedekleri üzerinde denenmelidir.

## Lisans

Proje için henüz bir lisans belirlenmemiştir.
