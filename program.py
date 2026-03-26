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
            if not dfs:
                raise FileNotFoundError("Nem található egyik megadott Excel sem.")
            self.df = pd.concat(dfs, ignore_index=True)

            # Tisztítás és kereséshez előkészítés: a fájlnév és az elérési út egyaránt kereshető
            self.df['Címkék'] = self.df['Címkék'].fillna("").astype(str)
            self.df['Fájlnév'] = self.df['Fájlnév'].fillna("").astype(str)
            self.df['Elérési út'] = self.df['Elérési út'].fillna("").astype(str)
            self.df['search_tags'] = self.df['Címkék'].apply(ekezet_mentesites)
            self.df['search_name'] = (self.df['Fájlnév'] + ' ' + self.df['Elérési út']).apply(ekezet_mentesites)
        except Exception as e:
            print(f"Hiba az Excel beolvasásakor: {e}")

# --- Megjelenés beállítása - ELRENDEZÉS ---

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
        kedvencek = ["2023", "2024", "2025", "GTK", "MIK", 
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
        self.entry = ctk.CTkEntry(search_frame, placeholder_text="Keress címke vagy név alapján...", height=40, corner_radius=30)
        self.entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
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
                file_icon_path = os.path.join('icons', 'word.png')
                path_icon_path = os.path.join('icons', 'location.png')
                if os.path.exists(file_icon_path):
                    self.icon_file_img = ctk.CTkImage(PILImage.open(file_icon_path), size=(16, 16))
                if os.path.exists(path_icon_path):
                    self.icon_path_img = ctk.CTkImage(PILImage.open(path_icon_path), size=(16, 16))
            except Exception as e:
                print(f"Ikon betöltési hiba: {e}")

    def valts_megjelenest(self):
        if self.appearance_mode_switch.get() == 1:
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def gyors_kereses(self, szo):
        self.entry.delete(0, "end")
        self.entry.insert(0, szo)
        self.kereses()

    def kereses(self):
        for widget in self.results_list.winfo_children():
            widget.destroy()

        nyers_bevitel = self.entry.get().strip()
        if not nyers_bevitel: return

        tiszta_bevitel = ekezet_mentesites(nyers_bevitel)
        keresett_szavak = [szo for szo in tiszta_bevitel.split() if len(szo) >= 2]
        
        talalati_lista = []

        for index, sor in self.df.iterrows():
            # Keressünk mind a címkékben, mind a fájlnévben
            szoveg_amiben_keresunk = f"{sor.get('search_tags','')} {sor.get('search_name','') }"
            
            pontszam = 0
            kizaro_ok = False
            megtalalt_fontos_szo = False # Ez figyeli, hogy a lényeg megvan-e

            for szo in keresett_szavak:
                # 1. SZÁMOK (Évszámok) - Szigorú marad
                szamok = "".join(filter(str.isdigit, szo))
                if len(szamok) >= 3:
                    if szamok in szoveg_amiben_keresunk:
                        pontszam += 500
                        megtalalt_fontos_szo = True
                    else:
                        kizaro_ok = True
                        break
                
                # 2. SZAVAK (pl. labor, hajo)
                else:
                    # Szóhatár teszt: teljes szó egyezés vagy legalább az első 4 karakter egyezése
                    if re.search(r"\b" + re.escape(szo) + r"\b", szoveg_amiben_keresunk) or szo[:4] in szoveg_amiben_keresunk:
                        pontszam += 100
                        megtalalt_fontos_szo = True
                    else:
                        # Ha nem találja meg pontosan, de a Fuzzy nagyon erős (>90)
                        # akkor kap egy kevés pontot, de nem jelöljük "fontos találatnak"
                        p_fuzzy = fuzz.partial_ratio(szo, szoveg_amiben_keresunk)
                        if p_fuzzy > 90:
                            pontszam += p_fuzzy / 2 # Csak fél súlyú pont

            # A LOGIKA: 
            # Ha nem volt rossz évszám ÉS legalább EGY fontos kulcsszót megtaláltunk
            if not kizaro_ok and megtalalt_fontos_szo:
                talalati_lista.append((pontszam, sor))

        # Rendezés a legmagasabb pontszám szerint
        talalati_lista.sort(key=lambda x: x[0], reverse=True)

        self.results_list.configure(label_text=f"Találatok ({len(talalati_lista)} db):")
        
        if not talalati_lista:
            ctk.CTkLabel(self.results_list, text="Nincs találat.").pack(pady=10)
        else:
            for pont, sor in talalati_lista[:100]:
                item = ctk.CTkFrame(self.results_list)
                item.pack(fill="x", pady=5, padx=5)
                fajlnev = str(sor.get('Fájlnév', '')).strip()
                eleresi_ut = str(sor.get('Elérési út', '')).strip()
                if fajlnev:
                    display_name = fajlnev
                else:
                    # Ha nincs fájlnév, használjuk az elérési út utolsó elemét (mappa vagy fájlnév)
                    display_name = os.path.basename(eleresi_ut.rstrip('/\\')) or eleresi_ut or '(nincs fájlnév)'

                # Ha van betöltött ikon, használjunk külön label-eket (ikon + szöveg), különben fallback emoji
                if self.icon_file_img:
                    # Use grid inside the item to align icon and text rows neatly
                    icon_lbl = ctk.CTkLabel(item, image=self.icon_file_img, text="")
                    icon_lbl.grid(row=0, column=0, rowspan=2, padx=(10,8), pady=8, sticky='n')

                    # Title (bold)
                    title_lbl = ctk.CTkLabel(item, text=display_name, justify="left", font=("Arial", 12, "bold"))
                    title_lbl.grid(row=0, column=1, sticky='w', padx=(0,6), pady=(8,0))

                    # Path row with optional small icon
                    if self.icon_path_img:
                        path_icon_lbl = ctk.CTkLabel(item, image=self.icon_path_img, text="")
                        path_icon_lbl.grid(row=1, column=1, sticky='w', padx=(0,6), pady=(0,8))
                        path_lbl = ctk.CTkLabel(item, text=eleresi_ut, justify="left")
                        path_lbl.grid(row=1, column=1, sticky='w', padx=(22,0), pady=(0,8))
                    else:
                        path_lbl = ctk.CTkLabel(item, text=eleresi_ut, justify="left")
                        path_lbl.grid(row=1, column=1, sticky='w', padx=(0,6), pady=(0,8))

                    item.grid_columnconfigure(1, weight=1)
                else:
                    info = f"📄 {display_name}\n📍 {eleresi_ut}"
                    ctk.CTkLabel(item, text=info, justify="left", wraplength=700).pack(side="left", padx=10, pady=5)

if __name__ == "__main__":
    app = MediaKeresoApp()
    app.mainloop()