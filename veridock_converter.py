#!/usr/bin/env python3
"""
VeriDock Converter - Główny moduł do konwersji PDF na SVG z OCR
Autor: VeriDock System
Wersja: 1.0
"""

import os
import sys
import time
import json
import base64
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('veridock.log'),
        logging.StreamHandler()
    ]
)


class VeriDockConverter:
    """Główna klasa systemu VeriDock Converter"""

    def __init__(self, config_file: str = ".veridock"):
        self.config_file = config_file
        self.watch_directories = []
        self.scan_interval = 10  # sekundy
        self.ocr_interval = 60  # sekundy
        self.last_ocr_run = 0
        self.processed_files = set()

        self.load_config()
        self.ensure_dependencies()

    def load_config(self):
        """Ładuje konfigurację z pliku .veridock"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            expanded_path = os.path.expanduser(line)
                            if os.path.exists(expanded_path):
                                self.watch_directories.append(expanded_path)
                                logging.info(f"Dodano folder do monitorowania: {expanded_path}")
            else:
                # Domyślne foldery
                default_dirs = ["~/Downloads/", "~/Documents/"]
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    f.write("# VeriDock Converter - Foldery do monitorowania\n")
                    f.write("# Dodaj kolejne ścieżki, każda w nowej linii\n")
                    for dir_path in default_dirs:
                        f.write(f"{dir_path}\n")
                        expanded_path = os.path.expanduser(dir_path)
                        if os.path.exists(expanded_path):
                            self.watch_directories.append(expanded_path)

        except Exception as e:
            logging.error(f"Błąd wczytywania konfiguracji: {e}")

    def ensure_dependencies(self):
        """Sprawdza i instaluje wymagane zależności"""
        required_packages = [
            'pdf2image',
            'pytesseract',
            'Pillow',
            'watchdog'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            logging.warning(f"Brakujące pakiety: {missing_packages}")
            logging.info("Zainstaluj je używając: pip install " + " ".join(missing_packages))

    def get_file_hash(self, file_path: str) -> str:
        """Generuje hash pliku do identyfikacji"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def find_pdf_files(self) -> List[str]:
        """Znajdź wszystkie pliki PDF w monitorowanych folderach"""
        pdf_files = []
        for directory in self.watch_directories:
            try:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            file_path = os.path.join(root, file)
                            file_hash = self.get_file_hash(file_path)
                            if file_hash not in self.processed_files:
                                pdf_files.append(file_path)
            except Exception as e:
                logging.error(f"Błąd skanowania folderu {directory}: {e}")

        return pdf_files

    def process_pdf(self, pdf_path: str) -> bool:
        """Przetwarza pojedynczy plik PDF"""
        try:
            logging.info(f"Przetwarzanie: {pdf_path}")

            # Import funkcji konwersji
            from pdf_to_svg import PDFToSVGConverter
            from pdf_to_png import PDFToPNGConverter
            from ocr_processor import OCRProcessor

            # Konwersja PDF na SVG z osadzonymi danymi
            svg_converter = PDFToSVGConverter()
            svg_path = svg_converter.convert(pdf_path)

            if svg_path:
                # Generowanie miniaturek PNG
                png_converter = PDFToPNGConverter()
                png_converter.generate_thumbnails(pdf_path, svg_path)

                # Oznacz jako przetworzony
                file_hash = self.get_file_hash(pdf_path)
                self.processed_files.add(file_hash)

                # Usuń oryginalny PDF
                os.remove(pdf_path)
                logging.info(f"Usunięto oryginalny plik: {pdf_path}")

                return True

        except Exception as e:
            logging.error(f"Błąd przetwarzania {pdf_path}: {e}")

        return False

    def process_ocr(self):
        """Przetwarza OCR dla wszystkich SVG"""
        try:
            from ocr_processor import OCRProcessor
            ocr_processor = OCRProcessor()

            for directory in self.watch_directories:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.lower().endswith('.svg'):
                            svg_path = os.path.join(root, file)
                            ocr_processor.process_svg(svg_path)

            self.last_ocr_run = time.time()
            logging.info("Zakończono przetwarzanie OCR")

        except Exception as e:
            logging.error(f"Błąd przetwarzania OCR: {e}")

    def run_daemon(self):
        """Uruchamia demon monitorujący"""
        logging.info("Uruchamianie demona VeriDock Converter")
        logging.info(f"Monitorowane foldery: {self.watch_directories}")

        while True:
            try:
                # Skanuj nowe pliki PDF
                pdf_files = self.find_pdf_files()

                for pdf_file in pdf_files:
                    self.process_pdf(pdf_file)

                # Sprawdź czy czas na OCR
                current_time = time.time()
                if current_time - self.last_ocr_run >= self.ocr_interval:
                    self.process_ocr()

                # Poczekaj przed następnym skanowaniem
                time.sleep(self.scan_interval)

            except KeyboardInterrupt:
                logging.info("Zatrzymywanie demona...")
                break
            except Exception as e:
                logging.error(f"Błąd w pętli głównej: {e}")
                time.sleep(5)


def main():
    """Funkcja główna"""
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = ".veridock"

    converter = VeriDockConverter(config_file)

    if len(sys.argv) > 2 and sys.argv[2] == "--daemon":
        converter.run_daemon()
    else:
        # Jednorazowe skanowanie
        pdf_files = converter.find_pdf_files()
        if pdf_files:
            logging.info(f"Znaleziono {len(pdf_files)} plików PDF")
            for pdf_file in pdf_files:
                converter.process_pdf(pdf_file)
        else:
            logging.info("Nie znaleziono plików PDF do przetworzenia")


if __name__ == "__main__":
    main()