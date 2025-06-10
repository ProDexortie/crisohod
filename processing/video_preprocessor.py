"""
processing/video_preprocessor.py
Модуль для предобработки видео (калибровка камеры, коррекция искажений)
"""

import cv2
import numpy as np
import json
from pathlib import Path


class VideoPreprocessor:
    """Предобработчик видео с калибровкой камеры"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        # Используем абсолютный путь
        self.calibration_file = Path(config_manager.get_absolute_path('calibration_file', 'camera_calibration.json'))
        self.calibration_data = None
        self.camera_matrix = None
        self.dist_coeffs = None
        self.pixel_to_mm = None
        
        # Загружаем калибровку если есть
        if self.calibration_file.exists():
            self.load_calibration()
            
    def load_calibration(self):
        """Загрузка параметров калибровки"""
        with open(self.calibration_file, 'r') as f:
            self.calibration_data = json.load(f)
            
        self.camera_matrix = np.array(self.calibration_data['camera_matrix'])
        self.dist_coeffs = np.array(self.calibration_data['distortion_coefficients'])
        self.pixel_to_mm = self.calibration_data.get('pixel_to_mm_ratio', None)
        
        print(f"Калибровка загружена: {self.calibration_file}")
        
    def calibrate_from_images(self, calibration_images_dir, square_size_mm=25.0, pattern_size=(9, 6)):
        """Выполнить калибровку по изображениям"""
        from ..camera_calibration import CameraCalibrator
        
        calibrator = CameraCalibrator(square_size_mm, pattern_size)
        
        # Находим изображения
        images_path = Path(calibration_images_dir)
        image_files = list(images_path.glob('*.jpg')) + list(images_path.glob('*.png'))
        
        if not image_files:
            raise ValueError(f"Не найдены калибровочные изображения в {calibration_images_dir}")
            
        # Выполняем калибровку
        successful_images, errors = calibrator.calibrate_from_images([str(f) for f in image_files])
        
        # Сохраняем
        calibrator.save_calibration(self.calibration_file)
        
        # Загружаем новую калибровку
        self.load_calibration()
        
        # Вычисляем pixel_to_mm
        if successful_images:
            test_img = cv2.imread(successful_images[0])
            undistorted = calibrator.undistort_image(test_img)
            self.pixel_to_mm = calibrator.calculate_pixel_to_mm_ratio(undistorted)
            
            # Обновляем файл калибровки
            self.calibration_data['pixel_to_mm_ratio'] = self.pixel_to_mm
            with open(self.calibration_file, 'w') as f:
                json.dump(self.calibration_data, f, indent=2)
                
        return len(successful_images), np.mean(errors)
        
    def process_video(self, input_video_path, output_video_path=None):
        """
        Обработка видео с применением калибровки
        
        Args:
            input_video_path: путь к исходному видео
            output_video_path: путь для сохранения обработанного видео
            
        Returns:
            путь к обработанному видео
        """
        input_path = Path(input_video_path)
        
        if output_video_path is None:
            output_video_path = input_path.parent / f"{input_path.stem}_calibrated{input_path.suffix}"
        else:
            output_video_path = Path(output_video_path)
            
        # Если калибровка не загружена, просто копируем видео
        if self.camera_matrix is None:
            print("Калибровка не найдена, используется исходное видео")
            if input_path != output_video_path:
                import shutil
                shutil.copy(input_path, output_video_path)
            return str(output_video_path)
            
        # Проверяем, не обработано ли уже
        if output_video_path.exists() and not self.config_manager.get('force_reprocess', False):
            print(f"Видео уже обработано: {output_video_path}")
            return str(output_video_path)
            
        print(f"Применение калибровки к видео: {input_path}")
        
        # Открываем видео
        cap = cv2.VideoCapture(str(input_path))
        
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {input_path}")
            
        # Получаем параметры видео
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Создаем writer для выходного видео
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))
        
        # Создаем карты для быстрого undistort
        map1, map2 = cv2.initUndistortRectifyMap(
            self.camera_matrix, self.dist_coeffs, None,
            self.camera_matrix, (width, height), cv2.CV_32FC1
        )
        
        # Обрабатываем видео
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Применяем undistort
            undistorted_frame = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)
            
            # Опционально: добавляем информацию о калибровке
            if self.config_manager.get('show_calibration_info', False):
                self._add_calibration_info(undistorted_frame)
                
            # Записываем кадр
            out.write(undistorted_frame)
            
            frame_count += 1
            
            # Показываем прогресс
            if frame_count % 100 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Обработано: {progress:.1f}%")
                
        # Освобождаем ресурсы
        cap.release()
        out.release()
        
        print(f"Обработка завершена: {output_video_path}")
        
        # Сохраняем информацию о pixel_to_mm
        if self.pixel_to_mm:
            info_file = output_video_path.with_suffix('.cal')
            with open(info_file, 'w') as f:
                json.dump({
                    'pixel_to_mm': self.pixel_to_mm,
                    'calibration_file': self.calibration_file
                }, f)
                
        return str(output_video_path)
        
    def _add_calibration_info(self, frame):
        """Добавление информации о калибровке на кадр"""
        if self.pixel_to_mm:
            text = f"Cal: {self.pixel_to_mm:.4f} mm/px"
            cv2.putText(frame, text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                       
    def process_image(self, image):
        """Применение калибровки к одному изображению"""
        if self.camera_matrix is None:
            return image
            
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
        
    def get_pixel_to_mm_ratio(self):
        """Получение коэффициента преобразования пикселей в мм"""
        if self.pixel_to_mm is not None:
            return self.pixel_to_mm
            
        # Если не вычислен, используем приблизительное значение
        # основанное на типичных параметрах камеры
        if self.camera_matrix is not None:
            # Фокусное расстояние в пикселях
            fx = self.camera_matrix[0, 0]
            
            # Приблизительная оценка для типичной установки
            # Предполагаем расстояние до объекта ~30 см
            # и типичный размер сенсора
            estimated_ratio = 0.1  # 0.1 мм/пиксель
            
            print(f"Используется оценочный коэффициент: {estimated_ratio} мм/пиксель")
            return estimated_ratio
        else:
            # Значение по умолчанию
            default_ratio = 0.1
            print(f"Используется коэффициент по умолчанию: {default_ratio} мм/пиксель")
            return default_ratio
            
    def create_calibration_report(self, output_path):
        """Создание отчета о калибровке"""
        if self.calibration_data is None:
            print("Калибровка не загружена")
            return
            
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('Отчет о калибровке камеры', fontsize=16)
        
        # 1. Параметры камеры
        ax = axes[0, 0]
        ax.axis('off')
        
        info_text = "Параметры камеры:\n\n"
        info_text += f"Размер изображения: {self.calibration_data.get('image_size', 'N/A')}\n"
        info_text += f"Ошибка калибровки: {self.calibration_data.get('calibration_error', 'N/A'):.3f}\n"
        info_text += f"Размер клетки: {self.calibration_data.get('square_size_mm', 'N/A')} мм\n"
        info_text += f"Размер паттерна: {self.calibration_data.get('pattern_size', 'N/A')}\n"
        
        if self.pixel_to_mm:
            info_text += f"\nКоэффициент: {self.pixel_to_mm:.4f} мм/пиксель\n"
            info_text += f"1 см = {10/self.pixel_to_mm:.1f} пикселей"
            
        ax.text(0.1, 0.9, info_text, transform=ax.transAxes,
               fontsize=12, verticalalignment='top')
               
        # 2. Матрица камеры
        ax = axes[0, 1]
        ax.axis('off')
        
        matrix_text = "Матрица камеры:\n\n"
        if self.camera_matrix is not None:
            for i in range(3):
                row = "  ".join([f"{self.camera_matrix[i,j]:8.2f}" for j in range(3)])
                matrix_text += f"{row}\n"
                
        ax.text(0.1, 0.9, matrix_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top', family='monospace')
               
        # 3. Коэффициенты искажения
        ax = axes[1, 0]
        ax.axis('off')
        
        dist_text = "Коэффициенты искажения:\n\n"
        if self.dist_coeffs is not None:
            labels = ['k1', 'k2', 'p1', 'p2', 'k3']
            for i, (label, coeff) in enumerate(zip(labels, self.dist_coeffs)):
                dist_text += f"{label}: {coeff:10.6f}\n"
                
        ax.text(0.1, 0.9, dist_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top', family='monospace')
               
        # 4. Визуализация искажений
        ax = axes[1, 1]
        
        # Создаем сетку для визуализации
        if self.calibration_data.get('image_size'):
            w, h = self.calibration_data['image_size']
            
            # Создаем сетку точек
            nx, ny = 20, 15
            x = np.linspace(0, w, nx)
            y = np.linspace(0, h, ny)
            
            # Рисуем исходную сетку
            for i in range(nx):
                ax.plot([x[i], x[i]], [0, h], 'b-', alpha=0.3, linewidth=0.5)
            for i in range(ny):
                ax.plot([0, w], [y[i], y[i]], 'b-', alpha=0.3, linewidth=0.5)
                
            # Применяем искажения и рисуем искаженную сетку
            if self.camera_matrix is not None and self.dist_coeffs is not None:
                # Создаем точки сетки
                grid_points = []
                for yi in y:
                    for xi in x:
                        grid_points.append([xi, yi])
                        
                grid_points = np.array(grid_points, dtype=np.float32)
                
                # Применяем искажения
                distorted = cv2.projectPoints(
                    grid_points.reshape(-1, 1, 3),
                    np.zeros(3), np.zeros(3),
                    self.camera_matrix, self.dist_coeffs
                )[0].reshape(-1, 2)
                
                # Рисуем искаженные линии
                for i in range(ny):
                    row_points = distorted[i*nx:(i+1)*nx]
                    ax.plot(row_points[:, 0], row_points[:, 1], 'r-', alpha=0.5)
                    
                for i in range(nx):
                    col_points = distorted[i::nx]
                    ax.plot(col_points[:, 0], col_points[:, 1], 'r-', alpha=0.5)
                    
            ax.set_xlim(0, w)
            ax.set_ylim(h, 0)
            ax.set_aspect('equal')
            ax.set_title('Визуализация искажений')
            ax.set_xlabel('X (пиксели)')
            ax.set_ylabel('Y (пиксели)')
            
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Отчет о калибровке сохранен: {output_path}")