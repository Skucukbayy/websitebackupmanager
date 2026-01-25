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
        exit 1
    fi
}

# 1. Sistem Kontrolü
echo -e "\n${YELLOW}[1/4] Sistem gereksinimleri kontrol ediliyor...${NC}"

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 bulunamadı. Yüklenmeye çalışılıyor...${NC}"
    install_package python3
fi

# Venv modül kontrolü
if ! python3 -c "import venv" &> /dev/null; then
    echo -e "${YELLOW}python3-venv modülü eksik. Yükleniyor...${NC}"
    install_package python3-venv
fi

# Pip kontrolü
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo -e "${YELLOW}python3-pip eksik. Yükleniyor...${NC}"
    install_package python3-pip
fi

echo "   Python ortamı: Mevcut"

# 2. Virtual Environment
echo -e "\n${YELLOW}[2/4] Sanal ortam (venv) hazırlanıyor...${NC}"
if [ -d "venv" ]; then
    echo "   venv zaten mevcut."
else
    echo "   venv oluşturuluyor..."
    # Venv oluşturmayı dene
    if ! python3 -m venv venv; then
        echo -e "${RED}Hata: venv oluşturulamadı!${NC}"
        echo "Lütfen 'python3-venv' paketinin yüklü olduğundan emin olun."
        echo "Ubuntu/Debian için: sudo apt install python3-venv"
        exit 1
    fi
    echo "   venv başarıyla oluşturuldu."
fi

# Aktivasyon dosyasını kontrol et
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}Hata: venv/bin/activate dosyası bulunamadı!${NC}"
    echo "venv oluşturma işlemi başarısız olmuş olabilir."
    rm -rf venv
    exit 1
fi

# 3. Bağımlılıklar
echo -e "\n${YELLOW}[3/4] Kütüphaneler yükleniyor...${NC}"
source venv/bin/activate

# Pip güncelle
pip install --upgrade pip > /dev/null 2>&1

# Paketleri yükle
echo "   requirements.txt yükleniyor..."
if ! pip install -r requirements.txt; then
    echo -e "${RED}Hata: Kütüphaneler yüklenemedi.${NC}"
    echo "Geliştirme paketleri eksik olabilir. Yüklenmeye çalışılıyor..."
    install_package "python3-dev build-essential libssl-dev libffi-dev"
    
    echo "   Tekrar deneniyor..."
    if ! pip install -r requirements.txt; then
        echo -e "${RED}Yine başarısız oldu. Lütfen hata çıktısını kontrol edin.${NC}"
        exit 1
    fi
fi

# Gerekli klasörler
mkdir -p backups instance

# 4. Servis Başlatma
echo -e "\n${YELLOW}[4/4] Uygulama başlatılıyor...${NC}"

if [ -z "$ENCRYPTION_KEY" ]; then
    echo -e "${YELLOW}Uyarı: ENCRYPTION_KEY ayarlı değil. Varsayılan anahtar kullanılıyor.${NC}"
fi

export PORT=5050
IP_ADDR=$(hostname -I 2>/dev/null | cut -d' ' -f1)
if [ -z "$IP_ADDR" ]; then
    IP_ADDR="localhost"
fi

echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   Kurulum Tamamlandı! 🚀                     ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "Web Arayüzü: ${BLUE}http://$IP_ADDR:5050${NC}"
echo -e "Durdurmak için: CTRL+C"
echo ""

python app.py
