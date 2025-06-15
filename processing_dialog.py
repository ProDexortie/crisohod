"""
processing_dialog.py
"""

import sys
import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QFrame, QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QSequentialAnimationGroup, QParallelAnimationGroup,
    pyqtProperty, QRect, QPoint
)
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, 
    QLinearGradient, QConicalGradient, QPalette
)


class AnimatedProgressBar(QProgressBar):
    """Анимированный прогресс-бар с градиентом и эффектами"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        
        # Анимация градиента
        self._gradient_offset = 0.0
        self.gradient_timer = QTimer()
        self.gradient_timer.timeout.connect(self.update_gradient)
        self.gradient_timer.start(50)  # 20 FPS
        
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #404040;
                border-radius: 10px;
                text-align: center;
                background-color: #1a1a1a;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        
    def update_gradient(self):
        """Обновление позиции градиента"""
        self._gradient_offset += 0.02
        if self._gradient_offset > 1.0:
            self._gradient_offset = 0.0
        self.update()
        
    def paintEvent(self, event):
        """Переопределенная отрисовка с градиентом"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Получаем размеры
        rect = self.rect()
        
        # Фон
        painter.fillRect(rect, QColor(26, 26, 26))
        
        # Прогресс
        if self.value() > 0:
            progress_width = int((rect.width() - 4) * self.value() / self.maximum())
            progress_rect = QRect(2, 2, progress_width, rect.height() - 4)
            
            # Создаем анимированный градиент
            gradient = QLinearGradient(0, 0, progress_rect.width(), 0)
            
            # Цвета градиента
            color1 = QColor(74, 144, 226)    # Синий
            color2 = QColor(46, 204, 113)    # Зеленый
            color3 = QColor(241, 196, 15)    # Желтый
            
            # Анимированные позиции
            pos1 = (self._gradient_offset) % 1.0
            pos2 = (self._gradient_offset + 0.3) % 1.0
            pos3 = (self._gradient_offset + 0.6) % 1.0
            
            gradient.setColorAt(pos1, color1)
            gradient.setColorAt(pos2, color2)
            gradient.setColorAt(pos3, color3)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(progress_rect, 8, 8)
            
            # Блики
            highlight_gradient = QLinearGradient(0, 0, 0, progress_rect.height())
            highlight_gradient.setColorAt(0.0, QColor(255, 255, 255, 60))
            highlight_gradient.setColorAt(0.5, QColor(255, 255, 255, 20))
            highlight_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(highlight_gradient))
            painter.drawRoundedRect(progress_rect, 8, 8)
            
        # Рамка
        painter.setPen(QPen(QColor(64, 64, 64), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)
        
        # Текст
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"{self.value()}%")


class PulsingIcon(QLabel):
    """Пульсирующая иконка для индикации процесса"""
    
    def __init__(self, text="🔬", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("font-size: 48px;")
        
        # Анимация пульсации
        self.pulse_animation = QPropertyAnimation(self, b"geometry")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Анимация вращения (имитация через изменение размера)
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.update_rotation)
        self.rotation_timer.start(100)
        
        self._rotation_angle = 0
        self._base_size = 48
        
    def update_rotation(self):
        """Обновление эффекта вращения"""
        self._rotation_angle += 10
        if self._rotation_angle >= 360:
            self._rotation_angle = 0
            
        # Создаем эффект пульсации через изменение размера
        scale = 1.0 + 0.1 * math.sin(math.radians(self._rotation_angle * 2))
        size = int(self._base_size * scale)
        
        self.setStyleSheet(f"font-size: {size}px; color: #4a90e2;")
        
    def start_pulse(self):
        """Запуск анимации пульсации"""
        if not self.pulse_animation.state() == QPropertyAnimation.Running:
            start_geometry = self.geometry()
            end_geometry = QRect(
                start_geometry.x() - 5, start_geometry.y() - 5,
                start_geometry.width() + 10, start_geometry.height() + 10
            )
            
            self.pulse_animation.setStartValue(start_geometry)
            self.pulse_animation.setEndValue(end_geometry)
            self.pulse_animation.finished.connect(self.reverse_pulse)
            self.pulse_animation.start()
            
    def reverse_pulse(self):
        """Обратная анимация пульсации"""
        self.pulse_animation.finished.disconnect()
        start_value = self.pulse_animation.endValue()
        end_value = self.pulse_animation.startValue()
        
        self.pulse_animation.setStartValue(start_value)
        self.pulse_animation.setEndValue(end_value)
        self.pulse_animation.finished.connect(self.start_pulse)
        self.pulse_animation.start()


class FloatingParticle(QLabel):
    """Плавающая частица для анимации фона"""
    
    def __init__(self, parent=None):
        super().__init__("✦", parent)
        self.setStyleSheet("color: rgba(74, 144, 226, 100); font-size: 16px;")
        self.resize(20, 20)
        
        # Случайная начальная позиция
        import random
        self.start_x = random.randint(0, 400)
        self.start_y = random.randint(400, 500)
        self.move(self.start_x, self.start_y)
        
        # Анимация движения
        self.move_animation = QPropertyAnimation(self, b"pos")
        self.move_animation.setDuration(random.randint(3000, 6000))
        self.move_animation.setEasingCurve(QEasingCurve.InOutSine)
        
        # Анимация прозрачности
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(2000)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    def start_floating(self):
        """Запуск анимации плавания"""
        import random
        
        # Движение к случайной точке вверху
        end_x = random.randint(0, 400)
        end_y = random.randint(-50, 0)
        
        self.move_animation.setStartValue(QPoint(self.start_x, self.start_y))
        self.move_animation.setEndValue(QPoint(end_x, end_y))
        self.move_animation.finished.connect(self.hide)
        self.move_animation.start()
        
        # Постепенное исчезновение
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()


class ProcessingDialog(QDialog):
    """Диалог обработки с анимированными эффектами"""
    
    def __init__(self, parent=None, title="Обработка данных"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(500, 350)
        
        # Убираем стандартные кнопки окна
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        # Переменные состояния
        self.is_processing = True
        self.particles = []
        
        self.setup_ui()
        self.setup_animations()
        self.setup_styling()
        
        # Запускаем анимации
        self.start_animations()
        
    def setup_ui(self):
        """Настройка интерфейса"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Заголовок
        self.title_label = QLabel("Обработка данных")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #4a90e2;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Анимированная иконка
        icon_layout = QHBoxLayout()
        icon_layout.addStretch()
        
        self.processing_icon = PulsingIcon("🔬")
        icon_layout.addWidget(self.processing_icon)
        
        icon_layout.addStretch()
        layout.addLayout(icon_layout)
        
        # Статус
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: white;
                margin: 10px 0;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Прогресс-бар
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setFixedHeight(25)
        layout.addWidget(self.progress_bar)
        
        # Детальная информация
        self.details_label = QLabel("Подготовка к анализу...")
        self.details_label.setAlignment(Qt.AlignCenter)
        self.details_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #888888;
                margin-top: 5px;
            }
        """)
        layout.addWidget(self.details_label)
        
        # Кнопка отмены (скрыта по умолчанию)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none;
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
    def setup_animations(self):
        """Настройка анимаций"""
        # Анимация появления диалога
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Анимация заголовка
        self.title_animation = QPropertyAnimation(self.title_label, b"geometry")
        self.title_animation.setDuration(800)
        self.title_animation.setEasingCurve(QEasingCurve.OutBounce)
        
        # Таймер для создания частиц
        self.particle_timer = QTimer()
        self.particle_timer.timeout.connect(self.create_particle)
        self.particle_timer.start(500)  # Новая частица каждые 500мс
        
    def setup_styling(self):
        """Настройка стилей"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2a2a2a, stop: 1 #1a1a1a);
                border: 2px solid #404040;
                border-radius: 15px;
            }
        """)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)
        
    def start_animations(self):
        """Запуск всех анимаций"""
        # Анимация появления
        self.fade_in_animation.start()
        
        # Анимация заголовка
        original_geometry = self.title_label.geometry()
        start_geometry = QRect(
            original_geometry.x(), 
            original_geometry.y() - 50,
            original_geometry.width(), 
            original_geometry.height()
        )
        
        self.title_animation.setStartValue(start_geometry)
        self.title_animation.setEndValue(original_geometry)
        self.title_animation.start()
        
        # Запуск пульсации иконки
        QTimer.singleShot(300, self.processing_icon.start_pulse)
        
    def create_particle(self):
        """Создание новой частицы"""
        if len(self.particles) < 8:  # Ограничиваем количество частиц
            particle = FloatingParticle(self)
            particle.show()
            particle.start_floating()
            self.particles.append(particle)
            
            # Удаляем частицу через некоторое время
            QTimer.singleShot(6000, lambda: self.remove_particle(particle))
            
    def remove_particle(self, particle):
        """Удаление частицы"""
        if particle in self.particles:
            self.particles.remove(particle)
            particle.deleteLater()
            
    def set_status(self, status_text):
        """Установка текста статуса"""
        self.status_label.setText(status_text)
        
        # Анимация изменения текста
        self.animate_label_change(self.status_label)
        
    def set_details(self, details_text):
        """Установка детальной информации"""
        self.details_label.setText(details_text)
        
    def set_progress(self, value):
        """Установка значения прогресса"""
        # Плавная анимация изменения прогресса
        if hasattr(self, 'progress_animation'):
            self.progress_animation.stop()
            
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_animation.setDuration(300)
        self.progress_animation.setStartValue(self.progress_bar.value())
        self.progress_animation.setEndValue(value)
        self.progress_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.progress_animation.start()
        
        # Изменяем иконку в зависимости от прогресса
        if value >= 100:
            self.processing_icon.setText("✅")
            self.processing_icon.setStyleSheet("font-size: 48px; color: #27ae60;")
            self.show_completion_animation()
        elif value >= 75:
            self.processing_icon.setText("⚡")
            self.processing_icon.setStyleSheet("font-size: 48px; color: #f39c12;")
        elif value >= 50:
            self.processing_icon.setText("🚀")
            self.processing_icon.setStyleSheet("font-size: 48px; color: #e67e22;")
            
    def animate_label_change(self, label):
        """Анимация изменения текста в label"""
        # Эффект мигания
        original_color = label.styleSheet()
        
        # Подсветка
        label.setStyleSheet(original_color + "color: #4a90e2;")
        
        # Возврат к исходному цвету через 200мс
        QTimer.singleShot(200, lambda: label.setStyleSheet(original_color))
        
    def show_completion_animation(self):
        """Анимация завершения"""
        self.particle_timer.stop()
        
        for i in range(12):
            particle = QLabel("✨", self)
            particle.setStyleSheet("color: #f1c40f; font-size: 20px;")
            particle.resize(25, 25)
            
            # Позиционируем вокруг иконки
            icon_center = self.processing_icon.geometry().center()
            angle = (i * 30) * math.pi / 180
            radius = 60
            
            start_x = icon_center.x()
            start_y = icon_center.y()
            end_x = icon_center.x() + int(radius * math.cos(angle))
            end_y = icon_center.y() + int(radius * math.sin(angle))
            
            particle.move(start_x, start_y)
            particle.show()
            
            # Анимация движения
            animation = QPropertyAnimation(particle, b"pos")
            animation.setDuration(1000)
            animation.setStartValue(QPoint(start_x, start_y))
            animation.setEndValue(QPoint(end_x, end_y))
            animation.setEasingCurve(QEasingCurve.OutQuad)
            animation.start()
            
            # Анимация исчезновения
            fade_animation = QPropertyAnimation(particle, b"windowOpacity")
            fade_animation.setDuration(1000)
            fade_animation.setStartValue(1.0)
            fade_animation.setEndValue(0.0)
            fade_animation.finished.connect(particle.deleteLater)
            fade_animation.start()
            
        # Автоматически закрываем через 2 секунды
        QTimer.singleShot(2000, self.accept)
        
    def show_cancel_button(self):
        """Показать кнопку отмены"""
        self.cancel_button.setVisible(True)
        
        # Анимация появления кнопки
        self.cancel_button.setStyleSheet(self.cancel_button.styleSheet() + "background-color: transparent;")
        
        button_animation = QPropertyAnimation(self.cancel_button, b"geometry")
        button_animation.setDuration(300)
        
        original_geometry = self.cancel_button.geometry()
        start_geometry = QRect(
            original_geometry.x(), 
            original_geometry.y() + 20,
            original_geometry.width(), 
            0
        )
        
        button_animation.setStartValue(start_geometry)
        button_animation.setEndValue(original_geometry)
        button_animation.setEasingCurve(QEasingCurve.OutBounce)
        button_animation.finished.connect(lambda: self.cancel_button.setStyleSheet(
            self.cancel_button.styleSheet().replace("background-color: transparent;", "")
        ))
        button_animation.start()
        
    def cancel_processing(self):
        """Отмена обработки"""
        self.is_processing = False
        self.processing_icon.setText("❌")
        self.processing_icon.setStyleSheet("font-size: 48px; color: #e74c3c;")
        self.status_label.setText("Обработка отменена")
        self.particle_timer.stop()
        
        # Закрываем через секунду
        QTimer.singleShot(1000, self.reject)
        
    def closeEvent(self, event):
        """Обработка закрытия диалога"""
        # Останавливаем все таймеры
        if hasattr(self, 'particle_timer'):
            self.particle_timer.stop()
            
        # Удаляем все частицы
        for particle in self.particles:
            particle.deleteLater()
            
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Темная тема
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    # Создаем и показываем диалог
    dialog = ProcessingDialog(title="Обработка")
    dialog.show()
    
    def simulate_processing():
        import time
        stages = [
            (10, "Загрузка данных...", "Чтение видео файла"),
            (25, "Инициализация...", "Настройка алгоритмов"),
            (40, "Анализ кадров...", "Обработка изображений"),
            (60, "Определение контуров...", "Поиск контактных областей"),
            (80, "Расчет метрик...", "Вычисление параметров"),
            (95, "Финализация...", "Сохранение результатов"),
            (100, "Готово!", "Анализ завершен успешно")
        ]
        
        for progress, status, details in stages:
            QTimer.singleShot(
                stages.index((progress, status, details)) * 1000,
                lambda p=progress, s=status, d=details: (
                    dialog.set_progress(p),
                    dialog.set_status(s),
                    dialog.set_details(d)
                )
            )
    
    QTimer.singleShot(1000, simulate_processing)
    
    QTimer.singleShot(2000, dialog.show_cancel_button)
    
    sys.exit(app.exec_())