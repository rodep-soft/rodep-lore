import os
import yaml
import datetime

JST = datetime.timezone(datetime.timedelta(hours=9), "JST")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

DEFAULT_CONFIG = {
    "bot": {"command_prefix": "!"},
    "channels": {"attendance_channel_id": 0, "late_channel_ids": [1238834537417412770]},
    "roles": {
        "assign_unanswered_role": False,
        "unanswered_role_name": "未回答者",
        "target_role_name": "ROX-2026",
    },
    "schedule": {
        "send_check_time": "08:00",
        "remind_unanswered_time": "12:00",
        "aggregate_summary_time": "12:30",
    },
    "messages": {
        "saturday_question": "会議に参加しますか？",
        "weekday_question": "今日の活動に参加しますか？",
        "note": "\n\n⚠️ **回答できない場合や「未回答」に残る場合は、このチャンネルで連絡してください！**",
        "remind_title": "🔔 **【リマインド】**",
        "remind_body": "今日の出欠がまだ未回答です！回答をお願いします！",
    },
    "meetings": [],
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            # Merge with default config to ensure missing keys have defaults
            merged = DEFAULT_CONFIG.copy()
            for key, val in config.items():
                if isinstance(val, dict) and key in merged:
                    merged[key] = {**merged[key], **val}
                else:
                    merged[key] = val
            return merged
    except Exception as e:
        print(f"Error loading config.yaml: {e}, falling back to defaults")
        return DEFAULT_CONFIG


def save_config(config_data: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        print(f"Error saving config.yaml: {e}")
        return False


def parse_time(time_str: str, default_hour: int, default_minute: int) -> datetime.time:
    try:
        parts = time_str.split(":")
        return datetime.time(hour=int(parts[0]), minute=int(parts[1]), tzinfo=JST)
    except Exception:
        return datetime.time(hour=default_hour, minute=default_minute, tzinfo=JST)
