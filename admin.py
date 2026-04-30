import streamlit as st
import sqlite3
import qrcode
import io

# --- 1. การตั้งค่าพื้นฐาน ---
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"
ADMIN_PASSWORD = "admin1234" # เปลี่ยนเป็นรหัสที่ปลอดภัยกว่านี้ในภายหลัง

def get_db_connection():
    return sqlite3.connect('repairs.db', check_same_thread=False)

st.set_page_config(page_title="Admin Panel", layout="wide")
st.title("🛡️ ระบบจัดการหลังบ้าน (Admin Panel)")

if "admin_logged_in" not in st.session_state:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        with st.form("admin_login"):
            email_input = st.text_input("Gmail").lower().strip()
            pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT role FROM users WHERE LOWER(email)=? AND role='admin'", (email_input,))
                is_db_admin = c.fetchone()
                
                # เช็คแอดมินหลัก หรือ แอดมินจาก DB (รหัสผ่านกลาง 1234)
                if (email_input == ADMIN_EMAIL.lower() and pass_input == ADMIN_PASSWORD) or \
                   (is_db_admin and pass_input == "1234"):
                    st.session_state.admin_logged_in = email_input
                    st.rerun()
                else:
                    st.error("อีเมลหรือรหัสผ่านไม่ถูกต้อง")
                conn.close()
else:
    st.sidebar.info(f"แอดมิน: {st.session_state.admin_logged_in}")
    if st.sidebar.button("ออกจากระบบ"):
        del st.session_state.admin_logged_in
        st.rerun()

    menu = st.sidebar.radio("เมนู:", ["👥 จัดการรายชื่อพนักงาน", "📋 ดูรายการแจ้งซ่อมทั้งหมด", "📲 สร้าง QR Code"])
    conn = get_db_connection()
    c = conn.cursor()

    if menu == "👥 จัดการรายชื่อพนักงาน":
        st.header("จัดการผู้มีสิทธิ์ใช้งาน")
        with st.form("add_user"):
            new_email = st.text_input("อีเมล Gmail พนักงาน").lower().strip()
            new_role = st.selectbox("ตำแหน่ง", ["staff", "admin"])
            if st.form_submit_button("เพิ่มรายชื่อ"):
                if new_email:
                    c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_email, new_role))
                    conn.commit()
                    st.success(f"เพิ่ม {new_email} สำเร็จ!")
                    st.rerun()

        st.subheader("รายชื่อในระบบ")
        c.execute("SELECT email, role FROM users")
        for u in c.fetchall():
            col1, col2 = st.columns([4, 1])
            col1.write(f"📧 {u[0]} | สิทธิ์: `{u[1]}`")
            if col2.button("ลบ", key=f"del_{u[0]}"):
                c.execute("DELETE FROM users WHERE email=?", (u[0],))
                conn.commit()
                st.rerun()

    elif menu == "📋 ดูรายการแจ้งซ่อมทั้งหมด":
        st.header("ประวัติการแจ้งซ่อมทั้งหมด")
        c.execute("SELECT id, user_email, room, device, status FROM repairs ORDER BY id DESC")
        rows = c.fetchall()
        if rows:
            st.table(rows) # แสดงแบบตารางเพื่อความง่ายในการตรวจสอบ
        else:
            st.write("ยังไม่มีข้อมูล")

    elif menu == "📲 สร้าง QR Code":
        st.header("สร้าง QR Code สำหรับเข้าแอป")
        url = st.text_input("Link App ของคุณ", "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app")
        if st.button("Generate QR"):
            qr = qrcode.make(url)
            buf = io.BytesIO()
            qr.save(buf, format='PNG')
            st.image(buf.getvalue(), caption="สแกนเพื่อแจ้งซ่อม")
            st.download_button("โหลดไฟล์ QR", buf.getvalue(), "qr_repair.png", "image/png")
    
    conn.close()