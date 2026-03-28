import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
import random
import string
import datetime

# ================= CONFIG =================
st.set_page_config(page_title="Owlyx SaaS", layout="wide")

# ================= DATABASE =================
conn = sqlite3.connect("owlyx.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT,
    api_key TEXT,
    created_at TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    item TEXT,
    score INTEGER,
    level TEXT,
    created_at TEXT
)
""")
conn.commit()

# ================= SECURITY =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def verify_password(p, h):
    return hash_password(p) == h

def generate_key(n=24):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def generate_credentials():
    user = "owlyx_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    api_key = generate_key()
    return user, password, api_key

# ================= INIT ADMIN =================
c.execute("SELECT * FROM users WHERE username='admin'")
if not c.fetchone():
    c.execute("""
    INSERT INTO users VALUES (?,?,?,?,?)
    """, ("admin", hash_password("admin123"), "admin", generate_key(), str(datetime.datetime.now())))
    conn.commit()

# ================= AUTH =================
def login(u, p):
    c.execute("SELECT password, role, api_key FROM users WHERE username=?", (u,))
    data = c.fetchone()
    if data and verify_password(p, data[0]):
        return data[1], data[2]
    return None, None

def register():
    u, p, k = generate_credentials()
    c.execute("INSERT INTO users VALUES (?,?,?,?,?)",
              (u, hash_password(p), "client", k, str(datetime.datetime.now())))
    conn.commit()
    return u, p, k

# ================= ENGINE =================
def risk_score(text):
    base = len(text) * random.randint(2, 8)
    noise = random.randint(0, 20)
    return min(base + noise, 100)

def risk_level(score):
    return "Low" if score < 35 else "Medium" if score < 70 else "High"

def save_scan(user, item, score, level):
    c.execute("INSERT INTO scans VALUES (NULL,?,?,?,?,?)",
              (user, item, score, level, str(datetime.datetime.now())))
    conn.commit()

def get_scans(user):
    c.execute("SELECT item, score, level, created_at FROM scans WHERE username=?", (user,))
    return c.fetchall()

# ================= SESSION =================
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.api = None

# ================= UI =================
st.title("🚀 Owlyx SaaS Platform")

menu = st.sidebar.selectbox("Menu", ["Login", "Register", "Dashboard"])

# ================= REGISTER =================
if menu == "Register":
    st.subheader("Auto Client Generator")

    if st.button("Generate Client Account"):
        u, p, k = register()
        st.success("Client Created ✔")
        st.code(f"USERNAME: {u}\nPASSWORD: {p}\nAPI KEY: {k}")

# ================= LOGIN =================
if menu == "Login":
    st.subheader("Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        role, api = login(u, p)
        if role:
            st.session_state.user = u
            st.session_state.role = role
            st.session_state.api = api
            st.success("Login success ✔")
        else:
            st.error("Invalid credentials")

# ================= DASHBOARD =================
if menu == "Dashboard" and st.session_state.user:

    user = st.session_state.user

    st.sidebar.success(f"User: {user}")
    st.sidebar.code(f"API KEY: {st.session_state.api}")

    st.header("🔐 Owlyx Smart Scanner Engine")

    text = st.text_area("Enter items (comma separated)")
    items = [i.strip() for i in text.split(",") if i.strip()]

    results = []

    for i in items:
        score = risk_score(i)
        level = risk_level(score)
        save_scan(user, i, score, level)
        results.append((i, score, level))

    df = pd.DataFrame(results, columns=["Item", "Score", "Level"])

    st.dataframe(df)

    # ================= ANALYTICS =================
    if not df.empty:
        st.subheader("📊 Analytics")

        fig = px.bar(df, x="Item", y="Score", color="Level")
        st.plotly_chart(fig, use_container_width=True)

    # ================= HISTORY =================
    st.subheader("📜 History")

    history = get_scans(user)

    if history:
        hist_df = pd.DataFrame(history, columns=["Item", "Score", "Level", "Time"])
        st.dataframe(hist_df)
    else:
        st.info("No history yet")

    # ================= ADMIN =================
    if st.session_state.role == "admin":
        st.subheader("👑 Admin Panel")

        c.execute("SELECT username, role, created_at FROM users")
        st.dataframe(pd.DataFrame(c.fetchall(), columns=["User", "Role", "Created"]))

        c.execute("SELECT COUNT(*) FROM scans")
        st.metric("Total Scans", c.fetchone()[0])

else:
    if menu == "Dashboard":
        st.warning("Login required 🔐")