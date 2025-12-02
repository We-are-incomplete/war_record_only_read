# Streamlit Cloud Secrets 設定ガイド

## 📝 Streamlit Cloudでの設定手順

### 1. Streamlit Cloudにアクセス
1. [Streamlit Cloud](https://streamlit.io/cloud) にログイン
2. デプロイしたアプリを選択
3. 右上の **⚙️ Settings** をクリック

### 2. Secretsセクションを開く
1. 左メニューから **Secrets** を選択
2. エディタが表示されます

### 3. 以下の内容を貼り付け・編集

```toml
[gcp_service_account]
type = "service_account"
project_id = "あなたのプロジェクトID"
private_key_id = "あなたのプライベートキーID"
private_key = "-----BEGIN PRIVATE KEY-----\nあなたのプライベートキー\n-----END PRIVATE KEY-----\n"
client_email = "あなたのサービスアカウント@プロジェクト.iam.gserviceaccount.com"
client_id = "あなたのクライアントID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

[app_credentials]
password = "あなたの安全なパスワード"
cookie_encryption_key = "32文字以上の強力なランダム文字列"

[spreadsheet_ids]
war_record = "1V9guZQbpV8UDU_W2pC1WBsE1hOHqIO4yTsG8oGzaPQU"
player_data = "選手データのスプレッドシートID"
```

### 4. Save をクリック

---

## 🔐 各項目の説明

### `[gcp_service_account]`
Google Cloud Platformのサービスアカウント情報です。
- `service_account.json` ファイルの内容をコピーして貼り付けてください
- **注意**: private_key の改行は `\n` で表現されます

### `[app_credentials]`
アプリケーションの認証情報です。
- **password**: アプリにログインするためのパスワード
- **cookie_encryption_key**: クッキーを暗号化するためのキー（32文字以上推奨）

### `[spreadsheet_ids]`
各スプレッドシートのIDです。
- **war_record**: 戦績記録用のスプレッドシート
  - シート: シート1
  - 列: season, date, environment, my_deck, my_deck_type, opponent_deck, opponent_deck_type, first_second, result, finish_turn, memo
- **player_data**: 選手データ用のスプレッドシート（同じスプレッドシート内に2つのシート）
  - シート1「選手一覧」
    - 列: 選手名, TwitterID, 所属チーム, 通称
  - シート2「戦績一覧」
    - 列: 選手名, 大会名, 使用デッキ, 戦績, メモ

---

## 📍 スプレッドシートIDの取得方法

Google SheetsのURLから取得できます：

```
https://docs.google.com/spreadsheets/d/【ここがID】/edit
                                      ↑
                              この部分をコピー
```

例：
```
https://docs.google.com/spreadsheets/d/1V9guZQbpV8UDU_W2pC1WBsE1hOHqIO4yTsG8oGzaPQU/edit
```
この場合、IDは `1V9guZQbpV8UDU_W2pC1WBsE1hOHqIO4yTsG8oGzaPQU` です。

---

## 🏠 ローカル開発での設定

ローカルで開発する場合は、`.streamlit/secrets.toml` ファイルを作成してください：

1. `.streamlit/secrets.toml.example` をコピー
2. `.streamlit/secrets.toml` にリネーム
3. 実際の値を入力
4. **.gitignoreに含まれているので、Gitにコミットされません**

---

## ✅ 設定確認

設定が正しく反映されると：
- アプリ起動時に警告が表示されなくなります
- Google Sheetsからデータが正常に読み込まれます
- 選手データ検索ページでデータが表示されます

---

## 🔧 トラブルシューティング

### 「スプレッドシートIDがSecretsに設定されていません」と表示される
- Streamlit CloudのSecretsセクションで `[spreadsheet_ids]` が正しく設定されているか確認
- タイポがないか確認（war_record, player_data）

### 「Google Sheetsへの接続に失敗しました」と表示される
- `[gcp_service_account]` の内容が正しいか確認
- サービスアカウントにスプレッドシートへのアクセス権限があるか確認

### データが表示されない
- スプレッドシートIDが正しいか確認
- シート名が一致しているか確認（大文字小文字も区別されます）
