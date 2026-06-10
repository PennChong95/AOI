from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPainterPath, QPainterPathStroker
from PyQt5.QtCore import Qt


def hit_test_rectangle(point: QPointF, rect: QRectF) -> bool:
    return (rect.left() <= point.x() <= rect.right()
            and rect.top() <= point.y() <= rect.bottom())


def hit_test_circle(point: QPointF, center: QPointF, radius: float) -> bool:
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    distance_squared = dx * dx + dy * dy
    return distance_squared <= radius * radius


def hit_test_polygon(point: QPointF, vertices: list) -> bool:
    if not vertices or len(vertices) < 3:
        return False
    n = len(vertices)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i].x(), vertices[i].y()
        xj, yj = vertices[j].x(), vertices[j].y()
        if ((yi > point.y()) != (yj > point.y())) and (point.x() < (xj - xi) * (point.y() - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def hit_test_ring(point: QPointF, center: QPointF, outer_radius: float, inner_radius: float) -> bool:
    dx = point.x() - center.x()
    dy = point.y() - center.y()
    d2 = dx * dx + dy * dy
    return d2 <= outer_radius * outer_radius and d2 >= inner_radius * inner_radius


def hit_test_arc(point: QPointF, bounding_rect: QRectF, start_angle: float, span_angle: float, thickness: float) -> bool:
    path = QPainterPath()
    path.arcMoveTo(bounding_rect, start_angle)
    path.arcTo(bounding_rect, start_angle, span_angle)
    stroker = QPainterPathStroker()
    stroker.setWidth(max(1, thickness))
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    stroked = stroker.createStroke(path)
    return stroked.contains(point)
