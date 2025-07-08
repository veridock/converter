#!/bin/bash
# VeriDock Converter - Skrypt systemowy
# Autor: VeriDock System

VERIDOCK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIDOCK_USER="$USER"

if [ "$(id -u)" -ne 0 ]; then
    echo "Ten skrypt wymaga uprawnień administratora. Uruchom z sudo."
    exit 1
fi

case "$1" in
    "install-service")
        echo "Instalowanie usługi systemowej VeriDock..."

        # Sprawdź czy katalog istnieje
        if [ ! -d "$VERIDOCK_DIR" ]; then
            echo "Błąd: Katalog $VERIDOCK_DIR nie istnieje!"
            exit 1
        fi

        # Utwórz plik usługi systemd
        cat > /etc/systemd/system/veridock.service << EOF
[Unit]
Description=VeriDock Converter Daemon
After=network.target

[Service]
Type=forking
User=$VERIDOCK_USER
WorkingDirectory=$VERIDOCK_DIR
ExecStart=$VERIDOCK_DIR/scripts/veridock.sh daemon
ExecStop=$VERIDOCK_DIR/scripts/veridock.sh stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Nadaj uprawnienia
        chmod 644 /etc/systemd/system/veridock.service
        chmod +x "$VERIDOCK_DIR/scripts/veridock.sh"

        # Przeładuj systemd
        systemctl daemon-reload
        systemctl enable veridock.service

        echo "Usługa systemowa zainstalowana. Użyj:"
        echo "  sudo systemctl start veridock    - uruchom"
        echo "  sudo systemctl stop veridock     - zatrzymaj"
        echo "  sudo systemctl status veridock   - status"
        ;;

    "uninstall-service")
        echo "Odinstalowywanie usługi systemowej..."
        systemctl stop veridock.service 2>/dev/null || true
        systemctl disable veridock.service 2>/dev/null || true
        rm -f /etc/systemd/system/veridock.service
        systemctl daemon-reload
        systemctl reset-failed
        echo "Usługa systemowa odinstalowana"
        ;;

    "install-cron")
        echo "Instalowanie zadania cron..."

        # Dodaj zadanie cron co 10 minut
        (crontab -l 2>/dev/null | grep -v "$VERIDOCK_DIR/scripts/veridock.sh scan"; 
         echo "*/10 * * * * $VERIDOCK_DIR/scripts/veridock.sh scan >/dev/null 2>&1") | crontab -

        echo "Zadanie cron zainstalowane (skanowanie co 10 minut)"
        ;;

    "uninstall-cron")
        echo "Odinstalowywanie zadania cron..."
        crontab -l 2>/dev/null | grep -v "$VERIDOCK_DIR/scripts/veridock.sh scan" | crontab -
        echo "Zadanie cron odinstalowane"
        ;;

    *)
        echo "Użycie: sudo $0 {install-service|uninstall-service|install-cron|uninstall-cron}"
        exit 1
        ;;
esac

exit 0
