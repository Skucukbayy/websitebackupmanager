#!/bin/bash

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Web Backup Manager Kurulumu ===${NC}"

# 1. Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Hata: Python 3 yüklü değil! Lütfen önce Python 3 yükleyin.${NC}"
    exit 1
fi

# 2. Virtual Environment Oluşturma
echo -e "${GREEN}1. Sanal ortam (venv) oluşturuluyor...${NC}"
if [ -d "venv" ]; then
    echo "   venv zaten mevcut, atlanıyor."
else
    python3 -m venv venv
    echo "   venv oluşturuldu."
fi

# 3. Bağımlılıkları Yükleme
echo -e "${GREEN}2. Bağımlılıklar yükleniyor...${NC}"
source venv/bin/activate
pip install --upgrade pip
if pip install -r requirements.txt; then
    echo "   Bağımlılıklar başarıyla yüklendi."
else
    echo -e "${RED}Bağımlılık yükleme hatası!${NC}"
    exit 1
fi

# 4. Gerekli Dizinleri Oluşturma
echo -e "${GREEN}3. Dizinler kontrol ediliyor...${NC}"
mkdir -p backups
mkdir -p instance
echo "   Yedekleme ve veritabanı dizinleri hazır."

# 5. Başlatma Scripti Oluşturma
echo -e "${GREEN}4. Başlatma scripti (run.sh) oluşturuluyor...${NC}"
cat > run.sh << EOL
#!/bin/bash
source venv/bin/activate
export PORT=5050
echo "Uygulama başlatılıyor: http://localhost:5050"
python app.py
EOL
chmod +x run.sh

echo -e "${BLUE}=== Kurulum Tamamlandı! ===${NC}"
echo ""
echo -e "Uygulamayı başlatmak için şu komutu çalıştırın:"
echo -e "${GREEN}./run.sh${NC}"
echo ""
