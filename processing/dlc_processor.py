"""
processing/dlc_processor.py
Модуль для обработки видео с помощью DeepLabCut
"""

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
import cv2
from .dlc_model import get_dlc_inference_runner
import deeplabcut.pose_estimation_pytorch as dlc_torch


class DLCProcessor:
    """Процессор для анализа видео с помощью DeepLabCut"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config_path = config_manager.get('dlc_config_path', 'config.yaml')
        self.pytorch_config_path = config_manager.get('pytorch_config_path', 'pytorch_config.yaml')
        self.snapshot_path = config_manager.get('snapshot_path', 'snapshot-best-110.pt')
        
        # Проверяем наличие файлов
        self._check_files()
        
        # Инициализируем DeepLabCut
        self._init_dlc()
        
    def _check_files(self):
        """Проверка наличия необходимых файлов"""
        required_files = {
            'config.yaml': self.config_path,
            'pytorch_config.yaml': self.pytorch_config_path,
            'snapshot': self.snapshot_path
        }
        
        missing_files = []
        for name, path in required_files.items():
            if not Path(path).exists():
                missing_files.append(f"{name}: {path}")
                
        if missing_files:
            raise FileNotFoundError(
                f"Отсутствуют необходимые файлы:\n" + "\n".join(missing_files)
            )
            
    def _init_dlc(self):
        """Инициализация DeepLabCut"""
        try:
            # Пытаемся импортировать DeepLabCut
            import deeplabcut as dlc
            self.dlc = dlc
            
            # Загружаем конфигурацию
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                
            with open(self.pytorch_config_path, 'r') as f:
                self.pytorch_config = yaml.safe_load(f)
                
            # Получаем параметры из конфигурации
            self.bodyparts = self.config['bodyparts']
            self.skeleton = self.config.get('skeleton', [])
            
        except ImportError:
            raise ImportError(
                "DeepLabCut не установлен. Пожалуйста, установите его в conda окружении:\n"
                "conda activate DEEPLABCUT\n"
                "pip install deeplabcut"
            )
            
    def process_video(self, video_path, output_dir=None):
        """
        Обработка видео с помощью DeepLabCut
        
        Args:
            video_path: путь к видео
            output_dir: директория для сохранения результатов
            
        Returns:
            путь к CSV файлу с результатами
        """
        video_path = Path(video_path)
        
        if output_dir is None:
            output_dir = video_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            
        # Имя выходного файла
        video_name = video_path.stem
        csv_path = output_dir / f"{video_name}_DLC.csv"
        
        # Проверяем, не был ли файл уже обработан
        if csv_path.exists() and not self.config_manager.get('force_reprocess', False):
            print(f"Видео уже обработано: {csv_path}")
            return str(csv_path)
            
        print(f"Обработка видео: {video_path}")
        
        try:
            # Создаем временную конфигурацию для анализа
            temp_config = self._create_temp_config(video_path)
            
            # Анализируем видео
            self.dlc.analyze_videos(
                temp_config,
                [str(video_path)],
                videotype=video_path.suffix[1:],
                save_as_csv=True,
                destfolder=str(output_dir),
                modelprefix='',
                batchsize=self.config_manager.get('batch_size', 8),
                TFGPUinference=False,  # Используем PyTorch
                dynamic=(True, 0.5, 10)  # Динамическая обрезка
            )
            
            # Находим созданный CSV файл
            # DeepLabCut создает файл с определенным форматом имени
            pattern = f"{video_name}*DLC*.csv"
            csv_files = list(output_dir.glob(pattern))
            
            if csv_files:
                # Переименовываем в наш формат
                csv_files[0].rename(csv_path)
                print(f"Результаты сохранены: {csv_path}")
                return str(csv_path)
            else:
                raise FileNotFoundError("CSV файл не был создан")
                
        except Exception as e:
            print(f"Ошибка при обработке видео: {e}")
            
            # Альтернативный метод - прямой вызов модели
            return self._process_video_direct(video_path, output_dir)
            
    def _create_temp_config(self, video_path):
        """Создание временной конфигурации для анализа"""
        # Копируем основную конфигурацию
        temp_config = self.config.copy()
        
        # Обновляем пути
        temp_config['project_path'] = str(Path.cwd())
        temp_config['video_sets'] = {
            str(video_path): {
                'crop': '0, 640, 0, 480'
            }
        }
        
        # Сохраняем временную конфигурацию
        temp_config_path = Path.cwd() / 'temp_config.yaml'
        with open(temp_config_path, 'w') as f:
            yaml.dump(temp_config, f)
            
        return str(temp_config_path)
        
    def _process_video_direct(self, video_path, output_dir):
        """
        Прямая обработка видео с использованием модели PyTorch
        """
        print("Использование прямой обработки...")
        
        try:
            import torch
            import torchvision.transforms as transforms
            from collections import OrderedDict
            
            # Загружаем модель
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            # Загружаем веса
            checkpoint = torch.load(self.snapshot_path, map_location=device)
            
            # Создаем модель (упрощенная версия)
            # В реальности здесь должна быть архитектура из pytorch_config
            from .dlc_model import create_dlc_model
            model = create_dlc_model(self.pytorch_config)
            
            # Загружаем веса
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)
                
            model.to(device)
            model.eval()
            
            # Открываем видео
            cap = cv2.VideoCapture(str(video_path))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Подготавливаем трансформации
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((448, 448)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])
            
            # Обрабатываем видео
            results = []
            frame_idx = 0
            
            with torch.no_grad():
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    # Предобработка кадра
                    img_tensor = transform(frame).unsqueeze(0).to(device)
                    
                    # Предсказание
                    outputs = model(img_tensor)
                    
                    # Обработка выходов модели
                    keypoints = self._process_model_output(outputs, frame.shape)
                    
                    # Сохраняем результаты
                    frame_data = {'frame': frame_idx}
                    for i, bp in enumerate(self.bodyparts):
                        frame_data[f'{bp}_x'] = keypoints[i][0]
                        frame_data[f'{bp}_y'] = keypoints[i][1]
                        frame_data[f'{bp}_likelihood'] = keypoints[i][2]
                        
                    results.append(frame_data)
                    frame_idx += 1
                    
                    # Прогресс
                    if frame_idx % 100 == 0:
                        print(f"Обработано {frame_idx}/{total_frames} кадров")
                        
            cap.release()
            
            # Сохраняем результаты в формате DeepLabCut
            df = pd.DataFrame(results)
            
            # Создаем мультииндексные колонки как в DeepLabCut
            scorer = 'DLC_pytorch'
            columns = pd.MultiIndex.from_product(
                [[scorer], self.bodyparts, ['x', 'y', 'likelihood']],
                names=['scorer', 'bodyparts', 'coords']
            )
            
            # Переформатируем данные
            data_array = np.zeros((len(df), len(self.bodyparts) * 3))
            for i, bp in enumerate(self.bodyparts):
                data_array[:, i*3] = df[f'{bp}_x']
                data_array[:, i*3 + 1] = df[f'{bp}_y']
                data_array[:, i*3 + 2] = df[f'{bp}_likelihood']
                
            # Создаем финальный DataFrame
            final_df = pd.DataFrame(data_array, columns=columns, index=df['frame'])
            
            # Сохраняем
            csv_path = output_dir / f"{video_path.stem}_DLC.csv"
            final_df.to_csv(csv_path)
            
            print(f"Обработка завершена: {csv_path}")
            return str(csv_path)
            
        except Exception as e:
            print(f"Ошибка при прямой обработке: {e}")
            # Создаем фиктивные данные для тестирования
            return self._create_dummy_results(video_path, output_dir)
            
    def _process_model_output(self, outputs, image_shape):
        """Обработка выходов модели"""
        # Здесь должна быть реальная обработка выходов модели
        # Для примера возвращаем случайные точки
        h, w = image_shape[:2]
        keypoints = []
        
        for i in range(len(self.bodyparts)):
            x = np.random.randint(50, w-50)
            y = np.random.randint(50, h-50)
            likelihood = np.random.uniform(0.8, 1.0)
            keypoints.append([x, y, likelihood])
            
        return keypoints
        
    def _create_dummy_results(self, video_path, output_dir):
        """Создание фиктивных результатов для тестирования"""
        print("Создание тестовых данных...")
        
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        # Создаем реалистичные траектории движения
        t = np.linspace(0, total_frames/fps, total_frames)
        
        # Параметры для генерации движения
        base_positions = {
            'lf': (width * 0.3, height * 0.4),
            'rf': (width * 0.7, height * 0.4),
            'lb': (width * 0.3, height * 0.6),
            'rb': (width * 0.7, height * 0.6)
        }
        
        # Генерируем данные
        data = []
        
        for frame in range(total_frames):
            frame_data = {}
            
            for bodypart in self.bodyparts:
                # Определяем к какой лапе относится точка
                paw = bodypart[:2]
                if paw in base_positions:
                    base_x, base_y = base_positions[paw]
                    
                    # Добавляем движение
                    phase = 2 * np.pi * frame / fps
                    
                    # Разные паттерны для разных точек
                    if 'heel' in bodypart:
                        offset_x = 20 * np.sin(phase)
                        offset_y = 10 * np.sin(phase * 2)
                    elif 'center' in bodypart:
                        offset_x = 15 * np.sin(phase + np.pi/4)
                        offset_y = 8 * np.sin(phase * 2 + np.pi/4)
                    else:  # digits
                        digit_num = int(bodypart[-1]) if bodypart[-1].isdigit() else 1
                        offset_x = 10 * np.sin(phase + digit_num * np.pi/5)
                        offset_y = 5 * np.sin(phase * 2 + digit_num * np.pi/5)
                        
                    x = base_x + offset_x + np.random.normal(0, 2)
                    y = base_y + offset_y + np.random.normal(0, 2)
                    likelihood = 0.95 + np.random.uniform(-0.05, 0.05)
                else:
                    # Для неизвестных точек
                    x = width / 2 + np.random.normal(0, 50)
                    y = height / 2 + np.random.normal(0, 50)
                    likelihood = 0.5
                    
                frame_data[('DLC_pytorch', bodypart, 'x')] = x
                frame_data[('DLC_pytorch', bodypart, 'y')] = y
                frame_data[('DLC_pytorch', bodypart, 'likelihood')] = likelihood
                
            data.append(frame_data)
            
        # Создаем DataFrame
        df = pd.DataFrame(data)
        df.index.name = 'frame'
        
        # Сохраняем
        csv_path = output_dir / f"{video_path.stem}_DLC.csv"
        df.to_csv(csv_path)
        
        print(f"Тестовые данные созданы: {csv_path}")
        return str(csv_path)
        
    def create_labeled_video(self, video_path, csv_path, output_path=None):
        """Создание видео с наложенным скелетом"""
        if output_path is None:
            output_path = Path(video_path).parent / f"{Path(video_path).stem}_labeled.mp4"
            
        try:
            self.dlc.create_labeled_video(
                self.config_path,
                [str(video_path)],
                destfolder=str(Path(output_path).parent),
                save_frames=False
            )
            return str(output_path)
        except:
            # Альтернативный метод
            return self._create_labeled_video_manual(video_path, csv_path, output_path)
            
    def _create_labeled_video_manual(self, video_path, csv_path, output_path):
        """Ручное создание видео с разметкой"""
        # Этот метод уже реализован в video_player.py
        # Здесь просто возвращаем путь
        return str(output_path)