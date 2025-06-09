import cv2
import numpy as np
import pandas as pd
from pathlib import Path

class ThresholdTuner:
    """
    Интерактивный инструмент для настройки порогов бинаризации
    для анализа контактных областей лап.
    """
    
    def __init__(self, video_path, csv_path, config_path='config.yaml'):
        self.video_path = video_path
        self.csv_path = csv_path
        self.config_path = config_path
        
        # Загружаем анализатор
        from paw_contact_analyzer import PawContactAnalyzer
        self.analyzer = PawContactAnalyzer(config_path)
        
        # Загружаем данные
        self.df = self.analyzer.load_deeplabcut_csv(csv_path)
        self.cap = cv2.VideoCapture(video_path)
        
        # Параметры
        self.current_frame = 0
        self.threshold_value = 128
        self.selected_paw = 'lf'
        self.show_binary = True
        self.paw_names = ['lf', 'rf', 'lb', 'rb']
        
    def run(self):
        """Запуск интерактивного интерфейса"""
        cv2.namedWindow('Threshold Tuner', cv2.WINDOW_NORMAL)
        cv2.createTrackbar('Threshold', 'Threshold Tuner', self.threshold_value, 255, self._on_threshold_change)
        cv2.createTrackbar('Frame', 'Threshold Tuner', 0, 
                          int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1, 
                          self._on_frame_change)
        
        print("Управление:")
        print("- Используйте трекбары для настройки порога и выбора кадра")
        print("- Клавиши 1-4: выбор лапы (1:lf, 2:rf, 3:lb, 4:rb)")
        print("- Пробел: переключение отображения бинарного изображения")
        print("- S: сохранить текущие настройки")
        print("- Q/ESC: выход")
        
        while True:
            self._update_display()
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q или ESC
                break
            elif key == ord(' '):
                self.show_binary = not self.show_binary
            elif key == ord('s'):
                self._save_settings()
            elif ord('1') <= key <= ord('4'):
                self.selected_paw = self.paw_names[key - ord('1')]
                print(f"Выбрана лапа: {self.selected_paw}")
        
        self.cap.release()
        cv2.destroyAllWindows()
    
    def _on_threshold_change(self, value):
        """Обработчик изменения порога"""
        self.threshold_value = value
    
    def _on_frame_change(self, value):
        """Обработчик изменения кадра"""
        self.current_frame = value
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, value)
    
    def _update_display(self):
        """Обновление отображения"""
        # Читаем текущий кадр
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Создаем копию для аннотаций
        display_frame = frame.copy()
        
        # Получаем bbox для выбранной лапы
        bbox = self.analyzer.get_paw_bbox(self.df, self.current_frame, self.selected_paw)
        
        if bbox is not None:
            x_min, y_min, x_max, y_max = bbox
            
            # Анализируем контактную область
            contact_area, binary_roi = self.analyzer.analyze_contact_area(
                frame, bbox, self.threshold_value
            )
            
            # Рисуем bbox
            color = self.analyzer._get_paw_color(self.selected_paw)
            cv2.rectangle(display_frame, (x_min, y_min), (x_max, y_max), color, 2)
            
            # Показываем информацию
            info_text = f"{self.selected_paw}: {contact_area} px | Threshold: {self.threshold_value}"
            cv2.putText(display_frame, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Показываем бинарное изображение
            if self.show_binary and binary_roi is not None:
                # Увеличиваем для лучшей видимости
                scale_factor = 3
                binary_large = cv2.resize(binary_roi, None, fx=scale_factor, fy=scale_factor, 
                                        interpolation=cv2.INTER_NEAREST)
                
                # Конвертируем в цветное
                binary_color = cv2.cvtColor(binary_large, cv2.COLOR_GRAY2BGR)
                
                # Добавляем рамку
                cv2.rectangle(binary_color, (0, 0), 
                            (binary_color.shape[1]-1, binary_color.shape[0]-1), 
                            color, 2)
                
                # Размещаем в углу
                h, w = binary_color.shape[:2]
                display_frame[50:50+h, 10:10+w] = binary_color
        else:
            cv2.putText(display_frame, f"Лапа {self.selected_paw} не обнаружена", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Рисуем скелет
        self.analyzer._draw_skeleton(display_frame, self.df, self.current_frame)
        
        # Показываем номер кадра
        cv2.putText(display_frame, f"Frame: {self.current_frame}", 
                   (display_frame.shape[1] - 150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow('Threshold Tuner', display_frame)
    
    def _save_settings(self):
        """Сохранение текущих настроек"""
        settings = {
            'threshold_value': self.threshold_value,
            'selected_frame': self.current_frame,
            'selected_paw': self.selected_paw
        }
        
        import json
        with open('threshold_settings.json', 'w') as f:
            json.dump(settings, f, indent=2)
        
        print(f"Настройки сохранены: порог={self.threshold_value}")


# Дополнительный скрипт для пакетной обработки
class BatchProcessor:
    """
    Пакетная обработка нескольких видео с использованием
    сохраненных настроек порогов.
    """
    
    def __init__(self, config_path='config.yaml'):
        from paw_contact_analyzer import PawContactAnalyzer
        self.analyzer = PawContactAnalyzer(config_path)
    
    def process_batch(self, video_csv_pairs, output_dir, threshold_settings=None):
        """
        Обработка нескольких видео.
        
        Args:
            video_csv_pairs: список кортежей (video_path, csv_path)
            output_dir: директория для сохранения результатов
            threshold_settings: путь к файлу с настройками порогов
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Загружаем настройки порогов
        threshold_value = None
        if threshold_settings:
            import json
            with open(threshold_settings, 'r') as f:
                settings = json.load(f)
                threshold_value = settings.get('threshold_value', None)
        
        # Обрабатываем каждое видео
        for idx, (video_path, csv_path) in enumerate(video_csv_pairs):
            print(f"\nОбработка видео {idx + 1}/{len(video_csv_pairs)}: {video_path}")
            
            # Имена файлов для результатов
            video_name = Path(video_path).stem
            output_video = output_dir / f"{video_name}_annotated.mp4"
            output_csv = output_dir / f"{video_name}_contact_areas.csv"
            output_plot = output_dir / f"{video_name}_plot.png"
            
            # Обрабатываем видео
            self.analyzer.results = []  # Очищаем предыдущие результаты
            self.analyzer.process_video(
                video_path=video_path,
                csv_path=csv_path,
                output_path=str(output_video),
                threshold_value=threshold_value
            )
            
            # Сохраняем результаты
            self.analyzer.save_results(str(output_csv))
            self.analyzer.plot_results(str(output_plot))
            
            print(f"Результаты сохранены в {output_dir}")
    
    def generate_summary_report(self, results_dir):
        """
        Генерация сводного отчета по всем обработанным видео.
        
        Args:
            results_dir: директория с результатами анализа
        """
        results_dir = Path(results_dir)
        all_results = []
        
        # Собираем все CSV файлы с результатами
        for csv_file in results_dir.glob("*_contact_areas.csv"):
            df = pd.read_csv(csv_file)
            df['video'] = csv_file.stem.replace('_contact_areas', '')
            all_results.append(df)
        
        if not all_results:
            print("Не найдено файлов с результатами")
            return
        
        # Объединяем результаты
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Генерируем статистику
        summary = []
        for video in combined_df['video'].unique():
            video_data = combined_df[combined_df['video'] == video]
            
            stats = {'video': video}
            for paw in ['lf', 'rf', 'lb', 'rb']:
                col_name = f'{paw}_area'
                if col_name in video_data.columns:
                    stats[f'{paw}_mean'] = video_data[col_name].mean()
                    stats[f'{paw}_std'] = video_data[col_name].std()
                    stats[f'{paw}_max'] = video_data[col_name].max()
            
            summary.append(stats)
        
        # Сохраняем сводный отчет
        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(results_dir / 'summary_report.csv', index=False)
        
        print(f"Сводный отчет сохранен: {results_dir / 'summary_report.csv'}")
        
        return summary_df


# Пример использования
if __name__ == "__main__":
    # Интерактивная настройка порогов
    tuner = ThresholdTuner(
        video_path="path/to/video.mp4",
        csv_path="path/to/deeplabcut_results.csv",
        config_path="config.yaml"
    )
    tuner.run()
    
    # Пакетная обработка
    processor = BatchProcessor("config.yaml")
    
    # Список видео для обработки
    videos_to_process = [
        ("video1.mp4", "video1_DLC.csv"),
        ("video2.mp4", "video2_DLC.csv"),
        # ... добавьте больше видео
    ]
    
    processor.process_batch(
        video_csv_pairs=videos_to_process,
        output_dir="results",
        threshold_settings="threshold_settings.json"
    )
    
    # Генерация сводного отчета
    processor.generate_summary_report("results")