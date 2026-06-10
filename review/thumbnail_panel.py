import os
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QToolButton, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont
from utils.image_utils import ImageUtils


@dataclass
class ThumbInfo:
    image_path: str
    thumb_path: str
    result: str  # "OK" / "NG"
    defect_count: int


class ThumbWidget(QWidget):
    THUMB_W = 108
    THUMB_H = 136

    def __init__(self, info: ThumbInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        center = QWidget()
        center.setFixedSize(self.THUMB_W, self.THUMB_H)
        layout = QVBoxLayout(center)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.img_label = QLabel()
        self.img_label.setFixedSize(self.THUMB_W - 8, 100)
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background-color: #1E1E1E; border-radius: 4px;")
        layout.addWidget(self.img_label, 1, Qt.AlignCenter)

        is_ng = self.info.result.lower() in ("failed", "ng")
        status_text = "NG" if is_ng else "OK"
        status_color = "#FF4D4F" if is_ng else "#52C41A"
        self.status_label = QLabel(status_text)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"color: {status_color}; font-size: 13px; font-weight: 700;"
            f"background: transparent; padding: 0px;"
        )
        layout.addWidget(self.status_label)

        outer.addWidget(center, 0, Qt.AlignCenter)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cw = self.width()
        ch = self.height()
        if self._selected:
            p.setPen(QPen(QColor("#409EFF"), 3))
            p.setBrush(QColor(64, 158, 255, 25))
        else:
            p.setPen(QPen(QColor("#3A3D41"), 1))
            p.setBrush(QColor("#2D2D30"))
        p.drawRoundedRect(1, 1, cw - 2, ch - 2, 8, 8)
        p.end()


class ThumbnailPanel(QWidget):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._infos: List[ThumbInfo] = []
        self._current_idx = 0
        self.setFixedWidth(150)
        self.setStyleSheet("background-color: #252526; border-radius: 6px;")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.btn_prev = QToolButton()
        self.btn_prev.setText("▲ 上一张")
        self.btn_prev.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_prev.setStyleSheet(
            "QToolButton{background:#3A3D41;color:#CCCCCC;padding:6px;border-radius:4px;font-size:12px;font-weight:600;}"
            "QToolButton:hover{background:#4A4D51;}"
        )
        self.btn_prev.clicked.connect(self.go_prev)
        self.btn_prev.setEnabled(False)
        layout.addWidget(self.btn_prev)

        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(
            "QListWidget{background:#252526;border:none;outline:none;padding:0px;margin:0px;}"
            "QListWidget::item{background:transparent;border:none;padding:0px;margin:0px;}"
        )
        self.list_widget.setSpacing(8)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, 1)

        self.btn_next = QToolButton()
        self.btn_next.setText("▼ 下一张")
        self.btn_next.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_next.setStyleSheet(
            "QToolButton{background:#3A3D41;color:#CCCCCC;padding:6px;border-radius:4px;font-size:12px;font-weight:600;}"
            "QToolButton:hover{background:#4A4D51;}"
        )
        self.btn_next.clicked.connect(self.go_next)
        self.btn_next.setEnabled(False)
        layout.addWidget(self.btn_next)

    def set_items(self, infos: List[ThumbInfo]):
        self._infos = infos
        self.list_widget.clear()
        self.list_widget.updateGeometry()
        list_w = max(self.list_widget.viewport().width(), ThumbWidget.THUMB_W)
        for info in infos:
            tw = ThumbWidget(info)
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(list_w, ThumbWidget.THUMB_H + 4))
            self.list_widget.setItemWidget(item, tw)
            self._load_thumb(tw, info)
        self._current_idx = 0
        self._update_selection()
        self.btn_prev.setEnabled(len(infos) > 1)
        self.btn_next.setEnabled(len(infos) > 1)

    def _load_thumb(self, tw: ThumbWidget, info: ThumbInfo):
        path = info.thumb_path if os.path.exists(info.thumb_path) else info.image_path
        if os.path.exists(path):
            try:
                img = ImageUtils.load_image(path)
                if img is not None:
                    h, w = img.shape[:2]
                    if len(img.shape) == 3:
                        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    else:
                        rgb = img
                    tw_w = ThumbWidget.THUMB_W - 8
                    th = 100
                    scale = min(tw_w / w, th / h)
                    nw, nh = int(w * scale), int(h * scale)
                    resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
                    qimg = QImage(resized.data, nw, nh, 3 * nw, QImage.Format_RGB888)
                    pix = QPixmap.fromImage(qimg)
                    tw.img_label.setPixmap(pix)
                    tw.img_label.setAlignment(Qt.AlignCenter)
                    return
            except Exception:
                pass
        tw.img_label.setText("无图")

    def _update_selection(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if isinstance(w, ThumbWidget):
                w.set_selected(i == self._current_idx)

    def _on_item_clicked(self, item):
        row = self.list_widget.row(item)
        if row != self._current_idx:
            self._current_idx = row
            self._update_selection()
            self.list_widget.scrollToItem(item)
            self.currentIndexChanged.emit(row)

    def go_prev(self):
        if self._current_idx > 0:
            self._current_idx -= 1
            self._update_selection()
            item = self.list_widget.item(self._current_idx)
            self.list_widget.scrollToItem(item)
            self.currentIndexChanged.emit(self._current_idx)

    def go_next(self):
        if self._current_idx < len(self._infos) - 1:
            self._current_idx += 1
            self._update_selection()
            item = self.list_widget.item(self._current_idx)
            self.list_widget.scrollToItem(item)
            self.currentIndexChanged.emit(self._current_idx)

    @property
    def current_index(self) -> int:
        return self._current_idx

    def set_current_index(self, idx: int):
        if 0 <= idx < len(self._infos):
            self._current_idx = idx
            self._update_selection()
            item = self.list_widget.item(idx)
            if item:
                self.list_widget.scrollToItem(item)
