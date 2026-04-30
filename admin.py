import streamlit as st
import sqlite3

ADMIN_EMAIL = "aphisit.k65@rsu.ac.th"
ADMIN_PASSWORD = "admin1234"

st.set_page_config(page_title="Admin Panel")
st.title("🛡️ ระบบจัดการพนักงาน")

if "admin_user" not in st.session_state:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login"):
            e = st.text_input("Email (Gmail)").lower().strip()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                # เช็คแอดมินหลัก
                if e == ADMIN_EMAIL.lower().strip() and p == ADMIN_PASSWORD:
                    st.session_state.admin_user = e
                    st.rerun()
                else:
                    # เช็คพนักงานที่แอดไว้ (ใช้รหัส 1234)
                    conn = sqlite3.connect('repairs.db')
                    c = conn.cursor()
                    c.execute("SELECT role FROM users WHERE LOWER(email)=?", (e,))
                    res = c.fetchone()
                    conn.close()
                    if res and p == "1234":
                        st.session_state.admin_user = e
                        st.rerun()
                    else: st.error("ข้อมูลไม่ถูกต้อง")
else:
    st.sidebar.write(f"Logged in: {st.session_state.admin_user}")
    menu = st.sidebar.radio("เมนู", ["ดูงานซ่อม", "จัดการพนักงาน"])
    
    if menu == "ดูงานซ่อม":
        st.header("รายการแจ้งซ่อม")
        conn = sqlite3.connect('repairs.db')
        c = conn.cursor()
        c.execute("SELECT * FROM repairs")
        for r in c.fetchall(): st.write(r)
        conn.close()
        
    elif menu == "จัดการพนักงาน":
        st.header("เพิ่มพนักงาน (Staff)")
        with st.form("add"):
            new_e = st.text_input("Gmail พนักงาน").lower().strip()
            new_r = st.selectbox("สิทธิ์", ["staff", "admin"])
            if st.form_submit_button("บันทึก"):
                conn = sqlite3.connect('repairs.db')
                c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO users (email, role) VALUES (?, ?)", (new_e, new_r))
                conn.commit() ; conn.close()
                st.success(f"เพิ่ม {new_e} แล้ว! ให้เขาเข้าหน้านี้ด้วยรหัส 1234")
                st.rerun()

    if st.sidebar.button("Logout"):
        del st.session_state.admin_user
        st.rerun()