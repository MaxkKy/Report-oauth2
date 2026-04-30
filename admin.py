import streamlit as st
from streamlit_oauth import OAuth2Component
import sqlite3
import qrcode
import io
import os

# --- 1. การตั้งค่าพื้นฐาน ---
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"
ADMIN_PASSWORD = "admin1234"  # 🔑 รหัสผ่านสำหรับ Login แบบ Manual (เปลี่ยนได้)
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app"
SCOPE = "email profile"

oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                        "https://accounts.google.com/o/oauth2/v2/auth", 
                        "https://oauth2.googleapis.com/token", 
                        "https://oauth2.googleapis.com/oauth2/v1/revoke")

# --- 2. ฟังก์ชันจัดการ Database ---
def init_db():
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, 
                  device TEXT, detail TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. ส่วนการตรวจสอบ Login ---
st.title("🛡️ ระบบจัดการ (Admin & Staff)")

if "user_email" not in st.session_state:
    st.subheader("เลือกวิธีการเข้าสู่ระบบ")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### แบบที่ 1: Google")
        result = oauth.authorize_button(
            name="Login with Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        )
        if result and "token" in result:
            st.session_state.user_email = result["token"].get("email")
            st.rerun()

    with col2:
        st.markdown("### แบบที่ 2: กรอกรหัสผ่าน")
        with st.form("manual_login"):
            email_input = st.text_input("Gmail")
            pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if email_input == ADMIN_EMAIL and pass_input == ADMIN_PASSWORD:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    # เช็คพนักงานใน DB
                    conn = sqlite3.connect('repairs.db')
                    c = conn.cursor()
                    c.execute("SELECT email FROM users WHERE email=?", (email_input,))
                    is_staff = c.fetchone()
                    conn.close()
                    if is_staff and pass_input == "1234": # รหัสผ่านกลางของพนักงาน
                        st.session_state.user_email = email_input
                        st.rerun()
                    else:
                        st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง")

else:
    # --- เมื่อ Login สำเร็จแล้ว ---
    user_email = st.session_state.user_email
    st.sidebar.success(f"ล็อกอินโดย: {user_email}")
    
    if st.sidebar.button("Log out"):
        del st.session_state.user_email
        st.rerun()

    # ตรวจสอบสิทธิ์
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email = ?", (user_email,))
    user_role_db = c.fetchone()
    conn.close()

    is_admin = (user_email == ADMIN_EMAIL) or (user_role_db and user_role_db[0] == 'admin')

    if is_admin:
        menu = st.sidebar.radio("เมนูจัดการ:", ["รายการแจ้งซ่อม", "จัดการรายชื่อพนักงาน", "สร้าง QR Code"])
        
        if menu == "รายการแจ้งซ่อม":
            st.header("📋 รายการแจ้งซ่อม")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM repairs ORDER BY id DESC")
            for r in c.fetchall():
                st.write(f"ID: {r[0]} | ห้อง: {r[2]} | อุปกรณ์: {r[3]} | สถานะ: **{r[5]}**")
                if r[5] == "รอดำเนินการ":
                    if st.button(f"ยืนยันว่าเสร็จสิ้น (ID {r[0]})"):
                        c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                        conn.commit()
                        st.rerun()
            conn.close()

        elif menu == "จัดการรายชื่อพนักงาน":
            st.header("👥 รายชื่อพนักงานที่มีสิทธิ์เข้าถึง")
            
            # ฟอร์มเพิ่มพนักงาน
            with st.form("add_staff"):
                new_email = st.text_input("ระบุ Gmail พนักงานใหม่")
                role = st.selectbox("สิทธิ์", ["staff", "admin"])
                if st.form_submit_button("เพิ่มพนักงาน"):
                    if new_email:
                        conn = sqlite3.connect('repairs.db')
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_email, role))
                        conn.commit()
                        conn.close()
                        st.success(f"เพิ่ม {new_email} เรียบร้อย!")
                        st.rerun()

            # แสดงรายชื่อพนักงานทั้งหมด
            st.subheader("พนักงานปัจจุบัน")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users")
            for u in c.fetchall():
                col1, col2 = st.columns([3,1])
                col1.write(f"📧 {u[0]} ({u[1]})")
                if col2.button("ลบ", key=u[0]):
                    c.execute("DELETE FROM users WHERE email = ?", (u[0],))
                    conn.commit()
                    st.rerun()
            conn.close()

        elif menu == "สร้าง QR Code":
            st.header("📲 สร้าง QR Code สำหรับส่งให้คนสแกน")
            qr_link = st.text_input("ลิงก์ที่จะให้ QR สแกนไป:", REDIRECT_URI)
            if st.button("Generate QR Code"):
                img = qrcode.make(qr_link)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                st.image(buf.getvalue(), caption="สแกนเพื่อเข้าสู่ระบบแจ้งซ่อม")

    else:
        st.warning("คุณเข้าสู่ระบบในฐานะพนักงานทั่วไป (Staff) หรือยังไม่ได้รับสิทธิ์ Admin")