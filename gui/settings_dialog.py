"""
gui/settings_dialog.py
Диалог настроек приложения
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QLabel, QLineEdit, QPushButton,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
                             QGroupBox, QFormLayout, QFileDialog, QMessageBox,
                             QTextEdit, QDialogButtonBox)
from PyQt5.QtCore import Qt
from pathlib import Path


class SettingsDialog(QDialog):
    """Диалог настроек приложения"""
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        
        # Вкладка общих настроек
        self.general_tab = self.create_general_tab()
        self.tabs.addTab(self.general_tab, "Общие")
        
        # Вкладка путей
        self.paths_tab = self.create_paths_tab()
        self.tabs.addTab(self.paths_tab, "Пути к файлам")
        
        # Вкладка обработки
        self.processing_tab = self.create_processing_tab()
        self.tabs.addTab(self.processing_tab, "Обработка")
        
        # Вкладка анализа
        self.analysis_tab = self.create_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "Анализ")
        
        layout.addWidget(self.tabs)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        
        layout.addWidget(buttons)
        
    def create_general_tab(self):
        """Создание вкладки общих настроек"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Группа интерфейса
        ui_group = QGroupBox("Интерфейс")
        ui_layout = QFormLayout()
        
        # Язык
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Русский", "English"])
        ui_layout.addRow("Язык:", self.language_combo)
        
        # Автосохранение
        self.auto_save_check = QCheckBox("Включить автосохранение")
        ui_layout.addRow(self.auto_save_check)
        
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(60, 3600)
        self.auto_save_interval.setSuffix(" сек")
        ui_layout.addRow("Интервал автосохранения:", self.auto_save_interval)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Группа экспериментов
        exp_group = QGroupBox("Эксперименты")
        exp_layout = QFormLayout()
        
        # Директория экспериментов
        self.experiments_dir_layout = QHBoxLayout()
        self.experiments_dir_edit = QLineEdit()
        self.experiments_dir_btn = QPushButton("Обзор...")
        self.experiments_dir_btn.clicked.connect(self.browse_experiments_dir)
        self.experiments_dir_layout.addWidget(self.experiments_dir_edit)
        self.experiments_dir_layout.addWidget(self.experiments_dir_btn)
        
        exp_layout.addRow("Папка экспериментов:", self.experiments_dir_layout)
        
        exp_group.setLayout(exp_layout)
        layout.addWidget(exp_group)
        
        layout.addStretch()
        
        return widget
        
    def create_paths_tab(self):
        """Создание вкладки путей к файлам"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # DeepLabCut файлы
        dlc_group = QGroupBox("Файлы DeepLabCut")
        dlc_layout = QFormLayout()
        
        # Config
        self.config_path_layout = QHBoxLayout()
        self.config_path_edit = QLineEdit()
        self.config_path_btn = QPushButton("Обзор...")
        self.config_path_btn.clicked.connect(lambda: self.browse_file(self.config_path_edit, "YAML Files (*.yaml)"))
        self.config_path_layout.addWidget(self.config_path_edit)
        self.config_path_layout.addWidget(self.config_path_btn)
        dlc_layout.addRow("config.yaml:", self.config_path_layout)
        
        # PyTorch config
        self.pytorch_config_layout = QHBoxLayout()
        self.pytorch_config_edit = QLineEdit()
        self.pytorch_config_btn = QPushButton("Обзор...")
        self.pytorch_config_btn.clicked.connect(lambda: self.browse_file(self.pytorch_config_edit, "YAML Files (*.yaml)"))
        self.pytorch_config_layout.addWidget(self.pytorch_config_edit)
        self.pytorch_config_layout.addWidget(self.pytorch_config_btn)
        dlc_layout.addRow("pytorch_config.yaml:", self.pytorch_config_layout)
        
        # Snapshot
        self.snapshot_layout = QHBoxLayout()
        self.snapshot_edit = QLineEdit()
        self.snapshot_btn = QPushButton("Обзор...")
        self.snapshot_btn.clicked.connect(lambda: self.browse_file(self.snapshot_edit, "PyTorch Files (*.pt *.pth)"))
        self.snapshot_layout.addWidget(self.snapshot_edit)
        self.snapshot_layout.addWidget(self.snapshot_btn)
        dlc_layout.addRow("Веса модели:", self.snapshot_layout)
        
        dlc_group.setLayout(dlc_layout)
        layout.addWidget(dlc_group)
        
        # Калибровка
        cal_group = QGroupBox("Калибровка камеры")
        cal_layout = QFormLayout()
        
        self.calibration_layout = QHBoxLayout()
        self.calibration_edit = QLineEdit()
        self.calibration_btn = QPushButton("Обзор...")
        self.calibration_btn.clicked.connect(lambda: self.browse_file(self.calibration_edit, "JSON Files (*.json)"))
        self.calibration_layout.addWidget(self.calibration_edit)
        self.calibration_layout.addWidget(self.calibration_btn)
        cal_layout.addRow("Файл калибровки:", self.calibration_layout)
        
        # Статус калибровки
        self.calibration_status = QLabel()
        cal_layout.addRow("Статус:", self.calibration_status)
        
        cal_group.setLayout(cal_layout)
        layout.addWidget(cal_group)
        
        # Кнопка проверки
        self.check_paths_btn = QPushButton("Проверить пути")
        self.check_paths_btn.clicked.connect(self.check_paths)
        layout.addWidget(self.check_paths_btn)
        
        layout.addStretch()
        
        return widget
        
    def create_processing_tab(self):
        """Создание вкладки настроек обработки"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Параметры обработки
        proc_group = QGroupBox("Параметры обработки видео")
        proc_layout = QFormLayout()
        
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 32)
        proc_layout.addRow("Размер батча:", self.batch_size_spin)
        
        self.force_reprocess_check = QCheckBox("Принудительная переобработка")
        proc_layout.addRow(self.force_reprocess_check)
        
        self.show_calibration_check = QCheckBox("Показывать информацию о калибровке")
        proc_layout.addRow(self.show_calibration_check)
        
        proc_group.setLayout(proc_layout)
        layout.addWidget(proc_group)
        
        # Параметры DeepLabCut
        dlc_group = QGroupBox("Параметры DeepLabCut")
        dlc_layout = QFormLayout()
        
        self.likelihood_threshold_spin = QDoubleSpinBox()
        self.likelihood_threshold_spin.setRange(0.0, 1.0)
        self.likelihood_threshold_spin.setSingleStep(0.05)
        self.likelihood_threshold_spin.setDecimals(2)
        dlc_layout.addRow("Порог достоверности:", self.likelihood_threshold_spin)
        
        dlc_group.setLayout(dlc_layout)
        layout.addWidget(dlc_group)
        
        layout.addStretch()
        
        return widget
        
    def create_analysis_tab(self):
        """Создание вкладки настроек анализа"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Параметры анализа контактных областей
        contact_group = QGroupBox("Анализ контактных областей")
        contact_layout = QFormLayout()
        
        self.use_adaptive_check = QCheckBox("Использовать адаптивный порог")
        contact_layout.addRow(self.use_adaptive_check)
        
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        contact_layout.addRow("Фиксированный порог:", self.threshold_spin)
        
        self.min_area_spin = QSpinBox()
        self.min_area_spin.setRange(10, 1000)
        self.min_area_spin.setSuffix(" px")
        contact_layout.addRow("Минимальная площадь:", self.min_area_spin)
        
        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)
        
        # Калибровка размеров
        size_group = QGroupBox("Калибровка размеров")
        size_layout = QFormLayout()
        
        self.pixel_to_mm_spin = QDoubleSpinBox()
        self.pixel_to_mm_spin.setRange(0.001, 1.0)
        self.pixel_to_mm_spin.setSingleStep(0.001)
        self.pixel_to_mm_spin.setDecimals(4)
        self.pixel_to_mm_spin.setSuffix(" мм/px")
        size_layout.addRow("Коэффициент преобразования:", self.pixel_to_mm_spin)
        
        # Информация о калибровке
        cal_info = QLabel("Типичные значения:\n"
                         "- Близкая съемка: 0.05-0.1 мм/px\n"
                         "- Средняя дистанция: 0.1-0.2 мм/px\n"
                         "- Дальняя съемка: 0.2-0.5 мм/px")
        cal_info.setStyleSheet("color: gray; font-style: italic;")
        size_layout.addRow(cal_info)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        layout.addStretch()
        
        return widget
        
    def load_settings(self):
        """Загрузка текущих настроек"""
        try:
            # Общие
            self.language_combo.setCurrentIndex(0 if self.config_manager.get('language') == 'ru' else 1)
            self.auto_save_check.setChecked(self.config_manager.get('auto_save', True))
            self.auto_save_interval.setValue(self.config_manager.get('auto_save_interval', 300))
            self.experiments_dir_edit.setText(self.config_manager.get('experiments_dir', 'experiments'))
            
            # Пути
            self.config_path_edit.setText(self.config_manager.get('config_path', ''))
            self.pytorch_config_edit.setText(self.config_manager.get('pytorch_config_path', ''))
            self.snapshot_edit.setText(self.config_manager.get('snapshot_path', ''))
            self.calibration_edit.setText(self.config_manager.get('calibration_file', ''))
            
            # Обновляем статус калибровки
            self.update_calibration_status()
            
            # Обработка
            self.batch_size_spin.setValue(self.config_manager.get('batch_size', 8))
            self.force_reprocess_check.setChecked(self.config_manager.get('force_reprocess', False))
            self.show_calibration_check.setChecked(self.config_manager.get('show_calibration_info', False))
            self.likelihood_threshold_spin.setValue(self.config_manager.get('likelihood_threshold', 0.6))
            
            # Анализ
            self.use_adaptive_check.setChecked(self.config_manager.get('use_adaptive_threshold', True))
            self.threshold_spin.setValue(self.config_manager.get('threshold_value', 128))
            self.min_area_spin.setValue(self.config_manager.get('min_contact_area', 50))
            self.pixel_to_mm_spin.setValue(self.config_manager.get('pixel_to_mm', 0.1))
        except Exception as e:
            print(f"Ошибка при загрузке настроек: {e}")
            # Устанавливаем значения по умолчанию
            self.set_default_values()
    
    def set_default_values(self):
        """Установка значений по умолчанию"""
        self.language_combo.setCurrentIndex(0)
        self.auto_save_check.setChecked(True)
        self.auto_save_interval.setValue(300)
        self.experiments_dir_edit.setText('experiments')
        
        self.batch_size_spin.setValue(8)
        self.force_reprocess_check.setChecked(False)
        self.show_calibration_check.setChecked(False)
        self.likelihood_threshold_spin.setValue(0.6)
        
        self.use_adaptive_check.setChecked(True)
        self.threshold_spin.setValue(128)
        self.min_area_spin.setValue(50)
        self.pixel_to_mm_spin.setValue(0.1)
        
        self.calibration_status.setText("Калибровка не выполнена")
        self.calibration_status.setStyleSheet("color: orange;")
        
    def save_settings(self):
        """Сохранение настроек"""
        try:
            # Общие
            self.config_manager.set('language', 'ru' if self.language_combo.currentIndex() == 0 else 'en')
            self.config_manager.set('auto_save', self.auto_save_check.isChecked())
            self.config_manager.set('auto_save_interval', self.auto_save_interval.value())
            self.config_manager.set('experiments_dir', self.experiments_dir_edit.text())
            
            # Пути
            self.config_manager.set('config_path', self.config_path_edit.text())
            self.config_manager.set('pytorch_config_path', self.pytorch_config_edit.text())
            self.config_manager.set('snapshot_path', self.snapshot_edit.text())
            self.config_manager.set('calibration_file', self.calibration_edit.text())
            
            # Обработка
            self.config_manager.set('batch_size', self.batch_size_spin.value())
            self.config_manager.set('force_reprocess', self.force_reprocess_check.isChecked())
            self.config_manager.set('show_calibration_info', self.show_calibration_check.isChecked())
            self.config_manager.set('likelihood_threshold', self.likelihood_threshold_spin.value())
            
            # Анализ
            self.config_manager.set('use_adaptive_threshold', self.use_adaptive_check.isChecked())
            self.config_manager.set('threshold_value', self.threshold_spin.value())
            self.config_manager.set('min_contact_area', self.min_area_spin.value())
            self.config_manager.set('pixel_to_mm', self.pixel_to_mm_spin.value())
            
            self.config_manager.save_config()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
        
    def browse_experiments_dir(self):
        """Выбор директории экспериментов"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Выберите папку для экспериментов",
            self.experiments_dir_edit.text()
        )
        if dir_path:
            self.experiments_dir_edit.setText(dir_path)
            
    def browse_file(self, line_edit, file_filter):
        """Выбор файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл",
            line_edit.text(),
            file_filter
        )
        if file_path:
            line_edit.setText(file_path)
            
    def check_paths(self):
        """Проверка путей к файлам"""
        missing = []
        
        paths_to_check = {
            "config.yaml": self.config_path_edit.text(),
            "pytorch_config.yaml": self.pytorch_config_edit.text(),
            "Веса модели": self.snapshot_edit.text()
        }
        
        for name, path in paths_to_check.items():
            if not path or not Path(path).exists():
                missing.append(f"- {name}: {path if path else 'не указан'}")
                
        if missing:
            QMessageBox.warning(
                self, "Проверка путей",
                "Следующие файлы не найдены:\n" + "\n".join(missing)
            )
        else:
            QMessageBox.information(
                self, "Проверка путей",
                "Все файлы найдены успешно!"
            )
            
    def update_calibration_status(self):
        """Обновление статуса калибровки"""
        try:
            cal_status = self.config_manager.get_calibration_status()
            
            if cal_status.get('calibrated', False):
                # Безопасное форматирование значений
                error_val = cal_status.get('error')
                pixel_to_mm_val = cal_status.get('pixel_to_mm')
                
                status_text = "✓ Калибровка выполнена\n"
                
                # Обрабатываем ошибку
                if error_val is not None:
                    try:
                        error_float = float(error_val)
                        status_text += f"Ошибка: {error_float:.3f}\n"
                    except (ValueError, TypeError):
                        status_text += f"Ошибка: {error_val}\n"
                else:
                    status_text += "Ошибка: н/д\n"
                
                # Обрабатываем коэффициент
                if pixel_to_mm_val is not None:
                    try:
                        pixel_to_mm_float = float(pixel_to_mm_val)
                        status_text += f"Коэффициент: {pixel_to_mm_float:.4f} мм/px"
                    except (ValueError, TypeError):
                        status_text += f"Коэффициент: {pixel_to_mm_val} мм/px"
                else:
                    status_text += "Коэффициент: н/д"
                
                self.calibration_status.setText(status_text)
                self.calibration_status.setStyleSheet("color: green;")
            else:
                self.calibration_status.setText("✗ Калибровка не выполнена")
                self.calibration_status.setStyleSheet("color: orange;")
                
        except Exception as e:
            print(f"Ошибка при обновлении статуса калибровки: {e}")
            self.calibration_status.setText("Ошибка при проверке калибровки")
            self.calibration_status.setStyleSheet("color: red;")
            
    def restore_defaults(self):
        """Восстановление значений по умолчанию"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Восстановить все настройки по умолчанию?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.config_manager.reset_to_defaults()
                self.load_settings()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось восстановить настройки: {e}")
            
    def accept(self):
        """Принятие изменений"""
        self.save_settings()
        super().accept()