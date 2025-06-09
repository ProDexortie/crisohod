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
from typing import Optional, Union, Dict, List
import logging

logger = logging.getLogger(__name__)


class DLCProcessor:
    """Процессор для анализа видео с помощью DeepLabCut"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config_path = Path(config_manager.get('config_path', 'config.yaml'))
        self.pytorch_config_path = Path(config_manager.get('pytorch_config_path', 'pytorch_config.yaml'))
        self.snapshot_path = Path(config_manager.get('snapshot_path', 'snapshot-best-110.pt'))
        
        self.model = None
        self.inference = None
        self.config = None
        self.bodyparts = []
        
        # Проверяем и загружаем модель
        self._check_files()
        self._init_model()
        
    def _check_files(self):
        """Проверка наличия необходимых файлов"""
        required_files = {
            'config.yaml': self.config_path,
            'pytorch_config.yaml': self.pytorch_config_path,
            'snapshot': self.snapshot_path
        }
        
        missing_files = []
        for name, path in required_files.items():
            if not path.exists():
                missing_files.append(f"{name}: {path}")
                
        if missing_files:
            raise FileNotFoundError(
                f"Отсутствуют необходимые файлы:\n" + "\n".join(missing_files)
            )
            
    def _init_model(self):
        """Инициализация модели DeepLabCut"""
        try:
            # Пытаемся использовать официальный DeepLabCut PyTorch
            import deeplabcut
            
            # Загружаем конфигурацию проекта
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            
            self.bodyparts = self.config['bodyparts']
            self.skeleton = self.config.get('skeleton', [])
            
            # Используем встроенную функцию analyze_videos
            self._use_official_dlc = True
            logger.info("Используется официальный DeepLabCut")
            
        except ImportError:
            # Используем нашу реализацию
            logger.warning("DeepLabCut не установлен, используется встроенная реализация")
            self._use_official_dlc = False
            self._init_custom_model()
            
    def _init_custom_model(self):
        """Инициализация кастомной модели"""
        from .dlc_model import get_dlc_inference_model, DLCInference
        
        # Загружаем модель
        self.model, model_config = get_dlc_inference_model(
            str(self.pytorch_config_path),
            str(self.snapshot_path)
        )
        
        # Создаем объект для инференса
        device = 'cuda' if self.config_manager.get('use_gpu', True) else 'cpu'
        self.inference = DLCInference(self.model, model_config, device)
        
        # Загружаем конфигурацию
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.bodyparts = self.config['bodyparts']
        self.skeleton = self.config.get('skeleton', [])
        
    def process_video(self, video_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None) -> str:
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
            output_dir.mkdir(exist_ok=True, parents=True)
            
        # Имя выходного файла
        video_name = video_path.stem
        csv_path = output_dir / f"{video_name}_DLC.csv"
        
        # Проверяем, не был ли файл уже обработан
        if csv_path.exists() and not self.config_manager.get('force_reprocess', False):
            logger.info(f"Видео уже обработано: {csv_path}")
            return str(csv_path)
            
        logger.info(f"Обработка видео: {video_path}")
        
        if self._use_official_dlc:
            return self._process_with_official_dlc(video_path, output_dir, csv_path)
        else:
            return self._process_with_custom_model(video_path, output_dir, csv_path)
            
    def _process_with_official_dlc(self, video_path: Path, output_dir: Path, csv_path: Path) -> str:
        """Обработка с использованием официального DeepLabCut"""
        import deeplabcut
        
        try:
            # Создаем временную конфигурацию
            temp_config = self._create_temp_config(video_path)
            
            # Анализируем видео
            deeplabcut.analyze_videos(
                temp_config,
                [str(video_path)],
                shuffle=1,
                save_as_csv=True,
                destfolder=str(output_dir),
                batchsize=self.config_manager.get('batch_size', 8),
                dynamic=(True, 0.5, 10)
            )
            
            # Находим созданный CSV файл
            pattern = f"{video_path.stem}*DLC*.csv"
            csv_files = list(output_dir.glob(pattern))
            
            if csv_files:
                # Переименовываем в наш формат
                csv_files[0].rename(csv_path)
                logger.info(f"Результаты сохранены: {csv_path}")
                return str(csv_path)
            else:
                raise FileNotFoundError("CSV файл не был создан")
                
        except Exception as e:
            logger.error(f"Ошибка при использовании официального DLC: {e}")
            # Fallback на кастомную обработку
            return self._process_with_custom_model(video_path, output_dir, csv_path)
            
    def _process_with_custom_model(self, video_path: Path, output_dir: Path, csv_path: Path) -> str:
        """Обработка с использованием кастомной модели"""
        if self.inference is None:
            self._init_custom_model()
            
        # Открываем видео
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {video_path}")
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        logger.info(f"Видео: {total_frames} кадров, {fps} FPS")
        
        # Обрабатываем видео
        all_results = []
        frame_idx = 0
        batch_frames = []
        batch_indices = []
        batch_size = self.config_manager.get('batch_size', 8)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            batch_frames.append(frame)
            batch_indices.append(frame_idx)
            
            # Обрабатываем батч
            if len(batch_frames) >= batch_size or frame_idx == total_frames - 1:
                batch_results = self.inference.process_video_batch(batch_frames)
                
                for idx, result in zip(batch_indices, batch_results):
                    frame_data = {'frame': idx}
                    
                    for bp_name, bp_data in result.items():
                        frame_data[('DLC_pytorch', bp_name, 'x')] = bp_data['x']
                        frame_data[('DLC_pytorch', bp_name, 'y')] = bp_data['y']
                        frame_data[('DLC_pytorch', bp_name, 'likelihood')] = bp_data['likelihood']
                    
                    all_results.append(frame_data)
                
                batch_frames = []
                batch_indices = []
                
            frame_idx += 1
            
            # Прогресс
            if frame_idx % 100 == 0:
                progress = (frame_idx / total_frames) * 100
                logger.info(f"Обработано: {progress:.1f}%")
                
        cap.release()
        
        # Создаем DataFrame в формате DeepLabCut
        df = pd.DataFrame(all_results)
        df.set_index('frame', inplace=True)
        
        # Сохраняем
        df.to_csv(csv_path)
        logger.info(f"Результаты сохранены: {csv_path}")
        
        return str(csv_path)
        
    def _create_temp_config(self, video_path: Path) -> str:
        """Создание временной конфигурации для анализа"""
        # Копируем основную конфигурацию
        temp_config = self.config.copy()
        
        # Обновляем пути
        project_path = Path.cwd()
        temp_config['project_path'] = str(project_path)
        
        # Обновляем video_sets
        temp_config['video_sets'] = {
            str(video_path): {
                'crop': '0, 1280, 0, 720'  # Используем полный размер
            }
        }
        
        # Путь к модели
        model_path = project_path / 'dlc-models-pytorch' / 'iteration-0' / f"{Path(self.config_path).stem}-trainset95shuffle1"
        model_path.mkdir(parents=True, exist_ok=True)
        
        # Копируем файлы модели
        if self.pytorch_config_path.exists():
            import shutil
            shutil.copy(self.pytorch_config_path, model_path / 'train' / 'pytorch_config.yaml')
        if self.snapshot_path.exists():
            import shutil
            snapshot_dir = model_path / 'train' / 'snapshots'
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.snapshot_path, snapshot_dir / self.snapshot_path.name)
        
        # Сохраняем временную конфигурацию
        temp_config_path = project_path / 'temp_dlc_config.yaml'
        with open(temp_config_path, 'w') as f:
            yaml.dump(temp_config, f)
            
        return str(temp_config_path)
        
    def create_labeled_video(self, video_path: Union[str, Path], csv_path: Union[str, Path], 
                           output_path: Optional[Union[str, Path]] = None) -> str:
        """Создание видео с наложенным скелетом"""
        video_path = Path(video_path)
        csv_path = Path(csv_path)
        
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_labeled.mp4"
        else:
            output_path = Path(output_path)
            
        if self._use_official_dlc:
            try:
                import deeplabcut
                temp_config = self._create_temp_config(video_path)
                
                deeplabcut.create_labeled_video(
                    temp_config,
                    [str(video_path)],
                    destfolder=str(output_path.parent),
                    save_frames=False
                )
                return str(output_path)
            except Exception as e:
                logger.error(f"Ошибка при создании labeled video через DLC: {e}")
                
        # Используем ручной метод (уже реализован в video_player.py)
        logger.info("Создание labeled video будет выполнено через video_player")
        return str(output_path)