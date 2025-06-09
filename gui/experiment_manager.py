"""
gui/experiment_manager.py
Виджет для управления экспериментами
"""

import os
import json
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
                             QMessageBox, QFileDialog, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtGui import QIcon


class ExperimentManager(QWidget):
    """Менеджер экспериментов"""
    experiment_selected = pyqtSignal(str)  # Путь к эксперименту
    video_selected = pyqtSignal(str)  # Путь к видео
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.experiments_dir = Path(config_manager.get('experiments_dir', 'experiments'))
        self.experiments_dir.mkdir(exist_ok=True)
        self.init_ui()
        self.load_experiments()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header_label = QLabel("Эксперименты")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        
        # Кнопка создания нового эксперимента
        new_btn = QPushButton("+")
        new_btn.setMaximumWidth(30)
        new_btn.clicked.connect(self.new_experiment)
        header_layout.addWidget(new_btn)
        
        layout.addLayout(header_layout)
        
        # Дерево экспериментов
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Структура проекта")
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # Информация о выбранном элементе
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setMaximumHeight(100)
        self.info_label.setStyleSheet("background-color: #2a2a2a; padding: 5px;")
        layout.addWidget(self.info_label)
        
    def load_experiments(self):
        """Загрузка списка экспериментов"""
        self.tree.clear()
        
        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir() and (exp_dir / 'experiment.json').exists():
                self.add_experiment_to_tree(exp_dir)
                
    def add_experiment_to_tree(self, exp_path):
        """Добавление эксперимента в дерево"""
        # Загружаем метаданные эксперимента
        meta_file = exp_path / 'experiment.json'
        with open(meta_file, 'r') as f:
            metadata = json.load(f)
            
        # Создаем элемент эксперимента
        exp_item = QTreeWidgetItem(self.tree)
        exp_item.setText(0, metadata['name'])
        exp_item.setData(0, Qt.UserRole, str(exp_path))
        exp_item.setData(0, Qt.UserRole + 1, 'experiment')
        
        # Добавляем папки
        folders = {
            'videos': 'Видео',
            'raw_videos': 'Исходные видео',
            'processed_videos': 'Обработанные видео',
            'results': 'Результаты',
            'configs': 'Конфигурации'
        }
        
        for folder, label in folders.items():
            folder_path = exp_path / folder
            if folder_path.exists():
                folder_item = QTreeWidgetItem(exp_item)
                folder_item.setText(0, label)
                folder_item.setData(0, Qt.UserRole, str(folder_path))
                folder_item.setData(0, Qt.UserRole + 1, 'folder')
                
                # Добавляем файлы
                self.add_files_to_folder(folder_item, folder_path)
                
    def add_files_to_folder(self, parent_item, folder_path):
        """Добавление файлов в папку"""
        folder_path = Path(folder_path)
        
        # Фильтры для разных типов файлов
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        data_extensions = ['.csv', '.xlsx', '.json']
        
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                file_item = QTreeWidgetItem(parent_item)
                file_item.setText(0, file_path.name)
                file_item.setData(0, Qt.UserRole, str(file_path))
                
                # Определяем тип файла
                if file_path.suffix in video_extensions:
                    file_item.setData(0, Qt.UserRole + 1, 'video')
                elif file_path.suffix in data_extensions:
                    file_item.setData(0, Qt.UserRole + 1, 'data')
                else:
                    file_item.setData(0, Qt.UserRole + 1, 'file')
                    
    def new_experiment(self):
        """Создание нового эксперимента"""
        name, ok = QInputDialog.getText(
            self, "Новый эксперимент", 
            "Введите название эксперимента:"
        )
        
        if ok and name:
            # Создаем структуру папок
            exp_path = self.experiments_dir / name
            if exp_path.exists():
                QMessageBox.warning(self, "Ошибка", 
                                  "Эксперимент с таким именем уже существует")
                return
                
            exp_path.mkdir()
            
            # Создаем подпапки
            folders = ['videos', 'raw_videos', 'processed_videos', 
                      'results', 'configs', 'calibration']
            for folder in folders:
                (exp_path / folder).mkdir()
                
            # Создаем метаданные
            metadata = {
                'name': name,
                'created': datetime.now().isoformat(),
                'description': '',
                'animal_id': '',
                'experiment_type': 'gait_analysis',
                'parameters': {
                    'species': 'rat',
                    'age': '',
                    'weight': '',
                    'sex': ''
                }
            }
            
            with open(exp_path / 'experiment.json', 'w') as f:
                json.dump(metadata, f, indent=2)
                
            # Копируем конфигурационные файлы
            import shutil
            config_files = ['config.yaml', 'pytorch_config.yaml']
            for config_file in config_files:
                if Path(config_file).exists():
                    shutil.copy(config_file, exp_path / 'configs' / config_file)
                    
            # Обновляем дерево
            self.add_experiment_to_tree(exp_path)
            
            QMessageBox.information(self, "Успех", 
                                  f"Эксперимент '{name}' создан успешно")
            
    def open_experiment(self):
        """Открытие существующего эксперимента"""
        exp_dir = QFileDialog.getExistingDirectory(
            self, "Выберите папку эксперимента", 
            str(self.experiments_dir)
        )
        
        if exp_dir:
            exp_path = Path(exp_dir)
            if (exp_path / 'experiment.json').exists():
                self.experiment_selected.emit(str(exp_path))
            else:
                QMessageBox.warning(self, "Ошибка", 
                                  "Выбранная папка не содержит эксперимент")
                
    def show_context_menu(self, position):
        """Показать контекстное меню"""
        item = self.tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        item_type = item.data(0, Qt.UserRole + 1)
        item_path = Path(item.data(0, Qt.UserRole))
        
        if item_type == 'experiment':
            menu.addAction("Открыть", lambda: self.open_experiment_item(item))
            menu.addAction("Переименовать", lambda: self.rename_experiment(item))
            menu.addSeparator()
            menu.addAction("Добавить видео", lambda: self.add_video_to_experiment(item))
            menu.addAction("Импортировать результаты", 
                          lambda: self.import_results(item))
            menu.addSeparator()
            menu.addAction("Свойства", lambda: self.show_properties(item))
            menu.addAction("Удалить", lambda: self.delete_experiment(item))
            
        elif item_type == 'folder':
            folder_name = item.text(0)
            if folder_name == "Видео" or folder_name == "Исходные видео":
                menu.addAction("Добавить видео", 
                              lambda: self.add_video_to_folder(item))
                              
        elif item_type == 'video':
            menu.addAction("Открыть", lambda: self.open_video(item))
            menu.addAction("Обработать", lambda: self.process_video(item))
            menu.addSeparator()
            menu.addAction("Удалить", lambda: self.delete_file(item))
            
        elif item_type == 'data':
            menu.addAction("Открыть", lambda: self.open_data_file(item))
            menu.addAction("Экспорт", lambda: self.export_data(item))
            menu.addSeparator()
            menu.addAction("Удалить", lambda: self.delete_file(item))
            
        menu.exec_(self.tree.mapToGlobal(position))
        
    def on_item_double_clicked(self, item, column):
        """Обработка двойного клика"""
        item_type = item.data(0, Qt.UserRole + 1)
        
        if item_type == 'experiment':
            self.open_experiment_item(item)
        elif item_type == 'video':
            self.open_video(item)
        elif item_type == 'data':
            self.open_data_file(item)
            
    def open_experiment_item(self, item):
        """Открыть эксперимент"""
        exp_path = item.data(0, Qt.UserRole)
        self.experiment_selected.emit(exp_path)
        
        # Обновляем информацию
        self.update_info(item)
        
    def update_info(self, item):
        """Обновить информацию о выбранном элементе"""
        item_type = item.data(0, Qt.UserRole + 1)
        item_path = Path(item.data(0, Qt.UserRole))
        
        if item_type == 'experiment':
            with open(item_path / 'experiment.json', 'r') as f:
                metadata = json.load(f)
                
            info = f"<b>{metadata['name']}</b><br>"
            info += f"Создан: {metadata['created'][:10]}<br>"
            
            # Подсчитываем файлы
            video_count = len(list((item_path / 'videos').glob('*')))
            result_count = len(list((item_path / 'results').glob('*')))
            
            info += f"Видео: {video_count}, Результатов: {result_count}"
            
            self.info_label.setText(info)
            
        elif item_type == 'video':
            info = f"<b>{item_path.name}</b><br>"
            size = item_path.stat().st_size / (1024 * 1024)  # MB
            info += f"Размер: {size:.1f} МБ<br>"
            
            # Если есть соответствующий CSV
            csv_path = item_path.with_suffix('.csv')
            if csv_path.exists():
                info += "✓ Обработано"
            else:
                info += "✗ Не обработано"
                
            self.info_label.setText(info)
            
    def add_video_to_experiment(self, exp_item):
        """Добавить видео в эксперимент"""
        video_files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите видео файлы", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if video_files:
            exp_path = Path(exp_item.data(0, Qt.UserRole))
            videos_path = exp_path / 'raw_videos'
            
            import shutil
            for video_file in video_files:
                dest = videos_path / Path(video_file).name
                shutil.copy(video_file, dest)
                
            # Обновляем дерево
            self.load_experiments()
            
    def add_video_to_folder(self, folder_item):
        """Добавить видео в папку"""
        video_files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите видео файлы", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if video_files:
            folder_path = Path(folder_item.data(0, Qt.UserRole))
            
            import shutil
            for video_file in video_files:
                dest = folder_path / Path(video_file).name
                shutil.copy(video_file, dest)
                
            # Обновляем папку в дереве
            folder_item.takeChildren()
            self.add_files_to_folder(folder_item, folder_path)
            
    def open_video(self, item):
        """Открыть видео"""
        video_path = item.data(0, Qt.UserRole)
        self.video_selected.emit(video_path)
        
    def process_video(self, item):
        """Обработать видео"""
        video_path = item.data(0, Qt.UserRole)
        # Сигнал для обработки будет обработан в главном окне
        self.parent().parent().load_video(video_path)
        self.parent().parent().process_video()
        
    def rename_experiment(self, item):
        """Переименовать эксперимент"""
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(
            self, "Переименовать эксперимент",
            "Новое название:", text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            old_path = Path(item.data(0, Qt.UserRole))
            new_path = old_path.parent / new_name
            
            if new_path.exists():
                QMessageBox.warning(self, "Ошибка", 
                                  "Эксперимент с таким именем уже существует")
                return
                
            # Переименовываем папку
            old_path.rename(new_path)
            
            # Обновляем метаданные
            meta_file = new_path / 'experiment.json'
            with open(meta_file, 'r') as f:
                metadata = json.load(f)
            metadata['name'] = new_name
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            # Обновляем дерево
            self.load_experiments()
            
    def delete_experiment(self, item):
        """Удалить эксперимент"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить эксперимент '{item.text(0)}' и все его данные?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            exp_path = Path(item.data(0, Qt.UserRole))
            
            # Рекурсивно удаляем папку
            import shutil
            shutil.rmtree(exp_path)
            
            # Обновляем дерево
            self.load_experiments()
            
    def delete_file(self, item):
        """Удалить файл"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить файл '{item.text(0)}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            file_path = Path(item.data(0, Qt.UserRole))
            file_path.unlink()
            
            # Удаляем из дерева
            parent = item.parent()
            parent.removeChild(item)
            
    def import_results(self, exp_item):
        """Импортировать результаты в эксперимент"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите файлы результатов", "",
            "Data Files (*.csv *.xlsx *.json)"
        )
        
        if files:
            exp_path = Path(exp_item.data(0, Qt.UserRole))
            results_path = exp_path / 'results'
            
            import shutil
            for file in files:
                dest = results_path / Path(file).name
                shutil.copy(file, dest)
                
            # Обновляем дерево
            self.load_experiments()
            
    def show_properties(self, item):
        """Показать свойства эксперимента"""
        from .experiment_properties_dialog import ExperimentPropertiesDialog
        
        exp_path = Path(item.data(0, Qt.UserRole))
        dialog = ExperimentPropertiesDialog(exp_path, self)
        
        if dialog.exec_():
            # Обновляем дерево если были изменения
            self.load_experiments()
            
    def open_data_file(self, item):
        """Открыть файл данных"""
        file_path = Path(item.data(0, Qt.UserRole))
        
        # Определяем тип файла и открываем соответствующим образом
        if file_path.suffix == '.csv':
            # Можно открыть во встроенном просмотрщике или внешней программе
            os.startfile(str(file_path))  # Windows
            # subprocess.call(['open', str(file_path)])  # macOS
            # subprocess.call(['xdg-open', str(file_path)])  # Linux
            
    def export_data(self, item):
        """Экспорт данных"""
        file_path = Path(item.data(0, Qt.UserRole))
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как", str(file_path),
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if save_path:
            import shutil
            shutil.copy(file_path, save_path)
            
    def get_experiments(self):
        """Получить список экспериментов"""
        experiments = []
        
        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir() and (exp_dir / 'experiment.json').exists():
                experiments.append(exp_dir)
                
        return experiments