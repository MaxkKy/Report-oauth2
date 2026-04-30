import streamlit as st
from streamlit_oauth import OAuth2Component
import sqlite3
import qrcode
import io
import os

# --- 1. การตั้งค่าพื้นฐาน (Config) ---
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th" # อีเมลแอดมินหลัก
ADMIN_PASSWORD = "admin1234"         # รหัสผ่านสำหรับเข้าแบบ Manual (เปลี่ยนได้ตามต้องการ)

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# ลิงก์ Redirect ต้องตรงกับที่ตั้งไว้ใน Google Cloud Console
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
    # ตารางแจ้งซ่อม
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, 
                  device TEXT, detail TEXT, status TEXT)''')
    # ตารางรายชื่อผู้มีสิทธิ์ใช้งาน
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. ส่วนการตรวจสอบ Login ---
st.set_page_config(page_title="Admin Management", layout="wide")
st.title("🛡️ ระบบจัดการหลังบ้าน (Admin & Staff Panel)")

if "user_email" not in st.session_state:
    st.subheader("กรุณาเข้าสู่ระบบเพื่อใช้งาน")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### แบบที่ 1: Google Login")
        result = oauth.authorize_button(
            name="Login with Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        )
        if result and "token" in result:
            # ดึงอีเมลจาก ID Token ของ Google
            st.session_state.user_email = result["token"].get("email")
            st.rerun()

    with col2:
        st.warning("### แบบที่ 2: รหัสผ่านระบบ")
        with st.form("manual_login"):
            email_input = st.text_input("Gmail")
            pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                # เช็คแอดมินหลัก
                if email_input == ADMIN_EMAIL and pass_input == ADMIN_PASSWORD:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    # เช็คพนักงานคนอื่นในฐานข้อมูล
                    conn = sqlite3.connect('repairs.db')
                    c = conn.cursor()
                    c.execute("SELECT email FROM users WHERE email=?", (email_input,))
                    db_user = c.fetchone()
                    conn.close()
                    
                    if db_user and pass_input == "1234": # รหัสผ่านเริ่มต้นพนักงาน
                        st.session_state.user_email = email_input
                        st.rerun()
                    else:
                        st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง")

else:
    # --- เมื่อ Login สำเร็จแล้ว ---
    user_email = st.session_state.user_email
    st.sidebar.success(f"ผู้ใช้งาน: {user_email}")
    
    if st.sidebar.button("ออกจากระบบ (Log out)"):
        del st.session_state.user_email
        st.rerun()

    # ตรวจสอบสิทธิ์จาก Database
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email = ?", (user_email,))
    user_role_db = c.fetchone()
    conn.close()

    # สิทธิ์ Admin คือ แอดมินหลัก หรือ คนที่มี role='admin' ใน DB
    is_admin = (user_email == ADMIN_EMAIL) or (user_role_db and user_role_db[0] == 'admin')

    if is_admin:
        menu = st.sidebar.radio("เมนูจัดการ:", ["📋 รายการแจ้งซ่อม", "👥 จัดการรายชื่อพนักงาน", "📲 สร้าง QR Code"])
        
        if menu == "📋 รายการแจ้งซ่อม":
            st.header("รายการแจ้งซ่อมทั้งหมด")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT id, user_email, room, device, detail, status FROM repairs ORDER BY id DESC")
            rows = c.fetchall()
            
            if not rows:
                st.write("ยังไม่มีข้อมูลการแจ้งซ่อม")
            
            for r in rows:
                with st.expander(f"ID: {r[0]} | ห้อง: {r[2]} | สถานะ: {r[5]}"):
                    st.write(f"**ผู้แจ้ง:** {r[1]}")
                    st.write(f"**อุปกรณ์:** {r[3]}")
                    st.write(f"**รายละเอียด:** {r[4]}")
                    if r[5] == "รอดำเนินการ":
                        if st.button(f"เปลี่ยนสถานะเป็น 'เสร็จสิ้น'", key=f"btn_{r[0]}"):
                            c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                            conn.commit()
                            st.success(f"อัปเดตงาน ID {r[0]} เรียบร้อย!")
                            st.rerun()
            conn.close()

        elif menu == "👥 จัดการรายชื่อพนักงาน":
            st.header("จัดการผู้มีสิทธิ์เข้าใช้งาน")
            
            # ฟอร์มเพิ่มพนักงาน
            with st.form("add_staff_form"):
                st.subheader("เพิ่มรายชื่อใหม่")
                new_email = st.text_input("อีเมล Gmail พนักงาน")
                new_role = st.selectbox("กำหนดสิทธิ์", ["staff", "admin"])
                if st.form_submit_button("เพิ่มเข้าสู่ระบบ"):
                    if new_email:
                        conn = sqlite3.connect('repairs.db')
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_email, new_role))
                        conn.commit()
                        conn.close()
                        st.success(f"เพิ่ม {new_email} สำเร็จ!")
                        st.rerun()
            
            st.divider()
            st.subheader("รายชื่อในระบบปัจจุบัน")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM users")
            user_list = c.fetchall()
            
            for u in user_list:
                col1, col2 = st.columns([4, 1])
                col1.write(f"📧 **{u[0]}** | สิทธิ์: `{u[1]}`")
                if col2.button("ลบสิทธิ์", key=f"del_{u[0]}"):
                    c.execute("DELETE FROM users WHERE email = ?", (u[0],))
                    conn.commit()
                    st.rerun()
            conn.close()

        elif menu == "📲 สร้าง QR Code":
            st.header("เครื่องมือสร้าง QR Code")
            qr_text = st.text_input("ใส่ลิงก์เว็บไซต์แจ้งซ่อมของคุณ:", REDIRECT_URI)
            if st.button("สร้าง QR Code"):
                img = qrcode.make(qr_text)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                st.image(buf.getvalue(), caption="สแกนเพื่อเข้าหน้าแจ้งซ่อม")
                st.download_button("ดาวน์โหลดภาพ QR", buf.getvalue(), file_name="repair_qr.png", mime="image/png")

    else:
        # กรณี Login เข้ามาได้แต่ไม่มีชื่อในระบบแอดมิน
        st.warning(f"อีเมล {user_email} ยังไม่ได้รับสิทธิ์เข้าถึงหน้า Admin")
        st.info("กรุณาติดต่อแอดมินหลักเพื่อขอรับสิทธิ์ใช้งาน (Staff/Admin)")