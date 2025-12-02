import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
from streamlit.errors import StreamlitAPIException
from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(layout="wide", page_title="戦績閲覧", page_icon="📊")

# --- 定数定義 ---
SPREADSHEET_NAME_DISPLAY = "Waic-戦績"
try:
    if hasattr(st, 'secrets') and "spreadsheet_ids" in st.secrets and "war_record" in st.secrets["spreadsheet_ids"]:
        SPREADSHEET_ID = st.secrets["spreadsheet_ids"]["war_record"]
    else:
        SPREADSHEET_ID = "1V9guZQbpV8UDU_W2pC1WBsE1hOHqIO4yTsG8oGzaPQU"
        st.warning("⚠️ スプレッドシートIDがSecretsに設定されていません。デフォルト値を使用します。")
except Exception as e:
    SPREADSHEET_ID = "1V9guZQbpV8UDU_W2pC1WBsE1hOHqIO4yTsG8oGzaPQU"
    st.warning("⚠️ スプレッドシートIDがSecretsに設定されていません。デフォルト値を使用します。")
WORKSHEET_NAME = "シート1"
COLUMNS = ['season', 'date', 'environment', 
'my_deck', 'my_deck_type', 'opponent_deck', 'opponent_deck_type', 'first_second', 'result', 'finish_turn', 'memo']
SELECT_PLACEHOLDER = "--- 選択してください ---"
ALL_TYPES_PLACEHOLDER = "全タイプ"

# --- パスワード認証のための設定 ---
def get_app_password():
    try:
        if hasattr(st, 'secrets') and "app_credentials" in st.secrets and "password" in st.secrets["app_credentials"]:
            return st.secrets["app_credentials"]["password"]
    except Exception as e:
        pass
    st.warning("アプリケーションパスワードがSecretsに設定されていません。ローカルテスト用に 'test_password' を使用します。デプロイ時には必ずSecretsを設定してください。")
    return "test_password" 
CORRECT_PASSWORD = get_app_password()

# ★追加：クッキーマネージャを初期化
# 暗号化キーは st.secrets から取得することを強く推奨します。
# キー名は任意ですが、ここでは "cookie_encryption_key" としています。
# Streamlit Cloud の場合、Secretsに COOKIE_ENCRYPTION_KEY = "あなた自身の強力な秘密のキー" のように設定してください。
try:
    cookie_encryption_key = st.secrets.get("app_credentials", {}).get("cookie_encryption_key", "YOUR_FALLBACK_DEFAULT_KEY_12345")
except Exception as e:
    cookie_encryption_key = "YOUR_FALLBACK_DEFAULT_KEY_12345"
if cookie_encryption_key == "YOUR_FALLBACK_DEFAULT_KEY_12345":
    st.warning("クッキー暗号化キーがデフォルトのままです。Secretsに 'cookie_encryption_key' を設定してください。")

cookies = EncryptedCookieManager(
    password=cookie_encryption_key,
    # クッキーのプレフィックスやパスは必要に応じて設定できます
    # prefix="streamlit_auth_",
    # path="/",
)
if not cookies.ready(): # クッキーがロードされるまで待機 (通常は不要ですが、念のため)
    st.stop()

# --- Google Sheets 連携 ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

@st.cache_resource
def get_gspread_client():
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

# --- データ読み込み ---
def load_data(spreadsheet_id, worksheet_name):
    """スプレッドシートからデータを読み込み（キャッシュなし - 毎回最新データを取得）"""
    client = get_gspread_client()
    if client is None:
        st.error("Google Sheetsに接続できなかったため、データを読み込めません。認証情報を確認してください。")
        empty_df = pd.DataFrame(columns=COLUMNS)
        for col in COLUMNS: 
            if col == 'date': empty_df[col] = pd.Series(dtype='datetime64[ns]')
            elif col == 'finish_turn': empty_df[col] = pd.Series(dtype='Int64')
            else: empty_df[col] = pd.Series(dtype='object')
        return empty_df
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=False, header=0, na_filter=True) 
        if df.empty and worksheet.row_count > 0 and worksheet.row_values(1):
            header_row = worksheet.row_values(1)
            df = pd.DataFrame(columns=header_row)
            expected_header = COLUMNS
            actual_header_subset = list(df.columns)[:len(expected_header)]
            if not (actual_header_subset == expected_header or list(df.columns) == expected_header or set(COLUMNS).issubset(set(df.columns))):
                 st.warning(f"スプレッドシートのヘッダーが期待と異なります。\n期待(一部): {expected_header}\n実際(一部): {actual_header_subset}")

        temp_df = pd.DataFrame(columns=COLUMNS)
        for col in COLUMNS:
            if col in df.columns:
                temp_df[col] = df[col]
            else:
                if col == 'date': temp_df[col] = pd.Series(dtype='datetime64[ns]')
                elif col == 'finish_turn': temp_df[col] = pd.Series(dtype='Int64')
                else: temp_df[col] = pd.Series(dtype='object')
        df = temp_df

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if 'finish_turn' in df.columns:
            df['finish_turn'] = pd.to_numeric(df['finish_turn'], errors='coerce').astype('Int64')
        
        string_cols = ['my_deck_type', 'opponent_deck_type', 'my_deck', 'opponent_deck', 
                       'season', 'memo', 'first_second', 'result', 'environment']
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna('')
            else:
                df[col] = pd.Series(dtype='str').fillna('')
        
        df = df.reindex(columns=COLUMNS)

    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"スプレッドシート (ID: {spreadsheet_id}) が見つからないか、アクセス権がありません。共有設定を確認してください。")
        df = pd.DataFrame(columns=COLUMNS)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"ワークシート '{worksheet_name}' がスプレッドシート (ID: {spreadsheet_id}) 内に見つかりません。")
        df = pd.DataFrame(columns=COLUMNS)
    except Exception as e:
        st.error(f"Google Sheetsからのデータ読み込み中に予期せぬエラーが発生しました: {type(e).__name__}: {e}")
        df = pd.DataFrame(columns=COLUMNS)
    return df

# --- メイン処理 ---
def main():
    st.title(f"📊 {SPREADSHEET_NAME_DISPLAY} - 戦績閲覧")
    
    if SPREADSHEET_ID == "ここに実際の Waic-戦績 のスプレッドシートIDを貼り付け":
        st.error("コード内の SPREADSHEET_ID を、お使いのGoogleスプレッドシートの実際のIDに置き換えてください。")
        st.warning("スプレッドシートIDは、スプレッドシートのURLに含まれる長い英数字の文字列です。")
        st.code("https://docs.google.com/spreadsheets/d/【この部分がIDです】/edit")
        st.stop()
    
    # --- ▼▼▼ 認証処理の変更 ▼▼▼ ---
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # ★追加：アプリ起動時にクッキーを確認し、自動ログインを試みる
    if not st.session_state.authenticated: # まだst.session_stateで認証されていなければ
        try:
            stored_password_from_cookie = cookies.get('auth_password') # クッキーから保存されたパスワードを取得
            if stored_password_from_cookie and stored_password_from_cookie == CORRECT_PASSWORD:
                st.session_state.authenticated = True
                # 自動ログイン成功時は st.rerun() を呼ばない方がスムーズな場合がある
                # st.rerun() # 必要に応じて呼び出す
        except Exception as e:
            # クッキーのデコードエラーやその他の問題が発生した場合のフォールバック
            st.warning(f"クッキーの読み取り中にエラーが発生しました: {e}")
            pass # ログインフォームに進む

    if not st.session_state.authenticated:
        st.title("アプリへのログイン")
        login_col1, login_col2, login_col3 = st.columns([1,1,1])
        with login_col2:
            with st.form("login_form_main"):
                st.markdown("#### パスワードを入力してください")
                password_input = st.text_input("パスワード", type="password", key="password_input_field_main", label_visibility="collapsed")
                login_button = st.form_submit_button("ログイン")
                if login_button:
                    if password_input == CORRECT_PASSWORD:
                        st.session_state.authenticated = True
                        # ★追加：ログイン成功時にパスワードをクッキーに保存
                        cookies['auth_password'] = CORRECT_PASSWORD
                        # クッキーの有効期限を設定（例: 365日）
                        # cookies.set('auth_password', CORRECT_PASSWORD, expires_at=datetime.now() + timedelta(days=365))
                        # ↑ timedelta を使う場合は from datetime import timedelta が必要
                        # EncryptedCookieManager では set 時に expires_at を直接は指定できないようです。
                        # CookieManager の save メソッドでグローバルな有効期限を設定するか、
                        # ライブラリのドキュメントで詳細な有効期限設定方法を確認する必要があります。
                        # ここでは、ライブラリのデフォルトの有効期限（またはブラウザセッション）に依存します。
                        # より長期間の保持のためには、CookieManager の設定を調べるか、
                        # 単純にキーが存在し、CORRECT_PASSWORDと一致するかどうかで判断します。
                        # (EncryptedCookieManagerのデフォルトでは永続的なクッキーになることが多いです)
                        cookies.save() # 変更をクッキーに保存
                        st.rerun()
                    else:
                        st.error("パスワードが正しくありません。")
        st.stop()
    # --- ▲▲▲ 認証処理の変更ここまで ▲▲▲ ---

    # Cookieの初期化（認証後に実行）
    if not cookies.ready():
        st.warning("⏳ Cookieを初期化中...")
        st.stop()

    # データ読み込み
    df = load_data(SPREADSHEET_ID, WORKSHEET_NAME)
    
    # 戦績一覧
    st.header("📋 戦績一覧")
    if df.empty:
        st.info("まだ戦績データがありません。")
    else:
        display_columns = ['date', 'season', 'environment', 'my_deck', 'my_deck_type', 'opponent_deck', 'opponent_deck_type', 'first_second', 'result', 'finish_turn', 'memo']
        cols_to_display_actual = [col for col in display_columns if col in df.columns]
        df_display = df.copy()
        if 'date' in df_display.columns:
            df_display['date'] = pd.to_datetime(df_display['date'], errors='coerce')
            not_nat_dates = df_display.dropna(subset=['date'])
            nat_dates = df_display[df_display['date'].isna()]
            df_display_sorted = pd.concat([not_nat_dates.sort_values(by='date', ascending=False), nat_dates]).reset_index(drop=True)
            if pd.api.types.is_datetime64_any_dtype(df_display_sorted['date']):
                 df_display_sorted['date'] = df_display_sorted['date'].apply(
                     lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else None)
        else:
            df_display_sorted = df_display.reset_index(drop=True)
        st.dataframe(df_display_sorted[cols_to_display_actual], use_container_width=True)
        csv_export = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 戦績データをCSVでダウンロード", data=csv_export,
            file_name='game_records_download.csv', mime='text/csv',
        )

if __name__ == '__main__':
    main()