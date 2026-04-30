import streamlit as st
import sqlite3
import qrcode
import io

# --- 1. ตั้งค่าบัญชีแอดมิน ---
# คุณใช้ Gmail เดิมของคุณ แต่กำหนดรหัสผ่านใหม่สำหรับเข้าแอปนี้
ADMIN_USER = "aphisit.k65@rsu.ac.th"
ADMIN_PW = "admin1234"  # 🔑 เปลี่ยนรหัสผ่านตรงนี้ตามใจชอบ

# --- 2. ตั้งค่า Database ---
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

st.title("🛠️ ระบบจัดการแจ้งซ่อม (Admin Panel)")

# --- 3. ระบบ Login แบบกรอกเอง ---
if "logged_in_email" not in st.session_state:
    st.subheader("กรุณาเข้าสู่ระบบ")
    with st.form("login_form"):
        email_input = st.text_input("Gmail")
        pass_input = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if email_input == ADMIN_USER and pass_input == ADMIN_PW:
                st.session_state.logged_in_email = email_input
                st.success("ยินดีต้อนรับคุณแอดมิน!")
                st.rerun()
            else:
                # เช็คพนักงานคนอื่นใน Database
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("SELECT email FROM users WHERE email=? AND role='staff'", (email_input,))
                user_exists = c.fetchone()
                conn.close()
                
                # สำหรับพนักงาน ให้ใช้รหัสผ่านกลาง (เช่น 1234)
                if user_exists and pass_input == "1234":
                    st.session_state.logged_in_email = email_input
                    st.rerun()
                else:
                    st.error("Gmail หรือ Password ไม่ถูกต้อง")
else:
    # ส่วนที่เหลือของโค้ดจัดการข้อมูลเหมือนเดิม
    current_user = st.session_state.logged_in_email
    st.sidebar.info(f"Logged in as: {current_user}")
    
    if st.sidebar.button("Logout"):
        del st.session_state.logged_in_email
        st.rerun()

    menu = st.sidebar.radio("เมนู", ["รายการแจ้งซ่อม", "จัดการพนักงาน", "สร้าง QR Code"])

    if menu == "รายการแจ้งซ่อม":
        st.header("📋 รายการแจ้งซ่อมทั้งหมด")
        conn = sqlite3.connect('repairs.db')
        c = conn.cursor()
        c.execute("SELECT * FROM repairs")
        rows = c.fetchall()
        for r in rows:
            st.write(f"ID: {r[0]} | ห้อง: {r[2]} | {r[3]} | สถานะ: {r[5]}")
            if r[5] == "รอดำเนินการ":
                if st.button(f"เสร็จสิ้น (ID {r[0]})", key=f"btn_{r[0]}"):
                    c.execute("UPDATE repairs SET status='เสร็จสิ้น' WHERE id=?", (r[0],))
                    conn.commit()
                    st.rerun()
        conn.close()

    elif menu == "จัดการพนักงาน":
        st.header("👥 เพิ่มรายชื่อพนักงาน")
        with st.form("add_staff"):
            new_mail = st.text_input("Gmail พนักงาน")
            if st.form_submit_button("บันทึก"):
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, 'staff')", (new_mail,))
                conn.commit()
                conn.close()
                st.success(f"เพิ่ม {new_mail} แล้ว (รหัสผ่านเริ่มต้นคือ 1234)")

    elif menu == "สร้าง QR Code":
        st.header("📱 สร้าง QR Code")
        url = "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app"
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        st.image(buf.getvalue())