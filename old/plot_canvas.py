# plot_canvas.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class PlotCanvas(QWidget):
    """
    Виджет для отображения графиков Matplotlib в PyQt.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot(self, df):
        """
        Отрисовка данных из DataFrame.
        Создает 4 сублота для площадей и 4 для длин.
        """
        self.figure.clear()

        if df.empty:
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Нет данных для отображения', horizontalalignment='center', verticalalignment='center')
            self.canvas.draw()
            return
            
        paw_names = ['lf', 'rf', 'lb', 'rb']
        paw_titles = {'lf': 'ЛП', 'rf': 'ПП', 'lb': 'ЛЗ', 'rb': 'ПЗ'}

        # Графики площадей
        for i, paw in enumerate(paw_names):
            ax = self.figure.add_subplot(4, 2, 2 * i + 1)
            col_name = f'{paw}_area_px'
            if col_name in df.columns:
                ax.plot(df['frame'], df[col_name], label='Площадь')
            ax.set_title(f"Площадь, {paw_titles[paw]} (пикс²)")
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.tick_params(axis='x', labelbottom=False) # Убираем подписи оси X для экономии места

        # Графики длин
        for i, paw in enumerate(paw_names):
            ax = self.figure.add_subplot(4, 2, 2 * i + 2)
            col_name = f'{paw}_length_px'
            if col_name in df.columns:
                ax.plot(df['frame'], df[col_name], color='orange', label='Длина')
            ax.set_title(f"Длина, {paw_titles[paw]} (пикс)")
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.tick_params(axis='x', labelbottom=False)

        # Добавляем подпись оси X к последним графикам
        self.figure.get_axes()[-1].tick_params(axis='x', labelbottom=True)
        self.figure.get_axes()[-2].tick_params(axis='x', labelbottom=True)
        self.figure.get_axes()[-1].set_xlabel("Кадр")
        self.figure.get_axes()[-2].set_xlabel("Кадр")
        
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()