#!/usr/bin/env python3
"""
Быстрый запуск анализа контактных областей лап крысы.
Использование:
    python quick_analyze.py --video path/to/video.mp4 --csv path/to/deeplabcut.csv
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Анализ контактных областей лап крысы')
    parser.add_argument('--video', required=True, help='Путь к видео файлу')
    parser.add_argument('--csv', required=True, help='Путь к CSV файлу DeepLabCut')
    parser.add_argument('--config', default='config.yaml', help='Путь к конфигурации DeepLabCut')
    parser.add_argument('--output-dir', default='output', help='Директория для сохранения результатов')
    parser.add_argument('--start-frame', type=int, default=0, help='Начальный кадр')
    parser.add_argument('--end-frame', type=int, default=None, help='Конечный кадр')
    parser.add_argument('--threshold', type=int, default=None, help='Пороговое значение (0-255)')
    parser.add_argument('--no-video', action='store_true', help='Не создавать аннотированное видео')
    parser.add_argument('--tune', action='store_true', help='Запустить интерактивную настройку порогов')
    
    args = parser.parse_args()
    
    # Проверяем существование файлов
    if not Path(args.video).exists():
        print(f"Ошибка: видео файл не найден: {args.video}")
        sys.exit(1)
    
    if not Path(args.csv).exists():
        print(f"Ошибка: CSV файл не найден: {args.csv}")
        sys.exit(1)
    
    if not Path(args.config).exists():
        print(f"Ошибка: файл конфигурации не найден: {args.config}")
        sys.exit(1)
    
    # Создаем выходную директорию
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Если запрошена интерактивная настройка
    if args.tune:
        from threshold_tuner import ThresholdTuner
        print("Запуск интерактивной настройки порогов...")
        tuner = ThresholdTuner(args.video, args.csv, args.config)
        tuner.run()
        return
    
    # Импортируем анализатор
    from paw_contact_analyzer import PawContactAnalyzer
    
    # Создаем анализатор
    print("Инициализация анализатора...")
    analyzer = PawContactAnalyzer(args.config)
    
    # Определяем пути для выходных файлов
    video_name = Path(args.video).stem
    output_video = output_dir / f"{video_name}_annotated.mp4" if not args.no_video else None
    output_csv = output_dir / f"{video_name}_contact_areas.csv"
    output_plot = output_dir / f"{video_name}_plot.png"
    
    # Запускаем анализ
    print(f"Анализ видео: {args.video}")
    print(f"Кадры: {args.start_frame} - {args.end_frame if args.end_frame else 'конец'}")
    if args.threshold:
        print(f"Пороговое значение: {args.threshold}")
    
    analyzer.process_video(
        video_path=args.video,
        csv_path=args.csv,
        output_path=str(output_video) if output_video else None,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        threshold_value=args.threshold
    )
    
    # Сохраняем результаты
    print("\nСохранение результатов...")
    analyzer.save_results(str(output_csv))
    analyzer.plot_results(str(output_plot))
    
    print(f"\nАнализ завершен!")
    print(f"Результаты сохранены в директории: {output_dir}")
    print(f"- CSV с данными: {output_csv}")
    print(f"- График: {output_plot}")
    if output_video:
        print(f"- Аннотированное видео: {output_video}")
    
    # Показываем краткую статистику
    import pandas as pd
    df_results = pd.DataFrame(analyzer.results)
    
    print("\nКраткая статистика:")
    for paw in ['lf', 'rf', 'lb', 'rb']:
        col_name = f'{paw}_area'
        if col_name in df_results.columns:
            mean_area = df_results[col_name].mean()
            max_area = df_results[col_name].max()
            print(f"  {paw}: средняя площадь = {mean_area:.1f} px, макс = {max_area:.0f} px")


if __name__ == "__main__":
    main()