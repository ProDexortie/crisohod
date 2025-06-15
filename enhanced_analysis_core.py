"""
enhanced_analysis_core.py
"""

import cv2
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from PyQt5.QtCore import pyqtSignal, QObject
from PIL import Image, ImageDraw, ImageFont
import warnings
warnings.filterwarnings('ignore')


class EnhancedAnalysisCore(QObject):
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)

    def __init__(self, video_path, csv_path, config_path='config.yaml'):
        super().__init__()
        
        # Проверка файлов
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Видео файл не найден: {video_path}")
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"CSV файл не найден: {csv_path}")
        if not Path(config_path).exists():
            raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

        self.video_path = video_path
        self.csv_path = csv_path
        self.config_path = config_path
        
        # Коэффициент перевода пикселей в миллиметры
        # По умолчанию 0.3 мм/пиксель (реалистично для большинства видео)
        self.pixel_to_mm_scale = 0.3
        
        # Загружаем конфигурацию
        self.load_config()
        
        # Инициализируем данные
        self.load_data()
        
        # Настройка шрифтов
        self.setup_fonts()
        
        # Цвета для визуализации
        self.PAW_COLORS = {
            'lf': (74, 144, 226),   # Синий
            'rf': (46, 204, 113),   # Зеленый
            'lb': (231, 76, 60),    # Красный
            'rb': (241, 196, 15)    # Желтый
        }
        
        self.PAW_LABELS = {
            'lf': 'lf', 'rf': 'rf', 
            'lb': 'lb', 'rb': 'rb'
        }
        
        # Алгоритмы обработки
        self.setup_algorithms()
        
    def set_pixel_to_mm_scale(self, scale):
        """Установка коэффициента перевода пикселей в мм"""
        self.pixel_to_mm_scale = float(scale)
        
    def get_pixel_to_mm_scale(self):
        """Получение коэффициента перевода"""
        return self.pixel_to_mm_scale
        
    def pixels_to_mm(self, pixels):
        """Перевод пикселей в миллиметры"""
        return pixels * self.pixel_to_mm_scale
        
    def pixels_to_mm2(self, pixels_squared):
        """Перевод квадратных пикселей в квадратные миллиметры"""
        return pixels_squared * (self.pixel_to_mm_scale ** 2)
        
    def load_config(self):
        """Загрузка конфигурации"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.bodyparts = config['bodyparts']
        self.skeleton = config.get('skeleton', [])
        
        # Группировка частей тела по лапам
        self.paw_groups = self._define_paw_groups()
        
    def _define_paw_groups(self):
        """Определение групп точек для каждой лапы"""
        groups = {'lf': [], 'rf': [], 'lb': [], 'rb': []}
        
        for bodypart in self.bodyparts:
            for paw_name in groups.keys():
                if bodypart.startswith(paw_name + '_'):
                    groups[paw_name].append(bodypart)
        
        return groups
        
    def load_data(self):
        """Загрузка данных CSV и видео"""
        # Загружаем CSV с координатами
        self.df = pd.read_csv(self.csv_path, header=[0, 1, 2], index_col=0)
        self.scorer = self.df.columns.levels[0][0]
        
        # Открываем видео
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {self.video_path}")
            
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
    def setup_fonts(self):
        """Настройка шрифтов для текста"""
        font_paths = [
            "arial.ttf",
            "DejaVuSans.ttf"
        ]
        
        self.font = None
        for font_path in font_paths:
            try:
                self.font = ImageFont.truetype(font_path, 24)
                break
            except (IOError, OSError):
                continue
        
        if not self.font:
            self.font = ImageFont.load_default()
            
    def setup_algorithms(self):
        """Настройка алгоритмов обработки"""
        # Ядра для морфологических операций
        self.morphology_kernels = {
            'small': cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
            'medium': cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
            'large': cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        }
        
    def get_coords(self, frame_idx, bodypart, likelihood_threshold=0.6):
        """Получение координат части тела с проверкой достоверности"""
        try:
            x = self.df.loc[frame_idx, (self.scorer, bodypart, 'x')]
            y = self.df.loc[frame_idx, (self.scorer, bodypart, 'y')]
            likelihood = self.df.loc[frame_idx, (self.scorer, bodypart, 'likelihood')]
            
            if likelihood >= likelihood_threshold and not pd.isna(x) and not pd.isna(y):
                return (float(x), float(y), float(likelihood))
        except (KeyError, IndexError, ValueError):
            pass
        return None
        
    def calculate_sciatic_index(self, length_mm, width_mm):
        """
        Вычисление седалищного индекса
        Формула: (Длина отпечатка / Ширина отпечатка) × 100
        
        Args:
            length_mm: Длина отпечатка в мм
            width_mm: Ширина отпечатка в мм
            
        Returns:
            float: Седалищный индекс
        """
        if width_mm > 0:
            return (length_mm / width_mm) * 100
        return 0.0
        
    def calculate_enhanced_metrics(self, frame_idx, paw_name):
        """Расчет улучшенных метрик для лапы в миллиметрах + седалищный индекс"""
        metrics = {
            'length_mm': 0.0,
            'width_1_5_mm': 0.0,
            'width_2_4_mm': 0.0,
            'perimeter_mm': 0.0,
            'aspect_ratio': 0.0,
            'solidity': 0.0,
            'eccentricity': 0.0,
            'sciatic_index': 0.0  # Добавляем седалищный индекс
        }
        
        # Получаем все координаты точек лапы
        paw_points = []
        for bodypart in self.paw_groups[paw_name]:
            coords = self.get_coords(frame_idx, bodypart)
            if coords:
                paw_points.append(coords)
                
        if len(paw_points) < 3:
            return metrics
            
        points_array = np.array([(p[0], p[1]) for p in paw_points])
        
        # Длина лапы (максимальное расстояние между точками) в пикселях, затем в мм
        distances = []
        for i in range(len(points_array)):
            for j in range(i + 1, len(points_array)):
                dist = np.linalg.norm(points_array[i] - points_array[j])
                distances.append(dist)
        
        if distances:
            metrics['length_mm'] = self.pixels_to_mm(max(distances))
            
        # Ширина для задних лап
        if paw_name in ['lb', 'rb']:
            digit1_coords = self.get_coords(frame_idx, f'{paw_name}_digit1')
            digit5_coords = self.get_coords(frame_idx, f'{paw_name}_digit5')
            
            if digit1_coords and digit5_coords:
                width_px = np.linalg.norm(
                    np.array([digit1_coords[0], digit1_coords[1]]) -
                    np.array([digit5_coords[0], digit5_coords[1]])
                )
                metrics['width_1_5_mm'] = self.pixels_to_mm(width_px)
                
        # Ширина между 2 и 4 пальцами
        digit2_coords = self.get_coords(frame_idx, f'{paw_name}_digit2')
        digit4_coords = self.get_coords(frame_idx, f'{paw_name}_digit4')
        
        if digit2_coords and digit4_coords:
            width_px = np.linalg.norm(
                np.array([digit2_coords[0], digit2_coords[1]]) -
                np.array([digit4_coords[0], digit4_coords[1]])
            )
            metrics['width_2_4_mm'] = self.pixels_to_mm(width_px)
            
        # Вычисляем седалищный индекс
        # Используем ширину 2-4 как основную для всех лап
        if metrics['length_mm'] > 0 and metrics['width_2_4_mm'] > 0:
            metrics['sciatic_index'] = self.calculate_sciatic_index(
                metrics['length_mm'], 
                metrics['width_2_4_mm']
            )
        # Для задних лап также можем использовать ширину 1-5 если она доступна
        elif paw_name in ['lb', 'rb'] and metrics['length_mm'] > 0 and metrics['width_1_5_mm'] > 0:
            metrics['sciatic_index'] = self.calculate_sciatic_index(
                metrics['length_mm'], 
                metrics['width_1_5_mm']
            )
            
        return metrics
        
    def analyze_paw_area_enhanced(self, frame, bbox, threshold_value, filters=None):
        # --- 1. Подготовка области интереса (ROI) ---
        if bbox is None or len(bbox) != 4:
            return 0, np.zeros((100, 100, 3), dtype=np.uint8), {}

        x_min, y_min, x_max, y_max = bbox
        x_min, y_min = max(0, x_min), max(0, y_min)
        x_max, y_max = min(frame.shape[1], x_max), min(frame.shape[0], y_max)

        if x_min >= x_max or y_min >= y_max:
            return 0, np.zeros((100, 100, 3), dtype=np.uint8), {}

        roi = frame[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            return 0, np.zeros((100, 100, 3), dtype=np.uint8), {}
        
        # --- 2. Обработка изображения (точно как в paw_contact_analyzer.py) ---
        
        # Преобразуем в градации серого
        if len(roi.shape) == 3:
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray_roi = roi.copy()
        
        # Применяем размытие для уменьшения шума
        blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
        
        # Бинаризация (КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ!)
        if threshold_value == -1:  # Автоматический порог
            # Используем адаптивный порог или метод Otsu (как в paw_contact_analyzer)
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            # Ручной порог (как в paw_contact_analyzer)
            _, binary = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Морфологические операции для очистки (как в paw_contact_analyzer)
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # --- 3. Подсчет белых пикселей (контактная область) ---
        # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: используем точно тот же метод, что в paw_contact_analyzer
        contact_area_px = np.sum(binary == 255)
        
        # --- 4. Дополнительный анализ компонентов для расширенных метрик ---
        analysis_results = self.analyze_components(binary)
        analysis_results['total_area'] = contact_area_px  # Убеждаемся, что площадь правильная
        
        # --- 5. Создание визуализации ---
        # Создаем цветную версию бинарного изображения для отображения
        if roi.shape[0] > 0 and roi.shape[1] > 0:
            # Создаем трехканальную версию оригинального ROI
            original_roi_color = roi.copy() if len(roi.shape) == 3 else cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
            
            # Создаем цветную маску для контактной области
            color_mask = np.zeros_like(original_roi_color)
            color_mask[binary == 255] = (0, 255, 255)  # Желтый цвет (BGR)
            
            # Комбинируем оригинал с маской
            visualization_image = cv2.addWeighted(color_mask, 0.4, original_roi_color, 0.6, 0)
        else:
            visualization_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # --- 6. Возврат результатов ---
        return contact_area_px, visualization_image, analysis_results
        
    def apply_filters(self, image, filters):
        """Применение фильтров"""
        result = image.copy()
        
        # Гауссово размытие
        if filters.get('gaussian_blur', True):
            result = cv2.GaussianBlur(result, (5, 5), 1.0)
            
        # Медианный фильтр
        if filters.get('noise_reduction', True):
            result = cv2.medianBlur(result, 3)
            
        # Улучшение контраста
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        result = clahe.apply(result)
        
        return result
        
    def apply_thresholding(self, image, threshold_value):

        if threshold_value == -1:
            # Автоматический метод Otsu (как в paw_contact_analyzer)
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            # Ручной порог (как в paw_contact_analyzer)
            _, binary = cv2.threshold(image, threshold_value, 255, cv2.THRESH_BINARY)
                
        return binary
        
    def apply_morphology(self, binary_image):

        kernel = np.ones((3, 3), np.uint8)
        
        # Заполнение отверстий
        closed = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
        
        # Удаление шума
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
        
        return opened
        
    def analyze_components(self, binary_image):

        # 1. Главное: считаем площадь как количество белых пикселей (как в paw_contact_analyzer)
        contact_area = np.sum(binary_image == 255)

        # 2. Инициализируем словарь с результатами
        analysis_results = {
            'total_area': contact_area,
            'num_components': 0,
            'perimeter_px': 0,
            'length_px': 0,
            'width_2_4_px': 0,
            'width_1_5_px': 0,
            'aspect_ratio': 0,
            'solidity': 0,
            'eccentricity': 0,
            'key_points': []
        }

        # 3. Находим контуры для вычисления дополнительных метрик
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        analysis_results['num_components'] = len(contours)

        # 4. Если контуры найдены, вычисляем по самому большому из них
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Периметр в пикселях
            perimeter_px = cv2.arcLength(largest_contour, True)
            analysis_results['perimeter_px'] = round(perimeter_px, 2)
            
            # Длина (по описанному прямоугольнику) в пикселях
            x, y, w, h = cv2.boundingRect(largest_contour)
            analysis_results['length_px'] = max(w, h)
            
            # Соотношение сторон
            if h > 0:
                analysis_results['aspect_ratio'] = round(w / h, 2)

            # Солидность (плотность)
            hull = cv2.convexHull(largest_contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                contour_area = cv2.contourArea(largest_contour)
                analysis_results['solidity'] = round(contour_area / hull_area, 2)
                
        return analysis_results
        
    def get_data_for_frame(self, frame_idx, threshold_value=128, crop_pixels=0, filters=None):
        if filters is None:
            filters = {
                'gaussian_blur': True,
                'morphology': True,
                'noise_reduction': True
            }
            
        # Читаем кадр
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        
        if not ret:
            return None, None
            
        # Обрезка
        h, w, _ = frame.shape
        if crop_pixels > 0 and (h - 2 * crop_pixels) > 0:
            cropped_frame = frame[crop_pixels:h - crop_pixels, :].copy()
        else:
            cropped_frame = frame.copy()
            crop_pixels = 0
            
        # Создаем аннотированную версию
        annotated_frame = cropped_frame.copy()
        
        # Анализируем каждую лапу
        frame_analysis_results = {}
        
        for paw_name in self.paw_groups.keys():
            # Получаем координаты точек лапы
            paw_points = []
            for bodypart in self.paw_groups[paw_name]:
                coords = self.get_coords(frame_idx, bodypart)
                if coords:
                    paw_points.append((coords[0], coords[1] - crop_pixels))
                    
            if len(paw_points) >= 3:
                # Вычисляем bounding box
                points_array = np.array(paw_points)
                x_min, y_min = points_array.min(axis=0)
                x_max, y_max = points_array.max(axis=0)
                
                # Добавляем отступ
                padding = 15
                x_min = max(0, int(x_min - padding))
                y_min = max(0, int(y_min - padding))
                x_max = min(cropped_frame.shape[1], int(x_max + padding))
                y_max = min(cropped_frame.shape[0], int(y_max + padding))
                
                bbox = (x_min, y_min, x_max, y_max)
                
                # Анализируем контактную область
                area_px, viz_roi, analysis_data = self.analyze_paw_area_enhanced(
                    cropped_frame, bbox, threshold_value, filters
                )
                
                # Переводим площадь в мм²
                area_mm2 = self.pixels_to_mm2(area_px)
                
                # Вычисляем метрики (уже в мм + седалищный индекс)
                metrics = self.calculate_enhanced_metrics(frame_idx, paw_name)
                
                # Сохраняем результаты
                frame_analysis_results[paw_name] = {
                    'area_mm2': area_mm2,  # Площадь в мм²
                    'roi_image': viz_roi,  # Правильное цветное изображение для визуализации
                    'bbox': bbox,
                    'analysis_data': analysis_data,
                    **metrics  # Все метрики уже в мм + седалищный индекс
                }
                
                # Рисуем bbox и информацию на кадре
                color = self.PAW_COLORS[paw_name]
                cv2.rectangle(annotated_frame, (x_min, y_min), (x_max, y_max), color, 2)
                
                text = f"{self.PAW_LABELS[paw_name]}: {area_mm2:.1f}mm2"
                cv2.putText(annotated_frame, text, (x_min, y_min - 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Добавляем седалищный индекс
                if metrics['sciatic_index'] > 0:
                    sciatic_text = f"SI: {metrics['sciatic_index']:.1f}"
                    cv2.putText(annotated_frame, sciatic_text, (x_min, y_min - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                           
            else:
                # Нет достаточно точек для анализа
                frame_analysis_results[paw_name] = {
                    'area_mm2': 0.0,
                    'roi_image': np.zeros((100, 100, 3), dtype=np.uint8),  # Цветное изображение
                    'bbox': None,
                    'analysis_data': {},
                    'length_mm': 0.0,
                    'width_1_5_mm': 0.0,
                    'width_2_4_mm': 0.0,
                    'perimeter_mm': 0.0,
                    'aspect_ratio': 0.0,
                    'solidity': 0.0,
                    'eccentricity': 0.0,
                    'sciatic_index': 0.0  # Седалищный индекс
                }
                
        # Рисуем скелет
        self.draw_skeleton(annotated_frame, frame_idx, y_offset=-crop_pixels)
        
        return annotated_frame, frame_analysis_results
        
    def draw_skeleton(self, frame, frame_idx, y_offset=0, likelihood_threshold=0.6):
        """Рисование скелета"""
        # Рисуем соединения
        for connection in self.skeleton:
            point1, point2 = connection
            
            coords1 = self.get_coords(frame_idx, point1, likelihood_threshold)
            coords2 = self.get_coords(frame_idx, point2, likelihood_threshold)
            
            if coords1 and coords2:
                p1 = (int(coords1[0]), int(coords1[1] + y_offset))
                p2 = (int(coords2[0]), int(coords2[1] + y_offset))
                
                cv2.line(frame, p1, p2, (255, 255, 0), 2)
                
        # Рисуем точки
        for bodypart in self.bodyparts:
            coords = self.get_coords(frame_idx, bodypart, likelihood_threshold)
            
            if coords:
                # Определяем цвет точки по принадлежности к лапе
                color = (255, 255, 255)  # Белый по умолчанию
                
                for paw_name, paw_points in self.paw_groups.items():
                    if bodypart in paw_points:
                        color = self.PAW_COLORS[paw_name]
                        break
                        
                center = (int(coords[0]), int(coords[1] + y_offset))
                confidence = coords[2]
                
                # Размер точки зависит от достоверности
                radius = max(1, int(2 * confidence))
                
                cv2.circle(frame, center, radius, color, -1)
                cv2.circle(frame, center, radius + 1, (255, 255, 255), 1)
                
    def analyze_entire_video(self, threshold_value, filters=None, progress_callback=None):
        """Исправленная версия анализа всего видео с переводом в мм + седалищный индекс"""
        if filters is None:
            filters = {
                'gaussian_blur': True,
                'morphology': True,
                'noise_reduction': True
            }
            
        all_results = []
        
        for frame_idx in range(self.total_frames):
            # Обновляем прогресс
            if progress_callback:
                progress = (frame_idx / self.total_frames) * 100
                progress_callback(progress)
                
            # Базовые данные кадра
            frame_data = {'frame': frame_idx}
            
            # Читаем кадр
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            
            if not ret:
                continue
                
            # Анализируем каждую лапу
            for paw_name in self.paw_groups.keys():
                # Получаем метрики в мм + седалищный индекс
                metrics = self.calculate_enhanced_metrics(frame_idx, paw_name)
                
                # Анализируем контактную область
                paw_points = []
                for bodypart in self.paw_groups[paw_name]:
                    coords = self.get_coords(frame_idx, bodypart)
                    if coords:
                        paw_points.append((coords[0], coords[1]))
                        
                area_mm2 = 0.0
                if len(paw_points) >= 3:
                    points_array = np.array(paw_points)
                    x_min, y_min = points_array.min(axis=0)
                    x_max, y_max = points_array.max(axis=0)
                    
                    padding = 15
                    bbox = (
                        max(0, int(x_min - padding)),
                        max(0, int(y_min - padding)),
                        min(frame.shape[1], int(x_max + padding)),
                        min(frame.shape[0], int(y_max + padding))
                    )
                    
                    # Используем исправленный метод!
                    area_px, _, _ = self.analyze_paw_area_enhanced(frame, bbox, threshold_value, filters)
                    area_mm2 = self.pixels_to_mm2(area_px)
                    
                # Сохраняем данные в мм + седалищный индекс
                frame_data[f'{paw_name}_area_mm2'] = area_mm2
                frame_data[f'{paw_name}_length_mm'] = metrics['length_mm']
                frame_data[f'{paw_name}_width_2_4_mm'] = metrics['width_2_4_mm']
                frame_data[f'{paw_name}_sciatic_index'] = metrics['sciatic_index']  # Добавляем седалищный индекс
                
                if paw_name in ['lb', 'rb']:
                    frame_data[f'{paw_name}_width_1_5_mm'] = metrics['width_1_5_mm']
                    
                # Дополнительные метрики
                frame_data[f'{paw_name}_perimeter_mm'] = self.pixels_to_mm(metrics.get('perimeter_mm', 0))
                frame_data[f'{paw_name}_aspect_ratio'] = metrics['aspect_ratio']
                frame_data[f'{paw_name}_solidity'] = metrics['solidity']
                frame_data[f'{paw_name}_eccentricity'] = metrics['eccentricity']
                
            all_results.append(frame_data)
            
            # Обновляем статус
            if frame_idx % 50 == 0:
                self.status_updated.emit(f"Обработано {frame_idx}/{self.total_frames} кадров")
                
        # Финальное обновление прогресса
        if progress_callback:
            progress_callback(100)
            
        self.status_updated.emit("Анализ завершен")
        
        return pd.DataFrame(all_results)
        
    def close(self):
        """Освобождение ресурсов"""
        if self.cap:
            self.cap.release()