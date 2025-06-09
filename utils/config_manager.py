"""
utils/config_manager.py
Менеджер конфигурации приложения
"""

import json
import os
from pathlib import Path
from PyQt5.QtCore import QSettings


class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    def __init__(self):
        self.settings = QSettings('PhysioLab', 'CrisohodAnalyzer')
        self.config_file = Path('app_config.json')
        self.config = self._load_config()
        
    def _load_config(self):
        """Загрузка конфигурации"""
        # Значения по умолчанию
        default_config = {
            # Пути к файлам
            'experiments_dir': 'experiments',
            'config_path': 'config.yaml',
            'dlc_config_path': 'config.yaml',
            'pytorch_config_path': 'pytorch_config.yaml',
            'snapshot_path': 'snapshot-best-110.pt',
            'calibration_file': 'camera_calibration.json',
            
            # Параметры обработки
            'batch_size': 8,
            'force_reprocess': False,
            'show_calibration_info': False,
            'use_adaptive_threshold': True,
            'threshold_value': 128,
            
            # Параметры анализа
            'pixel_to_mm': 0.1,
            'min_contact_area': 50,
            'likelihood_threshold': 0.6,
            
            # Параметры интерфейса
            'theme': 'dark',
            'language': 'ru',
            'auto_save': True,
            'auto_save_interval': 300,  # секунд
            
            # Последние использованные пути
            'last_video_dir': '',
            'last_experiment_dir': '',
            'last_export_dir': ''
        }
        
        # Загружаем сохраненную конфигурацию
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                saved_config = json.load(f)
                # Объединяем с значениями по умолчанию
                default_config.update(saved_config)
                
        return default_config
        
    def save_config(self):
        """Сохранение конфигурации"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def get(self, key, default=None):
        """Получение значения конфигурации"""
        return self.config.get(key, default)
        
    def set(self, key, value):
        """Установка значения конфигурации"""
        self.config[key] = value
        
    def get_last_video_dir(self):
        """Получение последней директории с видео"""
        last_dir = self.get('last_video_dir', '')
        if last_dir and Path(last_dir).exists():
            return last_dir
        return str(Path.home())
        
    def set_last_video_dir(self, path):
        """Установка последней директории с видео"""
        self.set('last_video_dir', path)
        self.save_config()
        
    def get_dlc_paths(self):
        """Получение путей к файлам DeepLabCut"""
        return {
            'config': self.get('dlc_config_path'),
            'pytorch_config': self.get('pytorch_config_path'),
            'snapshot': self.get('snapshot_path')
        }
        
    def validate_dlc_setup(self):
        """Проверка настройки DeepLabCut"""
        paths = self.get_dlc_paths()
        missing = []
        
        for name, path in paths.items():
            if not Path(path).exists():
                missing.append(f"{name}: {path}")
                
        if missing:
            return False, "Отсутствуют файлы:\n" + "\n".join(missing)
            
        return True, "Все файлы найдены"
        
    def get_calibration_status(self):
        """Получение статуса калибровки"""
        cal_file = Path(self.get('calibration_file', 'camera_calibration.json'))
        
        if cal_file.exists():
            with open(cal_file, 'r') as f:
                cal_data = json.load(f)
                
            return {
                'calibrated': True,
                'file': str(cal_file),
                'error': cal_data.get('calibration_error', 'N/A'),
                'pixel_to_mm': cal_data.get('pixel_to_mm_ratio', None)
            }
        else:
            return {
                'calibrated': False,
                'file': None,
                'error': None,
                'pixel_to_mm': None
            }
            
    def reset_to_defaults(self):
        """Сброс к значениям по умолчанию"""
        self.config = self._load_config()
        self.save_config()
        
    def export_config(self, filepath):
        """Экспорт конфигурации"""
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def import_config(self, filepath):
        """Импорт конфигурации"""
        with open(filepath, 'r') as f:
            imported_config = json.load(f)
            
        # Обновляем только существующие ключи
        for key in self.config:
            if key in imported_config:
                self.config[key] = imported_config[key]
                
        self.save_config()