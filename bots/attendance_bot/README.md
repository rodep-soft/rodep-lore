# 出欠確認Bot (Attendance Bot)

Discordでメンバーの出欠状況を自動確認・集計・リマインドするBotです。

## 概要

- **出欠フォーム自動配信**: 設定した時間（デフォルト 08:00）にボタン付き出欠フォームを配信
- **未回答者リマインド**: 設定した時間（デフォルト 12:00）に未回答者へ一時ロール（`未回答者`）を付与してメンション
- **未回答者ロール解除**: 
  - ボタンで出欠を入力したとき
  - 遅刻欠席連絡用チャンネル（または出欠確認用チャンネル）で発言したとき
- **集計結果送信**: 設定した時間（デフォルト 12:30）に画像付き集計結果を送信

---

## 設定ファイル (`config.yaml`)

Botの挙動は `config.yaml` で柔軟にカスタマイズできます。

```yaml
# ボットの基本設定
bot:
  command_prefix: "!"

# チャンネルID設定
channels:
  attendance_channel_id: 0  # .envのCHANNEL_IDが存在しない場合のデフォルト
  late_channel_ids:
    - 1238834537417412770  # 遅刻欠席連絡用チャンネルIDリスト

# ロール設定
roles:
  unanswered_role_name: "未回答者"
  target_role_name: "ROX-2026"

# スケジュール設定 (JST 24時間表記 HH:MM)
schedule:
  send_check_time: "08:00"
  remind_unanswered_time: "12:00"
  aggregate_summary_time: "12:30"

# メッセージ文面設定
messages:
  saturday_question: "会議に参加しますか？"
  weekday_question: "今日の活動に参加しますか？"
  note: "\n\n⚠️ **回答できない場合や「未回答」に残る場合は、このチャンネルで連絡してください！**"
  remind_title: "🔔 **【リマインド】**"
  remind_body: "今日の出欠がまだ未回答です！回答をお願いします！"
```

### 設定ファイルの変更反映
Bot起動中に `config.yaml` を変更した場合は、管理者権限を持つユーザーが Discord 上で `!reload_config` コマンドを実行することで設定を即座に再読み込みできます。
