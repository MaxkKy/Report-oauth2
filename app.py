import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
import sqlite3
import os

# --- 1. การตั้งค่าพื้นฐาน ---
# ดึงค่าจาก Streamlit Secrets หรือ Environment Variable
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app" 
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"  

oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                        "https://accounts.google.com/o/oauth2/v2/auth", 
                        "https://oauth2.googleapis.com/token", 
                        "https://oauth2.googleapis.com/oauth2/v1/revoke")

def init_db():
    conn = sqlite3.connect('repairs.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, device TEXT, detail TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    return conn

conn = init_db()

if "user" not in st.session_state:
    st.title("🛠️ ระบบแจ้งซ่อมอุปกรณ์")
    st.info("กรุณาเข้าสู่ระบบด้วย Google Account เพื่อดำเนินการ")
    result = oauth.authorize_button(name="Login with Google", icon="https://www.google.com/favicon.ico", redirect_uri=REDIRECT_URI, scope="email profile")
    if result:
        st.session_state.user = result
        st.rerun()
else:
    token = st.session_state.user.get("token", {}).get("access_token")
    # ดึงข้อมูลโปรไฟล์จาก Google
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {token}"}).json()
    user_email = user_info.get('email').lower().strip()
    
    st.sidebar.success(f"ล็อกอินโดย: {user_email}")
    
    # เช็คสิทธิ์จาก DB
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE LOWER(email) = ?", (user_email,))
    db_res = c.fetchone()
    
    is_admin = (user_email == ADMIN_EMAIL.lower().strip()) or (db_res and db_res[0] == 'admin')

    tabs = st.tabs(["📢 แจ้งซ่อม", "📋 สถานะของฉัน", "🛠️ แผงควบคุมแอดมิน"])
    
    with tabs[0]:
        st.header("แบบฟอร์มแจ้งซ่อม")
        with st.form("repair_form", clear_on_submit=True):
            room = st.selectbox("ห้องที่เกิดปัญหา", ["101", "102", "103", "104", "ห้องประชุม"])
            dev = st.text_input("ชื่ออุปกรณ์ (เช่น แอร์, โปรเจคเตอร์)")
            det = st.text_area("อาการเสียโดยละเอียด")
            if st.form_submit_button("ส่งข้อมูลแจ้งซ่อม"):
                if dev and det:
                    c.execute("INSERT INTO repairs (user_email, room, device, detail, status) VALUES (?,?,?,?,?)", 
                              (user_email, room, dev, det, "รอดำเนินการ"))
                    conn.commit()
                    st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")

    with tabs[1]:
        st.header("ประวัติการแจ้งซ่อมของคุณ")
        c.execute("SELECT room, device, status, detail FROM repairs WHERE user_email = ? ORDER BY id DESC", (user_email,))
        rows = c.fetchall()
        if rows:
            for r in rows:
                with st.expander(f"{r[0]} | {r[1]} - สถานะ: {r[2]}"):
                    st.write(f"รายละเอียด: {r[3]}")
        else:
            st.write("ยังไม่มีประวัติการแจ้งซ่อม")

    with tabs[2]:
        if is_admin:
            st.header("จัดการงานซ่อม (สำหรับ Admin)")
            c.execute("SELECT id, user_email, room, device, status FROM repairs WHERE status='รอดำเนินการ'")
            admin_rows = c.fetchall()
            for r in admin_rows:
                col1, col2 = st.columns([3, 1])
                col1.write(f"**ID {r[0]}** | ห้อง {r[2]} | {r[3]} (แจ้งโดย: {r[1]})")
                if col2.button(f"ปิดงาน #{r[0]}", key=f"btn_close_{r[0]}"):
                    c.execute("UPDATE repairs SET status='เสร็จสิ้น' WHERE id=?", (r[0],))
                    conn.commit()
                    st.rerun()
        else:
            st.error("เฉพาะผู้ดูแลระบบเท่านั้นที่เข้าถึงส่วนนี้ได้")

    if st.sidebar.button("Log out"):
        del st.session_state.user
        st.rerun()