"""
gui/experiment_properties_dialog.py
Диалог свойств эксперимента
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                             QLineEdit, QTextEdit, QDialogButtonBox)
import json

class ExperimentPropertiesDialog(QDialog):
    def __init__(self, experiment_path, parent=None):
        super().__init__(parent)
        self.experiment_path = experiment_path
        self.setWindowTitle("Свойства эксперимента")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Поля для редактирования
        self.name_edit = QLineEdit()
        form_layout.addRow("Название:", self.name_edit)
        
        self.animal_id_edit = QLineEdit()
        form_layout.addRow("ID животного:", self.animal_id_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Описание:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Загружаем данные
        self.load_data()
        
    def load_data(self):
        meta_file = self.experiment_path / 'experiment.json'
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                self.metadata = json.load(f)
                
            self.name_edit.setText(self.metadata.get('name', ''))
            self.animal_id_edit.setText(self.metadata.get('animal_id', ''))
            self.description_edit.setPlainText(self.metadata.get('description', ''))
            
    def accept(self):
        # Сохраняем изменения
        self.metadata['name'] = self.name_edit.text()
        self.metadata['animal_id'] = self.animal_id_edit.text()
        self.metadata['description'] = self.description_edit.toPlainText()
        
        meta_file = self.experiment_path / 'experiment.json'
        with open(meta_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
            
        super().accept()