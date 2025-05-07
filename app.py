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

# Create two main tabs
tab1, tab2 = st.tabs(["Email Debugger", "Merchant Activation"])

with tab1:
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
                            if st.button(f"Remove from Deny List: {email} "):
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

with tab2:
    st.subheader("🚀 Merchant Activation")

    mandrill_api_key = st.secrets["MANDRILL_API_KEY"]
    date_from = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    search_payload = {
        "key": mandrill_api_key,
        "query": "Activate Tamara for your store",
        "date_from": date_from,
        "limit": 1000
    }

    response = requests.post("https://mandrillapp.com/api/1.0/messages/search.json", json=search_payload)

    if response.status_code == 200:
        results = response.json()
        sent_count = len(results)

        opened = [msg for msg in results if msg.get("opens", 0) > 0]
        soft_bounced = [msg for msg in results if msg.get("state") == "soft-bounced"]
        rejected = [msg for msg in results if msg.get("state") == "rejected"]
        delivered = [msg for msg in results if msg.get("state") == "sent"]

        open_rate = (len(opened) / sent_count * 100) if sent_count else 0

        st.markdown("""
        <div style='background-color:#ffffff;padding:30px 30px 10px 30px;margin-top:10px;border-radius:12px;border:1px solid #ccc;'>
            <h3>📊 Activation Email Funnel (Last 7 Days)</h3>
            <p><strong>Total Sent:</strong> {}</p>
            <p><strong>Opened:</strong> {} ({}%)</p>
            <p><strong>Rejected:</strong> {}</p>
            <p><strong>Soft Bounced:</strong> {}</p>
            <p><strong>Delivered:</strong> {}</p>
        </div>
        """.format(sent_count, len(opened), f"{open_rate:.1f}", len(rejected), len(soft_bounced), len(delivered)), unsafe_allow_html=True)

        # Rejected section with bulk remove button
        if rejected:
            st.markdown("---")
            st.subheader("❌ Rejected Emails")
            for msg in rejected:
                st.write(f"- {msg.get('email')}")

            if st.button("🧹 Remove All Rejected from Deny List"):
                reject_payloads = [{"email": msg.get("email"), "key": mandrill_api_key} for msg in rejected if msg.get("email")]
                removed = 0
                for payload in reject_payloads:
                    r = requests.post("https://mandrillapp.com/api/1.0/rejects/delete.json", json=payload)
                    if r.status_code == 200:
                        removed += 1
                st.success(f"✅ Removed {removed} emails from deny list.")

        # Soft bounced section with reason breakdown
        if soft_bounced:
            st.markdown("---")
            st.subheader("📛 Soft Bounced Reasons")
            reason_counts = defaultdict(int)
            for msg in soft_bounced:
                reason = (
                    msg.get("diag") or
                    msg.get("reject_reason") or
                    msg.get("metadata", {}).get("smtp_response") or
                    msg.get("metadata", {}).get("reason")
                )
                if reason:
                    match = re.search(r"Recipient address rejected: (.*)", reason)
                    if match:
                        reason = match.group(1).strip()
                    reason_counts[reason] += 1

            for reason, count in reason_counts.items():
                st.write(f"- **{reason}**: {count}")

        # Unopened funnel continues after
        unopened = [msg for msg in results if msg.get("opens", 0) == 0]
        if unopened:
            st.markdown("---")
            st.subheader("📪 Unopened Emails")
            for msg in unopened:
                st.write(f"- {msg.get('email')}")

            confirm = st.checkbox("Confirm you want to resend these emails")
            if confirm and st.button("📤 SEND AGAIN to All Unopened"):
                errors = []
                for msg in unopened:
                    msg_id = msg.get("_id")
                    if not msg_id:
                        continue

                    info_payload = {
                        "key": mandrill_api_key,
                        "id": msg_id
                    }
                    info_response = requests.post("https://mandrillapp.com/api/1.0/messages/info.json", json=info_payload)

                    if info_response.status_code == 200:
                        original = info_response.json()
                        html = original.get("html", "")
                        subject = original.get("subject", "")
                        to_email = original.get("email")

                        if html and subject and to_email:
                            send_payload = {
                                "key": mandrill_api_key,
                                "message": {
                                    "html": html,
                                    "subject": subject,
                                    "from_email": original.get("sender", "noreply@example.com"),
                                    "to": [{"email": to_email, "type": "to"}]
                                }
                            }
                            send_response = requests.post("https://mandrillapp.com/api/1.0/messages/send.json", json=send_payload)
                            if send_response.status_code != 200:
                                errors.append(to_email)
                        else:
                            errors.append(to_email or "Unknown")
                    else:
                        errors.append(msg.get("email", "Unknown"))

                if not errors:
                    st.success("✅ Emails resent successfully to all unopened users.")
                else:
                    st.warning(f"⚠️ Some emails failed to resend: {', '.join(errors)}")
            elif not confirm:
                st.info("Please check the confirmation box to resend emails.")
    else:
        st.error("Failed to fetch activation email data from Mandrill.")
