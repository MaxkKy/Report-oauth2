import streamlit as st
from streamlit_oauth import OAuth2Component
import requests
import sqlite3
import qrcode
import io
import os

# --- 1. ตั้งค่าพื้นฐาน ---
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th" # อีเมลของคุณจะได้สิทธิ์ Admin อัตโนมัติ
SCOPE = "email profile"

oauth = OAuth2Component(CLIENT_ID, CLIENT_SECRET, 
                        "https://accounts.google.com/o/oauth2/v2/auth", 
                        "https://oauth2.googleapis.com/token", 
                        "https://oauth2.googleapis.com/oauth2/v1/revoke")

# --- 2. ตั้งค่า Database ---
def init_db():
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    # ตารางแจ้งซ่อม
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, 
                  device TEXT, detail TEXT, status TEXT)''')
    # ตารางเก็บบัญชีพนักงาน (เพิ่มใหม่)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. หน้า UI ---
st.title("ระบบจัดการสำหรับแจ้งซ่อมออนไลน์")

if "user" not in st.session_state:
    result = oauth.authorize_button(name="Login with Google", icon="https://www.google.com/favicon.ico", 
                                    redirect_uri="http://localhost:8501", scope=SCOPE)
    if result:
        st.session_state.user = result
        st.rerun()
else:
    token = st.session_state.user.get("token", {}).get("access_token")
    user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", 
                             headers={"Authorization": f"Bearer {token}"}).json()
    email = user_info.get('email')

    # --- ตรวจสอบสิทธิ์การเข้าใช้งาน ---
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email = ?", (email,))
    db_user = c.fetchone()
    conn.close()

    # ให้สิทธิ์ ADMIN_EMAIL เป็น admin เสมอ หรือคนที่มี role='admin' ในฐานข้อมูล
    is_admin = (email == ADMIN_EMAIL) or (db_user and db_user[0] == 'admin')
    # เป็นพนักงาน (staff)
    is_staff = db_user and db_user[0] == 'staff'

    # --- ส่วนของ Admin ---
    if is_admin:
        st.sidebar.subheader("🛠️ Admin Panel")
        menu = st.sidebar.radio("เมนูจัดการ:", ["รายการแจ้งซ่อม", "จัดการบัญชีพนักงาน", "สร้าง QR Code"])
        
        if menu == "รายการแจ้งซ่อม":
            st.header("จัดการสถานะงาน")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM repairs")
            for r in c.fetchall():
                st.write(f"ID: {r[0]} | ห้อง: {r[2]} | {r[3]} | สถานะ: **{r[5]}**")
                if r[5] == "รอดำเนินการ":
                    if st.button(f"เปลี่ยนเป็นเสร็จสิ้น (ID {r[0]})", key=f"upd_{r[0]}"):
                        c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                        conn.commit()
                        st.rerun()
            conn.close()
            
        elif menu == "จัดการบัญชีพนักงาน":
            st.header("👤 เพิ่มและจัดการบัญชีพนักงาน")
            with st.form("add_user_form"):
                new_email = st.text_input("ใส่อีเมลพนักงานที่ต้องการอนุญาต:")
                new_role = st.selectbox("กำหนดสิทธิ์:", ["staff", "admin"])
                if st.form_submit_button("บันทึกข้อมูล"):
                    if new_email:
                        conn = sqlite3.connect('repairs.db')
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_email, new_role))
                        conn.commit()
                        conn.close()
                        st.success(f"เพิ่ม {new_email} สำเร็จ!")
                    else:
                        st.error("กรุณากรอกอีเมล")
            
            st.subheader("รายชื่อพนักงานในระบบ")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users")
            for u in c.fetchall():
                col1, col2 = st.columns([3, 1])
                col1.write(f"อีเมล: {u[0]} | สิทธิ์: **{u[1]}**")
                if col2.button("ลบ", key=f"del_{u[0]}"):
                    c.execute("DELETE FROM users WHERE email = ?", (u[0],))
                    conn.commit()
                    st.rerun()
            conn.close()

        elif menu == "สร้าง QR Code":
            st.header("สร้าง QR Code สำหรับแจ้งซ่อม")
            url = st.text_input("ใส่ลิงก์เว็บของคุณ:", "http://localhost:8501")
            if st.button("Generate QR"):
                img = qrcode.make(url)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                st.image(buf.getvalue(), caption="สแกนเพื่อแจ้งซ่อม")

    # --- ส่วนของ พนักงาน (Staff) ---
    elif is_staff:
        st.header(f"ยินดีต้อนรับคุณ {email}")
        with st.form("repair_form"):
            room = st.selectbox("เลือกห้อง", ["ห้อง 101", "ห้อง 102", "ห้อง 103"])
            device = st.selectbox("เลือกอุปกรณ์", ["Monitor", "แอร์", "เครื่อง PC", "อื่นๆ"])
            detail = st.text_area("รายละเอียดปัญหา")
            if st.form_submit_button("ส่งรายงาน"):
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("INSERT INTO repairs (user_email, room, device, detail, status) VALUES (?,?,?,?,?)",
                          (email, room, device, detail, "รอดำเนินการ"))
                conn.commit()
                conn.close()
                st.success("บันทึกข้อมูลเรียบร้อย!")
                
    # --- กรณีไม่มีรายชื่อในระบบ ---
    else:
        st.error(f"อีเมล ({email}) ของคุณยังไม่ได้รับสิทธิ์เข้าใช้งาน กรุณาติดต่อหัวหน้าเพื่อเพิ่มบัญชี")

    # ปุ่ม Logout สำหรับทุกคน
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()