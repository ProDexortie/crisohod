"""
processing/dlc_processor.py
Упрощенный и надежный модуль для обработки видео с помощью DeepLabCut
"""

import os
from pathlib import Path
import yaml
import logging
import deeplabcut # Убедитесь, что deeplabcut установлен: pip install deeplabcut

logger = logging.getLogger(__name__)

class DLCProcessor:
    """Процессор для анализа видео с помощью DeepLabCut"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config_path = Path(config_manager.get('config_path', 'config.yaml'))
        
        self._check_files()
        
        with open(self.config_path, 'r') as f:
            self.dlc_config = yaml.safe_load(f)
            
        self.bodyparts = self.dlc_config.get('bodyparts', [])

    def _check_files(self):
        """Проверка наличия файла конфигурации"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Файл конфигурации DeepLabCut не найден: {self.config_path}")

    def process_video(self, video_path: Path) -> str:
        """
        Обработка видео с помощью официального API DeepLabCut.
        
        Args:
            video_path: Путь к видео для анализа.
            
        Returns:
            Путь к CSV файлу с результатами.
        """
        video_path = Path(video_path)
        output_dir = video_path.parent
        
        logger.info(f"Начало обработки видео: {video_path.name}")
        
        # DeepLabCut сам найдет нужные файлы модели на основе config.yaml
        deeplabcut.analyze_videos(
            config=str(self.config_path),
            videos=[str(video_path)],
            save_as_csv=True,
            destfolder=str(output_dir)
        )
        
        # Находим созданный CSV файл
        # Имя файла обычно: VideoNameDLC_resnet50_ProjectNameDateShuffle1_110000.csv
        pattern = f"{video_path.stem}DLC*.csv"
        csv_files = list(output_dir.glob(pattern))
        
        if not csv_files:
            raise FileNotFoundError(f"DeepLabCut не создал CSV файл для видео {video_path.name}")
            
        # Возвращаем путь к первому найденному файлу
        found_csv = csv_files[0]
        logger.info(f"Видео успешно обработано. Результат в файле: {found_csv.name}")
        
        return str(found_csv)