from datetime import datetime
from database.manager import DBManager
from database.models import REVIEW_OK, REVIEW_NG


class ReviewService:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def review_ok(self, sn: str, user: str, source_name: str = "") -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        remark = f"复判人员: {user} | 复判结果: OK | 复判时间: {now}"
        if not self.db.update_review(sn, REVIEW_OK, user, remark, source_name):
            raise RuntimeError(f"复判写入失败，未找到可更新记录: SN={sn}")
        return "复判完成: 判定为 OK"

    def review_ng(self, sn: str, user: str, source_name: str = "") -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        remark = f"复判人员: {user} | 复判结果: NG | 复判时间: {now}"
        if not self.db.update_review(sn, REVIEW_NG, user, remark, source_name):
            raise RuntimeError(f"复判写入失败，未找到可更新记录: SN={sn}")
        return "复判完成: 判定为 NG"
