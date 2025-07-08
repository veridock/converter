#!/usr/bin/env python3
"""
OCR Processor - Przetwarzanie OCR dla dokumentów VeriDock
"""

import os
import json
import base64
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    import io
except ImportError:
    logging.error("Brakuje wymaganych bibliotek. Zainstaluj: pip install pytesseract Pillow pdf2image")
    exit(1)


class OCRProcessor:
    """Procesor OCR dla dokumentów VeriDock"""

    def __init__(self):
        self.languages = 'pol+eng'  # Polszczyzna i angielski
        self.dpi = 300  # DPI dla OCR
        self.ocr_config = '--oem 3 --psm 6'  # Konfiguracja Tesseract

        # Sprawdź dostępność Tesseract
        self.check_tesseract()

    def check_tesseract(self):
        """Sprawdza dostępność Tesseract OCR"""
        try:
            pytesseract.get_tesseract_version()
            logging.info("Tesseract OCR dostępny")
        except Exception as e:
            logging.error(f"Tesseract OCR niedostępny: {e}")
            logging.info("Zainstaluj Tesseract: sudo apt-get install tesseract-ocr tesseract-ocr-pol")

    def extract_pdf_from_svg(self, svg_path: str) -> Optional[bytes]:
        """Wyciąga dane PDF z pliku SVG"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Znajdź dane PDF
            pdf_pattern = r'data:application/pdf;base64,([A-Za-z0-9+/=]+)'
            match = re.search(pdf_pattern, svg_content)

            if match:
                pdf_base64 = match.group(1)
                return base64.b64decode(pdf_base64)

            return None

        except Exception as e:
            logging.error(f"Błąd wyciągania PDF ze SVG: {e}")
            return None

    def pdf_to_images_for_ocr(self, pdf_data: bytes) -> List[Image.Image]:
        """Konwertuje PDF na obrazy do OCR"""
        try:
            # Zapisz tymczasowy PDF
            temp_pdf = "/tmp/temp_ocr.pdf"
            with open(temp_pdf, 'wb') as f:
                f.write(pdf_data)

            # Konwertuj na obrazy
            images = convert_from_path(temp_pdf, dpi=self.dpi)

            # Usuń tymczasowy plik
            os.remove(temp_pdf)

            return images

        except Exception as e:
            logging.error(f"Błąd konwersji PDF na obrazy do OCR: {e}")
            return []

    def process_image_ocr(self, image: Image.Image, page_number: int) -> Dict[str, Any]:
        """Przetwarza OCR dla pojedynczego obrazu"""
        try:
            # OCR tekstu
            text = pytesseract.image_to_string(
                image,
                lang=self.languages,
                config=self.ocr_config
            )

            # OCR danych strukturalnych (bounding boxes)
            data = pytesseract.image_to_data(
                image,
                lang=self.languages,
                config=self.ocr_config,
                output_type=pytesseract.Output.DICT
            )

            # Przetwórz dane strukturalne
            words = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 30:  # Poziom pewności > 30%
                    word_data = {
                        'text': data['text'][i].strip(),
                        'confidence': int(data['conf'][i]),
                        'bbox': {
                            'x': int(data['left'][i]),
                            'y': int(data['top'][i]),
                            'width': int(data['width'][i]),
                            'height': int(data['height'][i])
                        }
                    }
                    if word_data['text']:  # Tylko niepuste słowa
                        words.append(word_data)

            return {
                'page': page_number,
                'text': text.strip(),
                'words': words,
                'word_count': len(words),
                'confidence_avg': sum(w['confidence'] for w in words) / len(words) if words else 0,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logging.error(f"Błąd OCR strony {page_number}: {e}")
            return {
                'page': page_number,
                'text': '',
                'words': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def process_pdf_ocr(self, pdf_data: bytes) -> List[Dict[str, Any]]:
        """Przetwarza OCR dla całego PDF"""
        try:
            # Konwertuj PDF na obrazy
            images = self.pdf_to_images_for_ocr(pdf_data)

            if not images:
                logging.error("Nie udało się skonwertować PDF na obrazy")
                return []

            logging.info(f"Rozpoczynam OCR dla {len(images)} stron")

            # Przetwarzaj każdą stronę
            ocr_results = []
            for i, image in enumerate(images):
                logging.info(f"Przetwarzam OCR strony {i + 1}/{len(images)}")
                result = self.process_image_ocr(image, i + 1)
                ocr_results.append(result)

            return ocr_results

        except Exception as e:
            logging.error(f"Błąd przetwarzania OCR PDF: {e}")
            return []

    def update_svg_with_ocr(self, svg_path: str, ocr_results: List[Dict[str, Any]]):
        """Aktualizuje plik SVG z wynikami OCR"""
        try:
            # Wczytaj SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Przygotuj dane OCR jako JSON
            ocr_data = {
                'processing_date': datetime.now().isoformat(),
                'total_pages': len(ocr_results),
                'languages': self.languages,
                'pages': ocr_results,
                'summary': self.generate_ocr_summary(ocr_results)
            }

            ocr_json = json.dumps(ocr_data, ensure_ascii=False, indent=2)

            # Aktualizuj status OCR
            svg_content = re.sub(
                r'<veridock:ocr_status>[^<]*</veridock:ocr_status>',
                '<veridock:ocr_status>completed</veridock:ocr_status>',
                svg_content
            )

            # Aktualizuj dane OCR
            if '<veridock:ocr_data>' in svg_content:
                svg_content = re.sub(
                    r'<veridock:ocr_data>.*?</veridock:ocr_data>',
                    f'<veridock:ocr_data>{ocr_json}</veridock:ocr_data>',
                    svg_content,
                    flags=re.DOTALL
                )
            else:
                # Dodaj dane OCR
                insert_pos = svg_content.find('</veridock:document>')
                if insert_pos != -1:
                    svg_content = (svg_content[:insert_pos] +
                                   f'      <veridock:ocr_data>{ocr_json}</veridock:ocr_data>\n    ' +
                                   svg_content[insert_pos:])

            # Aktualizuj interfejs z informacją o OCR
            svg_content = re.sub(
                r'Status OCR: <tspan fill="#f39c12">Oczekuje</tspan>',
                'Status OCR: <tspan fill="#27ae60">Zakończono</tspan>',
                svg_content
            )

            # Zapisz zaktualizowany SVG
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            logging.info(f"Zaktualizowano SVG z danymi OCR: {svg_path}")

        except Exception as e:
            logging.error(f"Błąd aktualizacji SVG z OCR: {e}")

    def generate_ocr_summary(self, ocr_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generuje podsumowanie wyników OCR"""
        try:
            total_words = sum(result.get('word_count', 0) for result in ocr_results)
            total_chars = sum(len(result.get('text', '')) for result in ocr_results)

            confidences = []
            for result in ocr_results:
                if 'words' in result:
                    confidences.extend(word['confidence'] for word in result['words'])

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Znajdź najczęstsze słowa
            all_words = []
            for result in ocr_results:
                if 'words' in result:
                    all_words.extend(word['text'].lower() for word in result['words']
                                     if len(word['text']) > 3)  # Słowa dłuższe niż 3 znaki

            word_freq = {}
            for word in all_words:
                word_freq[word] = word_freq.get(word, 0) + 1

            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                'total_pages': len(ocr_results),
                'total_words': total_words,
                'total_characters': total_chars,
                'average_confidence': round(avg_confidence, 2),
                'pages_with_text': len([r for r in ocr_results if r.get('text', '').strip()]),
                'top_words': top_words,
                'languages_detected': self.languages
            }

        except Exception as e:
            logging.error(f"Błąd generowania podsumowania OCR: {e}")
            return {}

    def process_svg(self, svg_path: str) -> bool:
        """Główna funkcja przetwarzania OCR dla pliku SVG"""
        try:
            logging.info(f"Rozpoczynam przetwarzanie OCR: {svg_path}")

            # Sprawdź czy OCR już został wykonany
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            if 'ocr_status>completed</veridock:ocr_status>' in svg_content:
                logging.info("OCR już wykonany dla tego pliku")
                return True

            # Wyciągnij PDF
            pdf_data = self.extract_pdf_from_svg(svg_path)
            if not pdf_data:
                logging.error("Nie udało się wyciągnąć PDF ze SVG")
                return False

            # Przetwórz OCR
            ocr_results = self.process_pdf_ocr(pdf_data)
            if not ocr_results:
                logging.error("Nie udało się przetworzyć OCR")
                return False

            # Aktualizuj SVG
            self.update_svg_with_ocr(svg_path, ocr_results)

            logging.info(f"Zakończono przetwarzanie OCR: {svg_path}")
            return True

        except Exception as e:
            logging.error(f"Błąd przetwarzania OCR: {e}")
            return False

    def export_ocr_text(self, svg_path: str, output_format: str = 'txt') -> Optional[str]:
        """Eksportuje tekst OCR do pliku"""
        try:
            # Wczytaj dane OCR ze SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Znajdź dane OCR
            ocr_pattern = r'<veridock:ocr_data>(.*?)</veridock:ocr_data>'
            match = re.search(ocr_pattern, svg_content, re.DOTALL)

            if not match:
                logging.error("Nie znaleziono danych OCR w SVG")
                return None

            ocr_data = json.loads(match.group(1))

            # Przygotuj nazwę pliku wyjściowego
            base_name = os.path.splitext(svg_path)[0]

            if output_format == 'txt':
                output_path = f"{base_name}_ocr.txt"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"VeriDock OCR Export\n")
                    f.write(f"Data przetwarzania: {ocr_data.get('processing_date', '')}\n")
                    f.write(f"Języki: {ocr_data.get('languages', '')}\n")
                    f.write(f"Łączna liczba stron: {ocr_data.get('total_pages', 0)}\n")
                    f.write("=" * 50 + "\n\n")

                    for page_data in ocr_data.get('pages', []):
                        f.write(f"STRONA {page_data.get('page', '?')}\n")
                        f.write("-" * 20 + "\n")
                        f.write(page_data.get('text', '') + "\n\n")

            elif output_format == 'json':
                output_path = f"{base_name}_ocr.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(ocr_data, f, ensure_ascii=False, indent=2)

            else:
                logging.error(f"Nieobsługiwany format: {output_format}")
                return None

            logging.info(f"Wyeksportowano OCR do: {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Błąd eksportu OCR: {e}")
            return None


def main():
    """Funkcja główna dla testowania"""
    import sys

    if len(sys.argv) < 2:
        print("Użycie: python ocr_processor.py <ścieżka_do_svg> [export_format]")
        sys.exit(1)

    svg_path = sys.argv[1]
    processor = OCRProcessor()

    if len(sys.argv) == 3 and sys.argv[2] in ['export_txt', 'export_json']:
        # Eksport OCR
        format_type = sys.argv[2].replace('export_', '')
        result = processor.export_ocr_text(svg_path, format_type)
        if result:
            print(f"Wyeksportowano OCR: {result}")
    else:
        # Przetwarzanie OCR
        result = processor.process_svg(svg_path)
        if result:
            print("Przetwarzanie OCR zakończone sukcesem")
        else:
            print("Błąd przetwarzania OCR")


if __name__ == "__main__":
    main()