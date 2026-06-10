from PyQt5.QtCore import QObject, pyqtSignal
from typing import List, Optional
from editor.product_layout import ProductLayoutModel, LayoutPersistence


class ProductLayoutManager(QObject):
    layoutLoaded = pyqtSignal(object)
    layoutSaved = pyqtSignal(str)
    layoutApplied = pyqtSignal(object)
    productListChanged = pyqtSignal()

    _instance = None

    @staticmethod
    def instance(parent=None):
        if ProductLayoutManager._instance is None:
            ProductLayoutManager._instance = ProductLayoutManager.__new__(ProductLayoutManager)
            ProductLayoutManager._instance._do_init(parent)
        return ProductLayoutManager._instance

    def __init__(self, parent=None):
        pass

    def _do_init(self, parent=None):
        super(ProductLayoutManager, self).__init__(parent)
        self._current_layout: Optional[ProductLayoutModel] = None
        self._cache: dict = {}
        self._cached_names: List[str] = []

    @property
    def current_layout(self) -> Optional[ProductLayoutModel]:
        return self._current_layout

    def list_products(self, force_refresh=False) -> List[str]:
        if force_refresh or not self._cached_names:
            self._cached_names = LayoutPersistence.list_products()
        return self._cached_names

    def load_layout(self, product_name: str) -> Optional[ProductLayoutModel]:
        if product_name in self._cache:
            layout = self._cache[product_name]
        else:
            layout = LayoutPersistence.load_layout(product_name)
            if layout:
                self._cache[product_name] = layout
        if layout:
            self._current_layout = layout
            self.layoutLoaded.emit(layout)
        return layout

    def save_layout(self, layout: ProductLayoutModel) -> bool:
        ok = LayoutPersistence.save_layout(layout)
        if ok:
            self._cache[layout.product_name] = layout
            if self._current_layout and self._current_layout.product_name == layout.product_name:
                self._current_layout = layout
            self.layoutSaved.emit(layout.product_name)
            self._cached_names = LayoutPersistence.list_products()
            self.productListChanged.emit()
        return ok

    def delete_layout(self, product_name: str) -> bool:
        ok = LayoutPersistence.delete_layout(product_name)
        if ok:
            self._cache.pop(product_name, None)
            if self._current_layout and self._current_layout.product_name == product_name:
                self._current_layout = None
            self._cached_names = LayoutPersistence.list_products()
            self.productListChanged.emit()
        return ok

    def apply_layout(self, layout: ProductLayoutModel = None):
        target = layout or self._current_layout
        if target:
            self.layoutApplied.emit(target)

    def invalidate_cache(self, product_name: str = None):
        if product_name:
            self._cache.pop(product_name, None)
        else:
            self._cache.clear()
