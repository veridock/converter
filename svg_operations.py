#!/usr/bin/env python3
"""
SVG Operations - Operacje na plikach SVG VeriDock
"""

import os
import json
import base64
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging


class SVGOperations:
    """Klasa do operacji na plikach SVG VeriDock"""

    def __init__(self):
        pass

    def extract_pdf_from_svg(self, svg_path: str, output_path: str = None) -> Optional[str]:
        """Wyciąga PDF z pliku SVG i zapisuje go"""
        try:
            if not os.path.exists(svg_path):
                logging.error(f"Plik SVG nie istnieje: {svg_path}")
                return None

            # Wczytaj SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Znajdź dane PDF
            pdf_pattern = r'data:application/pdf;base64,([A-Za-z0-9+/=]+)'
            match = re.search(pdf_pattern, svg_content)

            if not match:
                logging.error("Nie znaleziono danych PDF w SVG")
                return None

            # Dekoduj PDF
            pdf_base64 = match.group(1)
            pdf_data = base64.b64decode(pdf_base64)

            # Określ ścieżkę wyjściową
            if output_path is None:
                base_name = os.path.splitext(svg_path)[0]
                output_path = f"{base_name}_extracted.pdf"

            # Zapisz PDF
            with open(output_path, 'wb') as f:
                f.write(pdf_data)

            logging.info(f"Wyciągnięto PDF ze SVG: {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"Błąd wyciągania PDF ze SVG: {e}")
            return None

    def get_svg_metadata(self, svg_path: str) -> Optional[Dict[str, Any]]:
        """Pobiera metadane z pliku SVG"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            metadata = {}

            # Pobierz metadane dokumentu
            patterns = {
                'filename': r'<veridock:filename>([^<]+)</veridock:filename>',
                'creation_time': r'<veridock:creation_time>([^<]+)</veridock:creation_time>',
                'pages': r'<veridock:pages>([^<]+)</veridock:pages>',
                'ocr_status': r'<veridock:ocr_status>([^<]+)</veridock:ocr_status>',
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, svg_content)
                if match:
                    metadata[key] = match.group(1)

            # Pobierz metadane PDF
            pdf_metadata_pattern = r'<veridock:pdf_metadata>([^<]+)</veridock:pdf_metadata>'
            match = re.search(pdf_metadata_pattern, svg_content)
            if match:
                try:
                    metadata['pdf_metadata'] = json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Sprawdź czy są dane OCR
            if '<veridock:ocr_data>' in svg_content:
                ocr_pattern = r'<veridock:ocr_data>(.*?)</veridock:ocr_data>'
                match = re.search(ocr_pattern, svg_content, re.DOTALL)
                if match:
                    try:
                        ocr_data = json.loads(match.group(1))
                        metadata['ocr_summary'] = ocr_data.get('summary', {})
                        metadata['ocr_processing_date'] = ocr_data.get('processing_date', '')
                    except json.JSONDecodeError:
                        pass

            return metadata

        except Exception as e:
            logging.error(f"Błąd pobierania metadanych SVG: {e}")
            return None

    def update_svg_metadata(self, svg_path: str, new_metadata: Dict[str, Any]) -> bool:
        """Aktualizuje metadane w pliku SVG"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Aktualizuj poszczególne pola metadanych
            for key, value in new_metadata.items():
                if key in ['filename', 'creation_time', 'pages', 'ocr_status']:
                    pattern = f'<veridock:{key}>[^<]*</veridock:{key}>'
                    replacement = f'<veridock:{key}>{value}</veridock:{key}>'
                    svg_content = re.sub(pattern, replacement, svg_content)

            # Zapisz zaktualizowany SVG
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            logging.info(f"Zaktualizowano metadane SVG: {svg_path}")
            return True

        except Exception as e:
            logging.error(f"Błąd aktualizacji metadanych SVG: {e}")
            return False

    def export_svg_data(self, svg_path: str, export_type: str = 'all') -> Optional[str]:
        """Eksportuje dane z SVG do pliku JSON"""
        try:
            metadata = self.get_svg_metadata(svg_path)
            if not metadata:
                return None

            # Wczytaj pełne dane SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'source_file': svg_path,
                'metadata': metadata
            }

            if export_type in ['all', 'ocr']:
                # Dodaj pełne dane OCR
                ocr_pattern = r'<veridock:ocr_data>(.*?)</veridock:ocr_data>'
                match = re.search(ocr_pattern, svg_content, re.DOTALL)
                if match:
                    try:
                        export_data['ocr_data'] = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        pass

            if export_type in ['all', 'thumbnails']:
                # Dodaj metadane miniaturek
                thumbnail_pattern = r'<veridock:thumbnail_metadata>(.*?)</veridock:thumbnail_metadata>'
                match = re.search(thumbnail_pattern, svg_content, re.DOTALL)
                if match:
                    try:
                        export_data['thumbnail_metadata'] = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        pass

            # Zapisz dane eksportu
            base_name = os.path.splitext(svg_path)[0]
            export_path = f"{base_name}_export_{export_type}.json"

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logging.info(f"Wyeksportowano dane SVG: {export_path}")
            return export_path

        except Exception as e:
            logging.error(f"Błąd eksportu danych SVG: {e}")
            return None

    def import_svg_data(self, svg_path: str, import_file: str) -> bool:
        """Importuje dane do pliku SVG z pliku JSON"""
        try:
            # Wczytaj dane do importu
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # Wczytaj SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Importuj dane OCR jeśli są dostępne
            if 'ocr_data' in import_data:
                ocr_json = json.dumps(import_data['ocr_data'], ensure_ascii=False, indent=2)

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

                # Aktualizuj status OCR
                svg_content = re.sub(
                    r'<veridock:ocr_status>[^<]*</veridock:ocr_status>',
                    '<veridock:ocr_status>completed</veridock:ocr_status>',
                    svg_content
                )

            # Importuj metadane miniaturek jeśli są dostępne
            if 'thumbnail_metadata' in import_data:
                thumb_json = json.dumps(import_data['thumbnail_metadata'], ensure_ascii=False, indent=2)

                if '<veridock:thumbnail_metadata>' in svg_content:
                    svg_content = re.sub(
                        r'<veridock:thumbnail_metadata>.*?</veridock:thumbnail_metadata>',
                        f'<veridock:thumbnail_metadata>{thumb_json}</veridock:thumbnail_metadata>',
                        svg_content,
                        flags=re.DOTALL
                    )
                else:
                    # Dodaj metadane miniaturek
                    insert_pos = svg_content.find('</veridock:document>')
                    if insert_pos != -1:
                        svg_content = (svg_content[:insert_pos] +
                                       f'      <veridock:thumbnail_metadata>{thumb_json}</veridock:thumbnail_metadata>\n    ' +
                                       svg_content[insert_pos:])

            # Zapisz zaktualizowany SVG
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            logging.info(f"Zaimportowano dane do SVG: {svg_path}")
            return True

        except Exception as e:
            logging.error(f"Błąd importu danych do SVG: {e}")
            return False

    def validate_svg(self, svg_path: str) -> Dict[str, Any]:
        """Waliduje plik SVG VeriDock"""
        try:
            validation_result = {
                'valid': False,
                'errors': [],
                'warnings': [],
                'metadata': {}
            }

            if not os.path.exists(svg_path):
                validation_result['errors'].append("Plik nie istnieje")
                return validation_result

            # Wczytaj SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Sprawdź podstawową strukturę
            if 'xmlns:veridock="http://veridock.com/ns"' not in svg_content:
                validation_result['errors'].append("Brak namespace VeriDock")

            if '<veridock:document>' not in svg_content:
                validation_result['errors'].append("Brak sekcji metadanych dokumentu")

            if '<veridock:pdf_data' not in svg_content:
                validation_result['errors'].append("Brak osadzonych danych PDF")

            # Sprawdź metadane
            required_fields = ['filename', 'creation_time', 'pages']
            for field in required_fields:
                pattern = f'<veridock:{field}>[^<]+</veridock:{field}>'
                if not re.search(pattern, svg_content):
                    validation_result['errors'].append(f"Brak wymaganego pola: {field}")

            # Sprawdź dane PDF
            pdf_pattern = r'data:application/pdf;base64,([A-Za-z0-9+/=]+)'
            match = re.search(pdf_pattern, svg_content)
            if match:
                try:
                    pdf_data = base64.b64decode(match.group(1))
                    if len(pdf_data) < 100:  # Minimalny rozmiar PDF
                        validation_result['warnings'].append("Podejrzanie mały rozmiar PDF")
                except Exception:
                    validation_result['errors'].append("Nieprawidłowe dane PDF base64")

            # Sprawdź status OCR
            ocr_status_pattern = r'<veridock:ocr_status>([^<]+)</veridock:ocr_status>'
            match = re.search(ocr_status_pattern, svg_content)
            if match:
                ocr_status = match.group(1)
                if ocr_status == 'completed':
                    if '<veridock:ocr_data>' not in svg_content:
                        validation_result['warnings'].append("Status OCR = completed, ale brak danych OCR")

            # Pobierz metadane do wyniku
            validation_result['metadata'] = self.get_svg_metadata(svg_path) or {}

            # Określ czy plik jest prawidłowy
            validation_result['valid'] = len(validation_result['errors']) == 0

            return validation_result

        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Błąd walidacji: {e}"],
                'warnings': [],
                'metadata': {}
            }

    def list_svg_files(self, directory: str) -> List[Dict[str, Any]]:
        """Listuje wszystkie pliki SVG w katalogu z metadanami"""
        try:
            svg_files = []

            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.svg'):
                        svg_path = os.path.join(root, file)

                        # Pobierz podstawowe informacje o pliku
                        file_stat = os.stat(svg_path)
                        file_info = {
                            'path': svg_path,
                            'filename': file,
                            'size': file_stat.st_size,
                            'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                            'is_veridock': False,
                            'metadata': {}
                        }

                        # Sprawdź czy to plik VeriDock
                        try:
                            with open(svg_path, 'r', encoding='utf-8') as f:
                                content = f.read(1000)  # Pierwszych 1000 znaków
                                if 'xmlns:veridock=' in content:
                                    file_info['is_veridock'] = True
                                    file_info['metadata'] = self.get_svg_metadata(svg_path) or {}
                        except Exception:
                            pass  # Ignoruj błędy odczytu

                        svg_files.append(file_info)

            return sorted(svg_files, key=lambda x: x['modified'], reverse=True)

        except Exception as e:
            logging.error(f"Błąd listowania plików SVG: {e}")
            return []

    def cleanup_svg(self, svg_path: str) -> bool:
        """Czyści i optymalizuje plik SVG"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Usuń nadmiarowe białe znaki
            svg_content = re.sub(r'\n\s*\n', '\n', svg_content)
            svg_content = re.sub(r'  +', ' ', svg_content)

            # Zapisz oczyszczony plik
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            logging.info(f"Oczyszczono plik SVG: {svg_path}")
            return True

        except Exception as e:
            logging.error(f"Błąd czyszczenia SVG: {e}")
            return False


def main():
    """Funkcja główna dla testowania"""
    import sys

    if len(sys.argv) < 3:
        print("Użycie: python svg_operations.py <operacja> <ścieżka_svg> [dodatkowe_parametry]")
        print("Operacje:")
        print("  extract_pdf <svg_path> [output_path]")
        print("  get_metadata <svg_path>")
        print("  validate <svg_path>")
        print("  export_data <svg_path> [all|ocr|thumbnails]")
        print("  import_data <svg_path> <import_file>")
        print("  list_directory <directory_path>")
        print("  cleanup <svg_path>")
        sys.exit(1)

    operation = sys.argv[1]
    svg_ops = SVGOperations()

    if operation == "extract_pdf":
        svg_path = sys.argv[2]
        output_path = sys.argv[3] if len(sys.argv) > 3 else None
        result = svg_ops.extract_pdf_from_svg(svg_path, output_path)
        if result:
            print(f"PDF wyciągnięty: {result}")
        else:
            print("Błąd wyciągania PDF")

    elif operation == "get_metadata":
        svg_path = sys.argv[2]
        metadata = svg_ops.get_svg_metadata(svg_path)
        if metadata:
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
        else:
            print("Błąd pobierania metadanych")

    elif operation == "validate":
        svg_path = sys.argv[2]
        result = svg_ops.validate_svg(svg_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif operation == "export_data":
        svg_path = sys.argv[2]
        export_type = sys.argv[3] if len(sys.argv) > 3 else 'all'
        result = svg_ops.export_svg_data(svg_path, export_type)
        if result:
            print(f"Dane wyeksportowane: {result}")
        else:
            print("Błąd eksportu danych")

    elif operation == "import_data":
        if len(sys.argv) < 4:
            print("Brak pliku do importu")
            sys.exit(1)
        svg_path = sys.argv[2]
        import_file = sys.argv[3]
        result = svg_ops.import_svg_data(svg_path, import_file)
        if result:
            print("Dane zaimportowane pomyślnie")
        else:
            print("Błąd importu danych")

    elif operation == "list_directory":
        directory = sys.argv[2]
        files = svg_ops.list_svg_files(directory)
        for file_info in files:
            print(f"{file_info['filename']} - VeriDock: {file_info['is_veridock']} - "
                  f"Rozmiar: {file_info['size']} B - Modyfikacja: {file_info['modified']}")

    elif operation == "cleanup":
        svg_path = sys.argv[2]
        result = svg_ops.cleanup_svg(svg_path)
        if result:
            print("Plik oczyszczony")
        else:
            print("Błąd czyszczenia pliku")

    else:
        print(f"Nieznana operacja: {operation}")


if __name__ == "__main__":
    main()