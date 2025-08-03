import streamlit as st
import requests
import datetime
from collections import Counter
import re
import hashlib

# -------------------- CONFIG & STYLE --------------------
st.set_page_config(page_title="Mandrill Email Debugger", layout="centered")

st.markdown("""
<style>
body {
    background: linear-gradient(to bottom right, #e0e0e0, #f7f7f7);
    text-align: center;
}
.block-container {
    margin: auto;
    max-width: 800px;
    font-family: sans-serif;
}
.card {
    background-color: #fff;
    padding: 20px;
    margin: 16px auto;
    border-radius: 12px;
    border: 1px solid #ccc;
    max-width: 700px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}
</style>
""", unsafe_allow_html=True)

# -------------------- STATE --------------------
if "remove_results" not in st.session_state:
    st.session_state.remove_results = {}  # per-message feedback
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

# -------------------- INPUTS --------------------
st.title("📬 Mandrill Email Debugger")
mandrill_api_key = st.secrets.get("MANDRILL_API_KEY", "")
email_input = st.text_input("Enter Customer Email", st.session_state.last_query).strip()

# persist search when button clicked
if st.button("Check Email Status"):
    st.session_state.last_query = email_input

email = st.session_state.last_query

# helper to validate minimal email shape
def is_valid_email(e):
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", e))

# -------------------- PROCESS --------------------
if not email:
    st.info("Enter an email and click 'Check Email Status'.")
    st.stop()

if not is_valid_email(email):
    st.error("The email you entered doesn't look valid.")
    st.stop()

# perform search
date_from = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
search_payload = {"key": mandrill_api_key, "query": email, "date_from": date_from, "limit": 50}
response = requests.post("https://mandrillapp.com/api/1.0/messages/search.json", json=search_payload)
if response.status_code != 200:
    st.error("Failed to contact Mandrill API. Check your API key or network.")
    st.stop()
results = response.json()

# exact-match filtering
exact_matches = [msg for msg in results if msg.get("email", "").lower() == email.lower()]
if not exact_matches:
    if results:
        st.info(f"No email found with exact address '{email}', but there are related results.")
    else:
        st.info(f"No emails found in the last 7 days for '{email}'.")
    st.stop()

# summary
st.subheader("📊 Email Summary")
st.write(f"Total Exact-Match Emails Found: {len(exact_matches)}")
status_counts = Counter([msg.get("state", "").lower() for msg in exact_matches])
for status, count in status_counts.items():
    st.write(f"**{status.capitalize()}**: {count}")

# render each
for msg in exact_matches:
    state = (msg.get("state") or "").lower()
    to_email = msg.get("email", "")
    subject = msg.get("subject") or "No subject"
    try:
        sent_time = datetime.datetime.fromtimestamp(msg.get("ts")).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        sent_time = "Unknown"
    opens = msg.get("opens", 0)
    clicks = msg.get("clicks", 0)

    if state == "sent":
        status_color = "#eafbea"
        readable_state = "✅ Successfully delivered"
    elif state == "rejected":
        status_color = "#fdeaea"
        readable_state = "Rejected"
    else:
        status_color = "#fff8e5"
        readable_state = state.capitalize() if state else "Unknown"

    extra_html = ""

    # soft-bounce or bounce-like
    if state not in ("sent", "rejected"):
        bounce_detail = (
            msg.get("diag", "") or
            msg.get("reject_reason", "") or
            msg.get("metadata", {}).get("smtp_response", "") or
            msg.get("metadata", {}).get("reason", "")
        )
        if bounce_detail:
            match = re.search(r"Recipient address rejected: (.*)", bounce_detail)
            if match:
                bounce_reason = match.group(1).strip()
                extra_html += f"""
<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;margin:5px 0;'>⚠️ Bounce Reason: {bounce_reason}</p>"""
            else:
                extra_html += f"""
<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;margin:5px 0;'>⚠️ Bounce Detail: {bounce_detail.strip()}</p>"""
        else:
            extra_html += f"""
<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;margin:5px 0;'>⚠️ Bounce: No detailed reason provided.</p>"""

    # rejected logic with remove from deny list
    if state == "rejected":
        reject_reason = msg.get("reject_reason", "Unknown reason")
        extra_html += f"""
<p style='color:#721c24;background:#f8d7da;padding:10px;border-radius:5px;margin:5px 0;'>🚫 Rejected: {reject_reason}</p>"""

        if isinstance(to_email, str) and "@" in to_email:
            msg_id = msg.get("_id", "")
            unique_key = f"{to_email}_{msg_id}"
            key_hash = hashlib.md5(unique_key.encode()).hexdigest()
            form_key = f"remove_form_{key_hash}"
            result_key = f"remove_result_{key_hash}"

            if result_key not in st.session_state.remove_results:
                st.session_state.remove_results[result_key] = None

            with st.form(key=form_key):
                submitted = st.form_submit_button("🧹 Remove from Deny List")
                if submitted:
                    reject_payload = {"key": mandrill_api_key, "email": to_email}
                    remove_response = requests.post(
                        "https://mandrillapp.com/api/1.0/rejects/delete.json",
                        json=reject_payload,
                    )
                    if remove_response.status_code == 200:
                        result = remove_response.json()
                        if result.get("deleted"):
                            st.session_state.remove_results[result_key] = f"✅ {to_email} successfully removed from deny list."
                        else:
                            st.session_state.remove_results[result_key] = f"⚠️ {to_email} was not on the deny list."
                    else:
                        st.session_state.remove_results[result_key] = "❌ Failed to contact Mandrill API for deny list removal."

            if st.session_state.remove_results.get(result_key):
                extra_html += f"<p style='margin-top:6px;font-weight:600;'>{st.session_state.remove_results[result_key]}</p>"

    # ---------- Render Card ----------
    st.markdown(f"""
<div class="card" style="background-color:{status_color};">
  <h4 style='margin-top:0;color:#003366;'>📨 Subject: {subject}</h4>
  <p style='margin:0;color:#333;'><strong>Status:</strong> {readable_state}</p>
  <p style='margin:0;color:#333;'><strong>Sent At:</strong> {sent_time}</p>
  <p style='margin:0;color:#333;'><strong>Opens:</strong> {opens} | <strong>Clicks:</strong> {clicks}</p>
  {extra_html}
</div>
""", unsafe_allow_html=True)
