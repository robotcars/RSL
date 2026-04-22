"""
Analizador de Resultados de Busqueda de Articulos
Analiza archivos CSV exportados de IEEE, Science Direct y ACM Digital,
identifica DOIs repetidos y unicos, y permite exportar los resultados.

Funciones nuevas respecto a la version anterior:
  - Acumulado de DOIs: seccion que registra todos los DOIs unicos que van
    apareciendo en cada analisis sin borrar los anteriores entre ejecuciones.
  - Historial de busquedas DOI: lista desplegable con las ultimas consultas.
  - Copiar resultado al portapapeles: boton en el buscador DOI.
  - Eliminar archivo individual: clic derecho sobre un archivo en la lista.
  - Barra de estado: franja inferior que muestra la ultima accion realizada.
  - Exportar acumulado: boton independiente para guardar el acumulado de sesion.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv as cs
import os
import re
from collections import defaultdict
import bibtexparser

# ---------------------------------------------------------------------------
# Paleta de colores y fuentes
# ---------------------------------------------------------------------------
BG        = "#F5F7FA"
CARD      = "#FFFFFF"
ACCENT    = "#3B82F6"
ACCENT2   = "#1D4ED8"
SUCCESS   = "#10B981"
WARN      = "#F59E0B"
TEXT      = "#1E293B"
MUTED     = "#64748B"
BORDER    = "#E2E8F0"
BADGE_BG  = "#EFF6FF"
BADGE_FG  = "#1D4ED8"
PURPLE    = "#7C3AED"
STATUS_BG = "#1E293B"

FT  = ("Segoe UI", 13, "bold")
FLB = ("Segoe UI", 10, "bold")
FS  = ("Segoe UI", 9)
FM  = ("Consolas", 9)


# ---------------------------------------------------------------------------
# Helpers de widgets
# ---------------------------------------------------------------------------

def make_btn(parent, text, cmd, bg=ACCENT, fg="white", **kw):
    """Boton plano con cursor de mano."""
    return tk.Button(
        parent, text=text, command=cmd, bg=bg, fg=fg,
        relief=tk.FLAT, font=FLB, cursor="hand2",
        padx=12, pady=5,
        activebackground=ACCENT2, activeforeground="white", **kw)


def make_sep(parent, row, padx=16, pady=3):
    ttk.Separator(parent, orient="horizontal").grid(
        row=row, column=0, sticky="ew", padx=padx, pady=pady)


def make_card(parent, row, pady=(4, 4), padx=16):
    """Frame con borde suave que simula una tarjeta."""
    f = tk.Frame(parent, bg=CARD,
                 highlightthickness=1, highlightbackground=BORDER)
    f.grid(row=row, column=0, sticky="ew", padx=padx, pady=pady)
    return f


def make_scrolled_text(parent, height, **kw):
    """
    Text widget con scrollbar vertical.
    Devuelve (frame_contenedor, widget_text).
    El frame debe ser posicionado por el llamador.
    """
    frame = tk.Frame(parent, bg=kw.get("bg", CARD))
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    txt = tk.Text(frame, height=height, relief=tk.FLAT, bd=0,
                  wrap="word", padx=10, pady=8, **kw)
    sb  = tk.Scrollbar(frame, orient="vertical", command=txt.yview)
    txt.configure(yscrollcommand=sb.set)
    txt.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")
    return frame, txt


# ---------------------------------------------------------------------------
# Aplicacion principal
# ---------------------------------------------------------------------------

class AnalizadorApp:

    # ------------------------------------------------------------------ init
    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title("Analizador de Resultados de Busqueda")
        self.ventana.configure(bg=BG)

        w, h = 980, 920
        sw = self.ventana.winfo_screenwidth()
        sh = self.ventana.winfo_screenheight()
        self.ventana.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.ventana.resizable(True, True)
        self.ventana.grid_columnconfigure(0, weight=1)
        # filas que expanden verticalmente
        self.ventana.grid_rowconfigure(8,  weight=2)   # resultados analisis
        self.ventana.grid_rowconfigure(11, weight=1)   # acumulado DOIs

        # ---- estado interno ------------------------------------------------
        self.archivoRuta    = []   # rutas de archivos cargados
        self.doi_repetidos  = {}   # {doi: {titulos, archivos}}
        self.doi_unicos     = {}   # {doi: {titulo, archivo}}
        self.acumulado_dois = {}   # {doi: {titulo, archivo}} acumulado sesion
        self._n_busq_doi    = 0    # contador de busquedas DOI
        self._historial_doi = []   # terminos buscados (max 20)

        # ---- construccion de secciones ------------------------------------
        self._build_header()
        self._build_archivos()
        self._build_analizar()
        self._build_buscador_doi()
        self._build_resultados()
        self._build_acumulado()
        self._build_exportar()
        self._build_statusbar()

    # ================================================================== BUILD

    def _build_header(self):
        hdr = tk.Frame(self.ventana, bg=ACCENT)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        tk.Label(
            hdr,
            text="  Analizador de Resultados de Busqueda de Articulos",
            font=("Segoe UI", 13, "bold"), fg="white", bg=ACCENT,
            anchor="w", pady=10
        ).grid(row=0, column=0, sticky="ew", padx=12)

    def _build_archivos(self):
        ca = make_card(self.ventana, row=1, pady=(12, 4))
        ca.grid_columnconfigure(1, weight=1)

        tk.Label(ca, text="Archivos CSV", font=FT,
                 bg=CARD, fg=TEXT).grid(
            row=0, column=0, columnspan=4,
            sticky="w", padx=14, pady=(10, 4))

        self.btnSelec = make_btn(ca, "Agregar CSV", self.seleccionArchivo)
        self.btnSelec.grid(row=1, column=0, padx=(14, 6), pady=6, sticky="w")

        self.btnRIS = make_btn(ca, "Convertir RIS a CSV",
                               self.convertidorRI, bg="#6366F1")
        self.btnRIS.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        self.btnBIB = make_btn(ca, "Convertir BIB a CSV",
                               self.convertidorBIB, bg="#8B5CF6")
        self.btnBIB.grid(row=1, column=2, padx=6, pady=6, sticky="w")

        make_btn(ca, "Limpiar todo", self.limpiarSeleccion,
                 bg="#94A3B8", fg=TEXT).grid(
            row=1, column=3, padx=(6, 14), pady=6, sticky="e")

        self.lblArchivos = tk.Label(
            ca, text="Sin archivos seleccionados",
            font=FS, bg=CARD, fg=MUTED, anchor="w")
        self.lblArchivos.grid(row=2, column=0, columnspan=4,
                              sticky="ew", padx=14, pady=(0, 2))

        # listbox con scrollbar
        fl = tk.Frame(ca, bg=CARD)
        fl.grid(row=3, column=0, columnspan=4,
                sticky="ew", padx=14, pady=(0, 4))
        fl.grid_columnconfigure(0, weight=1)

        self.listaArchivos = tk.Listbox(
            fl, height=3, bg="#F8FAFC", fg=TEXT, font=FS,
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=BORDER,
            selectbackground=ACCENT, selectforeground="white", bd=0)
        self.listaArchivos.grid(row=0, column=0, sticky="ew")
        sb = tk.Scrollbar(fl, orient="vertical",
                          command=self.listaArchivos.yview)
        self.listaArchivos.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")

        tk.Label(ca,
                 text="Clic derecho sobre un archivo para eliminarlo de la lista.",
                 font=FS, bg=CARD, fg=MUTED).grid(
            row=4, column=0, columnspan=4,
            sticky="w", padx=14, pady=(0, 8))

        # menu contextual para eliminar archivo individual
        self._menu_arch = tk.Menu(self.ventana, tearoff=0)
        self._menu_arch.add_command(
            label="Eliminar archivo seleccionado",
            command=self._eliminar_archivo_seleccionado)
        self.listaArchivos.bind(
            "<Button-3>",
            lambda e: self._mostrar_menu_arch(e))

    def _build_analizar(self):
        make_sep(self.ventana, 2)
        bf = tk.Frame(self.ventana, bg=BG)
        bf.grid(row=3, column=0, sticky="ew", padx=16, pady=6)
        bf.grid_columnconfigure(0, weight=1)

        make_btn(bf, "Analizar archivos", self.Buscador,
            bg=SUCCESS).grid(row=0, column=0, sticky="ew")
        tk.Label(
            bf,
            text="El formato se detecta automaticamente"
                 "  (IEEE  /  Science Direct  /  ACM Digital)",
            font=FS, bg=BG, fg=MUTED
        ).grid(row=1, column=0, pady=(2, 0))

    def _build_buscador_doi(self):
        make_sep(self.ventana, 4)
        cd = make_card(self.ventana, row=5, pady=(4, 4))
        cd.grid_columnconfigure(1, weight=1)

        # titulo + badge contador
        th = tk.Frame(cd, bg=CARD)
        th.grid(row=0, column=0, columnspan=4,
                sticky="ew", padx=14, pady=(10, 6))
        tk.Label(th, text="Buscar DOI especifico",
                 font=FT, bg=CARD, fg=TEXT).pack(side="left")
        self.badge = tk.Label(
            th, text="  0 busquedas  ", font=FS,
            bg=BADGE_BG, fg=BADGE_FG, padx=6, pady=2)
        self.badge.pack(side="left", padx=(10, 0))

        # entrada con historial desplegable
        tk.Label(cd, text="DOI:", font=FLB,
                 bg=CARD, fg=TEXT).grid(
            row=1, column=0, padx=(14, 6), pady=6, sticky="w")
        self.entradaDoi = ttk.Combobox(cd, font=FM, values=[])
        self.entradaDoi.grid(row=1, column=1, padx=6, pady=6,
                             sticky="ew", ipady=4)
        self.entradaDoi.bind('<Return>', lambda _: self.buscarDoiEspecifico())

        make_btn(cd, "Buscar", self.buscarDoiEspecifico).grid(
            row=1, column=2, padx=6, pady=6, sticky="e")

        self.btnCopiarDoi = make_btn(
            cd, "Copiar resultado", self._copiar_resultado_doi,
            bg="#64748B")
        self.btnCopiarDoi.grid(
            row=1, column=3, padx=(0, 14), pady=6, sticky="e")
        self.btnCopiarDoi.config(state=tk.DISABLED)

        # panel resultado con color dinamico
        self.panelDoi = tk.Frame(
            cd, bg="#F8FAFC",
            highlightthickness=1, highlightbackground=BORDER)
        self.panelDoi.grid(row=2, column=0, columnspan=4,
                           sticky="ew", padx=14, pady=(0, 10))
        self.panelDoi.grid_columnconfigure(0, weight=1)

        fr_doi, self.txtDoi = make_scrolled_text(
            self.panelDoi, height=5, font=FM, bg="#F8FAFC", fg=TEXT)
        fr_doi.grid(row=0, column=0, sticky="ew")
        self.txtDoi.config(state=tk.DISABLED)

    def _build_resultados(self):
        make_sep(self.ventana, 6)

        rh = tk.Frame(self.ventana, bg=BG)
        rh.grid(row=7, column=0, sticky="ew", padx=16, pady=(4, 0))
        rh.grid_columnconfigure(0, weight=1)
        tk.Label(rh, text="Resultados del analisis",
                 font=FT, bg=BG, fg=TEXT).pack(side="left")
        self.lblStats = tk.Label(rh, text="", font=FS, bg=BG, fg=MUTED)
        self.lblStats.pack(side="right")

        cr = make_card(self.ventana, row=8, pady=(4, 4))
        cr.grid_columnconfigure(0, weight=1)
        cr.grid_rowconfigure(0, weight=1)

        fr_res, self.resultadosTexto = make_scrolled_text(
            cr, height=14, font=FM, bg=CARD, fg=TEXT)
        fr_res.grid(row=0, column=0, sticky="nsew")
        self.resultadosTexto.config(state=tk.DISABLED)

        T = self.resultadosTexto
        T.tag_config("sec",  font=("Segoe UI", 10, "bold"), foreground=ACCENT)
        T.tag_config("doi",  foreground=PURPLE, font=FM)
        T.tag_config("tit",  foreground=TEXT)
        T.tag_config("arc",  foreground=MUTED, font=FS)
        T.tag_config("warn", foreground=WARN,
                     font=("Segoe UI", 9, "bold"))
        T.tag_config("num",  foreground=ACCENT2,
                     font=("Segoe UI", 9, "bold"))

    def _build_acumulado(self):
        """
        Seccion que muestra todos los DOIs unicos encontrados durante
        la sesion, acumulando cada nuevo analisis sin borrar los anteriores.
        """
        make_sep(self.ventana, 9)

        ah = tk.Frame(self.ventana, bg=BG)
        ah.grid(row=10, column=0, sticky="ew", padx=16, pady=(4, 0))
        ah.grid_columnconfigure(0, weight=1)
        tk.Label(ah, text="Acumulado de DOIs unicos en la sesion",
                 font=FT, bg=BG, fg=TEXT).pack(side="left")
        self.lblAcumStats = tk.Label(
            ah, text="0 DOIs", font=FS, bg=BG, fg=MUTED)
        self.lblAcumStats.pack(side="right")
        make_btn(ah, "Limpiar acumulado", self._limpiar_acumulado,
                 bg="#94A3B8", fg=TEXT).pack(
            side="right", padx=(0, 12))

        ca = make_card(self.ventana, row=11, pady=(4, 4))
        ca.grid_columnconfigure(0, weight=1)
        ca.grid_rowconfigure(0, weight=1)

        fr_ac, self.txtAcumulado = make_scrolled_text(
            ca, height=8, font=FM, bg=CARD, fg=TEXT)
        fr_ac.grid(row=0, column=0, sticky="nsew")
        self.txtAcumulado.config(state=tk.DISABLED)

        A = self.txtAcumulado
        A.tag_config("doi",  foreground=PURPLE, font=FM)
        A.tag_config("tit",  foreground=TEXT)
        A.tag_config("arc",  foreground=MUTED, font=FS)
        A.tag_config("num",  foreground=ACCENT2,
                     font=("Segoe UI", 9, "bold"))
        A.tag_config("new",  foreground=SUCCESS,
                     font=("Segoe UI", 9, "bold"))

    def _build_exportar(self):
        make_sep(self.ventana, 12)
        ef = tk.Frame(self.ventana, bg=BG)
        ef.grid(row=13, column=0, sticky="ew", padx=16, pady=(4, 12))
        ef.grid_columnconfigure(0, weight=1)
        ef.grid_columnconfigure(1, weight=1)

        self.btnExportar = make_btn(
            ef, "Exportar resultados del analisis",
            self.exportarResultados, bg="#0F172A")
        self.btnExportar.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btnExportar.config(state=tk.DISABLED)

        self.btnExportarAcum = make_btn(
            ef, "Exportar acumulado de DOIs",
            self._exportar_acumulado, bg="#334155")
        self.btnExportarAcum.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.btnExportarAcum.config(state=tk.DISABLED)

    def _build_statusbar(self):
        self.statusbar = tk.Label(
            self.ventana, text="Listo.",
            font=FS, bg=STATUS_BG, fg="#94A3B8",
            anchor="w", padx=12, pady=4)
        self.statusbar.grid(row=14, column=0, sticky="ew")

    # ================================================================== ESTADO

    def _set_status(self, msg):
        self.statusbar.config(text=msg)

    def _doi_color(self, modo):
        paleta = {
            "ok":    ("#F0FDF4", "#BBF7D0"),
            "warn":  ("#FFFBEB", "#FDE68A"),
            "empty": ("#F8FAFC", BORDER),
        }
        bg, br = paleta.get(modo, paleta["empty"])
        self.panelDoi.config(bg=bg, highlightbackground=br)
        self.txtDoi.config(bg=bg)

    def _upd_badge(self):
        n = self._n_busq_doi
        self.badge.config(
            text=f"  {n} busqueda{'s' if n != 1 else ''}  ")

    # ================================================================== ARCHIVOS

    def seleccionArchivo(self, _=None):
        ruta = filedialog.askopenfilename(
            title="Seleccionar CSV",
            filetypes=[("CSV", "*.csv")],
            initialdir=".")
        if ruta and ruta not in self.archivoRuta:
            self.archivoRuta.append(ruta)
            self._upd_lista()
            self._bloquear("CSV")
            self._set_status(f"Archivo agregado: {os.path.basename(ruta)}")

    def limpiarSeleccion(self):
        self.archivoRuta = []
        self._upd_lista()
        for b in (self.btnRIS, self.btnBIB, self.btnSelec):
            b.config(state=tk.NORMAL)
        for txt in (self.resultadosTexto, self.txtDoi):
            txt.config(state=tk.NORMAL)
            txt.delete(1.0, tk.END)
            txt.config(state=tk.DISABLED)
        self.btnExportar.config(state=tk.DISABLED)
        self.lblStats.config(text="")
        self.entradaDoi.set("")
        self._n_busq_doi = 0
        self._upd_badge()
        self._doi_color("empty")
        self.btnCopiarDoi.config(state=tk.DISABLED)
        self._set_status("Seleccion limpiada.")

    def _upd_lista(self):
        self.listaArchivos.delete(0, tk.END)
        n = len(self.archivoRuta)
        if n == 0:
            self.lblArchivos.config(
                text="Sin archivos seleccionados", fg=MUTED)
        else:
            self.lblArchivos.config(
                text=(f"{n} archivo{'s' if n != 1 else ''} "
                      f"seleccionado{'s' if n != 1 else ''}"),
                fg=SUCCESS)
        for r in self.archivoRuta:
            self.listaArchivos.insert(tk.END, f"  {os.path.basename(r)}")

    def _mostrar_menu_arch(self, event):
        idx = self.listaArchivos.nearest(event.y)
        if idx >= 0:
            self.listaArchivos.selection_clear(0, tk.END)
            self.listaArchivos.selection_set(idx)
            self._menu_arch.post(event.x_root, event.y_root)

    def _eliminar_archivo_seleccionado(self):
        sel = self.listaArchivos.curselection()
        if not sel:
            return
        idx    = sel[0]
        nombre = os.path.basename(self.archivoRuta[idx])
        del self.archivoRuta[idx]
        self._upd_lista()
        if not self.archivoRuta:
            self.btnRIS.config(state=tk.NORMAL)
            self.btnBIB.config(state=tk.NORMAL)
        self._set_status(f"Archivo eliminado: {nombre}")

    # ================================================================== CONVERTIDORES

    def convertidorRI(self):
        f = filedialog.askopenfilename(
            title="Seleccionar RIS",
            filetypes=[("RIS", "*.ris")],
            initialdir=".")
        if not f:
            return
        nombre = os.path.basename(f)
        with open(f, 'r', encoding='utf-8') as ar:
            leer = ar.read()
        registros = re.split(r'\n(?=TY\s+-)', leer)
        referencias, todoCam = [], set()
        for registro in registros:
            if not registro.strip():
                continue
            ref = defaultdict(list)
            campo_actual = None
            for linea in registro.strip().split('\n'):
                m = re.match(r'^([A-Z0-9]{2})\s+-\s+(.+)$', linea)
                if m:
                    campo_actual, valor = m.groups()
                    ref[campo_actual].append(valor)
                    todoCam.add(campo_actual)
                elif campo_actual and linea.strip():
                    ref[campo_actual][-1] += ' ' + linea.strip()
            if ref:
                referencias.append(ref)
        ordenCampos = sorted(todoCam)
        csv_nombre  = f"{nombre[:-4]}.csv"
        csv_ruta    = os.path.join(os.path.dirname(f), csv_nombre)
        with open(csv_ruta, 'w', encoding='utf-8', newline='') as out:
            w = cs.DictWriter(out, fieldnames=ordenCampos)
            w.writeheader()
            for ref in referencias:
                w.writerow(
                    {c: ' ; '.join(ref.get(c, [])) for c in ordenCampos})
        self.archivoRuta = [csv_ruta]
        self._upd_lista()
        messagebox.showinfo("Conversion lista",
                            f"CSV creado:\n\n{csv_nombre}")
        self._bloquear("RIS")
        self._set_status(f"RIS convertido: {csv_nombre}")

    def convertidorBIB(self):
        f = filedialog.askopenfilename(
            title="Seleccionar BIB",
            filetypes=[("BIB", "*.bib")],
            initialdir=".")
        if not f:
            return
        nombre   = os.path.basename(f)
        csv_ruta = os.path.join(os.path.dirname(f),
                                f"{nombre[:-4]}.csv")
        with open(f, 'r', encoding='utf-8') as ar:
            bib = bibtexparser.load(ar)
        if not bib.entries:
            messagebox.showwarning("Archivo vacio",
                                   "No hay entradas en el BIB.")
            return
        todoCam = set()
        for e in bib.entries:
            todoCam.update(e.keys())
        campos = list(todoCam)
        orden  = []
        for fijo in ["ID", "ENTRYTYPE"]:
            if fijo in campos:
                orden.append(fijo)
                campos.remove(fijo)
        orden.extend(sorted(campos))
        with open(csv_ruta, 'w', encoding='utf-8', newline='') as out:
            w = cs.DictWriter(out, fieldnames=orden)
            w.writeheader()
            for e in bib.entries:
                w.writerow(e)
        self.archivoRuta = [csv_ruta]
        self._upd_lista()
        messagebox.showinfo("Conversion lista",
                            f"CSV creado:\n\n{nombre[:-4]}.csv")
        self._bloquear("BIB")
        self._set_status(f"BIB convertido: {nombre[:-4]}.csv")

    # ================================================================== ANALISIS

    def _detectar_motor(self, ruta):
        """Detecta el motor de busqueda por las cabeceras del CSV."""
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                campos = [c.strip().lower()
                          for c in (cs.DictReader(f).fieldnames or [])]
            if "document title" in campos or "publication title" in campos:
                return "IEEE"
            if ("entrytype" in campos
                    or ("abstract" in campos
                        and "title" in campos
                        and "doi" in campos)):
                return "ACM"
            if "ti" in campos or "t1" in campos or "source title" in campos:
                return "SD"
            return "IEEE"
        except Exception:
            return "IEEE"

    def Buscador(self):
        if not self.archivoRuta:
            messagebox.showwarning("Sin archivos",
                                   "Selecciona al menos un archivo CSV.")
            return
        motor = self._detectar_motor(self.archivoRuta[0])
        campos_titulo = {
            "IEEE": ["Document Title", "Title", "title"],
            "SD":   ["TI", "T1", "Title", "title"],
            "ACM":  ["title", "Title"],
        }.get(motor, ["title", "Title", "Document Title"])
        self._set_status(f"Analizando con perfil: {motor} ...")
        self._analizarMultiple(self.archivoRuta, campos_titulo)

    def _analizarMultiple(self, archivos, poCampos):
        self.doi_repetidos = {}
        self.doi_unicos    = {}
        agrupado = defaultdict(lambda: {"titulos": [], "archivos": []})

        for ruta in archivos:
            nombre = os.path.basename(ruta)
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    leer   = cs.DictReader(f)
                    campos = leer.fieldnames or []

                    campoDoi = next(
                        (c for c in campos if 'doi' in c.strip().lower()),
                        None)
                    if not campoDoi:
                        messagebox.showerror(
                            "Error", f"Sin campo DOI en:\n{nombre}")
                        continue

                    campoTit = None
                    for cand in poCampos:
                        campoTit = next(
                            (c for c in campos
                             if cand.lower() in c.strip().lower()),
                            None)
                        if campoTit:
                            break
                    if not campoTit:
                        campoTit = campos[0] if campos else None

                    for fila in leer:
                        doi = fila.get(campoDoi, '').strip()
                        tit = (fila.get(campoTit, '').strip()
                               if campoTit else 'Sin titulo')
                        if doi and doi.lower() not in \
                                ['', 'n/a', 'na', 'none', 'null']:
                            agrupado[doi]["titulos"].append(tit)
                            agrupado[doi]["archivos"].append(nombre)
            except Exception as e:
                messagebox.showerror(
                    "Error de lectura",
                    f"No se pudo leer {nombre}:\n{e}")

        for doi, d in agrupado.items():
            if len(d["titulos"]) > 1:
                self.doi_repetidos[doi] = d
            else:
                self.doi_unicos[doi] = {
                    "titulo":  d["titulos"][0],
                    "archivo": d["archivos"][0],
                }

        self._mostrarResultados()
        self._actualizar_acumulado()
        self.btnExportar.config(state=tk.NORMAL)
        self._set_status(
            f"Analisis completo: "
            f"{len(self.doi_unicos)} unicos, "
            f"{len(self.doi_repetidos)} repetidos.")

    # ================================================================== MOSTRAR

    def _mostrarResultados(self):
        T = self.resultadosTexto
        T.config(state=tk.NORMAL)
        T.delete(1.0, tk.END)

        if not self.doi_repetidos and not self.doi_unicos:
            T.insert(tk.END, "No se encontraron articulos.\n")
            T.config(state=tk.DISABLED)
            return

        total = len(self.doi_repetidos) + len(self.doi_unicos)
        self.lblStats.config(
            text=(f"{total} DOIs totales"
                  f"  /  {len(self.doi_repetidos)} repetidos"
                  f"  /  {len(self.doi_unicos)} unicos"))

        T.insert(tk.END,
                 f"DOIs REPETIDOS ({len(self.doi_repetidos)})\n", "sec")
        T.insert(tk.END, "-" * 64 + "\n")
        if not self.doi_repetidos:
            T.insert(tk.END, "  Ninguno\n\n")
        else:
            for doi, d in self.doi_repetidos.items():
                T.insert(tk.END, "  DOI: ", "arc")
                T.insert(tk.END, f"{doi}\n", "doi")
                T.insert(
                    tk.END,
                    f"  AVISO: aparece en {len(d['titulos'])} archivos:\n",
                    "warn")
                for t in d["titulos"]:
                    T.insert(tk.END, f"    - {t}\n", "tit")
                T.insert(tk.END, "\n")

        T.insert(tk.END,
                 f"DOIs UNICOS ({len(self.doi_unicos)})\n", "sec")
        T.insert(tk.END, "-" * 64 + "\n")
        if not self.doi_unicos:
            T.insert(tk.END, "  Ninguno\n")
        else:
            for i, (doi, d) in enumerate(self.doi_unicos.items(), 1):
                T.insert(tk.END, f"  {i:>4}. ", "num")
                T.insert(tk.END, f"{d['titulo']}\n", "tit")
                T.insert(tk.END, "         DOI: ", "arc")
                T.insert(tk.END, f"{doi}\n", "doi")
                T.insert(tk.END,
                         f"         Archivo: {d['archivo']}\n\n", "arc")

        T.config(state=tk.DISABLED)

    # ================================================================== ACUMULADO

    def _actualizar_acumulado(self):
        """
        Incorpora los DOIs unicos del analisis actual al acumulado
        de la sesion. Los que ya existen no se duplican.
        """
        nuevos = 0
        for doi, d in self.doi_unicos.items():
            if doi not in self.acumulado_dois:
                self.acumulado_dois[doi] = d
                nuevos += 1

        self._renderizar_acumulado(nuevos_dois=nuevos)

        total = len(self.acumulado_dois)
        self.lblAcumStats.config(
            text=(f"{total} DOI{'s' if total != 1 else ''}"
                  f"  (+{nuevos} nuevos en este analisis)"))
        if total > 0:
            self.btnExportarAcum.config(state=tk.NORMAL)

    def _renderizar_acumulado(self, nuevos_dois=0):
        A = self.txtAcumulado
        A.config(state=tk.NORMAL)
        A.delete(1.0, tk.END)

        if not self.acumulado_dois:
            A.insert(tk.END, "  Todavia no hay DOIs acumulados.\n")
            A.config(state=tk.DISABLED)
            return

        claves  = list(self.acumulado_dois.keys())
        umbral  = len(claves) - nuevos_dois   # indices >= umbral son nuevos

        for i, doi in enumerate(claves, 1):
            d       = self.acumulado_dois[doi]
            es_nuevo = (i - 1) >= umbral and nuevos_dois > 0

            A.insert(tk.END, f"  {i:>4}. ", "new" if es_nuevo else "num")
            if es_nuevo:
                A.insert(tk.END, "[NUEVO] ", "new")
            A.insert(tk.END, f"{d['titulo']}\n", "tit")
            A.insert(tk.END, "         DOI: ", "arc")
            A.insert(tk.END, f"{doi}\n", "doi")
            A.insert(tk.END,
                     f"         Archivo: {d['archivo']}\n\n", "arc")

        A.config(state=tk.DISABLED)

    def _limpiar_acumulado(self):
        self.acumulado_dois = {}
        self._renderizar_acumulado()
        self.lblAcumStats.config(text="0 DOIs")
        self.btnExportarAcum.config(state=tk.DISABLED)
        self._set_status("Acumulado de DOIs limpiado.")

    # ================================================================== BUSCADOR DOI

    def buscarDoiEspecifico(self):
        doi_q = self.entradaDoi.get().strip()
        if not doi_q:
            messagebox.showwarning("Campo vacio",
                                   "Introduce un DOI para buscar.")
            return
        if not self.archivoRuta:
            messagebox.showwarning("Sin archivos",
                                   "Selecciona archivos primero.")
            return

        doi_n      = doi_q.lower()
        resultados = []

        for ruta in self.archivoRuta:
            nombre = os.path.basename(ruta)
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    leer   = cs.DictReader(f)
                    campos = leer.fieldnames or []
                    campoDoi = next(
                        (c for c in campos if 'doi' in c.strip().lower()),
                        None)
                    if not campoDoi:
                        continue
                    campoTit = None
                    for posible in ["Title", "title", "Document Title",
                                    "TI", "T1"]:
                        campoTit = next(
                            (c for c in campos
                             if posible.lower() in c.lower()),
                            None)
                        if campoTit:
                            break
                    if not campoTit and campos:
                        campoTit = campos[0]
                    for fila in leer:
                        df = fila.get(campoDoi, '').strip().lower()
                        if df and df not in ['', 'n/a', 'na', 'none', 'null']:
                            if doi_n in df or df in doi_n:
                                resultados.append({
                                    "archivo": nombre,
                                    "doi":     fila.get(campoDoi, '').strip(),
                                    "titulo":  (fila.get(campoTit, 'Sin titulo')
                                                if campoTit else 'Sin titulo'),
                                })
            except Exception as e:
                print(f"Error leyendo {nombre}: {e}")

        # actualizar historial (sin duplicados, max 20)
        if doi_q not in self._historial_doi:
            self._historial_doi.insert(0, doi_q)
            self._historial_doi = self._historial_doi[:20]
        self.entradaDoi.config(values=self._historial_doi)

        self._n_busq_doi += 1
        self._upd_badge()

        R = self.txtDoi
        R.config(state=tk.NORMAL)
        R.delete(1.0, tk.END)

        if not resultados:
            self._doi_color("empty")
            R.insert(tk.END,
                     f"No se encontro el DOI en los archivos cargados.\n"
                     f"Buscado: {doi_q}\n")
            self.btnCopiarDoi.config(state=tk.DISABLED)
        elif len(resultados) > 1:
            self._doi_color("warn")
            R.insert(
                tk.END,
                f"DOI REPETIDO -- encontrado en "
                f"{len(resultados)} ubicaciones\n\n")
            for i, r in enumerate(resultados, 1):
                R.insert(tk.END, f"  {i}. {r['titulo']}\n")
                R.insert(tk.END, f"     DOI:     {r['doi']}\n")
                R.insert(tk.END, f"     Archivo: {r['archivo']}\n\n")
            self.btnCopiarDoi.config(state=tk.NORMAL)
        else:
            self._doi_color("ok")
            r = resultados[0]
            R.insert(tk.END, "DOI encontrado\n\n")
            R.insert(tk.END, f"  Titulo:  {r['titulo']}\n")
            R.insert(tk.END, f"  DOI:     {r['doi']}\n")
            R.insert(tk.END, f"  Archivo: {r['archivo']}\n")
            self.btnCopiarDoi.config(state=tk.NORMAL)

        R.config(state=tk.DISABLED)
        self._set_status(
            f"Busqueda '{doi_q}': "
            f"{len(resultados)} resultado{'s' if len(resultados) != 1 else ''}.")

    def _copiar_resultado_doi(self):
        """Copia el texto del panel DOI al portapapeles del sistema."""
        contenido = self.txtDoi.get("1.0", tk.END).strip()
        if contenido:
            self.ventana.clipboard_clear()
            self.ventana.clipboard_append(contenido)
            self._set_status("Resultado DOI copiado al portapapeles.")

    # ================================================================== EXPORTAR

    def exportarResultados(self):
        if not self.doi_unicos and not self.doi_repetidos:
            messagebox.showwarning("Sin datos",
                                   "No hay resultados para exportar.")
            return
        out = filedialog.asksaveasfilename(
            title="Guardar resultados",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialdir=".")
        if not out:
            return
        with open(out, 'w', encoding='utf-8', newline='') as f:
            w = cs.writer(f)
            w.writerow(["#", "Titulo", "DOI", "Archivo", "Tipo"])
            for i, (doi, d) in enumerate(self.doi_unicos.items(), 1):
                w.writerow([i, d["titulo"], doi, d["archivo"], "Unico"])
            for doi, d in self.doi_repetidos.items():
                for t, a in zip(d["titulos"], d["archivos"]):
                    w.writerow(["", t, doi, a, "Repetido"])
        messagebox.showinfo("Exportado",
                            f"Resultados guardados en:\n\n{out}")
        self._set_status(f"Exportado: {os.path.basename(out)}")

    def _exportar_acumulado(self):
        if not self.acumulado_dois:
            messagebox.showwarning("Sin datos", "El acumulado esta vacio.")
            return
        out = filedialog.asksaveasfilename(
            title="Guardar acumulado",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialdir=".")
        if not out:
            return
        with open(out, 'w', encoding='utf-8', newline='') as f:
            w = cs.writer(f)
            w.writerow(["#", "Titulo", "DOI", "Archivo"])
            for i, (doi, d) in enumerate(self.acumulado_dois.items(), 1):
                w.writerow([i, d["titulo"], doi, d["archivo"]])
        messagebox.showinfo("Exportado",
                            f"Acumulado guardado en:\n\n{out}")
        self._set_status(f"Acumulado exportado: {os.path.basename(out)}")

    # ================================================================== BLOQUEO

    def _bloquear(self, origen):
        """Deshabilita botones incompatibles segun el tipo de archivo cargado."""
        match origen:
            case "CSV":
                self.btnRIS.config(state=tk.DISABLED)
                self.btnBIB.config(state=tk.DISABLED)
            case "RIS":
                self.btnSelec.config(state=tk.DISABLED)
                self.btnBIB.config(state=tk.DISABLED)
            case "BIB":
                self.btnSelec.config(state=tk.DISABLED)
                self.btnRIS.config(state=tk.DISABLED)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = AnalizadorApp()
    app.ventana.mainloop()