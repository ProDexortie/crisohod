# analysis_core.py (исправленная версия)

import cv2
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from PyQt5.QtCore import pyqtSignal, QObject
from PIL import Image, ImageDraw, ImageFont

class AnalysisCore(QObject):
    progress_updated = pyqtSignal(int)

    def __init__(self, video_path, csv_path, config_path='config.yaml'):
        super().__init__()
        # ... (код __init__ до загрузки шрифта)
        if not Path(video_path).exists() or not Path(csv_path).exists() or not Path(config_path).exists():
            raise FileNotFoundError("Один или несколько файлов (видео, csv, config) не найдены.")

        self.config_path = config_path
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.bodyparts = config['bodyparts']
        self.skeleton = config.get('skeleton', [])
        
        self.paw_groups = self._define_paw_groups()
        self.df = pd.read_csv(csv_path, header=[0, 1, 2], index_col=0)
        self.scorer = self.df.columns.levels[0][0]
        
        self.cap = cv2.VideoCapture(video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.PAW_COLORS = {'lf': (255, 100, 100), 'rf': (100, 255, 100), 'lb': (100, 100, 255), 'rb': (255, 255, 100)}
        self.PAW_LABELS = {'lf': 'ЛП', 'rf': 'ПП', 'lb': 'ЛЗ', 'rb': 'ПЗ'}
        
        # --- ИСПРАВЛЕНИЕ: Более надежный поиск шрифта ---
        font_paths = [
            "arial.ttf",                   # Для Windows
            "DejaVuSans.ttf",              # Стандарт для многих Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Явный путь в Linux
            "/System/Library/Fonts/Supplemental/Arial.ttf"     # Для macOS
        ]
        self.font = None
        for font_path in font_paths:
            try:
                self.font = ImageFont.truetype(font_path, 20)
                print(f"Шрифт '{font_path}' успешно загружен.")
                break
            except IOError:
                continue
        
        if not self.font:
            self.font = ImageFont.load_default()
            print("ПРЕДУПРЕЖДЕНИЕ: Подходящий шрифт не найден. Кириллица может не отображаться.")

    # ... (остальной код остается без изменений) ...
    def _define_paw_groups(self):
        groups = {'lf': [], 'rf': [], 'lb': [], 'rb': []}
        for bodypart in self.bodyparts:
            for paw_name in groups.keys():
                if bodypart.startswith(paw_name + '_'):
                    groups[paw_name].append(bodypart)
        return groups

    def _get_coords(self, frame_idx, bodypart, likelihood_threshold=0.6):
        try:
            x = self.df.loc[frame_idx, (self.scorer, bodypart, 'x')]
            y = self.df.loc[frame_idx, (self.scorer, bodypart, 'y')]
            likelihood = self.df.loc[frame_idx, (self.scorer, bodypart, 'likelihood')]
            if likelihood >= likelihood_threshold:
                return (float(x), float(y))
        except (KeyError, IndexError):
            pass
        return None

    def _calculate_metrics(self, frame_idx, paw_name):
        metrics = {'length_px': 0.0, 'width_1_5_px': 0.0, 'width_2_4_px': 0.0}
        heel_coords = self._get_coords(frame_idx, f'{paw_name}_heel')
        if heel_coords:
            max_dist = 0
            digit_bodyparts = [bp for bp in self.bodyparts if bp.startswith(f'{paw_name}_digit')]
            for digit_bp in digit_bodyparts:
                digit_coords = self._get_coords(frame_idx, digit_bp)
                if digit_coords:
                    dist = np.linalg.norm(np.array(heel_coords) - np.array(digit_coords))
                    if dist > max_dist:
                        max_dist = dist
            metrics['length_px'] = max_dist
        if paw_name in ['lb', 'rb']:
            d1 = self._get_coords(frame_idx, f'{paw_name}_digit1'); d5 = self._get_coords(frame_idx, f'{paw_name}_digit5')
            if d1 and d5: metrics['width_1_5_px'] = np.linalg.norm(np.array(d1) - np.array(d5))
        d2 = self._get_coords(frame_idx, f'{paw_name}_digit2'); d4 = self._get_coords(frame_idx, f'{paw_name}_digit4')
        if d2 and d4: metrics['width_2_4_px'] = np.linalg.norm(np.array(d2) - np.array(d4))
        return metrics

    def _analyze_paw_area(self, frame, bbox, threshold_value):
        roi = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]
        if roi.size == 0:
            return 0, np.zeros((100, 100), dtype=np.uint8)

        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
        
        if threshold_value == -1:
            _, binary_roi_raw = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, binary_roi_raw = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY_INV)
            
        kernel = np.ones((3, 3), np.uint8)
        binary_roi = cv2.morphologyEx(binary_roi_raw, cv2.MORPH_CLOSE, kernel)
        area = np.sum(binary_roi == 255)
        
        if area > 450:
            area = 0
            binary_roi.fill(0)
            
        return area, binary_roi
        
    def get_data_for_frame(self, frame_idx, threshold_value=128, crop_pixels=0):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if not ret: return None, None

        h, w, _ = frame.shape
        if (h - 2 * crop_pixels) <= 0: crop_pixels = 0
        
        cropped_frame_np = frame[crop_pixels : h - crop_pixels, :].copy()
        
        pil_img = Image.fromarray(cv2.cvtColor(cropped_frame_np, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        frame_analysis_results = {}
        for paw_name in self.paw_groups.keys():
            paw_points = [self._get_coords(frame_idx, bp) for bp in self.paw_groups[paw_name]]
            valid_points = [p for p in paw_points if p is not None]
            area, binary_roi = 0, np.zeros((100, 100), dtype=np.uint8)

            if len(valid_points) >= 3:
                valid_points_np = np.array(valid_points)
                x_min, y_min = valid_points_np.min(axis=0); x_max, y_max = valid_points_np.max(axis=0)
                padding = 10
                bbox = (int(max(0, x_min - padding)), int(max(0, y_min - padding)),
                        int(x_max + padding), int(y_max + padding))
                
                area, binary_roi = self._analyze_paw_area(frame, bbox, threshold_value)
                
                new_bbox = (bbox[0], bbox[1] - crop_pixels, bbox[2], bbox[3] - crop_pixels)
                color = self.PAW_COLORS.get(paw_name, (255, 255, 255))
                label = self.PAW_LABELS.get(paw_name, '')
                
                draw.rectangle([(new_bbox[0], new_bbox[1]), (new_bbox[2], new_bbox[3])], outline=color, width=2)
                draw.text((new_bbox[0], new_bbox[1] - 25), label, font=self.font, fill=color)

            metrics = self._calculate_metrics(frame_idx, paw_name)
            frame_analysis_results[paw_name] = {'area_px': area, 'roi_image': binary_roi, **metrics}

        annotated_frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        self._draw_skeleton(annotated_frame, frame_idx, y_offset=-crop_pixels)
        
        return annotated_frame, frame_analysis_results

    def analyze_entire_video(self, threshold_value):
        all_results = []
        for frame_idx in range(self.total_frames):
            frame_data = {'frame': frame_idx}
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.cap.read()
            if not ret: continue
            for paw_name in self.paw_groups.keys():
                metrics = self._calculate_metrics(frame_idx, paw_name)
                frame_data[f'{paw_name}_length_px'] = metrics['length_px']
                
                paw_points = [self._get_coords(frame_idx, bp) for bp in self.paw_groups[paw_name]]
                valid_points = [p for p in paw_points if p is not None]
                area = 0
                if len(valid_points) >= 3:
                    valid_points_np = np.array(valid_points)
                    x_min, y_min = valid_points_np.min(axis=0); x_max, y_max = valid_points_np.max(axis=0)
                    padding = 10
                    bbox = (int(max(0, x_min - padding)), int(max(0, y_min - padding)), int(x_max + padding), int(y_max + padding))
                    area, _ = self._analyze_paw_area(frame, bbox, threshold_value)
                
                frame_data[f'{paw_name}_area_px'] = area

            all_results.append(frame_data)
            
            if frame_idx > 0 and frame_idx % (self.total_frames // 20) == 0:
                self.progress_updated.emit(int(100 * frame_idx / self.total_frames))

        self.progress_updated.emit(100)
        return pd.DataFrame(all_results)
        
    def _draw_skeleton(self, frame, frame_idx, y_offset=0, likelihood_threshold=0.6):
        for bodypart in self.bodyparts:
            coords = self._get_coords(frame_idx, bodypart, likelihood_threshold)
            if coords:
                color = self.PAW_COLORS.get(bodypart[:2], (255, 255, 255))
                cv2.circle(frame, (int(coords[0]), int(coords[1] + y_offset)), 2, color, -1)
        
        for connection in self.skeleton:
            p1_coords = self._get_coords(frame_idx, connection[0], likelihood_threshold)
            p2_coords = self._get_coords(frame_idx, connection[1], likelihood_threshold)
            if p1_coords and p2_coords:
                p1 = (int(p1_coords[0]), int(p1_coords[1] + y_offset))
                p2 = (int(p2_coords[0]), int(p2_coords[1] + y_offset))
                cv2.line(frame, p1, p2, (255, 255, 0), 1)

    def close(self):
        self.cap.release()