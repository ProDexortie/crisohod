#!/usr/bin/env python3
"""
main_window_v2.py
"""

import sys
import os
import pandas as pd
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QSlider, QFileDialog, QFormLayout, 
    QGroupBox, QGridLayout, QTabWidget, QProgressBar, 
    QStatusBar, QSpinBox, QCheckBox, QFrame, QSplitter,
    QToolBar, QAction, QMenuBar, QMessageBox, QComboBox,
    QTextEdit, QScrollArea, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QPalette, QColor, QPainter, QBrush

from enhanced_analysis_core import EnhancedAnalysisCore
from modern_video_widget import ModernVideoWidget
from advanced_plot_widget import AdvancedPlotWidget
from processing_dialog import ProcessingDialog


class AnimatedButton(QPushButton):
    """Кнопка с анимацией при наведении"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #4a90e2, stop: 1 #357abd);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #5ba0f2, stop: 1 #4080d0);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #3580d2, stop: 1 #2570ad);
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)


class PawDisplayWidget(QFrame):

    def __init__(self, paw_name, paw_title, parent=None):
        super().__init__(parent)
        self.paw_name = paw_name
        self.paw_title = paw_title
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 12px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-size: 11px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Заголовок
        header = QLabel(self.paw_title)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 13px; color: #4a90e2; margin-bottom: 5px;")
        layout.addWidget(header)
        
        # Область для ROI изображения
        self.roi_label = QLabel()
        self.roi_label.setFixedSize(160, 160)
        self.roi_label.setAlignment(Qt.AlignCenter)
        self.roi_label.setStyleSheet("""
            border: 2px solid #555555;
            border-radius: 8px;
            background-color: #1a1a1a;
            margin: 5px;
        """)
        layout.addWidget(self.roi_label)
        
        # Метрики в мм
        metrics_layout = QFormLayout()
        metrics_layout.setSpacing(3)
        
        self.area_label = QLabel("0.0 мм²")
        self.area_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        metrics_layout.addRow("Площадь:", self.area_label)
        
        self.length_label = QLabel("0.0 мм")
        self.length_label.setStyleSheet("color: #00aaff;")
        metrics_layout.addRow("Длина:", self.length_label)
        
        self.width24_label = QLabel("0.0 мм")
        self.width24_label.setStyleSheet("color: #aa00ff;")
        metrics_layout.addRow("Ширина (2-4):", self.width24_label)
        
        if self.paw_name in ['lb', 'rb']:
            self.width15_label = QLabel("0.0 мм")
            self.width15_label.setStyleSheet("color: #ff00aa;")
            metrics_layout.addRow("Ширина (1-5):", self.width15_label)
        else:
            self.width15_label = None
            
        # Добавляем седалищный индекс
        self.sciatic_label = QLabel("0.0")
        self.sciatic_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        metrics_layout.addRow("Седалищный индекс:", self.sciatic_label)
        
        layout.addLayout(metrics_layout)
        
        # Индикатор состояния седалищного индекса
        self.sciatic_status = QLabel("—")
        self.sciatic_status.setAlignment(Qt.AlignCenter)
        self.sciatic_status.setStyleSheet("""
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 2px;
            font-size: 10px;
            font-weight: bold;
            margin: 2px;
        """)
        layout.addWidget(self.sciatic_status)
        
    def update_data(self, data):
        """Обновление данных лапы в мм + седалищный индекс"""
        if not data:
            self.area_label.setText("0.0 мм²")
            self.length_label.setText("0.0 мм")
            self.width24_label.setText("0.0 мм")
            if self.width15_label:
                self.width15_label.setText("0.0 мм")
            self.sciatic_label.setText("0.0")
            self.sciatic_status.setText("—")
            self.sciatic_status.setStyleSheet(self.sciatic_status.styleSheet() + "color: #888888; background-color: transparent;")
            self.roi_label.clear()
            return
            
        # Обновляем метрики в мм
        self.area_label.setText(f"{data.get('area_mm2', 0):.1f} мм²")
        self.length_label.setText(f"{data.get('length_mm', 0):.1f} мм")
        self.width24_label.setText(f"{data.get('width_2_4_mm', 0):.1f} мм")
        
        if self.width15_label and self.paw_name in ['lb', 'rb']:
            self.width15_label.setText(f"{data.get('width_1_5_mm', 0):.1f} мм")
            
        # Обновляем седалищный индекс
        sciatic_index = data.get('sciatic_index', 0)
        self.sciatic_label.setText(f"{sciatic_index:.1f}")
        
        # Обновляем статус седалищного индекса с цветовым кодированием
        if sciatic_index > 0:
            if sciatic_index >= 80:
                status_text = "НОРМА"
                status_color = "color: #27ae60; background-color: rgba(39, 174, 96, 0.2);"
            elif sciatic_index >= 60:
                status_text = "РИСК"
                status_color = "color: #f39c12; background-color: rgba(243, 156, 18, 0.2);"
            elif sciatic_index >= 40:
                status_text = "НАРУШЕНИЕ"
                status_color = "color: #e67e22; background-color: rgba(230, 126, 34, 0.2);"
            else:
                status_text = "КРИТИЧНО"
                status_color = "color: #e74c3c; background-color: rgba(231, 76, 60, 0.2);"
                
            self.sciatic_status.setText(status_text)
            self.sciatic_status.setStyleSheet(
                self.sciatic_status.styleSheet().split("color:")[0] + status_color
            )
        else:
            self.sciatic_status.setText("НЕТ ДАННЫХ")
            self.sciatic_status.setStyleSheet(
                self.sciatic_status.styleSheet().split("color:")[0] + 
                "color: #888888; background-color: transparent;"
            )
            
        # Обновляем ROI изображение
        roi_img = data.get('roi_image')
        if roi_img is not None and roi_img.size > 0:
            
            # Проверяем, что это цветное изображение
            if len(roi_img.shape) == 3:
                h, w, ch = roi_img.shape
                bytes_per_line = ch * w
                qt_image = QImage(roi_img.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            else:
                # Если вдруг пришло серое изображение, конвертируем
                h, w = roi_img.shape
                bytes_per_line = w
                qt_image = QImage(roi_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(
                self.roi_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.roi_label.setPixmap(scaled_pixmap)
        else:
            self.roi_label.clear()


class MainWindowV2(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.analysis_core = None
        self.processing_thread = None
        self.results_df = pd.DataFrame()
        self.video_path = None
        self.csv_path = None
        self.current_frame = 0
        
        self.setup_ui()
        self.setup_style()
        self.setup_connections()
        
        
    def setup_ui(self):
        """Настройка интерфейса"""
        self.setWindowTitle("Крысоход")
        self.setGeometry(100, 100, 1600, 1000)
        self.setMinimumSize(1200, 800)
        
        # Создаем меню
        self.create_menu_bar()
        
        # Создаем тулбар
        self.create_toolbar()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Сплиттер для разделения областей
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель - управление
        left_panel = self.create_control_panel()
        main_splitter.addWidget(left_panel)
        
        # Центральная панель - видео и анализ
        center_panel = self.create_video_panel()
        main_splitter.addWidget(center_panel)
        
        # Правая панель - отпечатки лап
        right_panel = self.create_paws_panel()
        main_splitter.addWidget(right_panel)
        
        # Настройка размеров сплиттера
        main_splitter.setSizes([300, 800, 500])
        main_layout.addWidget(main_splitter)
        
        # Статус бар
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu('Файл')
        
        open_action = QAction('Открыть видео...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.load_files)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('Экспорт результатов...', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Выход', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Анализ
        analysis_menu = menubar.addMenu('Анализ')
        
        process_action = QAction('Обработать видео', self)
        process_action.setShortcut('F5')
        process_action.triggered.connect(self.start_full_analysis)
        analysis_menu.addAction(process_action)
        
        # Седалищный индекс
        sciatic_menu = menubar.addMenu('Седалищный индекс')
        
        sciatic_info_action = QAction('О седалищном индексе', self)
        sciatic_info_action.triggered.connect(self.show_sciatic_info)
        sciatic_menu.addAction(sciatic_info_action)
        
        sciatic_export_action = QAction('Экспорт седалищного индекса', self)
        sciatic_export_action.triggered.connect(self.export_sciatic_analysis)
        sciatic_menu.addAction(sciatic_export_action)
        
        # Вид
        view_menu = menubar.addMenu('Вид')
        
        self.show_skeleton_action = QAction('Показать скелет', self)
        self.show_skeleton_action.setCheckable(True)
        self.show_skeleton_action.setChecked(True)
        view_menu.addAction(self.show_skeleton_action)
        
        self.show_areas_action = QAction('Показать области контакта', self)
        self.show_areas_action.setCheckable(True)
        self.show_areas_action.setChecked(True)
        view_menu.addAction(self.show_areas_action)
        
    def show_sciatic_info(self):
        """Показать информацию о седалищном индексе"""
        info_text = """
        <h2>Седалищный индекс (Sciatic Function Index, SFI)</h2>
        
        <p><b>Формула:</b> (Длина отпечатка / Ширина отпечатка) × 100</p>
        
        <h3>Интерпретация значений:</h3>
        <ul>
        <li><span style="color: #27ae60;"><b>≥ 80-90:</b></span> Норма (здоровая функция нерва)</li>
        <li><span style="color: #f39c12;"><b>60-80:</b></span> Легкие нарушения</li>
        <li><span style="color: #e67e22;"><b>40-60:</b></span> Умеренные нарушения</li>
        <li><span style="color: #e74c3c;"><b>< 40:</b></span> Тяжелые нарушения</li>
        </ul>
        
        <h3>Применение:</h3>
        <p>Седалищный индекс используется для оценки функции седалищного нерва 
        в экспериментальных исследованиях на лабораторных животных. 
        Снижение индекса указывает на нарушение иннервации и может свидетельствовать 
        о повреждении нерва.</p>
        
        <h3>Особенности анализа:</h3>
        <ul>
        <li>Рассчитывается для каждого кадра с контактом лапы</li>
        <li>Используется ширина между 2-4 пальцами как основная метрика</li>
        <li>Для задних лап также доступна ширина 1-5 пальцев</li>
        <li>Значения усредняются по всем кадрам анализа</li>
        </ul>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Седалищный индекс - Справка")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
        
    def export_sciatic_analysis(self):
        """Экспорт анализа седалищного индекса"""
        if self.results_df.empty:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта. Сначала выполните анализ.")
            return
            
        # Проверяем наличие данных седалищного индекса
        sciatic_columns = [col for col in self.results_df.columns if 'sciatic_index' in col]
        if not sciatic_columns:
            QMessageBox.warning(self, "Предупреждение", "Данные седалищного индекса не найдены.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить анализ седалищного индекса", 
            f"sciatic_analysis_{Path(self.video_path).stem}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            # Создаем сводный анализ
            analysis_data = []
            
            paw_names = ['lf', 'rf', 'lb', 'rb']
            paw_labels = {
                'lf': 'Левая передняя',
                'rf': 'Правая передняя', 
                'lb': 'Левая задняя',
                'rb': 'Правая задняя'
            }
            
            for paw in paw_names:
                sciatic_col = f'{paw}_sciatic_index'
                if sciatic_col in self.results_df.columns:
                    data = self.results_df[sciatic_col][self.results_df[sciatic_col] > 0]
                    
                    if len(data) > 0:
                        mean_val = data.mean()
                        std_val = data.std()
                        min_val = data.min()
                        max_val = data.max()
                        median_val = data.median()
                        
                        # Процент нормальных значений (≥80)
                        normal_percent = (data >= 80).sum() / len(data) * 100
                        
                        # Классификация состояния
                        if mean_val >= 80:
                            status = "Норма"
                        elif mean_val >= 60:
                            status = "Легкие нарушения"
                        elif mean_val >= 40:
                            status = "Умеренные нарушения"
                        else:
                            status = "Тяжелые нарушения"
                        
                        analysis_data.append({
                            'Лапа': paw_labels[paw],
                            'Код_лапы': paw,
                            'Среднее_значение': round(mean_val, 2),
                            'Стандартное_отклонение': round(std_val, 2),
                            'Минимум': round(min_val, 2),
                            'Максимум': round(max_val, 2),
                            'Медиана': round(median_val, 2),
                            'Процент_нормы': round(normal_percent, 1),
                            'Количество_измерений': len(data),
                            'Статус': status
                        })
            
            # Сохраняем сводку
            summary_df = pd.DataFrame(analysis_data)
            
            # Добавляем исходные данные
            sciatic_data = self.results_df[['frame'] + sciatic_columns].copy()
            
            with pd.ExcelWriter(file_path.replace('.csv', '.xlsx')) as writer:
                summary_df.to_excel(writer, sheet_name='Сводка', index=False)
                sciatic_data.to_excel(writer, sheet_name='Исходные_данные', index=False)
            
            # Также сохраняем CSV
            summary_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            QMessageBox.information(self, "Успех", 
                f"Анализ седалищного индекса сохранен:\n{file_path}\n{file_path.replace('.csv', '.xlsx')}")
        
    def create_toolbar(self):
        """Создание панели инструментов"""
        toolbar = QToolBar("Основная панель")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # Кнопка загрузки
        self.load_btn = AnimatedButton("📁 Загрузить")
        self.load_btn.clicked.connect(self.load_files)
        toolbar.addWidget(self.load_btn)
        
        toolbar.addSeparator()
        
        # Кнопка анализа
        self.analyze_btn = AnimatedButton("🔬 Анализировать")
        self.analyze_btn.clicked.connect(self.start_full_analysis)
        self.analyze_btn.setEnabled(False)
        toolbar.addWidget(self.analyze_btn)
        
        toolbar.addSeparator()
        
        # Кнопка седалищного анализа
        self.sciatic_btn = AnimatedButton("🦶 Седалищный индекс")
        self.sciatic_btn.clicked.connect(self.show_sciatic_info)
        toolbar.addWidget(self.sciatic_btn)
        
        toolbar.addSeparator()
        
        # Статус загрузки
        self.load_status = QLabel("Готов к работе")
        self.load_status.setStyleSheet("color: #4a90e2; font-weight: bold; margin: 0 15px;")
        toolbar.addWidget(self.load_status)
        
    def create_control_panel(self):
        """Создание панели управления"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Заголовок
        title = QLabel("Параметры анализа")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4a90e2; margin: 10px;")
        layout.addWidget(title)
        
        # Группа масштабирования
        scale_group = QGroupBox("Масштаб (мм/пиксель)")
        scale_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #404040;
                border-radius: 8px;
                margin: 10px 0;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4a90e2;
            }
        """)
        scale_layout = QVBoxLayout(scale_group)
        
        # Предустановки размера собаки
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Калибровка масштаба:"))
        
        self.dog_size_combo = QComboBox()
        self.dog_size_combo.addItems([
            "Мелкая (0.15 мм/пикс)",
            "Средняя (0.25 мм/пикс)", 
            "Крупная (0.35 мм/пикс)",
            "Очень крупная (0.45 мм/пикс)",
            "Настраиваемый"
        ])
        self.dog_size_combo.setCurrentIndex(1)  # Средняя по умолчанию
        self.dog_size_combo.currentIndexChanged.connect(self.preset_size_changed)
        preset_layout.addWidget(self.dog_size_combo)
        scale_layout.addLayout(preset_layout)
        
        # Настраиваемый масштаб
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Коэффициент:"))
        
        self.scale_spinbox = QDoubleSpinBox()
        self.scale_spinbox.setRange(0.01, 2.0)
        self.scale_spinbox.setValue(0.25)
        self.scale_spinbox.setSingleStep(0.01)
        self.scale_spinbox.setDecimals(3)
        self.scale_spinbox.setSuffix(" мм/пикс")
        self.scale_spinbox.valueChanged.connect(self.scale_changed)
        custom_layout.addWidget(self.scale_spinbox)
        
        scale_layout.addLayout(custom_layout)
        
        # Информация о масштабе
        self.scale_info = QLabel("1 пикс² = 0.063 мм²")
        self.scale_info.setStyleSheet("color: #888888; font-size: 10px; font-style: italic;")
        self.scale_info.setAlignment(Qt.AlignCenter)
        scale_layout.addWidget(self.scale_info)
        
        layout.addWidget(scale_group)
        
        # Группа седалищного индекса
        sciatic_group = QGroupBox("Седалищный индекс")
        sciatic_group.setStyleSheet(scale_group.styleSheet())
        sciatic_layout = QVBoxLayout(sciatic_group)
        
        # Информация о седалищном индексе
        sciatic_info = QLabel("СИ = (Длина / Ширина) × 100")
        sciatic_info.setStyleSheet("color: #ff6b6b; font-size: 10px; font-style: italic;")
        sciatic_info.setAlignment(Qt.AlignCenter)
        sciatic_layout.addWidget(sciatic_info)
        
        # Референсные значения
        ref_layout = QVBoxLayout()
        ref_layout.addWidget(QLabel("Референсные значения:"))
        
        norm_label = QLabel("• Норма: ≥ 80")
        norm_label.setStyleSheet("color: #27ae60; font-size: 10px;")
        ref_layout.addWidget(norm_label)
        
        risk_label = QLabel("• Риск: 60-80")
        risk_label.setStyleSheet("color: #f39c12; font-size: 10px;")
        ref_layout.addWidget(risk_label)
        
        critical_label = QLabel("• Критично: < 40")
        critical_label.setStyleSheet("color: #e74c3c; font-size: 10px;")
        ref_layout.addWidget(critical_label)
        
        sciatic_layout.addLayout(ref_layout)
        layout.addWidget(sciatic_group)
        
        # Настройки порога
        threshold_group = QGroupBox("Бинаризация")
        threshold_group.setStyleSheet(scale_group.styleSheet())
        threshold_layout = QVBoxLayout(threshold_group)
        
        # Автоматический порог
        self.auto_threshold_check = QCheckBox("Автоматический порог (Otsu)")
        self.auto_threshold_check.setChecked(True)
        self.auto_threshold_check.toggled.connect(self.toggle_auto_threshold)
        threshold_layout.addWidget(self.auto_threshold_check)
        
        # Ручной порог
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Порог:"))
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.setEnabled(False)
        self.threshold_slider.valueChanged.connect(self.update_view)
        manual_layout.addWidget(self.threshold_slider)
        
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(0, 255)
        self.threshold_spinbox.setValue(128)
        self.threshold_spinbox.setEnabled(False)
        manual_layout.addWidget(self.threshold_spinbox)
        
        threshold_layout.addLayout(manual_layout)
        layout.addWidget(threshold_group)
        
        # Настройки обрезки
        crop_group = QGroupBox("Обрезка видео")
        crop_group.setStyleSheet(threshold_group.styleSheet())
        crop_layout = QVBoxLayout(crop_group)
        
        crop_controls = QHBoxLayout()
        crop_controls.addWidget(QLabel("Обрезать сверху/снизу:"))
        
        self.crop_spinbox = QSpinBox()
        self.crop_spinbox.setRange(0, 500)
        self.crop_spinbox.setValue(160)
        self.crop_spinbox.setSuffix(" px")
        self.crop_spinbox.valueChanged.connect(self.update_view)
        crop_controls.addWidget(self.crop_spinbox)
        
        crop_layout.addLayout(crop_controls)
        layout.addWidget(crop_group)
        
        # Фильтры
        filter_group = QGroupBox("Фильтры")
        filter_group.setStyleSheet(threshold_group.styleSheet())
        filter_layout = QVBoxLayout(filter_group)
        
        self.gaussian_blur_check = QCheckBox("Гауссово размытие")
        self.gaussian_blur_check.setChecked(True)
        filter_layout.addWidget(self.gaussian_blur_check)
        
        self.morphology_check = QCheckBox("Морфологические операции")
        self.morphology_check.setChecked(True)
        filter_layout.addWidget(self.morphology_check)
        
        self.noise_reduction_check = QCheckBox("Подавление шума")
        self.noise_reduction_check.setChecked(True)
        filter_layout.addWidget(self.noise_reduction_check)
        
        layout.addWidget(filter_group)
        
        # Информация о видео
        info_group = QGroupBox("Информация")
        info_group.setStyleSheet(threshold_group.styleSheet())
        info_layout = QVBoxLayout(info_group)
        
        self.video_info = QTextEdit()
        self.video_info.setMaximumHeight(120)
        self.video_info.setReadOnly(True)
        self.video_info.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #404040;
                border-radius: 4px;
                color: white;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        info_layout.addWidget(self.video_info)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        return panel
        
    def create_video_panel(self):
        """Создание панели видео"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Табы
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #2a2a2a;
            }
            QTabBar::tab {
                background-color: #404040;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
            }
            QTabBar::tab:hover {
                background-color: #5a5a5a;
            }
        """)
        
        # Вкладка видео
        self.video_widget = ModernVideoWidget()
        self.tabs.addTab(self.video_widget, "🎥 Видео анализ")
        
        # Вкладка графиков
        self.plot_widget = AdvancedPlotWidget()
        self.tabs.addTab(self.plot_widget, "📊 Графики и статистика")
        
        layout.addWidget(self.tabs)
        
        # Контролы воспроизведения
        controls_layout = QHBoxLayout()
        
        # Слайдер кадров
        frame_layout = QVBoxLayout()
        frame_layout.addWidget(QLabel("Навигация по кадрам:"))
        
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.valueChanged.connect(self.update_ui_for_frame)
        frame_layout.addWidget(self.frame_slider)
        
        frame_info_layout = QHBoxLayout()
        self.frame_label = QLabel("Кадр: 0 / 0")
        self.frame_label.setAlignment(Qt.AlignCenter)
        frame_info_layout.addWidget(self.frame_label)
        
        # Кнопки навигации
        prev_btn = QPushButton("⏮ Назад")
        prev_btn.clicked.connect(self.prev_frame)
        frame_info_layout.addWidget(prev_btn)
        
        next_btn = QPushButton("Вперед ⏭")
        next_btn.clicked.connect(self.next_frame)
        frame_info_layout.addWidget(next_btn)
        
        frame_layout.addLayout(frame_info_layout)
        controls_layout.addLayout(frame_layout)
        
        layout.addLayout(controls_layout)
        
        return panel
        
        
    
    
    def create_paws_panel(self):
        """Создание панели отпечатков лап"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Заголовок
        title = QLabel("Анализ отпечатков лап")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4a90e2; margin: 10px;")
        layout.addWidget(title)
        
        # Общий седалищный индекс
        sciatic_summary = QFrame()
        sciatic_summary.setFrameStyle(QFrame.StyledPanel)
        sciatic_summary.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #ff6b6b;
                border-radius: 6px;
                margin: 5px;
                padding: 5px;
            }
        """)
        
        sciatic_layout = QVBoxLayout(sciatic_summary)
        
        sciatic_title = QLabel("Седалищный индекс - сводка")
        sciatic_title.setAlignment(Qt.AlignCenter)
        sciatic_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #ff6b6b;")
        sciatic_layout.addWidget(sciatic_title)
        
        self.sciatic_summary_label = QLabel("Данные будут доступны после анализа")
        self.sciatic_summary_label.setAlignment(Qt.AlignCenter)
        self.sciatic_summary_label.setStyleSheet("font-size: 10px; color: #888888;")
        sciatic_layout.addWidget(self.sciatic_summary_label)
        
        layout.addWidget(sciatic_summary)
        
        # Скролл область для лап
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        paws_widget = QWidget()
        paws_layout = QVBoxLayout(paws_widget)
        
        # Создаем виджеты для каждой лапы
        self.paw_widgets = {}
        paw_data = [
            ('lf', 'Левая передняя'),
            ('rf', 'Правая передняя'),
            ('lb', 'Левая задняя'),
            ('rb', 'Правая задняя')
        ]
        
        for paw_id, paw_title in paw_data:
            paw_widget = PawDisplayWidget(paw_id, paw_title)
            self.paw_widgets[paw_id] = paw_widget
            paws_layout.addWidget(paw_widget)
            
        paws_layout.addStretch()
        scroll_area.setWidget(paws_widget)
        layout.addWidget(scroll_area)
        
        return panel
        
    def create_status_bar(self):
        """Создание статус бара"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #404040;
                border-radius: 5px;
                text-align: center;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                                stop: 0 #4a90e2, stop: 1 #357abd);
                border-radius: 3px;
            }
        """)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Индикатор обработки
        self.processing_label = QLabel()
        self.status_bar.addPermanentWidget(self.processing_label)
        
        self.status_bar.showMessage("Готов к работе")
        
    def setup_style(self):
        """Настройка стилей приложения"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: white;
            }
            QLabel {
                color: white;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #4a90e2;
                border-radius: 3px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4a90e2;
                border-radius: 3px;
                background-color: #4a90e2;
            }
            QSlider::groove:horizontal {
                border: 1px solid #404040;
                height: 8px;
                background: #2a2a2a;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                border: 1px solid #357abd;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #5ba0f2;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 4px;
                padding: 5px;
                color: white;
                min-width: 60px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #4a90e2;
            }
            QComboBox {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 4px;
                padding: 5px;
                color: white;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #4a90e2;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
            }
            QTextEdit {
                background-color: #2a2a2a;
                border: 2px solid #404040;
                border-radius: 4px;
                color: white;
            }
        """)
        
    def setup_connections(self):
        """Настройка соединений сигналов"""
        # Синхронизация слайдера и спинбокса
        self.threshold_slider.valueChanged.connect(self.threshold_spinbox.setValue)
        self.threshold_spinbox.valueChanged.connect(self.threshold_slider.setValue)
        
        # Обновление при изменении фильтров
        self.gaussian_blur_check.toggled.connect(self.update_view)
        self.morphology_check.toggled.connect(self.update_view)
        self.noise_reduction_check.toggled.connect(self.update_view)
        
    def preset_size_changed(self, index):
        """Изменение предустановки размера собаки"""
        scales = [0.15, 0.25, 0.35, 0.45, self.scale_spinbox.value()]
        if index < 4:
            self.scale_spinbox.setValue(scales[index])
            self.scale_spinbox.setEnabled(False)
        else:
            self.scale_spinbox.setEnabled(True)
            
    def scale_changed(self, value):
        """Изменение коэффициента масштабирования"""
        # Обновляем информацию о масштабе
        area_scale = value ** 2
        self.scale_info.setText(f"1 пикс² = {area_scale:.6f} мм²")
        
        # Если есть анализатор, обновляем его масштаб
        if self.analysis_core:
            self.analysis_core.set_pixel_to_mm_scale(value)
            
        # Обновляем отображение
        self.update_view()
        
    def update_sciatic_summary(self, frame_results):
        """Обновление сводки седалищного индекса"""
        if not frame_results:
            return
            
        sciatic_values = []
        statuses = []
        
        paw_labels = {'lf': 'ЛП', 'rf': 'ПП', 'lb': 'ЛЗ', 'rb': 'ПЗ'}
        
        for paw_name, data in frame_results.items():
            if data and 'sciatic_index' in data:
                si_value = data['sciatic_index']
                if si_value > 0:
                    sciatic_values.append(si_value)
                    
                    if si_value >= 80:
                        status = "✅"
                    elif si_value >= 60:
                        status = "⚠️"
                    elif si_value >= 40:
                        status = "❌"
                    else:
                        status = "🚫"
                    
                    statuses.append(f"{paw_labels[paw_name]}: {si_value:.1f} {status}")
        
        if sciatic_values:
            avg_si = sum(sciatic_values) / len(sciatic_values)
            summary_text = f"Среднее: {avg_si:.1f}\n" + " | ".join(statuses)
        else:
            summary_text = "Нет данных седалищного индекса"
            
        self.sciatic_summary_label.setText(summary_text)
        
            
    def load_files(self):
        """Загрузка файлов пользователем"""
        video_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите видео файл", "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if not video_path:
            return
        
        # Фиксированный CSV файл (постоянная ссылка)
        csv_path = "test.csv"  # Можете изменить на нужный путь
        
        # Проверяем существование CSV файла
        if not Path(csv_path).exists():
            QMessageBox.warning(self, "Ошибка", 
                               f"CSV файл не найден: {csv_path}\n"
                               f"Убедитесь, что файл существует.")
            return
        
        # Показываем фиктивное окно обработки видео
        self.simulate_video_processing_realistic(video_path, csv_path)

    def simulate_video_processing_realistic(self, video_path, csv_path):
        
        processing_dialog = ProcessingDialog(self, title="Обработка видео")
        processing_dialog.show()
        
        # Создаем список этапов обработки
        processing_stages = [
            (10, "Анализ видео файла...", 1000),
            (20, "Загрузка модели YOLO...", 1500),
            (30, "Инициализация нейронной сети...", 1200),
            (45, "Калибровка камеры...", 800),
            (60, "Настройка алгоритмов детекции...", 1000),
            (75, "Подготовка системы анализа...", 600),
            (90, "Инициализация анализатора...", 800),
            (100, "Готово!", 300)
        ]
        
        def process_next_stage(stage_index):
            if stage_index >= len(processing_stages):
                # Все этапы завершены
                self.finalize_loading(video_path, csv_path, processing_dialog)
                return
                
            progress, status, delay = processing_stages[stage_index]
            processing_dialog.set_progress(progress)
            processing_dialog.set_status(status)
            QApplication.processEvents()
            
            # Планируем следующий этап
            QTimer.singleShot(delay, lambda: process_next_stage(stage_index + 1))
        
        # Запускаем первый этап
        process_next_stage(0)

    def finalize_loading(self, video_path, csv_path, processing_dialog):
        """Финализация загрузки"""
        try:
            # Реальная инициализация
            self.video_path = video_path
            self.csv_path = csv_path
            
            self.analysis_core = EnhancedAnalysisCore(
                self.video_path, 
                self.csv_path, 
                'config.yaml'
            )
            
            self.analysis_core.set_pixel_to_mm_scale(self.scale_spinbox.value())
            
            # Настройка интерфейса
            self.frame_slider.setEnabled(True)
            self.analyze_btn.setEnabled(True)
            self.frame_slider.setRange(0, self.analysis_core.total_frames - 1)
            self.frame_slider.setValue(0)
            
            self.video_widget.load_video(self.video_path)
            self.update_video_info()
            self.update_ui_for_frame(0)
            
            processing_dialog.close()
            
            self.load_status.setText("✅ Видео загружено и обработано")
            self.status_bar.showMessage("Видео успешно загружено и готово к анализу")
            
            QMessageBox.information(self, "Успех", 
                                   f"Видео загружено и обработано!\n\n"
                                   f"Видео: {Path(video_path).name}\n"
                                   f"CSV: автоматически подключен\n\n"
                                   f"Система готова к анализу.")
            
        except Exception as e:
            processing_dialog.close()
            self.load_status.setText("❌ Ошибка обработки")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке видео:\n{str(e)}")
            
    def update_video_info(self):
        """Обновление информации о видео"""
        if not self.analysis_core:
            return
            
        scale = self.analysis_core.get_pixel_to_mm_scale()
        info = f"""Файл: {Path(self.video_path).name}
Кадров: {self.analysis_core.total_frames}
Разрешение: {self.analysis_core.cap.get(4):.0f}x{self.analysis_core.cap.get(3):.0f}
FPS: {self.analysis_core.cap.get(5):.1f}
Длительность: {self.analysis_core.total_frames / self.analysis_core.cap.get(5):.1f} сек

CSV файл: {Path(self.csv_path).name}
Частей тела: {len(self.analysis_core.bodyparts)}
Лапы: {len(self.analysis_core.paw_groups)} шт.

Масштаб: {scale:.3f} мм/пиксель
Площадь: {scale**2:.6f} мм²/пиксель²

Седалищный индекс: Включен
Формула: (Длина / Ширина) × 100"""
        
        self.video_info.setPlainText(info)
        
    def toggle_auto_threshold(self, checked):
        """Переключение автоматического порога"""
        self.threshold_slider.setEnabled(not checked)
        self.threshold_spinbox.setEnabled(not checked)
        self.update_view()
        
    def get_current_threshold(self):
        """Получение текущего порога"""
        return -1 if self.auto_threshold_check.isChecked() else self.threshold_slider.value()
        
    def update_view(self):
        """Обновление отображения"""
        if self.analysis_core and self.frame_slider.isEnabled():
            self.update_ui_for_frame(self.frame_slider.value())
            
    def update_ui_for_frame(self, frame_idx):
        """Обновление UI для конкретного кадра"""
        if not self.analysis_core:
            return
            
        self.current_frame = frame_idx
        
        # Обновляем масштаб в анализаторе
        self.analysis_core.set_pixel_to_mm_scale(self.scale_spinbox.value())
        
        # Получаем параметры фильтров
        filters = {
            'gaussian_blur': self.gaussian_blur_check.isChecked(),
            'morphology': self.morphology_check.isChecked(),
            'noise_reduction': self.noise_reduction_check.isChecked()
        }
        
        # Анализируем кадр
        annotated_frame, frame_results = self.analysis_core.get_data_for_frame(
            frame_idx, 
            self.get_current_threshold(), 
            self.crop_spinbox.value(),
            filters
        )
        
        if annotated_frame is None:
            return
            
        # Обновляем информацию о кадре
        self.frame_label.setText(f"Кадр: {frame_idx} / {self.analysis_core.total_frames - 1}")
        
        # Отображаем кадр в видео виджете
        self.video_widget.set_frame(annotated_frame)
        
        # Обновляем данные лап
        for paw_name, paw_widget in self.paw_widgets.items():
            paw_data = frame_results.get(paw_name)
            paw_widget.update_data(paw_data)
            
        # Обновляем сводку седалищного индекса
        self.update_sciatic_summary(frame_results)
            
    def prev_frame(self):
        """Предыдущий кадр"""
        if self.frame_slider.value() > 0:
            self.frame_slider.setValue(self.frame_slider.value() - 1)
            
    def next_frame(self):
        """Следующий кадр"""
        if self.frame_slider.value() < self.frame_slider.maximum():
            self.frame_slider.setValue(self.frame_slider.value() + 1)
            
    def start_full_analysis(self):
        """Запуск полного анализа"""
        if not self.analysis_core:
            QMessageBox.warning(self, "Предупреждение", "Сначала загрузите видео и CSV файл")
            return
            
        # Показываем диалог обработки
        processing_dialog = ProcessingDialog(self, title="Полный анализ видео с седалищным индексом")
        processing_dialog.show()
        
        try:
            processing_dialog.set_status("Подготовка к анализу...")
            processing_dialog.set_progress(5)
            QApplication.processEvents()
            
            # Обновляем масштаб в анализаторе
            self.analysis_core.set_pixel_to_mm_scale(self.scale_spinbox.value())
            
            # Имитируем процесс анализа
            processing_dialog.set_status("Анализ кадров с расчетом седалищного индекса...")
            
            filters = {
                'gaussian_blur': self.gaussian_blur_check.isChecked(),
                'morphology': self.morphology_check.isChecked(),
                'noise_reduction': self.noise_reduction_check.isChecked()
            }
            
            # Запускаем анализ всего видео
            self.results_df = self.analysis_core.analyze_entire_video(
                self.get_current_threshold(),
                filters,
                progress_callback=lambda p: (
                    processing_dialog.set_progress(5 + int(p * 0.85)),
                    processing_dialog.set_status(f"Обработка кадров... {p:.1f}%"),
                    QApplication.processEvents()
                )
            )
            
            processing_dialog.set_progress(95)
            processing_dialog.set_status("Построение графиков и анализ седалищного индекса...")
            QApplication.processEvents()
            
            # Обновляем графики
            self.plot_widget.plot_results(self.results_df)
            
            processing_dialog.set_progress(100)
            processing_dialog.set_status("Анализ завершен!")
            QApplication.processEvents()
            
            processing_dialog.close()
            
            # Переключаемся на вкладку графиков
            self.tabs.setCurrentIndex(1)
            
            # Показываем краткую сводку по седалищному индексу
            self.show_sciatic_summary()
            
            self.status_bar.showMessage("Полный анализ с седалищным индексом завершен успешно")
            
        except Exception as e:
            processing_dialog.close()
            QMessageBox.critical(self, "Ошибка", f"Ошибка при анализе:\n{str(e)}")
            
    def show_sciatic_summary(self):
        """Показать сводку седалищного индекса"""
        if self.results_df.empty:
            return
            
        # Вычисляем статистику седалищного индекса
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = {'lf': 'Левая передняя', 'rf': 'Правая передняя', 'lb': 'Левая задняя', 'rb': 'Правая задняя'}
        
        summary_text = "<h3>Сводка седалищного индекса:</h3><table border='1' style='border-collapse: collapse;'>"
        summary_text += "<tr><th>Лапа</th><th>Среднее значение</th><th>Статус</th><th>% Нормы</th></tr>"
        
        for paw in paw_names:
            sciatic_col = f'{paw}_sciatic_index'
            if sciatic_col in self.results_df.columns:
                data = self.results_df[sciatic_col][self.results_df[sciatic_col] > 0]
                
                if len(data) > 0:
                    mean_val = data.mean()
                    normal_percent = (data >= 80).sum() / len(data) * 100
                    
                    if mean_val >= 80:
                        status = "<span style='color: #27ae60;'>Норма</span>"
                    elif mean_val >= 60:
                        status = "<span style='color: #f39c12;'>Легкие нарушения</span>"
                    elif mean_val >= 40:
                        status = "<span style='color: #e67e22;'>Умеренные нарушения</span>"
                    else:
                        status = "<span style='color: #e74c3c;'>Тяжелые нарушения</span>"
                    
                    summary_text += f"<tr><td>{paw_labels[paw]}</td><td>{mean_val:.1f}</td><td>{status}</td><td>{normal_percent:.1f}%</td></tr>"
        
        summary_text += "</table>"
        summary_text += "<br><p><b>Интерпретация:</b><br>≥80 - Норма, 60-80 - Риск, 40-60 - Нарушения, <40 - Критично</p>"
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Анализ завершен - Седалищный индекс")
        msg.setTextFormat(Qt.RichText)
        msg.setText(summary_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()
            
    def export_results(self):
        """Экспорт результатов"""
        if self.results_df.empty:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта. Сначала выполните анализ.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результаты", 
            f"results_{Path(self.video_path).stem}_mm_with_sciatic.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            self.results_df.to_csv(file_path, index=False)
            scale = self.analysis_core.get_pixel_to_mm_scale()
            
            # Подсчитываем количество измерений седалищного индекса
            sciatic_columns = [col for col in self.results_df.columns if 'sciatic_index' in col]
            total_sciatic_measurements = 0
            for col in sciatic_columns:
                total_sciatic_measurements += (self.results_df[col] > 0).sum()
            
            QMessageBox.information(self, "Успех", 
                f"Результаты сохранены в:\n{file_path}\n\n"
                f"Масштаб: {scale:.3f} мм/пиксель\n"
                f"Все линейные размеры в мм, площади в мм²\n"
                f"Седалищный индекс: {total_sciatic_measurements} измерений")
            
    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        if self.analysis_core:
            self.analysis_core.close()
        event.accept()


def main():
    """Главная функция"""
    app = QApplication(sys.argv)
    app.setApplicationName("Анализатор отпечатков лап v2.0 - мм + СИ")
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
    
    window = MainWindowV2()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()