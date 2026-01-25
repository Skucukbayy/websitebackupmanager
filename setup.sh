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

# --- ADIM 0: Proje Dosyalarını Kontrol Et ---
# Eğer script tek başına indirildiyse, projeyi clone'lamamız lazım.
if [ ! -f "requirements.txt" ]; then
    echo -e "\n${YELLOW}[0/3] Proje dosyaları aranıyor...${NC}"
    
    # Git yüklü mü?
    if ! command -v git &> /dev/null; then
         echo -e "${RED}Hata: Git bulunamadı.${NC}"
         echo "Lütfen git yükleyin: sudo apt-get install git"
         exit 1
    fi

    if [ -d "websitebackupmanager" ]; then
        echo "   Klasör mevcut, içine giriliyor..."
        cd websitebackupmanager
        echo "   Güncelleniyor..."
        git pull
    else
        echo "   Proje GitHub'dan indiriliyor..."
        git clone https://github.com/Skucukbayy/websitebackupmanager.git
        cd websitebackupmanager
    fi
fi

# Artık proje klasörünün içindeyiz

# Fonksiyon: Paket yükleme denemesi
install_package() {
    PACKAGE=$1
    if command -v apt-get &> /dev/null; then
        echo -e "${YELLOW}   [apt] $PACKAGE yükleniyor...${NC}"
        sudo apt-get update && sudo apt-get install -y $PACKAGE
    elif command -v dnf &> /dev/null; then
        echo -e "${YELLOW}   [dnf] $PACKAGE yükleniyor...${NC}"
        sudo dnf install -y $PACKAGE
    elif command -v yum &> /dev/null; then
        echo -e "${YELLOW}   [yum] $PACKAGE yükleniyor...${NC}"
        sudo yum install -y $PACKAGE
    elif command -v apk &> /dev/null; then
        echo -e "${YELLOW}   [apk] $PACKAGE yükleniyor...${NC}"
        sudo apk add $PACKAGE
    else
        echo -e "${RED}Hata: Paket yöneticisi bulunamadı. Lütfen manuel olarak '$PACKAGE' yükleyin.${NC}"
    fi
}

# 1. Sistem Kontrolü
echo -e "\n${YELLOW}[1/3] Kontroller yapılıyor...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 bulunamadı. Yüklenmeye çalışılıyor...${NC}"
    install_package python3
fi

# 2. Kurulum
echo -e "\n${YELLOW}[2/3] Kurulum başlıyor...${NC}"

USE_VENV=true

# Venv oluşturmayı dene
echo "   Sanal ortam (venv) oluşturuluyor..."
# Temizlik
[ -d "venv" ] && rm -rf venv

if python3 -m venv venv > /dev/null 2>&1; then
    echo "   venv başarıyla oluşturuldu."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        USE_VENV=false
    fi
else
    echo -e "${YELLOW}   venv oluşturulamadı. Kullanıcı modunda (user) kurulacak.${NC}"
    USE_VENV=false
fi

# Kütüphaneleri yükle
echo "   Kütüphaneler yükleniyor..."
pip install --upgrade pip > /dev/null 2>&1

if [ "$USE_VENV" = true ]; then
    if ! pip install -r requirements.txt; then
         echo -e "${RED}   Bağımlılık hatası. Geliştirme araçları yüklenip tekrar deneniyor...${NC}"
         install_package "python3-dev build-essential libssl-dev libffi-dev"
         pip install -r requirements.txt
    fi
else
    pip install --user -r requirements.txt
    export PATH="$HOME/.local/bin:$PATH"
fi

# Gerekli klasörler
mkdir -p backups instance

# 3. Başlatma
echo -e "\n${YELLOW}[3/3] Uygulama başlatılıyor...${NC}"

if [ -z "$ENCRYPTION_KEY" ]; then
    echo -e "${YELLOW}Uyarı: ENCRYPTION_KEY ayarlı değil. Varsayılan anahtar kullanılıyor.${NC}"
fi

export PORT=5050
IP_ADDR=$(hostname -I 2>/dev/null | cut -d' ' -f1)
[ -z "$IP_ADDR" ] && IP_ADDR="localhost"

echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   Kurulum Tamamlandı! 🚀                     ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "Web Arayüzü: ${BLUE}http://$IP_ADDR:5050${NC}"
echo ""

python3 app.py
