import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
from streamlit.errors import StreamlitAPIException

st.set_page_config(layout="wide", page_title="選手データ検索")

# --- 定数定義 ---
# スプレッドシートIDをSecretsから取得（選手データ用）
if hasattr(st, 'secrets') and "spreadsheet_ids" in st.secrets:
    PLAYER_DATA_SPREADSHEET_ID = st.secrets["spreadsheet_ids"].get("player_data", "")
else:
    # ローカル開発時は空文字（画面で入力可能）
    PLAYER_DATA_SPREADSHEET_ID = ""

# シート名
PLAYER_LIST_WORKSHEET_NAME = "選手一覧"  # 選手一覧のシート名
RECORD_LIST_WORKSHEET_NAME = "戦績一覧"  # 戦績一覧のシート名

# 列名の定義
PLAYER_COLUMNS = ["選手名", "TwitterID", "所属チーム", "通称"]
RECORD_COLUMNS = ["選手名", "大会名", "使用デッキ", "戦績", "メモ"]

# --- Google Sheets 連携 ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

@st.cache_resource
def get_gspread_client():
    """Google Sheets クライアントを取得"""
    creds = None
    use_streamlit_secrets = False
    
    if hasattr(st, 'secrets'):
        try:
            if "gcp_service_account" in st.secrets:
                use_streamlit_secrets = True
        except StreamlitAPIException:
            pass
    
    if use_streamlit_secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        try:
            creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
        except Exception as e:
            st.error(f"サービスアカウントの認証情報ファイル (service_account.json) の読み込みに失敗しました: {e}")
            return None
    
    try:
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheetsへの接続に失敗しました: {e}")
        return None

def load_data_from_sheet(spreadsheet_id, worksheet_name, expected_columns=None):
    """スプレッドシートからデータを読み込み（キャッシュなし - 毎回最新データを取得）"""
    if not spreadsheet_id:
        return pd.DataFrame()
    
    client = get_gspread_client()
    if client is None:
        st.error("Google Sheetsに接続できませんでした。")
        return pd.DataFrame()
    
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=False, header=0, na_filter=True)
        
        # デバッグ情報
        st.info(f"シート「{worksheet_name}」から {len(df)} 行読み込みました。列: {list(df.columns)}")
        
        # 空の行を削除
        df = df.dropna(how='all')
        
        # 空の列を削除
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # 列名を確認・調整
        if expected_columns and not df.empty:
            # 既存の列名と期待する列名が異なる場合、列数が一致すれば名前を変更
            if list(df.columns)[:len(expected_columns)] != expected_columns:
                if len(df.columns) >= len(expected_columns):
                    st.warning(f"列名が一致しないため、自動的に変更します: {list(df.columns)[:len(expected_columns)]} → {expected_columns}")
                    df.columns = expected_columns + list(df.columns[len(expected_columns):])
        
        return df
    except PermissionError:
        st.error(f"🚫 シート「{worksheet_name}」へのアクセス権限がありません")
        st.warning("""
        **解決方法:**
        1. Google Sheetsを開く
        2. 右上の「共有」ボタンをクリック
        3. サービスアカウントのメールアドレスを追加
        4. 「編集者」または「閲覧者」権限を付与
        
        **サービスアカウントのメールアドレスは Secrets の `client_email` を確認してください**
        """)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"シート「{worksheet_name}」のデータ読み込みに失敗しました: {e}")
        with st.expander("詳細を表示"):
            import traceback
            st.code(traceback.format_exc())
        return pd.DataFrame()

# --- メイン画面 ---
def main():
    st.title("🔍 選手データ検索")
    
    # スプレッドシートIDの設定チェック
    if not PLAYER_DATA_SPREADSHEET_ID:
        st.warning("⚠️ スプレッドシートIDが設定されていません。")
        st.info("""
        **設定方法:**
        1. Streamlit CloudのSecretsに `spreadsheet_ids.player_data` を設定
        2. または、このファイル（`pages/01_選手データ検索.py`）を開いて直接IDを設定
        
        **スプレッドシートIDの取得方法:**
        - Google SheetsのURL: `https://docs.google.com/spreadsheets/d/【ここがID】/edit`
        
        **このスプレッドシート内に以下の2つのシートが必要です:**
        - `選手一覧`: 選手名、TwitterID、所属チーム、通称
        - `戦績一覧`: 選手名、大会名、使用デッキ、戦績、メモ
        """)
        
        # テスト用のスプレッドシートID入力
        with st.expander("一時的にスプレッドシートIDを入力"):
            temp_spreadsheet_id = st.text_input("スプレッドシートID", key="temp_spreadsheet_id")
            temp_player_sheet = st.text_input("選手一覧 シート名", value="選手一覧", key="temp_player_sheet")
            temp_record_sheet = st.text_input("戦績一覧 シート名", value="戦績一覧", key="temp_record_sheet")
            
            if st.button("読み込み"):
                if temp_spreadsheet_id:
                    st.session_state['temp_spreadsheet_id'] = temp_spreadsheet_id
                    st.session_state['temp_player_sheet'] = temp_player_sheet
                    st.session_state['temp_record_sheet'] = temp_record_sheet
                    st.rerun()
        
        if 'temp_spreadsheet_id' in st.session_state:
            spreadsheet_id = st.session_state['temp_spreadsheet_id']
            player_sheet = st.session_state['temp_player_sheet']
            record_sheet = st.session_state['temp_record_sheet']
        else:
            return
    else:
        spreadsheet_id = PLAYER_DATA_SPREADSHEET_ID
        player_sheet = PLAYER_LIST_WORKSHEET_NAME
        record_sheet = RECORD_LIST_WORKSHEET_NAME
    
    # データ読み込み（同じスプレッドシートの別シート）
    with st.spinner("データを読み込み中..."):
        player_df = load_data_from_sheet(spreadsheet_id, player_sheet, PLAYER_COLUMNS)
        record_df = load_data_from_sheet(spreadsheet_id, record_sheet, RECORD_COLUMNS)
    
    if player_df.empty and record_df.empty:
        st.warning("データがありません。スプレッドシートを確認してください。")
        return
    
    # データの統合（選手情報と戦績を結合）
    if not player_df.empty and not record_df.empty:
        # 選手名と通称の両方で戦績をマッチング
        # 1. 選手名での結合
        merged_df = pd.merge(
            record_df,
            player_df,
            on="選手名",
            how="left"
        )
        
        # 2. 通称でもマッチング（選手名が一致しなかった行を通称で再マッチ）
        if "通称" in player_df.columns:
            # まだマッチしていない戦績（TwitterIDが空の行）を抽出
            unmatched_mask = merged_df["TwitterID"].isna() if "TwitterID" in merged_df.columns else pd.Series([True] * len(merged_df))
            unmatched_records = record_df[unmatched_mask.values].copy()
            
            if not unmatched_records.empty:
                # 通称で再マッチング
                nickname_match = pd.merge(
                    unmatched_records,
                    player_df,
                    left_on="選手名",
                    right_on="通称",
                    how="left",
                    suffixes=('', '_from_nickname')
                )
                
                # マッチした行で元のmerged_dfを更新
                for idx, row in nickname_match.iterrows():
                    if pd.notna(row.get("選手名_from_nickname")):
                        # 元のインデックスを取得
                        original_idx = unmatched_records.index[unmatched_records["選手名"] == row["選手名"]].tolist()
                        if original_idx:
                            # 選手情報を更新
                            for col in ["TwitterID", "所属チーム", "通称"]:
                                if col in nickname_match.columns and col in merged_df.columns:
                                    merged_df.loc[original_idx[0], col] = row.get(col, row.get(f"{col}_from_nickname"))
        
        st.success(f"✅ 選手: {len(player_df)} 件、戦績: {len(record_df)} 件のデータを読み込みました")
    elif not player_df.empty:
        merged_df = player_df
        st.success(f"✅ 選手: {len(player_df)} 件のデータを読み込みました")
    else:
        merged_df = record_df
        st.success(f"✅ 戦績: {len(record_df)} 件のデータを読み込みました")
    
    # タブで表示を切り替え
    tab1, tab2, tab3 = st.tabs(["📋 統合データ", "👤 選手一覧", "🏆 戦績一覧"])
    
    with tab1:
        st.subheader("統合データ（選手情報 + 戦績）")
        if not player_df.empty:
            display_and_filter_data(merged_df, "merged", player_df)
        else:
            display_and_filter_data(merged_df, "merged")
    
    with tab2:
        st.subheader("選手一覧")
        if not player_df.empty:
            display_and_filter_data(player_df, "player", player_df)
        else:
            st.info("選手一覧データがありません")
    
    with tab3:
        st.subheader("戦績一覧")
        if not record_df.empty:
            # 戦績一覧では選手情報も含めたデータを表示
            if not player_df.empty:
                display_and_filter_data(merged_df, "record", player_df)
            else:
                display_and_filter_data(record_df, "record")
        else:
            st.info("戦績データがありません")

def display_and_filter_data(df, data_type, player_df=None):
    """データを表示・フィルタリングする共通関数
    
    Args:
        df: 表示するデータフレーム
        data_type: データタイプ（merged, player, record）
        player_df: 選手一覧データフレーム（戦績フィルタリング用）
    """
    if df.empty:
        st.info("データがありません")
        return
    
    # サイドバーでフィルタリングオプション
    st.sidebar.header(f"検索オプション ({data_type})")
    
    # 検索方法の選択
    search_method = st.sidebar.radio(
        "検索方法",
        ["キーワード検索", "列ごとに絞り込み"],
        help="全体を検索するか、特定の列で絞り込むかを選択",
        key=f"search_method_{data_type}"
    )
    
    filtered_df = df.copy()
    
    if search_method == "キーワード検索":
        # キーワード検索
        search_term = st.sidebar.text_input(
            "🔎 検索キーワード",
            placeholder="選手名、チーム、大会名など",
            help="すべての列を対象に検索します",
            key=f"search_{data_type}"
        )
        
        if search_term:
            # 選手名検索時に通称の記録も含める
            if player_df is not None and "選手名" in df.columns and "通称" in player_df.columns:
                # 1. 検索キーワードに一致する選手名を取得
                matching_players = player_df[
                    player_df["選手名"].astype(str).str.contains(search_term, case=False, na=False)
                ]
                
                # 2. その選手の通称も取得
                if not matching_players.empty:
                    player_names = matching_players["選手名"].tolist()
                    nicknames = matching_players["通称"].dropna().astype(str).tolist()
                    # 選手名と通称の両方で戦績を検索
                    all_names = list(set(player_names + nicknames))
                    mask_player = df["選手名"].isin(all_names)
                else:
                    mask_player = pd.Series([False] * len(df))
                
                # 3. 通称で検索した場合、その通称を持つ選手の名前も取得
                matching_nicknames = player_df[
                    player_df["通称"].astype(str).str.contains(search_term, case=False, na=False)
                ]
                if not matching_nicknames.empty:
                    player_names_from_nickname = matching_nicknames["選手名"].tolist()
                    nicknames_from_search = matching_nicknames["通称"].dropna().astype(str).tolist()
                    all_names_from_nickname = list(set(player_names_from_nickname + nicknames_from_search))
                    mask_nickname = df["選手名"].isin(all_names_from_nickname)
                else:
                    mask_nickname = pd.Series([False] * len(df))
                
                # 4. その他の列でも検索（大会名、デッキなど）
                mask_other = df.apply(
                    lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
                    axis=1
                )
                
                # すべてのマッチを統合
                filtered_df = df[mask_player | mask_nickname | mask_other]
            else:
                # player_dfがない場合は通常の検索
                mask = df.apply(
                    lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
                    axis=1
                )
                filtered_df = df[mask]
    
    else:  # 列ごとに絞り込み
        st.sidebar.subheader("列ごとの絞り込み")
        
        # 各列でフィルタリング
        for col in df.columns:
            unique_values = df[col].dropna().unique()
            if len(unique_values) > 0 and len(unique_values) <= 50:  # 選択肢が50以下の場合のみ
                selected_values = st.sidebar.multiselect(
                    f"{col}",
                    options=sorted(unique_values.astype(str)),
                    default=None,
                    key=f"filter_{col}_{data_type}"
                )
                if selected_values:
                    filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_values)]
    
    # 結果表示
    st.write(f"**検索結果: {len(filtered_df)} 件**")
    
    if not filtered_df.empty:
        # 表示する列を選択
        col1, col2 = st.columns([3, 1])
        with col1:
            display_columns = st.multiselect(
                "表示する列を選択",
                options=list(df.columns),
                default=list(df.columns),
                key=f"display_columns_{data_type}"
            )
        with col2:
            st.write("")  # スペーサー
            st.write("")  # スペーサー
            if st.button("🔄 リセット", use_container_width=True, key=f"reset_{data_type}"):
                st.cache_data.clear()
                keys_to_delete = [k for k in st.session_state.keys() if data_type in k]
                for key in keys_to_delete:
                    del st.session_state[key]
                st.rerun()
        
        if display_columns:
            # TwitterIDがある場合はリンク化したデータフレームを作成
            display_df = filtered_df[display_columns].copy()
            if 'TwitterID' in display_df.columns:
                # TwitterIDをリンク形式に変換
                def make_twitter_link(twitter_id):
                    if pd.isna(twitter_id) or str(twitter_id).strip() == "":
                        return ""
                    twitter_id = str(twitter_id).strip()
                    # @を除去（もしあれば）
                    twitter_id = twitter_id.lstrip('@')
                    return f"https://twitter.com/{twitter_id}"
                
                display_df['TwitterID'] = display_df['TwitterID'].apply(make_twitter_link)
            
            # データフレームを表示
            st.dataframe(
                display_df,
                use_container_width=True,
                height=500,
                column_config={
                    "TwitterID": st.column_config.LinkColumn(
                        "TwitterID",
                        help="クリックでTwitterプロフィールに遷移",
                        display_text="🐦 Twitter"
                    )
                } if 'TwitterID' in display_columns else None
            )
            
            # CSVダウンロード
            csv = filtered_df[display_columns].to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV形式でダウンロード",
                data=csv,
                file_name=f"{data_type}_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key=f"download_{data_type}"
            )
            
            # 統計情報
            with st.expander("📊 統計情報"):
                st.write("#### データの概要")
                # 数値列のみ統計を表示
                numeric_cols = filtered_df[display_columns].select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    st.write(filtered_df[display_columns].describe())
                else:
                    st.info("数値列がないため統計情報はありません")
                
                # 各列のユニーク値数
                st.write("#### 各列のユニーク値数")
                unique_counts = pd.DataFrame({
                    '列名': display_columns,
                    'ユニーク値数': [filtered_df[col].nunique() for col in display_columns]
                })
                st.dataframe(unique_counts, use_container_width=True)
        else:
            st.warning("表示する列を少なくとも1つ選択してください。")
    else:
        st.info("検索条件に一致するデータが見つかりませんでした。")
    
    # 元のデータの概要
    with st.expander("ℹ️ データセット情報"):
        st.write("#### 全データの列一覧")
        col_info = pd.DataFrame({
            '列名': df.columns,
            'データ型': df.dtypes.astype(str),
            '非欠損値数': df.count(),
            'ユニーク値数': [df[col].nunique() for col in df.columns]
        })
        st.dataframe(col_info, use_container_width=True)

if __name__ == "__main__":
    main()
