import streamlit as st
import sqlite3

st.set_page_config(page_title="NÖHÜ Öğrenci Destek Sistemi", page_icon="🎓")

st.title("🎓 NÖHÜ Öğrenci Çakışma Bildirim Merkezi")
st.markdown("Sevgili öğrenciler, çakışan derslerinizi buradan Dekanlık Yapay Zeka Asistanına bildirebilirsiniz. Sistemimiz şikayetlerinizi analiz edip yeni ders programını optimize edecektir.")

def baglanti_olustur():
    return sqlite3.connect('opticampus.db') # Ana sistemin veritabanına bağlanıyor!

with st.container(border=True):
    with st.form("ogrenci_sikayet_formu"):
        col1, col2 = st.columns(2)
        with col1:
            ders1 = st.text_input("1. Dersin Adı (Örn: Veri Yapıları)", placeholder="Tam veya kısmi adını yazın...")
        with col2:
            ders2 = st.text_input("Çakışan 2. Dersin Adı (Örn: İşletim Sistemleri)", placeholder="Tam veya kısmi adını yazın...")
            
        sebep = st.text_area("Bu çakışma sizi nasıl etkiliyor? (Dekanlığa İletilecek Not)", placeholder="Örn: İkisi de aynı saatte, üstten ders alamıyorum...")
        
        if st.form_submit_button("🚀 Şikayetimi YZ Asistanına İlet", type="primary", use_container_width=True):
            # SADECE 1. DERS VE SEBEP ZORUNLU, 2. DERS OPSİYONEL
            if ders1 and sebep:
                conn = baglanti_olustur()
                conn.cursor().execute('''CREATE TABLE IF NOT EXISTS ogrenci_sikayetleri (id INTEGER PRIMARY KEY AUTOINCREMENT, ders1 TEXT NOT NULL, ders2 TEXT NOT NULL, sebep TEXT NOT NULL)''')
                
                # 2. ders boş bırakıldıysa "Belirtilmedi" yaz
                ders2_kayit = ders2 if ders2 else "Belirtilmedi"
                
                conn.cursor().execute("INSERT INTO ogrenci_sikayetleri (ders1, ders2, sebep) VALUES (?, ?, ?)", (ders1, ders2_kayit, sebep))
                conn.commit()
                conn.close()
                st.success("✅ Talebiniz başarıyla Dekanlığa ulaştı! Yeni program hazırlanırken dikkate alınacaktır.")
                st.balloons()
            else:
                st.error("⚠️ Lütfen en az 1. Dersin adını ve şikayet sebebinizi yazın.")