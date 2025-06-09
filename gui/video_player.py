"""
gui/video_player.py
Виджет для воспроизведения видео с наложением скелета
"""

import cv2
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QSlider, QLabel, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
import yaml


class VideoThread(QThread):
    """Поток для чтения видео"""
    frame_ready = pyqtSignal(np.ndarray)
    position_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.csv_data = None
        self.bodyparts = []
        self.skeleton = []
        self.show_skeleton = True
        self.show_labels = True
        self.show_paw_areas = True
        
    def load_video(self, video_path):
        """Загрузка видео"""
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.current_frame = 0
        
    def load_csv(self, csv_path):
        """Загрузка CSV с координатами"""
        self.csv_data = pd.read_csv(csv_path, header=[0, 1, 2], index_col=0)
        
    def load_config(self, config_path):
        """Загрузка конфигурации для скелета"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        self.bodyparts = config.get('bodyparts', [])
        self.skeleton = config.get('skeleton', [])
        
    def run(self):
        """Основной цикл воспроизведения"""
        while self.cap:
            if self.is_playing:
                ret, frame = self.cap.read()
                if ret:
                    # Накладываем скелет если есть данные
                    if self.csv_data is not None:
                        frame = self.draw_skeleton(frame, self.current_frame)
                    
                    self.frame_ready.emit(frame)
                    self.current_frame += 1
                    self.position_changed.emit(self.current_frame)
                    
                    if self.current_frame >= self.total_frames:
                        self.is_playing = False
                        self.current_frame = 0
                        
                    self.msleep(int(1000 / self.fps))
                else:
                    self.is_playing = False
            else:
                self.msleep(50)
                
    def draw_skeleton(self, frame, frame_idx):
        """Отрисовка скелета на кадре"""
        if self.csv_data is None or frame_idx >= len(self.csv_data):
            return frame
            
        frame_copy = frame.copy()
        scorer = self.csv_data.columns.levels[0][0]
        
        # Цвета для разных лап
        paw_colors = {
            'lf': (255, 0, 0),      # Красный
            'rf': (0, 255, 0),      # Зеленый
            'lb': (0, 0, 255),      # Синий
            'rb': (255, 255, 0)     # Желтый
        }
        
        # Рисуем скелет
        if self.show_skeleton:
            for connection in self.skeleton:
                point1, point2 = connection
                try:
                    x1 = self.csv_data.loc[frame_idx, (scorer, point1, 'x')]
                    y1 = self.csv_data.loc[frame_idx, (scorer, point1, 'y')]
                    likelihood1 = self.csv_data.loc[frame_idx, (scorer, point1, 'likelihood')]
                    
                    x2 = self.csv_data.loc[frame_idx, (scorer, point2, 'x')]
                    y2 = self.csv_data.loc[frame_idx, (scorer, point2, 'y')]
                    likelihood2 = self.csv_data.loc[frame_idx, (scorer, point2, 'likelihood')]
                    
                    if likelihood1 > 0.6 and likelihood2 > 0.6:
                        cv2.line(frame_copy, (int(x1), int(y1)), (int(x2), int(y2)), 
                                (0, 255, 255), 2)
                except:
                    continue
        
        # Рисуем точки
        for bodypart in self.bodyparts:
            try:
                x = self.csv_data.loc[frame_idx, (scorer, bodypart, 'x')]
                y = self.csv_data.loc[frame_idx, (scorer, bodypart, 'y')]
                likelihood = self.csv_data.loc[frame_idx, (scorer, bodypart, 'likelihood')]
                
                if likelihood > 0.6:
                    # Определяем цвет по принадлежности к лапе
                    color = (255, 255, 255)
                    for paw_prefix, paw_color in paw_colors.items():
                        if bodypart.startswith(paw_prefix):
                            color = paw_color
                            break
                    
                    cv2.circle(frame_copy, (int(x), int(y)), 4, color, -1)
                    
                    # Добавляем подписи
                    if self.show_labels:
                        cv2.putText(frame_copy, bodypart, (int(x) + 5, int(y) - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
            except:
                continue
                
        # Рисуем области контакта лап (если включено)
        if self.show_paw_areas:
            self.draw_paw_areas(frame_copy, frame_idx)
            
        return frame_copy
        
    def draw_paw_areas(self, frame, frame_idx):
        """Отрисовка областей контакта лап"""
        # Здесь будет логика отрисовки областей контакта
        # Пока просто рисуем bbox вокруг каждой лапы
        paw_groups = {
            'lf': [], 'rf': [], 'lb': [], 'rb': []
        }
        
        scorer = self.csv_data.columns.levels[0][0]
        
        # Группируем точки по лапам
        for bodypart in self.bodyparts:
            for paw_name in paw_groups.keys():
                if bodypart.startswith(paw_name + '_'):
                    paw_groups[paw_name].append(bodypart)
        
        # Рисуем bbox для каждой лапы
        for paw_name, points in paw_groups.items():
            valid_points = []
            for point in points:
                try:
                    x = self.csv_data.loc[frame_idx, (scorer, point, 'x')]
                    y = self.csv_data.loc[frame_idx, (scorer, point, 'y')]
                    likelihood = self.csv_data.loc[frame_idx, (scorer, point, 'likelihood')]
                    
                    if likelihood > 0.6:
                        valid_points.append((x, y))
                except:
                    continue
                    
            if len(valid_points) >= 3:
                valid_points = np.array(valid_points)
                x_min, y_min = valid_points.min(axis=0)
                x_max, y_max = valid_points.max(axis=0)
                
                # Добавляем отступ
                padding = 10
                x_min = max(0, x_min - padding)
                y_min = max(0, y_min - padding)
                x_max = min(frame.shape[1], x_max + padding)
                y_max = min(frame.shape[0], y_max + padding)
                
                # Цвет в зависимости от лапы
                colors = {
                    'lf': (255, 100, 100),
                    'rf': (100, 255, 100),
                    'lb': (100, 100, 255),
                    'rb': (255, 255, 100)
                }
                
                cv2.rectangle(frame, (int(x_min), int(y_min)), 
                             (int(x_max), int(y_max)), colors[paw_name], 2)
                
    def play(self):
        """Начать воспроизведение"""
        self.is_playing = True
        
    def pause(self):
        """Пауза"""
        self.is_playing = False
        
    def seek(self, frame_number):
        """Перейти к кадру"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.current_frame = frame_number
            ret, frame = self.cap.read()
            if ret:
                if self.csv_data is not None:
                    frame = self.draw_skeleton(frame, frame_number)
                self.frame_ready.emit(frame)
                self.position_changed.emit(frame_number)


class VideoPlayer(QWidget):
    """Виджет видеоплеера"""
    frame_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.csv_path = None
        self.video_thread = VideoThread()
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Область отображения видео
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setScaledContents(True)
        self.video_label.setStyleSheet("border: 2px solid #505050;")
        layout.addWidget(self.video_label)
        
        # Контролы управления
        controls_layout = QVBoxLayout()
        
        # Слайдер прогресса
        progress_layout = QHBoxLayout()
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setEnabled(False)
        progress_layout.addWidget(self.progress_slider)
        
        self.frame_spin = QSpinBox()
        self.frame_spin.setEnabled(False)
        self.frame_spin.setMinimumWidth(80)
        progress_layout.addWidget(self.frame_spin)
        
        controls_layout.addLayout(progress_layout)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setEnabled(False)
        self.play_btn.setCheckable(True)
        buttons_layout.addWidget(self.play_btn)
        
        self.prev_frame_btn = QPushButton("◀◀")
        self.prev_frame_btn.setEnabled(False)
        buttons_layout.addWidget(self.prev_frame_btn)
        
        self.next_frame_btn = QPushButton("▶▶")
        self.next_frame_btn.setEnabled(False)
        buttons_layout.addWidget(self.next_frame_btn)
        
        buttons_layout.addStretch()
        
        # Опции отображения
        self.show_skeleton_cb = QCheckBox("Скелет")
        self.show_skeleton_cb.setChecked(True)
        buttons_layout.addWidget(self.show_skeleton_cb)
        
        self.show_labels_cb = QCheckBox("Подписи")
        self.show_labels_cb.setChecked(True)
        buttons_layout.addWidget(self.show_labels_cb)
        
        self.show_areas_cb = QCheckBox("Области контакта")
        self.show_areas_cb.setChecked(True)
        buttons_layout.addWidget(self.show_areas_cb)
        
        controls_layout.addLayout(buttons_layout)
        layout.addLayout(controls_layout)
        
        # Запускаем поток
        self.video_thread.start()
        
    def setup_connections(self):
        """Настройка соединений"""
        self.video_thread.frame_ready.connect(self.update_frame)
        self.video_thread.position_changed.connect(self.update_position)
        
        self.play_btn.clicked.connect(self.toggle_playback)
        self.prev_frame_btn.clicked.connect(self.prev_frame)
        self.next_frame_btn.clicked.connect(self.next_frame)
        
        self.progress_slider.sliderMoved.connect(self.seek)
        self.frame_spin.valueChanged.connect(self.seek)
        
        self.show_skeleton_cb.toggled.connect(
            lambda checked: setattr(self.video_thread, 'show_skeleton', checked)
        )
        self.show_labels_cb.toggled.connect(
            lambda checked: setattr(self.video_thread, 'show_labels', checked)
        )
        self.show_areas_cb.toggled.connect(
            lambda checked: setattr(self.video_thread, 'show_paw_areas', checked)
        )
        
    def load_video(self, video_path):
        """Загрузка видео"""
        self.video_path = video_path
        self.video_thread.load_video(video_path)
        
        # Обновляем контролы
        total_frames = self.video_thread.total_frames
        self.progress_slider.setRange(0, total_frames - 1)
        self.progress_slider.setEnabled(True)
        
        self.frame_spin.setRange(0, total_frames - 1)
        self.frame_spin.setEnabled(True)
        
        self.play_btn.setEnabled(True)
        self.prev_frame_btn.setEnabled(True)
        self.next_frame_btn.setEnabled(True)
        
        # Показываем первый кадр
        self.seek(0)
        
    def load_processed_video(self, video_path, csv_path, config_path='config.yaml'):
        """Загрузка обработанного видео с CSV"""
        self.load_video(video_path)
        self.csv_path = csv_path
        self.video_thread.load_csv(csv_path)
        self.video_thread.load_config(config_path)
        
        # Обновляем первый кадр
        self.seek(0)
        
    def get_video_info(self):
        """Получение информации о видео"""
        if not self.video_thread.cap:
            return {}
            
        return {
            'width': int(self.video_thread.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.video_thread.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.video_thread.fps,
            'total_frames': self.video_thread.total_frames,
            'duration': self.video_thread.total_frames / self.video_thread.fps
        }
        
    def update_frame(self, frame):
        """Обновление кадра"""
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_image)
        
        # Масштабируем под размер label
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)
        
    def update_position(self, position):
        """Обновление позиции"""
        self.progress_slider.blockSignals(True)
        self.frame_spin.blockSignals(True)
        
        self.progress_slider.setValue(position)
        self.frame_spin.setValue(position)
        
        self.progress_slider.blockSignals(False)
        self.frame_spin.blockSignals(False)
        
        self.frame_changed.emit(position)
        
    def toggle_playback(self):
        """Переключение воспроизведения"""
        if self.play_btn.isChecked():
            self.video_thread.play()
            self.play_btn.setText("⏸")
        else:
            self.video_thread.pause()
            self.play_btn.setText("▶")
            
    def prev_frame(self):
        """Предыдущий кадр"""
        current = self.video_thread.current_frame
        if current > 0:
            self.seek(current - 1)
            
    def next_frame(self):
        """Следующий кадр"""
        current = self.video_thread.current_frame
        if current < self.video_thread.total_frames - 1:
            self.seek(current + 1)
            
    def seek(self, frame_number):
        """Перейти к кадру"""
        self.video_thread.seek(frame_number)
        
    def seek_to_frame(self, frame_number):
        """Публичный метод для перехода к кадру"""
        self.seek(frame_number)