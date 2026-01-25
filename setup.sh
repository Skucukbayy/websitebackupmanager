#!/bin/bash

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   Web Backup Manager - Otomatik Kurulum      ${NC}"
echo -e "${BLUE}==============================================${NC}"

# Hata durumunda durma
set -e

# 1. Sistem Kontrolü
echo -e "\n${YELLOW}[1/4] Sistem gereksinimleri kontrol ediliyor...${NC}"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    echo "   İşletim Sistemi: $OS"
else
    echo "   İşletim sistemi tespit edilemedi."
fi

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Hata: Python 3 bulunamadı.${NC}"
    echo "Lütfen Python 3'ü yükleyin (sudo apt install python3 python3-venv python3-pip)"
    exit 1
fi
echo "   Python 3: Mevcut"

# 2. Virtual Environment
echo -e "\n${YELLOW}[2/4] Sanal ortam (venv) hazırlanıyor...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   venv oluşturuldu."
else
    echo "   venv zaten mevcut."
fi

# 3. Bağımlılıklar
echo -e "\n${YELLOW}[3/4] Kütüphaneler yükleniyor...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
if pip install -r requirements.txt; then
    echo "   Kurulum başarılı."
else
    echo -e "${RED}Hata: Kütüphaneler yüklenemedi.${NC}"
    echo "Sistem kütüphaneleri eksik olabilir. Şunu deneyin:"
    echo "sudo apt-get install python3-dev build-essential libssl-dev libffi-dev"
    exit 1
fi

# Gerekli klasörler
mkdir -p backups instance

# 4. Servis Başlatma
echo -e "\n${YELLOW}[4/4] Uygulama başlatılıyor...${NC}"

# Şifreleme anahtarı kontrolü
if [ -z "$ENCRYPTION_KEY" ]; then
    echo -e "${YELLOW}Uyarı: ENCRYPTION_KEY ortam değişkeni ayarlı değil. Varsayılan (güvensiz) anahtar kullanılacak.${NC}"
fi

export PORT=5050
IP_ADDR=$(hostname -I | cut -d' ' -f1)

echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   Kurulum Tamamlandı! 🚀                     ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "Web Arayüzü: ${BLUE}http://$IP_ADDR:5050${NC} veya ${BLUE}http://localhost:5050${NC}"
echo -e "Durdurmak için: CTRL+C"
echo ""

python app.py
