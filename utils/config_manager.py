import json
import os
import base64
import hashlib
import hmac
import logging
import secrets
from datetime import datetime
from typing import Optional, List, Dict

ROLE_ADMIN = "admin"
ROLE_INSPECTOR = "inspector"
ROLE_OPERATOR = "operator"

ROLE_NAMES = {
    ROLE_ADMIN: "管理员",
    ROLE_INSPECTOR: "质检员",
    ROLE_OPERATOR: "作业员",
}

ROLE_LOGIN_METHODS = {
    ROLE_ADMIN: ["fingerprint", "password"],
    ROLE_INSPECTOR: ["fingerprint"],
    ROLE_OPERATOR: ["fingerprint"],
}

ALL_ROLES = [ROLE_ADMIN, ROLE_INSPECTOR, ROLE_OPERATOR]


def role_display_name(role: str) -> str:
    return ROLE_NAMES.get(role, role)


def can_login_with_password(role: str) -> bool:
    return "password" in ROLE_LOGIN_METHODS.get(role, [])


class ConfigManager:
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "InspectionReview")
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

    DEFAULTS = {
        "databases": [
            {"name": "默认数据库", "host": "127.0.0.1", "port": 3306, "user": "root", "password": "", "database": "aoi", "enabled": True},
        ],
        "defect_box_scale": 1.2,
        "defect_line_width": 2,
        "defect_box_color": "#00FF00",
        "nine_grid_line_color": "#64C8FF",
        "nine_grid_highlight_color": "#64C8FF",
        "nine_grid_line_width": 1,
        "nine_grid_highlight_width": 2,
        "show_defect_box": True,
        "show_ok_images": False,
        "query_mode": "default",
        "quick_days": 0,
        "query_start_time": "",
        "query_end_time": "",
        "last_user": "",
        "session_timeout_minutes": 30,
        "session_reauthenticate_seconds": 60,
        "login_mode": "fingerprint",
        "history_query_months": 6,
        "review_constraint_measurement_enabled": True,
        "review_constraint_appearance_names": [],
        "dashboard_kpi_items": ["total", "ok", "ng", "yield_rate", "review_ok", "review_ng", "post_review_yield_rate"],
        "dashboard_refresh_interval": 0,
    }

    LOGIN_MODE_FINGERPRINT = "fingerprint"
    LOGIN_MODE_PASSWORD = "password"

    @classmethod
    def load(cls) -> dict:
        try:
            if os.path.exists(cls.CONFIG_PATH):
                with open(cls.CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    merged = cls.DEFAULTS.copy()
                    merged.update(cfg)
                    return merged
        except Exception:
            pass
        return cls.DEFAULTS.copy()

    @classmethod
    def save(cls, cfg: dict):
        try:
            os.makedirs(cls.CONFIG_DIR, exist_ok=True)
            with open(cls.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"保存配置失败: {e}")

    @classmethod
    def get_databases(cls, cfg: dict) -> list:
        dbs = cfg.get("databases")
        if isinstance(dbs, list) and dbs:
            return dbs
        host = cfg.get("db_host")
        if host:
            return [{"name": "默认数据库", "host": host, "port": int(cfg.get("db_port", 3306)),
                     "user": cfg.get("db_user", "root"), "password": cfg.get("db_password", ""),
                     "database": cfg.get("db_name", "aoi"), "enabled": True}]
        return [{"name": "默认数据库", "host": "127.0.0.1", "port": 3306, "user": "root",
                 "password": "", "database": "aoi", "enabled": True}]

    @classmethod
    def get_db_config(cls, cfg: dict) -> dict:
        dbs = cls.get_databases(cfg)
        if dbs:
            return dbs[0]
        return {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "", "database": "aoi"}


class UserManager:
    USERS_PATH = os.path.join(ConfigManager.CONFIG_DIR, "users.json")
    HASH_PREFIX = "pbkdf2_sha256"
    HASH_ITERATIONS = 260000

    DEFAULTS = [
        {"username": "admin", "password": "", "password_hash": "", "must_change_password": True, "role": ROLE_ADMIN, "fingerprint_template": "", "can_review": True},
        {"username": "质检员01", "password": "", "role": ROLE_INSPECTOR, "fingerprint_template": "", "can_review": True},
        {"username": "作业员01", "password": "", "role": ROLE_OPERATOR, "fingerprint_template": "", "can_review": True},
    ]

    @classmethod
    def _hash_password(cls, password: str, salt: bytes = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cls.HASH_ITERATIONS)
        return "$".join([
            cls.HASH_PREFIX,
            str(cls.HASH_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ])

    @classmethod
    def _verify_hash(cls, password: str, password_hash: str) -> bool:
        try:
            prefix, rounds, salt_b64, digest_b64 = password_hash.split("$", 3)
            if prefix != cls.HASH_PREFIX:
                return False
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(digest_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False

    @classmethod
    def _normalize_user(cls, user: dict) -> dict:
        user.setdefault("password", "")
        user.setdefault("password_hash", "")
        user.setdefault("fingerprint_template", "")
        user.setdefault("can_review", True)
        return user

    @classmethod
    def _default_users(cls) -> List[dict]:
        users = [dict(u) for u in cls.DEFAULTS]
        for u in users:
            cls._normalize_user(u)
            if u.get("username") == "admin" and not u.get("password_hash"):
                u["password_hash"] = cls._hash_password("admin123")
        return users

    @classmethod
    def _migrate_legacy_passwords(cls, users: List[dict]) -> bool:
        changed = False
        for u in users:
            cls._normalize_user(u)
            legacy_password = u.get("password", "")
            if legacy_password and not u.get("password_hash"):
                u["password_hash"] = cls._hash_password(str(legacy_password))
                if u.get("username") == "admin" and str(legacy_password) == "admin123":
                    u["must_change_password"] = True
                u["password"] = ""
                changed = True
        return changed

    @classmethod
    def password_is_set(cls, user: dict) -> bool:
        return bool(user.get("password_hash") or user.get("password"))

    @classmethod
    def verify_password(cls, user: dict, password: str) -> bool:
        if user.get("password_hash"):
            return cls._verify_hash(password, user.get("password_hash", ""))
        legacy_password = user.get("password", "")
        return bool(legacy_password) and hmac.compare_digest(str(legacy_password), password)

    @classmethod
    def _ensure_file(cls):
        if not os.path.exists(cls.USERS_PATH):
            os.makedirs(os.path.dirname(cls.USERS_PATH), exist_ok=True)
            with open(cls.USERS_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._default_users(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_users(cls) -> List[dict]:
        cls._ensure_file()
        try:
            with open(cls.USERS_PATH, "r", encoding="utf-8") as f:
                users = json.load(f)
                for u in users:
                    cls._normalize_user(u)
                if cls._migrate_legacy_passwords(users):
                    cls.save_users(users)
                return users
        except Exception:
            return cls._default_users()

    @classmethod
    def save_users(cls, users: List[dict]):
        for u in users:
            cls._normalize_user(u)
        os.makedirs(os.path.dirname(cls.USERS_PATH), exist_ok=True)
        with open(cls.USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    @classmethod
    def verify_login(cls, username: str, password: str) -> Optional[dict]:
        users = cls.load_users()
        for u in users:
            if u["username"] == username and cls.verify_password(u, password):
                return u
        return None

    @classmethod
    def find_by_username(cls, username: str) -> Optional[dict]:
        users = cls.load_users()
        for u in users:
            if u["username"] == username:
                return dict(u)
        return None

    @classmethod
    def has_fingerprint(cls, username: str) -> bool:
        u = cls.find_by_username(username)
        if u:
            return bool(u.get("fingerprint_template", ""))
        return False

    @classmethod
    def verify_fingerprint_login(cls, template_b64: str) -> Optional[dict]:
        users = cls.load_users()
        for u in users:
            if u.get("fingerprint_template", "") == template_b64:
                return u
        return None

    @classmethod
    def add_user(cls, username: str, password: str = "", role: str = ROLE_OPERATOR,
                 can_review: bool = None):
        users = cls.load_users()
        if any(u["username"] == username for u in users):
            raise ValueError(f"用户 [{username}] 已存在")
        if can_review is None:
            can_review = True
        users.append({
            "username": username,
            "password": "",
            "password_hash": cls._hash_password(password) if password else "",
            "role": role,
            "fingerprint_template": "",
            "can_review": can_review,
        })
        cls.save_users(users)

    @classmethod
    def update_user(cls, username: str, password: str = None, role: str = None,
                    fingerprint_template: str = None, can_review: bool = None,
                    new_username: str = None):
        users = cls.load_users()
        for u in users:
            if u["username"] == username:
                if new_username is not None and new_username != username:
                    if any(x["username"] == new_username for x in users):
                        raise ValueError(f"用户名 [{new_username}] 已存在")
                    u["username"] = new_username
                if password is not None:
                    u["password"] = ""
                    u["password_hash"] = cls._hash_password(password) if password else ""
                    u["must_change_password"] = False
                if role is not None:
                    u["role"] = role
                if fingerprint_template is not None:
                    u["fingerprint_template"] = fingerprint_template
                if can_review is not None:
                    u["can_review"] = can_review
                cls.save_users(users)
                return
        raise ValueError(f"用户 [{username}] 不存在")

    @classmethod
    def delete_user(cls, username: str):
        users = cls.load_users()
        new_users = [u for u in users if u["username"] != username]
        if len(new_users) == len(users):
            raise ValueError(f"用户 [{username}] 不存在")
        cls.save_users(new_users)


class LogManager:
    LOGIN_LOG = "LOGIN"
    OPERATION_LOG = "OPERATION"
    SYSTEM_LOG = "SYSTEM"
    _logging_configured = False

    @classmethod
    def _log_dir(cls) -> str:
        return os.path.join(ConfigManager.CONFIG_DIR, "log")

    @classmethod
    def _log_path(cls) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(cls._log_dir(), f"{today}.txt")

    @classmethod
    def setup_logging(cls):
        if cls._logging_configured:
            return
        os.makedirs(cls._log_dir(), exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(cls._log_dir(), "app.log"),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            encoding="utf-8",
        )
        cls._logging_configured = True

    @classmethod
    def _write(cls, log_type: str, username: str, message: str, detail: str = ""):
        try:
            log_dir = cls._log_dir()
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if detail:
                line = f"[{timestamp}] [{log_type}] [{username}] {message} | {detail}\n"
            else:
                line = f"[{timestamp}] [{log_type}] [{username}] {message}\n"
            with open(cls._log_path(), "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            logging.getLogger(__name__).exception("write operation log failed")

    @classmethod
    def add_log(cls, log_type: str, username: str, message: str, detail: str = ""):
        cls._write(log_type, username, message, detail)

    @classmethod
    def log_login(cls, username: str, method: str, success: bool):
        cls._write(
            cls.LOGIN_LOG, username,
            f"登录{'成功' if success else '失败'}",
            f"方式: {method}",
        )

    @classmethod
    def log_logout(cls, username: str):
        cls._write(cls.LOGIN_LOG, username, "退出登录", "")

    @classmethod
    def log_operation(cls, username: str, operation: str, detail: str = ""):
        cls._write(cls.OPERATION_LOG, username, operation, detail)

    @classmethod
    def log_system(cls, message: str, detail: str = ""):
        cls._write(cls.SYSTEM_LOG, "system", message, detail)

    @classmethod
    def log_exception(cls, message: str, exc: Exception = None, detail: str = ""):
        if exc:
            logging.getLogger(__name__).exception("%s | %s", message, detail)
            cls._write(cls.SYSTEM_LOG, "system", message, f"{detail} | {type(exc).__name__}: {exc}")
        else:
            logging.getLogger(__name__).error("%s | %s", message, detail)
            cls._write(cls.SYSTEM_LOG, "system", message, detail)

    @classmethod
    def log_fingerprint_init(cls, success: bool, detail: str = ""):
        cls._write(cls.SYSTEM_LOG, "system",
                   f"指纹设备初始化{'成功' if success else '失败'}", detail)

    @classmethod
    def log_fingerprint_enroll(cls, username: str, success: bool, detail: str = ""):
        cls._write(cls.OPERATION_LOG, username,
                   f"指纹注册{'成功' if success else '失败'}", detail)

    @classmethod
    def log_fingerprint_identify(cls, username: str, success: bool, detail: str = ""):
        cls._write(cls.LOGIN_LOG, username if success else "unknown",
                   f"指纹识别{'成功' if success else '失败'}", detail)

    @classmethod
    def get_logs(cls, log_type: str = None, limit: int = 100) -> List[str]:
        try:
            path = cls._log_path()
            if not os.path.exists(path):
                return []
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if log_type:
                tag = f"[{log_type}]"
                lines = [l for l in lines if tag in l]
            return lines[-limit:]
        except Exception:
            return []

    @classmethod
    def get_all_logs(cls, limit: int = 200) -> List[str]:
        return cls.get_logs(None, limit)
