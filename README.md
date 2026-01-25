# Web Backup Manager

**[English](#english) | [Türkçe](#türkçe)**

---

<a name="english"></a>
## English

A modern, web-based backup manager for Linux systems. Backup your remote websites via SSH/SFTP or FTP to your local machine with automated schedules.

### 🚀 One-Command Installation

Run this command on your Linux server:

```bash
curl -O https://raw.githubusercontent.com/Skucukbayy/websitebackupmanager/main/setup.sh && chmod +x setup.sh && ./setup.sh
```

This script will:
1. Check system requirements.
2. create a virtual environment.
3. Install all dependencies.
4. **Start the application**.

Access via browser: `http://<YOUR_IP>:5050`

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

### 🚀 Tek Komutla Kurulum

Linux sunucunuzda şu komutu çalıştırın:

```bash
curl -O https://raw.githubusercontent.com/Skucukbayy/websitebackupmanager/main/setup.sh && chmod +x setup.sh && ./setup.sh
```

Bu script şunları yapar:
1. Sistem gereksinimlerini kontrol eder.
2. Sanal ortam (venv) oluşturur.
3. Kütüphaneleri kurar.
4. **Uygulamayı başlatır.**

Tarayıcınızdan: `http://<SUNUCU_IP_ADRESINIZ>:5050`

---

### Docker ile Kurulum (Alternatif)

Docker tercih ederseniz:

```bash
docker-compose up -d --build
```
