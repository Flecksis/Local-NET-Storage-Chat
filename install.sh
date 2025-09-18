#!/bin/bash

APP_NAME="local-net-storage-chat"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
VENV_DIR="$INSTALL_DIR/venv"

echo ">>> Установка $APP_NAME..."

# Update package lists and install required packages
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# Clone or update the repository
if [ ! -d "$INSTALL_DIR" ]; then
    sudo git clone https://github.com/Flecksis/Local-NET-Storage-Chat.git "$INSTALL_DIR"
else
    echo ">>> Репозиторий уже существует, обновляем..."
    cd "$INSTALL_DIR" && sudo git pull
fi

cd "$INSTALL_DIR"

# Create and activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo ">>> Создание виртуального окружения..."
    sudo python3 -m venv "$VENV_DIR"
fi

# Install dependencies in the virtual environment
echo ">>> Установка зависимостей из requirements.txt..."
sudo "$VENV_DIR/bin/pip" install --upgrade pip
sudo "$VENV_DIR/bin/pip" install -r requirements.txt

# Create systemd service file
echo ">>> Создание systemd сервиса..."
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Local NET Storage Chat
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/app.py
Restart=always
User=$USER
Environment="PATH=$VENV_DIR/bin:$PATH"

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd and enable/start the service
sudo systemctl daemon-reload
sudo systemctl enable --now "$APP_NAME"

echo ">>> Установка завершена!"
echo "Сервис запущен: systemctl status $APP_NAME"
echo "Чтобы остановить: sudo systemctl stop $APP_NAME"
