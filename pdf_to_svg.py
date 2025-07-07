#!/usr/bin/env python3
"""
PDF to SVG Converter - Konwersja PDF na SVG z osadzonymi danymi
"""

import os
import base64
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

try:
    from pdf2image import convert_from_path
    from PIL import Image
    import io
except ImportError:
    logging.error("Brakuje wymaganych bibliotek. Zainstaluj: pip install pdf2image Pillow")
    exit(1)


class PDFToSVGConverter:
    """Konwerter PDF na SVG z osadzonymi metadanymi"""

    def __init__(self):
        self.dpi = 150  # DPI dla konwersji
        self.thumbnail_size = (200, 280)  # Rozmiar miniaturek

    def pdf_to_base64(self, pdf_path: str) -> str:
        """Konwertuje PDF na base64 string"""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
                return base64.b64encode(pdf_data).decode('utf-8')
        except Exception as e:
            logging.error(f"Błąd konwersji PDF na base64: {e}")
            return ""

    def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Pobiera metadane z pliku PDF"""
        try:
            from PyPDF2 import PdfReader

            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                info = pdf_reader.metadata

                metadata = {
                    'title': info.get('/Title', ''),
                    'author': info.get('/Author', ''),
                    'creator': info.get('/Creator', ''),
                    'producer': info.get('/Producer', ''),
                    'creation_date': str(info.get('/CreationDate', '')),
                    'modification_date': str(info.get('/ModDate', '')),
                    'pages': len(pdf_reader.pages)
                }

                return metadata
        except Exception as e:
            logging.warning(f"Nie można pobrać metadanych PDF: {e}")
            return {'pages': 0}

    def generate_thumbnail_grid(self, pdf_path: str) -> Optional[str]:
        """Generuje grid miniaturek wszystkich stron jako base64"""
        try:
            # Konwertuj PDF na obrazy
            images = convert_from_path(pdf_path, dpi=self.dpi)

            if not images:
                return None

            # Przygotuj miniaturki
            thumbnails = []
            for img in images:
                img_thumb = img.copy()
                img_thumb.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                thumbnails.append(img_thumb)

            # Oblicz wymiary gridu
            cols = min(4, len(thumbnails))  # Maksymalnie 4 kolumny
            rows = (len(thumbnails) + cols - 1) // cols

            # Utwórz grid
            grid_width = cols * self.thumbnail_size[0]
            grid_height = rows * self.thumbnail_size[1]

            grid_image = Image.new('RGB', (grid_width, grid_height), 'white')

            for i, thumb in enumerate(thumbnails):
                col = i % cols
                row = i // cols
                x = col * self.thumbnail_size[0]
                y = row * self.thumbnail_size[1]
                grid_image.paste(thumb, (x, y))

            # Konwertuj na base64
            buffer = io.BytesIO()
            grid_image.save(buffer, format='PNG')
            grid_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            return grid_base64

        except Exception as e:
            logging.error(f"Błąd generowania miniaturek: {e}")
            return None

    def create_svg_template(self, pdf_path: str, pdf_base64: str,
                            thumbnail_grid: str, metadata: Dict[str, Any]) -> str:
        """Tworzy szablon SVG z osadzonymi danymi"""

        filename = os.path.basename(pdf_path)
        creation_time = datetime.now().isoformat()

        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:veridock="http://veridock.com/ns"
     width="800" height="600" viewBox="0 0 800 600">

  <!-- VeriDock Metadata -->
  <metadata>
    <veridock:document>
      <veridock:filename>{filename}</veridock:filename>
      <veridock:creation_time>{creation_time}</veridock:creation_time>
      <veridock:pages>{metadata.get('pages', 0)}</veridock:pages>
      <veridock:pdf_metadata>{json.dumps(metadata)}</veridock:pdf_metadata>
      <veridock:ocr_status>pending</veridock:ocr_status>
      <veridock:ocr_data></veridock:ocr_data>
    </veridock:document>
  </metadata>

  <!-- Osadzony PDF jako data URI -->
  <defs>
    <veridock:pdf_data id="original_pdf">
      data:application/pdf;base64,{pdf_base64}
    </veridock:pdf_data>

    <!-- Grid miniaturek -->
    <veridock:thumbnail_grid id="thumbnail_grid">
      data:image/png;base64,{thumbnail_grid}
    </veridock:thumbnail_grid>
  </defs>

  <!-- Interfejs SVG -->
  <rect width="800" height="600" fill="#f5f5f5" stroke="#ddd" stroke-width="1"/>

  <!-- Nagłówek -->
  <rect x="0" y="0" width="800" height="80" fill="#2c3e50"/>
  <text x="20" y="30" fill="white" font-family="Arial" font-size="18" font-weight="bold">
    VeriDock Document
  </text>
  <text x="20" y="55" fill="#ecf0f1" font-family="Arial" font-size="12">
    {filename} • {metadata.get('pages', 0)} stron • {creation_time[:10]}
  </text>

  <!-- Miniaturki -->
  <g id="thumbnail_display">
    <rect x="20" y="100" width="360" height="480" fill="white" stroke="#bdc3c7" stroke-width="1"/>
    <text x="200" y="130" text-anchor="middle" font-family="Arial" font-size="14" fill="#7f8c8d">
      Miniaturki stron
    </text>

    <!-- Tutaj będą wyświetlane miniaturki -->
    <image x="30" y="150" width="340" height="300" 
           href="data:image/png;base64,{thumbnail_grid}"
           style="object-fit: contain"/>
  </g>

  <!-- Panel kontrolny -->
  <g id="control_panel">
    <rect x="400" y="100" width="380" height="480" fill="white" stroke="#bdc3c7" stroke-width="1"/>
    <text x="590" y="130" text-anchor="middle" font-family="Arial" font-size="14" fill="#2c3e50">
      Opcje dokumentu
    </text>

    <!-- Przyciski -->
    <rect x="420" y="150" width="100" height="30" fill="#3498db" rx="5"/>
    <text x="470" y="170" text-anchor="middle" fill="white" font-family="Arial" font-size="12">
      Otwórz PDF
    </text>

    <rect x="540" y="150" width="100" height="30" fill="#27ae60" rx="5"/>
    <text x="590" y="170" text-anchor="middle" fill="white" font-family="Arial" font-size="12">
      Eksportuj OCR
    </text>

    <rect x="660" y="150" width="100" height="30" fill="#e74c3c" rx="5"/>
    <text x="710" y="170" text-anchor="middle" fill="white" font-family="Arial" font-size="12">
      Usuń
    </text>

    <!-- Informacje -->
    <text x="420" y="220" font-family="Arial" font-size="11" fill="#7f8c8d">
      Status OCR: <tspan fill="#f39c12">Oczekuje</tspan>
    </text>
    <text x="420" y="240" font-family="Arial" font-size="11" fill="#7f8c8d">
      Ostatnia aktualizacja: {creation_time[:16]}
    </text>
  </g>

  <!-- JavaScript dla interakcji -->
  <script type="text/javascript">
    <![CDATA[
      function openPDF() {{
        const pdfData = document.getElementById('original_pdf').textContent;
        const blob = new Blob([atob(pdfData.split(',')[1])], {{type: 'application/pdf'}});
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      }}

      function exportOCR() {{
        const ocrData = document.querySelector('veridock\\:ocr_data').textContent;
        if (ocrData) {{
          const blob = new Blob([ocrData], {{type: 'text/plain'}});
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = '{filename}_ocr.txt';
          a.click();
        }} else {{
          alert('OCR jeszcze nie został przetworzony');
        }}
      }}

      document.addEventListener('DOMContentLoaded', function() {{
        const openBtn = document.querySelector('rect[fill="#3498db"]');
        const exportBtn = document.querySelector('rect[fill="#27ae60"]');

        if (openBtn) openBtn.addEventListener('click', openPDF);
        if (exportBtn) exportBtn.addEventListener('click', exportOCR);
      }});
    ]]>
  </script>

</svg>'''

        return svg_content

    def convert(self, pdf_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """Główna funkcja konwersji PDF na SVG"""
        try:
            if not os.path.exists(pdf_path):
                logging.error(f"Plik PDF nie istnieje: {pdf_path}")
                return None

            # Określ ścieżkę wyjściową
            if output_dir is None:
                output_dir = os.path.dirname(pdf_path)

            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            svg_path = os.path.join(output_dir, f"{pdf_name}.svg")

            logging.info(f"Konwersja PDF na SVG: {pdf_path} -> {svg_path}")

            # Pobierz metadane
            metadata = self.get_pdf_metadata(pdf_path)

            # Konwertuj PDF na base64
            pdf_base64 = self.pdf_to_base64(pdf_path)
            if not pdf_base64:
                logging.error("Nie udało się skonwertować PDF na base64")
                return None

            # Wygeneruj grid miniaturek
            thumbnail_grid = self.generate_thumbnail_grid(pdf_path)
            if not thumbnail_grid:
                logging.error("Nie udało się wygenerować miniaturek")
                return None

            # Utwórz SVG
            svg_content = self.create_svg_template(
                pdf_path, pdf_base64, thumbnail_grid, metadata
            )

            # Zapisz SVG
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)

            logging.info(f"Utworzono plik SVG: {svg_path}")
            return svg_path

        except Exception as e:
            logging.error(f"Błąd konwersji PDF na SVG: {e}")
            return None


def main():
    """Funkcja główna dla testowania"""
    import sys

    if len(sys.argv) != 2:
        print("Użycie: python pdf_to_svg.py <ścieżka_do_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    converter = PDFToSVGConverter()
    result = converter.convert(pdf_path)

    if result:
        print(f"Konwersja zakończona sukcesem: {result}")
    else:
        print("Konwersja nie powiodła się")


if __name__ == "__main__":
    main()