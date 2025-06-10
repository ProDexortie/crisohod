# main_app.py (исправленная версия)

import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QFileDialog, QFormLayout, 
                             QGroupBox, QGridLayout, QTabWidget, QProgressBar, 
                             QStatusBar, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

from analysis_core import AnalysisCore
from plot_canvas import PlotCanvas
from video_viewer import ZoomableVideoLabel 

class ProcessingThread(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    def __init__(self, video_path, csv_path, config_path, threshold):
        super().__init__()
        self.video_path, self.csv_path, self.config_path, self.threshold = video_path, csv_path, config_path, threshold
    def run(self):
        local_analysis_core = AnalysisCore(self.video_path, self.csv_path, self.config_path)
        local_analysis_core.progress_updated.connect(self.progress)
        df_results = local_analysis_core.analyze_entire_video(self.threshold)
        local_analysis_core.close()
        self.finished.emit(df_results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор Походки v2.4 (Исправлено)")
        self.setGeometry(100, 100, 1300, 950)

        self.analysis_core = None; self.processing_thread = None
        self.results_df = pd.DataFrame(); self.video_path = None; self.csv_path = None

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.tab_analysis = QWidget()
        self.tabs.addTab(self.tab_analysis, "Анализ кадра")
        self.create_analysis_tab()
        
        self.tab_plots = QWidget()
        self.plot_canvas = PlotCanvas(self)
        self.create_plots_tab()
        self.tabs.addTab(self.tab_plots, "Графики")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()
        
    def create_plots_tab(self):
        layout = QVBoxLayout(self.tab_plots)
        self.build_graphs_button = QPushButton("Построить / Обновить графики")
        self.build_graphs_button.clicked.connect(self.start_full_analysis)
        self.build_graphs_button.setEnabled(False)
        layout.addWidget(self.build_graphs_button)
        layout.addWidget(self.plot_canvas)
        
    def create_analysis_tab(self):
        main_layout = QVBoxLayout(self.tab_analysis)
        
        top_controls = QHBoxLayout()
        self.load_button = QPushButton("Загрузить видео и CSV")
        self.load_button.clicked.connect(self.load_files)
        top_controls.addWidget(self.load_button)
        top_controls.addStretch()
        main_layout.addLayout(top_controls)

        settings_panel = QHBoxLayout()
        self.auto_threshold_check = QCheckBox("Авто-порог (Оцу)")
        self.auto_threshold_check.toggled.connect(self.toggle_auto_threshold)
        settings_panel.addWidget(self.auto_threshold_check)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255); self.threshold_slider.setValue(128)
        self.threshold_slider.valueChanged.connect(self.update_view)
        self.threshold_label = QLabel("128"); self.threshold_label.setMinimumWidth(30)
        settings_panel.addWidget(self.threshold_slider)
        settings_panel.addWidget(self.threshold_label)
        
        settings_panel.addSpacing(20)
        
        settings_panel.addWidget(QLabel("Обрезать (px):"))
        self.crop_spinbox = QSpinBox()
        self.crop_spinbox.setRange(0, 2000); self.crop_spinbox.setSingleStep(10)
        self.crop_spinbox.setValue(160)
        self.crop_spinbox.valueChanged.connect(self.update_view)
        settings_panel.addWidget(self.crop_spinbox)
        main_layout.addLayout(settings_panel)

        grid_layout = QGridLayout()
        self.video_label = ZoomableVideoLabel() 
        self.video_label.setText("Загрузите видео и CSV файл для начала работы")
        grid_layout.addWidget(self.video_label, 0, 0, 1, 2)
        self.frame_slider = QSlider(Qt.Horizontal); self.frame_slider.setEnabled(False)
        self.frame_slider.valueChanged.connect(self.update_ui_for_frame)
        grid_layout.addWidget(self.frame_slider, 1, 0, 1, 2)
        self.frame_label = QLabel("Кадр: -/-"); self.frame_label.setAlignment(Qt.AlignCenter)
        grid_layout.addWidget(self.frame_label, 2, 0, 1, 2)
        
        self.paw_widgets = {}
        paws = ['lf', 'rf', 'lb', 'rb']
        positions = [(3, 0), (3, 1), (4, 0), (4, 1)]
        paw_titles = {'lf': 'Левая передняя', 'rf': 'Правая передняя', 'lb': 'Левая задняя', 'rb': 'Правая задняя'}
        for paw, pos in zip(paws, positions):
            group_box = QGroupBox(paw_titles[paw])
            group_layout = QHBoxLayout(group_box)
            roi_label = QLabel(); roi_label.setFixedSize(150, 150)
            roi_label.setStyleSheet("border: 1px solid gray; background-color: black;")
            roi_label.setAlignment(Qt.AlignCenter)
            form_layout = QFormLayout()
            area_label = QLabel("0 px²"); length_label = QLabel("0.0 px")
            width24_label = QLabel("0.0 px"); width15_label = QLabel("0.0 px") if paw in ['lb', 'rb'] else QLabel("N/A")
            form_layout.addRow("Площадь:", area_label); form_layout.addRow("Длина:", length_label)
            form_layout.addRow("Ширина (2-4):", width24_label); form_layout.addRow("Ширина (1-5):", width15_label)
            group_layout.addWidget(roi_label); group_layout.addLayout(form_layout)
            grid_layout.addWidget(group_box, pos[0], pos[1])
            self.paw_widgets[paw] = {'roi': roi_label, 'area': area_label, 'length': length_label, 'width24': width24_label, 'width15': width15_label}
        main_layout.addLayout(grid_layout)
        
    def load_files(self):
        video_path, _ = QFileDialog.getOpenFileName(self, "Выберите видео файл", "", "Video Files (*.mp4 *.avi)")
        if not video_path: return
        csv_path, _ = QFileDialog.getOpenFileName(self, "Выберите CSV файл DeepLabCut", "", "CSV Files (*.csv)")
        if not csv_path: return
            
        try:
            self.video_path = video_path
            self.csv_path = csv_path
            self.analysis_core = AnalysisCore(self.video_path, self.csv_path)
            
            # --- ИСПРАВЛЕНИЕ: Меняем порядок активации ---
            # 1. Сначала активируем все элементы управления
            self.frame_slider.setEnabled(True)
            self.build_graphs_button.setEnabled(True) # <--- Активируем кнопку здесь!
            
            # 2. Настраиваем диапазоны
            self.frame_slider.setRange(0, self.analysis_core.total_frames - 1)
            self.crop_spinbox.setRange(0, self.analysis_core.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) // 2 - 10)
            
            # 3. Только потом отрисовываем первый кадр
            self.frame_slider.setValue(0)
            self.update_ui_for_frame(0)
            
        except Exception as e:
            self.video_label.setText(f"Ошибка загрузки файлов:\n{e}")
            self.build_graphs_button.setEnabled(False) # Деактивируем кнопку при ошибке

    def toggle_auto_threshold(self, checked):
        self.threshold_slider.setEnabled(not checked)
        self.threshold_label.setEnabled(not checked)
        self.update_view()

    def get_current_threshold(self):
        return -1 if self.auto_threshold_check.isChecked() else self.threshold_slider.value()

    def start_full_analysis(self):
        if not self.analysis_core: return
        self.progress_bar.show()
        self.status_bar.showMessage("Идет полный анализ видео для построения графиков...")
        self.tabs.setTabEnabled(1, False)
        self.build_graphs_button.setEnabled(False)

        self.processing_thread = ProcessingThread(
            video_path=self.video_path, csv_path=self.csv_path,
            config_path='config.yaml', threshold=self.get_current_threshold()
        )
        self.processing_thread.progress.connect(self.progress_bar.setValue)
        self.processing_thread.finished.connect(self.on_full_analysis_finished)
        self.processing_thread.start()

    def update_view(self):
        self.threshold_label.setText(str(self.threshold_slider.value()))
        if self.analysis_core and self.frame_slider.isEnabled():
            self.update_ui_for_frame(self.frame_slider.value())
            
    def update_ui_for_frame(self, frame_idx):
        if not self.analysis_core: return
        
        annotated_frame, frame_results = self.analysis_core.get_data_for_frame(
            frame_idx, self.get_current_threshold(), self.crop_spinbox.value()
        )
        if annotated_frame is None: return
        self.frame_label.setText(f"Кадр: {frame_idx} / {self.analysis_core.total_frames - 1}")
        h, w, ch = annotated_frame.shape
        q_img = QImage(annotated_frame.data, w, h, ch * w, QImage.Format_RGB888).rgbSwapped()
        self.video_label.set_pixmap(QPixmap.fromImage(q_img))
        
        for paw_name, widgets in self.paw_widgets.items():
            data = frame_results.get(paw_name)
            if data:
                widgets['area'].setText(f"{data['area_px']} px²")
                widgets['length'].setText(f"{data['length_px']:.1f} px")
                widgets['width24'].setText(f"{data['width_2_4_px']:.1f} px")
                if paw_name in ['lb', 'rb']: widgets['width15'].setText(f"{data['width_1_5_px']:.1f} px")
                roi_img = data['roi_image']
                if roi_img is not None and roi_img.size > 0:
                    roi_h, roi_w = roi_img.shape
                    q_roi_img = QImage(roi_img.data, roi_w, roi_h, roi_w, QImage.Format_Grayscale8)
                    widgets['roi'].setPixmap(QPixmap.fromImage(q_roi_img).scaled(widgets['roi'].size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else: widgets['roi'].clear()

    def on_full_analysis_finished(self, df):
        self.results_df = df
        self.plot_canvas.plot(df)
        self.status_bar.showMessage("Анализ завершен. Графики построены.", 5000)
        self.progress_bar.hide()
        self.tabs.setTabEnabled(1, True)
        self.build_graphs_button.setEnabled(True)

    def closeEvent(self, event):
        if self.analysis_core: self.analysis_core.close()
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.quit()
            self.processing_thread.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())