# crisohod/processing/dlc_model.py
# Модуль для инициализации модели DeepLabCut для анализа видео.

from pathlib import Path
from deeplabcut.core.config import read_config_as_dict
import deeplabcut.pose_estimation_pytorch as dlc_torch

def get_dlc_inference_runner(pytorch_config_path: str, snapshot_path: str, batch_size: int = 16):
    """
    Создает и настраивает исполнителя (runner) для анализа видео с помощью
    модели DeepLabCut.

    Эта функция загружает конфигурацию модели, строит саму модель и загружает в нее
    указанные веса (снэпшот), подготавливая ее к работе.

    Args:
        pytorch_config_path (str): Путь к файлу pytorch_config.yaml.
        snapshot_path (str): Путь к файлу с весами модели (*.pt).
        batch_size (int): Размер пакета для обработки. Подберите в зависимости от вашей GPU.

    Returns:
        dlc_torch.PoseInferenceRunner: Готовый к работе исполнитель для анализа поз.
    """
    print(f"Загрузка конфигурации модели из: {pytorch_config_path}")
    model_cfg = read_config_as_dict(pytorch_config_path)

    # В вашем проекте одно животное, поэтому max_individuals=1
    max_individuals = 1

    print(f"Инициализация модели и загрузка весов из: {snapshot_path}")
    # Используем встроенную функцию DeepLabCut для получения готового "исполнителя" (runner).
    pose_runner = dlc_torch.get_pose_inference_runner(
        model_config=model_cfg,
        snapshot_path=snapshot_path,
        max_individuals=max_individuals,
        batch_size=batch_size,
    )
    
    print("Исполнитель DeepLabCut (Inference Runner) успешно создан и готов к работе.")
    return pose_runner