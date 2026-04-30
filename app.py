import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
import sqlite3
import os

# --- 1. ตั้งค่าพื้นฐาน ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app" 
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"  

oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                        "https://accounts.google.com/o/oauth2/v2/auth", 
                        "https://oauth2.googleapis.com/token", 
                        "https://oauth2.googleapis.com/oauth2/v1/revoke")

def init_db():
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS repairs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, device TEXT, detail TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    conn.close()

init_db()

if "user" not in st.session_state:
    st.title("ระบบแจ้งซ่อม")
    result = oauth.authorize_button(name="Login with Google", icon="https://www.google.com/favicon.ico", redirect_uri=REDIRECT_URI, scope="email profile")
    if result:
        st.session_state.user = result
        st.rerun()
else:
    token = st.session_state.user.get("token", {}).get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {token}"}).json()
    
    # ⚡ จุดแก้ไข: ล้างค่าอีเมลให้สะอาดที่สุด
    user_email = user_info.get('email').lower().strip()
    
    st.sidebar.write(f"Logged in: **{user_email}**")
    
    # เช็คสิทธิ์จาก DB
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE LOWER(email) = ?", (user_email,))
    db_res = c.fetchone()
    conn.close()
    
    # ⚡ เป็น Admin ถ้า: 1. อีเมลตรงกับตัวแปร หรือ 2. มีชื่อในตาราง users ว่าเป็น admin
    is_admin = (user_email == ADMIN_EMAIL.lower().strip()) or (db_res and db_res[0] == 'admin')

    tabs = st.tabs(["📢 แจ้งซ่อม", "📋 สถานะของฉัน", "🛠️ แอดมิน"])
    
    with tabs[0]:
        st.header("แบบฟอร์มแจ้งซ่อม")
        with st.form("f1"):
            room = st.selectbox("ห้อง", ["101", "102", "103"])
            dev = st.text_input("อุปกรณ์")
            det = st.text_area("อาการเสีย")
            if st.form_submit_button("ส่ง"):
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("INSERT INTO repairs (user_email, room, device, detail, status) VALUES (?,?,?,?,?)", (user_email, room, dev, det, "รอดำเนินการ"))
                conn.commit() ; conn.close()
                st.success("ส่งข้อมูลแล้ว")

    with tabs[1]:
        st.header("สถานะของคุณ")
        conn = sqlite3.connect('repairs.db')
        c = conn.cursor()
        c.execute("SELECT room, device, status FROM repairs WHERE user_email = ?", (user_email,))
        for r in c.fetchall(): st.write(f"{r[0]} | {r[1]} | {r[2]}")
        conn.close()

    with tabs[2]:
        if is_admin:
            st.header("จัดการงานซ่อม (Admin)")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT id, user_email, room, device, status FROM repairs WHERE status='รอดำเนินการ'")
            for r in c.fetchall():
                st.write(f"ID:{r[0]} | ผู้แจ้ง:{r[1]} | ห้อง:{r[2]} | {r[3]}")
                if st.button(f"ปิดงาน {r[0]}", key=f"app_{r[0]}"):
                    c.execute("UPDATE repairs SET status='เสร็จสิ้น' WHERE id=?", (r[0],))
                    conn.commit() ; st.rerun()
            conn.close()
        else:
            st.error("คุณไม่มีสิทธิ์เข้าถึง (ต้องเป็น Admin เท่านั้น)")

    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()