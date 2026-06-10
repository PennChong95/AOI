import os
import struct
import threading
import time
from typing import Optional, Callable, Dict, List
import sys
from PyQt5.QtCore import QObject, pyqtSignal
import base64

ZKFP_ERR_OK = 0
ZKFP_ERR_ALREADY_INIT = 1
ZKFP_ERR_INITLIB = -1
ZKFP_ERR_INIT = -2
ZKFP_ERR_NO_DEVICE = -3
ZKFP_ERR_NOT_SUPPORT = -4
ZKFP_ERR_INVALID_PARAM = -5
ZKFP_ERR_OPEN = -6
ZKFP_ERR_INVALID_HANDLE = -7
ZKFP_ERR_CAPTURE = -8
ZKFP_ERR_EXTRACT_FP = -9
ZKFP_ERR_ABSORT = -10
ZKFP_ERR_MEMORY_NOT_ENOUGH = -11
ZKFP_ERR_BUSY = -12
ZKFP_ERR_ADD_FINGER = -13
ZKFP_ERR_DEL_FINGER = -14
ZKFP_ERR_FAIL = -17
ZKFP_ERR_CANCEL = -18
ZKFP_ERR_VERIFY_FP = -20
ZKFP_ERR_MERGE = -22
ZKFP_ERR_NOT_OPENED = -23
ZKFP_ERR_NOT_INIT = -24
ZKFP_ERR_ALREADY_OPENED = -25
ZKFP_ERR_LOADIMAGE = -26
ZKFP_ERR_ANALYSE_IMG = -27
ZKFP_ERR_TIMEOUT = -28


class _NetFingerprintService:
    def __init__(self):
        self._dev_handle = None
        self._db_handle = None
        self._initialized = False
        self._device_open = False
        self._lock = threading.Lock()
        self.image_width = 0
        self.image_height = 0
        self._net_module = None
        self._err_module = None
        self._dll_path = None

        self.fid_user_map: Dict[int, str] = {}
        self.next_fid: int = 1

    def _load_assembly(self) -> bool:
        dll_name = "libzkfpcsharp.dll"
        search_paths = [
            os.path.join(os.path.dirname(__file__), "..", "Fingerprint Login", "c#", "WindowsFormsApp2", "bin", "Debug", dll_name),
            os.path.join(os.path.dirname(__file__), "..", "Fingerprint Login", "c#", "WindowsFormsApp2", "bin", "Release", dll_name),
            os.path.join(os.path.dirname(sys.executable), "_internal", dll_name),
            os.path.join(os.path.dirname(sys.executable), dll_name),
            os.path.join(os.getcwd(), dll_name),
            dll_name,
        ]
        if hasattr(sys, '_MEIPASS'):
            search_paths.insert(0, os.path.join(sys._MEIPASS, dll_name))
        for p in search_paths:
            full = os.path.abspath(p)
            if os.path.exists(full):
                self._dll_path = full
                break
        if not self._dll_path:
            return False

        try:
            import clr
            import importlib
            dll_dir = os.path.dirname(self._dll_path)
            if dll_dir not in sys.path:
                sys.path.insert(0, dll_dir)
            clr.AddReference(self._dll_path)
            mod = importlib.import_module(os.path.splitext(os.path.basename(self._dll_path))[0])
            self._net_module = mod.zkfp2
            self._err_module = mod.zkfperrdef
            return True
        except Exception:
            return False

    def init(self) -> int:
        if self._initialized:
            return ZKFP_ERR_OK
        if not self._load_assembly():
            return ZKFP_ERR_NO_DEVICE
        try:
            ret = self._net_module.Init()
            if ret == self._err_module.ZKFP_ERR_OK or ret == self._err_module.ZKFP_ERR_ALREADY_INIT:
                self._initialized = True
                return ZKFP_ERR_OK
            return ret
        except Exception:
            return ZKFP_ERR_NO_DEVICE

    def terminate(self):
        with self._lock:
            if self._device_open and self._dev_handle is not None:
                try:
                    self._net_module.CloseDevice(self._dev_handle)
                except Exception:
                    pass
                self._device_open = False
                self._dev_handle = None
            if self._db_handle is not None:
                try:
                    self._net_module.DBFree(self._db_handle)
                except Exception:
                    pass
                self._db_handle = None
            if self._initialized:
                try:
                    self._net_module.Terminate()
                except Exception:
                    pass
                self._initialized = False
            self.fid_user_map.clear()
            self.next_fid = 1

    def get_device_count(self) -> int:
        if not self._initialized or not self._net_module:
            return 0
        try:
            return self._net_module.GetDeviceCount()
        except Exception:
            return 0

    def open_device(self, index: int = 0) -> int:
        if not self._initialized or not self._net_module:
            return ZKFP_ERR_NOT_INIT
        try:
            handle = self._net_module.OpenDevice(index)
            if handle is not None and str(handle) != "0" and str(handle) != "0x0":
                self._dev_handle = handle
                self._device_open = True
                self._get_device_params()
                return ZKFP_ERR_OK
            return ZKFP_ERR_OPEN
        except Exception:
            return ZKFP_ERR_OPEN

    def close_device(self):
        with self._lock:
            if self._device_open and self._dev_handle is not None:
                try:
                    self._net_module.CloseDevice(self._dev_handle)
                except Exception:
                    pass
                self._device_open = False
                self._dev_handle = None
            if self._db_handle is not None:
                try:
                    self._net_module.DBFree(self._db_handle)
                except Exception:
                    pass
                self._db_handle = None

    def ensure_device_ready(self, user_list=None) -> int:
        if self.is_available:
            return ZKFP_ERR_OK
        if self._initialized and not self._device_open:
            ret = self.open_device(0)
            if ret != ZKFP_ERR_OK:
                return ret
            ret = self.db_init()
            if ret != ZKFP_ERR_OK:
                self.close_device()
                return ret
            if user_list is not None:
                self.load_templates(user_list)
            return ZKFP_ERR_OK
        self.terminate()
        ret = self.init()
        if ret != ZKFP_ERR_OK:
            return ret
        if self.get_device_count() <= 0:
            return ZKFP_ERR_NO_DEVICE
        ret = self.open_device(0)
        if ret != ZKFP_ERR_OK:
            return ret
        ret = self.db_init()
        if ret != ZKFP_ERR_OK:
            self.close_device()
            return ret
        if user_list is not None:
            self.load_templates(user_list)
        return ZKFP_ERR_OK

    def release_device(self):
        self.terminate()

    def _get_device_params(self):
        if not self._net_module or self._dev_handle is None:
            return
        try:
            import System
            buf = System.Array[System.Byte]([0] * 4)
            ret = self._net_module.GetParameters(self._dev_handle, 1, buf, 4)
            if not hasattr(ret, '__iter__'):
                return
            code, _ = ret
            if code == self._err_module.ZKFP_ERR_OK:
                self.image_width = struct.unpack('<i', bytes(bytearray(buf)))[0]
        except Exception:
            pass
        try:
            import System
            buf = System.Array[System.Byte]([0] * 4)
            ret = self._net_module.GetParameters(self._dev_handle, 2, buf, 4)
            if not hasattr(ret, '__iter__'):
                return
            code, _ = ret
            if code == self._err_module.ZKFP_ERR_OK:
                self.image_height = struct.unpack('<i', bytes(bytearray(buf)))[0]
        except Exception:
            pass

    def _set_capture_timeout(self, seconds: int = 1):
        if not self._net_module or self._dev_handle is None:
            return
        try:
            val = bytearray(struct.pack('<i', seconds))
            size_info = [4]
            self._net_module.SetParameters(self._dev_handle, 5, val, size_info)
        except Exception:
            pass

    # ── 指纹采集 ──

    def acquire_fingerprint(self) -> tuple:
        if not self._net_module or self._dev_handle is None:
            return ZKFP_ERR_NOT_INIT, None, None
        try:
            img_size = self.image_width * self.image_height
            if img_size <= 0:
                img_size = 320 * 480
            import System
            img_buf = System.Array[System.Byte]([0] * img_size)
            tmp_buf = System.Array[System.Byte]([0] * 2048)
            ret, tmp_size = self._net_module.AcquireFingerprint(
                self._dev_handle, img_buf, tmp_buf, 2048,
            )
            if ret == self._err_module.ZKFP_ERR_OK:
                template = bytes(bytearray(tmp_buf))[:int(tmp_size)]
                image_data = bytes(bytearray(img_buf))
                return ZKFP_ERR_OK, template, image_data
            return ret, None, None
        except Exception:
            return ZKFP_ERR_TIMEOUT, None, None

    def db_init(self):
        if not self._net_module:
            return ZKFP_ERR_NOT_INIT
        try:
            handle = self._net_module.DBInit()
            if handle is not None and str(handle) != "0" and str(handle) != "0x0":
                self._db_handle = handle
                return ZKFP_ERR_OK
            return ZKFP_ERR_NO_DEVICE
        except Exception:
            return ZKFP_ERR_NO_DEVICE

    def db_free(self):
        with self._lock:
            if self._db_handle is not None and self._net_module:
                try:
                    self._net_module.DBFree(self._db_handle)
                except Exception:
                    pass
                self._db_handle = None

    def db_add(self, fid: int, reg_template: bytes) -> int:
        if not self._net_module or self._db_handle is None:
            return ZKFP_ERR_NOT_INIT
        try:
            return self._net_module.DBAdd(self._db_handle, fid, bytearray(reg_template))
        except Exception:
            return ZKFP_ERR_ADD_FINGER

    def db_del(self, fid: int) -> int:
        if not self._net_module or self._db_handle is None:
            return ZKFP_ERR_NOT_INIT
        try:
            return self._net_module.DBDel(self._db_handle, fid)
        except Exception:
            return -14

    def db_clear(self):
        if not self._net_module or self._db_handle is None:
            return
        try:
            self._net_module.DBClear(self._db_handle)
        except Exception:
            pass

    def db_count(self) -> int:
        if not self._net_module or self._db_handle is None:
            return 0
        try:
            return self._net_module.DBCount(self._db_handle)
        except Exception:
            return 0

    def db_identify(self, template: bytes) -> tuple:
        if not self._net_module or self._db_handle is None:
            return ZKFP_ERR_NOT_INIT, -1, 0
        try:
            fid = [-1]
            score = [0]
            ret = self._net_module.DBIdentify(self._db_handle, bytearray(template), fid, score)
            if ret == self._err_module.ZKFP_ERR_OK:
                return ZKFP_ERR_OK, fid[0], score[0]
            return ret, -1, 0
        except Exception:
            return ZKFP_ERR_NO_DEVICE, -1, 0

    def db_match(self, template1: bytes, template2: bytes) -> int:
        if not self._net_module or self._db_handle is None:
            return ZKFP_ERR_NOT_INIT
        try:
            return self._net_module.DBMatch(self._db_handle, bytearray(template1), bytearray(template2))
        except Exception:
            return 0

    def db_merge(self, temp1: bytes, temp2: bytes, temp3: bytes) -> tuple:
        if not self._net_module or self._db_handle is None:
            return ZKFP_ERR_NOT_INIT, None
        try:
            import System
            reg_temp = System.Array[System.Byte]([0] * 2048)
            ret, reg_len = self._net_module.DBMerge(
                self._db_handle,
                bytearray(temp1), bytearray(temp2), bytearray(temp3),
                reg_temp, 0,
            )
            if ret == self._err_module.ZKFP_ERR_OK:
                return ZKFP_ERR_OK, bytes(bytearray(reg_temp))[:int(reg_len)]
            return ret, None
        except Exception:
            return ZKFP_ERR_MERGE, None

    def blob_to_base64(self, blob: bytes) -> str:
        import base64
        try:
            if self._net_module:
                result = self._net_module.BlobToBase64(blob, len(blob))
                if result:
                    return result
        except Exception:
            pass
        return base64.b64encode(blob).decode("ascii")

    def base64_to_blob(self, b64_str: str) -> Optional[bytes]:
        import base64
        try:
            if self._net_module:
                result = self._net_module.Base64ToBlob(b64_str)
                if result:
                    return bytes(result)
        except Exception:
            pass
        try:
            return base64.b64decode(b64_str)
        except Exception:
            return None

    def load_templates(self, user_list: List[dict]) -> Dict[int, str]:
        self.fid_user_map.clear()
        fid = 1
        loaded = skipped = 0
        for u in user_list:
            b64 = u.get("fingerprint_template", "")
            if not b64:
                skipped += 1
                continue
            try:
                blob = self.base64_to_blob(b64)
                if blob and self.db_add(fid, blob) == ZKFP_ERR_OK:
                    self.fid_user_map[fid] = u["username"]
                    fid += 1
                    loaded += 1
            except Exception:
                skipped += 1
        self.next_fid = max(self.fid_user_map.keys(), default=0) + 1
        return dict(self.fid_user_map)

    def delete_user_fingerprint(self, username: str) -> bool:
        fid_to_del = next((f for f, n in self.fid_user_map.items() if n == username), None)
        if fid_to_del is not None:
            self.db_del(fid_to_del)
            del self.fid_user_map[fid_to_del]
            return True
        return False

    @property
    def is_available(self) -> bool:
        return self._initialized and self._device_open and self._net_module is not None

    @property
    def is_initialized(self) -> bool:
        return self._initialized


class FingerprintEnroller:
    ENROLL_COUNT = 3

    def __init__(self, fp_service):
        self.fp_service = fp_service
        self.templates = []
        self.current_count = 0
        self.merged_template = None

    def reset(self):
        self.templates = []
        self.current_count = 0
        self.merged_template = None

    def capture_for_enroll(self) -> tuple:
        ret, template, image = self.fp_service.acquire_fingerprint()
        if ret != ZKFP_ERR_OK:
            return ret, None, self.current_count

        if self.current_count > 0:
            if not self._matches_previous(template):
                return -100, None, self.current_count

        self.templates.append(template)
        self.current_count += 1
        return ZKFP_ERR_OK, template, self.current_count

    def _matches_previous(self, template: bytes) -> bool:
        for t in self.templates:
            score = self.fp_service.db_match(t, template)
            if score > 0:
                return True
        return False

    def is_complete(self) -> bool:
        return self.current_count >= self.ENROLL_COUNT

    def merge(self) -> tuple:
        if not self.is_complete():
            return ZKFP_ERR_MERGE, None
        ret, merged = self.fp_service.db_merge(
            self.templates[0], self.templates[1], self.templates[2]
        )
        if ret == ZKFP_ERR_OK:
            self.merged_template = merged
        return ret, merged


class FingerprintEnrollWorker(QObject):
    status_msg = pyqtSignal(str)
    status_btn = pyqtSignal(str)
    count_msg = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        from utils.config_manager import UserManager, LogManager

        user = self.username

        try:
            self.status_msg.emit("正在初始化指纹设备...")
            self.status_btn.emit("连接设备中...")

            if not fingerprint_service.is_available:
                LogManager.log_fingerprint_init(False, "service not available, cold init")

                fingerprint_service.terminate()

                ret = fingerprint_service.init()
                if ret != ZKFP_ERR_OK:
                    self.finished.emit(False, "初始化指纹SDK失败")
                    LogManager.log_fingerprint_init(False, f"init() returned {ret}")
                    return

                if self._cancel:
                    self.finished.emit(False, "已取消")
                    return

                self.status_msg.emit("SDK就绪，检测设备...")

                cnt = fingerprint_service.get_device_count()
                if cnt <= 0:
                    self.finished.emit(False, "未检测到指纹设备")
                    LogManager.log_fingerprint_init(False, "get_device_count=0")
                    return

                self.status_msg.emit(f"发现 {cnt} 个设备，正在打开...")

                ret = fingerprint_service.open_device(0)
                if ret != ZKFP_ERR_OK:
                    self.finished.emit(False, "无法打开指纹设备")
                    LogManager.log_fingerprint_init(False, f"open_device() returned {ret}")
                    return

                self.status_msg.emit("设备已打开，初始化数据库...")

                ret = fingerprint_service.db_init()
                if ret != ZKFP_ERR_OK:
                    fingerprint_service.close_device()
                    self.finished.emit(False, "指纹数据库初始化失败")
                    LogManager.log_fingerprint_init(False, f"db_init() returned {ret}")
                    return

                # 冷启动后重新加载已有指纹模板到设备
                from utils.config_manager import UserManager
                users = UserManager.load_users()
                loaded = fingerprint_service.load_templates(users)
                LogManager.log_fingerprint_init(True, f"device_count={cnt}, loaded_templates={len(loaded)}")

                self.status_msg.emit("设备就绪，开始采集...")
            else:
                self.status_msg.emit("设备就绪，开始采集...")
                LogManager.log_fingerprint_init(True, "service was already available")

            self.status_btn.emit("采集中...")
            self.status_msg.emit("请将手指按压在指纹采集器上")

            enroller = FingerprintEnroller(fingerprint_service)
            enroller.reset()
            enroll_success = False
            CAPTURE_TIMEOUT_ERRORS = {ZKFP_ERR_CAPTURE, ZKFP_ERR_TIMEOUT}
            consecutive_capture_failures = 0
            MAX_CONSECUTIVE_FAILURES = 15

            for attempt in range(60):
                if self._cancel:
                    self.finished.emit(False, "已取消")
                    return

                ret, template, count = enroller.capture_for_enroll()

                if ret == ZKFP_ERR_OK:
                    consecutive_capture_failures = 0
                    self.count_msg.emit(f"采集次数: {count}/3")
                    self.status_msg.emit(f"第 {count} 次采集成功")
                    if enroller.is_complete():
                        break
                elif ret == -100:
                    self.status_msg.emit("请按压同一手指")
                elif ret in CAPTURE_TIMEOUT_ERRORS:
                    consecutive_capture_failures += 1
                    if consecutive_capture_failures < MAX_CONSECUTIVE_FAILURES:
                        self.status_msg.emit("请将手指按压在指纹采集器上")
                    else:
                        self.status_msg.emit("采集超时，请确认设备连接正常后重试")
                elif ret in {ZKFP_ERR_BUSY, ZKFP_ERR_NOT_OPENED, ZKFP_ERR_NOT_INIT,
                             ZKFP_ERR_OPEN, ZKFP_ERR_FAIL}:
                    self.status_msg.emit(f"设备异常(错误码{ret})，请重试")
                else:
                    consecutive_capture_failures += 1
                    self.status_msg.emit(f"采集中...({ret})")

                time.sleep(0.3)

            if enroller.is_complete():
                ret, merged = enroller.merge()
                if ret == ZKFP_ERR_OK and merged:
                    fid = fingerprint_service.next_fid
                    add_ret = fingerprint_service.db_add(fid, merged)
                    if add_ret != ZKFP_ERR_OK:
                        LogManager.log_fingerprint_enroll(user, False,
                                                          f"DBAdd returned {add_ret}")
                        self.status_msg.emit(f"注册失败：DBAdd 错误 {add_ret}")
                        self.finished.emit(False, f"用户 [{user}] 指纹注册失败")
                        return

                    fingerprint_service.fid_user_map[fid] = user
                    fingerprint_service.next_fid += 1

                    b64 = base64.b64encode(merged).decode("ascii")
                    UserManager.update_user(user, fingerprint_template=b64)
                    LogManager.log_operation("admin", "指纹注册", f"用户名={user}")
                    LogManager.log_fingerprint_enroll(user, True,
                                                      f"template_size={len(merged)}")
                    self.finished.emit(True, f"用户 [{user}] 指纹注册成功")
                    return

            self.finished.emit(False, "指纹注册失败，请重试")
            LogManager.log_fingerprint_enroll(user, False,
                                              "enrollment did not complete")

        except Exception as e:
            self.finished.emit(False, f"错误: {e}")
            LogManager.log_fingerprint_enroll(user, False, f"exception: {e}")


fingerprint_service = _NetFingerprintService()
