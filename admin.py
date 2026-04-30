import streamlit as st
import sqlite3
import qrcode
import io
import os

# --- 1. การตั้งค่าพื้นฐาน (Config) ---
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th" # อีเมลแอดมินหลัก
ADMIN_PASSWORD = "admin1234"         # รหัสผ่านสำหรับแอดมิน

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

# --- 3. ส่วนการตรวจสอบ Login (Manual Only) ---
st.set_page_config(page_title="Admin Management", layout="wide")
st.title("🛡️ ระบบจัดการหลังบ้าน (Admin Panel)")

if "user_email" not in st.session_state:
    st.subheader("กรุณาเข้าสู่ระบบ")
    
    # หน้ากาก Login แบบฟอร์มเดียว
    with st.center(): # จัดให้อยู่กลางหน้าจอ (จำลองด้วย columns)
        _, col_mid, _ = st.columns([1, 2, 1])
        with col_mid:
            with st.form("login_form"):
                email_input = st.text_input("Gmail (อีเมล)").lower().strip()
                pass_input = st.text_input("Password (รหัสผ่าน)", type="password")
                submit = st.form_submit_button("เข้าสู่ระบบ")
                
                if submit:
                    # 1. เช็คแอดมินหลักจากโค้ด
                    if email_input == ADMIN_EMAIL.lower() and pass_input == ADMIN_PASSWORD:
                        st.session_state.user_email = email_input
                        st.rerun()
                    else:
                        # 2. เช็คพนักงานคนอื่นในฐานข้อมูล (ใช้รหัสผ่านกลาง 1234)
                        conn = sqlite3.connect('repairs.db')
                        c = conn.cursor()
                        c.execute("SELECT email FROM users WHERE LOWER(email)=?", (email_input,))
                        db_user = c.fetchone()
                        conn.close()
                        
                        if db_user and pass_input == "1234":
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
    c.execute("SELECT role FROM users WHERE LOWER(email) = ?", (user_email,))
    user_role_db = c.fetchone()
    conn.close()

    # สิทธิ์ Admin คือ แอดมินหลัก หรือ คนที่มี role='admin' ใน DB
    is_admin = (user_email == ADMIN_EMAIL.lower()) or (user_role_db and user_role_db[0] == 'admin')

    if is_admin:
        menu = st.sidebar.radio("เมนูจัดการ:", ["📋 รายการแจ้งซ่อม", "👥 จัดการรายชื่อพนักงาน", "📲 สร้าง QR Code"])
        
        if menu == "📋 รายการแจ้งซ่อม":
            st.header("รายการแจ้งซ่อมทั้งหมด")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT id, user_email, room, device, detail, status FROM repairs ORDER BY id DESC")
            rows = c.fetchall()
            
            if not rows:
                st.info("ยังไม่มีข้อมูลการแจ้งซ่อม")
            
            for r in rows:
                with st.expander(f"ID: {r[0]} | ห้อง: {r[2]} | สถานะ: {r[5]}"):
                    st.write(f"**ผู้แจ้ง:** {r[1]}")
                    st.write(f"**อุปกรณ์:** {r[3]}")
                    st.write(f"**รายละเอียด:** {r[4]}")
                    if r[5] == "รอดำเนินการ":
                        if st.button(f"ยืนยันว่าแก้ไขเสร็จสิ้น", key=f"btn_{r[0]}"):
                            c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                            conn.commit()
                            st.success(f"อัปเดตงาน ID {r[0]} เรียบร้อย!")
                            st.rerun()
            conn.close()

        elif menu == "👥 จัดการรายชื่อพนักงาน":
            st.header("จัดการผู้มีสิทธิ์เข้าใช้งาน")
            
            with st.form("add_staff_form"):
                st.subheader("เพิ่มรายชื่อใหม่")
                new_email = st.text_input("อีเมล Gmail พนักงาน").lower().strip()
                new_role = st.selectbox("กำหนดสิทธิ์", ["staff", "admin"])
                if st.form_submit_button("บันทึกรายชื่อ"):
                    if new_email:
                        conn = sqlite3.connect('repairs.db')
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_email, new_role))
                        conn.commit()
                        conn.close()
                        st.success(f"เพิ่ม {new_email} เรียบร้อย! (รหัสผ่านเริ่มต้นคือ 1234)")
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
            qr_text = st.text_input("ใส่ลิงก์หน้าแจ้งซ่อม (app.py) ของคุณ:", "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app")
            if st.button("สร้าง QR Code"):
                img = qrcode.make(qr_text)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                st.image(buf.getvalue(), caption="สแกนเพื่อเข้าสู่หน้าแจ้งซ่อม")
                st.download_button("ดาวน์โหลดภาพ QR", buf.getvalue(), file_name="repair_qr.png", mime="image/png")

    else:
        st.error(f"ขออภัย อีเมล {user_email} ไม่มีสิทธิ์เข้าถึงส่วนนี้")
        st.info("กรุณาล็อกอินด้วยบัญชีแอดมินหลัก")