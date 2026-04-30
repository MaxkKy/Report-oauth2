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
# ใส่ URL ตรงๆ ห้ามใช้ os.getenv ครอบแบบเดิม
REDIRECT_URI = "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app" 
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"  

SCOPE = "email profile https://www.googleapis.com/auth/gmail.send"

oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                        "https://accounts.google.com/o/oauth2/v2/auth", 
                        "https://oauth2.googleapis.com/token", 
                        "https://oauth2.googleapis.com/oauth2/v1/revoke")

def init_db():
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, 
                  device TEXT, detail TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. หน้าจอหลัก ---
if "user" not in st.session_state:
    st.title("ระบบแจ้งซ่อมห้องเรียน")
    # แก้ไขจุดที่ผิด: redirect_uri ต้องเท่ากับตัวแปร REDIRECT_URI โดยไม่มี "" ครอบ
    result = oauth.authorize_button(name="Login with Google", icon="https://www.google.com/favicon.ico", 
                                    redirect_uri=REDIRECT_URI, scope=SCOPE)
    if result:
        st.session_state.user = result
        st.rerun()
else:
    token = st.session_token = st.session_state.user.get("token", {}).get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", 
                             headers={"Authorization": f"Bearer {token}"}).json()
    user_email = user_info.get('email').lower().strip() # ล้างค่าว่างและตัวพิมพ์ใหญ่
    
    st.sidebar.write(f"Logged in: **{user_email}**")
    
    # ดึงสิทธิ์จาก Database
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE LOWER(email) = ?", (user_email,))
    db_res = c.fetchone()
    conn.close()
    
    # เช็คว่าเป็น Admin หรือไม่
    is_admin = (user_email == ADMIN_EMAIL.lower()) or (db_res and db_res[0] == 'admin')

    tabs = st.tabs(["📢 แจ้งซ่อม", "📋 สถานะงานของฉัน", "🛠️ แอดมิน (จัดการงาน)"])
    
    with tabs[0]:
        st.header("แบบฟอร์มแจ้งซ่อม")
        with st.form("repair_form"):
            room = st.selectbox("เลือกห้อง", ["ห้อง 101", "ห้อง 102", "ห้อง 103"])
            device = st.selectbox("เลือกอุปกรณ์", ["Monitor", "แอร์", "เครื่อง PC", "อื่นๆ"])
            detail = st.text_area("รายละเอียดปัญหา")
            if st.form_submit_button("ส่งรายงาน"):
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("INSERT INTO repairs (user_email, room, device, detail, status) VALUES (?,?,?,?,?)",
                          (user_email, room, device, detail, "รอดำเนินการ"))
                conn.commit()
                conn.close()
                st.success("บันทึกข้อมูลเรียบร้อย!")

    with tabs[1]:
        st.header("สถานะรายการของคุณ")
        conn = sqlite3.connect('repairs.db')
        c = conn.cursor()
        c.execute("SELECT room, device, status FROM repairs WHERE user_email = ? ORDER BY id DESC", (user_email,))
        for row in c.fetchall():
            st.write(f"ห้อง: {row[0]} | อุปกรณ์: {row[1]} | สถานะ: **{row[2]}**")
        conn.close()

    with tabs[2]:
        if is_admin:
            st.header("จัดการรายการแจ้งซ่อม (Admin)")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            # ดึงข้อมูลทุก Column
            c.execute("SELECT id, user_email, room, device, detail, status FROM repairs ORDER BY id DESC")
            repairs = c.fetchall()
            for r in repairs:
                with st.expander(f"ID: {r[0]} | ห้อง: {r[2]} | สถานะ: {r[5]}"):
                    st.write(f"**ผู้แจ้ง:** {r[1]}")
                    st.write(f"**อุปกรณ์:** {r[3]}")
                    st.write(f"**รายละเอียด:** {r[4]}")
                    if r[5] == "รอดำเนินการ":
                        if st.button("✅ แก้ไขเสร็จสิ้น", key=f"app_upd_{r[0]}"):
                            c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                            conn.commit()
                            st.rerun()
            conn.close()
        else:
            st.error("ขออภัย คุณไม่มีสิทธิ์เข้าถึงหน้านี้")

    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()