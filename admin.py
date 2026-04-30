import streamlit as st
from streamlit_oauth import OAuth2Component
import sqlite3
import qrcode
import io
import os

# --- 1. ตั้งค่าพื้นฐาน ---
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"
ADMIN_PASSWORD = "admin1234"
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app"
SCOPE = "email profile"

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

st.title("🛡️ ระบบจัดการหลังบ้าน")

if "user_email" not in st.session_state:
    st.subheader("กรุณาเข้าสู่ระบบ")
    col1, col2 = st.columns(2)
    with col1:
        result = oauth.authorize_button(name="Login with Google", icon="https://www.google.com/favicon.ico", 
                                        redirect_uri=REDIRECT_URI, scope=SCOPE)
        if result and "token" in result:
            st.session_state.user_email = result["token"].get("email").lower().strip()
            st.rerun()
    with col2:
        with st.form("manual"):
            e = st.text_input("Gmail").lower().strip()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if e == ADMIN_EMAIL.lower() and p == ADMIN_PASSWORD:
                    st.session_state.user_email = e
                    st.rerun()
                else:
                    st.error("อีเมลหรือรหัสผ่านผิด")
else:
    user_email = st.session_state.user_email
    st.sidebar.write(f"ล็อกอิน: {user_email}")
    
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE LOWER(email) = ?", (user_email,))
    db_res = c.fetchone()
    conn.close()
    
    is_admin = (user_email == ADMIN_EMAIL.lower()) or (db_res and db_res[0] == 'admin')

    if is_admin:
        menu = st.sidebar.radio("เมนู", ["รายการแจ้งซ่อม", "จัดการพนักงาน", "สร้าง QR Code"])
        
        if menu == "รายการแจ้งซ่อม":
            st.header("📋 รายการแจ้งซ่อมทั้งหมด")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            # เลือกข้อมูลทุกฟิลด์เพื่อความถูกต้อง
            c.execute("SELECT id, user_email, room, device, detail, status FROM repairs ORDER BY id DESC")
            for r in c.fetchall():
                with st.expander(f"ID: {r[0]} | ห้อง: {r[2]} | สถานะ: {r[5]}"):
                    st.write(f"**ผู้แจ้ง:** {r[1]}")
                    st.write(f"**อุปกรณ์:** {r[3]}")
                    st.write(f"**รายละเอียด:** {r[4]}")
                    if r[5] == "รอดำเนินการ":
                        if st.button("แจ้งว่าเสร็จสิ้น", key=f"adm_upd_{r[0]}"):
                            c.execute("UPDATE repairs SET status='เสร็จสิ้น' WHERE id=?", (r[0],))
                            conn.commit()
                            st.rerun()
            conn.close()

        elif menu == "จัดการพนักงาน":
            st.header("👥 จัดการสิทธิ์พนักงาน")
            with st.form("add"):
                new_e = st.text_input("ระบุ Gmail พนักงาน").lower().strip()
                new_r = st.selectbox("สิทธิ์", ["staff", "admin"])
                if st.form_submit_button("เพิ่มพนักงาน"):
                    conn = sqlite3.connect('repairs.db')
                    c = conn.cursor()
                    c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_e, new_r))
                    conn.commit()
                    conn.close()
                    st.success("บันทึกสำเร็จ")
                    st.rerun()
            
            st.subheader("รายชื่อพนักงาน")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users")
            for u in c.fetchall():
                st.write(f"📧 {u[0]} | สิทธิ์: **{u[1]}**")
            conn.close()

        elif menu == "สร้าง QR Code":
            st.header("สร้าง QR")
            url = st.text_input("ลิงก์เว็บ:", REDIRECT_URI)
            if st.button("Generate"):
                img = qrcode.make(url)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                st.image(buf.getvalue())
    else:
        st.error("คุณไม่มีสิทธิ์ Admin")

    if st.sidebar.button("Logout"):
        del st.session_state.user_email
        st.rerun()