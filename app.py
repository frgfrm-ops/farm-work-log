"""
農作業記録簿 - メインアプリケーション
Streamlit で構築された農作業記録・閲覧システム
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import database as db
import io
import plotly.express as px

# ============================================================
# アプリケーション設定
# ============================================================
st.set_page_config(
    page_title="農作業記録簿",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# カスタムCSS
# ============================================================
st.markdown("""
<style>
    /* メトリクスカード */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* タイムラインスタイル */
    .tl-container { position: relative; padding: 10px 0 10px 40px; }
    .tl-container::before {
        content: ''; position: absolute; left: 18px; top: 0; bottom: 0;
        width: 3px; background: linear-gradient(to bottom, #4CAF50, #81C784);
        border-radius: 2px;
    }
    .tl-item {
        position: relative; margin-bottom: 18px; padding: 14px 18px;
        background: #ffffff; border-radius: 10px;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .tl-item::before {
        content: ''; position: absolute; left: -31px; top: 18px;
        width: 13px; height: 13px; border-radius: 50%;
        background: #4CAF50; border: 3px solid #e8f5e9;
    }
    .tl-date {
        font-size: 0.82em; color: #888; font-weight: 600;
        margin-bottom: 4px;
    }
    .tl-type {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        background: #e8f5e9; color: #2e7d32;
        font-size: 0.82em; font-weight: 600; margin-bottom: 6px;
    }
    .tl-content { font-size: 0.95em; color: #333; line-height: 1.5; }
    .tl-note { font-size: 0.82em; color: #999; margin-top: 4px; }

    /* ステータスバッジ */
    .badge {
        display: inline-block; padding: 3px 12px; border-radius: 12px;
        font-size: 0.82em; font-weight: 600;
    }
    .badge-active { background: #e8f5e9; color: #2e7d32; }
    .badge-plan { background: #fff3e0; color: #e65100; }
    .badge-done { background: #e3f2fd; color: #1565c0; }

    /* サイクルカード */
    .cycle-card {
        background: #fff; border-radius: 10px; padding: 16px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }
    .cycle-card h4 { margin: 0 0 8px 0; color: #2e7d32; }
    .cycle-meta { font-size: 0.85em; color: #777; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 定数
# ============================================================
# 管理者パスワード: st.secrets があればそちらを優先（クラウド用）
try:
    ADMIN_PASSWORD = st.secrets["admin_password"]
except (FileNotFoundError, KeyError):
    ADMIN_PASSWORD = "farm2026"

WORK_TYPES = [
    "播種","播種セル","播種ポット", "育苗", "定植", "施肥", "基肥",
    "耕耘", "畝立て", "畝立てマルチ張り", "マルチ張り",
    "灌水", "除草", "防除", "摘果・摘花",
    "誘引・仕立て", "剪定・整枝",
    "収穫", "出荷・販売",
    "土作り", "圃場準備", "片付け",
    "観察・記録", "機械整備", "その他",
]

STATUS_OPTIONS = ["計画中", "進行中", "完了"]
QUALITY_OPTIONS = ["", "A", "B", "C"]

# ============================================================
# 初期化
# ============================================================
db.init_db()

if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "selected_cycle" not in st.session_state:
    st.session_state.selected_cycle = None
if "page" not in st.session_state:
    st.session_state.page = "📊 ダッシュボード"


# ============================================================
# ユーティリティ関数
# ============================================================
def status_badge(status):
    """ステータスに応じたバッジHTMLを返す"""
    cls = {"計画中": "badge-plan", "進行中": "badge-active", "完了": "badge-done"}
    return f'<span class="badge {cls.get(status, "")}">{status}</span>'


def safe_date(d):
    """日付文字列をdate型に変換（変換不可ならNone）"""
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def navigate_to_timeline(cycle_id):
    """タイムラインページへ遷移"""
    st.session_state.selected_cycle = cycle_id
    st.session_state.page = "📅 タイムライン"


# ============================================================
# ページ: ダッシュボード
# ============================================================
def page_dashboard():
    st.header("📊 ダッシュボード")

    stats = db.get_dashboard_stats()

    # メトリクスカード
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("作付け総数", stats["total_cycles"])
    c2.metric("進行中", stats["active_cycles"])
    c3.metric("完了", stats["completed_cycles"])
    c4.metric("作業記録数", stats["total_logs"])

    st.divider()

    col_left, col_right = st.columns([3, 2])

    # 進行中の作付け
    with col_left:
        st.subheader("🌱 進行中の作付け")
        active = db.get_all_crop_cycles(status_filter="進行中")
        if active:
            for cy in active[:10]:
                logs = db.get_work_logs_by_cycle(cy["id"])
                last_work = logs[-1]["work_type"] if logs else "―"
                field_text = f"📍 {cy['field_id']}" if cy["field_id"] else ""
                variety_text = f"（{cy['variety']}）" if cy["variety"] else ""
                st.markdown(f"""
                <div class="cycle-card">
                    <h4>🌱 {cy['crop_name']}{variety_text}</h4>
                    <div class="cycle-meta">
                        {field_text}　開始: {cy['start_date'] or '未設定'}　
                        作業数: {len(logs)}件　最新: {last_work}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("進行中の作付けはありません")

    # 最近の作業
    with col_right:
        st.subheader("📝 最近の作業")
        recent = db.get_recent_work_logs(limit=10)
        if recent:
            for log in recent:
                crop_info = ""
                if log.get("crop_name"):
                    crop_info = f" → {log['crop_name']}"
                st.markdown(
                    f"**{log['work_date']}**　"
                    f"`{log['work_type']}`{crop_info}  \n"
                    f"{log.get('content') or ''}",
                )
        else:
            st.info("作業記録がありません")


# ============================================================
# ページ: 作付け一覧
# ============================================================
def page_crop_cycles():
    st.header("🌱 作付け一覧")

    # フィルター
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        status_f = st.selectbox("ステータス", ["すべて"] + STATUS_OPTIONS)
    with fc2:
        crop_f = st.text_input("作物名で検索", "")
    with fc3:
        fields = ["すべて"] + db.get_distinct_fields()
        field_f = st.selectbox("圃場", fields)

    cycles = db.get_all_crop_cycles(
        status_filter=status_f, crop_filter=crop_f, field_filter=field_f
    )

    if not cycles:
        st.info("該当する作付けがありません")
        return

    st.caption(f"{len(cycles)} 件の作付け")

    for cy in cycles:
        variety_text = f"（{cy['variety']}）" if cy.get("variety") else ""
        title = f"{cy['crop_name']}{variety_text}"
        field_info = f"📍 {cy['field_id']}" if cy.get("field_id") else ""
        period = f"{cy.get('start_date') or '?'} ～ {cy.get('end_date') or '継続中'}"

        with st.expander(f"{title}　{field_info}　｜　{period}　{cy['status']}"):
            st.markdown(status_badge(cy["status"]), unsafe_allow_html=True)
            ic1, ic2, ic3 = st.columns(3)
            ic1.write(f"**作物:** {cy['crop_name']}")
            ic2.write(f"**品種:** {cy.get('variety') or '―'}")
            ic3.write(f"**圃場:** {cy.get('field_id') or '―'}")

            if cy.get("yield_amount"):
                st.write(
                    f"**収量:** {cy['yield_amount']} {cy.get('yield_unit', 'kg')}　"
                    f"**品質:** {cy.get('quality_rating') or '―'}"
                )
            if cy.get("quality_note"):
                st.write(f"**品質メモ:** {cy['quality_note']}")
            if cy.get("comment"):
                st.write(f"**コメント:** {cy['comment']}")

            # 紐づく作業記録
            logs = db.get_work_logs_by_cycle(cy["id"])
            if logs:
                st.write(f"**作業記録:** {len(logs)} 件")
                log_df = pd.DataFrame(logs)[
                    ["work_date", "work_type", "content", "note"]
                ]
                log_df.columns = ["日付", "作業", "内容", "備考"]
                st.dataframe(log_df, use_container_width=True, hide_index=True)

            if st.button("📅 タイムラインを見る", key=f"tl_{cy['id']}"):
                navigate_to_timeline(cy["id"])
                st.rerun()


# ============================================================
# ページ: タイムライン
# ============================================================
def page_timeline():
    st.header("📅 タイムライン")

    cycles = db.get_all_crop_cycles()
    if not cycles:
        st.info("作付けが登録されていません。先に作付けを登録してください。")
        return

    # 作付け選択
    cycle_options = {
        cy["id"]: f"{cy['crop_name']}"
                   f"{'（' + cy['variety'] + '）' if cy.get('variety') else ''}"
                   f" [{cy.get('field_id') or '圃場未設定'}]"
                   f" - {cy['status']}"
        for cy in cycles
    }

    # プリセレクト
    default_idx = 0
    if st.session_state.selected_cycle:
        ids = list(cycle_options.keys())
        if st.session_state.selected_cycle in ids:
            default_idx = ids.index(st.session_state.selected_cycle)

    selected_id = st.selectbox(
        "作付けを選択",
        options=list(cycle_options.keys()),
        format_func=lambda x: cycle_options[x],
        index=default_idx,
    )

    if not selected_id:
        return

    cycle = db.get_crop_cycle(selected_id)
    if not cycle:
        st.error("作付けが見つかりません")
        return

    st.session_state.selected_cycle = selected_id

    # ヘッダー情報
    variety_text = f"（{cycle['variety']}）" if cycle.get("variety") else ""
    st.subheader(f"🌱 {cycle['crop_name']}{variety_text}")

    hc1, hc2, hc3, hc4 = st.columns(4)
    hc1.write(f"**圃場:** {cycle.get('field_id') or '―'}")
    hc2.write(f"**畝:** {cycle.get('row_id') or '―'}")
    hc3.markdown(
        f"**ステータス:** {status_badge(cycle['status'])}",
        unsafe_allow_html=True,
    )
    hc4.write(
        f"**期間:** {cycle.get('start_date') or '?'} ～ "
        f"{cycle.get('end_date') or '継続中'}"
    )

    # 収量・品質（完了の場合）
    if cycle.get("yield_amount"):
        yc1, yc2, yc3 = st.columns(3)
        yc1.metric("収量", f"{cycle['yield_amount']} {cycle.get('yield_unit', 'kg')}")
        yc2.metric("品質評価", cycle.get("quality_rating") or "―")
        yc3.write(f"**品質メモ:** {cycle.get('quality_note') or '―'}")
    if cycle.get("comment"):
        st.info(f"💬 {cycle['comment']}")

    st.divider()

    # 作業記録タイムライン
    logs = db.get_work_logs_by_cycle(selected_id)

    if not logs:
        st.warning("この作付けにはまだ作業記録がありません")
        return

    st.caption(f"📋 作業記録: {len(logs)} 件")

    # タイムラインHTML生成
    html = '<div class="tl-container">'
    for log in logs:
        note_html = (
            f'<div class="tl-note">📌 {log["note"]}</div>'
            if log.get("note")
            else ""
        )
        content_text = log.get("content") or ""
        html += f"""
        <div class="tl-item">
            <div class="tl-date">{log['work_date']}</div>
            <span class="tl-type">{log['work_type']}</span>
            <div class="tl-content">{content_text}</div>
            {note_html}
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# ページ: 集計・分析
# ============================================================
def page_analytics():
    st.header("📈 集計・分析")

    tab1, tab2, tab3 = st.tabs(["📊 月別作業件数", "🌾 収量集計", "🔧 作業種別"])

    with tab1:
        monthly = db.get_monthly_work_counts()
        if monthly:
            df = pd.DataFrame(monthly)
            fig = px.bar(
                df, x="month", y="count",
                labels={"month": "月", "count": "件数"},
                title="月別作業件数",
                color_discrete_sequence=["#4CAF50"],
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("データがありません")

    with tab2:
        yields = db.get_yield_summary()
        if yields:
            df = pd.DataFrame(yields)
            fig = px.bar(
                df, x="crop_name", y="total_yield",
                labels={"crop_name": "作物", "total_yield": "総収量"},
                title="作物別 総収量",
                color_discrete_sequence=["#FF8F00"],
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("収量一覧")
            display_df = df[["crop_name", "total_yield", "yield_unit",
                             "avg_yield", "count"]].copy()
            display_df.columns = ["作物", "総収量", "単位", "平均収量", "作付け数"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("収量データがありません")

    with tab3:
        wt_counts = db.get_work_type_counts()
        if wt_counts:
            df = pd.DataFrame(wt_counts)
            fig = px.pie(
                df, values="count", names="work_type",
                title="作業種別の割合",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("データがありません")


# ============================================================
# 管理者ページ: 作業記録入力
# ============================================================
def page_work_log_input():
    st.header("📝 作業記録入力")

    if not st.session_state.admin_mode:
        st.warning("🔒 管理者ログインが必要です")
        return

    # 作付け選択肢
    cycles = db.get_all_crop_cycles()
    cycle_options = {0: "（紐づけなし）"}
    for cy in cycles:
        label = (
            f"{cy['crop_name']}"
            f"{'（' + cy['variety'] + '）' if cy.get('variety') else ''}"
            f" [{cy.get('field_id') or '―'}] - {cy['status']}"
        )
        cycle_options[cy["id"]] = label

    with st.form("work_log_form", clear_on_submit=True):
        st.subheader("新しい作業記録")

        fc1, fc2 = st.columns(2)
        with fc1:
            work_date = st.date_input("作業日", value=date.today())
        with fc2:
            # 作業種別: 選択 or 自由入力
            type_choice = st.selectbox(
                "作業種別", WORK_TYPES + ["（手動入力）"]
            )

        if type_choice == "（手動入力）":
            work_type = st.text_input("作業種別を入力")
        else:
            work_type = type_choice

        fc3, fc4 = st.columns(2)
        with fc3:
            field_id = st.text_input("圃場ID", placeholder="例: d01, hs01")
        with fc4:
            row_id = st.text_input("畝ID", placeholder="例: 1, A")

        cycle_id = st.selectbox(
            "紐づける作付け",
            options=list(cycle_options.keys()),
            format_func=lambda x: cycle_options[x],
        )

        content = st.text_area("作業内容", placeholder="具体的な作業内容を記入")
        note = st.text_area("備考", placeholder="補足情報があれば記入")

        submitted = st.form_submit_button("✅ 登録", use_container_width=True)

        if submitted:
            if not work_type:
                st.error("作業種別を入力してください")
            else:
                db.create_work_log(
                    work_date=work_date.strftime("%Y-%m-%d"),
                    work_type=work_type,
                    cycle_id=cycle_id if cycle_id != 0 else None,
                    field_id=field_id or None,
                    row_id=row_id or None,
                    content=content or None,
                    note=note or None,
                )
                st.success("✅ 作業記録を登録しました！")

    # 最近の作業記録
    st.divider()
    st.subheader("最近の作業記録")
    recent = db.get_recent_work_logs(limit=20)
    if recent:
        df = pd.DataFrame(recent)
        display_cols = ["id", "work_date", "work_type", "crop_name",
                        "field_id", "content", "note"]
        existing_cols = [c for c in display_cols if c in df.columns]
        display_df = df[existing_cols].copy()
        col_rename = {
            "id": "ID", "work_date": "日付", "work_type": "作業",
            "crop_name": "作付け", "field_id": "圃場",
            "content": "内容", "note": "備考",
        }
        display_df.rename(columns=col_rename, inplace=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # 削除機能
        with st.expander("🗑️ 作業記録の削除"):
            del_id = st.number_input(
                "削除するIDを入力", min_value=1, step=1, key="del_log_id"
            )
            if st.button("削除実行", key="del_log_btn"):
                db.delete_work_log(del_id)
                st.success(f"ID {del_id} を削除しました")
                st.rerun()


# ============================================================
# 管理者ページ: 作付け登録・編集
# ============================================================
def page_crop_cycle_form():
    st.header("🌱 作付け登録・編集")

    if not st.session_state.admin_mode:
        st.warning("🔒 管理者ログインが必要です")
        return

    tab_new, tab_edit, tab_link = st.tabs([
        "➕ 新規登録", "✏️ 編集・結果入力", "🔗 作業記録の紐づけ"
    ])

    # --- 新規登録 ---
    with tab_new:
        with st.form("new_cycle_form", clear_on_submit=True):
            st.subheader("新しい作付け")

            nc1, nc2 = st.columns(2)
            with nc1:
                crop_name = st.text_input("作物名 *", placeholder="例: トマト")
            with nc2:
                variety = st.text_input("品種", placeholder="例: 桃太郎")

            nc3, nc4 = st.columns(2)
            with nc3:
                field_id = st.text_input(
                    "圃場ID", placeholder="例: d01", key="nc_field"
                )
            with nc4:
                row_id = st.text_input(
                    "畝ID", placeholder="例: 1", key="nc_row"
                )

            nc5, nc6 = st.columns(2)
            with nc5:
                start_date = st.date_input("開始日", value=date.today())
            with nc6:
                status = st.selectbox("ステータス", STATUS_OPTIONS, index=1)

            comment = st.text_area("コメント", key="nc_comment")

            if st.form_submit_button("✅ 登録", use_container_width=True):
                if not crop_name:
                    st.error("作物名を入力してください")
                else:
                    db.create_crop_cycle(
                        crop_name=crop_name,
                        variety=variety or None,
                        field_id=field_id or None,
                        row_id=row_id or None,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        status=status,
                        comment=comment or None,
                    )
                    st.success(f"✅ 「{crop_name}」の作付けを登録しました！")

    # --- 編集・結果入力 ---
    with tab_edit:
        cycles = db.get_all_crop_cycles()
        if not cycles:
            st.info("作付けが登録されていません")
        else:
            cycle_opts = {
                cy["id"]: (
                    f"{cy['crop_name']}"
                    f"{'（' + cy['variety'] + '）' if cy.get('variety') else ''}"
                    f" [{cy.get('field_id') or '―'}] - {cy['status']}"
                )
                for cy in cycles
            }
            edit_id = st.selectbox(
                "編集する作付け",
                options=list(cycle_opts.keys()),
                format_func=lambda x: cycle_opts[x],
                key="edit_cycle_select",
            )

            cy = db.get_crop_cycle(edit_id)
            if cy:
                with st.form("edit_cycle_form"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_crop = st.text_input("作物名", value=cy["crop_name"])
                    with ec2:
                        e_variety = st.text_input(
                            "品種", value=cy.get("variety") or ""
                        )

                    ec3, ec4 = st.columns(2)
                    with ec3:
                        e_field = st.text_input(
                            "圃場ID", value=cy.get("field_id") or "",
                            key="ec_field",
                        )
                    with ec4:
                        e_row = st.text_input(
                            "畝ID", value=cy.get("row_id") or "",
                            key="ec_row",
                        )

                    ec5, ec6 = st.columns(2)
                    with ec5:
                        e_start = st.date_input(
                            "開始日",
                            value=safe_date(cy.get("start_date")) or date.today(),
                            key="ec_start",
                        )
                    with ec6:
                        e_end = st.date_input(
                            "終了日",
                            value=safe_date(cy.get("end_date")),
                            key="ec_end",
                        )

                    e_status = st.selectbox(
                        "ステータス", STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(cy["status"])
                        if cy["status"] in STATUS_OPTIONS else 1,
                    )

                    st.divider()
                    st.subheader("🏆 収量・品質の記録")

                    rc1, rc2, rc3 = st.columns(3)
                    with rc1:
                        e_yield = st.number_input(
                            "収量", value=cy.get("yield_amount") or 0.0,
                            min_value=0.0, step=0.1,
                        )
                    with rc2:
                        e_unit = st.text_input(
                            "単位", value=cy.get("yield_unit") or "kg",
                        )
                    with rc3:
                        current_q = cy.get("quality_rating") or ""
                        q_idx = (
                            QUALITY_OPTIONS.index(current_q)
                            if current_q in QUALITY_OPTIONS else 0
                        )
                        e_quality = st.selectbox(
                            "品質評価", QUALITY_OPTIONS, index=q_idx,
                        )

                    e_q_note = st.text_area(
                        "品質メモ", value=cy.get("quality_note") or "",
                    )
                    e_comment = st.text_area(
                        "コメント", value=cy.get("comment") or "",
                        key="ec_comment",
                    )

                    bc1, bc2 = st.columns([3, 1])
                    with bc1:
                        save = st.form_submit_button(
                            "💾 保存", use_container_width=True
                        )
                    with bc2:
                        delete = st.form_submit_button(
                            "🗑️ 削除", use_container_width=True
                        )

                    if save:
                        db.update_crop_cycle(
                            edit_id,
                            crop_name=e_crop,
                            variety=e_variety or None,
                            field_id=e_field or None,
                            row_id=e_row or None,
                            start_date=e_start.strftime("%Y-%m-%d"),
                            end_date=(
                                e_end.strftime("%Y-%m-%d") if e_end else None
                            ),
                            status=e_status,
                            yield_amount=e_yield if e_yield > 0 else None,
                            yield_unit=e_unit,
                            quality_rating=e_quality or None,
                            quality_note=e_q_note or None,
                            comment=e_comment or None,
                        )
                        st.success("✅ 保存しました")
                        st.rerun()

                    if delete:
                        db.delete_crop_cycle(edit_id)
                        st.success("🗑️ 削除しました")
                        st.rerun()

    # --- 作業記録の紐づけ ---
    with tab_link:
        st.subheader("未紐づけの作業記録を作付けにリンク")

        cycles = db.get_all_crop_cycles()
        if not cycles:
            st.info("先に作付けを登録してください")
        else:
            cycle_opts = {
                cy["id"]: (
                    f"{cy['crop_name']}"
                    f"{'（' + cy['variety'] + '）' if cy.get('variety') else ''}"
                    f" [{cy.get('field_id') or '―'}]"
                )
                for cy in cycles
            }
            target_cycle = st.selectbox(
                "紐づけ先の作付け",
                options=list(cycle_opts.keys()),
                format_func=lambda x: cycle_opts[x],
                key="link_target",
            )

            unlinked = db.get_unlinked_work_logs()
            if unlinked:
                st.write(f"未紐づけの作業記録: {len(unlinked)} 件")
                for log in unlinked[:50]:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.write(
                            f"**{log['work_date']}** `{log['work_type']}`　"
                            f"{log.get('field_id') or ''}　"
                            f"{log.get('content') or ''}"
                        )
                    with col2:
                        if st.button("リンク", key=f"link_{log['id']}"):
                            db.link_work_log_to_cycle(log["id"], target_cycle)
                            st.success("紐づけました")
                            st.rerun()
            else:
                st.info("未紐づけの作業記録はありません")


# ============================================================
# 管理者ページ: CSVインポート
# ============================================================
def page_csv_import():
    st.header("📥 CSVインポート")

    if not st.session_state.admin_mode:
        st.warning("🔒 管理者ログインが必要です")
        return

    st.write(
        "既存の農作業記録CSVファイルをインポートします。"
        "インポートされたデータは作業記録として登録されます"
        "（作付けとの紐づけは後から行えます）。"
    )

    uploaded = st.file_uploader(
        "CSVファイルを選択", type=["csv"],
        help="Shift-JIS または UTF-8 のCSVファイルに対応"
    )

    if uploaded is not None:
        # エンコーディング自動判定
        raw = uploaded.read()
        uploaded.seek(0)

        df = None
        for enc in ["cp932", "shift_jis", "utf-8", "utf-8-sig", "latin1"]:
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc)
                break
            except (UnicodeDecodeError, Exception):
                continue

        if df is None:
            st.error("CSVの読み込みに失敗しました。エンコーディングを確認してください。")
            return

        st.subheader("📋 プレビュー")
        st.write(f"列数: {len(df.columns)}　行数: {len(df)}")
        st.dataframe(df.head(20), use_container_width=True)

        # カラムマッピング
        st.subheader("🔧 列の対応づけ")
        cols = ["（なし）"] + list(df.columns)

        mc1, mc2 = st.columns(2)
        with mc1:
            col_date = st.selectbox("日付の列", cols, index=min(1, len(cols) - 1))
            col_type = st.selectbox("作業種別の列", cols, index=min(2, len(cols) - 1))
            col_field = st.selectbox("圃場IDの列", cols, index=min(3, len(cols) - 1))
        with mc2:
            col_row = st.selectbox("畝IDの列", cols, index=min(4, len(cols) - 1))
            col_content = st.selectbox("内容の列", cols, index=min(5, len(cols) - 1))
            col_note = st.selectbox("備考の列", cols, index=min(6, len(cols) - 1))

        if st.button("📥 インポート実行", use_container_width=True):
            records = []
            prev_date = ""
            for _, row in df.iterrows():
                # 日付処理
                raw_date = ""
                if col_date != "（なし）":
                    raw_date = str(row.get(col_date, "")).strip()

                work_date = _convert_date(raw_date, prev_date)
                if work_date:
                    prev_date = work_date

                # 作業種別
                work_type = ""
                if col_type != "（なし）":
                    work_type = str(row.get(col_type, "")).strip()
                if not work_type or work_type == "nan":
                    work_type = "その他"

                # その他のフィールド
                field_id = _get_val(row, col_field)
                row_id = _get_val(row, col_row)
                content = _get_val(row, col_content)
                note = _get_val(row, col_note)

                # 空行スキップ
                if not work_date and not content:
                    continue

                records.append({
                    "work_date": work_date,
                    "work_type": work_type,
                    "field_id": field_id,
                    "row_id": row_id,
                    "content": content,
                    "note": note,
                })

            if records:
                count = db.import_csv_records(records)
                st.success(f"✅ {count} 件の作業記録をインポートしました！")
                st.balloons()
            else:
                st.warning("インポートするレコードがありませんでした")


def _convert_date(raw_date, prev_date):
    """日付文字列を YYYY-MM-DD 形式に変換"""
    if not raw_date or raw_date == "nan":
        return prev_date  # 空欄は前行の日付を引き継ぐ

    raw_date = raw_date.strip()

    # YY/MM/DD 形式
    if "/" in raw_date:
        parts = raw_date.split("/")
        if len(parts) == 3:
            try:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 100:
                    y += 2000
                return f"{y:04d}-{m:02d}-{d:02d}"
            except ValueError:
                pass

    # YYYY-MM-DD 形式（そのまま）
    if "-" in raw_date and len(raw_date) == 10:
        return raw_date

    # YYYYMMDD 形式 (8桁数値)
    if len(raw_date) == 8 and raw_date.isdigit():
        try:
            return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        except (ValueError, IndexError):
            pass

    return prev_date


def _get_val(row, col_name):
    """DataFrameの行から値を取得（なし/nan → None）"""
    if col_name == "（なし）":
        return None
    val = str(row.get(col_name, "")).strip()
    if val == "nan" or val == "":
        return None
    return val


# ============================================================
# 管理者ページ: 作業記録一覧・管理
# ============================================================
def page_work_log_list():
    st.header("📋 作業記録一覧")

    # フィルター
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        d_from = st.date_input("開始日", value=date.today() - timedelta(days=90),
                               key="wl_from")
    with fc2:
        d_to = st.date_input("終了日", value=date.today(), key="wl_to")
    with fc3:
        types = ["すべて"] + db.get_distinct_work_types()
        type_f = st.selectbox("作業種別", types, key="wl_type")
    with fc4:
        fields = ["すべて"] + db.get_distinct_fields()
        field_f = st.selectbox("圃場", fields, key="wl_field")

    logs = db.get_all_work_logs(
        date_from=d_from.strftime("%Y-%m-%d"),
        date_to=d_to.strftime("%Y-%m-%d"),
        work_type=type_f,
        field_id=field_f,
    )

    if logs:
        st.caption(f"{len(logs)} 件の作業記録")
        df = pd.DataFrame(logs)
        display_cols = ["id", "work_date", "work_type", "crop_name",
                        "field_id", "content", "note"]
        existing_cols = [c for c in display_cols if c in df.columns]
        display_df = df[existing_cols].copy()
        col_rename = {
            "id": "ID", "work_date": "日付", "work_type": "作業",
            "crop_name": "作付け", "field_id": "圃場",
            "content": "内容", "note": "備考",
        }
        display_df.rename(columns=col_rename, inplace=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("該当する作業記録がありません")


# ============================================================
# サイドバー & ルーティング
# ============================================================
with st.sidebar:
    st.markdown("## 🌾 農作業記録簿")
    st.divider()

    # 閲覧メニュー
    st.markdown("### 📖 閲覧")
    view_pages = [
        "📊 ダッシュボード",
        "🌱 作付け一覧",
        "📅 タイムライン",
        "📋 作業記録一覧",
        "📈 集計・分析",
    ]
    for p in view_pages:
        if st.button(p, key=f"nav_{p}", use_container_width=True):
            st.session_state.page = p

    st.divider()

    # 管理者セクション
    if not st.session_state.admin_mode:
        st.markdown("### 🔒 管理者")
        pw = st.text_input("パスワード", type="password", key="admin_pw")
        if st.button("ログイン", key="login_btn"):
            if pw == ADMIN_PASSWORD:
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    else:
        st.markdown("### 🔓 管理者メニュー")
        admin_pages = [
            "📝 作業記録入力",
            "🌱 作付け登録・編集",
            "📥 CSVインポート",
        ]
        for p in admin_pages:
            if st.button(p, key=f"nav_{p}", use_container_width=True):
                st.session_state.page = p

        st.divider()
        if st.button("🚪 ログアウト", key="logout_btn"):
            st.session_state.admin_mode = False
            st.session_state.page = "📊 ダッシュボード"
            st.rerun()

    # フッター
    st.divider()
    st.caption("農作業記録簿 v1.0")
    if st.session_state.admin_mode:
        st.caption("ローカル初期PW: farm2026")

# ============================================================
# ページルーティング
# ============================================================
page = st.session_state.page

if page == "📊 ダッシュボード":
    page_dashboard()
elif page == "🌱 作付け一覧":
    page_crop_cycles()
elif page == "📅 タイムライン":
    page_timeline()
elif page == "📋 作業記録一覧":
    page_work_log_list()
elif page == "📈 集計・分析":
    page_analytics()
elif page == "📝 作業記録入力":
    page_work_log_input()
elif page == "🌱 作付け登録・編集":
    page_crop_cycle_form()
elif page == "📥 CSVインポート":
    page_csv_import()
else:
    page_dashboard()
