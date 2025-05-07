import streamlit as st
import requests
import datetime
from collections import Counter, defaultdict
import re
import json
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, ConnectionPatch

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
    st.subheader("📬 Email Debugger")
    mandrill_api_key = st.secrets["MANDRILL_API_KEY"]
    email = st.text_input("Enter Customer Email")

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
            if response.status_code == 200:
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
                        status_color = "#eafbea" if state == "sent" else (
                            "#fff8e5" if state == "soft-bounced" else (
                                "#fdeaea" if state == "rejected" else "#f0f0f0"
                            )
                        )
                    
                        # Extract common values
                        subject = msg.get("subject", "No Subject")
                        sent_at = datetime.datetime.fromtimestamp(msg.get("ts")).strftime("%Y-%m-%d %H:%M:%S")
                        opens = msg.get("opens", 0)
                        clicks = msg.get("clicks", 0)
                    
                        # Start the extra block (reason or button)
                        extra_html = ""
                    
                        # Soft bounce reason
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
                                extra_html = f"<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;'>⚠️ Bounce Reason: {bounce_reason}</p>"
                            elif bounce_detail:
                                extra_html = f"<p style='color:#8a6d3b;background:#fff3cd;padding:10px;border-radius:5px;'>⚠️ Bounce Detail: {bounce_detail.strip()}</p>"
                    
                        # Rejected emails – add deny list removal button
                        if state == "rejected":
                            extra_html += f"""
                            <form method='post'>
                                <button onclick="window.location.reload();"
                                style='background:#f44336;color:white;padding:8px 16px;border:none;border-radius:5px;margin-top:10px;'>
                                    Remove from Deny List
                                </button>
                            </form>
                            """
                    
                        # Delivered status label
                        readable_state = "✅ Successfully delivered" if state == "sent" else state
                    
                        # Final email card rendering
                        st.markdown(f"""
                        <div style='background-color:{status_color};padding:20px;margin:20px auto;
                                    border-radius:12px;font-family:sans-serif;border:1px solid #ccc;max-width:700px;'>
                          <h4 style='margin-top:0;color:#003366;'>📨 Subject: {subject}</h4>
                          <p style='color:#333;'><strong>Status:</strong> {readable_state}</p>
                          <p style='color:#333;'><strong>Sent At:</strong> {sent_at}</p>
                          <p style='color:#333;'><strong>Opens:</strong> {opens} | <strong>Clicks:</strong> {clicks}</p>
                          {extra_html}
                        </div>
                        """, unsafe_allow_html=True)

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
        unopened = [msg for msg in results if msg.get("opens", 0) == 0]
        delivered = [msg for msg in unopened if msg.get("state") == "sent"]
        open_rate = (len(opened) / sent_count * 100) if sent_count else 0

        st.markdown(f"""
        <div style='background: #2c3e50; color: #ffffff; padding: 30px; margin-top: 10px; border-radius: 16px; border: 1px solid #1a252f; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: sans-serif;'>
            <h3>📊 Activation Email Funnel (Last 7 Days)</h3>
            <p><strong>Total Sent:</strong> {sent_count}</p>
            <p><strong>Opened:</strong> {len(opened)} ({open_rate:.1f}%)</p>
            <p><strong>Rejected:</strong> {len(rejected)}</p>
            <p><strong>Soft Bounced:</strong> {len(soft_bounced)}</p>
            <p><strong>Delivered:</strong> {len(delivered)}</p>
        </div>
        """, unsafe_allow_html=True)

        # Funnel chart rendering
        st.markdown("---")
        st.subheader("🧭 Growth Flow Funnel")
        fig, ax = plt.subplots(figsize=(12, 6))
        positions = {
            "Sent": (0, 5),
            "Opened": (-2, 4),
            "Unopened": (2, 4),
            "Rejected": (-1.5, 3),
            "Soft Bounced": (2, 3),
            "Delivered": (5, 3),
        }
        levels = {
            "Sent": sent_count,
            "Opened": len(opened),
            "Unopened": len(unopened),
            "Rejected": len(rejected),
            "Soft Bounced": len(soft_bounced),
            "Delivered": len(delivered),
        }
        colors = {
            "Sent": "#dceefb",
            "Opened": "#d3f9d8",
            "Unopened": "#fff3cd",
            "Rejected": "#f8d7da",
            "Soft Bounced": "#ffe6cc",
            "Delivered": "#e2e3f3"
        }
        for stage, (x, y) in positions.items():
            width = 3.4 if y == 3 else 2.2
            box = FancyBboxPatch((x - width/2, y - 0.4), width, 0.8,
                                 boxstyle="round,pad=0.02", linewidth=1, edgecolor="#aaa",
                                 facecolor=colors[stage])
            ax.add_patch(box)
            ax.text(x, y, f"{stage}\n{levels[stage]}", ha="center", va="center", fontsize=11, weight="medium", color="#333", fontname="DejaVu Sans")
        def connect(parent, child):
            x1, y1 = positions[parent]
            x2, y2 = positions[child]
            ax.add_patch(ConnectionPatch(xyA=(x1, y1 - 0.4), coordsA=ax.transData,
                                         xyB=(x2, y2 + 0.4), coordsB=ax.transData,
                                         arrowstyle="-|>", color="#888", lw=1.3))
        connect("Sent", "Opened")
        connect("Sent", "Unopened")
        connect("Unopened", "Rejected")
        connect("Unopened", "Soft Bounced")
        connect("Unopened", "Delivered")
        ax.set_xlim(-4, 7)
        ax.set_ylim(2, 6)
        ax.axis("off")
        st.pyplot(fig)

        with st.expander("📪 Unopened Emails (click to expand)", expanded=False):
            unopened = [msg for msg in results if msg.get("opens", 0) == 0]
            for msg in unopened:
                st.write(f"- {msg.get('email')}")
            confirm = st.checkbox("Confirm you want to resend these emails")
            if confirm and st.button("📤 SEND AGAIN to All Unopened"):
                errors = []
                for msg in unopened:
                    msg_id = msg.get("_id")
                    if not msg_id:
                        continue
                    info_payload = {"key": mandrill_api_key, "id": msg_id}
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
