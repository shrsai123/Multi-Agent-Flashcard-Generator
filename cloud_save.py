import threading
import requests
import streamlit as st
from dotenv import load_dotenv
import os

load_dotenv()

def _get_url():
    try:
        return st.secrets.get("WEBHOOK_URL") or os.getenv("WEBHOOK_URL", "")
    except Exception:
        return os.getenv("WEBHOOK_URL", "")

def _post(data: dict):
    url = _get_url()
    print("[cloud_save] url =", url)

    if not url:
        print("[cloud_save] WEBHOOK_URL not configured")
        return

    try:
        resp = requests.post(url, json=data, timeout=10)
        print("[cloud_save] status =", resp.status_code)
        print("[cloud_save] body =", resp.text)
    except Exception as e:
        print(f"[cloud_save] POST exception: {e}")

def save_eval_to_sheets(eval_data: dict):
    payload = {**eval_data, "type": "eval"}
    _post(payload)   # synchronous for debugging

def save_survey_to_sheets(survey_data: dict):
    payload = {**survey_data, "type": "survey"}
    _post(payload)   # synchronous for debugging