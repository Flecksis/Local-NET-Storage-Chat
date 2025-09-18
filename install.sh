
set -e

APP_NAME="local-net-storage-chat"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

echo ">>> Установка $APP_NAME..."


sudo apt update
sudo apt install -y python3 python3-pip git


if [ ! -d "$INSTALL_DIR" ]; then
    sudo git clone https://github.com/Flecksis/Local-NET-Storage-Chat.git "$INSTALL_DIR"
else
    echo ">>> Репозиторий уже существует, обновляем..."
    cd "$INSTALL_DIR" && sudo git pull
fi

cd "$INSTALL_DIR"

sudo pip3 install -r requirements.txt


echo ">>> Создание systemd сервиса..."
sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Local NET Storage Chat
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOL


sudo systemctl daemon-reexec
sudo systemctl enable --now $APP_NAME

echo ">>> Установка завершена!"
echo "Сервис запущен: systemctl status $APP_NAME"
echo "Чтобы остановить: sudo systemctl stop $APP_NAME"
