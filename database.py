"""
農作業記録簿 - データベースモジュール
SQLiteデータベースの初期化、CRUD操作を提供する。
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "farm_records.db")


def get_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """データベースの初期化（テーブル作成）"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crop_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crop_name TEXT NOT NULL,
            variety TEXT,
            field_id TEXT,
            row_id TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT '進行中' CHECK(status IN ('計画中', '進行中', '完了')),
            yield_amount REAL,
            yield_unit TEXT DEFAULT 'kg',
            quality_rating TEXT,
            quality_note TEXT,
            comment TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER REFERENCES crop_cycles(id) ON DELETE SET NULL,
            work_date TEXT NOT NULL,
            work_type TEXT NOT NULL,
            cell_pot TEXT,
            quantity TEXT,
            field_id TEXT,
            row_id TEXT,
            content TEXT,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 既存DBへのカラム追加（テーブルが既に存在する場合）
    for col_name, col_type in [("cell_pot", "TEXT"), ("quantity", "TEXT")]:
        try:
            cursor.execute(
                f"ALTER TABLE work_logs ADD COLUMN {col_name} {col_type}"
            )
        except Exception:
            pass  # カラムが既に存在する場合はスキップ

    conn.commit()
    conn.close()


# ============================================================
# 作付け (Crop Cycles) CRUD
# ============================================================

def create_crop_cycle(crop_name, variety=None, field_id=None, row_id=None,
                      start_date=None, end_date=None, status="進行中",
                      yield_amount=None, yield_unit="kg",
                      quality_rating=None, quality_note=None, comment=None):
    """作付けを新規作成"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crop_cycles
            (crop_name, variety, field_id, row_id,
             start_date, end_date, status,
             yield_amount, yield_unit,
             quality_rating, quality_note, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (crop_name, variety, field_id, row_id,
          start_date, end_date, status,
          yield_amount, yield_unit,
          quality_rating, quality_note, comment))
    cycle_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cycle_id


def get_all_crop_cycles(status_filter=None, crop_filter=None, field_filter=None):
    """作付け一覧を取得（フィルタ付き）"""
    conn = get_connection()
    query = "SELECT * FROM crop_cycles WHERE 1=1"
    params = []

    if status_filter and status_filter != "すべて":
        query += " AND status = ?"
        params.append(status_filter)
    if crop_filter:
        query += " AND crop_name LIKE ?"
        params.append(f"%{crop_filter}%")
    if field_filter and field_filter != "すべて":
        query += " AND field_id = ?"
        params.append(field_filter)

    query += " ORDER BY COALESCE(start_date, '9999') DESC, id DESC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_crop_cycle(cycle_id):
    """作付けを1件取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM crop_cycles WHERE id = ?", (cycle_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_crop_cycle(cycle_id, **kwargs):
    """作付けを更新"""
    if not kwargs:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
    values = list(kwargs.values()) + [cycle_id]
    conn.execute(
        f"UPDATE crop_cycles SET {set_clause}, "
        f"updated_at = datetime('now', 'localtime') WHERE id = ?",
        values
    )
    conn.commit()
    conn.close()


def delete_crop_cycle(cycle_id):
    """作付けを削除"""
    conn = get_connection()
    conn.execute("DELETE FROM crop_cycles WHERE id = ?", (cycle_id,))
    conn.commit()
    conn.close()


# ============================================================
# 作業記録 (Work Logs) CRUD
# ============================================================

def create_work_log(work_date, work_type, cycle_id=None, cell_pot=None,
                    quantity=None, field_id=None,
                    row_id=None, content=None, note=None):
    """作業記録を新規作成"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO work_logs (cycle_id, work_date, work_type, cell_pot, quantity,
                               field_id, row_id, content, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (cycle_id, work_date, work_type, cell_pot, quantity,
          field_id, row_id, content, note))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def get_work_logs_by_cycle(cycle_id):
    """指定作付けの作業記録を時系列で取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM work_logs WHERE cycle_id = ?
        ORDER BY work_date ASC, id ASC
    """, (cycle_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_work_logs(date_from=None, date_to=None, work_type=None,
                      field_id=None, cycle_id=None):
    """作業記録一覧を取得（フィルタ付き）"""
    conn = get_connection()
    query = """
        SELECT wl.*, cc.crop_name, cc.variety
        FROM work_logs wl
        LEFT JOIN crop_cycles cc ON wl.cycle_id = cc.id
        WHERE 1=1
    """
    params = []

    if date_from:
        query += " AND wl.work_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND wl.work_date <= ?"
        params.append(date_to)
    if work_type and work_type != "すべて":
        query += " AND wl.work_type = ?"
        params.append(work_type)
    if field_id and field_id != "すべて":
        query += " AND wl.field_id = ?"
        params.append(field_id)
    if cycle_id is not None:
        query += " AND wl.cycle_id = ?"
        params.append(cycle_id)

    query += " ORDER BY wl.work_date DESC, wl.id DESC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unlinked_work_logs():
    """作付けに紐づいていない作業記録を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM work_logs WHERE cycle_id IS NULL
        ORDER BY work_date DESC, id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_work_log(log_id, **kwargs):
    """作業記録を更新"""
    if not kwargs:
        return
    conn = get_connection()
    set_clause = ", ".join(f"{key} = ?" for key in kwargs.keys())
    values = list(kwargs.values()) + [log_id]
    conn.execute(f"UPDATE work_logs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_work_log(log_id):
    """作業記録を削除"""
    conn = get_connection()
    conn.execute("DELETE FROM work_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()


def link_work_log_to_cycle(log_id, cycle_id):
    """作業記録を作付けに紐づける"""
    conn = get_connection()
    conn.execute("UPDATE work_logs SET cycle_id = ? WHERE id = ?",
                 (cycle_id, log_id))
    conn.commit()
    conn.close()


def unlink_work_log_from_cycle(log_id):
    """作業記録の作付け紐づけを解除"""
    conn = get_connection()
    conn.execute("UPDATE work_logs SET cycle_id = NULL WHERE id = ?",
                 (log_id,))
    conn.commit()
    conn.close()


# ============================================================
# 統計・集計
# ============================================================

def get_dashboard_stats():
    """ダッシュボード用の統計情報を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}

    cursor.execute("SELECT COUNT(*) FROM crop_cycles")
    stats["total_cycles"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM crop_cycles WHERE status = '進行中'")
    stats["active_cycles"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM crop_cycles WHERE status = '完了'")
    stats["completed_cycles"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM work_logs")
    stats["total_logs"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT crop_name) FROM crop_cycles")
    stats["crop_types"] = cursor.fetchone()[0]

    conn.close()
    return stats


def get_recent_work_logs(limit=10):
    """最近の作業記録を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT wl.*, cc.crop_name, cc.variety
        FROM work_logs wl
        LEFT JOIN crop_cycles cc ON wl.cycle_id = cc.id
        ORDER BY wl.work_date DESC, wl.id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_yield_summary():
    """収量集計を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT crop_name, variety,
               SUM(yield_amount) as total_yield,
               yield_unit,
               AVG(yield_amount) as avg_yield,
               COUNT(*) as count
        FROM crop_cycles
        WHERE yield_amount IS NOT NULL AND yield_amount > 0
        GROUP BY crop_name, yield_unit
        ORDER BY total_yield DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_monthly_work_counts():
    """月別作業件数を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT substr(work_date, 1, 7) as month,
               COUNT(*) as count
        FROM work_logs
        WHERE work_date IS NOT NULL AND work_date != ''
        GROUP BY month
        ORDER BY month
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_work_type_counts():
    """作業種別ごとの件数を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT work_type, COUNT(*) as count
        FROM work_logs
        GROUP BY work_type
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_distinct_fields():
    """登録済み圃場IDの一覧を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT field_id FROM (
            SELECT field_id FROM crop_cycles
            WHERE field_id IS NOT NULL AND field_id != ''
            UNION
            SELECT field_id FROM work_logs
            WHERE field_id IS NOT NULL AND field_id != ''
        ) ORDER BY field_id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [row["field_id"] for row in rows]


def get_distinct_crops():
    """登録済み作物名の一覧を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT crop_name FROM crop_cycles ORDER BY crop_name"
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["crop_name"] for row in rows]


def get_distinct_work_types():
    """登録済み作業種別の一覧を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT work_type FROM work_logs ORDER BY work_type"
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["work_type"] for row in rows]


# ============================================================
# CSVインポート
# ============================================================

def import_csv_records(records):
    """CSVから読み込んだレコードを一括インポート"""
    conn = get_connection()
    cursor = conn.cursor()
    imported = 0
    for rec in records:
        cursor.execute("""
            INSERT INTO work_logs
                (work_date, work_type, cell_pot, quantity,
                 field_id, row_id, content, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec.get("work_date", ""),
            rec.get("work_type", "その他"),
            rec.get("cell_pot"),
            rec.get("quantity"),
            rec.get("field_id"),
            rec.get("row_id"),
            rec.get("content"),
            rec.get("note"),
        ))
        imported += 1
    conn.commit()
    conn.close()
    return imported
