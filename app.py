import streamlit as st
import requests
import datetime
from collections import Counter
import re

# Title
st.title("Mandrill OTP Monitor & Deny List Remover")

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

                # Show message details
                for msg in results:
                    st.write("---")
                    st.write(f"**Subject:** {msg.get('subject')}")
                    st.write(f"**Status:** {msg.get('state')}")
                    st.write(f"**Sent At:** {datetime.datetime.fromtimestamp(msg.get('ts')).strftime('%Y-%m-%d %H:%M:%S')}")

                    # Extract bounce reason for soft bounces
                    if msg.get("state") == "bounced":
                        raw_msg = msg.get("_id", "")  # Replace with actual field if bounce reason is elsewhere
                        bounce_detail = msg.get("diag", "") or msg.get("reject_reason", "") or ""
                        match = re.search(r"Recipient address rejected: (.*?)\n", bounce_detail)
                        if match:
                            st.warning(f"Bounce Reason: {match.group(1)}")
                        elif bounce_detail:
                            st.warning(f"Bounce Detail: {bounce_detail}")

                    if msg.get("state") == "rejected":
                        st.error(f"Rejected Reason: {msg.get('reject_reason')}")
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
        else:
            st.error("Failed to contact Mandrill API. Check your API key or network.")
