# 🎓 OptiCampus: AI-Powered Academic Scheduling & Crisis Management System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite)
![AI](https://img.shields.io/badge/AI-Genetic_Algorithm-8A2BE2?style=for-the-badge)

OptiCampus, üniversitelerdeki haftalar süren, manuel ve hataya açık ders programı hazırlama sürecini **Genetik Algoritma** ve **Doğal Dil İşleme (NLP)** kullanarak dakikalara indiren bulut tabanlı bir B2B SaaS platformudur. 

Matematiksel olarak **"NP-Hard"** sınıfında yer alan ders atama ve çakışma problemini çözerken, aynı zamanda akademik nezaket ve hiyerarşiyi koruyan otonom bir kriz radarına sahiptir.

---

## 🚀 Temel Özellikler

- **🧬 Genetik Algoritma Motoru:** Binlerce öğrenci, yüzlerce hoca ve mekan kısıtını çaprazlayıp mutasyona uğratarak %100 çakışmasız "Global Optimum" programı saniyeler içinde üretir.
- **🤖 NLP Destekli Kriz Radarı:** Algoritma çözümsüz bir kısıtla karşılaştığında (örn. iki zorunlu durumun çakışması), soğuk bir sistem hatası vermek yerine akademisyene rütbesine uygun "Akademik Nezaket" protokolüyle otomatik alternatif saatler önerir.
- **📌 Çivileme (Pinning) Teknolojisi:** Dekanlıkların 1. sınıf zorunlu YÖK derslerini (İnkılap, Türk Dili vb.) sisteme sabitleyip, YZ'nin geri kalan programı bu çivilerin etrafına örmesini sağlar.
- **👥 Mikroservis Tabanlı Rol Panelleri:**
  - **Dekanlık Paneli (Admin):** Excel ile veri yükleme ve Genetik Algoritmayı tetikleme.
  - **Hoca Paneli:** Akademisyenlerin uygun olmadıkları gün ve saatleri sisteme işledikleri mazeret ekranı.
  - **Öğrenci Şikayet Modülü:** Öğrencilerin çakışan derslerini doğrudan veritabanına iletebildiği form yapısı.

---

## 🛠️ Kullanılan Teknolojiler (Tech Stack)

* **Backend & Algoritma Çekirdeği:** `Python`, `DEAP` (Evrimsel algoritmalar için), `Pandas`, `NumPy`
* **Frontend (Arayüz):** `Streamlit`
* **Veritabanı:** `SQLite`
* **Mimari:** Modüler B2B SaaS, Mikroservis Veri Akışı

---


## 💻 Kurulum ve Çalıştırma

Projeyi kendi yerel bilgisayarınızda (local) çalıştırmak için aşağıdaki adımları izleyebilirsiniz:

1. **Repoyu Klonlayın:**
   ```bash
   git clone [https://github.com/KULLANICI_ADIN/OptiCampus.git](https://github.com/KULLANICI_ADIN/OptiCampus.git)
   cd OptiCampus

## 🎮 Hızlı Demo Senaryosu (Nasıl Test Edilir?)

Sistemin yeteneklerini tam olarak deneyimlemek için aşağıdaki 3 adımlı senaryoyu uygulayabilirsiniz:

**Adım 1: Kısıtları Belirleyin (Hoca Rolü)**
1. `test_hoca` hesabı ile sisteme giriş yapın.
2. Sol menüden "Mazeret ve Kısıt Bildir" ekranına gelin.
3. Kendinize (örneğin Perşembe sabahı için) bir "Ders Veremez" kısıtı ekleyin ve sistemden çıkış yapın.

**Adım 2: Verileri Yükleyin (Dekanlık Rolü)**
1. `admin` hesabı ile sisteme giriş yapın.
2. Ana paneldeki yükleme alanına projemizin ana dizininde bulunan `ornek_veri_sablonu.xlsx` dosyasını yükleyin.

**Adım 3: Yapay Zekayı Tetikleyin (Sihir Zamanı)**
1. Admin panelindeki **"Genetik Algoritmayı Başlat"** butonuna tıklayın.
2. Algoritmanın saniyeler içinde binlerce varyasyonu eleyerek, `test_hoca`nın Perşembe günkü kısıtını **hiçbir dersle çakıştırmadan** %100 uyumlu programı nasıl çizdiğini (ve gerekirse NLP asistanının nasıl devreye girdiğini) canlı olarak izleyin!
