#!/usr/bin/env python3
"""
Модуль калибровки камеры для системы анализа контактных областей лап.
Использует шахматную доску для:
1. Исправления искажений объектива
2. Калибровки размеров (пиксели -> мм)
"""

import cv2
import numpy as np
import glob
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt


class CameraCalibrator:
    def __init__(self, square_size_mm=25.0, pattern_size=(9, 6)):
        """
        Инициализация калибратора камеры.
        
        Args:
            square_size_mm: размер одной клетки шахматной доски в мм
            pattern_size: количество внутренних углов (ширина, высота)
                         Например, для доски 10x7 клеток будет (9, 6) углов
        """
        self.square_size = square_size_mm
        self.pattern_size = pattern_size
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_error = None
        self.image_size = None
        
    def calibrate_from_images(self, image_paths):
        """
        Калибровка камеры по набору изображений с шахматной доской.
        
        Args:
            image_paths: список путей к изображениям или паттерн glob (например, "calib/*.jpg")
        """
        # Если передан паттерн, получаем список файлов
        if isinstance(image_paths, str):
            image_paths = glob.glob(image_paths)
        
        if len(image_paths) == 0:
            raise ValueError("Не найдено изображений для калибровки")
        
        print(f"Найдено {len(image_paths)} изображений для калибровки")
        
        # Подготовка точек объекта (координаты углов в системе координат доски)
        objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
        objp *= self.square_size
        
        # Массивы для хранения точек объекта и изображения
        objpoints = []  # 3D точки в реальном мире
        imgpoints = []  # 2D точки на изображении
        
        successful_images = []
        
        for idx, fname in enumerate(image_paths):
            img = cv2.imread(fname)
            if img is None:
                print(f"Не удалось загрузить изображение: {fname}")
                continue
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Запоминаем размер изображения
            if self.image_size is None:
                self.image_size = gray.shape[::-1]
            
            # Находим углы шахматной доски
            ret, corners = cv2.findChessboardCorners(gray, self.pattern_size, None)
            
            if ret:
                # Уточняем положение углов
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                
                objpoints.append(objp)
                imgpoints.append(corners_refined)
                successful_images.append(fname)
                
                # Визуализация (опционально)
                img_vis = cv2.drawChessboardCorners(img, self.pattern_size, corners_refined, ret)
                
                # Сохраняем визуализацию
                output_name = f"calibration_detected_{idx}.jpg"
                cv2.imwrite(output_name, img_vis)
                print(f"✓ Обработано изображение {idx+1}/{len(image_paths)}: {os.path.basename(fname)}")
            else:
                print(f"✗ Не найдена доска на изображении {idx+1}: {os.path.basename(fname)}")
        
        if len(objpoints) < 3:
            raise ValueError(f"Недостаточно успешных изображений для калибровки. Найдено только {len(objpoints)}")
        
        print(f"\nКалибровка по {len(objpoints)} изображениям...")
        
        # Выполняем калибровку камеры
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, self.image_size, None, None
        )
        
        self.camera_matrix = mtx
        self.dist_coeffs = dist
        self.calibration_error = ret
        
        print(f"Калибровка завершена. Средняя ошибка репроекции: {ret:.3f} пикселей")
        
        # Вычисляем ошибку для каждого изображения
        total_error = 0
        errors = []
        for i in range(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            errors.append(error)
            total_error += error
        
        mean_error = total_error / len(objpoints)
        print(f"Средняя ошибка по всем изображениям: {mean_error:.3f} пикселей")
        
        return successful_images, errors
    
    def save_calibration(self, filename="camera_calibration.json"):
        """Сохранение параметров калибровки в файл."""
        if self.camera_matrix is None:
            raise ValueError("Сначала выполните калибровку")
        
        calibration_data = {
            "camera_matrix": self.camera_matrix.tolist(),
            "distortion_coefficients": self.dist_coeffs.tolist(),
            "calibration_error": float(self.calibration_error),
            "image_size": self.image_size,
            "square_size_mm": self.square_size,
            "pattern_size": self.pattern_size
        }
        
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)
        
        print(f"Калибровка сохранена в {filename}")
    
    def load_calibration(self, filename="camera_calibration.json"):
        """Загрузка параметров калибровки из файла."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.camera_matrix = np.array(data["camera_matrix"])
        self.dist_coeffs = np.array(data["distortion_coefficients"])
        self.calibration_error = data["calibration_error"]
        self.image_size = tuple(data["image_size"])
        self.square_size = data["square_size_mm"]
        self.pattern_size = tuple(data["pattern_size"])
        
        print(f"Калибровка загружена из {filename}")
    
    def undistort_image(self, image):
        """Исправление искажений на изображении."""
        if self.camera_matrix is None:
            raise ValueError("Сначала выполните калибровку или загрузите параметры")
        
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
    
    def get_optimal_camera_matrix(self, alpha=1):
        """
        Получение оптимальной матрицы камеры.
        
        Args:
            alpha: 0 - обрезать черные области, 1 - сохранить все пиксели
        """
        h, w = self.image_size[::-1]
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), alpha, (w, h)
        )
        return new_camera_matrix, roi
    
    def calculate_pixel_to_mm_ratio(self, undistorted_image=None):
        """
        Расчет коэффициента преобразования пикселей в миллиметры.
        
        Returns:
            pixel_to_mm: коэффициент мм/пиксель
        """
        if undistorted_image is not None:
            # Находим шахматную доску на исправленном изображении
            gray = cv2.cvtColor(undistorted_image, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, self.pattern_size, None)
            
            if ret:
                # Измеряем расстояние между соседними углами
                distances = []
                for i in range(len(corners) - 1):
                    if (i + 1) % self.pattern_size[0] != 0:  # Не на краю строки
                        dist = np.linalg.norm(corners[i] - corners[i + 1])
                        distances.append(dist)
                
                avg_pixel_distance = np.mean(distances)
                pixel_to_mm = self.square_size / avg_pixel_distance
                
                print(f"Средний размер клетки: {avg_pixel_distance:.2f} пикселей")
                print(f"Коэффициент: {pixel_to_mm:.4f} мм/пиксель")
                
                return pixel_to_mm
        
        # Приблизительный расчет по фокусному расстоянию
        if self.camera_matrix is not None:
            fx = self.camera_matrix[0, 0]
            # Приблизительная оценка (требует знания расстояния до объекта)
            # Это очень грубая оценка!
            pixel_to_mm = 0.1  # Типичное значение, требует уточнения
            print(f"Используется приблизительный коэффициент: {pixel_to_mm} мм/пиксель")
            print("Для точного значения используйте calculate_pixel_to_mm_ratio с изображением доски")
            return pixel_to_mm
    
    def create_undistortion_maps(self):
        """Создание карт для быстрого исправления искажений."""
        h, w = self.image_size[::-1]
        new_camera_matrix, roi = self.get_optimal_camera_matrix()
        
        mapx, mapy = cv2.initUndistortRectifyMap(
            self.camera_matrix, self.dist_coeffs, None, 
            new_camera_matrix, (w, h), cv2.CV_32FC1
        )
        
        return mapx, mapy, roi
    
    def visualize_distortion(self, sample_image_path):
        """Визуализация эффекта исправления искажений."""
        img = cv2.imread(sample_image_path)
        if img is None:
            raise ValueError(f"Не удалось загрузить изображение: {sample_image_path}")
        
        # Исправляем искажения
        undistorted = self.undistort_image(img)
        
        # Создаем визуализацию
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        ax1.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax1.set_title('Исходное изображение')
        ax1.axis('off')
        
        ax2.imshow(cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB))
        ax2.set_title('Исправленное изображение')
        ax2.axis('off')
        
        plt.tight_layout()
        plt.savefig('distortion_comparison.png')
        plt.show()
        
        # Вычисляем pixel_to_mm для исправленного изображения
        pixel_to_mm = self.calculate_pixel_to_mm_ratio(undistorted)
        
        return undistorted, pixel_to_mm


# Интеграция с анализатором контактных областей
class CalibratedPawAnalyzer:
    """
    Расширенный анализатор с поддержкой калибровки камеры.
    """
    
    def __init__(self, config_path='config.yaml', calibration_file='camera_calibration.json'):
        # Импортируем базовый анализатор
        from paw_contact_analyzer import PawContactAnalyzer
        
        self.base_analyzer = PawContactAnalyzer(config_path)
        self.calibrator = CameraCalibrator()
        
        # Загружаем калибровку если есть
        if os.path.exists(calibration_file):
            self.calibrator.load_calibration(calibration_file)
            self.pixel_to_mm = self.calibrator.calculate_pixel_to_mm_ratio()
        else:
            self.pixel_to_mm = None
            print(f"Файл калибровки {calibration_file} не найден. Результаты будут в пикселях.")
    
    def process_video_calibrated(self, video_path, csv_path, output_path=None, **kwargs):
        """
        Обработка видео с исправлением искажений и переводом в мм.
        """
        import cv2
        import pandas as pd
        
        # Открываем видео
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Создаем временное видео для исправленных кадров
        temp_video = "temp_undistorted.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_temp = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
        
        print("Исправление искажений видео...")
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Исправляем искажения
            if self.calibrator.camera_matrix is not None:
                frame = self.calibrator.undistort_image(frame)
            
            out_temp.write(frame)
            frame_count += 1
            
            if frame_count % 100 == 0:
                print(f"Обработано {frame_count} кадров...")
        
        cap.release()
        out_temp.release()
        
        # Обрабатываем исправленное видео
        print("Анализ контактных областей...")
        self.base_analyzer.process_video(temp_video, csv_path, output_path, **kwargs)
        
        # Удаляем временный файл
        os.remove(temp_video)
        
        # Конвертируем результаты в мм²
        if self.pixel_to_mm is not None:
            df_results = pd.DataFrame(self.base_analyzer.results)
            
            # Конвертируем площади
            for paw in ['lf', 'rf', 'lb', 'rb']:
                col_name = f'{paw}_area'
                if col_name in df_results.columns:
                    # Площадь = пиксели * (мм/пиксель)²
                    df_results[f'{paw}_area_mm2'] = df_results[col_name] * (self.pixel_to_mm ** 2)
            
            # Обновляем результаты
            self.base_analyzer.results = df_results.to_dict('records')
            
            print(f"\nКоэффициент преобразования: {self.pixel_to_mm:.4f} мм/пиксель")
            print("Результаты сохранены в пикселях и мм²")


# Скрипт для выполнения калибровки
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Калибровка камеры для анализа контактных областей')
    parser.add_argument('--images', required=True, help='Путь к изображениям калибровки (поддерживает wildcards, например "calib/*.jpg")')
    parser.add_argument('--square-size', type=float, default=25.0, help='Размер клетки шахматной доски в мм (по умолчанию: 25.0)')
    parser.add_argument('--pattern-size', nargs=2, type=int, default=[9, 6], help='Количество внутренних углов (ширина высота), по умолчанию: 9 6')
    parser.add_argument('--output', default='camera_calibration.json', help='Файл для сохранения калибровки')
    parser.add_argument('--visualize', action='store_true', help='Показать результат исправления искажений')
    
    args = parser.parse_args()
    
    # Создаем калибратор
    calibrator = CameraCalibrator(
        square_size_mm=args.square_size,
        pattern_size=tuple(args.pattern_size)
    )
    
    # Выполняем калибровку
    try:
        successful_images, errors = calibrator.calibrate_from_images(args.images)
        
        # Сохраняем результаты
        calibrator.save_calibration(args.output)
        
        # Визуализация
        if args.visualize and len(successful_images) > 0:
            calibrator.visualize_distortion(successful_images[0])
        
        print("\nКалибровка завершена успешно!")
        print(f"Параметры сохранены в: {args.output}")
        
    except Exception as e:
        print(f"Ошибка при калибровке: {e}")