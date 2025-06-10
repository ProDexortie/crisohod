# video_viewer.py (исправленная версия)

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QPoint, QRectF # Импортируем QRectF
from PyQt5.QtGui import QPainter, QPixmap

class ZoomableVideoLabel(QLabel):
    """
    Кастомный виджет QLabel, поддерживающий панорамирование 
    и масштабирование с помощью мыши.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.zoom_factor = 1.0
        self.panning = False
        self.pan_start_pos = QPoint()
        self.pan_offset = QPoint()

        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid gray; background-color: black;")

    def set_pixmap(self, pixmap):
        """Устанавливает новое изображение и сбрасывает масштабирование."""
        self._pixmap = pixmap
        # Сбрасываем зум и панорамирование при загрузке нового кадра/видео
        self.zoom_factor = 1.0
        self.pan_offset = QPoint()
        self.update()

    def wheelEvent(self, event):
        """Обработка колеса мыши для масштабирования."""
        if not self._pixmap.isNull():
            zoom_delta = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            self.zoom_factor *= zoom_delta
            self.zoom_factor = max(1.0, min(self.zoom_factor, 15.0))
            self.update()

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши для начала панорамирования."""
        if event.button() == Qt.LeftButton and self.zoom_factor > 1.0:
            self.panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """Обработка движения мыши для панорамирования."""
        if self.panning:
            self.pan_offset += event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши."""
        if event.button() == Qt.LeftButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        """Сброс зума и панорамирования по двойному клику."""
        self.set_pixmap(self._pixmap)

    def paintEvent(self, event):
        """
        Переопределенный метод отрисовки для применения зума и панорамирования.
        """
        if self._pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QPainter(self)
        
        target_rect = self.rect()
        pixmap_size = self._pixmap.size()
        pixmap_size.scale(target_rect.size(), Qt.KeepAspectRatio)
        
        centered_rect = QRectF(0, 0, pixmap_size.width(), pixmap_size.height())
        centered_rect.moveCenter(target_rect.center())
        
        zoomed_width = centered_rect.width() * self.zoom_factor
        zoomed_height = centered_rect.height() * self.zoom_factor
        
        source_width = self._pixmap.width() / self.zoom_factor
        source_height = self._pixmap.height() / self.zoom_factor
        
        pan_x = self.pan_offset.x() / self.zoom_factor
        pan_y = self.pan_offset.y() / self.zoom_factor

        source_x = (self._pixmap.width() - source_width) / 2 - pan_x
        source_y = (self._pixmap.height() - source_height) / 2 - pan_y
        
        source_x = max(0, min(source_x, self._pixmap.width() - source_width))
        source_y = max(0, min(source_y, self._pixmap.height() - source_height))

        source_rect = QRectF(source_x, source_y, source_width, source_height)
        
        # --- ИСПРАВЛЕНИЕ ---
        # Преобразуем target_rect (QRect) в QRectF перед отрисовкой,
        # чтобы типы аргументов совпадали.
        painter.drawPixmap(QRectF(target_rect), self._pixmap, source_rect)