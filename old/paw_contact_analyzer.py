import cv2
import numpy as np
import pandas as pd
import os
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import json

class PawContactAnalyzer:
    def __init__(self, config_path='config.yaml'):
        """
        Инициализация анализатора контактных пятен лап.
        
        Args:
            config_path: путь к файлу конфигурации DeepLabCut
        """
        self.config_path = config_path
        self.bodyparts = self._load_bodyparts()
        self.paw_groups = self._define_paw_groups()
        self.results = []
        
    def _load_bodyparts(self):
        """Загрузка списка частей тела из конфигурации"""
        import yaml
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config['bodyparts']
    
    def _define_paw_groups(self):
        """Определение групп точек для каждой лапы"""
        paw_groups = {
            'lf': [],  # левая передняя
            'rf': [],  # правая передняя
            'lb': [],  # левая задняя
            'rb': []   # правая задняя
        }
        
        for bodypart in self.bodyparts:
            for paw_name in paw_groups.keys():
                if bodypart.startswith(paw_name + '_'):
                    paw_groups[paw_name].append(bodypart)
        
        return paw_groups
    
    def load_deeplabcut_csv(self, csv_path):
        """
        Загрузка CSV файла с результатами DeepLabCut.
        
        Args:
            csv_path: путь к CSV файлу
            
        Returns:
            pandas DataFrame с координатами
        """
        # DeepLabCut CSV имеет многоуровневые заголовки:
        # Уровень 0: scorer (имя модели)
        # Уровень 1: bodyparts (части тела)
        # Уровень 2: coords (x, y, likelihood)
        df = pd.read_csv(csv_path, header=[0, 1, 2], index_col=0)
        return df
    
    def get_paw_bbox(self, df, frame_idx, paw_name, likelihood_threshold=0.6):
        """
        Получение ограничивающего прямоугольника для лапы.
        
        Args:
            df: DataFrame с координатами
            frame_idx: индекс кадра
            paw_name: название лапы ('lf', 'rf', 'lb', 'rb')
            likelihood_threshold: порог достоверности
            
        Returns:
            (x_min, y_min, x_max, y_max) или None
        """
        paw_points = self.paw_groups[paw_name]
        valid_points = []
        
        # Получаем имя scorer из первого уровня колонок
        scorer = df.columns.levels[0][0]
        
        for point in paw_points:
            try:
                x = df.loc[frame_idx, (scorer, point, 'x')]
                y = df.loc[frame_idx, (scorer, point, 'y')]
                likelihood = df.loc[frame_idx, (scorer, point, 'likelihood')]
                
                if likelihood > likelihood_threshold:
                    valid_points.append((x, y))
            except KeyError:
                continue
        
        if len(valid_points) < 3:  # Нужно минимум 3 точки для надежного bbox
            return None
        
        valid_points = np.array(valid_points)
        x_min, y_min = valid_points.min(axis=0)
        x_max, y_max = valid_points.max(axis=0)
        
        # Добавляем небольшой отступ
        padding = 10
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = x_max + padding
        y_max = y_max + padding
        
        return int(x_min), int(y_min), int(x_max), int(y_max)
    
    def analyze_contact_area(self, image, bbox, threshold_value=None):
        """
        Анализ площади контакта в заданной области.
        
        Args:
            image: изображение (кадр видео)
            bbox: ограничивающий прямоугольник (x_min, y_min, x_max, y_max)
            threshold_value: пороговое значение для бинаризации (если None, используется Otsu)
            
        Returns:
            площадь контакта в пикселях, обработанное изображение ROI
        """
        if bbox is None:
            return 0, None
        
        x_min, y_min, x_max, y_max = bbox
        
        # Вырезаем область интереса
        roi = image[y_min:y_max, x_min:x_max]
        
        if roi.size == 0:
            return 0, None
        
        # Преобразуем в градации серого
        if len(roi.shape) == 3:
            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray_roi = roi.copy()
        
        # Применяем размытие для уменьшения шума
        blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
        
        # Бинаризация
        if threshold_value is None:
            # Используем адаптивный порог или метод Otsu
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY)
        
        # Морфологические операции для очистки
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Подсчет белых пикселей (контактная область)
        contact_area = np.sum(binary == 255)
        
        return contact_area, binary
    
    def process_video(self, video_path, csv_path, output_path=None, 
                     start_frame=0, end_frame=None, threshold_value=None):
        """
        Обработка видео с анализом контактных областей.
        
        Args:
            video_path: путь к видео файлу
            csv_path: путь к CSV файлу с координатами DeepLabCut
            output_path: путь для сохранения аннотированного видео
            start_frame: начальный кадр
            end_frame: конечный кадр
            threshold_value: пороговое значение для бинаризации
        """
        # Загружаем данные DeepLabCut
        df = self.load_deeplabcut_csv(csv_path)
        
        # Открываем видео
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Настройка записи видео
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Переход к начальному кадру
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        frame_idx = start_frame
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if end_frame is None:
            end_frame = total_frames
        
        print(f"Обработка видео: {start_frame} - {end_frame} кадров")
        
        while frame_idx < end_frame:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Создаем копию для аннотаций
            annotated_frame = frame.copy()
            
            # Анализируем каждую лапу
            frame_results = {'frame': frame_idx}
            
            for paw_name in self.paw_groups.keys():
                bbox = self.get_paw_bbox(df, frame_idx, paw_name)
                
                if bbox is not None:
                    contact_area, binary_roi = self.analyze_contact_area(frame, bbox, threshold_value)
                    frame_results[f'{paw_name}_area'] = contact_area
                    
                    # Рисуем bbox и информацию на кадре
                    x_min, y_min, x_max, y_max = bbox
                    color = self._get_paw_color(paw_name)
                    cv2.rectangle(annotated_frame, (x_min, y_min), (x_max, y_max), color, 2)
                    
                    # Добавляем текст с площадью
                    text = f"{paw_name}: {contact_area} px"
                    cv2.putText(annotated_frame, text, (x_min, y_min - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    
                    # Опционально: показываем бинарное изображение в углу
                    if binary_roi is not None and binary_roi.size > 0:
                        # Масштабируем для отображения
                        display_size = 50
                        aspect = binary_roi.shape[1] / binary_roi.shape[0]
                        display_w = int(display_size * aspect)
                        display_h = display_size
                        
                        binary_display = cv2.resize(binary_roi, (display_w, display_h))
                        # Конвертируем в цветное для наложения
                        binary_color = cv2.cvtColor(binary_display, cv2.COLOR_GRAY2BGR)
                        
                        # Позиция для отображения миниатюры
                        y_offset = 10 + list(self.paw_groups.keys()).index(paw_name) * (display_h + 10)
                        annotated_frame[y_offset:y_offset+display_h, 10:10+display_w] = binary_color
                else:
                    frame_results[f'{paw_name}_area'] = 0
            
            # Рисуем скелет
            self._draw_skeleton(annotated_frame, df, frame_idx)
            
            # Добавляем информацию о кадре
            cv2.putText(annotated_frame, f"Frame: {frame_idx}", (width - 150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Сохраняем результаты
            self.results.append(frame_results)
            
            # Записываем кадр
            if output_path:
                out.write(annotated_frame)
            
            # Показываем прогресс
            if frame_idx % 100 == 0:
                print(f"Обработано {frame_idx}/{end_frame} кадров")
            
            frame_idx += 1
        
        # Освобождаем ресурсы
        cap.release()
        if output_path:
            out.release()
        
        print("Обработка завершена!")
        
    def _get_paw_color(self, paw_name):
        """Получение цвета для визуализации лапы"""
        colors = {
            'lf': (255, 0, 0),    # Красный
            'rf': (0, 255, 0),    # Зеленый
            'lb': (0, 0, 255),    # Синий
            'rb': (255, 255, 0)   # Желтый
        }
        return colors.get(paw_name, (255, 255, 255))
    
    def _draw_skeleton(self, frame, df, frame_idx, likelihood_threshold=0.6):
        """Рисование скелета на кадре"""
        # Загружаем конфигурацию скелета
        import yaml
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        skeleton = config.get('skeleton', [])
        scorer = df.columns.levels[0][0]
        
        # Рисуем соединения
        for connection in skeleton:
            point1, point2 = connection
            try:
                x1 = df.loc[frame_idx, (scorer, point1, 'x')]
                y1 = df.loc[frame_idx, (scorer, point1, 'y')]
                l1 = df.loc[frame_idx, (scorer, point1, 'likelihood')]
                
                x2 = df.loc[frame_idx, (scorer, point2, 'x')]
                y2 = df.loc[frame_idx, (scorer, point2, 'y')]
                l2 = df.loc[frame_idx, (scorer, point2, 'likelihood')]
                
                if l1 > likelihood_threshold and l2 > likelihood_threshold:
                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
                            (0, 255, 255), 1)
            except KeyError:
                continue
        
        # Рисуем точки
        for bodypart in self.bodyparts:
            try:
                x = df.loc[frame_idx, (scorer, bodypart, 'x')]
                y = df.loc[frame_idx, (scorer, bodypart, 'y')]
                likelihood = df.loc[frame_idx, (scorer, bodypart, 'likelihood')]
                
                if likelihood > likelihood_threshold:
                    # Определяем цвет точки по принадлежности к лапе
                    color = (255, 255, 255)
                    for paw_name, paw_points in self.paw_groups.items():
                        if bodypart in paw_points:
                            color = self._get_paw_color(paw_name)
                            break
                    
                    cv2.circle(frame, (int(x), int(y)), 3, color, -1)
            except KeyError:
                continue
    
    def save_results(self, output_path):
        """Сохранение результатов анализа в CSV"""
        df_results = pd.DataFrame(self.results)
        df_results.to_csv(output_path, index=False)
        print(f"Результаты сохранены в {output_path}")
    
    def plot_results(self, save_path=None):
        """Визуализация результатов анализа"""
        df_results = pd.DataFrame(self.results)
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Анализ контактных областей лап', fontsize=16)
        
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_titles = {
            'lf': 'Левая передняя',
            'rf': 'Правая передняя', 
            'lb': 'Левая задняя',
            'rb': 'Правая задняя'
        }
        
        for idx, (ax, paw_name) in enumerate(zip(axes.flat, paw_names)):
            column_name = f'{paw_name}_area'
            if column_name in df_results.columns:
                ax.plot(df_results['frame'], df_results[column_name])
                ax.set_title(paw_titles[paw_name])
                ax.set_xlabel('Кадр')
                ax.set_ylabel('Площадь контакта (пиксели)')
                ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
        plt.show()


# Пример использования
if __name__ == "__main__":
    # Создаем анализатор
    analyzer = PawContactAnalyzer('config.yaml')
    
    # Обрабатываем видео
    video_path = "path/to/your/video.mp4"
    csv_path = "path/to/deeplabcut/results.csv"
    output_video = "annotated_output.mp4"
    
    # Запускаем анализ
    analyzer.process_video(
        video_path=video_path,
        csv_path=csv_path,
        output_path=output_video,
        start_frame=0,
        end_frame=1000,  # или None для обработки всего видео
        threshold_value=None  # None для автоматического определения порога
    )
    
    # Сохраняем результаты
    analyzer.save_results("contact_areas_results.csv")
    
    # Строим графики
    analyzer.plot_results("contact_areas_plot.png")