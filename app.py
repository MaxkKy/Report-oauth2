import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
import base64
import sqlite3
from email.message import EmailMessage
import os
# --- 1. ตั้งค่าพื้นฐาน ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app/", "http://localhost:8501") # เพิ่มบรรทัดนี้
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"  # เปลี่ยนเป็นอีเมลของคุณเพื่อใช้สิทธิ์ Admin

SCOPE = "email profile https://www.googleapis.com/auth/gmail.send"

oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                        "https://accounts.google.com/o/oauth2/v2/auth", 
                        "https://oauth2.googleapis.com/token", 
                        "https://oauth2.googleapis.com/oauth2/v1/revoke")

# --- 2. ตั้งค่า Database ---
def init_db():
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, 
                  device TEXT, detail TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. ฟังก์ชันส่งเมล ---
def send_email_via_gmail_api(access_token, room, message_content):
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    msg = EmailMessage()
    msg.set_content(message_content)
    msg['Subject'] = f"🚨 แจ้งซ่อม: {room}"
    msg['To'] = ADMIN_EMAIL
    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"raw": raw_msg})
    return response.status_code == 200

# --- 4. หน้าจอหลัก ---
if "user" not in st.session_state:
    st.title("ระบบแจ้งซ่อมห้องเรียน")
    result = oauth.authorize_button(name="Login with Google", icon="https://www.google.com/favicon.ico", 
                                    redirect_uri="redirect_uri=REDIRECT_URI", scope=SCOPE)
    if result:
        st.session_state.user = result
        st.rerun()
else:
    token = st.session_state.user.get("token", {}).get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", 
                             headers={"Authorization": f"Bearer {token}"}).json()
    user_email = user_info.get('email')
    
    st.sidebar.write(f"Logged in: **{user_email}**")
    
    # --- ระบบ Tabs ---
    tabs = st.tabs(["📢 แจ้งซ่อม", "📋 สถานะงานของฉัน", "🛠️ แอดมิน (จัดการงาน)"])
    
    # แท็บ 1: แจ้งซ่อม
    with tabs[0]:
        st.header("แบบฟอร์มแจ้งซ่อม")
        with st.form("repair_form"):
            room = st.selectbox("เลือกห้อง", ["ห้อง 101", "ห้อง 102", "ห้อง 103"])
            device = st.selectbox("เลือกอุปกรณ์", ["Monitor", "แอร์", "เครื่อง PC", "อื่นๆ"])
            detail = st.text_area("รายละเอียดปัญหา")
            if st.form_submit_button("ส่งรายงาน"):
                # บันทึกลง Database
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("INSERT INTO repairs (user_email, room, device, detail, status) VALUES (?,?,?,?,?)",
                          (user_email, room, device, detail, "รอดำเนินการ"))
                conn.commit()
                conn.close()
                # ส่งอีเมล
                content = f"ผู้แจ้ง: {user_email}\nห้อง: {room}\nอุปกรณ์: {device}\nรายละเอียด: {detail}"
                send_email_via_gmail_api(token, room, content)
                st.success("บันทึกข้อมูลและส่งอีเมลแจ้งแอดมินแล้ว!")

    # แท็บ 2: ดูสถานะของตัวเอง
    with tabs[1]:
        st.header("สถานะรายการของคุณ")
        conn = sqlite3.connect('repairs.db')
        c = conn.cursor()
        c.execute("SELECT room, device, status FROM repairs WHERE user_email = ? ORDER BY id DESC", (user_email,))
        for row in c.fetchall():
            st.write(f"ห้อง: {row[0]} | อุปกรณ์: {row[1]} | สถานะ: **{row[2]}**")
        conn.close()

    # แท็บ 3: หน้า Admin
    with tabs[2]:
        if user_email == ADMIN_EMAIL:
            st.header("จัดการรายการแจ้งซ่อม (Admin)")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT id, user_email, room, device, status FROM repairs ORDER BY id DESC")
            repairs = c.fetchall()
            for r in repairs:
                col1, col2 = st.columns([3, 1])
                col1.write(f"**ห้อง:** {r[2]} | **อุปกร์:** {r[3]} | **สถานะ:** {r[4]}")
                if r[4] == "รอดำเนินการ":
                    if col2.button("✅ เสร็จสิ้น", key=f"upd_{r[0]}"):
                        c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                        conn.commit()
                        st.rerun()
            conn.close()
        else:
            st.warning("คุณไม่มีสิทธิ์เข้าถึงหน้านี้ (เฉพาะ Admin เท่านั้น)")

    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()