import streamlit as st
import os
import json
from datetime import datetime
import numpy as np
from PIL import Image
import requests
from deepface import DeepFace

st.set_page_config(page_title="Maktab Face ID", page_icon="🏫", layout="wide")

# ====================== CSS - CHIROYLI MAKTAB DIZAYNI ======================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #00b140, #007a2e); }
    .main { background: rgba(255,255,255,0.95); border-radius: 20px; padding: 25px; }
    h1, h2, h3 { color: #007a2e !important; }
    .success { color: #00c853; font-size: 1.6em; font-weight: bold; }
    .stButton>button { background-color: #00ff88; color: black; border-radius: 50px; height: 50px; }
    .delete-btn>button { background-color: #ff5252; color: white; }
</style>
""", unsafe_allow_html=True)

MODEL_NAME = "Facenet512"
THRESHOLD = 0.60
ADMIN_PASSWORD = "mak41tab"

os.makedirs("photos", exist_ok=True)

# ====================== YORDAMCHI FUNKSIYALAR ======================
def load_students():
    if os.path.exists("students.json"):
        with open("students.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_students(students):
    with open("students.json", "w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=4)

def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"bot_token": "", "class_chat_map": {}}

def save_config(config):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def get_embedding(image_path):
    try:
        result = DeepFace.represent(img_path=image_path, model_name=MODEL_NAME, enforce_detection=False, align=True)
        return result[0]["embedding"]
    except:
        return None

def cosine_distance(emb1, emb2):
    emb1 = np.array(emb1)
    emb2 = np.array(emb2)
    sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-6)
    return 1 - sim

def send_to_telegram(photo_path, name, class_name, bot_token, chat_id):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    caption = f"👤 {name} ({class_name})\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n✅ Face ID tasdiqlandi"
    try:
        with open(photo_path, "rb") as photo:
            r = requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"photo": photo}, timeout=15)
            return r.status_code == 200
    except:
        return False

# ====================== ASOSIY APP ======================
st.title("🏫 Maktab Face ID")
st.caption("Avtomatik yuz tanish orqali davomat tizimi")

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

tab1, tab2 = st.tabs(["📸 Face ID Rejimi (Kiosk)", "🔧 Admin Panel"])

with tab1:
    st.subheader("📍 Eshik oldidagi planshet rejimi")
    camera_input = st.camera_input("📸 Yuzingizni skaner qiling", key="camera")

    if camera_input:
        with st.spinner("Yuz tanilmoqda..."):
            temp_path = "temp_capture.jpg"
            with open(temp_path, "wb") as f:
                f.write(camera_input.getbuffer())

            new_emb = get_embedding(temp_path)
            if new_emb:
                students = load_students()
                best_match = None
                min_dist = float("inf")

                for stu in students:
                    if "embedding" in stu:
                        dist = cosine_distance(new_emb, stu["embedding"])
                        if dist < min_dist:
                            min_dist = dist
                            best_match = stu

                if best_match and min_dist < THRESHOLD:
                    name = best_match["name"]
                    class_name = best_match["class"]
                    st.markdown(f'<p class="success">✅ {name} ({class_name}) keldi!</p>', unsafe_allow_html=True)

                    config = load_config()
                    chat_id = config.get("class_chat_map", {}).get(class_name)
                    bot_token = config.get("bot_token")
                    if chat_id and bot_token and send_to_telegram(temp_path, name, class_name, bot_token, chat_id):
                        st.success("📨 Telegram guruhga yuborildi!")
                else:
                    st.error("❌ Yuz tanilmadi. Qayta urinib ko‘ring!")
            os.remove(temp_path) if os.path.exists(temp_path) else None

with tab2:
    st.subheader("🔧 Admin Panel")

    if not st.session_state.admin_authenticated:
        pw = st.text_input("Admin parolini kiriting", type="password")
        if st.button("Kirish"):
            if pw == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Noto‘g‘ri parol!")
    else:
        st.success("✅ Admin rejimi faol")
        if st.button("Chiqish"):
            st.session_state.admin_authenticated = False
            st.rerun()

        admin_tab1, admin_tab2 = st.tabs(["📡 Telegram sozlamalari", "👨‍🎓 O‘quvchilarni boshqarish"])

        with admin_tab1:
            config = load_config()
            bot_token = st.text_input("Telegram Bot Token", value=config.get("bot_token", ""), type="password")
            if st.button("Tokenni saqlash"):
                config["bot_token"] = bot_token
                save_config(config)
                st.success("Saqlandi")

            st.subheader("Sinf → Guruh (Chat ID)")
            class_map = config.get("class_chat_map", {})
            for cls in list(class_map.keys()):
                col1, col2, col3 = st.columns([2, 3, 1])
                col1.write(f"**{cls}**")
                col2.write(class_map[cls])
                if col3.button("O‘chirish", key=f"delcls_{cls}"):
                    del class_map[cls]
                    config["class_chat_map"] = class_map
                    save_config(config)
                    st.rerun()

            new_class = st.text_input("Yangi sinf nomi (10-A)")
            new_chat = st.text_input("Telegram Chat ID (-100xxxxxxxx)")
            if st.button("Sinf qo‘shish") and new_class and new_chat:
                class_map[new_class] = new_chat
                config["class_chat_map"] = class_map
                save_config(config)
                st.success("Qo‘shildi!")

        with admin_tab2:
            st.subheader("O‘quvchilar ro‘yxati va boshqaruvi")

            students = load_students()

            # Ro‘yxat jadval ko‘rinishida
            if students:
                for i, stu in enumerate(students[:]):
                    col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
                    if os.path.exists(stu.get("photo_path", "")):
                        col1.image(stu["photo_path"], width=80)
                    col2.write(f"**{stu['name']}**")
                    col2.caption(f"Sinf: {stu['class']}")
                    col3.write(f"ID: {i+1}")
                    if col4.button("🗑 O‘chirish", key=f"delstu_{i}"):
                        if os.path.exists(stu["photo_path"]):
                            os.remove(stu["photo_path"])
                        students.pop(i)
                        save_students(students)
                        st.rerun()
            else:
                st.info("Hozircha o‘quvchilar yo‘q")

            # Yangi o‘quvchi qo‘shish formasi
            st.subheader("➕ Yangi o‘quvchi qo‘shish")
            with st.form("add_student_form", clear_on_submit=True):
                ism = st.text_input("Ism")
                familiya = st.text_input("Familiya")
                full_name = f"{ism} {familiya}".strip()
                sinf = st.text_input("Sinf (masalan: 10-A)")
                rasm = st.file_uploader("O‘quvchining rasmini yuklang (jpg/png)", type=["jpg", "jpeg", "png"])
                submitted = st.form_submit_button("Qo‘shish")

                if submitted and full_name and sinf and rasm:
                    photo_path = f"photos/{full_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    with open(photo_path, "wb") as f:
                        f.write(rasm.getbuffer())

                    embedding = get_embedding(photo_path)
                    if embedding:
                        students.append({
                            "name": full_name,
                            "class": sinf,
                            "embedding": embedding,
                            "photo_path": photo_path
                        })
                        save_students(students)
                        st.success(f"✅ {full_name} ({sinf}) qo‘shildi va yuzi saqlandi!")
                    else:
                        st.error("Yuz aniqlanmadi. Rasmni qayta yuklang.")

# Kiosk uchun qo‘shimcha CSS
st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
