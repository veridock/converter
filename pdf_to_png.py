#!/usr/bin/env python3
"""
PDF to PNG Converter - Generowanie obrazów PNG z PDF
"""

import os
import base64
import json
from pathlib import Path
from typing import List, Optional, Tuple
import logging

try:
    from pdf2image import convert_from_path
    from PIL import Image
    import io
except ImportError:
    logging.error("Brakuje wymaganych bibliotek. Zainstaluj: pip install pdf2image Pillow")
    exit(1)


class PDFToPNGConverter:
    """Konwerter PDF na obrazy PNG"""

    def __init__(self):
        self.dpi = 200  # DPI dla konwersji
        self.thumbnail_size = (150, 200)  # Rozmiar miniaturek
        self.full_size_dpi = 300  # DPI dla pełnowymiarowych obrazów

    def convert_pdf_to_images(self, pdf_path: str, dpi: int = None) -> List[Image.Image]:
        """Konwertuje PDF na listę obrazów PIL"""
        try:
            if dpi is None:
                dpi = self.dpi

            images = convert_from_path(pdf_path, dpi=dpi)
            logging.info(f"Skonwertowano {len(images)} stron z PDF")
            return images

        except Exception as e:
            logging.error(f"Błąd konwersji PDF na obrazy: {e}")
            return []

    def save_individual_pages(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """Zapisuje każdą stronę jako osobny plik PNG"""
        try:
            if output_dir is None:
                output_dir = os.path.dirname(pdf_path)

            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

            # Utwórz folder dla stron
            pages_dir = os.path.join(output_dir, f"{pdf_name}_pages")
            os.makedirs(pages_dir, exist_ok=True)

            # Konwertuj PDF na obrazy
            images = self.convert_pdf_to_images(pdf_path, self.full_size_dpi)

            saved_files = []
            for i, img in enumerate(images):
                page_path = os.path.join(pages_dir, f"page_{i + 1:03d}.png")
                img.save(page_path, 'PNG', optimize=True)
                saved_files.append(page_path)
                logging.info(f"Zapisano stronę {i + 1}: {page_path}")

            return saved_files

        except Exception as e:
            logging.error(f"Błąd zapisywania stron: {e}")
            return []

    def create_thumbnail_matrix(self, pdf_path: str, max_cols: int = 4) -> Optional[Tuple[str, dict]]:
        """Tworzy matrycę miniaturek i zwraca base64 + metadane"""
        try:
            # Konwertuj PDF na obrazy
            images = self.convert_pdf_to_images(pdf_path)

            if not images:
                return None

            # Przygotuj miniaturki
            thumbnails = []
            for img in images:
                img_thumb = img.copy()
                img_thumb.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                thumbnails.append(img_thumb)

            # Oblicz wymiary gridu
            cols = min(max_cols, len(thumbnails))
            rows = (len(thumbnails) + cols - 1) // cols

            # Utwórz matrycę
            matrix_width = cols * self.thumbnail_size[0]
            matrix_height = rows * self.thumbnail_size[1]

            matrix_image = Image.new('RGB', (matrix_width, matrix_height), 'white')

            # Umieść miniaturki w matrycy
            page_positions = []
            for i, thumb in enumerate(thumbnails):
                col = i % cols
                row = i // cols
                x = col * self.thumbnail_size[0]
                y = row * self.thumbnail_size[1]

                matrix_image.paste(thumb, (x, y))

                # Zapisz pozycję strony
                page_positions.append({
                    'page': i + 1,
                    'x': x,
                    'y': y,
                    'width': self.thumbnail_size[0],
                    'height': self.thumbnail_size[1]
                })

            # Konwertuj na base64
            buffer = io.BytesIO()
            matrix_image.save(buffer, format='PNG')
            matrix_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Metadane matrycy
            metadata = {
                'total_pages': len(thumbnails),
                'matrix_cols': cols,
                'matrix_rows': rows,
                'thumbnail_size': self.thumbnail_size,
                'page_positions': page_positions
            }

            return matrix_base64, metadata

        except Exception as e:
            logging.error(f"Błąd tworzenia matrycy miniaturek: {e}")
            return None

    def generate_thumbnails(self, pdf_path: str, svg_path: str = None) -> bool:
        """Generuje miniaturki i aktualizuje plik SVG"""
        try:
            # Utwórz matrycę miniaturek
            result = self.create_thumbnail_matrix(pdf_path)
            if not result:
                return False

            matrix_base64, metadata = result

            # Jeśli podano ścieżkę SVG, zaktualizuj plik
            if svg_path and os.path.exists(svg_path):
                self.update_svg_thumbnails(svg_path, matrix_base64, metadata)

            # Zapisz również poszczególne strony
            saved_pages = self.save_individual_pages(pdf_path)

            logging.info(f"Wygenerowano miniaturki dla {pdf_path}")
            return True

        except Exception as e:
            logging.error(f"Błąd generowania miniaturek: {e}")
            return False

    def update_svg_thumbnails(self, svg_path: str, matrix_base64: str, metadata: dict):
        """Aktualizuje plik SVG z nowymi miniaturkami"""
        try:
            # Wczytaj SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Aktualizuj dane miniaturek
            old_pattern = r'<veridock:thumbnail_grid id="thumbnail_grid">[^<]*</veridock:thumbnail_grid>'
            new_content = f'<veridock:thumbnail_grid id="thumbnail_grid">data:image/png;base64,{matrix_base64}</veridock:thumbnail_grid>'

            import re
            svg_content = re.sub(old_pattern, new_content, svg_content)

            # Aktualizuj metadane miniaturek
            metadata_json = json.dumps(metadata, indent=2)
            metadata_pattern = r'<veridock:thumbnail_metadata>.*?</veridock:thumbnail_metadata>'
            metadata_content = f'<veridock:thumbnail_metadata>{metadata_json}</veridock:thumbnail_metadata>'

            if '<veridock:thumbnail_metadata>' in svg_content:
                svg_content = re.sub(metadata_pattern, metadata_content, svg_content, flags=re.DOTALL)
            else:
                # Dodaj metadane miniaturek do sekcji metadata
                insert_pos = svg_content.find('</veridock:document>')
                if insert_pos != -1:
                    svg_content = (svg_content[:insert_pos] +
                                   f'      {metadata_content}\n    ' +
                                   svg_content[insert_pos:])

            # Aktualizuj obraz miniaturek w interfejsie
            image_pattern = r'<image[^>]*href="data:image/png;base64,[^"]*"[^>]*>'
            new_image = f'<image x="30" y="150" width="340" height="300" href="data:image/png;base64,{matrix_base64}" style="object-fit: contain"/>'
            svg_content = re.sub(image_pattern, new_image, svg_content)

            # Zapisz zaktualizowany SVG
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            logging.info(f"Zaktualizowano miniaturki w SVG: {svg_path}")

        except Exception as e:
            logging.error(f"Błąd aktualizacji SVG: {e}")

    def extract_png_from_svg(self, svg_path: str, page_number: int) -> Optional[str]:
        """Wyciąga określoną stronę PNG z SVG"""
        try:
            # Pobierz oryginalny PDF z SVG
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Znajdź dane PDF
            import re
            pdf_pattern = r'data:application/pdf;base64,([A-Za-z0-9+/=]+)'
            match = re.search(pdf_pattern, svg_content)

            if not match:
                logging.error("Nie znaleziono danych PDF w SVG")
                return None

            pdf_base64 = match.group(1)
            pdf_data = base64.b64decode(pdf_base64)

            # Zapisz tymczasowy PDF
            temp_pdf = f"/tmp/temp_{os.path.basename(svg_path)}.pdf"
            with open(temp_pdf, 'wb') as f:
                f.write(pdf_data)

            # Konwertuj określoną stronę
            try:
                images = convert_from_path(temp_pdf,
                                           dpi=self.full_size_dpi,
                                           first_page=page_number,
                                           last_page=page_number)

                if images:
                    # Zapisz jako PNG
                    output_path = svg_path.replace('.svg', f'_page_{page_number}.png')
                    images[0].save(output_path, 'PNG')

                    # Usuń tymczasowy PDF
                    os.remove(temp_pdf)

                    return output_path

            except Exception as e:
                logging.error(f"Błąd konwersji strony {page_number}: {e}")

            # Usuń tymczasowy PDF w przypadku błędu
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)

        except Exception as e:
            logging.error(f"Błąd wyciągania PNG ze SVG: {e}")

        return None


def main():
    """Funkcja główna dla testowania"""
    import sys

    if len(sys.argv) < 2:
        print("Użycie: python pdf_to_png.py <ścieżka_do_pdf> [numer_strony]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    converter = PDFToPNGConverter()

    if len(sys.argv) == 3:
        # Konwertuj określoną stronę
        page_num = int(sys.argv[2])
        svg_path = pdf_path.replace('.pdf', '.svg')
        result = converter.extract_png_from_svg(svg_path, page_num)
        if result:
            print(f"Wyciągnięto stronę {page_num}: {result}")
    else:
        # Wygeneruj wszystkie miniaturki
        result = converter.generate_thumbnails(pdf_path)
        if result:
            print("Wygenerowano miniaturki pomyślnie")
        else:
            print("Błąd generowania miniaturek")


if __name__ == "__main__":
    main()