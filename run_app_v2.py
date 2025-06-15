#!/usr/bin/env python3
"""
run_app_v2.py
Запуск обновленного приложения для анализа отпечатков лап версии 2.0
"""

import sys
import os
from pathlib import Path
import traceback

# Добавляем текущую директорию в путь поиска модулей
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Проверка наличия необходимых зависимостей"""
    required_modules = [
        ('PyQt5', 'PyQt5'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('pandas', 'pandas'),
        ('matplotlib', 'matplotlib'),
        ('scipy', 'scipy'),
        ('sklearn', 'scikit-learn'),
        ('seaborn', 'seaborn'),
        ('PIL', 'Pillow'),
        ('yaml', 'PyYAML'),
        ('skimage', 'scikit-image')
    ]
    
    missing_modules = []
    
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(package_name)
    
    if missing_modules:
        print("❌ Отсутствуют необходимые модули:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\n📦 Установите недостающие модули командой:")
        print(f"   pip install {' '.join(missing_modules)}")
        return False
    
    print("✅ Все необходимые модули установлены")
    return True


def check_test_files():
    """Проверка наличия тестовых файлов"""
    test_files = [
        Path("old/test.mp4"),
        Path("old/test.csv"),
        Path("config.yaml")
    ]
    
    missing_files = []
    for file_path in test_files:
        if not file_path.exists():
            missing_files.append(str(file_path))
    
    if missing_files:
        print("⚠️  Отсутствуют тестовые файлы:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\n💡 Приложение все равно запустится, но тестовые данные будут недоступны")
        print("   Вы можете загрузить свои файлы через интерфейс")
        return False
    
    print("✅ Тестовые файлы найдены")
    return True


def create_default_config():
    """Создание файла конфигурации по умолчанию"""
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        print("📝 Создание файла конфигурации по умолчанию...")
        
        default_config = """# Конфигурация для анализа отпечатков лап
# Project definitions
Task: PawAnalysis
scorer: DefaultAnalyzer
date: Auto
multianimalproject: false

# Части тела для анализа
bodyparts:
- lf_digit1
- lf_digit2
- lf_digit3
- lf_digit4
- lf_center
- lf_heel
- rf_digit1
- rf_digit2
- rf_digit3
- rf_digit4
- rf_center
- rf_heel
- lb_digit1
- lb_digit2
- lb_digit3
- lb_digit4
- lb_digit5
- lb_center
- lb_heel
- rb_digit1
- rb_digit2
- rb_digit3
- rb_digit4
- rb_digit5
- rb_center
- rb_heel

# Соединения для скелета
skeleton:
- [lf_digit1, lf_center]
- [lf_digit2, lf_center]
- [lf_digit3, lf_center]
- [lf_digit4, lf_center]
- [lf_center, lf_heel]
- [rf_digit1, rf_center]
- [rf_digit2, rf_center]
- [rf_digit3, rf_center]
- [rf_digit4, rf_center]
- [rf_center, rf_heel]
- [lb_digit1, lb_center]
- [lb_digit2, lb_center]
- [lb_digit3, lb_center]
- [lb_digit4, lb_center]
- [lb_digit5, lb_center]
- [lb_center, lb_heel]
- [rb_digit1, rb_center]
- [rb_digit2, rb_center]
- [rb_digit3, rb_center]
- [rb_digit4, rb_center]
- [rb_digit5, rb_center]
- [rb_center, rb_heel]

# Параметры отображения
skeleton_color: yellow
pcutoff: 0.6
dotsize: 3
alphavalue: 0.7
colormap: rainbow

# Параметры анализа
start: 0
stop: 1
numframes2pick: 20
"""
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(default_config)
        
        print(f"✅ Файл конфигурации создан: {config_path}")


def setup_environment():
    """Настройка окружения для работы приложения"""
    print("🔧 Настройка окружения...")
    
    # Создаем необходимые директории
    directories = ['old', 'results', 'exports', 'temp']
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"📁 Создана директория: {dir_name}")
    
    # Создаем конфигурацию по умолчанию
    create_default_config()
    
    print("✅ Окружение настроено")


def main():
    """Главная функция запуска"""
    print("=" * 60)
    print("🦶 АНАЛИЗАТОР ОТПЕЧАТКОВ ЛАП v2.0")
    print("   Современная система анализа контактных областей")
    print("=" * 60)
    print()
    
    try:
        # Проверяем зависимости
        print("🔍 Проверка зависимостей...")
        if not check_dependencies():
            input("\nНажмите Enter для выхода...")
            return
        
        print()
        
        # Настраиваем окружение
        setup_environment()
        print()
        
        # Проверяем тестовые файлы
        print("📂 Проверка тестовых файлов...")
        check_test_files()
        print()
        
        # Импортируем и запускаем приложение
        print("🚀 Запуск приложения...")
        
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPalette, QColor
        
        # Создаем приложение
        app = QApplication(sys.argv)
        app.setApplicationName("Анализатор отпечатков лап v2.0")
        app.setApplicationVersion("2.0.0")
        app.setStyle("Fusion")
        
        # Устанавливаем темную тему
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(42, 42, 42))
        palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(64, 64, 64))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        app.setPalette(palette)
        
        # Импортируем главное окно
        from main_window_v2 import MainWindowV2
        
        # Создаем и показываем окно
        print("✅ Приложение готово к работе!")
        print()
        print("💡 Возможности приложения:")
        print("   • Анализ отпечатков лап в реальном времени")
        print("   • Современный интерфейс с темной темой")
        print("   • Интерактивные графики и статистика")
        print("   • Продвинутые алгоритмы обработки изображений")
        print("   • Экспорт результатов в различных форматах")
        print()
        
        window = MainWindowV2()
        window.show()
        
        # Запускаем основной цикл
        sys.exit(app.exec_())
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("🔧 Проверьте установку всех необходимых модулей")
        print("📋 Список модулей в файле requirements.txt")
        traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        print("🐛 Подробности ошибки:")
        traceback.print_exc()
        
    finally:
        input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()