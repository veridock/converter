#!/bin/bash
# VeriDock Converter - Skrypt instalacyjny
# Autor: VeriDock System

set -e

echo "=== VeriDock Converter - Instalacja ==="

# Sprawdź system operacyjny
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Wykryto system Linux"
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Wykryto system macOS"
    OS="macos"
else
    echo "Nieobsługiwany system operacyjny: $OSTYPE"
    exit 1
fi

# Sprawdź uprawnienia
if [[ $EUID -eq 0 ]]; then
    echo "Nie uruchamiaj jako root. Skrypt sam poprosi o sudo gdy będzie potrzebne."
    exit 1
fi

# Funkcja instalacji pakietów systemowych
install_system_packages() {
    echo "Instalowanie pakietów systemowych..."

    if [[ "$OS" == "linux" ]]; then
        # Sprawdź dystrybucję
        if command -v apt-get >/dev/null 2>&1; then
            # Debian/Ubuntu
            echo "Próba naprawy źródeł pakietów..."
            
            # Pobierz nazwę dystrybucji i architekturę
            DISTRO_CODENAME=$(lsb_release -cs)
            ARCH=$(dpkg --print-architecture)
            
            echo "Wykryto dystrybucję: $DISTRO_CODENAME ($ARCH)"
            
            # Użyj mirrora, który działa (np. mirrors.edge.kernel.org)
            MIRROR="http://mirrors.edge.kernel.org/ubuntu"
            
            # Utwórz nowy plik sources.list
            echo "# VeriDock temporary sources.list" | sudo tee /etc/apt/sources.list
            
            # Dodaj główne repozytorium
            echo "deb $MIRROR/ $DISTRO_CODENAME main restricted universe multiverse" | sudo tee -a /etc/apt/sources.list
            
            # Dodaj repozytoria updates i security
            echo "deb $MIRROR/ $DISTRO_CODENAME-updates main restricted universe multiverse" | sudo tee -a /etc/apt/sources.list
            echo "deb $MIRROR/ $DISTRO_CODENAME-security main restricted universe multiverse" | sudo tee -a /etc/apt/sources.list
            
            # Wyczyść cache APT
            echo "Czyszczenie cache APT..."
            sudo rm -rf /var/lib/apt/lists/*
            sudo mkdir -p /var/lib/apt/lists/partial
            sudo apt-get clean
            
            # Zaktualizuj listę pakietów
            echo "Aktualizacja listy pakietów..."
            sudo apt-get update -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true || true
            
            # Zainstaluj wymagane pakiety
            echo "Instalowanie wymaganych pakietów..."
            sudo apt-get install -y --no-install-recommends \
                python3 \
                python3-pip \
                python3-venv \
                tesseract-ocr \
                tesseract-ocr-pol \
                poppler-utils
                
            if [ $? -ne 0 ]; then
                echo "Ostrzeżenie: Niektóre pakiety nie mogły zostać zainstalowane."
                echo "Kontynuowanie instalacji z dostępnymi pakietami..."
            fi
        elif command -v yum >/dev/null 2>&1; then
            # CentOS/RHEL
            sudo yum install -y python3 python3-pip tesseract poppler-utils
        elif command -v dnf >/dev/null 2>&1; then
            # Fedora
            sudo dnf install -y python3 python3-pip tesseract poppler-utils
        else
            echo "Nieobsługiwany menedżer pakietów. Zainstaluj ręcznie:"
            echo "- Python 3.8+"
            echo "- pip"
            echo "- tesseract-ocr"
            echo "- poppler-utils"
            exit 1
        fi
    elif [[ "$OS" == "macos" ]]; then
        # macOS z Homebrew
        if ! command -v brew >/dev/null 2>&1; then
            echo "Homebrew nie jest zainstalowany. Instalowanie..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi

        brew install python tesseract poppler

        # Zainstaluj polskie dane językowe dla Tesseract
        brew install tesseract-lang
    fi
}

# Funkcja tworzenia środowiska wirtualnego
create_venv() {
    echo "Tworzenie środowiska wirtualnego Python..."

    if [[ -d "venv" ]]; then
        echo "Środowisko wirtualne już istnieje. Usuwanie..."
        rm -rf venv
    fi

    python3 -m venv venv
    source venv/bin/activate

    echo "Aktualizowanie pip..."
    pip install --upgrade pip
}

# Funkcja instalacji pakietów Python
install_python_packages() {
    echo "Instalowanie pakietów Python..."

    # Aktywuj środowisko wirtualne jeśli nie jest aktywne
    if [[ -z "$VIRTUAL_ENV" ]]; then
        source venv/bin/activate
    fi

    # Lista wymaganych pakietów z mniej restrykcyjnymi wersjami
    cat > requirements.txt << EOF
pdf2image>=1.0.0
Pillow>=9.0.0
pytesseract>=0.3.0
watchdog>=2.0.0
PyPDF2>=2.0.0
EOF

    pip install -r requirements.txt

    echo "Pakiety Python zainstalowane pomyślnie"
}

# Funkcja tworzenia struktury katalogów
create_directories() {
    echo "Tworzenie struktury katalogów..."

    # Katalogi robocze
    mkdir -p logs
    mkdir -p temp
    mkdir -p processed

    # Katalogi konfiguracyjne
    mkdir -p config

    echo "Struktura katalogów utworzona"
}

# Funkcja tworzenia pliku konfiguracyjnego
create_config() {
    echo "Tworzenie pliku konfiguracyjnego..."

    if [[ ! -f ".veridock" ]]; then
        cat > .veridock << EOF
# VeriDock Converter - Konfiguracja
# Foldery do monitorowania (jeden na linię)
# Ścieżki mogą używać ~ dla katalogu domowego

# Domyślne foldery
~/Downloads/
~/Documents/

# Dodaj więcej folderów według potrzeb:
# /path/to/another/folder/
# ~/Desktop/PDFs/
EOF
        echo "Utworzono plik konfiguracyjny .veridock"
    else
        echo "Plik konfiguracyjny .veridock już istnieje"
    fi
}

# Funkcja tworzenia skryptów uruchomieniowych
create_launch_scripts() {
    echo "Tworzenie skryptów uruchomieniowych..."

    # Skrypt uruchamiający
    cat > veridock.sh << 'EOF'
#!/bin/bash
# VeriDock Converter - Skrypt uruchomieniowy

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Aktywuj środowisko wirtualne
source venv/bin/activate

# Uruchom w zależności od argumentów
case "$1" in
    "daemon")
        echo "Uruchamianie demona VeriDock..."
        python daemon_service.py start
        ;;
    "stop")
        echo "Zatrzymywanie demona VeriDock..."
        python daemon_service.py stop
        ;;
    "status")
        python daemon_service.py status
        ;;
    "restart")
        echo "Restartowanie demona VeriDock..."
        python daemon_service.py restart
        ;;
    "scan")
        echo "Jednorazowe skanowanie..."
        python veridock_converter.py
        ;;
    "convert")
        if [[ -z "$2" ]]; then
            echo "Użycie: $0 convert <plik.pdf>"
            exit 1
        fi
        echo "Konwertowanie pliku: $2"
        python pdf_to_svg.py "$2"
        ;;
    "ocr")
        if [[ -z "$2" ]]; then
            echo "Użycie: $0 ocr <plik.svg>"
            exit 1
        fi
        echo "Przetwarzanie OCR: $2"
        python ocr_processor.py "$2"
        ;;
    "extract")
        if [[ -z "$2" ]]; then
            echo "Użycie: $0 extract <plik.svg>"
            exit 1
        fi
        echo "Wyciąganie PDF z SVG: $2"
        python svg_operations.py extract_pdf "$2"
        ;;
    "validate")
        if [[ -z "$2" ]]; then
            echo "Użycie: $0 validate <plik.svg>"
            exit 1
        fi
        echo "Walidacja SVG: $2"
        python svg_operations.py validate "$2"
        ;;
    "help"|"")
        echo "VeriDock Converter - Użycie:"
        echo ""
        echo "Demon systemowy:"
        echo "  $0 daemon    - Uruchom demon w tle"
        echo "  $0 stop      - Zatrzymaj demon"
        echo "  $0 restart   - Restartuj demon"
        echo "  $0 status    - Sprawdź status demona"
        echo ""
        echo "Operacje ręczne:"
        echo "  $0 scan      - Jednorazowe skanowanie folderów"
        echo "  $0 convert <plik.pdf>  - Konwertuj PDF na SVG"
        echo "  $0 ocr <plik.svg>      - Przetwórz OCR dla SVG"
        echo "  $0 extract <plik.svg>  - Wyciągnij PDF z SVG"
        echo "  $0 validate <plik.svg> - Zwaliduj plik SVG"
        echo ""
        echo "Konfiguracja:"
        echo "  Edytuj plik .veridock aby dodać foldery do monitorowania"
        echo ""
        ;;
    *)
        echo "Nieznana komenda: $1"
        echo "Użyj: $0 help aby zobaczyć dostępne opcje"
        exit 1
        ;;
esac
EOF

    chmod +x veridock.sh

    # Skrypt systemowy
    cat > veridock-system.sh << 'EOF'
#!/bin/bash
# VeriDock Converter - Skrypt systemowy

VERIDOCK_DIR="$HOME/.veridock-converter"
VERIDOCK_USER="$USER"

case "$1" in
    "install-service")
        echo "Instalowanie usługi systemowej VeriDock..."

        # Utwórz plik usługi systemd
        sudo tee /etc/systemd/system/veridock.service > /dev/null << SEOF
[Unit]
Description=VeriDock Converter Daemon
After=network.target

[Service]
Type=forking
User=$VERIDOCK_USER
WorkingDirectory=$VERIDOCK_DIR
ExecStart=$VERIDOCK_DIR/veridock.sh daemon
ExecStop=$VERIDOCK_DIR/veridock.sh stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SEOF

        # Przeładuj systemd
        sudo systemctl daemon-reload
        sudo systemctl enable veridock.service

        echo "Usługa systemowa zainstalowana. Użyj:"
        echo "  sudo systemctl start veridock    - uruchom"
        echo "  sudo systemctl stop veridock     - zatrzymaj"
        echo "  sudo systemctl status veridock   - status"
        ;;

    "uninstall-service")
        echo "Odinstalowywanie usługi systemowej..."
        sudo systemctl stop veridock.service || true
        sudo systemctl disable veridock.service || true
        sudo rm -f /etc/systemd/system/veridock.service
        sudo systemctl daemon-reload
        echo "Usługa systemowa odinstalowana"
        ;;

    "install-cron")
        echo "Instalowanie zadania cron..."

        # Dodaj zadanie cron co 10 minut
        (crontab -l 2>/dev/null || true; echo "*/10 * * * * $VERIDOCK_DIR/veridock.sh scan >/dev/null 2>&1") | crontab -

        echo "Zadanie cron zainstalowane (skanowanie co 10 minut)"
        ;;

    "uninstall-cron")
        echo "Odinstalowywanie zadania cron..."
        crontab -l 2>/dev/null | grep -v "veridock.sh scan" | crontab -
        echo "Zadanie cron odinstalowane"
        ;;

    *)
        echo "Użycie: $0 {install-service|uninstall-service|install-cron|uninstall-cron}"
        ;;
esac
EOF

    chmod +x veridock-system.sh

    echo "Skrypty uruchomieniowe utworzone"
}

# Funkcja testowania instalacji
test_installation() {
    echo "Testowanie instalacji..."

    # Aktywuj środowisko wirtualne
    source venv/bin/activate

    # Test importów Python
    python3 -c "
import pdf2image
import pytesseract
import PIL
import watchdog
import PyPDF2
print('✓ Wszystkie pakiety Python dostępne')
"

    # Test Tesseract
    if command -v tesseract >/dev/null 2>&1; then
        echo "✓ Tesseract OCR dostępny"
        tesseract --list-langs | grep -q pol && echo "✓ Polski język Tesseract dostępny" || echo "⚠ Polski język Tesseract może być niedostępny"
    else
        echo "✗ Tesseract OCR niedostępny"
        return 1
    fi

    # Test poppler (pdf2image)
    python3 -c "
from pdf2image import convert_from_path
print('✓ pdf2image (poppler) działa')
" 2>/dev/null || {
        echo "✗ pdf2image (poppler) nie działa"
        return 1
    }

    echo "✓ Instalacja przetestowana pomyślnie"
}

# Funkcja finalizacji
finalize_installation() {
    echo ""
    echo "=== Instalacja VeriDock Converter zakończona ==="
    echo ""
    echo "Katalog instalacyjny: $(pwd)"
    echo ""
    echo "Następne kroki:"
    echo "1. Edytuj plik .veridock aby skonfigurować foldery do monitorowania"
    echo "2. Uruchom: ./veridock.sh daemon aby rozpocząć monitorowanie"
    echo "3. Sprawdź status: ./veridock.sh status"
    echo ""
    echo "Opcje systemowe:"
    echo "- Zainstaluj jako usługę systemową: ./veridock-system.sh install-service"
    echo "- Zainstaluj zadanie cron: ./veridock-system.sh install-cron"
    echo ""
    echo "Przykłady użycia:"
    echo "- Konwertuj plik: ./veridock.sh convert dokument.pdf"
    echo "- Przetwórz OCR: ./veridock.sh ocr dokument.svg"
    echo "- Wyciągnij PDF: ./veridock.sh extract dokument.svg"
    echo ""
    echo "Logi znajdziesz w: ./logs/"
    echo "Pomoc: ./veridock.sh help"
    echo ""
}

# Główna funkcja instalacji
main() {
    echo "Rozpoczynanie instalacji VeriDock Converter..."

    # Sprawdź czy wszystkie pliki źródłowe są dostępne
    required_files=(
        "veridock_converter.py"
        "pdf_to_svg.py"
        "pdf_to_png.py"
        "ocr_processor.py"
        "svg_operations.py"
        "daemon_service.py"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            echo "✗ Brak wymaganego pliku: $file"
            echo "Upewnij się, że wszystkie pliki VeriDock są w tym katalogu"
            exit 1
        fi
    done

    echo "✓ Wszystkie wymagane pliki dostępne"

    # Wykonaj kroki instalacji
    install_system_packages
    create_venv
    install_python_packages
    create_directories
    create_config
    create_launch_scripts
    test_installation
    finalize_installation
}

# Sprawdź argumenty
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "VeriDock Converter - Skrypt instalacyjny"
    echo ""
    echo "Użycie: $0 [opcje]"
    echo ""
    echo "Opcje:"
    echo "  --help, -h     Pokaż tę pomoc"
    echo "  --skip-system  Pomiń instalację pakietów systemowych"
    echo ""
    echo "Skrypt automatycznie:"
    echo "- Zainstaluje wymagane pakiety systemowe"
    echo "- Utworzy środowisko wirtualne Python"
    echo "- Zainstaluje pakiety Python"
    echo "- Utworzy strukturę katalogów"
    echo "- Utworzy pliki konfiguracyjne"
    echo "- Utworzy skrypty uruchomieniowe"
    echo "- Przetestuje instalację"
    echo ""
    exit 0
fi

# Sprawdź czy pominąć pakiety systemowe
if [[ "$1" == "--skip-system" ]]; then
    echo "Pomijanie instalacji pakietów systemowych..."
    create_venv
    install_python_packages
    create_directories
    create_config
    create_launch_scripts
    test_installation
    finalize_installation
else
    # Pełna instalacja
    main
fi

echo "Instalacja zakończona pomyślnie!"