"""
analysis/paw_analyzer.py
Улучшенный анализатор для измерения параметров лап
"""

import cv2
import numpy as np
import pandas as pd
from pathlib import Path
import json
from scipy.spatial import distance


class EnhancedPawAnalyzer:
    """Расширенный анализатор параметров лап"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config_path = config_manager.get('config_path', 'config.yaml')
        self.threshold_value = config_manager.get('threshold_value', 128)
        self.pixel_to_mm = None
        
        # Загружаем конфигурацию
        self._load_config()
        
    def _load_config(self):
        """Загрузка конфигурации"""
        import yaml
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        self.bodyparts = config['bodyparts']
        self.skeleton = config.get('skeleton', [])
        
        # Определяем группы точек для каждой лапы
        self.paw_groups = {
            'lf': [],  # левая передняя
            'rf': [],  # правая передняя
            'lb': [],  # левая задняя
            'rb': []   # правая задняя
        }
        
        for bodypart in self.bodyparts:
            for paw_name in self.paw_groups.keys():
                if bodypart.startswith(paw_name + '_'):
                    self.paw_groups[paw_name].append(bodypart)
                    
    def analyze_video(self, video_path, csv_path, output_dir=None):
        """
        Полный анализ видео
        
        Returns:
            dict с результатами анализа
        """
        video_path = Path(video_path)
        csv_path = Path(csv_path)
        
        if output_dir is None:
            output_dir = video_path.parent / 'analysis_results'
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Проверяем калибровку
        self._load_calibration(video_path)
        
        # Загружаем данные DeepLabCut
        df = pd.read_csv(csv_path, header=[0, 1, 2], index_col=0)
        
        # Открываем видео
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        print(f"Анализ видео: {video_path.name}")
        print(f"Всего кадров: {total_frames}, FPS: {fps}")
        
        # Результаты для каждого кадра
        frame_results = []
        
        # Изображения лап для визуализации
        paw_images = {}
        
        frame_idx = 0
        while frame_idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Анализируем кадр
            frame_data = self._analyze_frame(frame, df, frame_idx)
            frame_data['frame'] = frame_idx
            frame_results.append(frame_data)
            
            # Сохраняем изображения лап для ключевых кадров
            if frame_idx % (total_frames // 10) == 0:  # Каждые 10%
                paw_images[frame_idx] = self._extract_paw_images(frame, df, frame_idx)
                
            frame_idx += 1
            
            # Прогресс
            if frame_idx % 100 == 0:
                progress = (frame_idx / total_frames) * 100
                print(f"Проанализировано: {progress:.1f}%")
                
        cap.release()
        
        # Создаем DataFrame с результатами
        results_df = pd.DataFrame(frame_results)
        
        # Вычисляем статистику
        statistics = self._calculate_statistics(results_df)
        
        # Сохраняем результаты
        results_df.to_csv(output_dir / 'frame_data.csv', index=False)
        
        with open(output_dir / 'statistics.json', 'w') as f:
            json.dump(statistics, f, indent=2)
            
        # Создаем визуализации
        self._create_visualizations(results_df, output_dir)
        
        print("Анализ завершен!")
        
        return {
            'frame_data': frame_results,
            'statistics': statistics,
            'paw_images': paw_images,
            'output_dir': str(output_dir)
        }
        
    def _load_calibration(self, video_path):
        """Загрузка калибровочных данных"""
        # Проверяем файл с калибровкой
        cal_file = video_path.with_suffix('.cal')
        if cal_file.exists():
            with open(cal_file, 'r') as f:
                cal_data = json.load(f)
                self.pixel_to_mm = cal_data.get('pixel_to_mm', 0.1)
        else:
            # Используем значение из конфигурации или по умолчанию
            self.pixel_to_mm = self.config_manager.get('pixel_to_mm', 0.1)
            
        print(f"Коэффициент преобразования: {self.pixel_to_mm:.4f} мм/пиксель")
        
    def _analyze_frame(self, frame, df, frame_idx):
        """Анализ одного кадра"""
        frame_data = {}
        scorer = df.columns.levels[0][0]
        
        for paw_name, paw_points in self.paw_groups.items():
            # Получаем координаты точек лапы
            points = []
            for point_name in paw_points:
                try:
                    x = df.loc[frame_idx, (scorer, point_name, 'x')]
                    y = df.loc[frame_idx, (scorer, point_name, 'y')]
                    likelihood = df.loc[frame_idx, (scorer, point_name, 'likelihood')]
                    
                    if likelihood > 0.6:
                        points.append({
                            'name': point_name,
                            'x': float(x),  # Конвертируем в float
                            'y': float(y),  # Конвертируем в float
                            'likelihood': float(likelihood)  # Конвертируем в float
                        })
                except:
                    continue
                    
            if len(points) < 3:
                # Недостаточно точек для анализа
                frame_data.update(self._get_empty_paw_data(paw_name))
                continue
                
            # Анализ площади контакта
            bbox = self._get_bbox(points)
            contact_area_px, contact_mask = self._analyze_contact_area(frame, bbox)
            contact_area_mm2 = contact_area_px * (self.pixel_to_mm ** 2)
            
            frame_data[f'{paw_name}_area_px'] = int(contact_area_px)  # Конвертируем в int
            frame_data[f'{paw_name}_area_mm2'] = float(contact_area_mm2)  # Конвертируем в float
            
            # Морфометрические параметры
            morpho_params = self._calculate_morphometric_params(points, paw_name)
            frame_data.update(morpho_params)
            
        return frame_data
        
    def _get_bbox(self, points):
        """Получение ограничивающего прямоугольника"""
        coords = [(p['x'], p['y']) for p in points]
        coords = np.array(coords)
        
        x_min, y_min = coords.min(axis=0)
        x_max, y_max = coords.max(axis=0)
        
        # Добавляем отступ
        padding = 15
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = x_max + padding
        y_max = y_max + padding
        
        return int(x_min), int(y_min), int(x_max), int(y_max)
        
    def _analyze_contact_area(self, image, bbox):
        """Анализ площади контакта"""
        x_min, y_min, x_max, y_max = bbox
        
        # Вырезаем область
        roi = image[y_min:y_max, x_min:x_max]
        
        if roi.size == 0:
            return 0, None
            
        # Преобразуем в градации серого
        if len(roi.shape) == 3:
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray_roi = roi.copy()
            
        # Применяем размытие
        blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
        
        # Адаптивная бинаризация
        if self.config_manager.get('use_adaptive_threshold', True):
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        else:
            _, binary = cv2.threshold(blurred, self.threshold_value, 255, cv2.THRESH_BINARY)
            
        # Морфологические операции
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Находим контуры
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Фильтруем контуры по размеру
        min_area = 50  # минимальная площадь в пикселях
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
        
        # Создаем маску контактной области
        contact_mask = np.zeros_like(binary)
        cv2.drawContours(contact_mask, valid_contours, -1, 255, -1)
        
        # Подсчет площади
        contact_area = np.sum(contact_mask == 255)
        
        return contact_area, contact_mask
        
    def _calculate_morphometric_params(self, points, paw_name):
        """Расчет морфометрических параметров лапы"""
        params = {}
        
        # Находим специфичные точки
        heel = next((p for p in points if 'heel' in p['name']), None)
        digits = [p for p in points if 'digit' in p['name']]
        center = next((p for p in points if 'center' in p['name']), None)
        
        # Длина лапы (от пятки до самого дальнего пальца)
        if heel and digits:
            heel_pos = np.array([heel['x'], heel['y']])
            
            max_dist = 0
            for digit in digits:
                digit_pos = np.array([digit['x'], digit['y']])
                dist = np.linalg.norm(digit_pos - heel_pos)
                max_dist = max(max_dist, dist)
                
            length_px = max_dist
            length_mm = length_px * self.pixel_to_mm
            
            params[f'{paw_name}_length_px'] = float(length_px)  # Конвертируем в float
            params[f'{paw_name}_length_mm'] = float(length_mm)  # Конвертируем в float
        else:
            params[f'{paw_name}_length_px'] = 0.0
            params[f'{paw_name}_length_mm'] = 0.0
            
        # Для задних лап - дополнительные параметры
        if paw_name.endswith('b'):  # lb или rb
            # Расстояние между 1 и 5 пальцами
            digit1 = next((p for p in points if 'digit1' in p['name']), None)
            digit5 = next((p for p in points if 'digit5' in p['name']), None)
            
            if digit1 and digit5:
                d1_pos = np.array([digit1['x'], digit1['y']])
                d5_pos = np.array([digit5['x'], digit5['y']])
                width_1_5_px = np.linalg.norm(d5_pos - d1_pos)
                width_1_5_mm = width_1_5_px * self.pixel_to_mm
                
                params[f'{paw_name}_width_1_5_px'] = float(width_1_5_px)
                params[f'{paw_name}_width_1_5_mm'] = float(width_1_5_mm)
            else:
                params[f'{paw_name}_width_1_5_px'] = 0.0
                params[f'{paw_name}_width_1_5_mm'] = 0.0
                
            # Расстояние между 2 и 4 пальцами
            digit2 = next((p for p in points if 'digit2' in p['name']), None)
            digit4 = next((p for p in points if 'digit4' in p['name']), None)
            
            if digit2 and digit4:
                d2_pos = np.array([digit2['x'], digit2['y']])
                d4_pos = np.array([digit4['x'], digit4['y']])
                width_2_4_px = np.linalg.norm(d4_pos - d2_pos)
                width_2_4_mm = width_2_4_px * self.pixel_to_mm
                
                params[f'{paw_name}_width_2_4_px'] = float(width_2_4_px)
                params[f'{paw_name}_width_2_4_mm'] = float(width_2_4_mm)
            else:
                params[f'{paw_name}_width_2_4_px'] = 0.0
                params[f'{paw_name}_width_2_4_mm'] = 0.0
        else:
            # Для передних лап только общая ширина
            if digits and len(digits) >= 2:
                # Находим крайние точки
                x_coords = [d['x'] for d in digits]
                width_px = max(x_coords) - min(x_coords)
                width_mm = width_px * self.pixel_to_mm
                
                params[f'{paw_name}_width_px'] = float(width_px)
                params[f'{paw_name}_width_mm'] = float(width_mm)
            else:
                params[f'{paw_name}_width_px'] = 0.0
                params[f'{paw_name}_width_mm'] = 0.0
                
        return params
        
    def _get_empty_paw_data(self, paw_name):
        """Возвращает пустые данные для лапы"""
        data = {
            f'{paw_name}_area_px': 0,
            f'{paw_name}_area_mm2': 0,
            f'{paw_name}_length_px': 0,
            f'{paw_name}_length_mm': 0
        }
        
        if paw_name.endswith('b'):
            data.update({
                f'{paw_name}_width_1_5_px': 0,
                f'{paw_name}_width_1_5_mm': 0,
                f'{paw_name}_width_2_4_px': 0,
                f'{paw_name}_width_2_4_mm': 0
            })
        else:
            data.update({
                f'{paw_name}_width_px': 0,
                f'{paw_name}_width_mm': 0
            })
            
        return data
        
    def _extract_paw_images(self, frame, df, frame_idx):
        """Извлечение изображений отдельных лап"""
        paw_images = {}
        scorer = df.columns.levels[0][0]
        
        for paw_name, paw_points in self.paw_groups.items():
            # Получаем координаты
            points = []
            for point_name in paw_points:
                try:
                    x = df.loc[frame_idx, (scorer, point_name, 'x')]
                    y = df.loc[frame_idx, (scorer, point_name, 'y')]
                    likelihood = df.loc[frame_idx, (scorer, point_name, 'likelihood')]
                    
                    if likelihood > 0.6:
                        points.append({'x': x, 'y': y})
                except:
                    continue
                    
            if len(points) >= 3:
                bbox = self._get_bbox(points)
                x_min, y_min, x_max, y_max = bbox
                
                # Вырезаем область
                paw_img = frame[y_min:y_max, x_min:x_max]
                
                if paw_img.size > 0:
                    # Масштабируем до стандартного размера
                    paw_img_resized = cv2.resize(paw_img, (200, 200))
                    paw_images[paw_name] = paw_img_resized
                    
        return paw_images
        
    def _calculate_statistics(self, df):
        """Расчет статистики по всему видео"""
        stats = {
            'total_frames': int(len(df)),
            'duration': float(len(df) / 30.0),  # Предполагаем 30 FPS
            'fps': 30
        }
        
        # Общая статистика контактных площадей
        total_areas = []
        for _, row in df.iterrows():
            total_area = sum([
                row.get(f'{paw}_area_mm2', 0) 
                for paw in ['lf', 'rf', 'lb', 'rb']
            ])
            total_areas.append(total_area)
        
        # Конвертируем numpy типы в Python типы
        stats['avg_total_contact_area'] = float(np.mean(total_areas))
        stats['max_total_contact_area'] = float(np.max(total_areas))
        stats['min_total_contact_area'] = float(np.min(total_areas))
        
        # Статистика по каждой лапе
        for paw in ['lf', 'rf', 'lb', 'rb']:
            paw_stats = {}
            
            # Площадь контакта
            area_col = f'{paw}_area_mm2'
            if area_col in df.columns:
                areas = df[area_col]
                paw_stats['avg_area'] = float(areas.mean())
                paw_stats['max_area'] = float(areas.max())
                paw_stats['min_area'] = float(areas[areas > 0].min()) if any(areas > 0) else 0.0
                paw_stats['std_area'] = float(areas.std())
                
            # Длина
            length_col = f'{paw}_length_mm'
            if length_col in df.columns:
                lengths = df[length_col]
                lengths_valid = lengths[lengths > 0]
                if len(lengths_valid) > 0:
                    paw_stats['avg_length'] = float(lengths_valid.mean())
                    paw_stats['std_length'] = float(lengths_valid.std())
                else:
                    paw_stats['avg_length'] = 0.0
                    paw_stats['std_length'] = 0.0
                    
            # Ширина
            if paw.endswith('b'):
                width_col = f'{paw}_width_1_5_mm'
            else:
                width_col = f'{paw}_width_mm'
                
            if width_col in df.columns:
                widths = df[width_col]
                widths_valid = widths[widths > 0]
                if len(widths_valid) > 0:
                    paw_stats['avg_width'] = float(widths_valid.mean())
                    paw_stats['std_width'] = float(widths_valid.std())
                else:
                    paw_stats['avg_width'] = 0.0
                    paw_stats['std_width'] = 0.0
                    
            stats[f'{paw}_stats'] = paw_stats
            
        return stats
        
    def _create_visualizations(self, df, output_dir):
        """Создание визуализаций результатов"""
        import matplotlib.pyplot as plt
        plt.style.use('dark_background')
        
        # 1. График площадей контакта
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Площадь контакта лап во времени', fontsize=16)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_titles = {
            'lf': 'Левая передняя',
            'rf': 'Правая передняя',
            'lb': 'Левая задняя',
            'rb': 'Правая задняя'
        }
        
        for idx, (ax, paw) in enumerate(zip(axes.flat, paw_names)):
            area_col = f'{paw}_area_mm2'
            if area_col in df.columns:
                ax.plot(df.index, df[area_col], color='orange', linewidth=1)
                ax.fill_between(df.index, 0, df[area_col], alpha=0.3, color='orange')
                
            ax.set_title(paw_titles[paw])
            ax.set_xlabel('Кадр')
            ax.set_ylabel('Площадь (мм²)')
            ax.grid(True, alpha=0.3)
            
        plt.tight_layout()
        plt.savefig(output_dir / 'contact_areas.png', dpi=150)
        plt.close()
        
        # 2. График морфометрических параметров
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Морфометрические параметры лап', fontsize=16)
        
        for idx, (ax, paw) in enumerate(zip(axes.flat, paw_names)):
            length_col = f'{paw}_length_mm'
            
            if length_col in df.columns:
                # Фильтруем нулевые значения для лучшей визуализации
                valid_data = df[df[length_col] > 0]
                
                if len(valid_data) > 0:
                    ax.scatter(valid_data.index, valid_data[length_col], 
                             alpha=0.5, s=10, color='cyan', label='Длина')
                    
                    # Добавляем скользящее среднее
                    if len(valid_data) > 20:
                        window = min(50, len(valid_data) // 10)
                        rolling_mean = valid_data[length_col].rolling(window=window).mean()
                        ax.plot(valid_data.index, rolling_mean, 
                               color='cyan', linewidth=2, label='Среднее')
                        
            # Для задних лап добавляем ширину
            if paw.endswith('b'):
                width_col = f'{paw}_width_1_5_mm'
                if width_col in df.columns:
                    valid_data = df[df[width_col] > 0]
                    if len(valid_data) > 0:
                        ax2 = ax.twinx()
                        ax2.scatter(valid_data.index, valid_data[width_col], 
                                  alpha=0.5, s=10, color='magenta', label='Ширина')
                        ax2.set_ylabel('Ширина (мм)', color='magenta')
                        ax2.tick_params(axis='y', labelcolor='magenta')
                        
            ax.set_title(paw_titles[paw])
            ax.set_xlabel('Кадр')
            ax.set_ylabel('Длина (мм)', color='cyan')
            ax.tick_params(axis='y', labelcolor='cyan')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
        plt.tight_layout()
        plt.savefig(output_dir / 'morphometric_params.png', dpi=150)
        plt.close()
        
        # 3. Сводная статистика в виде boxplot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Boxplot площадей
        area_data = []
        area_labels = []
        for paw in paw_names:
            col = f'{paw}_area_mm2'
            if col in df.columns:
                data = df[col][df[col] > 0]
                if len(data) > 0:
                    area_data.append(data)
                    area_labels.append(paw_titles[paw])
                    
        if area_data:
            bp1 = ax1.boxplot(area_data, labels=area_labels, patch_artist=True)
            for patch in bp1['boxes']:
                patch.set_facecolor('orange')
                patch.set_alpha(0.7)
            ax1.set_ylabel('Площадь контакта (мм²)')
            ax1.set_title('Распределение площадей контакта')
            ax1.grid(True, alpha=0.3)
            
        # Boxplot длин
        length_data = []
        length_labels = []
        for paw in paw_names:
            col = f'{paw}_length_mm'
            if col in df.columns:
                data = df[col][df[col] > 0]
                if len(data) > 0:
                    length_data.append(data)
                    length_labels.append(paw_titles[paw])
                    
        if length_data:
            bp2 = ax2.boxplot(length_data, labels=length_labels, patch_artist=True)
            for patch in bp2['boxes']:
                patch.set_facecolor('cyan')
                patch.set_alpha(0.7)
            ax2.set_ylabel('Длина лапы (мм)')
            ax2.set_title('Распределение длин лап')
            ax2.grid(True, alpha=0.3)
            
        plt.tight_layout()
        plt.savefig(output_dir / 'statistics_boxplot.png', dpi=150)
        plt.close()
        
        print(f"Визуализации сохранены в {output_dir}")