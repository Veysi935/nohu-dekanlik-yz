import random
import time 
from deap import base, creator, tools
from veri import derslikler, hocalar, dersler, gunler, saatler

hedef_strateji = "Dengeli"

if not hasattr(creator, "FitnessMin"):
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

def gen_uret():
    return {"gun": random.choice(gunler), "saat": random.choice(saatler), "derslik": random.choice(derslikler)}

def birey_uret():
    return [gen_uret() for _ in range(len(dersler))]

toolbox.register("individual", tools.initIterate, creator.Individual, birey_uret)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def degerlendir(birey):
    ceza = 0
    atama_listesi = []
    hoca_gunluk_ders_sayisi = {}
    sinif_gunluk_saatler = {} # YENİ: Öğrenci boşluklarını takip etmek için
    saat_indeksleri = {"08:00":0, "09:00":1, "10:00":2, "11:00":3, "13:00":4, "14:00":5, "15:00":6, "16:00":7}
    hoca_aktif_gunler = {} # YENİ: Şehir dışından gelen hocaların günlerini saymak için
    for i, ders_atama in enumerate(birey):
        su_anki_ders = dersler[i]
        
        # 1. HARD KISITLAR
        if su_anki_ders["ogrenci_sayisi"] > ders_atama["derslik"]["kapasite"]: ceza += 50
        hoca = next((h for h in hocalar if h["id"] == su_anki_ders["hoca_id"]), None)
        if hoca and ders_atama["gun"] in hoca["musait_olmayan_gunler"]: ceza += 80

        # VIP Kısıtları
        if hoca and "istenmeyen_saatler" in hoca and str(hoca["istenmeyen_saatler"]) != "nan" and str(hoca["istenmeyen_saatler"]).strip() != "":
            istenmeyenler = [s.strip() for s in str(hoca["istenmeyen_saatler"]).split(",")]
            for istenmeyen in istenmeyenler:
                if istenmeyen in ders_atama["saat"]:
                    ceza += 200

        # Mekan Kısıtları
        d_tipi = str(su_anki_ders.get("ders_tipi", "Teorik")).strip()
        sinif_tipi = str(ders_atama["derslik"].get("derslik_tipi", "Sınıf")).strip()
        if d_tipi == "Lab" and sinif_tipi != "Lab": ceza += 200
        elif d_tipi == "Teorik" and sinif_tipi == "Lab": ceza += 10

        # 2. ÇAKIŞMA KONTROLLERİ
        for j, diger_atama in enumerate(atama_listesi):
            diger_ders = dersler[j]
            if ders_atama["gun"] == diger_atama["gun"] and ders_atama["saat"] == diger_atama["saat"]:
                if su_anki_ders["hoca_id"] == diger_ders["hoca_id"]: ceza += 150
                if ders_atama["derslik"]["id"] == diger_atama["derslik"]["id"]: ceza += 150
                
                seviye1 = su_anki_ders.get("sinif_seviyesi")
                seviye2 = diger_ders.get("sinif_seviyesi")
                if seviye1 is not None and seviye2 is not None and str(seviye1) != "nan" and str(seviye1) == str(seviye2):
                    ceza += 150
        
        # 3. YORGUNLUK KONTROLLERİ
        hoca_anahtar = f"{su_anki_ders['hoca_id']}_{ders_atama['gun']}"
        hoca_gunluk_ders_sayisi[hoca_anahtar] = hoca_gunluk_ders_sayisi.get(hoca_anahtar, 0) + 1
        esnek_ceza_carpani = 50 if hedef_strateji == "Hoca Konforu Maksimum" else 5
        if hoca_gunluk_ders_sayisi[hoca_anahtar] > 2: ceza += esnek_ceza_carpani

        # --- YENİ: ÖĞRENCİ BOŞLUK (PENCERE) TAKİBİ ---
        seviye = str(su_anki_ders.get("sinif_seviyesi", ""))
        if seviye and seviye != "nan":
            ogr_anahtar = f"{seviye}_{ders_atama['gun']}"
            if ogr_anahtar not in sinif_gunluk_saatler: sinif_gunluk_saatler[ogr_anahtar] = []
            if ders_atama["saat"] in saat_indeksleri:
                sinif_gunluk_saatler[ogr_anahtar].append(saat_indeksleri[ders_atama["saat"]])
        hoca_aktif_gunler.setdefault(su_anki_ders['hoca_id'], set()).add(ders_atama['gun'])    
        atama_listesi.append(ders_atama)
        
    # --- YENİ: ŞEHİR DIŞI HOCA KORUMASI (TEK GÜNE SIKIŞTIRMA) ---
    for h_id, gunler_seti in hoca_aktif_gunler.items():
        hd = next((h for h in hocalar if h["id"] == h_id), None)
        if hd and hd.get("sehir_disi", False):
            if len(gunler_seti) > 1:
                ceza += (len(gunler_seti) - 1) * 300 # Farklı günlere yayılan her ders için DEVASA ceza        
    # --- YENİ: ÖĞRENCİ BOŞLUK CEZASI UYGULAMASI ---
    for k, saatler_listesi in sinif_gunluk_saatler.items():
        if len(saatler_listesi) > 1:
            fark = max(saatler_listesi) - min(saatler_listesi)
            bosluk = fark - (len(saatler_listesi) - 1)
            if bosluk > 1: # 1 saat boşluk normal, fazlası ceza
                ceza += bosluk * 15 
                
    return (ceza,)

toolbox.register("evaluate", degerlendir)
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)

def evrimi_baslat(nesil_sayisi=100, progress_bar=None):
    random.seed(42) 
    pop = toolbox.population(n=100)
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses): ind.fitness.values = fit
    gecmis = []

    for g in range(nesil_sayisi):
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < 0.7:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        for mutant in offspring:
            if random.random() < 0.2:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses): ind.fitness.values = fit

        pop[:] = offspring
        if progress_bar: progress_bar.progress((g + 1) / nesil_sayisi)
        en_iyi_anlik = tools.selBest(pop, 1)[0]
        gecmis.append(en_iyi_anlik.fitness.values[0])
        
    if progress_bar: progress_bar.progress(1.0)
    return tools.selBest(pop, 1)[0], gecmis