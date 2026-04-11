import json
import threading
import streamlit as st
 
def _get_url():
    try:
        return st.secrets.get("WEBHOOK_URL", "")
    except Exception:
        return ""
 
def _post(data):
    """POST data in a background thread so it doesn't block the UI."""
    url = _get_url()
    if not url:
        return
    try:
        import requests
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"[cloud_save] POST failed: {e}")
 
def save_eval_to_sheets(eval_data: dict):
    """Send full eval export to the webhook."""
    payload = {**eval_data, "type": "eval"}
    threading.Thread(target=_post, args=(payload,), daemon=True).start()
 
def save_survey_to_sheets(survey_data: dict):
    """Send survey response to the webhook."""
    payload = {**survey_data, "type": "survey"}
    threading.Thread(target=_post, args=(payload,), daemon=True).start()
 