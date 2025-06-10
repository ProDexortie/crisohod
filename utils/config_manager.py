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
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # Объединяем с значениями по умолчанию
                    default_config.update(saved_config)
            except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
                print(f"Ошибка при загрузке конфигурации: {e}")
                print("Используются настройки по умолчанию")
                
        return default_config
        
    def save_config(self):
        """Сохранение конфигурации"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка при сохранении конфигурации: {e}")
            
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
            if not path or not Path(path).exists():
                missing.append(f"{name}: {path}")
                
        if missing:
            return False, "Отсутствуют файлы:\n" + "\n".join(missing)
            
        return True, "Все файлы найдены"
        
    def get_calibration_status(self):
        """Получение статуса калибровки"""
        cal_file_path = self.get('calibration_file', 'camera_calibration.json')
        cal_file = Path(cal_file_path)
        
        if cal_file.exists():
            try:
                with open(cal_file, 'r', encoding='utf-8') as f:
                    cal_data = json.load(f)
                
                # Безопасное извлечение значений
                error = cal_data.get('calibration_error')
                pixel_to_mm = cal_data.get('pixel_to_mm_ratio')
                
                # Проверяем и преобразуем значения
                try:
                    if error is not None:
                        error = float(error)
                except (ValueError, TypeError):
                    error = None
                    
                try:
                    if pixel_to_mm is not None:
                        pixel_to_mm = float(pixel_to_mm)
                except (ValueError, TypeError):
                    pixel_to_mm = None
                
                return {
                    'calibrated': True,
                    'file': str(cal_file),
                    'error': error,
                    'pixel_to_mm': pixel_to_mm
                }
                
            except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
                print(f"Ошибка при чтении файла калибровки: {e}")
                return {
                    'calibrated': False,
                    'file': str(cal_file),
                    'error': f"Ошибка чтения файла: {e}",
                    'pixel_to_mm': None
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
        # Удаляем текущий файл конфигурации
        if self.config_file.exists():
            try:
                self.config_file.unlink()
            except Exception as e:
                print(f"Ошибка при удалении файла конфигурации: {e}")
        
        # Перезагружаем конфигурацию
        self.config = self._load_config()
        self.save_config()

    def get_absolute_path(self, key, default=None):
        """Получение абсолютного пути из конфигурации"""
        path = self.get(key, default)
        if path:
            path = Path(path)
            if not path.is_absolute():
                # Если путь относительный, делаем его относительным от текущей директории
                path = Path.cwd() / path
            return str(path)
        return default
        
    def export_config(self, filepath):
        """Экспорт конфигурации"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка при экспорте конфигурации: {e}")
            raise
            
    def import_config(self, filepath):
        """Импорт конфигурации"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
                
            # Обновляем только существующие ключи
            for key in self.config:
                if key in imported_config:
                    self.config[key] = imported_config[key]
                    
            self.save_config()
        except Exception as e:
            print(f"Ошибка при импорте конфигурации: {e}")
            raise