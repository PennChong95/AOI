import re
from PyQt5.QtWidgets import QApplication

SCALE_FACTOR = 1.0


def compute_scale_factor(ref_width=1920, ref_height=1080, min_factor=0.7, max_factor=1.0):
    app = QApplication.instance()
    if not app:
        return 1.0
    screen = app.primaryScreen()
    if not screen:
        return 1.0
    w = screen.size().width()
    h = screen.size().height()
    factor = min(w / ref_width, h / ref_height, max_factor)
    factor = max(factor, min_factor)
    return factor


def init_scale_factor():
    global SCALE_FACTOR
    SCALE_FACTOR = compute_scale_factor()


def sf():
    return SCALE_FACTOR


def sp(val):
    return max(1, round(val * SCALE_FACTOR))


def scale_css(css):
    factor = SCALE_FACTOR
    if factor >= 1.0:
        return css

    def _replace_size(m):
        val = int(m.group(1))
        return f"font-size: {sp(val)}px"

    css = re.sub(r'font-size:\s*(\d+)px', _replace_size, css)

    def _replace_pad(m):
        full = m.group(0)
        vals = re.findall(r'\d+', full)
        parts = m.group(1)
        for v in vals:
            parts = parts.replace(v, str(sp(int(v))), 1)
        return f"{m.group(2)}: {parts}"

    for prop in ('padding', 'margin', 'min-height', 'min-width', 'border-radius', 'max-height', 'max-width'):
        css = re.sub(rf'({prop}):\s*([\d\sA-Za-z%]+?)(?=[;}}])', _replace_pad, css)

    return css
