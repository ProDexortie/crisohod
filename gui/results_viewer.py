"""
gui/results_viewer.py
Виджет для отображения результатов анализа
"""

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QComboBox, QLabel, QGroupBox, QSplitter,
                             QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import cv2


class MplCanvas(FigureCanvas):
    """Matplotlib canvas для встраивания в Qt"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#353535')
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Настройка стиля
        plt.style.use('dark_background')
        

class ResultsViewer(QWidget):
    """Виджет для отображения результатов анализа"""
    point_selected = pyqtSignal(int)  # Сигнал при выборе точки на графике
    
    def __init__(self):
        super().__init__()
        self.results_data = None
        self.current_frame = 0
        self.init_ui()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Создаем табы для разных типов результатов
        self.tabs = QTabWidget()
        
        # Вкладка графиков
        self.graphs_widget = self.create_graphs_widget()
        self.tabs.addTab(self.graphs_widget, "Графики")
        
        # Вкладка таблицы
        self.table_widget = self.create_table_widget()
        self.tabs.addTab(self.table_widget, "Таблица данных")
        
        # Вкладка статистики
        self.stats_widget = self.create_stats_widget()
        self.tabs.addTab(self.stats_widget, "Статистика")
        
        # Вкладка визуализации лап
        self.paw_viz_widget = self.create_paw_visualization_widget()
        self.tabs.addTab(self.paw_viz_widget, "Визуализация лап")
        
        layout.addWidget(self.tabs)
        
    def create_graphs_widget(self):
        """Создание виджета с графиками"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Контролы для выбора данных
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Параметр:"))
        self.param_combo = QComboBox()
        self.param_combo.addItems([
            "Площадь контакта",
            "Длина лапы",
            "Ширина лапы (1-5)",
            "Ширина лапы (2-4)"
        ])
        self.param_combo.currentIndexChanged.connect(self.update_graphs)
        controls_layout.addWidget(self.param_combo)
        
        controls_layout.addWidget(QLabel("Лапа:"))
        self.paw_combo = QComboBox()
        self.paw_combo.addItems([
            "Все",
            "Левая передняя (LF)",
            "Правая передняя (RF)",
            "Левая задняя (LB)",
            "Правая задняя (RB)"
        ])
        self.paw_combo.currentIndexChanged.connect(self.update_graphs)
        controls_layout.addWidget(self.paw_combo)
        
        controls_layout.addStretch()
        
        self.export_btn = QPushButton("Экспорт")
        self.export_btn.clicked.connect(self.export_data)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)
        
        # Canvas для графиков
        self.graph_canvas = MplCanvas(self, width=8, height=6, dpi=80)
        layout.addWidget(self.graph_canvas)
        
        return widget
        
    def create_table_widget(self):
        """Создание виджета с таблицей данных"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица
        self.data_table = QTableWidget()
        self.data_table.setSortingEnabled(True)
        self.data_table.setAlternatingRowColors(True)
        layout.addWidget(self.data_table)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.filter_btn = QPushButton("Фильтр")
        self.filter_btn.clicked.connect(self.show_filter_dialog)
        buttons_layout.addWidget(self.filter_btn)
        
        self.export_table_btn = QPushButton("Экспорт в CSV")
        self.export_table_btn.clicked.connect(self.export_table)
        buttons_layout.addWidget(self.export_table_btn)
        
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return widget
        
    def create_stats_widget(self):
        """Создание виджета со статистикой"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Создаем группы для разных типов статистики
        splitter = QSplitter(Qt.Vertical)
        
        # Общая статистика
        general_group = QGroupBox("Общая статистика")
        general_layout = QVBoxLayout(general_group)
        self.general_stats_table = QTableWidget()
        self.general_stats_table.setColumnCount(2)
        self.general_stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        general_layout.addWidget(self.general_stats_table)
        splitter.addWidget(general_group)
        
        # Статистика по лапам
        paw_group = QGroupBox("Статистика по лапам")
        paw_layout = QVBoxLayout(paw_group)
        self.paw_stats_table = QTableWidget()
        self.paw_stats_table.setColumnCount(5)
        self.paw_stats_table.setHorizontalHeaderLabels([
            "Лапа", "Средняя площадь (мм²)", "Макс площадь (мм²)",
            "Средняя длина (мм)", "Средняя ширина (мм)"
        ])
        paw_layout.addWidget(self.paw_stats_table)
        splitter.addWidget(paw_group)
        
        layout.addWidget(splitter)
        
        return widget
        
    def create_paw_visualization_widget(self):
        """Создание виджета визуализации лап"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Контролы
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Кадр:"))
        self.frame_combo = QComboBox()
        self.frame_combo.currentIndexChanged.connect(self.update_paw_visualization)
        controls_layout.addWidget(self.frame_combo)
        
        controls_layout.addWidget(QLabel("Режим:"))
        self.viz_mode_combo = QComboBox()
        self.viz_mode_combo.addItems([
            "Контактные области",
            "Тепловая карта",
            "Контуры",
            "3D визуализация"
        ])
        self.viz_mode_combo.currentIndexChanged.connect(self.update_paw_visualization)
        controls_layout.addWidget(self.viz_mode_combo)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Область для изображений лап
        paw_images_layout = QHBoxLayout()
        
        # Создаем label для каждой лапы
        self.paw_labels = {}
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_titles = {
            'lf': 'Левая передняя',
            'rf': 'Правая передняя',
            'lb': 'Левая задняя',
            'rb': 'Правая задняя'
        }
        
        for paw in paw_names:
            paw_widget = QWidget()
            paw_layout = QVBoxLayout(paw_widget)
            
            title_label = QLabel(paw_titles[paw])
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-weight: bold; color: #ff8c00;")
            paw_layout.addWidget(title_label)
            
            img_label = QLabel()
            img_label.setMinimumSize(200, 200)
            img_label.setMaximumSize(300, 300)
            img_label.setScaledContents(True)
            img_label.setStyleSheet("border: 1px solid #505050;")
            self.paw_labels[paw] = img_label
            paw_layout.addWidget(img_label)
            
            info_label = QLabel()
            info_label.setAlignment(Qt.AlignCenter)
            self.paw_labels[f'{paw}_info'] = info_label
            paw_layout.addWidget(info_label)
            
            paw_images_layout.addWidget(paw_widget)
            
        layout.addLayout(paw_images_layout)
        
        # Canvas для дополнительной визуализации
        self.viz_canvas = MplCanvas(self, width=8, height=4, dpi=80)
        layout.addWidget(self.viz_canvas)
        
        return widget
        
    def load_results(self, results):
        """Загрузка результатов анализа"""
        self.results_data = results
        
        # Обновляем все виджеты
        self.update_graphs()
        self.update_table()
        self.update_statistics()
        self.update_frame_combo()
        
    def has_results(self):
        """Проверка наличия результатов"""
        return self.results_data is not None
        
    def get_frame_data(self, frame_number):
        """Получение данных для конкретного кадра"""
        if not self.has_results() or 'frame_data' not in self.results_data:
            return None
            
        frame_data = self.results_data['frame_data']
        if isinstance(frame_data, pd.DataFrame):
            if frame_number < len(frame_data):
                return frame_data.iloc[frame_number].to_dict()
        elif isinstance(frame_data, list):
            if frame_number < len(frame_data):
                return frame_data[frame_number]
                
        return None
        
    def update_graphs(self):
        """Обновление графиков"""
        if not self.has_results():
            return
            
        self.graph_canvas.fig.clear()
        
        # Получаем выбранные параметры
        param_idx = self.param_combo.currentIndex()
        paw_idx = self.paw_combo.currentIndex()
        
        # Маппинг параметров
        param_map = {
            0: 'area_mm2',
            1: 'length_mm',
            2: 'width_1_5_mm',
            3: 'width_2_4_mm'
        }
        
        paw_map = {
            1: 'lf',
            2: 'rf',
            3: 'lb',
            4: 'rb'
        }
        
        # Создаем график
        ax = self.graph_canvas.fig.add_subplot(111)
        ax.set_facecolor('#2a2a2a')
        
        df = pd.DataFrame(self.results_data['frame_data'])
        
        if paw_idx == 0:  # Все лапы
            colors = ['#ff6666', '#66ff66', '#6666ff', '#ffff66']
            labels = ['LF', 'RF', 'LB', 'RB']
            
            for i, (paw, label) in enumerate(zip(['lf', 'rf', 'lb', 'rb'], labels)):
                column = f'{paw}_{param_map[param_idx]}'
                if column in df.columns:
                    ax.plot(df.index, df[column], color=colors[i], 
                           label=label, linewidth=2)
        else:
            # Одна лапа
            paw = paw_map[paw_idx]
            column = f'{paw}_{param_map[param_idx]}'
            if column in df.columns:
                ax.plot(df.index, df[column], color='#ff8c00', linewidth=2)
                
        ax.set_xlabel('Кадр', color='white')
        ax.set_ylabel(self.param_combo.currentText(), color='white')
        ax.set_title(f'{self.param_combo.currentText()} - {self.paw_combo.currentText()}',
                    color='white', fontweight='bold')
        
        ax.grid(True, alpha=0.3, color='gray')
        ax.tick_params(colors='white')
        
        if paw_idx == 0:
            ax.legend(facecolor='#353535', edgecolor='#505050')
            
        # Делаем график интерактивным
        def on_click(event):
            if event.inaxes == ax:
                frame = int(event.xdata)
                self.point_selected.emit(frame)
                
        self.graph_canvas.mpl_connect('button_press_event', on_click)
        
        self.graph_canvas.draw()
        
    def update_table(self):
        """Обновление таблицы данных"""
        if not self.has_results():
            return
            
        df = pd.DataFrame(self.results_data['frame_data'])
        
        # Настройка таблицы
        self.data_table.setRowCount(len(df))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(df.columns.tolist())
        
        # Заполнение данными
        for i in range(len(df)):
            for j in range(len(df.columns)):
                value = df.iloc[i, j]
                if isinstance(value, float):
                    item = QTableWidgetItem(f"{value:.2f}")
                else:
                    item = QTableWidgetItem(str(value))
                self.data_table.setItem(i, j, item)
                
        # Настройка внешнего вида
        self.data_table.resizeColumnsToContents()
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(True)
        
    def update_statistics(self):
        """Обновление статистики"""
        if not self.has_results():
            return
            
        stats = self.results_data.get('statistics', {})
        
        # Общая статистика
        self.general_stats_table.setRowCount(5)
        
        general_items = [
            ("Всего кадров", stats.get('total_frames', 0)),
            ("Длительность (с)", f"{stats.get('duration', 0):.1f}"),
            ("FPS", stats.get('fps', 30)),
            ("Средняя общая площадь контакта (мм²)", 
             f"{stats.get('avg_total_contact_area', 0):.1f}"),
            ("Максимальная общая площадь контакта (мм²)", 
             f"{stats.get('max_total_contact_area', 0):.1f}")
        ]
        
        for i, (param, value) in enumerate(general_items):
            self.general_stats_table.setItem(i, 0, QTableWidgetItem(param))
            self.general_stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
            
        # Статистика по лапам
        self.paw_stats_table.setRowCount(4)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = ['Левая передняя', 'Правая передняя', 
                     'Левая задняя', 'Правая задняя']
        
        for i, (paw, label) in enumerate(zip(paw_names, paw_labels)):
            paw_stats = stats.get(f'{paw}_stats', {})
            
            self.paw_stats_table.setItem(i, 0, QTableWidgetItem(label))
            self.paw_stats_table.setItem(i, 1, 
                QTableWidgetItem(f"{paw_stats.get('avg_area', 0):.1f}"))
            self.paw_stats_table.setItem(i, 2, 
                QTableWidgetItem(f"{paw_stats.get('max_area', 0):.1f}"))
            self.paw_stats_table.setItem(i, 3, 
                QTableWidgetItem(f"{paw_stats.get('avg_length', 0):.1f}"))
            self.paw_stats_table.setItem(i, 4, 
                QTableWidgetItem(f"{paw_stats.get('avg_width', 0):.1f}"))
                
    def update_frame_combo(self):
        """Обновление комбобокса с кадрами"""
        if not self.has_results():
            return
            
        frame_data = self.results_data.get('frame_data', [])
        self.frame_combo.clear()
        
        # Добавляем ключевые кадры
        total_frames = len(frame_data)
        key_frames = [0, total_frames // 4, total_frames // 2, 
                     3 * total_frames // 4, total_frames - 1]
        
        for frame in key_frames:
            if frame < total_frames:
                self.frame_combo.addItem(f"Кадр {frame}")
                
    def update_paw_visualization(self):
        """Обновление визуализации лап"""
        if not self.has_results():
            return
            
        frame_idx = self.frame_combo.currentIndex()
        if frame_idx < 0:
            return
            
        # Получаем номер кадра из текста
        frame_text = self.frame_combo.currentText()
        frame_number = int(frame_text.split()[1])
        
        # Получаем изображения лап для этого кадра
        paw_images = self.results_data.get('paw_images', {})
        
        if frame_number in paw_images:
            frame_paw_images = paw_images[frame_number]
            
            for paw in ['lf', 'rf', 'lb', 'rb']:
                if paw in frame_paw_images:
                    img_data = frame_paw_images[paw]
                    
                    # Конвертируем в QPixmap
                    height, width, channel = img_data.shape
                    bytes_per_line = 3 * width
                    q_image = QImage(img_data.data, width, height, 
                                   bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)
                    
                    self.paw_labels[paw].setPixmap(pixmap)
                    
                    # Обновляем информацию
                    frame_data = self.get_frame_data(frame_number)
                    if frame_data:
                        area = frame_data.get(f'{paw}_area_mm2', 0)
                        self.paw_labels[f'{paw}_info'].setText(f"{area:.1f} мм²")
                        
    def export_data(self):
        """Экспорт данных"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить данные", "", 
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if filename:
            df = pd.DataFrame(self.results_data['frame_data'])
            
            if filename.endswith('.xlsx'):
                df.to_excel(filename, index=False)
            else:
                df.to_csv(filename, index=False)
                
    def export_table(self):
        """Экспорт таблицы"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить таблицу", "", "CSV Files (*.csv)"
        )
        
        if filename:
            # Собираем данные из таблицы
            rows = self.data_table.rowCount()
            cols = self.data_table.columnCount()
            
            data = []
            headers = []
            
            for col in range(cols):
                header = self.data_table.horizontalHeaderItem(col)
                headers.append(header.text() if header else f"Column {col}")
                
            for row in range(rows):
                row_data = []
                for col in range(cols):
                    item = self.data_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
                
            df = pd.DataFrame(data, columns=headers)
            df.to_csv(filename, index=False)
            
    def show_filter_dialog(self):
        """Показать диалог фильтрации"""
        # TODO: Реализовать диалог фильтрации
        pass