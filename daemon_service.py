#!/usr/bin/env python3
"""
VeriDock Daemon Service - Demon systemowy do monitorowania plików
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from typing import Set
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    logging.error("Brakuje biblioteki watchdog. Zainstaluj: pip install watchdog")
    sys.exit(1)

# Import modułów VeriDock
from veridock_converter import VeriDockConverter


class VeriDockFileHandler(FileSystemEventHandler):
    """Handler do obsługi zdarzeń systemu plików"""

    def __init__(self, converter: VeriDockConverter):
        super().__init__()
        self.converter = converter
        self.processing_files: Set[str] = set()

    def on_created(self, event):
        """Obsługuje utworzenie nowego pliku"""
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            self.process_pdf_file(event.src_path)

    def on_moved(self, event):
        """Obsługuje przeniesienie pliku"""
        if not event.is_directory and event.dest_path.lower().endswith('.pdf'):
            self.process_pdf_file(event.dest_path)

    def process_pdf_file(self, file_path: str):
        """Przetwarza plik PDF"""
        try:
            # Sprawdź czy plik nie jest już przetwarzany
            if file_path in self.processing_files:
                return

            # Poczekaj aż plik będzie w pełni zapisany
            self.wait_for_file_complete(file_path)

            # Dodaj do przetwarzanych
            self.processing_files.add(file_path)

            logging.info(f"Wykryto nowy plik PDF: {file_path}")

            # Przetwórz plik
            success = self.converter.process_pdf(file_path)

            if success:
                logging.info(f"Pomyślnie przetworzono: {file_path}")
            else:
                logging.error(f"Błąd przetwarzania: {file_path}")

            # Usuń z przetwarzanych
            self.processing_files.discard(file_path)

        except Exception as e:
            logging.error(f"Błąd obsługi pliku {file_path}: {e}")
            self.processing_files.discard(file_path)

    def wait_for_file_complete(self, file_path: str, timeout: int = 30):
        """Czeka aż plik będzie w pełni zapisany"""
        start_time = time.time()
        last_size = 0

        while time.time() - start_time < timeout:
            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    # Plik przestał rosnąć
                    time.sleep(1)  # Dodatkowe opóźnienie dla pewności
                    return
                last_size = current_size
                time.sleep(0.5)
            except (OSError, FileNotFoundError):
                time.sleep(0.5)
                continue

        logging.warning(f"Timeout oczekiwania na zakończenie zapisu: {file_path}")


class VeriDockDaemon:
    """Główna klasa demona VeriDock"""

    def __init__(self, config_file: str = ".veridock", pid_file: str = "/tmp/veridock.pid"):
        self.config_file = config_file
        self.pid_file = pid_file
        self.converter = VeriDockConverter(config_file)
        self.observer = None
        self.running = False

        # Konfiguracja logowania
        self.setup_logging()

        # Rejestracja sygnałów
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_logging(self):
        """Konfiguruje logowanie dla demona"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('/var/log/veridock.log'),
                logging.StreamHandler()
            ]
        )

    def signal_handler(self, signum, frame):
        """Obsługuje sygnały systemowe"""
        logging.info(f"Otrzymano sygnał {signum}, zatrzymywanie demona...")
        self.stop()

    def create_pid_file(self):
        """Tworzy plik PID"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            logging.info(f"Utworzono plik PID: {self.pid_file}")
        except Exception as e:
            logging.error(f"Nie można utworzyć pliku PID: {e}")

    def remove_pid_file(self):
        """Usuwa plik PID"""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                logging.info(f"Usunięto plik PID: {self.pid_file}")
        except Exception as e:
            logging.error(f"Nie można usunąć pliku PID: {e}")

    def is_running(self) -> bool:
        """Sprawdza czy demon już działa"""
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Sprawdź czy proces o tym PID istnieje
                try:
                    os.kill(pid, 0)  # Sygnał 0 nie zabija, tylko sprawdza
                    return True
                except OSError:
                    # Proces nie istnieje, usuń stary plik PID
                    os.remove(self.pid_file)
                    return False
            return False
        except Exception:
            return False

    def start(self):
        """Uruchamia demona"""
        if self.is_running():
            logging.error("Demon już działa")
            return False

        logging.info("Uruchamianie demona VeriDock...")

        # Utwórz plik PID
        self.create_pid_file()

        try:
            # Sprawdź foldery do monitorowania
            if not self.converter.watch_directories:
                logging.error("Brak folderów do monitorowania")
                return False

            # Skonfiguruj obserwator plików
            self.observer = Observer()
            handler = VeriDockFileHandler(self.converter)

            for directory in self.converter.watch_directories:
                self.observer.schedule(handler, directory, recursive=True)
                logging.info(f"Monitorowanie folderu: {directory}")

            # Uruchom obserwator
            self.observer.start()
            self.running = True

            logging.info("Demon VeriDock uruchomiony pomyślnie")

            # Jednorazowe skanowanie na start
            self.initial_scan()

            # Główna pętla z OCR
            self.main_loop()

        except Exception as e:
            logging.error(f"Błąd uruchamiania demona: {e}")
            self.cleanup()
            return False

        return True

    def initial_scan(self):
        """Wykonuje początkowe skanowanie folderów"""
        logging.info("Wykonywanie początkowego skanowania...")

        try:
            pdf_files = self.converter.find_pdf_files()
            if pdf_files:
                logging.info(f"Znaleziono {len(pdf_files)} plików PDF do przetworzenia")
                for pdf_file in pdf_files:
                    self.converter.process_pdf(pdf_file)
            else:
                logging.info("Nie znaleziono plików PDF do przetworzenia")
        except Exception as e:
            logging.error(f"Błąd początkowego skanowania: {e}")

    def main_loop(self):
        """Główna pętla demona"""
        last_ocr_run = 0

        try:
            while self.running:
                current_time = time.time()

                # Sprawdź czy czas na OCR
                if current_time - last_ocr_run >= self.converter.ocr_interval:
                    logging.info("Uruchamianie cyklicznego OCR...")
                    self.converter.process_ocr()
                    last_ocr_run = current_time

                # Poczekaj przed następną iteracją
                time.sleep(10)  # Sprawdź co 10 sekund

        except KeyboardInterrupt:
            logging.info("Otrzymano sygnał przerwania")
        except Exception as e:
            logging.error(f"Błąd w głównej pętli: {e}")
        finally:
            self.cleanup()

    def stop(self):
        """Zatrzymuje demona"""
        logging.info("Zatrzymywanie demona VeriDock...")
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()

        self.cleanup()

    def cleanup(self):
        """Czyści zasoby demona"""
        self.remove_pid_file()
        logging.info("Demon VeriDock zatrzymany")

    def status(self):
        """Sprawdza status demona"""
        if self.is_running():
            with open(self.pid_file, 'r') as f:
                pid = f.read().strip()
            print(f"VeriDock Daemon jest uruchomiony (PID: {pid})")
            return True
        else:
            print("VeriDock Daemon nie jest uruchomiony")
            return False


def main():
    """Funkcja główna"""
    if len(sys.argv) < 2:
        print("Użycie: python daemon_service.py {start|stop|restart|status} [config_file]")
        sys.exit(1)

    command = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else ".veridock"

    daemon = VeriDockDaemon(config_file)

    if command == "start":
        if not daemon.start():
            sys.exit(1)

    elif command == "stop":
        if daemon.is_running():
            # Wyślij sygnał TERM do działającego procesu
            try:
                with open(daemon.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print("Wysłano sygnał zatrzymania")
            except Exception as e:
                print(f"Błąd zatrzymywania: {e}")
        else:
            print("Demon nie jest uruchomiony")

    elif command == "restart":
        if daemon.is_running():
            # Zatrzymaj
            try:
                with open(daemon.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)  # Poczekaj na zatrzymanie
            except Exception:
                pass

        # Uruchom
        if not daemon.start():
            sys.exit(1)

    elif command == "status":
        daemon.status()

    else:
        print(f"Nieznana komenda: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()