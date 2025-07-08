#!/bin/bash
# VeriDock Converter - Skrypt uruchomieniowy
# Autor: VeriDock System

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Przejdź do głównego katalogu projektu

# Aktywuj środowisko wirtualne
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Błąd: Nie znaleziono środowiska wirtualnego. Uruchom install.sh najpierw."
    exit 1
fi

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
