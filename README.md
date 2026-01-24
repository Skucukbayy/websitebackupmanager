# Web Backup Manager

**[English](#english) | [Türkçe](#türkçe)**

---

<a name="english"></a>
## English

A modern, web-based backup manager for Linux systems. Backup your remote websites via SSH/SFTP or FTP to your local machine with automated schedules.

### Features
- 🌟 **Modern UI:** Glassmorphism design with dark theme.
- 🌍 **Multi-language:** English and Turkish support.
- 🔄 **Protocols:** SSH (SFTP) and FTP support.
- ⏰ **Scheduling:** Automated backups (minutely, hourly, daily, weekly).
- 📊 **Dashboard:** Real-time stats and backup history.

### Installation

1. **Clone & Setup:**
   ```bash
   # Clone repository (after you create one)
   git clone <your-repo-url>
   cd web-backup-manager

   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Run:**
   ```bash
   # Run on port 5050
   PORT=5050 python app.py
   ```
   Access via browser: [http://localhost:5050](http://localhost:5050)

---

<a name="türkçe"></a>
## Türkçe

Linux sistemler için geliştirilmiş, modern web tabanlı yedekleme yöneticisi. Uzak web sitelerinizi SSH/SFTP veya FTP protokolleri üzerinden yerel makinenize otomatik olarak yedekleyin.

### Özellikler
- 🌟 **Modern Arayüz:** Koyu temalı, şık Glassmorphism tasarımı.
- 🌍 **Çoklu Dil:** Türkçe ve İngilizce desteği.
- 🔄 **Protokoller:** SSH (SFTP) ve FTP desteği.
- ⏰ **Zamanlama:** Otomatik yedekleme (dakikalık, saatlik, günlük, haftalık).
- 📊 **Panel:** Anlık istatistikler ve yedekleme geçmişi.


   ```

### Nasıl Çalışır?

1. **Kurulum:**
   ```bash
   # Sanal ortamı aktif et
   source venv/bin/activate
   
   # Bağımlılıkları yükle (kurulu değilse)
   pip install -r requirements.txt
   ```

2. **Uygulamayı Başlatma:**
   ```bash
   # Varsayılan port 5050 ile başlat
   PORT=5050 python app.py
   ```
   Tarayıcınızda **[http://localhost:5050](http://localhost:5050)** adresine gidin.

3. **Kullanım Adımları:**
   - **Site Ekle:** "Yeni Site Ekle" butonuna tıklayın.
   - **Bilgileri Girin:** SSH veya FTP bilgilerinizi doldurun.
   - **Test Edin:** "Bağlantı Testi" ile bilgilerin doğruluğunu kontrol edin.
   - **Kaydedin:** Siteyi kaydedin.
   - **Yedekleyin:** Artık manuel olarak "Şimdi Yedekle" diyebilir veya ayarladığınız zamanlamanın çalışmasını bekleyebilirsiniz.
   - **Yedekler Nerede?:** Yedekler, proje klasörü içindeki `backups/` dizininde veya belirlediğiniz yerel yolda saklanır.

### Veritabanı
Uygulama, verilerini (site ayarları, geçmiş vb.) yerel bir SQLite veritabanında (`instance/backups.db`) saklar. Bu dosya Git'e dahil edilmemiştir (`.gitignore` sayesinde), böylece verileriniz güvende kalır.

## Yapılandırma

Ortam değişkenleri ile yapılandırılabilir:

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| HOST | 0.0.0.0 | Sunucu adresi |
| PORT | 5000 | Sunucu portu |
| DEBUG | True | Debug modu |
| SECRET_KEY | - | Flask secret key |
| BACKUP_PATH | ./backups | Varsayılan yedekleme dizini |

## Güvenlik Notları

⚠️ **Önemli**:
- Bu uygulama yerel ağda kullanım için tasarlanmıştır
- Production ortamında HTTPS kullanın
- Şifreler veritabanında düz metin olarak saklanır - ek şifreleme önerilir
- Güvenlik duvarı kurallarınızı uygun şekilde yapılandırın

## Lisans

MIT License
