from datetime import datetime, timedelta
from typing import List, Optional
from database.manager import DBManager
from analytics.yield_analyzer import YieldAnalyzer
from analytics.defect_analyzer import DefectAnalyzer
from analytics.station_analyzer import StationAnalyzer
from analytics.product_analyzer import ProductAnalyzer
from analytics.heatmap_analyzer import HeatmapAnalyzer
from analytics.trend_analyzer import TrendAnalyzer
from analytics.cache import DashboardCache


# 时间范围粒度映射
TIME_RANGE_GRANULARITY = {
    0: [  # 今天
        {"text": "全天", "value": "day"},
        {"text": "1小时", "value": "1hour"},
        {"text": "6小时", "value": "6hour"},
        {"text": "10分钟", "value": "10min"},
        {"text": "30分钟", "value": "30min"},
    ],
    7: [  # 近7天
        {"text": "按天", "value": "day"},
        {"text": "按周", "value": "week"},
        {"text": "全部", "value": "all"},
    ],
    30: [  # 近30天
        {"text": "按天", "value": "day"},
        {"text": "按周", "value": "week"},
        {"text": "按月", "value": "month"},
    ],
}


class DashboardService:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager
        self._cache = DashboardCache()

    def _get_conn(self) -> Optional[object]:
        return self.db_manager.get_first_connected()

    def _range(self, days: int) -> tuple[datetime, datetime]:
        end = datetime.now()
        if days == 0:
            start = datetime(end.year, end.month, end.day, 0, 0, 0)
        elif days == -1:
            start = datetime(end.year, end.month, 1, 0, 0, 0)
        else:
            d = end - timedelta(days=days)
            start = datetime(d.year, d.month, d.day, 0, 0, 0)
        return start, end

    def get_granularity_options(self, days: int) -> List[dict]:
        """获取指定时间范围的粒度选项"""
        return TIME_RANGE_GRANULARITY.get(days, TIME_RANGE_GRANULARITY[7])

    def kpi(self, days: int = 0) -> dict:
        conn = self._get_conn()
        if not conn:
            return {}
        start, end = self._range(days)
        return YieldAnalyzer(conn).kpi(start, end)

    def kpi_trend(self, days: int = 0) -> dict:
        conn = self._get_conn()
        if not conn:
            return {"current": {}, "previous": {}, "deltas": {}}
        start, end = self._range(days)
        span = end - start
        prev_start = start - span
        prev_end = start
        analyzer = YieldAnalyzer(conn)
        curr = analyzer.kpi(start, end)
        prev = analyzer.kpi(prev_start, prev_end)
        deltas = {}
        for key in ["total", "ok", "ng", "yield_rate", "review_ok", "review_ng", "post_review_yield_rate"]:
            cv = curr.get(key, 0)
            pv = prev.get(key, 0)
            if isinstance(cv, (int, float)) and isinstance(pv, (int, float)):
                if pv != 0:
                    deltas[key] = round((cv - pv) / pv * 100, 1)
                else:
                    deltas[key] = 0
            else:
                deltas[key] = 0
        return {"current": curr, "previous": prev, "deltas": deltas}

    def yield_trend(self, days: int = 7, granularity: str = "day") -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        return YieldAnalyzer(conn).trend(start, end, granularity)

    def yield_trend_granularity(self, days: int, granularity: str) -> List[dict]:
        """
        获取良率趋势（支持不同粒度）
        
        Args:
            days: 天数
            granularity: "10min" | "30min" | "1hour" | "6hour" | "day" | "week" | "month" | "all"
        """
        conn = self._get_conn()
        if not conn:
            return []
        
        # 根据粒度调整时间范围
        if granularity == "10min":
            end = datetime.now()
            start = end - timedelta(minutes=10)
            return YieldAnalyzer(conn).trend(start, end, "minute")
        elif granularity == "30min":
            end = datetime.now()
            start = end - timedelta(minutes=30)
            return YieldAnalyzer(conn).trend(start, end, "minute")
        elif granularity == "1hour":
            end = datetime.now()
            start = end - timedelta(hours=1)
            return YieldAnalyzer(conn).trend(start, end, "minute")
        elif granularity == "6hour":
            end = datetime.now()
            start = end - timedelta(hours=6)
            return YieldAnalyzer(conn).trend(start, end, "minute")
        elif granularity == "all":
            # 使用全部时间范围，按天粒度
            start, end = self._range(days)
            return YieldAnalyzer(conn).trend(start, end, "day")
        else:
            # day, week, month
            start, end = self._range(days)
            return YieldAnalyzer(conn).trend(start, end, granularity)

    def top_defects(self, days: int = 7, top_n: int = 10) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        return DefectAnalyzer(conn).top_defects(start, end, top_n)

    def defect_distribution(self, days: int = 0, top_n: int = 10) -> List[dict]:
        """
        获取缺陷分布（饼图用）
        """
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        return DefectAnalyzer(conn).defect_distribution(start, end, top_n)

    def defect_distribution_granularity(self, days: int, granularity: str, top_n: int = 10) -> List[dict]:
        """
        获取缺陷分布（支持不同粒度）
        
        Args:
            days: 天数
            granularity: "10min" | "30min" | "1hour" | "6hour" | "day" | "week" | "month" | "all"
            top_n: 返回前N个缺陷
        """
        conn = self._get_conn()
        if not conn:
            return []
        
        # 根据粒度调整时间范围
        if granularity == "10min":
            end = datetime.now()
            start = end - timedelta(minutes=10)
        elif granularity == "30min":
            end = datetime.now()
            start = end - timedelta(minutes=30)
        elif granularity == "1hour":
            end = datetime.now()
            start = end - timedelta(hours=1)
        elif granularity == "6hour":
            end = datetime.now()
            start = end - timedelta(hours=6)
        else:
            start, end = self._range(days)
        
        return DefectAnalyzer(conn).defect_distribution(start, end, top_n)

    def recent_records(self, limit: int = 20, result_filter: str = "ng", days: int = 0) -> List[dict]:
        """
        获取最近检测记录
        
        Args:
            limit: 记录数量
            result_filter: "ng" | "ok" | "all"
            days: 天数
        """
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        return DefectAnalyzer(conn).recent_records(start, end, limit, result_filter)

    def get_work_orders(self, days: int = 7) -> List[str]:
        """获取工单列表（动态）"""
        conn = self._get_conn()
        if not conn:
            return []
        
        # 从station_result表中获取工单列表
        try:
            start, end = self._range(days)
            tables = conn.router.build_table_list("t_station_result")
            work_orders = set()
            
            for table in tables:
                rows = conn._fetch_all(
                    f"SELECT DISTINCT WorkOrder FROM `{table}` WHERE CreateTime BETWEEN %s AND %s AND WorkOrder != ''",
                    (start, end),
                )
                for row in rows:
                    wo = row.get("WorkOrder", "")
                    if wo:
                        work_orders.add(wo)
            
            return sorted(list(work_orders))
        except Exception:
            return []

    def station_ng_rates(self, days: int = 7) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        return StationAnalyzer(conn).station_ng_rates(start, end)

    def product_ranking(self, days: int = 7, top_n: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        return ProductAnalyzer(conn).product_ranking(start, end, top_n)

    def heatmap(self, days: int = 7) -> dict:
        conn = self._get_conn()
        if not conn:
            return {}
        start, end = self._range(days)
        return HeatmapAnalyzer(conn).analyze(start, end)

    def defect_trend(self, days: int = 30) -> dict:
        conn = self._get_conn()
        if not conn:
            return {"dates": [], "series": []}
        start, end = self._range(days)
        return TrendAnalyzer(conn).defect_trend(start, end, top_n=5)

    def kpi_custom(self, start: datetime, end: datetime) -> dict:
        conn = self._get_conn()
        if not conn:
            return {}
        return YieldAnalyzer(conn).kpi(start, end)

    def top_defects_custom(self, start: datetime, end: datetime, top_n: int = 10) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        return DefectAnalyzer(conn).top_defects(start, end, top_n)

    def yield_trend_custom(self, start: datetime, end: datetime, granularity: str = "day") -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        return YieldAnalyzer(conn).trend(start, end, granularity)

    def station_ng_rates_custom(self, start: datetime, end: datetime) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        return StationAnalyzer(conn).station_ng_rates(start, end)

    def product_ranking_custom(self, start: datetime, end: datetime, top_n: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        return ProductAnalyzer(conn).product_ranking(start, end, top_n)

    def _range_custom(self, start_date: str, end_date: str) -> tuple[datetime, datetime]:
        """获取自定义日期范围"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        return start, end

    def kpi_trend_custom_date(self, start_date: str, end_date: str) -> dict:
        """获取KPI趋势（自定义日期范围）"""
        conn = self._get_conn()
        if not conn:
            return {"current": {}, "previous": {}, "deltas": {}}
        start, end = self._range_custom(start_date, end_date)
        span = end - start
        prev_start = start - span
        prev_end = start
        analyzer = YieldAnalyzer(conn)
        curr = analyzer.kpi(start, end)
        prev = analyzer.kpi(prev_start, prev_end)
        deltas = {}
        for key in ["total", "ok", "ng", "yield_rate", "review_ok", "review_ng", "post_review_yield_rate"]:
            cv = curr.get(key, 0)
            pv = prev.get(key, 0)
            if isinstance(cv, (int, float)) and isinstance(pv, (int, float)):
                if pv != 0:
                    deltas[key] = round((cv - pv) / pv * 100, 1)
                else:
                    deltas[key] = 0
            else:
                deltas[key] = 0
        return {"current": curr, "previous": prev, "deltas": deltas}

    def yield_trend_custom_date(self, start_date: str, end_date: str, granularity: str = "day") -> List[dict]:
        """获取良率趋势（自定义日期范围）"""
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range_custom(start_date, end_date)
        return YieldAnalyzer(conn).trend(start, end, granularity)

    def defect_distribution_custom_date(self, start_date: str, end_date: str, granularity: str = "day", top_n: int = 10) -> List[dict]:
        """获取缺陷分布（自定义日期范围）"""
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range_custom(start_date, end_date)
        return DefectAnalyzer(conn).defect_distribution(start, end, top_n)

    def recent_records_custom_date(self, limit: int = 20, result_filter: str = "ng", start_date: str = None, end_date: str = None) -> List[dict]:
        """获取最近检测记录（自定义日期范围）"""
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range_custom(start_date, end_date)
        return DefectAnalyzer(conn).recent_records(start, end, limit, result_filter)