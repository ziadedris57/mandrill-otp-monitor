import streamlit as st
import requests
import datetime
from collections import Counter
import re
import json

# Apply background styling and center layout
st.markdown("""
<style>
body {
    background: linear-gradient(to bottom right, #e0e0e0, #f7f7f7);
    display: flex;
    justify-content: center;
    text-align: center;
}
.block-container {
    margin: auto;
    max-width: 800px;
}
</style>
""", unsafe_allow_html=True)

# Navigation tabs
page = st.tabs(["Email Debugger", "Merchant Activation"])[0]

# Title
st.markdown("""
<h1 style='color:white; background-color:#003366; padding:20px; border-radius:10px; font-family:sans-serif;'>📧 TxM Simulator</h1>
""", unsafe_allow_html=True)

if page == "Email Debugger":
    # Input for API key (hidden)
    mandrill_api_key = st.secrets["MANDRILL_API_KEY"]

    # Input for customer email
    email = st.text_input("Enter Customer Email")

    # When submitted
    if st.button("Check Email Status"):
        if not email:
            st.warning("Please enter an email address.")
        else:
            # Get date 7 days ago
            date_from = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

            # Search Mandrill API for last 7 days
            search_payload = {
                "key": mandrill_api_key,
                "query": email,
                "date_from": date_from,
                "limit": 20
            }

            response = requests.post("https://mandrillapp.com/api/1.0/messages/search.json", json=search_payload)

            if response.status_code == 200:
                results = response.json()
                if not results:
                    st.info("No emails found in the last 7 days.")
                else:
                    # Count statuses
                    status_counts = Counter([msg.get('state') for msg in results])
                    st.subheader("📊 Email Summary")
                    st.write(f"Total Emails Found: {len(results)}")
                    for status, count in status_counts.items():
                        st.write(f"**{status.capitalize()}**: {count}")

                    # Show message details in styled cards
                    for msg in results:
                        state = msg.get("state")
                        status_color = "#eafbea" if state == "sent" else ("#fff8e5" if state == "soft-bounced" else "#fdeaea")

                        st.markdown(f"""
<div style='background-color:{status_color};padding:20px;margin:20px auto;border-radius:12px;font-family:sans-serif;border:1px solid #ccc;max-width:700px;'>
  <h4 style='margin-top:0;color:#003366;'>📨 Subject: {msg.get('subject')}</h4>
  <p style='color:#333;'><strong>Status:</strong> {'✅ Successfully delivered' if state == 'sent' else state}</p>
  <p style='color:#333;'><strong>Sent At:</strong> {datetime.datetime.fromtimestamp(msg.get('ts')).strftime('%Y-%m-%d %H:%M:%S')}</p>
  <p style='color:#333;'><strong>Opens:</strong> {msg.get('opens', 0)} | <strong>Clicks:</strong> {msg.get('clicks', 0)}</p>
""", unsafe_allow_html=True)

                        # Extract bounce reason for soft bounces
                        if state in ["bounced", "soft-bounced"]:
                            bounce_detail = (
                                msg.get("diag", "") or
                                msg.get("reject_reason", "") or
                                msg.get("metadata", {}).get("smtp_response", "") or
                                msg.get("metadata", {}).get("reason", "")
                            )
                            match = re.search(r"Recipient address rejected: (.*)", bounce_detail)
                            if match:
                                st.markdown(f"<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;'>⚠️ Bounce Reason: {match.group(1).strip()}</p>", unsafe_allow_html=True)
                            elif bounce_detail:
                                st.markdown(f"<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;'>⚠️ Bounce Detail: {bounce_detail.strip()}</p>", unsafe_allow_html=True)
                            else:
                                st.info("No bounce message details found.")

                        if state == "rejected":
                            st.markdown(f"<p style='color:#721c24;background:#f8d7da;padding:10px;border-radius:5px;'>❌ Rejected Reason: {msg.get('reject_reason')}</p>", unsafe_allow_html=True)
                            if st.button(f"Remove from Deny List: {email}"):
                                reject_payload = {
                                    "key": mandrill_api_key,
                                    "email": email
                                }
                                remove_response = requests.post("https://mandrillapp.com/api/1.0/rejects/delete.json", json=reject_payload)
                                if remove_response.status_code == 200:
                                    st.success("Email successfully removed from deny list.")
                                else:
                                    st.error("Failed to remove from deny list.")

                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error("Failed to contact Mandrill API. Check your API key or network.")

elif page == "Merchant Activation":
    st.subheader("🚀 Merchant Activation")
    st.write("This is a placeholder for merchant onboarding functionality.")
