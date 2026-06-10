"""
基于matplotlib的图表组件
替代ECharts，提供原生PyQt5图表显示
"""

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


# 统一配色方案
CHART_COLORS = [
    '#3B82F6',  # 蓝色
    '#8B5CF6',  # 紫色
    '#10B981',  # 绿色
    '#F59E0B',  # 黄色
    '#EF4444',  # 红色
    '#EC4899',  # 粉色
    '#06B6D4',  # 青色
    '#F97316',  # 橙色
    '#84CC16',  # 青柠
    '#64748B',  # 灰色
]

# 语义颜色
COLOR_PRIMARY = '#3B82F6'
COLOR_SUCCESS = '#10B981'
COLOR_DANGER = '#EF4444'
COLOR_WARNING = '#F59E0B'
COLOR_INFO = '#06B6D4'

# 背景色
BG_PRIMARY = '#F8FAFC'
BG_CARD = '#FFFFFF'

# 文字色
TEXT_PRIMARY = '#1E293B'
TEXT_SECONDARY = '#475569'
TEXT_MUTED = '#94A3B8'

# 边框色
BORDER = '#E2E8F0'
BORDER_LIGHT = '#F1F5F9'


def setup_matplotlib_style():
    """设置matplotlib全局样式"""
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['figure.facecolor'] = 'none'
    plt.rcParams['axes.facecolor'] = 'none'
    plt.rcParams['savefig.facecolor'] = 'none'


setup_matplotlib_style()


class BaseChartWidget(QWidget):
    """图表基类"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._setup_ui()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建matplotlib画布
        self._figure = Figure(dpi=100)
        self._figure.set_facecolor('none')
        
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setStyleSheet(f"""
            background: transparent;
            border: none;
        """)
        
        layout.addWidget(self._canvas)
        
        # 创建子图
        self._ax = self._figure.add_subplot(111)
        self._setup_axes()
    
    def _setup_axes(self):
        """设置坐标轴样式"""
        self._ax.set_facecolor('none')
        
        # 设置边框样式
        for spine in self._ax.spines.values():
            spine.set_color(BORDER)
            spine.set_linewidth(0.5)
        
        # 设置网格
        self._ax.grid(True, axis='y', color=BORDER_LIGHT, linestyle='-', linewidth=0.5, alpha=0.8)
        self._ax.set_axisbelow(True)
        
        # 设置刻度
        self._ax.tick_params(axis='both', colors=TEXT_MUTED, labelsize=9)
    
    def clear(self):
        """清除图表"""
        self._figure.clear()
        self._ax = self._figure.add_subplot(111)
        self._setup_axes()
    
    def refresh(self):
        """刷新画布"""
        self._figure.tight_layout()
        self._canvas.draw_idle()
    
    def resizeEvent(self, event):
        """窗口大小变化时重新绘制"""
        super().resizeEvent(event)
        if hasattr(self, '_canvas'):
            # 调整Figure大小以匹配widget大小
            width = event.size().width()
            height = event.size().height()
            if width > 0 and height > 0:
                dpi = self._figure.dpi
                self._figure.set_size_inches(width / dpi, height / dpi)
            self._canvas.draw_idle()


class LineChart(BaseChartWidget):
    """折线图组件"""
    
    def set_data(self, x_data: list, series: list, smooth: bool = True, fill: bool = False):
        """
        设置折线图数据
        
        Args:
            x_data: x轴数据
            series: 数据系列列表，每个元素为 {"name": str, "data": list}
            smooth: 是否平滑
            fill: 是否填充
        """
        self.clear()
        
        if not x_data or not series:
            self.refresh()
            return
        
        for i, s in enumerate(series):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            y_data = s.get("data", [])
            name = s.get("name", "")
            
            if smooth and len(x_data) >= 3 and len(y_data) >= 3:
                try:
                    from scipy.interpolate import make_interp_spline
                    k = min(3, len(x_data) - 1)
                    x_smooth = np.linspace(0, len(x_data) - 1, 300)
                    spl = make_interp_spline(range(len(x_data)), y_data, k=k)
                    y_smooth = spl(x_smooth)
                    
                    self._ax.plot(x_smooth, y_smooth, color=color, linewidth=2.5, label=name)
                    
                    if fill:
                        self._ax.fill_between(x_smooth, y_smooth, alpha=0.1, color=color)
                except Exception:
                    self._ax.plot(range(len(x_data)), y_data, color=color, linewidth=2.5,
                                 marker='o', markersize=4, label=name)
                    if fill:
                        self._ax.fill_between(range(len(x_data)), y_data, alpha=0.1, color=color)
                else:
                    self._ax.plot(range(len(x_data)), y_data, 'o', color=color, markersize=5,
                                 markerfacecolor=color, markeredgecolor='white', markeredgewidth=1,
                                 zorder=5)
            else:
                self._ax.plot(range(len(x_data)), y_data, color=color, linewidth=2.5,
                             marker='o', markersize=5, label=name,
                             markerfacecolor=color, markeredgecolor='white', markeredgewidth=1)
                if fill:
                    self._ax.fill_between(range(len(x_data)), y_data, alpha=0.1, color=color)
            
            # 在每个数据点上显示数值
            for xi, yi in zip(range(len(x_data)), y_data):
                self._ax.annotate(f'{yi:.1f}', (xi, yi),
                                 textcoords="offset points", xytext=(0, 12),
                                 ha='center', va='bottom', fontsize=8,
                                 color=color, fontweight='bold')
        
        # 设置x轴标签
        if len(x_data) <= 10:
            self._ax.set_xticks(range(len(x_data)))
            self._ax.set_xticklabels(x_data, rotation=0, ha='center')
        else:
            step = max(1, len(x_data) // 8)
            indices = range(0, len(x_data), step)
            self._ax.set_xticks(indices)
            self._ax.set_xticklabels([x_data[i] for i in indices], rotation=30, ha='right')
        
        # 自适应y轴范围：让数据变化更明显
        all_values = [v for s in series for v in s.get("data", [])]
        if all_values:
            y_min, y_max = min(all_values), max(all_values)
            if y_min != y_max:
                margin = (y_max - y_min) * 0.15
                self._ax.set_ylim(max(0, y_min - margin), y_max + margin)
        
        # 设置图例
        if len(series) > 1:
            self._ax.legend(loc='upper right', frameon=True, facecolor=BG_CARD,
                           edgecolor=BORDER, fontsize=9)
        
        self.refresh()


class BarChart(BaseChartWidget):
    """柱状图组件"""

    drilldown_triggered = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pick_connected = False

    def _ensure_pick(self):
        if not self._pick_connected:
            self._canvas.mpl_connect('pick_event', self._on_pick)
            self._pick_connected = True

    def _on_pick(self, event):
        if event.artist:
            label = event.artist.get_gid()
            if label:
                self.drilldown_triggered.emit(label)
                bar = event.artist
                bar.set_edgecolor('#3B82F6')
                bar.set_linewidth(2)
                self._canvas.draw_idle()
                QTimer.singleShot(400, lambda: self._restore_bar(bar))

    def _restore_bar(self, bar):
        try:
            if bar.axes is not None:
                bar.set_edgecolor('none')
                bar.set_linewidth(0)
                self._canvas.draw_idle()
        except (AttributeError, RuntimeError, ValueError):
            pass

    def set_data(self, labels: list, values: list, colors: list = None, 
                 orient: str = "vertical", series_name: str = ""):
        """
        设置柱状图数据
        
        Args:
            labels: 标签列表
            values: 值列表
            colors: 颜色列表
            orient: 方向，vertical或horizontal
            series_name: 系列名称
        """
        self.clear()
        
        if not labels or not values:
            self.refresh()
            return
        
        if colors is None:
            colors = CHART_COLORS[:len(labels)]
        
        x = np.arange(len(labels))
        
        if orient == "horizontal":
            # 水平柱状图
            bars = self._ax.barh(x, values, height=0.6, color=colors, 
                                edgecolor='none', alpha=0.9)
            
            # 添加数值标签
            for bar, val in zip(bars, values):
                self._ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height()/2,
                             f'{val:.1f}' if isinstance(val, float) else f'{val:,}',
                             va='center', ha='left', color=TEXT_SECONDARY, fontsize=9)
            
            self._ax.set_yticks(x)
            self._ax.set_yticklabels(labels, fontsize=9)
            self._ax.invert_yaxis()
            
            # 隐藏y轴刻度线
            self._ax.tick_params(axis='y', length=0)
            
        else:
            # 垂直柱状图
            bars = self._ax.bar(x, values, width=0.6, color=colors,
                               edgecolor='none', alpha=0.9)
            
            # 添加数值标签
            for bar, val in zip(bars, values):
                self._ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.02,
                             f'{val:.1f}' if isinstance(val, float) else f'{val:,}',
                             ha='center', va='bottom', color=TEXT_SECONDARY, fontsize=9)
            
            if len(labels) <= 10:
                self._ax.set_xticks(x)
                self._ax.set_xticklabels(labels, rotation=0, ha='center', fontsize=9)
            else:
                self._ax.set_xticks(x)
                self._ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
            
            # 隐藏x轴刻度线
            self._ax.tick_params(axis='x', length=0)

        for bar, lb in zip(bars, labels):
            bar.set_picker(True)
            bar.set_gid(lb)
        
        self._ensure_pick()
        self.refresh()


class ParetoChart(BaseChartWidget):
    """Pareto图组件"""
    
    def set_data(self, labels: list, values: list, show_80_line: bool = True):
        """
        设置Pareto图数据
        
        Args:
            labels: 标签列表
            values: 值列表
            show_80_line: 是否显示80%参考线
        """
        self.clear()
        
        if not labels or not values:
            self.refresh()
            return
        
        x = np.arange(len(labels))
        colors = CHART_COLORS[:len(labels)]
        
        # 柱状图
        bars = self._ax.bar(x, values, width=0.6, color=colors,
                           edgecolor='none', alpha=0.9, label='缺陷数')
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            self._ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values) * 0.02,
                         f'{val:,}',
                         ha='center', va='bottom', color=TEXT_SECONDARY, fontsize=8)
        
        # 计算累计百分比
        total = sum(values)
        cum_pct = []
        running_sum = 0
        for v in values:
            running_sum += v
            cum_pct.append(running_sum / total * 100)
        
        # 创建第二个y轴
        ax2 = self._ax.twinx()
        ax2.plot(x, cum_pct, color=COLOR_DANGER, linewidth=2.5, marker='o', 
                markersize=6, label='累计占比')
        
        # 添加百分比标签
        for i, pct in enumerate(cum_pct):
            ax2.annotate(f'{pct:.1f}%', (x[i], pct), textcoords="offset points",
                        xytext=(0, 10), ha='center', va='bottom', 
                        color=COLOR_DANGER, fontsize=8, fontweight='bold')
        
        # 添加80%参考线
        if show_80_line:
            ax2.axhline(y=80, color='#F59E0B', linewidth=2, linestyle='--', alpha=0.8, label='80%分界线')
        
        # 设置样式
        self._ax.set_xticks(x)
        self._ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=9)
        self._ax.tick_params(axis='x', length=0)
        
        # 设置y轴
        self._ax.set_ylabel('数量', color=TEXT_MUTED, fontsize=10)
        self._ax.tick_params(axis='y', colors=TEXT_MUTED)
        
        ax2.set_ylabel('累计占比 (%)', color=COLOR_DANGER, fontsize=10)
        ax2.set_ylim(0, 105)
        ax2.tick_params(axis='y', colors=COLOR_DANGER)
        
        # 设置图例（放在图表下方）
        lines1, labels1 = self._ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        self._ax.legend(lines1 + lines2, labels1 + labels2, loc='lower center',
                       bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=True,
                       facecolor=BG_CARD, edgecolor=BORDER, fontsize=8)

        self._figure.subplots_adjust(top=0.88)
        self._canvas.draw_idle()


class HeatmapChart(BaseChartWidget):
    """热力图组件"""
    
    def set_data(self, items: list, x_labels: list = None, y_labels: list = None):
        """
        设置热力图数据
        
        Args:
            items: 数据项列表，每个元素为 {"x": int, "y": int, "value": float, "label": str}
            x_labels: x轴标签
            y_labels: y轴标签
        """
        self.clear()
        
        if not items:
            self.refresh()
            return
        
        # 构建矩阵
        if x_labels and y_labels:
            rows = len(y_labels)
            cols = len(x_labels)
        else:
            max_x = max(item["x"] for item in items) + 1
            max_y = max(item["y"] for item in items) + 1
            rows, cols = max_y, max_x
        
        data = np.zeros((rows, cols))
        labels = [['' for _ in range(cols)] for _ in range(rows)]
        
        for item in items:
            x, y = item["x"], item["y"]
            if 0 <= x < cols and 0 <= y < rows:
                data[y][x] = item["value"]
                labels[y][x] = item.get("label", "")
        
        # 绘制热力图
        im = self._ax.imshow(data, cmap='Blues', aspect='auto', interpolation='nearest')
        
        # 添加颜色条
        cbar = self._figure.colorbar(im, ax=self._ax, shrink=0.8)
        cbar.ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        
        # 添加数值和标签
        for i in range(rows):
            for j in range(cols):
                if data[i][j] > 0:
                    # 根据背景颜色选择文字颜色
                    text_color = 'white' if data[i][j] > data.max() * 0.6 else TEXT_PRIMARY
                    
                    # 显示标签
                    if labels[i][j]:
                        self._ax.text(j, i - 0.15, labels[i][j], ha='center', va='center',
                                     color=text_color, fontsize=8, fontweight='bold')
                    
                    # 显示数值
                    self._ax.text(j, i + 0.2, f'{int(data[i][j])}', ha='center', va='center',
                                 color=text_color, fontsize=7)
        
        # 设置坐标轴
        if x_labels:
            self._ax.set_xticks(range(len(x_labels)))
            self._ax.set_xticklabels(x_labels, fontsize=8)
        
        if y_labels:
            self._ax.set_yticks(range(len(y_labels)))
            self._ax.set_yticklabels(y_labels, fontsize=8)
        
        # 隐藏刻度线
        self._ax.tick_params(length=0)
        
        self.refresh()


class PieChart(BaseChartWidget):
    """环形图组件"""

    drilldown_triggered = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pick_connected = False

    def _ensure_pick(self):
        if not self._pick_connected:
            self._canvas.mpl_connect('pick_event', self._on_pick)
            self._pick_connected = True

    def _on_pick(self, event):
        if event.artist:
            label = event.artist.get_gid()
            if label:
                self.drilldown_triggered.emit(label)
                wedge = event.artist
                wedge.set_edgecolor('#3B82F6')
                wedge.set_linewidth(3)
                self._canvas.draw_idle()
                QTimer.singleShot(400, lambda: self._restore_wedge(wedge))

    def _restore_wedge(self, wedge):
        try:
            if wedge.axes is not None:
                wedge.set_edgecolor('white')
                wedge.set_linewidth(2)
                self._canvas.draw_idle()
        except (AttributeError, RuntimeError, ValueError):
            pass

    def set_data(self, labels: list, values: list, colors: list = None, show_percent: bool = True):
        """
        设置环形图数据
        
        Args:
            labels: 标签列表
            values: 值列表
            colors: 颜色列表
            show_percent: 是否显示百分比
        """
        self._figure.clear()
        self._ax = None
        
        if not labels or not values:
            self.refresh()
            return
        
        if colors is None:
            colors = CHART_COLORS[:len(labels)]
        
        gs = self._figure.add_gridspec(1, 2, width_ratios=[6, 4], wspace=0.15)
        ax_pie = self._figure.add_subplot(gs[0, 0])
        ax_legend = self._figure.add_subplot(gs[0, 1])
        self._ax = ax_pie
        
        ax_pie.set_facecolor('none')
        ax_legend.set_facecolor('none')
        
        wedges, texts, autotexts = ax_pie.pie(
            values,
            labels=None,
            colors=colors,
            autopct='%1.1f%%' if show_percent else None,
            startangle=90,
            pctdistance=0.75,
            wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
        )
        
        for w, lb in zip(wedges, labels):
            w.set_picker(True)
            w.set_gid(lb)
        
        if autotexts:
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_fontweight('bold')
        
        ax_pie.set_aspect('equal')
        
        total = sum(values)
        ax_pie.text(0, 0, f"{total}\n总计", ha='center', va='center',
                    fontsize=12, fontweight='bold', color='#475569')
        
        ax_legend.axis('off')
        legend_labels = [f"{l}  {v/total*100:.1f}%" for l, v in zip(labels, values)]
        legend = ax_legend.legend(
            wedges, legend_labels,
            loc='center left',
            fontsize=9,
            frameon=False,
            ncol=1,
        )
        for text in legend.get_texts():
            text.set_color('#1E293B')
        
        self._figure.subplots_adjust(left=0, right=0.85, top=0.9, bottom=0.1)
        self._ensure_pick()
        self._canvas.draw_idle()


# 兼容性别名，保持与原ECharts组件相同的接口
LineEChart = LineChart
BarEChart = BarChart
ParetoEChart = ParetoChart
HeatmapEChart = HeatmapChart
PieEChart = PieChart
