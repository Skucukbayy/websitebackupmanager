# Web Backup Manager

**[English](#english) | [Türkçe](#türkçe)**

---

<a name="english"></a>
## English

A modern, web-based backup manager for Linux systems. Backup your remote websites via SSH/SFTP or FTP to your local machine with automated schedules.

### ✨ Features

- SSH/SFTP and FTP/FTPS backup support
- Automated scheduled backups (minutes, hours, days, weeks)
- Admin panel with password management
- NTP-synced accurate timestamps (Europe/Istanbul)
- Multi-language support (Turkish / English)
- Modern glassmorphism UI

### 🚀 One-Command Installation

Run this command on your Linux server:

```bash
curl -O https://raw.githubusercontent.com/Skucukbayy/websitebackupmanager/main/setup.sh && chmod +x setup.sh && ./setup.sh
```

This script will:
1. Check system requirements.
2. Create a virtual environment.
3. Install all dependencies (`pip install -r requirements.txt`).
4. **Start the application**.

Access via browser: `http://<YOUR_IP>:5050`

### 🔧 Manual Installation

```bash
git clone https://github.com/Skucukbayy/websitebackupmanager.git
cd websitebackupmanager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### 🔑 Default Login

- **Username:** `admin`
- **Password:** `admin`

> ⚠️ You will be prompted to change the password on first login.

---

### Docker Installation (Alternative)

If you prefer Docker:

```bash
docker-compose up -d --build
```

---

<a name="türkçe"></a>
## Türkçe

Linux sistemler için geliştirilmiş, modern web tabanlı yedekleme yöneticisi.

### ✨ Özellikler

- SSH/SFTP ve FTP/FTPS yedekleme desteği
- Otomatik zamanlanmış yedekleme (dakika, saat, gün, hafta)
- Yönetim paneli ve şifre yönetimi
- NTP senkronizasyonlu doğru saat (Europe/Istanbul)
- Çoklu dil desteği (Türkçe / İngilizce)
- Modern glassmorphism arayüz

### 🚀 Tek Komutla Kurulum

Linux sunucunuzda şu komutu çalıştırın:

```bash
curl -O https://raw.githubusercontent.com/Skucukbayy/websitebackupmanager/main/setup.sh && chmod +x setup.sh && ./setup.sh
```

Bu script şunları yapar:
1. Sistem gereksinimlerini kontrol eder.
2. Sanal ortam (venv) oluşturur.
3. Kütüphaneleri kurar (`pip install -r requirements.txt`).
4. **Uygulamayı başlatır.**

Tarayıcınızdan: `http://<SUNUCU_IP_ADRESINIZ>:5050`

### 🔧 Manuel Kurulum

```bash
git clone https://github.com/Skucukbayy/websitebackupmanager.git
cd websitebackupmanager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### 🔑 Varsayılan Giriş Bilgileri

- **Kullanıcı Adı:** `admin`
- **Şifre:** `admin`

> ⚠️ İlk girişte şifrenizi değiştirmeniz istenecektir.

---

### Docker ile Kurulum (Alternatif)

Docker tercih ederseniz:

```bash
docker-compose up -d --build
```

