"""
advanced_plot_widget.py
Виджет для создания графиков и статистики анализа лап крыс
"""

import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFrame,
    QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QTextEdit, QScrollArea, QSplitter,
    QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns

# Настройка стиля matplotlib для темной темы
plt.style.use('dark_background')
sns.set_palette("bright")


class PlotCanvas(FigureCanvas):
    """Холст для matplotlib графиков"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2a2a2a')
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Настройка стиля
        self.fig.patch.set_facecolor('#2a2a2a')


class StatisticsWidget(QFrame):
    """Виджет для отображения статистики"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                margin: 5px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QTableWidget {
                background-color: #1a1a1a;
                border: 1px solid #404040;
                gridline-color: #404040;
                color: white;
                selection-background-color: #4a90e2;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #404040;
            }
            QHeaderView::section {
                background-color: #404040;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("Общая статистика")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4a90e2; margin: 10px;")
        layout.addWidget(title)
        
        # Таблица общей статистики
        self.general_table = QTableWidget()
        self.general_table.setRowCount(4)
        self.general_table.setColumnCount(2)
        self.general_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.general_table.verticalHeader().setVisible(False)
        layout.addWidget(self.general_table)
        
        # Заголовок статистики по лапам
        paws_title = QLabel("Статистика по лапам")
        paws_title.setAlignment(Qt.AlignCenter)
        paws_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4a90e2; margin: 10px;")
        layout.addWidget(paws_title)
        
        # Таблица статистики по лапам
        self.paws_table = QTableWidget()
        layout.addWidget(self.paws_table)
        
        # Заголовок седалищного индекса
        sciatic_title = QLabel("Седалищный индекс")
        sciatic_title.setAlignment(Qt.AlignCenter)
        sciatic_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c; margin: 10px;")
        layout.addWidget(sciatic_title)
        
        # Таблица седалищного индекса
        self.sciatic_table = QTableWidget()
        layout.addWidget(self.sciatic_table)
        
        # Корреляционный анализ
        corr_title = QLabel("Корреляционный анализ")
        corr_title.setAlignment(Qt.AlignCenter)
        corr_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4a90e2; margin: 10px;")
        layout.addWidget(corr_title)
        
        self.correlation_text = QTextEdit()
        self.correlation_text.setMaximumHeight(150)
        self.correlation_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #404040;
                border-radius: 4px;
                color: white;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.correlation_text)
        
    def update_statistics(self, df):
        """Обновление статистики"""
        if df.empty:
            return
            
        # Общая статистика
        total_frames = len(df)
        duration = total_frames / 30.0 if total_frames > 0 else 0  # Предполагаем 30 FPS
        
        # Активность (процент кадров с контактом)
        activity = 0.0
        paw_names = ['lf', 'rf', 'lb', 'rb']
        
        total_contact_frames = 0
        for paw in paw_names:
            area_col = f'{paw}_area_mm2'
            if area_col in df.columns:
                contact_frames = (df[area_col] > 0).sum()
                total_contact_frames += contact_frames
        
        if total_frames > 0:
            activity = (total_contact_frames / (total_frames * len(paw_names))) * 100
        
        avg_fps = 30.0  # Значение по умолчанию
        
        # Заполняем общую таблицу
        general_data = [
            ("Всего кадров", str(total_frames)),
            ("Длительность (сек)", f"{duration:.1f}"),
            ("Среднее FPS", f"{avg_fps:.1f}"),
            ("Активность (%)", f"{activity:.1f}%")
        ]
        
        for i, (param, value) in enumerate(general_data):
            self.general_table.setItem(i, 0, QTableWidgetItem(param))
            self.general_table.setItem(i, 1, QTableWidgetItem(value))
            
        # Настройка размеров столбцов
        self.general_table.resizeColumnsToContents()
        
        # Статистика по лапам
        self.update_paws_statistics(df)
        
        # Статистика седалищного индекса
        self.update_sciatic_statistics(df)
        
        # Корреляционный анализ
        self.update_correlation_analysis(df)
        
    def update_paws_statistics(self, df):
        """Обновление статистики по лапам"""
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = {
            'lf': 'Левая передняя',
            'rf': 'Правая передняя', 
            'lb': 'Левая задняя',
            'rb': 'Правая задняя'
        }
        
        # Настройка таблицы
        self.paws_table.setRowCount(len(paw_names))
        self.paws_table.setColumnCount(5)
        self.paws_table.setHorizontalHeaderLabels([
            "Лапа", "Средняя площадь (мм²)", "Макс площадь (мм²)", 
            "Средняя длина (мм)", "Контакт (%)"
        ])
        self.paws_table.verticalHeader().setVisible(False)
        
        for i, paw in enumerate(paw_names):
            area_col = f'{paw}_area_mm2'
            length_col = f'{paw}_length_mm'
            
            # Название лапы
            self.paws_table.setItem(i, 0, QTableWidgetItem(paw_labels[paw]))
            
            if area_col in df.columns and length_col in df.columns:
                # Площадь
                mean_area = df[area_col].mean()
                max_area = df[area_col].max()
                
                # Длина
                mean_length = df[length_col].mean()
                
                # Процент контакта
                contact_frames = (df[area_col] > 0).sum()
                contact_percent = (contact_frames / len(df)) * 100 if len(df) > 0 else 0
                
                self.paws_table.setItem(i, 1, QTableWidgetItem(f"{mean_area:.1f}"))
                self.paws_table.setItem(i, 2, QTableWidgetItem(f"{max_area:.1f}"))
                self.paws_table.setItem(i, 3, QTableWidgetItem(f"{mean_length:.1f}"))
                self.paws_table.setItem(i, 4, QTableWidgetItem(f"{contact_percent:.1f}%"))
            else:
                # Заполняем нулями если данных нет
                for j in range(1, 5):
                    self.paws_table.setItem(i, j, QTableWidgetItem("0.0"))
                    
        # Настройка размеров столбцов
        self.paws_table.resizeColumnsToContents()
        
    def update_sciatic_statistics(self, df):
        """Обновление статистики седалищного индекса"""
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = {
            'lf': 'Левая передняя',
            'rf': 'Правая передняя', 
            'lb': 'Левая задняя',
            'rb': 'Правая задняя'
        }
        
        # Настройка таблицы
        self.sciatic_table.setRowCount(len(paw_names))
        self.sciatic_table.setColumnCount(5)
        self.sciatic_table.setHorizontalHeaderLabels([
            "Лапа", "Средний СИ", "Макс СИ", "Мин СИ", "Норма (%)"
        ])
        self.sciatic_table.verticalHeader().setVisible(False)
        
        for i, paw in enumerate(paw_names):
            sciatic_col = f'{paw}_sciatic_index'
            
            # Название лапы
            self.sciatic_table.setItem(i, 0, QTableWidgetItem(paw_labels[paw]))
            
            if sciatic_col in df.columns:
                # Убираем нулевые значения для корректной статистики
                sciatic_data = df[sciatic_col][df[sciatic_col] > 0]
                
                if len(sciatic_data) > 0:
                    mean_sciatic = sciatic_data.mean()
                    max_sciatic = sciatic_data.max()
                    min_sciatic = sciatic_data.min()
                    
                    # Нормальным считается индекс > 80 (типичное значение для здоровых лап)
                    normal_frames = (sciatic_data >= 80).sum()
                    normal_percent = (normal_frames / len(sciatic_data)) * 100
                    
                    self.sciatic_table.setItem(i, 1, QTableWidgetItem(f"{mean_sciatic:.1f}"))
                    self.sciatic_table.setItem(i, 2, QTableWidgetItem(f"{max_sciatic:.1f}"))
                    self.sciatic_table.setItem(i, 3, QTableWidgetItem(f"{min_sciatic:.1f}"))
                    
                    # Цветовое кодирование процента нормы
                    normal_item = QTableWidgetItem(f"{normal_percent:.1f}%")
                    if normal_percent >= 80:
                        normal_item.setBackground(self.palette().brush(self.palette().Dark).color().darker())
                    elif normal_percent >= 60:
                        normal_item.setBackground(self.palette().brush(self.palette().Mid).color())
                    else:
                        normal_item.setBackground(self.palette().brush(self.palette().Light).color())
                    
                    self.sciatic_table.setItem(i, 4, normal_item)
                else:
                    # Нет данных
                    for j in range(1, 5):
                        self.sciatic_table.setItem(i, j, QTableWidgetItem("0.0"))
            else:
                # Колонка отсутствует
                for j in range(1, 5):
                    self.sciatic_table.setItem(i, j, QTableWidgetItem("N/A"))
                    
        # Настройка размеров столбцов
        self.sciatic_table.resizeColumnsToContents()
        
    def update_correlation_analysis(self, df):
        """Обновление корреляционного анализа"""
        try:
            paw_names = ['lf', 'rf', 'lb', 'rb']
            
            # Анализ корреляций между различными метриками
            area_columns = [f'{paw}_area_mm2' for paw in paw_names if f'{paw}_area_mm2' in df.columns]
            length_columns = [f'{paw}_length_mm' for paw in paw_names if f'{paw}_length_mm' in df.columns]
            sciatic_columns = [f'{paw}_sciatic_index' for paw in paw_names if f'{paw}_sciatic_index' in df.columns]
            
            if len(area_columns) < 2:
                self.correlation_text.setPlainText("Недостаточно данных для корреляционного анализа")
                return
                
            # Формируем текст
            corr_text = "=== КОРРЕЛЯЦИОННЫЙ АНАЛИЗ ===\n\n"
            
            # 1. Корреляции между площадями лап
            if len(area_columns) >= 2:
                corr_text += "1. Корреляция между площадями лап:\n"
                correlation_data = df[area_columns]
                correlation_matrix = correlation_data.corr()
                
                for i, col1 in enumerate(area_columns):
                    for j, col2 in enumerate(area_columns):
                        if i < j:  # Показываем только уникальные пары
                            corr_value = correlation_matrix.loc[col1, col2]
                            paw1 = col1.replace('_area_mm2', '').upper()
                            paw2 = col2.replace('_area_mm2', '').upper()
                            corr_text += f"   {paw1} ↔ {paw2}: {corr_value:.3f}\n"
                
                corr_text += "\n"
            
            # 2. Корреляции седалищного индекса
            if len(sciatic_columns) >= 2:
                corr_text += "2. Корреляция седалищного индекса:\n"
                sciatic_data = df[sciatic_columns]
                sciatic_corr = sciatic_data.corr()
                
                for i, col1 in enumerate(sciatic_columns):
                    for j, col2 in enumerate(sciatic_columns):
                        if i < j:
                            corr_value = sciatic_corr.loc[col1, col2]
                            paw1 = col1.replace('_sciatic_index', '').upper()
                            paw2 = col2.replace('_sciatic_index', '').upper()
                            corr_text += f"   {paw1} ↔ {paw2}: {corr_value:.3f}\n"
                
                corr_text += "\n"
            
            # 3. Корреляция между площадью и седалищным индексом
            if len(area_columns) >= 1 and len(sciatic_columns) >= 1:
                corr_text += "3. Площадь vs Седалищный индекс:\n"
                
                for paw in paw_names:
                    area_col = f'{paw}_area_mm2'
                    sciatic_col = f'{paw}_sciatic_index'
                    
                    if area_col in df.columns and sciatic_col in df.columns:
                        # Убираем нулевые значения
                        mask = (df[area_col] > 0) & (df[sciatic_col] > 0)
                        if mask.sum() > 10:  # Минимум 10 точек для корреляции
                            corr_value = df.loc[mask, [area_col, sciatic_col]].corr().iloc[0, 1]
                            corr_text += f"   {paw.upper()}: r={corr_value:.3f}\n"
                
                corr_text += "\n"
            
            # 4. Статистическая значимость (упрощенная оценка)
            corr_text += "4. Статистическая значимость (приблизительная):\n"
            if len(area_columns) >= 2:
                correlation_data = df[area_columns]
                correlation_matrix = correlation_data.corr()
                
                for i, col1 in enumerate(area_columns):
                    for j, col2 in enumerate(area_columns):
                        if i < j:
                            corr_value = abs(correlation_matrix.loc[col1, col2])
                            paw1 = col1.replace('_area_mm2', '').upper()
                            paw2 = col2.replace('_area_mm2', '').upper()
                            
                            if corr_value > 0.7:
                                significance = "p<0.001 ***"
                            elif corr_value > 0.5:
                                significance = "p<0.01 **"
                            elif corr_value > 0.3:
                                significance = "p<0.05 *"
                            else:
                                significance = "p>0.05 ns"
                                
                            corr_text += f"   {paw1}↔{paw2}: {significance}\n"
            
            # 5. Интерпретация седалищного индекса
            corr_text += "\n=== ИНТЕРПРЕТАЦИЯ СЕДАЛИЩНОГО ИНДЕКСА ===\n"
            corr_text += "• Норма: > 80-90\n"
            corr_text += "• Легкие нарушения: 60-80\n"
            corr_text += "• Умеренные нарушения: 40-60\n"
            corr_text += "• Тяжелые нарушения: < 40\n"
            corr_text += "\nСедалищный индекс = (Длина / Ширина) × 100\n"
            corr_text += "Используется для оценки функции седалищного нерва"
            
            self.correlation_text.setPlainText(corr_text)
            
        except Exception as e:
            self.correlation_text.setPlainText(f"Ошибка при расчете корреляций: {str(e)}")


class AdvancedPlotWidget(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = pd.DataFrame()
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        
        # Панель управления
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # Основная область с табами
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
        
        # Вкладка основных графиков
        self.plots_tab = QWidget()
        self.setup_plots_tab()
        self.tabs.addTab(self.plots_tab, "Основной график")
        
        # Вкладка дополнительного анализа
        self.analysis_tab = QWidget()
        self.setup_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "Дополнительный анализ")
        
        # Вкладка 3D визуализации
        self.viz_tab = QWidget()
        self.setup_3d_tab()
        self.tabs.addTab(self.viz_tab, "3D визуализация")
        
        # Вкладка статистики
        self.stats_widget = StatisticsWidget()
        self.tabs.addTab(self.stats_widget, "Статистика")
        
        layout.addWidget(self.tabs)
        
    def create_control_panel(self):
        """Создание панели управления"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                margin: 5px;
            }
            QLabel, QComboBox, QCheckBox {
                color: white;
            }
            QComboBox {
                background-color: #404040;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }
            QPushButton {
                background-color: #4a90e2;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5ba0f2;
            }
        """)
        
        layout = QHBoxLayout(panel)
        
        # Тип графика
        layout.addWidget(QLabel("Тип графика:"))
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems([
            "Временные ряды", 
            "Распределения",
            "Сравнение лап",
            "Тепловая карта",
            "Седалищный индекс"  # Добавляем новый тип графика
        ])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot)
        layout.addWidget(self.plot_type_combo)
        
        layout.addWidget(QLabel("Параметр:"))
        self.parameter_combo = QComboBox()
        self.parameter_combo.addItems([
            "Длина лапы",
            "Площадь контакта", 
            "Ширина лапы",
            "Седалищный индекс",  # Добавляем седалищный индекс
            "Все параметры"
        ])
        self.parameter_combo.currentTextChanged.connect(self.update_plot)
        layout.addWidget(self.parameter_combo)
        
        # Чекбоксы для настройки отображения
        self.smoothing_check = QCheckBox("Сглаживание")
        self.smoothing_check.toggled.connect(self.update_plot)
        layout.addWidget(self.smoothing_check)
        
        self.normalization_check = QCheckBox("Нормализация")
        self.normalization_check.toggled.connect(self.update_plot)
        layout.addWidget(self.normalization_check)
        
        # Кнопка экспорта
        export_btn = QPushButton("📈 Экспорт")
        export_btn.clicked.connect(self.export_plots)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        return panel
        
    def setup_plots_tab(self):
        """Настройка вкладки основных графиков"""
        layout = QVBoxLayout(self.plots_tab)
        
        # Создаем холст для основного графика
        self.main_canvas = PlotCanvas(self, width=12, height=8)
        layout.addWidget(self.main_canvas)
        
    def setup_analysis_tab(self):
        """Настройка вкладки дополнительного анализа"""
        layout = QVBoxLayout(self.analysis_tab)
        
        # Разделитель для нескольких графиков
        splitter = QSplitter(Qt.Vertical)
        
        # Верхний график
        self.analysis_canvas1 = PlotCanvas(self, width=10, height=4)
        splitter.addWidget(self.analysis_canvas1)
        
        # Нижний график
        self.analysis_canvas2 = PlotCanvas(self, width=10, height=4)
        splitter.addWidget(self.analysis_canvas2)
        
        layout.addWidget(splitter)
        
    def setup_3d_tab(self):
        """Настройка вкладки 3D визуализации"""
        layout = QVBoxLayout(self.viz_tab)
        
        # Создаем холст для 3D
        self.viz_canvas = PlotCanvas(self, width=10, height=8)
        layout.addWidget(self.viz_canvas)
        
    def plot_results(self, df):
        """Основной метод для построения графиков"""
        self.df = df.copy()
        
        if df.empty:
            self.clear_all_plots()
            return
            
        # Строим графики
        self.update_plot()
        
        # Обновляем статистику
        self.stats_widget.update_statistics(df)
        
    def update_plot(self):
        """Обновление графиков"""
        if self.df.empty:
            return
            
        plot_type = self.plot_type_combo.currentText()
        parameter = self.parameter_combo.currentText()
        
        # Очищаем основной график
        self.main_canvas.fig.clear()
        
        if plot_type == "Временные ряды":
            self.plot_time_series(parameter)
        elif plot_type == "Распределения":
            self.plot_distributions(parameter)
        elif plot_type == "Сравнение лап":
            self.plot_paw_comparison(parameter)
        elif plot_type == "Тепловая карта":
            self.plot_heatmap(parameter)
        elif plot_type == "Седалищный индекс":
            self.plot_sciatic_index(parameter)
            
        self.main_canvas.draw()
        
        # Обновляем дополнительные графики
        self.update_analysis_plots()
        self.update_3d_plot()
        
    def plot_sciatic_index(self, parameter):
        ax = self.main_canvas.fig.add_subplot(111)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = {
            'lf': 'ЛП (левая передняя)',
            'rf': 'ПП (правая передняя)', 
            'lb': 'ЛЗ (левая задняя)',
            'rb': 'ПЗ (правая задняя)'
        }
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        if parameter == "Седалищный индекс":
            # Временной ряд седалищного индекса
            title = "Динамика седалищного индекса"
            ylabel = "Седалищный индекс"
            
            for i, paw in enumerate(paw_names):
                sciatic_col = f'{paw}_sciatic_index'
                if sciatic_col in self.df.columns:
                    data = self.df[sciatic_col].values
                    
                    # Убираем нулевые значения
                    mask = data > 0
                    if mask.sum() > 0:
                        filtered_data = data[mask]
                        x_indices = np.where(mask)[0]
                        
                        # Нормализация если выбрано
                        if self.normalization_check.isChecked():
                            data_max = np.max(filtered_data)
                            if data_max > 0:
                                filtered_data = filtered_data / data_max
                        
                        # Сглаживание если выбрано
                        if self.smoothing_check.isChecked() and len(filtered_data) > 5:
                            from scipy.ndimage import uniform_filter1d
                            filtered_data = uniform_filter1d(filtered_data, size=5)
                        
                        # Нормализуем x к диапазону 0-1
                        x_normalized = x_indices / len(self.df)
                        ax.plot(x_normalized, filtered_data, label=paw_labels[paw], 
                               color=colors[i], linewidth=2, marker='o', markersize=3)
            
            # Добавляем референсные линии
            ax.axhline(y=80, color='green', linestyle='--', alpha=0.7, label='Норма (80)')
            ax.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='Граница риска (60)')
            ax.axhline(y=40, color='red', linestyle='--', alpha=0.7, label='Критическое значение (40)')
            
        else:
            # Сравнение всех лап
            title = "Сравнение седалищного индекса по лапам"
            ylabel = "Седалищный индекс"
            
            data_for_box = []
            labels_for_box = []
            
            for i, paw in enumerate(paw_names):
                sciatic_col = f'{paw}_sciatic_index'
                if sciatic_col in self.df.columns:
                    data = self.df[sciatic_col].values
                    data = data[data > 0]  # Убираем нулевые значения
                    if len(data) > 0:
                        data_for_box.append(data)
                        labels_for_box.append(paw_labels[paw])
            
            if data_for_box:
                bp = ax.boxplot(data_for_box, labels=labels_for_box, patch_artist=True)
                
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                
                # Референсные линии
                ax.axhline(y=80, color='green', linestyle='--', alpha=0.7, label='Норма')
                ax.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='Риск')
                ax.axhline(y=40, color='red', linestyle='--', alpha=0.7, label='Критично')
        
        ax.set_title(title, fontsize=14, fontweight='bold', color='white')
        ax.set_xlabel("Кадр" if parameter == "Седалищный индекс" else "Лапа", fontsize=12, color='white')
        ax.set_ylabel(ylabel, fontsize=12, color='white')
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#2a2a2a')
        
        # Настройка цветов осей
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        
    def plot_time_series(self, parameter):
        ax = self.main_canvas.fig.add_subplot(111)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = {
            'lf': 'ЛП (левая передняя)',
            'rf': 'ПП (правая передняя)', 
            'lb': 'ЛЗ (левая задняя)',
            'rb': 'ПЗ (правая задняя)'
        }
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        if parameter == "Длина лапы":
            title = "Динамика длины лап"
            ylabel = "Длина лапы (мм)"
            columns = [f'{paw}_length_mm' for paw in paw_names]
        elif parameter == "Площадь контакта":
            title = "Динамика площади контакта"
            ylabel = "Площадь (мм²)"
            columns = [f'{paw}_area_mm2' for paw in paw_names]
        elif parameter == "Ширина лапы":
            title = "Динамика ширины лап"
            ylabel = "Ширина (мм)"
            columns = [f'{paw}_width_2_4_mm' for paw in paw_names]
        elif parameter == "Седалищный индекс":
            title = "Динамика седалищного индекса"
            ylabel = "Седалищный индекс"
            columns = [f'{paw}_sciatic_index' for paw in paw_names]
        else:  # Все параметры
            title = "Динамика всех параметров (нормализовано)"
            ylabel = "Нормализованные значения"
            columns = []
            for paw in paw_names:
                columns.extend([
                    f'{paw}_length_mm',
                    f'{paw}_area_mm2', 
                    f'{paw}_width_2_4_mm',
                    f'{paw}_sciatic_index'
                ])
        
        # Построение графиков
        for i, col in enumerate(columns):
            if col in self.df.columns:
                data = self.df[col].values
                
                # Для седалищного индекса убираем нулевые значения
                if 'sciatic_index' in col:
                    mask = data > 0
                    if mask.sum() == 0:
                        continue
                    filtered_data = data[mask]
                    x_indices = np.where(mask)[0]
                    x_normalized = x_indices / len(data)
                    data = filtered_data
                else:
                    x_normalized = np.linspace(0, 1, len(data))
                
                # Нормализация если выбрано
                if self.normalization_check.isChecked():
                    data_max = np.max(data)
                    if data_max > 0:
                        data = data / data_max
                
                # Сглаживание если выбрано
                if self.smoothing_check.isChecked() and len(data) > 5:
                    from scipy.ndimage import uniform_filter1d
                    data = uniform_filter1d(data, size=5)
                
                # Определяем метку и цвет
                if parameter == "Все параметры":
                    paw = col.split('_')[0]
                    param_type = col.split('_')[-1] if 'index' not in col else 'sciatic'
                    label = f"{paw_labels.get(paw, paw)} - {param_type}"
                    color = colors[i % len(colors)]
                else:
                    paw = col.split('_')[0]
                    label = paw_labels.get(paw, paw)
                    color = colors[i]
                
                ax.plot(x_normalized, data, label=label, color=color, linewidth=2)
        
        ax.set_title(title, fontsize=14, fontweight='bold', color='white')
        ax.set_xlabel("Кадр", fontsize=12, color='white')
        ax.set_ylabel(ylabel, fontsize=12, color='white')
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#2a2a2a')
        
        # Настройка цветов осей
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        
    def plot_distributions(self, parameter):
        """Построение распределений"""
        ax = self.main_canvas.fig.add_subplot(111)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = {
            'lf': 'ЛП',
            'rf': 'ПП', 
            'lb': 'ЛЗ',
            'rb': 'ПЗ'
        }
        
        if parameter == "Длина лапы":
            columns = [f'{paw}_length_mm' for paw in paw_names]
            title = "Распределение длины лап"
            xlabel = "Длина (мм)"
        elif parameter == "Площадь контакта":
            columns = [f'{paw}_area_mm2' for paw in paw_names]
            title = "Распределение площади контакта"
            xlabel = "Площадь (мм²)"
        elif parameter == "Седалищный индекс":
            columns = [f'{paw}_sciatic_index' for paw in paw_names]
            title = "Распределение седалищного индекса"
            xlabel = "Седалищный индекс"
        else:
            columns = [f'{paw}_width_2_4_mm' for paw in paw_names]
            title = "Распределение ширины лап"
            xlabel = "Ширина (мм)"
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        for i, col in enumerate(columns):
            if col in self.df.columns:
                data = self.df[col].values
                data = data[data > 0]  # Убираем нулевые значения
                
                if len(data) > 0:
                    paw = col.split('_')[0]
                    label = paw_labels.get(paw, paw)
                    ax.hist(data, bins=30, alpha=0.7, label=label, 
                           color=colors[i], density=True)
        
        # Для седалищного индекса добавляем референсные линии
        if parameter == "Седалищный индекс":
            ax.axvline(x=80, color='green', linestyle='--', alpha=0.7, label='Норма (80)')
            ax.axvline(x=60, color='orange', linestyle='--', alpha=0.7, label='Граница риска (60)')
            ax.axvline(x=40, color='red', linestyle='--', alpha=0.7, label='Критическое (40)')
        
        ax.set_title(title, fontsize=14, fontweight='bold', color='white')
        ax.set_xlabel(xlabel, fontsize=12, color='white')
        ax.set_ylabel("Плотность", fontsize=12, color='white')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#2a2a2a')
        
        # Настройка цветов
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
            
    def plot_paw_comparison(self, parameter):
        """Сравнение лап"""
        ax = self.main_canvas.fig.add_subplot(111)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_labels = ['ЛП', 'ПП', 'ЛЗ', 'ПЗ']
        
        if parameter == "Длина лапы":
            columns = [f'{paw}_length_mm' for paw in paw_names]
            title = "Сравнение длины лап"
            ylabel = "Длина (мм)"
        elif parameter == "Площадь контакта":
            columns = [f'{paw}_area_mm2' for paw in paw_names]
            title = "Сравнение площади контакта"
            ylabel = "Площадь (мм²)"
        elif parameter == "Седалищный индекс":
            columns = [f'{paw}_sciatic_index' for paw in paw_names]
            title = "Сравнение седалищного индекса"
            ylabel = "Седалищный индекс"
        else:
            columns = [f'{paw}_width_2_4_mm' for paw in paw_names]
            title = "Сравнение ширины лап"
            ylabel = "Ширина (мм)"
        
        data_for_box = []
        labels_for_box = []
        
        for i, col in enumerate(columns):
            if col in self.df.columns:
                data = self.df[col].values
                data = data[data > 0]  # Убираем нулевые значения
                if len(data) > 0:
                    data_for_box.append(data)
                    labels_for_box.append(paw_labels[i])
        
        if data_for_box:
            bp = ax.boxplot(data_for_box, labels=labels_for_box, patch_artist=True)
            
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
                
            # Для седалищного индекса добавляем референсные линии
            if parameter == "Седалищный индекс":
                ax.axhline(y=80, color='green', linestyle='--', alpha=0.7, label='Норма')
                ax.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='Риск')
                ax.axhline(y=40, color='red', linestyle='--', alpha=0.7, label='Критично')
                ax.legend()
        
        ax.set_title(title, fontsize=14, fontweight='bold', color='white')
        ax.set_ylabel(ylabel, fontsize=12, color='white')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#2a2a2a')
        
        # Настройка цветов
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
            
    def plot_heatmap(self, parameter):
        """Тепловая карта корреляций"""
        ax = self.main_canvas.fig.add_subplot(111)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        
        if parameter == "Все параметры":
            columns = []
            for paw in paw_names:
                columns.extend([
                    f'{paw}_length_mm',
                    f'{paw}_area_mm2',
                    f'{paw}_width_2_4_mm',
                    f'{paw}_sciatic_index'  # Добавляем седалищный индекс
                ])
        elif parameter == "Седалищный индекс":
            columns = [f'{paw}_sciatic_index' for paw in paw_names]
        else:
            if parameter == "Длина лапы":
                columns = [f'{paw}_length_mm' for paw in paw_names]
            elif parameter == "Площадь контакта":
                columns = [f'{paw}_area_mm2' for paw in paw_names]
            else:
                columns = [f'{paw}_width_2_4_mm' for paw in paw_names]
        
        # Фильтруем только существующие колонки
        available_columns = [col for col in columns if col in self.df.columns]
        
        if len(available_columns) > 1:
            # Для седалищного индекса используем только значения > 0
            df_filtered = self.df.copy()
            for col in available_columns:
                if 'sciatic_index' in col:
                    df_filtered = df_filtered[df_filtered[col] > 0]
            
            if len(df_filtered) > 10:  # Минимум данных для корреляции
                corr_data = df_filtered[available_columns].corr()
                
                # Создаем красивые метки
                labels = []
                for col in available_columns:
                    parts = col.split('_')
                    paw = parts[0].upper()
                    if 'sciatic' in col:
                        param = 'SI'
                    elif 'area' in col:
                        param = 'Area'
                    elif 'length' in col:
                        param = 'Length'
                    elif 'width' in col:
                        param = 'Width'
                    else:
                        param = parts[-1]
                    labels.append(f"{paw}_{param}")
                
                im = ax.imshow(corr_data.values, cmap='RdYlBu_r', aspect='auto', vmin=-1, vmax=1)
                
                # Настройка осей
                ax.set_xticks(range(len(labels)))
                ax.set_yticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=45, ha='right')
                ax.set_yticklabels(labels)
                
                # Добавляем значения корреляций
                for i in range(len(labels)):
                    for j in range(len(labels)):
                        text = ax.text(j, i, f'{corr_data.values[i, j]:.2f}',
                                     ha="center", va="center", color="black", fontsize=8)
                
                # Цветовая шкала
                cbar = self.main_canvas.fig.colorbar(im, ax=ax)
                cbar.set_label('Корреляция', color='white')
                cbar.ax.yaxis.set_tick_params(color='white')
                plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
            else:
                ax.text(0.5, 0.5, 'Недостаточно данных\nдля корреляционного анализа', 
                       transform=ax.transAxes, ha='center', va='center', 
                       fontsize=14, color='white')
        
        ax.set_title("Корреляционная матрица", fontsize=14, fontweight='bold', color='white')
        ax.tick_params(colors='white')
        
    def update_analysis_plots(self):
        """Обновление дополнительных графиков анализа"""
        if self.df.empty:
            return
            
        # График 1: Анализ активности + седалищный индекс
        self.analysis_canvas1.fig.clear()
        ax1 = self.analysis_canvas1.fig.add_subplot(111)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        activity_data = []
        sciatic_data = []
        labels = ['ЛП', 'ПП', 'ЛЗ', 'ПЗ']
        
        for paw in paw_names:
            area_col = f'{paw}_area_mm2'
            sciatic_col = f'{paw}_sciatic_index'
            
            if area_col in self.df.columns:
                contact_frames = (self.df[area_col] > 0).sum()
                activity_percent = (contact_frames / len(self.df)) * 100
                activity_data.append(activity_percent)
            else:
                activity_data.append(0)
                
            if sciatic_col in self.df.columns:
                sciatic_values = self.df[sciatic_col][self.df[sciatic_col] > 0]
                avg_sciatic = sciatic_values.mean() if len(sciatic_values) > 0 else 0
                sciatic_data.append(avg_sciatic)
            else:
                sciatic_data.append(0)
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        # Двойная ось для отображения и активности, и седалищного индекса
        ax2 = ax1.twinx()
        
        bars1 = ax1.bar([x - 0.2 for x in range(len(labels))], activity_data, 
                       width=0.4, color=colors, alpha=0.8, label='Активность (%)')
        bars2 = ax2.bar([x + 0.2 for x in range(len(labels))], sciatic_data, 
                       width=0.4, color=[c for c in colors], alpha=0.6, label='Средний СИ')
        
        ax1.set_title("Активность лап и седалищный индекс", fontsize=12, fontweight='bold', color='white')
        ax1.set_ylabel("Процент кадров с контактом", fontsize=10, color='white')
        ax2.set_ylabel("Седалищный индекс", fontsize=10, color='white')
        ax1.set_xticks(range(len(labels)))
        ax1.set_xticklabels(labels)
        ax1.set_facecolor('#2a2a2a')
        ax1.tick_params(colors='white')
        ax2.tick_params(colors='white')
        
        # Референсная линия для седалищного индекса
        ax2.axhline(y=80, color='green', linestyle='--', alpha=0.7)
        
        for spine in ax1.spines.values():
            spine.set_color('white')
        for spine in ax2.spines.values():
            spine.set_color('white')
        
        # Добавляем значения на столбцы
        for bar, value in zip(bars1, activity_data):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{value:.1f}%', ha='center', va='bottom', color='white', fontsize=9)
                    
        for bar, value in zip(bars2, sciatic_data):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{value:.1f}', ha='center', va='bottom', color='white', fontsize=9)
        
        self.analysis_canvas1.draw()
        
        # График 2: Динамика седалищного индекса со скользящим средним
        self.analysis_canvas2.fig.clear()
        ax2 = self.analysis_canvas2.fig.add_subplot(111)
        
        # Вычисляем скользящее среднее для седалищного индекса
        window_size = max(1, len(self.df) // 20)  # 5% от общего количества кадров
        
        for i, paw in enumerate(paw_names):
            sciatic_col = f'{paw}_sciatic_index'
            if sciatic_col in self.df.columns:
                # Убираем нулевые значения и вычисляем скользящее среднее
                data = self.df[sciatic_col].copy()
                data[data == 0] = np.nan  # Заменяем нули на NaN
                
                if not data.isna().all():
                    # Интерполируем NaN значения
                    data = data.interpolate()
                    rolling_data = data.rolling(window=window_size, center=True).mean()
                    
                    x_normalized = np.linspace(0, 1, len(rolling_data))
                    ax2.plot(x_normalized, rolling_data, label=labels[i], color=colors[i], linewidth=2)
        
        # Референсные линии
        ax2.axhline(y=80, color='green', linestyle='--', alpha=0.7, label='Норма (80)')
        ax2.axhline(y=60, color='orange', linestyle='--', alpha=0.7, label='Риск (60)')
        ax2.axhline(y=40, color='red', linestyle='--', alpha=0.7, label='Критично (40)')
        
        ax2.set_title("Динамика седалищного индекса (скользящее среднее)", fontsize=12, fontweight='bold', color='white')
        ax2.set_xlabel("Нормализованное время", fontsize=10, color='white')
        ax2.set_ylabel("Седалищный индекс", fontsize=10, color='white')
        ax2.legend(loc='upper right', framealpha=0.9)
        ax2.grid(True, alpha=0.3)
        ax2.set_facecolor('#2a2a2a')
        ax2.tick_params(colors='white')
        for spine in ax2.spines.values():
            spine.set_color('white')
        
        self.analysis_canvas2.draw()
        
    def update_3d_plot(self):
        """Обновление 3D визуализации"""
        if self.df.empty:
            return
            
        self.viz_canvas.fig.clear()
        
        # Используем проекцию 3D
        from mpl_toolkits.mplot3d import Axes3D
        ax = self.viz_canvas.fig.add_subplot(111, projection='3d')
        
        # Берем данные для 3D визуализации: Длина, Ширина, Седалищный индекс
        paw_names = ['lf', 'rf']  # Для примера берем только передние лапы
        
        for i, paw in enumerate(paw_names):
            length_col = f'{paw}_length_mm'
            width_col = f'{paw}_width_2_4_mm'
            sciatic_col = f'{paw}_sciatic_index'
            
            if all(col in self.df.columns for col in [length_col, width_col, sciatic_col]):
                # Берем каждый N-й кадр для уменьшения количества точек
                step = max(1, len(self.df) // 100)
                subset = self.df.iloc[::step]
                
                x = subset[length_col].values
                y = subset[width_col].values  
                z = subset[sciatic_col].values
                
                # Убираем нулевые значения
                mask = (x > 0) & (y > 0) & (z > 0)
                x, y, z = x[mask], y[mask], z[mask]
                
                if len(x) > 0:
                    colors = ['#FF6B6B', '#4ECDC4']
                    
                    # Цветовое кодирование по седалищному индексу
                    scatter = ax.scatter(x, y, z, c=z, cmap='RdYlGn', alpha=0.6, s=20, 
                                       label=f"{'ЛП' if paw == 'lf' else 'ПП'}")
        
        ax.set_xlabel('Длина (мм)', color='white')
        ax.set_ylabel('Ширина (мм)', color='white')
        ax.set_zlabel('Седалищный индекс', color='white')
        ax.set_title('3D: Длина × Ширина × Седалищный индекс', fontsize=12, fontweight='bold', color='white')
        
        # Настройка цветов для 3D
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.zaxis.label.set_color('white')
        ax.tick_params(colors='white')
        
        # Добавляем цветовую шкалу
        try:
            cbar = self.viz_canvas.fig.colorbar(scatter, ax=ax, shrink=0.6)
            cbar.set_label('Седалищный индекс', color='white')
            cbar.ax.yaxis.set_tick_params(color='white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        except:
            pass
        
        if len(ax.legend().get_texts()) > 0:
            ax.legend()
        
        self.viz_canvas.draw()
        
    def clear_all_plots(self):
        """Очистка всех графиков"""
        self.main_canvas.fig.clear()
        self.main_canvas.draw()
        
        self.analysis_canvas1.fig.clear()
        self.analysis_canvas1.draw()
        
        self.analysis_canvas2.fig.clear()
        self.analysis_canvas2.draw()
        
        self.viz_canvas.fig.clear()
        self.viz_canvas.draw()
        
    def export_plots(self):
        """Экспорт графиков"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить графики", "analysis_plots_with_sciatic_index.png",
            "PNG Files (*.png);;PDF Files (*.pdf)"
        )
        
        if file_path:
            self.main_canvas.fig.savefig(file_path, dpi=300, 
                                       bbox_inches='tight', 
                                       facecolor='#2a2a2a',
                                       edgecolor='none')