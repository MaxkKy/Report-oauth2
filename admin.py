import streamlit as st
import sqlite3
import qrcode
import io

# --- 1. ตั้งค่าบัญชี (ใช้ Gmail เป็นเหมือน Username) ---
ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"
ADMIN_PASSWORD = "admin"  # 🔑 รหัสผ่านสำหรับคุณ (Admin)
STAFF_PASSWORD = "1234"   # 🔑 รหัสผ่านกลางสำหรับพนักงานทุกคน

# --- 2. ตั้งค่า Database ---
def init_db():
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    # ตารางแจ้งซ่อม
    c.execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, room TEXT, 
                  device TEXT, detail TEXT, status TEXT)''')
    # ตารางเก็บบัญชีพนักงาน
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, role TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. หน้า UI ---
st.title("🛠️ ระบบจัดการสำหรับแจ้งซ่อมออนไลน์")

# --- ระบบ Login แบบกรอก Email และ รหัสผ่าน ---
if "user_email" not in st.session_state:
    st.info("กรุณากรอกอีเมล (Gmail) และรหัสผ่านเพื่อเข้าใช้งาน")
    with st.form("login_form"):
        input_email = st.text_input("อีเมล (เช่น aphisit.k65@rsu.ac.th)")
        input_password = st.text_input("รหัสผ่าน", type="password")
        submit = st.form_submit_button("เข้าสู่ระบบ")
        
        if submit:
            # 1. เช็คว่าเป็น Admin ไหม
            if input_email == ADMIN_EMAIL and input_password == ADMIN_PASSWORD:
                st.session_state.user_email = input_email
                st.rerun()
            else:
                # 2. เช็คว่าเป็นพนักงานในระบบไหม
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("SELECT role FROM users WHERE email = ?", (input_email,))
                db_user = c.fetchone()
                conn.close()
                
                if db_user and input_password == STAFF_PASSWORD:
                    st.session_state.user_email = input_email
                    st.rerun()
                else:
                    st.error("❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง หรือคุณยังไม่มีสิทธิ์ในระบบ")
else:
    email = st.session_state.user_email
    st.sidebar.success(f"ผู้ใช้งาน: **{email}**")

    # --- ตรวจสอบสิทธิ์การเข้าใช้งาน ---
    conn = sqlite3.connect('repairs.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email = ?", (email,))
    db_user = c.fetchone()
    conn.close()

    is_admin = (email == ADMIN_EMAIL) or (db_user and db_user[0] == 'admin')
    is_staff = db_user and db_user[0] == 'staff'

    # --- ส่วนของ Admin ---
    if is_admin:
        st.sidebar.subheader("📌 Admin Panel")
        menu = st.sidebar.radio("เมนูจัดการ:", ["รายการแจ้งซ่อม", "จัดการบัญชีพนักงาน", "สร้าง QR Code"])
        
        if menu == "รายการแจ้งซ่อม":
            st.header("จัดการสถานะงาน")
            conn = sqlite3.connect('repairs.db')
            c = conn.cursor()
            c.execute("SELECT * FROM repairs ORDER BY id DESC")
            repairs = c.fetchall()
            
            if not repairs:
                st.write("ยังไม่มีรายการแจ้งซ่อม")
            
            for r in repairs:
                st.write(f"**ID: {r[0]}** | ห้อง: {r[2]} | {r[3]} | สถานะ: **{r[5]}**")
                if r[5] == "รอดำเนินการ":
                    if st.button(f"✅ เปลี่ยนเป็นเสร็จสิ้น (ID {r[0]})", key=f"upd_{r[0]}"):
                        c.execute("UPDATE repairs SET status = 'เสร็จสิ้น' WHERE id = ?", (r[0],))
                        conn.commit()
                        st.rerun()
                st.markdown("---")
            conn.close()
            
        elif menu == "จัดการบัญชีพนักงาน":
            st.header("👤 เพิ่มและจัดการบัญชีพนักงาน")
            with st.form("add_user_form"):
                new_email = st.text_input("ใส่อีเมลพนักงานที่ต้องการอนุญาต (เช่น xxx@gmail.com):")
                new_role = st.selectbox("กำหนดสิทธิ์:", ["staff", "admin"])
                if st.form_submit_button("บันทึกข้อมูล"):
                    if new_email:
                        conn = sqlite3.connect('repairs.db')
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_email, new_role))
                        conn.commit()
                        conn.close()
                        st.success(f"เพิ่มสิทธิ์ให้ {new_email} สำเร็จ!")
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
            url = st.text_input("ใส่ลิงก์เว็บ Streamlit ของคุณ:", "https://report-oapp2-krppq6mmldybttknuwrfed.streamlit.app")
            if st.button("Generate QR"):
                img = qrcode.make(url)
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                st.image(buf.getvalue(), caption="สแกนเพื่อเข้าสู่ระบบ")

    # --- ส่วนของ พนักงาน (Staff) ---
    elif is_staff:
        st.header("📝 แบบฟอร์มแจ้งซ่อม")
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
                st.success("บันทึกข้อมูลแจ้งซ่อมเรียบร้อยแล้ว!")
                
    else:
        st.error("อีเมลของคุณยังไม่ได้รับสิทธิ์เข้าใช้งาน กรุณาติดต่อหัวหน้าเพื่อเพิ่มบัญชี")

    # ปุ่ม Logout สำหรับทุกคน
    if st.sidebar.button("🚪 ออกจากระบบ"):
        del st.session_state.user_email
        st.rerun()