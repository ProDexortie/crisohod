"""
processing/dlc_model.py
Модуль для работы с моделью DeepLabCut PyTorch
"""

import torch
import torch.nn as nn
from pathlib import Path
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
import yaml


def get_dlc_inference_model(config_path: str, snapshot_path: str):
    """
    Загрузка модели DeepLabCut для инференса
    """
    try:
        import deeplabcut.pose_estimation_pytorch as dlc_pytorch
        from deeplabcut.pose_estimation_pytorch.config import DLCConfig
        from deeplabcut.pose_estimation_pytorch.models import PoseModel
        
        # Загружаем конфигурацию
        with open(config_path, 'r') as f:
            cfg_dict = yaml.safe_load(f)
        
        # Создаем DLCConfig
        dlc_config = DLCConfig.from_dict(cfg_dict)
        
        # Создаем модель
        model = PoseModel.from_config(dlc_config)
        
        # Загружаем веса
        checkpoint = torch.load(snapshot_path, map_location='cpu')
        if isinstance(checkpoint, dict):
            if 'model' in checkpoint:
                model.load_state_dict(checkpoint['model'])
            elif 'state_dict' in checkpoint:
                model.load_state_dict(checkpoint['state_dict'])
            else:
                model.load_state_dict(checkpoint)
        else:
            model.load_state_dict(checkpoint)
        
        model.eval()
        
        return model, dlc_config
        
    except ImportError:
        # Fallback для базовой модели если DeepLabCut не установлен
        return create_basic_dlc_model(config_path, snapshot_path)


def create_basic_dlc_model(config_path: str, snapshot_path: str):
    """
    Создание базовой модели ResNet50 для DeepLabCut
    """
    import torchvision.models as models
    
    # Загружаем конфигурацию
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f)
    
    num_bodyparts = len(cfg['metadata']['bodyparts'])
    
    class BasicDLCModel(nn.Module):
        def __init__(self, num_outputs):
            super().__init__()
            # ResNet50 backbone
            resnet = models.resnet50(pretrained=True)
            
            # Удаляем последние слои
            self.backbone = nn.Sequential(*list(resnet.children())[:-2])
            
            # Deconv layers для увеличения разрешения
            self.deconv_layers = nn.Sequential(
                nn.ConvTranspose2d(2048, 256, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
                nn.ConvTranspose2d(256, 256, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
                nn.ConvTranspose2d(256, 256, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(256),
                nn.ReLU(inplace=True),
            )
            
            # Выходной слой для heatmaps
            self.output_layer = nn.Conv2d(256, num_outputs, kernel_size=1)
            
        def forward(self, x):
            features = self.backbone(x)
            x = self.deconv_layers(features)
            heatmaps = self.output_layer(x)
            return heatmaps
    
    # Создаем модель
    model = BasicDLCModel(num_bodyparts)
    
    # Загружаем веса если есть
    if Path(snapshot_path).exists():
        checkpoint = torch.load(snapshot_path, map_location='cpu')
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            model.load_state_dict(checkpoint['state_dict'], strict=False)
    
    model.eval()
    
    # Создаем простую конфигурацию
    class SimpleConfig:
        def __init__(self, cfg_dict):
            self.metadata = cfg_dict.get('metadata', {})
            self.bodyparts = self.metadata.get('bodyparts', [])
            self.stride = 8  # output stride для ResNet50
    
    config = SimpleConfig(cfg)
    
    return model, config


class DLCInference:
    """
    Класс для выполнения инференса с моделью DeepLabCut
    """
    
    def __init__(self, model, config, device='cuda'):
        self.model = model
        self.config = config
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Параметры предобработки
        self.mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(self.device)
        self.std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(self.device)
        
    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        """
        Предобработка кадра для модели
        """
        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Преобразуем в тензор
        frame_tensor = torch.from_numpy(frame_rgb).float().permute(2, 0, 1) / 255.0
        
        # Нормализация
        frame_tensor = frame_tensor.unsqueeze(0).to(self.device)
        frame_tensor = (frame_tensor - self.mean) / self.std
        
        return frame_tensor
    
    def extract_keypoints_from_heatmaps(self, heatmaps: torch.Tensor, 
                                      original_shape: Tuple[int, int]) -> List[Dict]:
        """
        Извлечение координат ключевых точек из heatmaps
        """
        batch_size, num_keypoints, h, w = heatmaps.shape
        
        keypoints = []
        
        for i in range(num_keypoints):
            heatmap = heatmaps[0, i]  # Берем первый батч
            
            # Находим максимум
            max_val = heatmap.max()
            max_loc = (heatmap == max_val).nonzero(as_tuple=True)
            
            if len(max_loc[0]) > 0:
                y_hm = max_loc[0][0].item()
                x_hm = max_loc[1][0].item()
                
                # Преобразуем координаты обратно к размеру изображения
                x = x_hm * original_shape[1] / w
                y = y_hm * original_shape[0] / h
                
                # Вычисляем likelihood на основе значения в heatmap
                likelihood = torch.sigmoid(max_val).item()
                
                keypoints.append({
                    'x': float(x),
                    'y': float(y),
                    'likelihood': float(likelihood)
                })
            else:
                keypoints.append({
                    'x': 0.0,
                    'y': 0.0,
                    'likelihood': 0.0
                })
        
        return keypoints
    
    def predict_single_frame(self, frame: np.ndarray) -> Dict:
        """
        Предсказание для одного кадра
        """
        original_shape = frame.shape[:2]
        
        # Предобработка
        input_tensor = self.preprocess_frame(frame)
        
        # Предсказание
        with torch.no_grad():
            heatmaps = self.model(input_tensor)
        
        # Извлечение ключевых точек
        keypoints = self.extract_keypoints_from_heatmaps(heatmaps, original_shape)
        
        # Формируем результат
        result = {}
        bodyparts = self.config.bodyparts if hasattr(self.config, 'bodyparts') else []
        
        for i, bp in enumerate(bodyparts):
            if i < len(keypoints):
                result[bp] = keypoints[i]
            else:
                result[bp] = {'x': 0.0, 'y': 0.0, 'likelihood': 0.0}
        
        return result
    
    def process_video_batch(self, frames: List[np.ndarray]) -> List[Dict]:
        """
        Обработка батча кадров
        """
        if not frames:
            return []
        
        results = []
        
        # Обрабатываем батчами
        batch_size = 8
        for i in range(0, len(frames), batch_size):
            batch_frames = frames[i:i+batch_size]
            
            # Предобработка батча
            batch_tensors = []
            for frame in batch_frames:
                tensor = self.preprocess_frame(frame)
                batch_tensors.append(tensor)
            
            if batch_tensors:
                batch_input = torch.cat(batch_tensors, dim=0)
                
                # Предсказание
                with torch.no_grad():
                    batch_heatmaps = self.model(batch_input)
                
                # Обработка результатов
                for j, frame in enumerate(batch_frames):
                    heatmaps = batch_heatmaps[j:j+1]
                    keypoints = self.extract_keypoints_from_heatmaps(
                        heatmaps, frame.shape[:2]
                    )
                    
                    frame_result = {}
                    bodyparts = self.config.bodyparts if hasattr(self.config, 'bodyparts') else []
                    
                    for k, bp in enumerate(bodyparts):
                        if k < len(keypoints):
                            frame_result[bp] = keypoints[k]
                        else:
                            frame_result[bp] = {'x': 0.0, 'y': 0.0, 'likelihood': 0.0}
                    
                    results.append(frame_result)
        
        return results