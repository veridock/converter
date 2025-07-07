# VeriDock Converter

Automatyczny system konwersji PDF na SVG z OCR i metadanymi dla Linux ext4.

## Opis

VeriDock Converter to zaawansowany system, który:
- Monitoruje wybrane foldery w systemie plików
- Automatycznie konwertuje pliki PDF na format SVG z osadzonymi danymi
- Generuje miniaturki wszystkich stron w formacie grid
- Wykonuje OCR (rozpoznawanie tekstu) dla każdej strony
- Przechowuje wszystkie dane w jednym pliku SVG z metadanymi
- Umożliwia późniejszy eksport i import danych

## Funkcje

### Automatyczne przetwarzanie
- **Monitorowanie folderów**: Skanuje wybrane katalogi co 10 sekund
- **Konwersja PDF→SVG**: Osadza PDF jako base64 w SVG
- **Generowanie miniaturek**: Tworzy grid miniaturek wszystkich stron
- **OCR**: Rozpoznaje tekst w języku polskim i angielskim
- **Usuwanie oryginałów**: Automatycznie usuwa pliki PDF po konwersji

### Format SVG
- **Osadzone dane**: PDF przechowywany jako data URI
- **Metadane**: Informacje o dokumencie, dacie utworzenia, liczbie stron
- **Miniaturki**: Grid wszystkich stron jako obrazy PNG
- **Dane OCR**: Pełny tekst ze współrzędnymi słów
- **Interfejs**: Interaktywny SVG z przyciskami i funkcjami

### Operacje
- **pdf2svg**: Konwersja PDF na SVG z osadzonymi danymi
- **svg2pdf**: Wyciąganie PDF z pliku SVG
- **pdf2png**: Generowanie miniaturek PNG z PDF
- **OCR**: Przetwarzanie rozpoznawania tekstu
- **Export/Import**: Eksport metadanych i danych OCR do JSON

## Instalacja

### Wymagania systemowe
- Linux (Ubuntu/Debian/CentOS/Fedora) lub macOS
- Python 3.8+
- Tesseract OCR
- Poppler (pdf2image)

### Automatyczna instalacja

1. **Pobierz wszystkie pliki VeriDock Converter**
```bash
# Upewnij się, że masz wszystkie pliki Python w jednym katalogu
ls -la *.py
# Powinny być widoczne:
# veridock_converter.py
# pdf_to_svg.py
# pdf_to_png.py
# ocr_processor.py
# svg_operations.py
# daemon_service.py
```

2. **Uruchom skrypt instalacyjny**
```bash
chmod +x install_setup.sh
./install_setup.sh
```

3. **Skonfiguruj foldery do monitorowania**
```bash
# Edytuj plik .veridock
nano .veridock

# Dodaj foldery, jeden na linię:
~/Downloads/
~/Documents/
/home/user/Inbox/
```

### Instalacja manualna

1. **Zainstaluj pakiety systemowe**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-pol poppler-utils

# CentOS/RHEL
sudo yum install python3 python3-pip tesseract poppler-utils

# macOS
brew install python tesseract poppler tesseract-lang
```

2. **Utwórz środowisko wirtualne**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Zainstaluj pakiety Python**
```bash
pip install pdf2image Pillow pytesseract watchdog PyPDF2
```

## Konfiguracja

### Plik .veridock
Zawiera listę folderów do monitorowania, jeden na linię:
```
# VeriDock Converter - Foldery do monitorowania
~/Downloads/
~/Documents/
/home/user/Inbox/
/var/spool/scanner/
```

### Parametry systemu
- **Interwał skanowania**: 10 sekund (można zmienić w `veridock_converter.py`)
- **Interwał OCR**: 60 sekund (przetwarzanie OCR w tle)
- **DPI konwersji**: 200 DPI dla miniaturek, 300 DPI dla OCR
- **Języki OCR**: Polski + Angielski

## Użytkowanie

### Uruchamianie jako demon
```bash
# Uruchom demon w tle
./veridock.sh daemon

# Sprawdź status
./veridock.sh status

# Zatrzymaj demon
./veridock.sh stop

# Restartuj demon
./veridock.sh restart
```

### Operacje ręczne
```bash
# Jednorazowe skanowanie folderów
./veridock.sh scan

# Konwertuj konkretny plik PDF
./veridock.sh convert dokument.pdf

# Przetwórz OCR dla pliku SVG
./veridock.sh ocr dokument.svg

# Wyciągnij PDF z pliku SVG
./veridock.sh extract dokument.svg

# Zwaliduj plik SVG
./veridock.sh validate dokument.svg
```

### Instalacja jako usługa systemowa
```bash
# Zainstaluj usługę systemd
./veridock-system.sh install-service

# Zarządzaj usługą
sudo systemctl start veridock
sudo systemctl stop veridock
sudo systemctl status veridock

# Odinstaluj usługę
./veridock-system.sh uninstall-service
```

### Instalacja zadania cron
```bash
# Zainstaluj skanowanie co 10 minut
./veridock-system.sh install-cron

# Odinstaluj zadanie cron
./veridock-system.sh uninstall-cron
```

## Struktura plików SVG

### Metadane dokumentu
```xml
<veridock:document>
  <veridock:filename>dokument.pdf</veridock:filename>
  <veridock:creation_time>2025-07-07T12:00:00</veridock:creation_time>
  <veridock:pages>5</veridock:pages>
  <veridock:pdf_metadata>{"title": "...", "author": "..."}</veridock:pdf_metadata>
  <veridock:ocr_status>completed</veridock:ocr_status>
  <veridock:ocr_data>{...}</veridock:ocr_data>
</veridock:document>
```

### Osadzone dane
```xml
<defs>
  <!-- Oryginalny PDF -->
  <veridock:pdf_data id="original_pdf">
    data:application/pdf;base64,JVBERi0xLjQ...
  </veridock:pdf_data>
  
  <!-- Grid miniaturek -->
  <veridock:thumbnail_grid id="thumbnail_grid">
    data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA...
  </veridock:thumbnail_grid>
</defs>
```

## Operacje na plikach

### Wyciąganie PDF z SVG
```bash
python svg_operations.py extract_pdf dokument.svg [output.pdf]
```

### Eksport danych OCR
```bash
# Eksport wszystkich danych
python svg_operations.py export_data dokument.svg all

# Eksport tylko OCR
python svg_operations.py export_data dokument.svg ocr

# Eksport metadanych miniaturek
python svg_operations.py export_data dokument.svg thumbnails
```

### Import danych do SVG
```bash
python svg_operations.py import_data dokument.svg dane_eksportu.json
```

### Listowanie plików SVG
```bash
python svg_operations.py list_directory ~/Documents/
```

### Walidacja pliku SVG
```bash
python svg_operations.py validate dokument.svg
```

## Struktura katalogów

```
veridock-converter/
├── venv/                     # Środowisko wirtualne Python
├── logs/                     # Logi systemu
├── temp/                     # Pliki tymczasowe
├── processed/                # Przetworzone pliki
├── config/                   # Dodatkowe konfiguracje
├── .veridock                 # Główna konfiguracja
├── veridock.sh              # Skrypt uruchomieniowy
├── veridock-system.sh       # Skrypt systemowy
├── veridock_converter.py    # Główny moduł
├── pdf_to_svg.py           # Konwersja PDF→SVG
├── pdf_to_png.py           # Generowanie PNG
├── ocr_processor.py        # Przetwarzanie OCR
├── svg_operations.py       # Operacje na SVG
├── daemon_service.py       # Demon systemowy
└── install_setup.sh        # Skrypt instalacyjny
```

## Monitorowanie i logi

### Logi systemu
```bash
# Logi główne
tail -f veridock.log

# Logi systemowe (jeśli zainstalowano jako usługę)
sudo journalctl -u veridock -f

# Logi demona
tail -f /var/log/veridock.log
```

### Sprawdzanie statusu
```bash
# Status demona
./veridock.sh status

# Status usługi systemowej
sudo systemctl status veridock

# Lista przetworzonych plików
ls -la processed/
```

## Rozwiązywanie problemów

### Tesseract OCR nie działa
```bash
# Sprawdź instalację
tesseract --version
tesseract --list-langs

# Zainstaluj język polski
sudo apt-get install tesseract-ocr-pol  # Ubuntu/Debian
brew install tesseract-lang             # macOS
```

### pdf2image nie działa
```bash
# Sprawdź poppler
which pdftoppm

# Zainstaluj poppler
sudo apt-get install poppler-utils      # Ubuntu/Debian
brew install poppler                    # macOS
```

### Problemy z uprawnieniami
```bash
# Sprawdź uprawnienia do folderów
ls -la ~/.veridock-converter/

# Popraw uprawnienia
chmod +x veridock.sh veridock-system.sh
chown -R $USER:$USER ~/.veridock-converter/
```

### Demon nie startuje
```bash
# Sprawdź logi
cat veridock.log

# Sprawdź czy port nie jest zajęty
ps aux | grep veridock

# Wymuś zatrzymanie
pkill -f veridock_converter
```

## Dostosowywanie

### Zmiana interwałów
Edytuj `veridock_converter.py`:
```python
self.scan_interval = 10  # sekundy - skanowanie plików
self.ocr_interval = 60   # sekundy - przetwarzanie OCR
```

### Zmiana jakości konwersji
Edytuj `pdf_to_svg.py` i `pdf_to_png.py`:
```python
self.dpi = 200              # DPI miniaturek
self.full_size_dpi = 300    # DPI dla OCR
self.thumbnail_size = (200, 280)  # Rozmiar miniaturek
```

### Dodanie nowych języków OCR
Edytuj `ocr_processor.py`:
```python
self.languages = 'pol+eng+deu'  # Dodaj niemiecki
```

## Licencja

VeriDock Converter - System do automatycznej konwersji PDF na SVG z OCR
Copyright (c) 2025 VeriDock System

Ten projekt jest udostępniony na licencji MIT.

## Wsparcie

W przypadku problemów:
1. Sprawdź logi w `veridock.log`
2. Uruchom `./veridock.sh help` dla pomocy
3. Sprawdź wymagania systemowe
4. Zweryfikuj konfigurację w `.veridock`

## Changelog

### v1.0 (2025-07-07)
- Pierwsza wersja systemu
- Automatyczne monitorowanie folderów
- Konwersja PDF na SVG z osadzonymi danymi
- Generowanie miniaturek w formacie grid
- OCR w języku polskim i angielskim
- Demon systemowy
- Skrypty instalacyjne
- Operacje eksportu/importu danych