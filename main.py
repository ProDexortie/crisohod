#!/usr/bin/env python3
"""
ИНТЕЛЛЕКТУАЛЬНАЯ СИСТЕМА ОПРЕДЕЛЕНИЯ ФИЗИОЛОГИЧЕСКИХ ПАРАМЕТРОВ
МЕЛКИХ ЛАБОРАТОРНЫХ ЖИВОТНЫХ

Главный файл запуска приложения
"""

import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

# Добавляем пути к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from utils.config_manager import ConfigManager


def setup_dark_theme(app):
    """Настройка темной темы с оранжевыми акцентами"""
    app.setStyle("Fusion")
    
    dark_palette = QPalette()
    
    # Основные цвета
    dark_gray = QColor(53, 53, 53)
    lighter_gray = QColor(80, 80, 80)
    light_gray = QColor(120, 120, 120)
    orange = QColor(255, 140, 0)
    dark_orange = QColor(255, 100, 0)
    
    # Настройка палитры
    dark_palette.setColor(QPalette.Window, dark_gray)
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, dark_gray)
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, lighter_gray)
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, orange)
    dark_palette.setColor(QPalette.Link, orange)
    dark_palette.setColor(QPalette.Highlight, orange)
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    
    # Дополнительные состояния
    dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, light_gray)
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, light_gray)
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, light_gray)
    
    app.setPalette(dark_palette)
    
    # Дополнительные стили
    app.setStyleSheet("""
        QToolTip {
            color: #ffffff;
            background-color: #2a2a2a;
            border: 1px solid #ff8c00;
        }
        
        QPushButton {
            border: 2px solid #505050;
            border-radius: 6px;
            padding: 5px;
            background-color: #505050;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #606060;
            border-color: #ff8c00;
        }
        
        QPushButton:pressed {
            background-color: #404040;
        }
        
        QPushButton:checked {
            background-color: #ff8c00;
            border-color: #ff8c00;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #3A3A3A;
            height: 8px;
            background: #505050;
            margin: 2px 0;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background: #ff8c00;
            border: 1px solid #ff8c00;
            width: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }
        
        QSlider::handle:horizontal:hover {
            background: #ff6400;
        }
        
        QProgressBar {
            border: 2px solid #505050;
            border-radius: 5px;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #ff8c00;
            border-radius: 3px;
        }
        
        QTabWidget::pane {
            border: 1px solid #505050;
            background-color: #353535;
        }
        
        QTabBar::tab {
            background-color: #505050;
            padding: 8px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #ff8c00;
        }
        
        QTabBar::tab:hover {
            background-color: #606060;
        }
        
        QGroupBox {
            border: 2px solid #505050;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QComboBox {
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 5px;
            min-width: 100px;
        }
        
        QComboBox:hover {
            border-color: #ff8c00;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #ff8c00;
            margin-right: 5px;
        }
        
        QSpinBox, QDoubleSpinBox {
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 5px;
        }
        
        QSpinBox:hover, QDoubleSpinBox:hover {
            border-color: #ff8c00;
        }
        
        QTableWidget {
            gridline-color: #505050;
            background-color: #2a2a2a;
        }
        
        QTableWidget::item:selected {
            background-color: #ff8c00;
        }
        
        QHeaderView::section {
            background-color: #505050;
            padding: 5px;
            border: 1px solid #3a3a3a;
        }
    """)


def main():
    """Главная функция запуска приложения"""
    # Создаем приложение
    app = QApplication(sys.argv)
    app.setApplicationName("CrisohodAnalyzer")
    app.setOrganizationName("PhysioLab")
    
    # Настраиваем тему
    setup_dark_theme(app)
    
    # Инициализируем менеджер конфигурации
    config_manager = ConfigManager()
    
    # Создаем и показываем главное окно
    window = MainWindow(config_manager)
    window.show()
    
    # Запускаем приложение
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()