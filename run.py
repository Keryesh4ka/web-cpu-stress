import subprocess
import sys

def install_dependencies():
    """
    Устанавливает зависимости из файла requirements.txt.
    """
    try:
        print("Устанавливаем зависимости...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Зависимости успешно установлены!")
    except subprocess.CalledProcessError:
        print("Ошибка при установке зависимостей. Проверьте содержимое requirements.txt.")
        sys.exit(1)

def run_application():
    """
    Запускает основное приложение.
    """
    try:
        print("Запускаем приложение...")
        subprocess.check_call([sys.executable, "main.py"])  # Замените "main.py" на имя вашего скрипта
    except subprocess.CalledProcessError:
        print("Ошибка при запуске приложения.")
        sys.exit(1)

if __name__ == "__main__":
    install_dependencies()
    run_application()
