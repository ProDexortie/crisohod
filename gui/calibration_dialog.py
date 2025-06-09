"""
gui/calibration_dialog.py
Диалог калибровки камеры
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt

class CalibrationDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Калибровка камеры")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel(
            "Для калибровки камеры необходимо:\n\n"
            "1. Поместить калибровочные изображения в папку calibration_images\n"
            "2. Указать размер клетки шахматной доски\n"
            "3. Запустить калибровку\n\n"
            "После калибровки все измерения будут в миллиметрах."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        calibrate_btn = QPushButton("Выполнить калибровку")
        calibrate_btn.clicked.connect(self.run_calibration)
        layout.addWidget(calibrate_btn)
        
        layout.addStretch()
        
    def run_calibration(self):
        try:
            from processing.video_preprocessor import VideoPreprocessor
            preprocessor = VideoPreprocessor(self.config_manager)
            
            # Запускаем калибровку
            success, error = preprocessor.calibrate_from_images('calibration_images')
            
            if success > 0:
                QMessageBox.information(
                    self, "Успех",
                    f"Калибровка выполнена успешно!\n"
                    f"Обработано изображений: {success}\n"
                    f"Средняя ошибка: {error:.3f} пикселей"
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не удалось выполнить калибровку.\n"
                    "Проверьте калибровочные изображения."
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка при калибровке:\n{str(e)}"
            )