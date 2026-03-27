import customtkinter as ctk
import pandas as pd
import unicodedata
import re
import os
from thefuzz import fuzz

# Pillow opcionális használata ikonokhoz
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Ékezetmentesítés
def ekezet_mentesites(szoveg):
    if not isinstance(szoveg, str):
        return str(szoveg).lower()
    return "".join(c for c in unicodedata.normalize('NFD', szoveg)
                   if unicodedata.category(c) != 'Mn').lower()

# Felület
class MediaKeresoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Egyetemi Médiatár - Kereső Szoftver")
        self.geometry("1100x700")
        
        ctk.set_appearance_mode("dark")

        #keresesi allapotok
        self.search_job = None
        self.osszes_talalat = []  # Itt tároljuk a teljes listát
        self.aktualis_limit = 30  # Ennyit mutatunk egyszerre

        self.df = pd.DataFrame(columns=['Címkék', 'Fájlnév', 'Elérési út', 'search_tags', 'search_name'])

        # Adatok betöltése
        # Betöltés több forrásból: videokereso.xlsx és kepkereso.xlsx
        try:
            files = ["videokereso.xlsx", "kepkereso.xlsx"]
            dfs = []
            for f in files:
                if os.path.exists(f):
                    df = pd.read_excel(f)
                    # Egyszerű átnevezések ha angol/osztott mezőnevek vannak
                    if 'Tags' in df.columns and 'Címkék' not in df.columns:
                        df = df.rename(columns={'Tags': 'Címkék'})
                    if 'Folder' in df.columns and 'Elérési út' not in df.columns:
                        df = df.rename(columns={'Folder': 'Elérési út'})
                    if 'Mappa' in df.columns and 'Elérési út' not in df.columns:
                        df = df.rename(columns={'Mappa': 'Elérési út'})
                    # Biztosítsuk a közös sémát
                    if 'Címkék' not in df.columns:
                        df['Címkék'] = ''
                    if 'Fájlnév' not in df.columns:
                        df['Fájlnév'] = ''
                    if 'Elérési út' not in df.columns:
                        df['Elérési út'] = ''
                    dfs.append(df)
            if dfs:
                self.df = pd.concat(dfs, ignore_index=True)
                self.df = self.df.fillna("")
                self.df['search_tags'] = self.df['Címkék'].astype(str).apply(ekezet_mentesites)
                self.df['search_name'] = (self.df['Fájlnév'].astype(str) + ' ' + self.df['Elérési út'].astype(str)).apply(ekezet_mentesites)
                print(f"Sikeres betöltés: {len(self.df)} sor.")
            else:
                print("Figyelem: Nem található Excel fájl.")
        except Exception as e:
            print(f"Hiba az Excel beolvasásakor: {e}")

        self.setup_ui()

# --- Megjelenés beállítása - ELRENDEZÉS ---
    def setup_ui(self):
                # --- ELRENDEZÉS: SIDEBAR ---
        self.sidebar_container = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="transparent")
        self.sidebar_container.pack(side="left", fill="y", padx=(20, 0), pady=20)

        # 1. A KAPCSOLÓ (Most már legfelülre kerül)
        self.appearance_mode_switch = ctk.CTkSwitch(
            self.sidebar_container, 
            text="Sötét mód", 
            command=self.valts_megjelenest
        )
        self.appearance_mode_switch.pack(side="top", pady=(10, 20), padx=20)
        self.appearance_mode_switch.select()

        # 2. A CÍM (A kapcsoló alá)
        ctk.CTkLabel(self.sidebar_container, text="KATEGÓRIÁK", font=("Arial", 16, "bold")).pack(pady=(0, 10))

        # 3. Kategória gombok (A cím alá)
        kedvencek = ["2023", "2024", "2025", "2026", "GTK", "MIK", 
                     "MK", "HTK", "GKZ", "Hajo", "Aula", 
                     "Konferencia", "Balaton", "Sport"]
        for szo in kedvencek:
            ctk.CTkButton(self.sidebar_container, 
                          text=szo, 
                          border_width=1, 
                          command=lambda s=szo: self.gyors_kereses(s)).pack(pady=5, padx=10, fill="x"
                        )

        # 4. JOBB oldali oszlop
        # Cím
        self.main_label = ctk.CTkLabel(self, text="Média Kereső", font=("Arial", 24, "bold"))
        self.main_label.pack(pady=20)

        # Kereső keret
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(pady=10, padx=20, fill="x")

        # Jobb oldali oszlop, MAIN
        self.entry = ctk.CTkEntry(search_frame, placeholder_text="Keress címke vagy kulcsszavak alapján...", height=40, corner_radius=30)
        self.entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        #gépelés közbeni keresés
        self.entry.bind("<KeyRelease>", self.kesleltetett_kereses) # Minden billentyűleütés után indítson egy új késleltetett keresést
        self.entry.bind("<Return>", lambda e: self.kereses()) # Enterre is keressen

        self.btn = ctk.CTkButton(search_frame, text="Keresés", command=self.kereses, width=100, height=40,  corner_radius=30)
        self.btn.pack(side="right", padx=10, pady=10)

        # Eredmények listája (Scrollable Frame)
        self.results_list = ctk.CTkScrollableFrame(self, label_text="Találatok")
        self.results_list.pack(pady=20, padx=20, fill="both", expand=True)

        # Ikonok betöltése (ha elérhető a Pillow és vannak ikonok a icons/ mappában)
        self.icon_file_img = None
        self.icon_path_img = None
        if PIL_AVAILABLE:
            try:
                if os.path.exists('icons/word.png'):
                    self.icon_file_img = ctk.CTkImage(PILImage.open('icons/word.png'), size=(16, 16))
                if os.path.exists('icons/location.png'):
                    self.icon_path_img = ctk.CTkImage(PILImage.open('icons/location.png'), size=(16, 16))
            except Exception as e:
                print(f"Ikon hiba: {e}")

    def valts_megjelenest(self):
        if self.appearance_mode_switch.get() == 1:
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def gyors_kereses(self, szo):
        self.entry.delete(0, "end")
        self.entry.insert(0, szo)
        self.kereses()

    def kesleltetett_kereses(self, event):
        if self.search_job:
            self.after_cancel(self.search_job)
        # 300ms várakozás az utolsó leütés után
        self.search_job = self.after(300, self.kereses)

    def kereses(self):
        nyers_bevitel = self.entry.get().strip()
        if not nyers_bevitel:
            self.osszes_talalat = []
            self.megjelenites_frissitese()
            return

        tiszta_bevitel = ekezet_mentesites(nyers_bevitel)
        keresett_szavak = [szo for szo in tiszta_bevitel.split() if len(szo) >= 2]
        
        if not keresett_szavak: return

        talalati_lista = []
        for index, sor in self.df.iterrows():
            # Keressünk mind a címkékben, mind a fájlnévben
            szoveg_amiben_keresunk = f"{sor.get('search_tags','')} {sor.get('search_name','') }"
            pontszam = 0
            kizaro_ok = False
            megtalalt_fontos_szo = False # Ez figyeli, hogy a lényeg megvan-e

            # 1. SZÁMOK (Évszámok) - Szigorú marad
            for szo in keresett_szavak:
                if szo.isdigit() and len(szo) >= 3:
                    if szo in szoveg_amiben_keresunk:
                        pontszam += 500
                        megtalalt_fontos_szo = True
                    else:
                        kizaro_ok = True; break
                else:
                    if re.search(r"\b" + re.escape(szo) + r"\b", szoveg_amiben_keresunk) or szo[:4] in szoveg_amiben_keresunk:
                        pontszam += 100
                        megtalalt_fontos_szo = True
                    else:
                        p_fuzzy = fuzz.partial_ratio(szo, szoveg_amiben_keresunk)
                        if p_fuzzy > 85: pontszam += p_fuzzy / 2

            if not kizaro_ok and megtalalt_fontos_szo:
                talalati_lista.append((pontszam, sor))

        # Rendezés a legmagasabb pontszám szerint
        talalati_lista.sort(key=lambda x: x[0], reverse=True)
        # ELMENTJÜK az összeset és alaphelyzetbe állítjuk a limitet
        self.osszes_talalat = talalati_lista
        self.aktualis_limit = 30
        self.megjelenites_frissitese()

        #self.results_list.configure(label_text=f"Találatok ({len(talalati_lista)} db):")

    def megjelenites_frissitese(self):
        # Töröljük a régi listát
        for widget in self.results_list.winfo_children():
            widget.destroy()

        # Csak a limitig jelenítünk meg
        megjelenitett = self.osszes_talalat[:self.aktualis_limit]
        self.results_list.configure(label_text=f"Találatok ({len(self.osszes_talalat)} db, ebből {len(megjelenitett)} látható):")

        if not self.osszes_talalat:
            ctk.CTkLabel(self.results_list, text="Nincs találat.").pack(pady=10)
            return

        for pont, sor in megjelenitett:
            item = ctk.CTkFrame(self.results_list)
            item.pack(fill="x", pady=5, padx=5)
            
            fajlnev = str(sor.get('Fájlnév', '')).strip()
            eleresi_ut = str(sor.get('Elérési út', '')).strip()
            display_name = fajlnev if fajlnev else (os.path.basename(eleresi_ut.rstrip('/\\')) or eleresi_ut)

            if self.icon_file_img:
                ctk.CTkLabel(item, image=self.icon_file_img, text="").grid(row=0, column=0, rowspan=2, padx=(10,8), pady=8, sticky='n')
                ctk.CTkLabel(item, text=display_name, font=("Arial", 12, "bold")).grid(row=0, column=1, sticky='w', pady=(8,0))
                if self.icon_path_img:
                    ctk.CTkLabel(item, image=self.icon_path_img, text="").grid(row=1, column=1, sticky='w')
                    ctk.CTkLabel(item, text=eleresi_ut).grid(row=1, column=1, sticky='w', padx=(22,0), pady=(0,8))
                else:
                    ctk.CTkLabel(item, text=eleresi_ut).grid(row=1, column=1, sticky='w', pady=(0,8))
                item.grid_columnconfigure(1, weight=1)
            else:
                ctk.CTkLabel(item, text=f"📄 {display_name}\n📍 {eleresi_ut}", justify="left").pack(side="left", padx=10, pady=5)

        if len(self.osszes_talalat) > self.aktualis_limit:
            ctk.CTkButton(self.results_list, text="További találatok betöltése...", command=self.tobb_betoltese, fg_color="transparent", border_width=1).pack(pady=15)
    
    def tobb_betoltese(self):
        """Növeli a látható találatok számát és frissíti a listát."""
        self.aktualis_limit += 30
        self.megjelenites_frissitese()

if __name__ == "__main__":
    app = MediaKeresoApp()
    app.mainloop()