"""
modern_video_widget.py
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QSpinBox, QCheckBox, QFrame, QButtonGroup,
    QToolButton, QMenu
)
from PyQt5.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QPixmap, QImage, QWheelEvent, QMouseEvent, 
    QPaintEvent, QResizeEvent, QFont, QPen, QBrush, QColor
)


class AdvancedVideoLabel(QLabel):
    
    # Сигналы для взаимодействия
    zoom_changed = pyqtSignal(float)
    position_changed = pyqtSignal(QPoint)
    double_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Основные параметры
        self._pixmap = QPixmap()
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 1.2
        
        # Панорамирование
        self.panning = False
        self.pan_start_pos = QPoint()
        self.pan_offset = QPoint()
        
        # Настройки виджета
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #404040;
                border-radius: 8px;
                background-color: #1a1a1a;
            }
        """)
        
        # Показываем сообщение по умолчанию
        self.set_default_message()
        
        # Настройки отображения
        self.show_grid = False
        self.show_crosshair = False
        self.show_zoom_info = True
        
    def set_default_message(self):
        """Установка сообщения по умолчанию"""
        self.setText("""
        🎥 Видео не загружено
        
        Загрузите видео файл для начала анализа
        
        Управление:
        • Колесо мыши - масштабирование
        • ЛКМ + перетаскивание - панорамирование
        • Двойной клик - сброс вида
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(self.styleSheet() + """
            QLabel {
                color: #888888;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
    def set_frame(self, frame):
        """Установка нового кадра"""
        if frame is None:
            self.set_default_message()
            return
            
        # Конвертируем кадр в QPixmap
        if len(frame.shape) == 3:
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        else:
            height, width = frame.shape
            q_image = QImage(frame.data, width, height, width, QImage.Format_Grayscale8)
            
        self._pixmap = QPixmap.fromImage(q_image)
        
        # Сбрасываем стили текста
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #404040;
                border-radius: 8px;
                background-color: #1a1a1a;
            }
        """)
        
        self.update()
        
    def load_video(self, video_path):
        """Загрузка видео (для совместимости)"""
        # Этот метод может быть расширен для прямой загрузки видео
        pass
        
    def reset_view(self):
        """Сброс вида"""
        self.zoom_factor = 1.0
        self.pan_offset = QPoint()
        self.zoom_changed.emit(self.zoom_factor)
        self.update()
        
    def zoom_in(self):
        """Увеличение масштаба"""
        new_zoom = min(self.zoom_factor * self.zoom_step, self.max_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.zoom_changed.emit(self.zoom_factor)
            self.update()
            
    def zoom_out(self):
        """Уменьшение масштаба"""
        new_zoom = max(self.zoom_factor / self.zoom_step, self.min_zoom)
        if new_zoom != self.zoom_factor:
            self.zoom_factor = new_zoom
            self.zoom_changed.emit(self.zoom_factor)
            self.update()
            
    def fit_to_window(self):
        """Подгонка под размер окна"""
        if self._pixmap.isNull():
            return
            
        widget_size = self.size()
        pixmap_size = self._pixmap.size()
        
        scale_x = widget_size.width() / pixmap_size.width()
        scale_y = widget_size.height() / pixmap_size.height()
        
        self.zoom_factor = min(scale_x, scale_y) * 0.95  # Небольшой отступ
        self.pan_offset = QPoint()
        self.zoom_changed.emit(self.zoom_factor)
        self.update()
        
    def toggle_grid(self):
        """Переключение сетки"""
        self.show_grid = not self.show_grid
        self.update()
        
    def toggle_crosshair(self):
        """Переключение перекрестия"""
        self.show_crosshair = not self.show_crosshair
        self.update()
        
    def wheelEvent(self, event: QWheelEvent):
        """Обработка колеса мыши для масштабирования"""
        if not self._pixmap.isNull():
            # Определяем направление прокрутки
            delta = event.angleDelta().y()
            
            if delta > 0:
                zoom_delta = self.zoom_step
            else:
                zoom_delta = 1 / self.zoom_step
                
            # Вычисляем новый масштаб
            new_zoom = self.zoom_factor * zoom_delta
            new_zoom = max(self.min_zoom, min(new_zoom, self.max_zoom))
            
            if new_zoom != self.zoom_factor:
                # Масштабируем относительно позиции курсора
                cursor_pos = event.pos()
                
                # Вычисляем смещение для масштабирования относительно курсора
                zoom_ratio = new_zoom / self.zoom_factor
                
                # Корректируем смещение панорамирования
                self.pan_offset = QPoint(
                    int(self.pan_offset.x() * zoom_ratio + cursor_pos.x() * (1 - zoom_ratio)),
                    int(self.pan_offset.y() * zoom_ratio + cursor_pos.y() * (1 - zoom_ratio))
                )
                
                self.zoom_factor = new_zoom
                self.zoom_changed.emit(self.zoom_factor)
                self.update()
                
    def mousePressEvent(self, event: QMouseEvent):
        """Обработка нажатия кнопки мыши"""
        if event.button() == Qt.LeftButton and self.zoom_factor > 1.0:
            self.panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.RightButton:
            # Правая кнопка для контекстного меню
            self.show_context_menu(event.pos())
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """Обработка движения мыши"""
        if self.panning:
            delta = event.pos() - self.pan_start_pos
            self.pan_offset += delta
            self.pan_start_pos = event.pos()
            self.position_changed.emit(self.pan_offset)
            self.update()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Обработка отпускания кнопки мыши"""
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Обработка двойного клика"""
        if event.button() == Qt.LeftButton:
            self.reset_view()
            self.double_clicked.emit()
            
    def show_context_menu(self, position):
        """Показ контекстного меню"""
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self)
        
        # Действия масштабирования
        zoom_in_action = QAction("Увеличить", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Уменьшить", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        menu.addAction(zoom_out_action)
        
        fit_action = QAction("Подогнать к окну", self)
        fit_action.triggered.connect(self.fit_to_window)
        menu.addAction(fit_action)
        
        reset_action = QAction("Сбросить вид", self)
        reset_action.triggered.connect(self.reset_view)
        menu.addAction(reset_action)
        
        menu.addSeparator()
        
        # Настройки отображения
        grid_action = QAction("Показать сетку", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(self.show_grid)
        grid_action.triggered.connect(self.toggle_grid)
        menu.addAction(grid_action)
        
        crosshair_action = QAction("Показать перекрестие", self)
        crosshair_action.setCheckable(True)
        crosshair_action.setChecked(self.show_crosshair)
        crosshair_action.triggered.connect(self.toggle_crosshair)
        menu.addAction(crosshair_action)
        
        menu.exec_(self.mapToGlobal(position))
        
    def paintEvent(self, event: QPaintEvent):
        """Переопределенная отрисовка"""
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Вычисляем области отрисовки
        widget_rect = self.rect()
        pixmap_size = self._pixmap.size()
        
        # Масштабированный размер
        scaled_width = pixmap_size.width() * self.zoom_factor
        scaled_height = pixmap_size.height() * self.zoom_factor
        
        # Центрируем изображение с учетом панорамирования
        x = (widget_rect.width() - scaled_width) / 2 + self.pan_offset.x()
        y = (widget_rect.height() - scaled_height) / 2 + self.pan_offset.y()
        
        target_rect = QRectF(x, y, scaled_width, scaled_height)
        
        # Отрисовываем изображение
        painter.drawPixmap(target_rect, self._pixmap, QRectF(self._pixmap.rect()))
        
        # Дополнительные элементы интерфейса
        self.draw_overlay_elements(painter, widget_rect)
        
    def draw_overlay_elements(self, painter, widget_rect):
        """Отрисовка дополнительных элементов интерфейса"""
        # Сетка
        if self.show_grid:
            self.draw_grid(painter, widget_rect)
            
        # Перекрестие
        if self.show_crosshair:
            self.draw_crosshair(painter, widget_rect)
            
        # Информация о масштабе
        if self.show_zoom_info and self.zoom_factor != 1.0:
            self.draw_zoom_info(painter, widget_rect)
            
    def draw_grid(self, painter, rect):
        """Отрисовка сетки"""
        painter.setPen(QPen(QColor(100, 100, 100, 100), 1, Qt.DotLine))
        
        grid_size = 50
        
        # Вертикальные линии
        for x in range(0, rect.width(), grid_size):
            painter.drawLine(x, 0, x, rect.height())
            
        # Горизонтальные линии
        for y in range(0, rect.height(), grid_size):
            painter.drawLine(0, y, rect.width(), y)
            
    def draw_crosshair(self, painter, rect):
        """Отрисовка перекрестия"""
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        
        center_x = rect.width() // 2
        center_y = rect.height() // 2
        
        # Горизонтальная линия
        painter.drawLine(center_x - 20, center_y, center_x + 20, center_y)
        
        # Вертикальная линия
        painter.drawLine(center_x, center_y - 20, center_x, center_y + 20)
        
    def draw_zoom_info(self, painter, rect):
        """Отрисовка информации о масштабе"""
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        
        # Прямоугольник для текста
        info_rect = QRectF(rect.width() - 120, 10, 110, 30)
        painter.drawRoundedRect(info_rect, 5, 5)
        
        # Текст
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        
        zoom_text = f"Zoom: {self.zoom_factor:.1f}x"
        painter.drawText(info_rect, Qt.AlignCenter, zoom_text)


class ModernVideoWidget(QWidget):
    """Современный виджет для работы с видео"""
    
    frame_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Основные данные
        self.video_path = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Основная область видео
        self.video_label = AdvancedVideoLabel()
        layout.addWidget(self.video_label)
        
        # Панель инструментов видео
        tools_frame = QFrame()
        tools_frame.setFrameStyle(QFrame.StyledPanel)
        tools_frame.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        
        tools_layout = QHBoxLayout(tools_frame)
        
        # Кнопки масштабирования
        zoom_group = QButtonGroup(self)
        
        zoom_in_btn = QToolButton()
        zoom_in_btn.setText("🔍+")
        zoom_in_btn.setToolTip("Увеличить (Колесо вверх)")
        zoom_in_btn.clicked.connect(self.video_label.zoom_in)
        tools_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QToolButton()
        zoom_out_btn.setText("🔍-")
        zoom_out_btn.setToolTip("Уменьшить (Колесо вниз)")
        zoom_out_btn.clicked.connect(self.video_label.zoom_out)
        tools_layout.addWidget(zoom_out_btn)
        
        fit_btn = QToolButton()
        fit_btn.setText("📐")
        fit_btn.setToolTip("Подогнать к окну")
        fit_btn.clicked.connect(self.video_label.fit_to_window)
        tools_layout.addWidget(fit_btn)
        
        reset_btn = QToolButton()
        reset_btn.setText("🔄")
        reset_btn.setToolTip("Сбросить вид (Двойной клик)")
        reset_btn.clicked.connect(self.video_label.reset_view)
        tools_layout.addWidget(reset_btn)
        
        # Добавляем вертикальный разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #555555;")
        tools_layout.addWidget(separator)
        
        # Переключатели отображения
        self.grid_check = QCheckBox("Сетка")
        self.grid_check.setToolTip("Показать сетку")
        self.grid_check.toggled.connect(self.video_label.toggle_grid)
        tools_layout.addWidget(self.grid_check)
        
        self.crosshair_check = QCheckBox("Прицел")
        self.crosshair_check.setToolTip("Показать перекрестие")
        self.crosshair_check.toggled.connect(self.video_label.toggle_crosshair)
        tools_layout.addWidget(self.crosshair_check)
        
        tools_layout.addStretch()
        
        # Информация о масштабе
        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setStyleSheet("font-weight: bold; color: #4a90e2;")
        tools_layout.addWidget(self.zoom_label)
        
        layout.addWidget(tools_frame)
        
        # Информационная панель
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_frame.setStyleSheet(tools_frame.styleSheet())
        
        info_layout = QHBoxLayout(info_frame)
        
        self.video_info_label = QLabel("Видео не загружено")
        self.video_info_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(self.video_info_label)
        
        info_layout.addStretch()
        
        self.position_label = QLabel("Позиция: (0, 0)")
        self.position_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(self.position_label)
        
        layout.addWidget(info_frame)
        
        # Стили для кнопок
        button_style = """
            QToolButton {
                background-color: #555555;
                border: 1px solid #777777;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
                min-width: 30px;
                min-height: 30px;
            }
            QToolButton:hover {
                background-color: #666666;
                border-color: #4a90e2;
            }
            QToolButton:pressed {
                background-color: #444444;
            }
        """
        
        for btn in [zoom_in_btn, zoom_out_btn, fit_btn, reset_btn]:
            btn.setStyleSheet(button_style)
            
    def setup_connections(self):
        """Настройка соединений сигналов"""
        self.video_label.zoom_changed.connect(self.on_zoom_changed)
        self.video_label.position_changed.connect(self.on_position_changed)
        
    def load_video(self, video_path):
        """Загрузка видео"""
        self.video_path = video_path
        
        # Получаем информацию о видео
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Обновляем информацию
            duration = self.total_frames / self.fps if self.fps > 0 else 0
            info_text = f"📹 {width}x{height} | {self.fps:.1f} FPS | {self.total_frames} кадров | {duration:.1f}с"
            self.video_info_label.setText(info_text)
            
            cap.release()
        else:
            self.video_info_label.setText("❌ Ошибка загрузки видео")
            
    def set_frame(self, frame):
        """Установка текущего кадра"""
        self.video_label.set_frame(frame)
        
    def on_zoom_changed(self, zoom_factor):
        """Обработка изменения масштаба"""
        self.zoom_label.setText(f"{zoom_factor:.1f}x")
        
    def on_position_changed(self, position):
        """Обработка изменения позиции"""
        self.position_label.setText(f"Позиция: ({position.x()}, {position.y()})")
        
    def get_current_view_info(self):
        """Получение информации о текущем виде"""
        return {
            'zoom': self.video_label.zoom_factor,
            'pan_offset': (self.video_label.pan_offset.x(), self.video_label.pan_offset.y()),
            'show_grid': self.video_label.show_grid,
            'show_crosshair': self.video_label.show_crosshair
        }
        
    def set_view_info(self, info):
        """Установка параметров вида"""
        if 'zoom' in info:
            self.video_label.zoom_factor = info['zoom']
            
        if 'pan_offset' in info:
            self.video_label.pan_offset = QPoint(*info['pan_offset'])
            
        if 'show_grid' in info:
            self.video_label.show_grid = info['show_grid']
            self.grid_check.setChecked(info['show_grid'])
            
        if 'show_crosshair' in info:
            self.video_label.show_crosshair = info['show_crosshair']
            self.crosshair_check.setChecked(info['show_crosshair'])
            
        self.video_label.update()