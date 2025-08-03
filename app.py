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
</style>
""", unsafe_allow_html=True)

# -------------------- INPUTS --------------------
st.title("📬 Email Debugger")
mandrill_api_key = st.secrets["MANDRILL_API_KEY"]
email = st.text_input("Enter Customer Email")

# -------------------- PROCESS --------------------
if st.button("Check Email Status"):
    if not email:
        st.warning("Please enter an email address.")
    else:
        date_from = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        search_payload = {
            "key": mandrill_api_key,
            "query": email,
            "date_from": date_from,
            "limit": 20
        }
        response = requests.post("https://mandrillapp.com/api/1.0/messages/search.json", json=search_payload)

        if response.status_code != 200:
            st.error("Failed to contact Mandrill API. Check your API key or network.")
        else:
            results = response.json()
            if not results:
                st.info("No emails found in the last 7 days.")
            else:
                status_counts = Counter([msg.get('state') for msg in results])

                st.subheader("📊 Email Summary")
                st.write(f"Total Emails Found: {len(results)}")
                for status, count in status_counts.items():
                    st.write(f"**{status.capitalize()}**: {count}")

                for msg in results:
                    state = msg.get("state")
                    to_email = msg.get("email")
                    subject = msg.get("subject")
                    sent_time = datetime.datetime.fromtimestamp(msg.get("ts")).strftime('%Y-%m-%d %H:%M:%S')
                    opens = msg.get("opens", 0)
                    clicks = msg.get("clicks", 0)

                    status_color = "#eafbea" if state == "sent" else ("#fff8e5" if state == "soft-bounced" else "#fdeaea")
                    extra_html = ""

                    # Soft Bounced Reason
                    if state == "soft-bounced":
                        bounce_detail = (
                            msg.get("diag", "") or
                            msg.get("reject_reason", "") or
                            msg.get("metadata", {}).get("smtp_response", "") or
                            msg.get("metadata", {}).get("reason", "")
                        )
                        match = re.search(r"Recipient address rejected: (.*)", bounce_detail)
                        if match:
                            bounce_reason = match.group(1).strip()
                            extra_html += f"""
<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;'>⚠️ Bounce Reason: {bounce_reason}</p>
"""
                        elif bounce_detail:
                            extra_html += f"""
<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;'>⚠️ Bounce Detail: {bounce_detail.strip()}</p>
"""

                    # Rejected with Deny List Button
                    if state == "rejected":
                        key_hash = hashlib.md5(to_email.encode()).hexdigest()
                        button_key = f"remove_deny_{key_hash}"
                        if st.button("🧹 Remove from Deny List", key=button_key):
                            reject_payload = {"key": mandrill_api_key, "email": to_email}
                            remove_response = requests.post("https://mandrillapp.com/api/1.0/rejects/delete.json", json=reject_payload)
                            if remove_response.status_code == 200:
                                st.success("Email successfully removed from deny list.")
                            else:
                                st.error("Failed to remove from deny list.")

                    st.markdown(f"""
<div style='background-color:{status_color};padding:20px;margin:20px auto;border-radius:12px;font-family:sans-serif;border:1px solid #ccc;max-width:700px;'>
  <h4 style='margin-top:0;color:#003366;'>📨 Subject: {subject}</h4>
  <p style='color:#333;'><strong>Status:</strong> {'✅ Successfully delivered' if state == 'sent' else state}</p>
  <p style='color:#333;'><strong>Sent At:</strong> {sent_time}</p>
  <p style='color:#333;'><strong>Opens:</strong> {opens} | <strong>Clicks:</strong> {clicks}</p>
  {extra_html}
</div>
""", unsafe_allow_html=True)
