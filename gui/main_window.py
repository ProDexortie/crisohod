"""
gui/main_window.py
Главное окно приложения
"""

import os
from pathlib import Path
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QMessageBox,
                             QTabWidget, QStatusBar, QToolBar, QAction,
                             QDockWidget, QSplitter, QGroupBox, QComboBox,
                             QProgressBar, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPixmap

from .video_player import VideoPlayer
from .results_viewer import ResultsViewer
from .experiment_manager import ExperimentManager
from .settings_dialog import SettingsDialog
from processing.dlc_processor import DLCProcessor
from processing.video_preprocessor import VideoPreprocessor
from analysis.paw_analyzer import EnhancedPawAnalyzer


class ProcessingThread(QThread):
    """Поток для обработки видео"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, video_path, config_manager):
        super().__init__()
        self.video_path = video_path
        self.config_manager = config_manager
        self.is_cancelled = False
        
    def run(self):
        try:
            # 1. Предобработка видео
            self.status.emit("Применение калибровки камеры...")
            self.progress.emit(10)
            
            preprocessor = VideoPreprocessor(self.config_manager)
            calibrated_video = preprocessor.process_video(self.video_path)
            
            if self.is_cancelled:
                return
            
            # 2. Обработка через DeepLabCut
            self.status.emit("Анализ позы с помощью DeepLabCut...")
            self.progress.emit(30)
            
            dlc_processor = DLCProcessor(self.config_manager)
            csv_path = dlc_processor.process_video(calibrated_video)
            
            if self.is_cancelled:
                return
            
            # 3. Анализ параметров лап
            self.status.emit("Анализ контактных областей и параметров лап...")
            self.progress.emit(70)
            
            analyzer = EnhancedPawAnalyzer(self.config_manager)
            results = analyzer.analyze_video(calibrated_video, csv_path)
            
            if self.is_cancelled:
                return
            
            self.progress.emit(100)
            self.status.emit("Обработка завершена!")
            
            # Возвращаем результаты
            self.finished.emit({
                'original_video': self.video_path,
                'calibrated_video': calibrated_video,
                'csv_path': csv_path,
                'results': results
            })
            
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True


class MainWindow(QMainWindow):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.current_experiment = None
        self.processing_thread = None
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Система анализа физиологических параметров лабораторных животных")
        self.setGeometry(100, 100, 1400, 900)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout(central_widget)
        
        # Создаем меню
        self.create_menu_bar()
        
        # Создаем панель инструментов
        self.create_toolbar()
        
        # Создаем основной сплиттер
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Левая панель - управление экспериментами
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Центральная панель - видео и результаты
        center_panel = self.create_center_panel()
        main_splitter.addWidget(center_panel)
        
        # Правая панель - детальная информация
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Настройка размеров сплиттера
        main_splitter.setSizes([250, 900, 250])
        
        main_layout.addWidget(main_splitter)
        
        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
    def create_menu_bar(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu('Файл')
        
        new_experiment = QAction('Новый эксперимент', self)
        new_experiment.setShortcut('Ctrl+N')
        new_experiment.triggered.connect(self.new_experiment)
        file_menu.addAction(new_experiment)
        
        open_experiment = QAction('Открыть эксперимент', self)
        open_experiment.setShortcut('Ctrl+O')
        open_experiment.triggered.connect(self.open_experiment)
        file_menu.addAction(open_experiment)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Выход', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Обработка
        process_menu = menubar.addMenu('Обработка')
        
        process_video = QAction('Обработать видео', self)
        process_video.setShortcut('F5')
        process_video.triggered.connect(self.process_video)
        process_menu.addAction(process_video)
        
        calibrate_camera = QAction('Калибровка камеры', self)
        calibrate_camera.triggered.connect(self.calibrate_camera)
        process_menu.addAction(calibrate_camera)
        
        # Меню Настройки
        settings_menu = menubar.addMenu('Настройки')
        
        preferences = QAction('Параметры', self)
        preferences.triggered.connect(self.show_settings)
        settings_menu.addAction(preferences)
        
        # Меню Помощь
        help_menu = menubar.addMenu('Помощь')
        
        about = QAction('О программе', self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)
        
    def create_toolbar(self):
        """Создание панели инструментов"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Кнопка выбора видео
        self.select_video_btn = QPushButton("Выбрать видео")
        self.select_video_btn.clicked.connect(self.select_video)
        toolbar.addWidget(self.select_video_btn)
        
        # Кнопка записи видео
        self.record_video_btn = QPushButton("Записать видео")
        self.record_video_btn.clicked.connect(self.record_video)
        toolbar.addWidget(self.record_video_btn)
        
        toolbar.addSeparator()
        
        # Кнопка обработки
        self.process_btn = QPushButton("Обработать")
        self.process_btn.clicked.connect(self.process_video)
        self.process_btn.setEnabled(False)
        toolbar.addWidget(self.process_btn)
        
        # Кнопка остановки
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        toolbar.addWidget(self.stop_btn)
        
        toolbar.addSeparator()
        
        # Выбор эксперимента
        toolbar.addWidget(QLabel("Эксперимент:"))
        self.experiment_combo = QComboBox()
        self.experiment_combo.setMinimumWidth(200)
        toolbar.addWidget(self.experiment_combo)
        
    def create_left_panel(self):
        """Создание левой панели"""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        
        # Менеджер экспериментов
        self.experiment_manager = ExperimentManager(self.config_manager)
        layout.addWidget(self.experiment_manager)
        
        # Информация о текущем видео
        info_group = QGroupBox("Информация о видео")
        info_layout = QVBoxLayout(info_group)
        
        self.video_info = QTextEdit()
        self.video_info.setReadOnly(True)
        self.video_info.setMaximumHeight(200)
        info_layout.addWidget(self.video_info)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        return left_widget
        
    def create_center_panel(self):
        """Создание центральной панели"""
        center_widget = QWidget()
        layout = QVBoxLayout(center_widget)
        
        # Табы для видео и результатов
        self.main_tabs = QTabWidget()
        
        # Вкладка видео
        self.video_player = VideoPlayer()
        self.main_tabs.addTab(self.video_player, "Видео")
        
        # Вкладка результатов
        self.results_viewer = ResultsViewer()
        self.main_tabs.addTab(self.results_viewer, "Результаты")
        
        layout.addWidget(self.main_tabs)
        
        return center_widget
        
    def create_right_panel(self):
        """Создание правой панели"""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        
        # Параметры лап
        paw_group = QGroupBox("Параметры лап")
        paw_layout = QVBoxLayout(paw_group)
        
        self.paw_info = QTextEdit()
        self.paw_info.setReadOnly(True)
        paw_layout.addWidget(self.paw_info)
        
        layout.addWidget(paw_group)
        
        # Настройки анализа
        settings_group = QGroupBox("Параметры анализа")
        settings_layout = QVBoxLayout(settings_group)
        
        self.threshold_slider = self.create_threshold_control()
        settings_layout.addWidget(self.threshold_slider)
        
        layout.addWidget(settings_group)
        
        layout.addStretch()
        
        return right_widget
        
    def create_threshold_control(self):
        """Создание контроля порога"""
        from PyQt5.QtWidgets import QSlider, QSpinBox
        
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        layout.addWidget(QLabel("Порог:"))
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(128)
        layout.addWidget(self.threshold_slider)
        
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        self.threshold_spin.setValue(128)
        layout.addWidget(self.threshold_spin)
        
        # Связываем slider и spinbox
        self.threshold_slider.valueChanged.connect(self.threshold_spin.setValue)
        self.threshold_spin.valueChanged.connect(self.threshold_slider.setValue)
        
        return widget
        
    def setup_connections(self):
        """Настройка соединений сигналов"""
        # Видео плеер
        self.video_player.frame_changed.connect(self.on_frame_changed)
        
        # Менеджер экспериментов
        self.experiment_manager.experiment_selected.connect(self.load_experiment)
        
        # Результаты
        self.results_viewer.point_selected.connect(self.on_result_point_selected)
        
    def select_video(self):
        """Выбор видео файла"""
        video_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать видео", 
            str(self.config_manager.get_last_video_dir()),
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if video_path:
            self.load_video(video_path)
            self.config_manager.set_last_video_dir(os.path.dirname(video_path))
            
    def record_video(self):
        """Запись видео (заглушка)"""
        QMessageBox.information(self, "Запись видео", 
                               "Функция записи видео будет реализована в следующей версии")
        
    def load_video(self, video_path):
        """Загрузка видео"""
        self.video_player.load_video(video_path)
        self.process_btn.setEnabled(True)
        
        # Обновляем информацию о видео
        video_info = self.video_player.get_video_info()
        info_text = f"Файл: {os.path.basename(video_path)}\n"
        info_text += f"Разрешение: {video_info['width']}x{video_info['height']}\n"
        info_text += f"FPS: {video_info['fps']}\n"
        info_text += f"Кадров: {video_info['total_frames']}\n"
        info_text += f"Длительность: {video_info['duration']:.1f} сек"
        
        self.video_info.setPlainText(info_text)
        
    def process_video(self):
        """Обработка видео"""
        if not self.video_player.video_path:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите видео")
            return
            
        # Запускаем обработку в отдельном потоке
        self.processing_thread = ProcessingThread(
            self.video_player.video_path,
            self.config_manager
        )
        
        self.processing_thread.progress.connect(self.update_progress)
        self.processing_thread.status.connect(self.update_status)
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.error.connect(self.on_processing_error)
        
        self.processing_thread.start()
        
        # Обновляем UI
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        
    def stop_processing(self):
        """Остановка обработки"""
        if self.processing_thread:
            self.processing_thread.cancel()
            self.processing_thread.wait()
            
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Обработка отменена")
        
    def update_progress(self, value):
        """Обновление прогресса"""
        self.progress_bar.setValue(value)
        
    def update_status(self, message):
        """Обновление статуса"""
        self.status_bar.showMessage(message)
        
    def on_processing_finished(self, results):
        """Обработка завершена"""
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Загружаем результаты
        self.video_player.load_processed_video(
            results['calibrated_video'],
            results['csv_path']
        )
        
        self.results_viewer.load_results(results['results'])
        
        # Переключаемся на вкладку результатов
        self.main_tabs.setCurrentIndex(1)
        
        QMessageBox.information(self, "Успех", "Обработка видео завершена!")
        
    def on_processing_error(self, error_message):
        """Ошибка обработки"""
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Ошибка", f"Ошибка при обработке видео:\n{error_message}")
        
    def on_frame_changed(self, frame_number):
        """Изменение текущего кадра"""
        if self.results_viewer.has_results():
            # Обновляем информацию о лапах для текущего кадра
            paw_data = self.results_viewer.get_frame_data(frame_number)
            self.update_paw_info(paw_data)
            
    def update_paw_info(self, paw_data):
        """Обновление информации о лапах"""
        if not paw_data:
            self.paw_info.clear()
            return
            
        info_text = f"Кадр: {paw_data.get('frame', 'N/A')}\n\n"
        
        paw_names = {
            'lf': 'Левая передняя',
            'rf': 'Правая передняя',
            'lb': 'Левая задняя',
            'rb': 'Правая задняя'
        }
        
        for paw_id, paw_name in paw_names.items():
            info_text += f"{paw_name}:\n"
            info_text += f"  Площадь: {paw_data.get(f'{paw_id}_area_mm2', 0):.1f} мм²\n"
            
            if paw_id.endswith('b'):  # Задние лапы
                info_text += f"  Длина: {paw_data.get(f'{paw_id}_length_mm', 0):.1f} мм\n"
                info_text += f"  Ширина (1-5): {paw_data.get(f'{paw_id}_width_1_5_mm', 0):.1f} мм\n"
                info_text += f"  Ширина (2-4): {paw_data.get(f'{paw_id}_width_2_4_mm', 0):.1f} мм\n"
            else:  # Передние лапы
                info_text += f"  Длина: {paw_data.get(f'{paw_id}_length_mm', 0):.1f} мм\n"
                
            info_text += "\n"
            
        self.paw_info.setPlainText(info_text)
        
    def on_result_point_selected(self, frame_number):
        """Выбрана точка на графике результатов"""
        self.video_player.seek_to_frame(frame_number)
        
    def calibrate_camera(self):
        """Открыть диалог калибровки камеры"""
        from .calibration_dialog import CalibrationDialog
        dialog = CalibrationDialog(self.config_manager, self)
        dialog.exec_()
        
    def show_settings(self):
        """Показать настройки"""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec_():
            # Применяем новые настройки
            self.config_manager.save_config()
            
    def new_experiment(self):
        """Создать новый эксперимент"""
        self.experiment_manager.new_experiment()
        
    def open_experiment(self):
        """Открыть эксперимент"""
        self.experiment_manager.open_experiment()
        
    def load_experiment(self, experiment_path):
        """Загрузить эксперимент"""
        self.current_experiment = experiment_path
        self.update_experiment_combo()
        
    def update_experiment_combo(self):
        """Обновить список экспериментов"""
        self.experiment_combo.clear()
        experiments = self.experiment_manager.get_experiments()
        self.experiment_combo.addItems([exp.name for exp in experiments])
        
    def show_about(self):
        """Показать информацию о программе"""
        about_text = """
        <h3>Система анализа физиологических параметров лабораторных животных</h3>
        <p>Версия 1.0</p>
        <p>Разработано для анализа параметров походки лабораторных крыс</p>
        <br>
        <p><b>Основные возможности:</b></p>
        <ul>
        <li>Автоматическая калибровка камеры</li>
        <li>Анализ позы с помощью DeepLabCut</li>
        <li>Измерение площади контакта лап</li>
        <li>Расчет морфометрических параметров</li>
        </ul>
        """
        QMessageBox.about(self, "О программе", about_text)
        
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        reply = QMessageBox.question(
            self, 'Выход',
            'Вы уверены, что хотите выйти?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Останавливаем обработку если идет
            if self.processing_thread and self.processing_thread.isRunning():
                self.processing_thread.cancel()
                self.processing_thread.wait()
            event.accept()
        else:
            event.ignore()