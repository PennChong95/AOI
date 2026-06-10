"""
UI样式定义
使用统一的主题系统
"""

from ui.theme import Theme

# 导出新的样式函数
__all__ = ['DASHBOARD_STYLE', 'get_dashboard_style', 'get_sidebar_style']

# 保持向后兼容
DASHBOARD_STYLE = Theme.get_color.__doc__  # 这个会被实际调用时替换

def get_dashboard_style():
    """获取看板主样式"""
    from ui.theme import get_dashboard_style as _get_style
    return _get_style()

def get_sidebar_style():
    """获取侧边栏样式"""
    from ui.theme import get_sidebar_style as _get_style
    return _get_style()
