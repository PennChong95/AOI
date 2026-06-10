import os
import json
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QUrl, Qt


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "templates")
ECHARTS_JS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "echarts", "echarts.min.js")

TEMPLATE_MAP = {
    "line": "line_chart.html",
    "bar": "bar_chart.html",
    "pareto": "pareto_chart.html",
    "heatmap": "heatmap_chart.html",
    "sankey": "sankey_chart.html",
    "matrix": "matrix_chart.html",
}

ECHARTS_JS_CONTENT = None


def _load_echarts_js():
    global ECHARTS_JS_CONTENT
    if ECHARTS_JS_CONTENT is None:
        with open(ECHARTS_JS_PATH, "r", encoding="utf-8") as f:
            ECHARTS_JS_CONTENT = f.read()
    return ECHARTS_JS_CONTENT


def _load_template_html(chart_type: str) -> str:
    template_file = TEMPLATE_MAP.get(chart_type, "bar_chart.html")
    template_path = os.path.join(TEMPLATE_DIR, template_file)
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()
    echarts_js = _load_echarts_js()
    html = html.replace('<script src="../echarts/echarts.min.js"></script>',
                        f"<script>{echarts_js}</script>")
    return html


def _ensure_js(items):
    if isinstance(items, np.integer):
        return int(items)
    if isinstance(items, np.floating):
        return float(items)
    if isinstance(items, (list, tuple)):
        return [_ensure_js(i) for i in items]
    if isinstance(items, dict):
        return {k: _ensure_js(v) for k, v in items.items()}
    return items


def _json_dumps(obj):
    return json.dumps(_ensure_js(obj), ensure_ascii=False)


class EChartWidget(QWidget):
    def __init__(self, chart_type: str = "bar", title: str = "", parent=None):
        super().__init__(parent)
        self._chart_type = chart_type
        self._title = title
        self._loaded = False
        self._pending_data = None
        self._webview = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if self._title:
            lbl = QLabel(self._title)
            lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E293B;")
            layout.addWidget(lbl)

        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            self._webview = QWebEngineView()
            self._webview.setStyleSheet("border: 1px solid #E2E8F0; border-radius: 6px;")
            self._webview.setMinimumHeight(150)
            self._webview.loadFinished.connect(self._on_load_finished)

            html = _load_template_html(self._chart_type)
            self._webview.setHtml(html, QUrl("about:blank"))

            layout.addWidget(self._webview, 1)
        except ImportError as e:
            fallback = QLabel(f"ECharts 组件加载失败\n\n请重启应用后重试\n\n({e})")
            fallback.setStyleSheet(
                "border: 1px solid #E2E8F0; border-radius: 6px; padding: 24px;"
                "color: #94A3B8; font-size: 12px; background: #F8FAFC;"
            )
            fallback.setAlignment(Qt.AlignCenter)
            layout.addWidget(fallback, 1)
        except Exception as e:
            fallback = QLabel(f"图表渲染失败: {e}")
            fallback.setStyleSheet(
                "border: 1px solid #EF4444; border-radius: 6px; padding: 24px;"
                "color: #EF4444; font-size: 12px; background: #FEF2F2;"
            )
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setWordWrap(True)
            layout.addWidget(fallback, 1)

    def _on_load_finished(self, ok: bool):
        self._loaded = ok
        if ok and self._pending_data is not None and self._webview:
            json_str = self._pending_data
            self._pending_data = None
            self._inject_chart(json_str)

    def _inject_chart(self, json_str: str):
        if not self._webview:
            return
        js = f"renderChart('{json_str}');"
        self._webview.page().runJavaScript(js)

    def set_data(self, data: dict):
        json_str = _json_dumps(data)
        json_str = json_str.replace("\\", "\\\\").replace("'", "\\'")
        if not self._webview:
            return
        if not self._loaded:
            self._pending_data = json_str
        else:
            self._inject_chart(json_str)

    def set_title(self, title: str):
        self._title = title

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._loaded and self._webview:
            self._webview.page().runJavaScript("if(typeof chart!=='undefined'&&chart.resize){chart.resize();}")


class LineEChart(EChartWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__("line", title, parent)

    def set_data(self, x_data: list, series: list, smooth: bool = True, fill: bool = False, colors: list = None):
        super().set_data({
            "xData": x_data,
            "series": series,
            "smooth": smooth,
            "fill": fill,
        })


class BarEChart(EChartWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__("bar", title, parent)

    def set_data(self, labels: list, values: list, colors: list = None, orient: str = "vertical", series_name: str = ""):
        super().set_data({
            "labels": labels,
            "values": values,
            "colors": colors,
            "orient": orient,
            "seriesName": series_name,
        })


class ParetoEChart(EChartWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__("pareto", title, parent)

    def set_data(self, labels: list, values: list):
        super().set_data({
            "labels": labels,
            "values": values,
        })


class HeatmapEChart(EChartWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__("heatmap", title, parent)

    def set_data(self, items: list, x_labels: list = None, y_labels: list = None):
        max_val = max((it["value"] for it in items), default=1)
        super().set_data({
            "items": items,
            "xLabels": x_labels or [],
            "yLabels": y_labels or [],
            "maxValue": max_val,
        })


class SankeyEChart(EChartWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__("sankey", title, parent)

    def set_data(self, nodes: list, links: list):
        super().set_data({
            "nodes": nodes,
            "links": links,
        })


class MatrixEChart(EChartWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__("matrix", title, parent)

    def set_data(self, data_2d: list, x_labels: list, y_labels: list):
        super().set_data({
            "data": data_2d,
            "xLabels": x_labels,
            "yLabels": y_labels,
        })
