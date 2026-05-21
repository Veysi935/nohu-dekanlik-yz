import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import main 
import io 
import time
import datetime

st.set_page_config(page_title="NÖHÜ OptiCampus", layout="wide", page_icon="🏫")

# ==========================================
# 1. VERİTABANI İŞLEMLERİ (ŞİFRELİ KAPI İÇİN)
# ==========================================
def baglanti_olustur():
    return sqlite3.connect('opticampus.db')

def veritabanini_hazirla():
    conn = baglanti_olustur()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS hocalar (id INTEGER PRIMARY KEY AUTOINCREMENT, ad_soyad TEXT NOT NULL, kullanici_adi TEXT UNIQUE NOT NULL, sifre TEXT NOT NULL, rutbe_carpani INTEGER DEFAULT 1, rol TEXT DEFAULT 'hoca')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS kisitlar (id INTEGER PRIMARY KEY AUTOINCREMENT, hoca_id INTEGER, gun TEXT NOT NULL, saat TEXT NOT NULL, sebep TEXT, FOREIGN KEY (hoca_id) REFERENCES hocalar (id))''')
    # Bunu tabloları oluşturduğun yerlerin arasına yapıştır
    cursor.execute('''CREATE TABLE IF NOT EXISTS ogrenci_sikayetleri (id INTEGER PRIMARY KEY AUTOINCREMENT, ders1 TEXT NOT NULL, ders2 TEXT NOT NULL, sebep TEXT NOT NULL)''')
    
    cursor.execute("SELECT COUNT(*) FROM hocalar")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO hocalar (ad_soyad, kullanici_adi, sifre, rutbe_carpani, rol) VALUES (?, ?, ?, ?, ?)", ("Sistem Yöneticisi", "admin", "1234", 3, "admin"))
    conn.commit()
    conn.close()
    # Eski tabloya hata vermeden yeni sütun ekleyen "Yama"
    try:
        cursor.execute("ALTER TABLE kisitlar ADD COLUMN sebep TEXT")
    except:
        pass # Sütun zaten varsa hata vermeden geçer

def giris_kontrol(k_adi, sifre):
    conn = baglanti_olustur()
    k = conn.cursor().execute("SELECT id, ad_soyad, rol FROM hocalar WHERE kullanici_adi=? AND sifre=?", (k_adi, sifre)).fetchone()
    conn.close()
    return k

def personel_ekle(ad, k_adi, sifre, rutbe_carpani, rol):
    conn = baglanti_olustur()
    try:
        conn.cursor().execute("INSERT INTO hocalar (ad_soyad, kullanici_adi, sifre, rutbe_carpani, rol) VALUES (?, ?, ?, ?, ?)", (ad, k_adi, sifre, rutbe_carpani, rol))
        conn.commit()
        basarili = True
    except sqlite3.IntegrityError:
        basarili = False 
    conn.close()
    return basarili

veritabanini_hazirla()

# ==========================================
# 2. GÖRSEL TASARIM (CSS) VE HAFIZA (SESSION)
# ==========================================
st.markdown("""
    <style>
    div.stButton > button:first-child { background-color: #0E1117; color: white; border-radius: 8px; border: 1px solid #4B4B4B; }
    div.stButton > button:hover { background-color: #0056b3; color: white; border-color: #0056b3; }
    [data-testid="stSidebar"] { background-color: #34495E; min-width: 260px !important; max-width: 300px !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

if 'giris_yapildi' not in st.session_state: st.session_state.giris_yapildi = False
if 'sonuc' not in st.session_state: st.session_state.sonuc = None
if 'secilen_strateji' not in st.session_state: st.session_state.secilen_strateji = "Dengeli"
if 'dersler' not in st.session_state: st.session_state.dersler = []
if 'hocalar' not in st.session_state: st.session_state.hocalar = []
if 'derslikler' not in st.session_state: st.session_state.derslikler = []
if 'gecmis' not in st.session_state: st.session_state.gecmis = []
if 'duzenlenecek_hoca' not in st.session_state: st.session_state.duzenlenecek_hoca = None 
if 'yuklenen_dosya_adi' not in st.session_state: st.session_state.yuklenen_dosya_adi = "" 

# --- YARDIMCI FONKSİYONLAR (Orijinal Projeden) ---
def memnuniyet_hesapla(df):
    hoca_puan, ogr_puan = 100, 100
    h_gunluk = df.groupby(['Hoca', 'Gün']).size()
    hoca_puan -= len(h_gunluk[h_gunluk > 3]) * 2
    s_idx = {"08:00":0, "09:00":1, "10:00":2, "11:00":3, "13:00":4, "14:00":5, "15:00":6, "16:00":7}
    df_ogr = df[df['Dönem/Sınıf'] != '-'].copy()
    if not df_ogr.empty:
        df_ogr['s_idx'] = df_ogr['Saat'].map(s_idx)
        s_gunluk = df_ogr.groupby(['Dönem/Sınıf', 'Gün'])['s_idx'].agg(['max', 'min', 'count'])
        s_gunluk['bosluk'] = (s_gunluk['max'] - s_gunluk['min']) - (s_gunluk['count'] - 1)
        ogr_puan -= s_gunluk[s_gunluk['bosluk'] > 1]['bosluk'].sum() * 3
    return max(0, min(100, int(hoca_puan))), max(0, min(100, int(ogr_puan)))

def asistan_anla(metin, hoca_listesi):
    def tr_lower(text):
        tr_map = {'I': 'ı', 'İ': 'i', 'Ş': 'ş', 'Ç': 'ç', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
        for key, val in tr_map.items(): text = text.replace(key, val)
        return text.lower()
    metin_k = tr_lower(str(metin)).replace("'", "").replace(".", "")
    kullanici_kelimeleri = set(metin_k.split())
    gunler_sozluk = {"pazartesi": "Pazartesi", "salı": "Salı", "çarşamba": "Çarşamba", "perşembe": "Perşembe", "cuma": "Cuma"}
    saatler_sozluk = {"sabah": ["08:00", "09:00", "10:00", "11:00"], "öğle": ["13:00", "14:00", "15:00", "16:00"]}
    unvanlar = {"prof", "doc", "doç", "dr", "ogr", "öğr", "gör", "üyesi", "arş"}
    hedef_hoca = None
    for h in hoca_listesi:
        hoca_kelimeleri = {k for k in set(tr_lower(str(h['ad'])).replace(".", " ").split()) if k not in unvanlar and len(k) > 2}
        if kullanici_kelimeleri.intersection(hoca_kelimeleri):
            hedef_hoca = h; break
    yasak_gunler = [g_ad for g_kelime, g_ad in gunler_sozluk.items() if g_kelime in metin_k]
    yasak_saatler = []
    for s_kelime, s_liste in saatler_sozluk.items():
        if s_kelime in metin_k: yasak_saatler.extend(s_liste)
    s_disi = any(k in metin_k for k in ["şehir dışı", "sehir disi", "tek gün"])
    is_radar = any(k in metin_k for k in ["radar", "şikayet", "öğrenci", "çakışma", "incele"]) and not hedef_hoca
    return hedef_hoca, list(set(yasak_gunler)), list(set(yasak_saatler)), s_disi, is_radar

# ==========================================
# 3. GİRİŞ EKRANI (LOGIN DUVARI)
# ==========================================
if not st.session_state.giris_yapildi:
    st.markdown("<br><br>", unsafe_allow_html=True)
    kol_bos, kol_orta, kol_bos2 = st.columns([1, 2, 1])
    with kol_orta:
        st.title("🎓 NÖHÜ OptiCampus")
        st.markdown("Lütfen size verilen yetkili hesabı ile giriş yapın.")
        with st.form("login_form"):
            k_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                k = giris_kontrol(k_adi, sifre)
                if k:
                    st.session_state.update({'giris_yapildi': True, 'kullanici_id': k[0], 'ad_soyad': k[1], 'rol': k[2]})
                    st.rerun()
                else: st.error("Kullanıcı adı veya şifre hatalı!")

           

# ==========================================
# 4. KONTROL PANELİ (SİSTEME GİRİLDİKTEN SONRA)
# ==========================================
else:
    # --- YETKİ: SİSTEM YÖNETİCİSİ (DEKANLIK / ADMİN) ---
    if st.session_state['rol'] == 'admin':
        # ORİJİNAL SOL MENÜ (SİDEBAR)
        with st.sidebar:
            st.markdown("""
                <div style='text-align: center; padding: 10px; background-color: #34495E; border-radius: 10px; margin-bottom: 20px;'>
                    <h2 style='color: #ECF0F1; margin-bottom: 0px;'>🏛️ NÖHÜ</h2>
                    <p style='color: #BDC3C7; font-size: 14px; font-weight: bold;'>Akıllı Kampüs & YZ Asistanı</p>
                </div>
            """, unsafe_allow_html=True)

            page = st.radio(
                "KONTROL PANELİ MENÜSÜ",
                ["📊 1. Ana Ekran & Veri", "💎 2. VIP Ayarları", "🚀 3. YZ Motoru", "✏️ 4. Manuel Düzenleme", "🤖 5. YZ Asistan & Kriz Radarı", "🔐 6. Hesap Yönetimi"]
            )
            
            st.write("---")
            st.markdown("### 🛡️ Sistem Durumu")
            st.success(f"🟢 **YZ Sunucusu:** Çevrimiçi\n\n👤 **Aktif Oturum:** {st.session_state['ad_soyad']}\n\n🏛️ **Yetki:** Yönetici")
            if st.button("🚪 Çıkış Yap", use_container_width=True):
                st.session_state.giris_yapildi = False
                st.rerun()

        st.markdown("## 🏫 YZ Destekli Ders Programı Otomasyonu")
        st.divider()

        # ORİJİNAL SAYFALAR BİREBİR AYNISI
        if page == "📊 1. Ana Ekran & Veri":
            st.markdown("### 📥 Veri Girişi ve Kapasite Özeti")
            yuklenen = st.file_uploader("Excel Dosyası (.xlsx)", type=["xlsx"])
            
            if yuklenen and st.session_state.yuklenen_dosya_adi != yuklenen.name:
                df_d = pd.read_excel(yuklenen, sheet_name="Dersler")
                df_h = pd.read_excel(yuklenen, sheet_name="Hocalar").fillna("")
                df_dl = pd.read_excel(yuklenen, sheet_name="Derslikler")

                def s_bul(df, kelimeler):
                    for col in df.columns:
                        c_kucuk = str(col).lower().replace(" ", "").replace("_", "")
                        for k in kelimeler:
                            if k in c_kucuk: return col
                    return df.columns[0] # Bulamazsa 1. sütunu al

                # DERSLER SAYFASI DÜZENLEMESİ
                df_d = df_d.rename(columns={s_bul(df_d, ["ders", "ad"]): "ad", s_bul(df_d, ["öğrenci", "sayı"]): "ogrenci_sayisi", s_bul(df_d, ["tür"]): "ders_tipi", s_bul(df_d, ["hoca", "öğretim"]): "hoca_id", s_bul(df_d, ["sınıf", "dönem"]): "sinif_seviyesi"})
                
                # HOCALAR SAYFASI (HATANIN ÇÖZÜLDÜĞÜ YER)
                h_ad_col = s_bul(df_h, ["hoca", "ad", "isim"])
                h_kisit_col = s_bul(df_h, ["istemediği", "yasak", "kısıt", "gün"])
                
                # Eğer algoritma kafası karışıp iki sütuna da aynı şeyi dediyse, zorla 1. ve 2. sütunu seç!
                if h_ad_col == h_kisit_col and len(df_h.columns) > 1:
                    h_ad_col = df_h.columns[0]
                    h_kisit_col = df_h.columns[1]
                    
                df_h = df_h.rename(columns={h_ad_col: "ad", h_kisit_col: "musait_olmayan_gunler"})
                
                # GÜVENLİK KONTROLLERİ
                if "id" not in df_h.columns: df_h["id"] = df_h["ad"] 
                if "istenmeyen_saatler" not in df_h.columns: df_h["istenmeyen_saatler"] = ""
                if "sehir_disi" not in df_h.columns: df_h["sehir_disi"] = False

                # DERSLİKLER SAYFASI
                df_dl = df_dl.rename(columns={s_bul(df_dl, ["derslik", "sınıf", "ad"]): "id", s_bul(df_dl, ["kapasite", "mevcut"]): "kapasite", s_bul(df_dl, ["tür"]): "derslik_tipi"})

                st.session_state.dersler = df_d.to_dict('records')
                st.session_state.hocalar = df_h.to_dict('records')
                st.session_state.derslikler = df_dl.to_dict('records')
                st.session_state.yuklenen_dosya_adi = yuklenen.name
                st.success("✅ Veritabanı bağlandı! Akıllı Sütun Tarayıcı Excel'deki her şeyi doğru formatta eşleştirdi.")
            if 'dersler' in st.session_state and len(st.session_state.dersler) > 0:
                st.divider()
                st.markdown("### 📊 Kapasite ve Sistem Özeti")
                m1, m2, m3 = st.columns(3)
                m1.metric("📚 Toplam Ders", len(st.session_state.dersler))
                m2.metric("👩‍🏫 Aktif Hoca", len(st.session_state.hocalar))
                m3.metric("🏢 Mevcut Derslik", len(st.session_state.derslikler))
            else: st.info("👈 Lütfen Excel yükleyin.")

        elif page == "💎 2. VIP Ayarları":
            if len(st.session_state.dersler) > 0:
                st.markdown("### 💎 VIP Hoca Kuralları")
                kol1, bosluk, kol2 = st.columns([4, 1, 5])
                with kol1:
                    h_list = [h["ad"] for h in st.session_state.hocalar]
                    sec_h = st.selectbox("👤 Hoca Seçin:", h_list)
                    a_hoca = next(h for h in st.session_state.hocalar if h["ad"] == sec_h)
                    def_vals = [v for v in [s.strip() for s in str(a_hoca.get("istenmeyen_saatler", "")).split(",") if s.strip()] if v in ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]]
                    yeni_k = st.multiselect("⛔ Kısıtlanacak Saatler:", ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"], default=def_vals)
                    is_sehir_disi = st.checkbox("✈️ Şehir Dışından Geliyor (Tüm derslerini tek güne topla)", value=bool(a_hoca.get("sehir_disi", False)))
                    if st.button("💾 Kaydet", type="primary", use_container_width=True):
                        a_hoca["istenmeyen_saatler"], a_hoca["sehir_disi"] = ", ".join(yeni_k), is_sehir_disi
                        st.rerun()
                with kol2:
                    vip_h = [h for h in st.session_state.hocalar if (str(h.get("istenmeyen_saatler", "")) != "") or h.get("sehir_disi")]
                    for v in vip_h:
                        with st.container(border=True):
                            st.write(f"👤 **{v['ad']}** {'✈️(Tek Gün)' if v.get('sehir_disi') else ''}\n\n 🕒 {v.get('istenmeyen_saatler', '')}")

        elif page == "🚀 3. YZ Motoru":
            if len(st.session_state.dersler) > 0:
                st.session_state.secilen_strateji = st.selectbox("🎯 Optimizasyon Hedefi", ["Dengeli", "Hoca Konforu Maksimum"])
                
                if st.button("✨ Yapay Zeka ile Optimize Et", type="primary", use_container_width=True):
                    
                    # --- 1. VERİTABANI VE YZ KÖPRÜSÜ (YENİ EKLENDİ) ---
                    # Hocaların kendi panellerinden girdiği kısıtları veritabanından çekip YZ'ye yediriyoruz
                    conn = baglanti_olustur()
                    db_kisitlar = pd.read_sql_query("SELECT h.ad_soyad, k.saat FROM kisitlar k JOIN hocalar h ON k.hoca_id = h.id", conn)
                    conn.close()

                    for hoca in st.session_state.hocalar:
                        # Bu hocanın veritabanında kendi girdiği bir kısıtı var mı?
                        h_kisit = db_kisitlar[db_kisitlar['ad_soyad'] == hoca['ad']]
                        if not h_kisit.empty:
                            saatler_listesi = h_kisit['saat'].tolist()
                            eski_kisitlar = str(hoca.get('istenmeyen_saatler', ''))
                            # Hem Excel'den gelen hem de Hocanın sistemden girdiği kısıtları birleştiriyoruz
                            yeni_kisitlar_str = ", ".join(list(set(saatler_listesi + [s.strip() for s in eski_kisitlar.split(',') if s.strip()])))
                            hoca['istenmeyen_saatler'] = yeni_kisitlar_str
                    # ----------------------------------------------------

                    with st.status("🧠 Yapay Zeka Programı İnşa Ediyor...", expanded=True) as durum:
                        progress_bar = st.progress(0) 
                        main.dersler, main.hocalar, main.derslikler = st.session_state.dersler, st.session_state.hocalar, st.session_state.derslikler
                        main.hedef_strateji = st.session_state.secilen_strateji 
                        
                        # Asıl Genetik Algoritma Motorun Çalışıyor
                        en_iyi_birey, final_skor = main.evrimi_baslat(100, progress_bar)
                        
                        st.session_state.fitness = final_skor[0] if isinstance(final_skor, (list, tuple)) else final_skor
                        res = [{"Gün": a['gun'], "Saat": a['saat'], "Ders": main.dersler[i]['ad'], "Hoca": next((h['ad'] for h in main.hocalar if h['id'] == main.dersler[i]['hoca_id']), "Bilinmiyor"), "Sınıf": a['derslik']['id'], "Dönem/Sınıf": main.dersler[i].get('sinif_seviyesi', '-')} for i, a in enumerate(en_iyi_birey)]
                        st.session_state.sonuc = pd.DataFrame(res)
                        durum.update(label="✨ Program Başarıyla Optimize Edildi!", state="complete", expanded=False)
                    st.rerun()

                # --- 2. SONUÇ EKRANI VE EXCEL İNDİRME BUTONU (YENİ EKLENDİ) ---
                if st.session_state.sonuc is not None:
                    h_skor, o_skor = memnuniyet_hesapla(st.session_state.sonuc)
                    kalite_puani = max(0, 100 - int(st.session_state.fitness / 5)) 
                    s1, s2, s3 = st.columns(3)
                    s1.metric("🎯 YZ Program Kalitesi", f"%{kalite_puani}")
                    s2.metric("👨‍🏫 Hoca Memnuniyeti", f"%{h_skor}")
                    s3.metric("🎓 Öğrenci Memnuniyeti", f"%{o_skor}")
                    
                    st.dataframe(st.session_state.sonuc, use_container_width=True, height=300)
                    
                    # DataFrame'i bellekte (RAM) Excel formatına dönüştürüp indirme butonu veriyoruz
                    c1, c2, c3 = st.columns([1,2,1])
                    with c2:
                        to_excel = io.BytesIO()
                        st.session_state.sonuc.to_excel(to_excel, index=False, sheet_name='NOHU_Program')
                        to_excel.seek(0)
                        st.download_button(
                            label="📥 Programı Excel Olarak İndir (Dekanlık Çıktısı)", 
                            data=to_excel, 
                            file_name="NOHU_YZ_Ders_Programi.xlsx", 
                            mime="application/vnd.ms-excel",
                            use_container_width=True
                        )

        elif page == "🤖 5. YZ Asistan & Kriz Radarı":
            st.markdown("### 💬 YZ Asistan & Kriz Yönetim Merkezi")
            
            tab_chat, tab_kriz, tab_gelen_kutusu, tab_ogrenci_sikayetleri = st.tabs(["💬 NLP Simülasyon", "⚡ Çakışma & Kapasite", "📥 Hoca Mesajları", "🎓 Öğrenci Şikayetleri"])
            
            # --- 1. SEKME: NLP SİMÜLASYON ---
            with tab_chat:
                st.info("💡 **Örnek Komutlar:** 'Sınıf önerilerini uygula', 'Öğrenci şikayetlerini çöz' veya 'Ahmet hoca sabahtan gelmesin'")
                mesaj = st.chat_input("Asistana bir görev verin...")
                if mesaj:
                    with st.chat_message("user"): st.write(mesaj)
                    with st.chat_message("assistant"):
                        msg_lower = mesaj.lower()
                        
                        # ==========================================
                        # SENARYO 1: SINIF KAPASİTE SİMÜLASYONU
                        # ==========================================
                        if "sınıf" in msg_lower and ("öneri" in msg_lower or "uygula" in msg_lower or "getir" in msg_lower):
                            if st.session_state.sonuc is None:
                                st.error("Önce '3. YZ Motoru' sayfasından ana programı üretmelisiniz!")
                            else:
                                st.success("✅ Sınıf kapasiteleri analiz ediliyor. **Anlık Simülasyon Başlatılıyor...**")
                                with st.spinner("YZ Alternatif Sınıfları Yerleştiriyor..."):
                                    df_sim = st.session_state.sonuc.copy()
                                    ders_dict = {d['ad']: d.get('ogrenci_sayisi', 0) for d in st.session_state.dersler}
                                    derslik_dict = {dl['id']: dl.get('kapasite', 0) for dl in st.session_state.derslikler}
                                    dolu_siniflar = {}
                                    for _, row in df_sim.iterrows():
                                        zaman = f"{row['Gün']}_{row['Saat']}"
                                        if zaman not in dolu_siniflar: dolu_siniflar[zaman] = []
                                        dolu_siniflar[zaman].append(row['Sınıf'])

                                    degisen_dersler = []
                                    for index, row in df_sim.iterrows():
                                        d_adi = row['Ders']
                                        s_adi = row['Sınıf']
                                        g_s = f"{row['Gün']}_{row['Saat']}"
                                        ogr_say = int(ders_dict.get(d_adi, 0)) if ders_dict.get(d_adi) else 0
                                        s_kap = int(derslik_dict.get(s_adi, 0)) if derslik_dict.get(s_adi) else 0

                                        if ogr_say > s_kap:
                                            for dl in st.session_state.derslikler:
                                                kap = int(dl.get('kapasite', 0)) if dl.get('kapasite') else 0
                                                if kap >= ogr_say and dl['id'] not in dolu_siniflar.get(g_s, []):
                                                    df_sim.at[index, 'Sınıf'] = dl['id']
                                                    dolu_siniflar[g_s].append(dl['id'])
                                                    degisen_dersler.append(f"**{d_adi}** ({s_adi} ➡️ {dl['id']})")
                                                    break

                                    st.write("**Kapasite Krizleri Çözülen Yeni Program (Sınıflar Güncellendi):**")
                                    if degisen_dersler: st.info(f"🔄 Değişen Sınıflar: {', '.join(degisen_dersler)}")
                                    else: st.success("Değiştirilecek bir kapasite sorunu bulunamadı.")
                                    st.dataframe(df_sim, use_container_width=True)
                                    st.session_state['gecici_simulasyon'] = df_sim
                                    st.session_state['gecici_fitness'] = st.session_state.get('fitness', 100)

                        # ==========================================
                        # SENARYO 2: ÖĞRENCİ ÇAKIŞMA SİMÜLASYONU VE YAN ETKİ ANALİZİ
                        # ==========================================
                        elif "öğrenci" in msg_lower and ("şikayet" in msg_lower or "çöz" in msg_lower or "uygula" in msg_lower or "getir" in msg_lower):
                            if st.session_state.sonuc is None:
                                st.error("Önce ana programı üretmelisiniz!")
                            else:
                                conn = baglanti_olustur()
                                df_sikayetler = pd.read_sql_query("SELECT ders1, ders2, sebep FROM ogrenci_sikayetleri", conn)
                                conn.close()

                                if df_sikayetler.empty:
                                    st.warning("Şu an sistemde kayıtlı bir öğrenci şikayeti bulunmuyor.")
                                else:
                                    st.success("✅ Öğrenci çakışmaları veritabanından çekildi. **Anlık Simülasyon ve Yan Etki Analizi Başlatılıyor...**")
                                    with st.spinner("YZ Çakışan Dersleri Ayırıyor ve Fatura Çıkarıyor..."):
                                        df_sim = st.session_state.sonuc.copy()
                                        degisen_dersler_raporu = []
                                        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]
                                        saatler = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]

                                        for _, sikayet in df_sikayetler.iterrows():
                                            d1 = sikayet['ders1'].strip()
                                            d2 = sikayet['ders2'].strip()

                                            satir1 = df_sim[df_sim['Ders'].str.contains(d1, case=False, na=False)]
                                            satir2 = df_sim[df_sim['Ders'].str.contains(d2, case=False, na=False)]

                                            if not satir1.empty and not satir2.empty:
                                                idx1, idx2 = satir1.index[0], satir2.index[0]
                                                eski_gun = df_sim.at[idx2, 'Gün']
                                                eski_saat = df_sim.at[idx2, 'Saat']
                                                
                                                if df_sim.at[idx1, 'Gün'] == eski_gun and str(df_sim.at[idx1, 'Saat'])[:5] == str(eski_saat)[:5]:
                                                    hoca2 = df_sim.at[idx2, 'Hoca']
                                                    sinif2 = df_sim.at[idx2, 'Sınıf']
                                                    yer_bulundu = False
                                                    
                                                    for g in gunler:
                                                        for s in saatler:
                                                            s_tam = f"{s} - {str(int(s[:2])+1).zfill(2)}:00"
                                                            h_mesgul = not df_sim[(df_sim['Gün'] == g) & (df_sim['Saat'].str.contains(s)) & (df_sim['Hoca'] == hoca2)].empty
                                                            s_mesgul = not df_sim[(df_sim['Gün'] == g) & (df_sim['Saat'].str.contains(s)) & (df_sim['Sınıf'] == sinif2)].empty
                                                            
                                                            if not h_mesgul and not s_mesgul:
                                                                df_sim.at[idx2, 'Gün'] = g
                                                                df_sim.at[idx2, 'Saat'] = s_tam
                                                                
                                                                rapor = f"🎓 **ÇÖZÜLEN KRİZ:** '{d1}' ile '{d2}' dersleri ayrıldı.\n"
                                                                rapor += f"🔄 **YAPILAN HAMLE:** **{d2}** dersi {eski_gun} {eski_saat} ➡️ **{g} {s_tam}** saatine kaydırıldı.\n"
                                                                rapor += f"⚠️ **BU HAMLENİN BİZE MALİYETİ (YAN ETKİLER):**\n"
                                                                
                                                                hoca_yeni_yuk = len(df_sim[(df_sim['Gün'] == g) & (df_sim['Hoca'] == hoca2)])
                                                                if hoca_yeni_yuk >= 3:
                                                                    rapor += f"  ➖ **Hoca Yorgunluğu:** {hoca2} hocamızın {g} günü ders yükü {hoca_yeni_yuk} saate çıktı. Rıza alınması tavsiye edilir!\n"
                                                                else:
                                                                    rapor += f"  ➕ **Hoca Uyumu:** {hoca2} hocamızın programı için gayet uygun.\n"
                                                                    
                                                                rapor += f"  📌 **Öğrenci Notu:** '{sikayet['sebep']}' sorunu giderilmiş oldu."
                                                                
                                                                degisen_dersler_raporu.append(rapor)
                                                                yer_bulundu = True
                                                                break
                                                        if yer_bulundu: break

                                        st.write("### 📊 YZ Çözüm ve Yan Etki (Trade-off) Raporu")
                                        if degisen_dersler_raporu: 
                                            for r in degisen_dersler_raporu:
                                                st.info(r)
                                        else: 
                                            st.success("Mevcut programda şikayet edilen dersler zaten çakışmıyor.")
                                            
                                        st.write("**Yeni Program Tablosu:**")
                                        st.dataframe(df_sim, use_container_width=True)
                                        st.session_state['gecici_simulasyon'] = df_sim
                                        st.session_state['gecici_fitness'] = st.session_state.get('fitness', 100)

                        # ==========================================
                        # SENARYO 3: HOCA KISITI SİMÜLASYONU
                        # ==========================================
                        else:
                            if len(st.session_state.hocalar) == 0:
                                st.error("Lütfen önce Excel yükleyin!")
                            else:
                                hedef_hoca, yasak_gunler, yasak_saatler, s_disi, is_radar = asistan_anla(mesaj, st.session_state.hocalar)
                                if hedef_hoca:
                                    m_k = str(hedef_hoca.get('istenmeyen_saatler', ''))
                                    y_k = [s.strip() for s in m_k.split(',') if s.strip()]
                                    for saat in yasak_saatler:
                                        if saat not in y_k: y_k.append(saat)
                                    hedef_hoca['istenmeyen_saatler'] = ", ".join(y_k)
                                    
                                    st.success(f"✅ {hedef_hoca['ad']} için kısıtlar işlendi. **Anlık Simülasyon Başlatılıyor...**")
                                    with st.spinner("YZ Yeni Programı Çiziyor..."):
                                        main.dersler, main.hocalar, main.derslikler = st.session_state.dersler, st.session_state.hocalar, st.session_state.derslikler
                                        en_iyi_birey, final_skor = main.evrimi_baslat(30, st.progress(0))
                                        res = [{"Gün": a['gun'], "Saat": a['saat'], "Ders": main.dersler[i]['ad'], "Hoca": next((h['ad'] for h in main.hocalar if h['id'] == main.dersler[i]['hoca_id']), "Bilinmiyor"), "Sınıf": a['derslik']['id'], "Dönem/Sınıf": main.dersler[i].get('sinif_seviyesi', '-')} for i, a in enumerate(en_iyi_birey)]
                                        df_sim = pd.DataFrame(res)
                                        st.write(f"**{hedef_hoca['ad']} İçin Simüle Edilen Yeni Program:**")
                                        st.dataframe(df_sim[df_sim['Hoca'].str.contains(hedef_hoca['ad'].strip(), case=False, na=False)], use_container_width=True)
                                        st.session_state['gecici_simulasyon'] = df_sim
                                        st.session_state['gecici_fitness'] = final_skor[0] if isinstance(final_skor, (list, tuple)) else final_skor
                                else:
                                    st.error("Komutu tam anlayamadım.")
                
                # ORTAK SİMÜLASYON ONAY BUTONU
                if 'gecici_simulasyon' in st.session_state:
                    st.markdown("---")
                    st.warning("Yukarıdaki simülasyon şu an taslak halindedir. Tüm sisteme uygulamak ister misiniz?")
                    if st.button("💾 Bu Simülasyonu Ana Programa (Tüm Sisteme) Entegre Et", type="primary", use_container_width=True):
                        st.session_state.sonuc = st.session_state['gecici_simulasyon']
                        st.session_state.fitness = st.session_state['gecici_fitness']
                        del st.session_state['gecici_simulasyon']
                        st.success("✅ Simülasyon başarıyla onaylandı! Yeni program tüm sisteme yansıtıldı.")
                        st.rerun()

            # --- 2. SEKME: ÇAKIŞMA YÖNETİMİ VE RÜTBE BAZLI ÖNERİ ---
            with tab_kriz:
                st.subheader("👨‍🏫 Akademik Uyum ve Kriz Yönetimi")
                if "cakisma_cozuldu" not in st.session_state: st.session_state.cakisma_cozuldu = False
                
                if st.session_state.sonuc is not None and not st.session_state.cakisma_cozuldu:
                    df_prog = st.session_state.sonuc
                    conn = baglanti_olustur()
                    kisitlar_df = pd.read_sql_query("SELECT h.ad_soyad, k.gun, k.saat FROM kisitlar k JOIN hocalar h ON k.hoca_id = h.id", conn)
                    conn.close()

                    sorunlu_hocalar = []
                    for _, k in kisitlar_df.iterrows():
                        s_kontrol = k['saat'][:5] 
                        ihlal = df_prog[(df_prog['Hoca'] == k['ad_soyad']) & (df_prog['Gün'] == k['gun']) & (df_prog['Saat'].str.contains(s_kontrol))]
                        if not ihlal.empty and k['ad_soyad'] not in sorunlu_hocalar:
                            sorunlu_hocalar.append(k['ad_soyad'])

                    if sorunlu_hocalar:
                        st.error(f"⚠️ **Otomatik Tespit:** Algoritma zorunluluktan dolayı bazı kısıtları ihlal etmek zorunda kaldı. Kısıtı ezilen hocalarımız: **{', '.join(sorunlu_hocalar)}**")
                        secilen_hedef_hoca = st.selectbox("Lütfen bilgilendirme ve yeni saat önerisi gönderilecek hocayı seçin:", sorunlu_hocalar)
                    else:
                        st.success("✅ Harika! Şu an hiçbir hocanın kısıtı ihlal edilmemiş, program herkesin isteğine uygun.")
                        hoca_isimleri = [h['ad'] for h in st.session_state.hocalar] if 'hocalar' in st.session_state and st.session_state.hocalar else ["Excel Yüklenmedi"]
                        secilen_hedef_hoca = st.selectbox("Yine de manuel bildirim göndermek isterseniz bir hoca seçin:", hoca_isimleri)
                    
                    oneri_metni = ""
                    if secilen_hedef_hoca != "Excel Yüklenmedi":
                        conn = baglanti_olustur()
                        temiz_isim = secilen_hedef_hoca.strip()
                        rutbe_sorgu = pd.read_sql_query(f"SELECT rutbe_carpani FROM hocalar WHERE ad_soyad='{temiz_isim}'", conn)
                        conn.close()
                        carp = 1 
                        if not rutbe_sorgu.empty: carp = rutbe_sorgu['rutbe_carpani'].values[0]
                            
                        if carp >= 3: oneri_metni = "💡 Kıymetli Hocam, programınızdaki yoğunluğu hafifletmek adına size en uygun alternatif saatler olarak **Salı 10:00-12:00** veya **Çarşamba 13:00-15:00** aralıklarını değerlendirmenizi saygılarımızla rica ederiz."
                        elif carp == 2: oneri_metni = "💡 Sayın Hocam, sistemimizdeki genel doluluk oranlarına göre **Perşembe 10:00-12:00** veya **Çarşamba 15:00-17:00** saatleri dersleriniz için oldukça uygundur."
                        else: oneri_metni = "💡 Bölüm programının sağlıklı yürütülebilmesi için uygun alternatif saatler olan **Pazartesi 08:00-10:00** veya **Cuma 15:00-17:00** aralıklarını değerlendirebilirsiniz."

                    st.info(f"🤖 **Hocanın Ekranına Düşecek YZ Önerisi:**\n{oneri_metni}")
                    ozel_not = st.text_area("Hocaya gönderilecek mesajın sonuna eklenecek Dekanlık Özel Notu (İsteğe Bağlı):", placeholder="Örn: Sayın hocam, bölüm başkanlığımızın ortak kararı gereği programınız bu şekilde güncellenmiştir...")
                    
                    if st.button("✨ Akademik Nezaketle Uyarı ve Öneriyi İlet", type="primary"):
                        st.session_state.cakisma_cozuldu = True
                        baz_mesaj = f"Kıymetli {secilen_hedef_hoca};\n\nDekanlığımıza iletmiş olduğunuz saat kısıtınız, zorunlu ortak derslerin yerleşimi ve akademik hiyerarşi optimizasyonu sebebiyle oluşan sistem tıkanıklığından dolayı maalesef programda tam olarak uygulanamamıştır. Anlayışınız için teşekkür ederiz.\n\n{oneri_metni}"
                        if ozel_not: baz_mesaj += f"\n\n📝 **Dekanlık Notu:** {ozel_not}"
                        st.session_state.hoca_uyari_mesaji = baz_mesaj
                        st.rerun()
                elif st.session_state.sonuc is None:
                    st.warning("Bu analizi yapabilmek için önce '3. YZ Motoru' sayfasından ana programı üretmelisiniz.")
                else:
                    st.success("✅ Tüm akademik uyarılar başarıyla hocalara iletildi.")

            # --- 3. SEKME: HOCALARDAN GELEN MESAJLAR ---
            with tab_gelen_kutusu:
                st.subheader("📬 Akademisyen Kısıt ve Mazeret Talepleri")
                conn = baglanti_olustur()
                df_gelenler = pd.read_sql_query("SELECT h.ad_soyad as 'Hoca', k.gun as 'İstediği Gün', k.saat as 'İstediği Saat', k.sebep as 'Hoca Mazereti/Açıklaması' FROM kisitlar k JOIN hocalar h ON k.hoca_id = h.id", conn)
                conn.close()
                if not df_gelenler.empty: st.dataframe(df_gelenler, use_container_width=True, hide_index=True)
                else: st.info("Şu an hocalardan gelen bir kısıt veya mesaj bulunmuyor.")

            # --- 4. SEKME: ÖĞRENCİLERDEN GELEN ŞİKAYETLER ---
            with tab_ogrenci_sikayetleri:
                st.subheader("🎓 Öğrencilerden Gelen Çakışma Bildirimleri")
                conn = baglanti_olustur()
                df_sikayetler = pd.read_sql_query("SELECT ders1 as '1. Ders', ders2 as '2. Ders', sebep as 'Öğrenci Mazereti' FROM ogrenci_sikayetleri", conn)
                conn.close()
                if not df_sikayetler.empty: st.dataframe(df_sikayetler, use_container_width=True, hide_index=True)
                else: st.info("Şu an öğrencilerden gelen bir çakışma bildirimi bulunmuyor.")
        elif page == "✏️ 4. Manuel Düzenleme":
            st.markdown("### ✏️ Manuel Program Düzenleyici")
            if st.session_state.sonuc is not None:
                st.info("💡 Tablodaki herhangi bir hücreye çift tıklayarak içeriğini değiştirebilirsiniz. Bittiğinde kaydetmeyi unutmayın.")
                
                # st.data_editor ile yapılan değişiklikleri yeni_df içine alıyoruz
                yeni_df = st.data_editor(st.session_state.sonuc, use_container_width=True, hide_index=True)
                
                # KAYDET BUTONU
                if st.button("💾 Değişiklikleri Ana Programa Kaydet", type="primary", use_container_width=True):
                    st.session_state.sonuc = yeni_df
                    st.success("✅ Manuel değişiklikler başarıyla ana programa entegre edildi!")
                    st.rerun()
            else:
                st.warning("Düzenleme yapabilmek için önce '3. YZ Motoru' sayfasından programı üretmelisiniz.")        
        elif page == "🔐 6. Hesap Yönetimi":
            st.subheader("⚙️ Kullanıcı ve Yetki Yönetimi Merkezî")
            
            # Sayfayı iki sekmeye bölüyoruz: Ekleme ve Silme
            tab_ekle, tab_sil = st.tabs(["👤 Yeni Personel Ekle", "🗑️ Personel Kaydı Sil"])
            
            # --- 1. SEKME: PERSONEL EKLEME (Mevcut Kodun) ---
            with tab_ekle:
                with st.form("yeni_personel_formu"):
                    y_ad = st.text_input("Ad Soyad")
                    y_kadi = st.text_input("Kullanıcı Adı")
                    y_sifre = st.text_input("Şifre", type="password")
                    y_rutbe = st.number_input("Rütbe Çarpanı (1: Asistan, 2: Doçent, 3: Profesör)", min_value=1, max_value=3, value=1)
                    y_rol = st.selectbox("Sistem Rolü", ["hoca", "admin"])
                    
                    if st.form_submit_button("Personeli Sisteme Kaydet", type="primary"):
                        if personel_ekle(y_ad, y_kadi, y_sifre, y_rutbe, y_rol):
                            st.success(f"✅ {y_ad} sisteme başarıyla eklendi!")
                        else:
                            st.error("❌ Bu kullanıcı adı zaten sistemde kayıtlı!")

            # --- 2. SEKME: PERSONEL SİLME (YENİ EKLENEN KISIM) ---
            with tab_sil:
                st.markdown("### ⚠️ Sistemden Hoca Çıkarma İşlemi")
                st.warning("Dikkat: Bir hocayı sildiğinizde, onun sisteme girdiği tüm kısıtlar ve mazeretler de kalıcı olarak silinecektir.")
                
                conn = baglanti_olustur()
                # Admin (Sistem Yöneticisi) hesabını yanlışlıkla silmemek için onu listeden çıkarıyoruz
                df_kullanicilar = pd.read_sql_query("SELECT id, ad_soyad, kullanici_adi, rutbe_carpani FROM hocalar WHERE rol != 'admin'", conn)
                conn.close()

                if not df_kullanicilar.empty:
                    st.dataframe(df_kullanicilar, use_container_width=True, hide_index=True)
                    
                    # Kullanıcıya seçmesi için isimleri ve ID'leri birleştiriyoruz
                    secenekler = df_kullanicilar['id'].astype(str) + " - " + df_kullanicilar['ad_soyad']
                    silinecek_hoca = st.selectbox("Lütfen sistemden tamamen silinecek hocayı seçin:", secenekler)

                    if st.button("🚨 Seçili Hocayı ve Verilerini Kalıcı Olarak Sil", type="primary"):
                        # Seçilen metinden sadece ID numarasını çekip alıyoruz
                        secili_id = int(silinecek_hoca.split(" - ")[0])
                        
                        conn = baglanti_olustur()
                        cursor = conn.cursor()
                        # 1. Önce hocanın girdiği kısıtları siliyoruz (Veritabanında yetim veri kalmasın diye)
                        cursor.execute("DELETE FROM kisitlar WHERE hoca_id=?", (secili_id,))
                        # 2. Sonra hocanın kendi hesabını siliyoruz
                        cursor.execute("DELETE FROM hocalar WHERE id=?", (secili_id,))
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ Hoca ve ona ait tüm veriler sistemden başarıyla kazındı!")
                        st.rerun() # Sayfayı yenile ki giden hocanın adı anında listeden düşsün
                else:
                    st.info("Sistemde silinebilecek kayıtlı bir hoca hesabı bulunmuyor.")
    # --- YETKİ: STANDART HOCA (SADECE KISIT EKRANI) ---
   # ==========================================
    # YETKİ 2: STANDART HOCA PANELİ (GELİŞMİŞ)
    # ==========================================
    # ==========================================
    # YETKİ 2: STANDART HOCA PANELİ (GELİŞMİŞ)
    # ==========================================
    # ==========================================
    # YETKİ 2: STANDART HOCA PANELİ (GELİŞMİŞ)
    # ==========================================
    elif st.session_state['rol'] == 'hoca':
        col_b, col_c = st.columns([8, 2])
        with col_b: st.markdown(f"### 👨‍🏫 Hoş Geldiniz, {st.session_state['ad_soyad']}")
        with col_c:
            if st.button("🚪 Çıkış Yap", use_container_width=True):
                st.session_state.giris_yapildi = False; st.rerun()
        st.divider()

        if 'hoca_uyari_mesaji' in st.session_state:
            st.warning("🔔 **DEKANLIK YZ SİSTEM BİLDİRİMİ:**")
            st.write(st.session_state.hoca_uyari_mesaji)
            if st.button("Okudum, Anladım"):
                del st.session_state['hoca_uyari_mesaji']
                st.rerun()

        tab_kisit, tab_program = st.tabs(["🚫 Kısıt (Kapalı Saat) Yönetimi", "📅 Haftalık Kişisel Ders Programım"])
        
        with tab_kisit:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Yeni Saat Kapat ve Dekanlığa Bildir")
                with st.form("coklu_kisit_formu"):
                    secilen_gun = st.selectbox("Gün Seçin", ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"])
                    
                    tum_saatler = ["08:00 - 09:00", "09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00", "16:00 - 17:00"]
                    
                    # YENİ: TÜM GÜNÜ KAPAT BUTONU
                    tum_gun = st.checkbox("🗓️ Bu Günün TAMAMINI Kapat")
                    
                    if tum_gun:
                        secilen_saatler = tum_saatler
                        st.info("💡 Seçili günün tüm saatleri otomatik olarak kapatılacak.")
                    else:
                        secilen_saatler = st.multiselect("Kapatılacak Saatleri Seçin", tum_saatler)
                    
                    # YENİ: İSTEĞE BAĞLI MAZERET
                    hoca_mesaji = st.text_input("Dekanlığa Notunuz / Mazeretiniz (İsteğe Bağlı)")
                    
                    if st.form_submit_button("Saatleri Kapat ve İlet", type="primary"):
                        if tum_gun or secilen_saatler:
                            final_saatler = tum_saatler if tum_gun else secilen_saatler
                            conn = baglanti_olustur()
                            cursor = conn.cursor()
                            sebep_kayit = hoca_mesaji if hoca_mesaji else "Belirtilmedi" # Boşsa belirtilmedi yazar
                            for saat in final_saatler:
                                cursor.execute("INSERT INTO kisitlar (hoca_id, gun, saat, sebep) VALUES (?, ?, ?, ?)", (st.session_state['kullanici_id'], secilen_gun, saat, sebep_kayit))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ {secilen_gun} günü için kısıtlarınız kaydedildi!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Lütfen kapatmak için saat seçin veya 'Tüm Günü Kapat'ı işaretleyin.")
                            
            with c2:
                st.subheader("Aktif Kısıtlarınız ve Yönetim")
                conn = baglanti_olustur()
                cursor = conn.cursor()
                # Kısıtları ID'si ile birlikte çekiyoruz ki hangisini sileceğimizi bilelim
                kisitlar = cursor.execute(f"SELECT id, gun, saat, sebep FROM kisitlar WHERE hoca_id={st.session_state['kullanici_id']}").fetchall()
                
                if kisitlar:
                    for k_id, gun, saat, sebep in kisitlar:
                        col_info, col_btn = st.columns([8, 2])
                        with col_info:
                            st.info(f"🚫 **{gun}** | {saat} \n*(Mazeret: {sebep})*")
                        with col_btn:
                            # Streamlit'te her butonun eşsiz bir key'i olmalıdır
                            if st.button("🗑️ Sil", key=f"sil_{k_id}", help="Bu kısıtı kaldır"):
                                conn.cursor().execute(f"DELETE FROM kisitlar WHERE id={k_id}")
                                conn.commit()
                                st.success("Kısıt silindi!")
                                st.rerun() # Sayfayı yenile ki silinen anında ekrandan kaybolsun
                else:
                    st.success("Şu an kapattığınız bir saat bulunmuyor. Programınız tamamen açık.")
                conn.close()
                    
        with tab_program:
            st.subheader("Bu Haftaki Derslerim")
            if st.session_state.sonuc is not None:
                df_prog = st.session_state.sonuc
                hoca_prog = df_prog[df_prog['Hoca'] == st.session_state['ad_soyad']]
                if not hoca_prog.empty:
                    st.dataframe(hoca_prog, use_container_width=True, hide_index=True)
                else:
                    st.info("Size atanmış bir ders bulunamadı.")
            else:
                st.info("Dekanlık henüz programı oluşturmamış.")
        # --- 2. SEKME: KİŞİSEL DERS PROGRAMI ---
        with tab_program:
            st.subheader("Bana Atanan Dersler")
            
            # Eğer Admin programı ürettiyse (sonuc varsa)
            if st.session_state.sonuc is not None:
                # Tüm programı DEĞİL, sadece bu hocanın adının geçtiği satırları filtreliyoruz
                # Tüm programı DEĞİL, sadece bu hocanın adının geçtiği satırları filtreliyoruz
                # Geliştirilmiş Filtre: Büyük/küçük harf duyarsız ve boşlukları yok sayarak arar
                aranan_isim = st.session_state['ad_soyad'].strip()
                df_hoca_prog = st.session_state.sonuc[st.session_state.sonuc['Hoca'].str.contains(aranan_isim, case=False, na=False)]
                
                if not df_hoca_prog.empty:
                    # Hocaya ufak istatistikler veriyoruz
                    k1, k2 = st.columns(2)
                    k1.metric("Toplam Ders Saatiniz", f"{len(df_hoca_prog)} Saat")
                    en_yogun_gun = df_hoca_prog['Gün'].mode()[0] if not df_hoca_prog.empty else "-"
                    k2.metric("En Yoğun Gününüz", en_yogun_gun)
                    
                    st.dataframe(df_hoca_prog, use_container_width=True, hide_index=True)
                else:
                    st.info("Dekanlığın oluşturduğu son programda size atanmış bir ders bulunmuyor.")
            else:
                st.warning("Dekanlık henüz resmi ders programını yayınlamadı. YZ motoru çalıştırıldığında programınız buraya düşecektir.")