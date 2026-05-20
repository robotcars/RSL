import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import csv as cs
import os
import re
import json
from collections import defaultdict
import bibtexparser
import copy

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
TEAL      = "#0D9488"
DANGER    = "#EF4444"
DUDA_BG   = "#FFFBEB"

FT  = ("Segoe UI", 13, "bold")
FLB = ("Segoe UI", 10, "bold")
FS  = ("Segoe UI", 9)
FM  = ("Consolas", 9)

# ---------------------------------------------------------------------------
# Fases del proceso PRISMA
# ---------------------------------------------------------------------------
FASES = {
    "fase1": "Fase 1: Ejecución de la búsqueda",
    "fase2": "Fase 2: Gestión de resultados y eliminación de duplicados",
    "fase3": "Fase 3: Filtrado por título y resumen",
    "fase4": "Fase 4: Evaluación de elegibilidad mediante lectura completa",
    "fase5": "Fase 5: Documentación PRISMA",
}


ORDEN_FASES = ["fase1", "fase2", "fase3", "fase4", "fase5"]

# ---------------------------------------------------------------------------
# Criterios de inclusion / exclusion
# ---------------------------------------------------------------------------
CRITERIOS = {
    "CI-1": "CI-1: Publicado entre 2020 y 2025",
    "CI-2": "CI-2: Articulo en idioma ingles",
    "CI-3": "CI-3: Titulo indica respuesta a pregunta de investigacion",
    "CI-4": "CI-4: Abstract indica respuesta a pregunta de investigacion",
    "CI-5": "CI-5: Lectura completa responde pregunta de investigacion",
    "CE-1": "CE-1: Articulo no accesible (sin lectura completa)",
    "CE-2": "CE-2: Articulo duplicado en una o mas fuentes",
    "CE-3": "CE-3: Centra en analisis tecnico de malware (no usuario final)",
}

CRITERIO_DEFAULT_POR_FASE = {
    "fase1": "CI-1",
    "fase2": "CE-2",
    "fase3": "CI-3",
    "fase4": "CI-5",
    "fase5": "CI-5",
}

MOTORES = ["IEEE", "ACM", "Springer Link", "Science Direct"]

# ---------------------------------------------------------------------------
# Columnas DOI conocidas por motor (en orden de prioridad)
# ---------------------------------------------------------------------------
DOI_CANDIDATES = ["doi", "do", "url"]

def _hallar_campo_doi(campos):
    campos_lower = {c.strip().lower(): c for c in campos}
    for cand in DOI_CANDIDATES:
        if cand in campos_lower:
            return campos_lower[cand]
    for c in campos:
        if "doi" in c.strip().lower():
            return c
    return None

def _es_doi_valido(valor):
    v = valor.strip().lower()
    return v not in ("", "n/a", "na", "none", "null", "-")


# ---------------------------------------------------------------------------
# Helpers de widgets
# ---------------------------------------------------------------------------

def make_btn(parent, text, cmd, bg=ACCENT, fg="white", **kw):
    return tk.Button(
        parent, text=text, command=cmd, bg=bg, fg=fg,
        relief=tk.FLAT, font=FLB, cursor="hand2",
        padx=12, pady=5,
        activebackground=ACCENT2, activeforeground="white", **kw)


def make_sep(parent, row, padx=16, pady=3):
    ttk.Separator(parent, orient="horizontal").grid(
        row=row, column=0, sticky="ew", padx=padx, pady=pady)


def make_card(parent, row, pady=(4, 4), padx=16):
    f = tk.Frame(parent, bg=CARD,
                 highlightthickness=1, highlightbackground=BORDER)
    f.grid(row=row, column=0, sticky="ew", padx=padx, pady=pady)
    return f


def make_scrolled_text(parent, height, **kw):
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
# Dialogo de seleccion de motor con opciones de avance y fase
# ---------------------------------------------------------------------------

class DialogMotor(tk.Toplevel):
    """Pregunta motor, fase PRISMA y si continuar o iniciar nuevo avance."""

    def __init__(self, parent, directorio_avance=None, fase_actual=None):
        super().__init__(parent)
        self.title("Seleccion de Estudios - Configuracion")
        self.configure(bg=BG)
        self.resizable(False, True)
        self.grab_set()

        self.result_motor      = None
        self.result_accion     = None   # "nuevo" | "continuar"
        self.result_directorio = directorio_avance
        self.result_fase       = fase_actual or "fase1"

        w, h = 560, 650
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._build()

    def _build(self):
        # ---- Motor ----
        tk.Label(self, text="Seleccion de Estudios",
                 font=FT, bg=BG, fg=TEXT).pack(pady=(18, 4), padx=20, anchor="w")
        tk.Label(self, text="Elige el motor de busqueda de esta cadena:",
                 font=FS, bg=BG, fg=MUTED).pack(padx=20, anchor="w")

        self.var_motor = tk.StringVar(value=MOTORES[0])
        frm = tk.Frame(self, bg=BG)
        frm.pack(padx=28, pady=8, anchor="w")
        for m in MOTORES:
            tk.Radiobutton(frm, text=m, variable=self.var_motor, value=m,
                           bg=BG, fg=TEXT, font=FLB,
                           activebackground=BG,
                           selectcolor=BADGE_BG).pack(anchor="w", pady=2)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=8)

        # ---- Fase PRISMA ----
        tk.Label(self, text="Fase del proceso PRISMA:",
                 font=FLB, bg=BG, fg=TEXT).pack(padx=20, anchor="w")

        self.var_fase = tk.StringVar(value=self.result_fase)
        frm_fase = tk.Frame(self, bg=BG)
        frm_fase.pack(padx=28, pady=(4, 8), anchor="w")
        for key, texto in FASES.items():
            tk.Radiobutton(
                frm_fase, text=texto, variable=self.var_fase, value=key,
                bg=BG, fg=TEXT, font=FS,
                activebackground=BG,
                selectcolor=BADGE_BG,
                wraplength=430, justify="left"
            ).pack(anchor="w", pady=2)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=8)

        # ---- Accion ----
        tk.Label(self, text="¿Que deseas hacer?",
                 font=FLB, bg=BG, fg=TEXT).pack(padx=20, anchor="w")

        self.var_accion = tk.StringVar(value="nuevo")
        tk.Radiobutton(self, text="Iniciar nueva seleccion (sin avance previo)",
                       variable=self.var_accion, value="nuevo",
                       bg=BG, fg=TEXT, font=FS,
                       activebackground=BG, selectcolor=BADGE_BG,
                       command=self._toggle_dir).pack(padx=28, anchor="w", pady=2)
        tk.Radiobutton(self, text="Continuar avance existente (cargar JSON)",
                       variable=self.var_accion, value="continuar",
                       bg=BG, fg=TEXT, font=FS,
                       activebackground=BG, selectcolor=BADGE_BG,
                       command=self._toggle_dir).pack(padx=28, anchor="w", pady=2)

        self.frm_dir = tk.Frame(self, bg=BG)
        self.lbl_dir = tk.Label(self.frm_dir, text="Sin directorio seleccionado",
                                font=FS, bg=BG, fg=MUTED)
        self.lbl_dir.pack(side="left")
        make_btn(self.frm_dir, "Seleccionar...", self._sel_dir,
                 bg="#94A3B8", fg=TEXT).pack(side="left", padx=(8, 0))
        # Mostrar frame de directorio si directorio ya esta seleccionado
        self._toggle_dir()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=20, pady=10)

        bf = tk.Frame(self, bg=BG)
        bf.pack(padx=20, fill="x")
        make_btn(bf, "Cancelar", self.destroy,
                 bg="#94A3B8", fg=TEXT).pack(side="right", padx=(8, 0))
        make_btn(bf, "Aceptar", self._aceptar).pack(side="right")

        # Actualizar label si ya hay directorio
        if self.result_directorio:
            d = self.result_directorio
            self.lbl_dir.config(
                text=d if len(d) < 50 else "..." + d[-47:], fg=TEXT)

    def _toggle_dir(self):
        if self.var_accion.get() == "continuar":
            self.frm_dir.pack(padx=28, anchor="w", pady=(4, 0))
        else:
            self.frm_dir.pack_forget()

    def _sel_dir(self):
        d = filedialog.askdirectory(title="Seleccionar directorio de avance")
        if d:
            self.result_directorio = d
            self.lbl_dir.config(
                text=d if len(d) < 50 else "..." + d[-47:], fg=TEXT)

    def _aceptar(self):
        self.result_motor  = self.var_motor.get()
        self.result_accion = self.var_accion.get()
        self.result_fase   = self.var_fase.get()
        if self.result_accion == "continuar" and not self.result_directorio:
            messagebox.showwarning("Directorio requerido",
                                   "Selecciona el directorio donde estan los avances.",
                                   parent=self)
            return
        self.destroy()


# ---------------------------------------------------------------------------
# Dialogo para elegir directorio donde guardar avances (primera vez)
# ---------------------------------------------------------------------------

class DialogGuardar(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Guardar avances - Primera vez")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        w, h = 420, 200
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self._build()

    def _build(self):
        tk.Label(self, text="Primera carga de CSV",
                 font=FT, bg=BG, fg=TEXT).pack(pady=(18, 4), padx=20, anchor="w")
        tk.Label(self,
                 text="Elige la carpeta donde se guardaran\nlos archivos de avance (JSON y CSV).",
                 font=FS, bg=BG, fg=MUTED, justify="left").pack(padx=20, anchor="w")

        self.lbl = tk.Label(self, text="Sin seleccionar",
                            font=FS, bg=BG, fg=MUTED)
        self.lbl.pack(padx=20, pady=6, anchor="w")

        bf = tk.Frame(self, bg=BG)
        bf.pack(padx=20, fill="x", pady=(0, 12))
        make_btn(bf, "Seleccionar carpeta...", self._sel).pack(side="left")
        make_btn(bf, "Aceptar", self._ok).pack(side="left", padx=(8, 0))
        make_btn(bf, "Cancelar", self.destroy,
                 bg="#94A3B8", fg=TEXT).pack(side="right")

    def _sel(self):
        d = filedialog.askdirectory(title="Carpeta de avances")
        if d:
            self.result = d
            self.lbl.config(text=d if len(d) < 55 else "..." + d[-52:], fg=TEXT)

    def _ok(self):
        if not self.result:
            messagebox.showwarning("Requerido",
                                   "Selecciona una carpeta primero.", parent=self)
            return
        self.destroy()


# ---------------------------------------------------------------------------
# Dialogo para agregar un estudio manualmente
# ---------------------------------------------------------------------------

class DialogAgregarEstudio(tk.Toplevel):
    """Formulario para ingresar los datos de un estudio manualmente."""

    CAMPOS = [
        ("Titulo *",          "titulo",   True),
        ("DOI",               "doi",      False),
        ("Año de publicacion","anio",     False),
        ("Autores",           "autores",  False),
        ("Fuente / Revista",  "fuente",   False),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Agregar estudio manualmente")
        self.configure(bg=BG)
        self.resizable(False, True)
        self.grab_set()
        self.result = None

        w, h = 560, 480
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._vars = {}
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=SUCCESS)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  + Agregar estudio manualmente",
                 font=("Segoe UI", 11, "bold"), fg="white", bg=SUCCESS,
                 anchor="w", pady=8).pack(fill="x", padx=10)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=12)
        body.grid_columnconfigure(1, weight=1)

        for row_i, (label, key, required) in enumerate(self.CAMPOS):
            tk.Label(body, text=label, font=FLB, bg=BG, fg=TEXT,
                     anchor="e", width=20).grid(
                row=row_i, column=0, sticky="e", padx=(0, 8), pady=5)
            var = tk.StringVar()
            self._vars[key] = var
            ent = tk.Entry(body, textvariable=var, font=FS,
                           relief=tk.FLAT, bd=0,
                           highlightthickness=1,
                           highlightbackground=BORDER,
                           highlightcolor=ACCENT,
                           bg=CARD, fg=TEXT)
            ent.grid(row=row_i, column=1, sticky="ew", ipady=5, pady=5)
            if row_i == 0:
                ent.focus_set()

        tk.Label(body, text="Abstract / Notas", font=FLB, bg=BG, fg=TEXT,
                 anchor="ne", width=20).grid(
            row=len(self.CAMPOS), column=0, sticky="ne", padx=(0, 8), pady=5)

        abs_frame = tk.Frame(body, bg=CARD,
                             highlightthickness=1, highlightbackground=BORDER)
        abs_frame.grid(row=len(self.CAMPOS), column=1, sticky="ew", pady=5)
        abs_frame.grid_columnconfigure(0, weight=1)

        self._txt_abstract = tk.Text(abs_frame, height=5, font=FS,
                                     relief=tk.FLAT, bd=0,
                                     wrap="word", padx=6, pady=6,
                                     bg=CARD, fg=TEXT)
        self._txt_abstract.grid(row=0, column=0, sticky="ew")
        sb_abs = tk.Scrollbar(abs_frame, orient="vertical",
                              command=self._txt_abstract.yview)
        self._txt_abstract.configure(yscrollcommand=sb_abs.set)
        sb_abs.grid(row=0, column=1, sticky="ns")

        tk.Label(body, text="* Campo requerido", font=FS,
                 bg=BG, fg=MUTED).grid(
            row=len(self.CAMPOS)+1, column=1, sticky="w", pady=(0, 4))

        bf = tk.Frame(self, bg=BG)
        bf.pack(fill="x", padx=20, pady=(0, 14))
        make_btn(bf, "Cancelar", self.destroy,
                 bg="#94A3B8", fg=TEXT).pack(side="right", padx=(8, 0))
        make_btn(bf, "Agregar estudio", self._aceptar,
                 bg=SUCCESS).pack(side="right")

    def _aceptar(self):
        titulo = self._vars["titulo"].get().strip()
        if not titulo:
            messagebox.showwarning("Campo requerido",
                                   "El titulo es obligatorio.", parent=self)
            return
        self.result = {
            "titulo":   titulo,
            "doi":      self._vars["doi"].get().strip(),
            "anio":     self._vars["anio"].get().strip(),
            "autores":  self._vars["autores"].get().strip(),
            "fuente":   self._vars["fuente"].get().strip(),
            "abstract": self._txt_abstract.get("1.0", tk.END).strip(),
        }
        self.destroy()


# ---------------------------------------------------------------------------
# Aplicacion principal
# ---------------------------------------------------------------------------

class AnalizadorApp:

    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title("Analizador de Resultados de Busqueda")
        self.ventana.configure(bg=BG)

        w, h = 1100, 960
        sw = self.ventana.winfo_screenwidth()
        sh = self.ventana.winfo_screenheight()
        self.ventana.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.ventana.resizable(True, True)

        self.archivoRuta    = []
        self.doi_repetidos  = {}
        self.doi_unicos     = {}
        self.acumulado_dois = {}
        self._n_busq_doi    = 0
        self._historial_doi = []
        self._dois_buscados = {}
        self._n_encontrados = 0

        # --- Estado pestaña Seleccion de Estudios ---
        self._sel_motor        = None
        self._sel_fase_actual  = "fase1"
        self._sel_fases_data   = {}   # snapshots por fase
        self._sel_dir          = None
        self._sel_estudios     = []
        self._sel_eliminados   = []
        self._sel_csv_path     = None
        self._sel_campos       = []
        self._sel_checkvars    = []
        self._sel_motivovars   = []
        self._sel_dudavars     = []
        self._sel_notadudavars = []
        self._sel_fasesvars    = []
        self._sel_fase_btns    = []
        self._sel_manuales     = 0
        self._sel_ocultar_eliminados = False

        self._build_notebook()
        self._build_statusbar()

    # ================================================================== NOTEBOOK

    def _build_notebook(self):
        self.nb = ttk.Notebook(self.ventana)
        self.nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_analizador = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_analizador, text="  Analizador  ")

        self.tab_seleccion = tk.Frame(self.nb, bg=BG)
        self.nb.add(self.tab_seleccion, text="  Seleccion de Estudios  ")

        self._build_tab_analizador()
        self._build_tab_seleccion()

    # ================================================================== TAB ANALIZADOR

    def _build_tab_analizador(self):
        p = self.tab_analizador
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(6, weight=2)
        p.grid_rowconfigure(9,  weight=1)

        self._build_header(p)
        self._build_archivos(p)
        self._build_analizar(p)
        self._build_buscador_doi(p)
        self._build_resultados(p)
        self._build_acumulado(p)
        self._build_exportar(p)

    # ================================================================== TAB SELECCION

    def _build_tab_seleccion(self):
        p = self.tab_seleccion
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(3, weight=1)

        # ---- Header ----
        hdr = tk.Frame(p, bg=PURPLE)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        tk.Label(hdr,
                 text="  Seleccion de Estudios  —  Aplicacion de Criterios de Inclusion/Exclusion",
                 font=("Segoe UI", 12, "bold"), fg="white", bg=PURPLE,
                 anchor="w", pady=9).grid(row=0, column=0, sticky="ew", padx=12)

        # ---- Barra de motor ----
        top = tk.Frame(p, bg=CARD,
                       highlightthickness=1, highlightbackground=BORDER)
        top.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 4))
        top.grid_columnconfigure(5, weight=1)

        tk.Label(top, text="Motor:", font=FLB,
                 bg=CARD, fg=TEXT).grid(row=0, column=0, padx=(14, 4), pady=8, sticky="w")
        self.lbl_motor_sel = tk.Label(top, text="Sin seleccionar",
                                      font=FS, bg=CARD, fg=MUTED)
        self.lbl_motor_sel.grid(row=0, column=1, padx=(0, 6), pady=8, sticky="w")

        # Label de fase actual
        tk.Label(top, text="Fase:", font=FLB,
                 bg=CARD, fg=TEXT).grid(row=0, column=2, padx=(10, 4), pady=8, sticky="w")
        self.lbl_fase_sel = tk.Label(top, text="—",
                                     font=FS, bg=CARD, fg=PURPLE)
        self.lbl_fase_sel.grid(row=0, column=3, padx=(0, 10), pady=8, sticky="w")

        make_btn(top, "Configurar motor / fase / avance",
                 self._sel_configurar, bg=PURPLE).grid(
            row=0, column=4, padx=6, pady=8, sticky="w")

        make_btn(top, "Cargar CSV / RIS / BIB",
                 self._sel_cargar_archivo, bg=ACCENT).grid(
            row=0, column=5, padx=6, pady=8, sticky="w")

        self.lbl_sel_archivo = tk.Label(top, text="Sin archivo cargado",
                                        font=FS, bg=CARD, fg=MUTED)
        self.lbl_sel_archivo.grid(row=0, column=6, padx=(0, 14), pady=8, sticky="w")

        # ---- Barra de estadísticas y botones ----
        stats_outer = tk.Frame(p, bg=BG)
        stats_outer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))
        stats_outer.grid_columnconfigure(0, weight=1)

        # -- Fila 1: estadísticas --
        stats_f = tk.Frame(stats_outer, bg=BG)
        stats_f.pack(fill="x", pady=(0, 3))
        stats_f.grid_columnconfigure(0, weight=1)

        self.lbl_sel_stats = tk.Label(
            stats_f, text="Carga un archivo para comenzar.",
            font=FS, bg=BG, fg=MUTED, anchor="w")
        self.lbl_sel_stats.pack(side="left")

        self.lbl_fases = tk.Label(
            stats_f, text="  CI-3: 0  |  CI-4: 0  |  CI-5: 0  ",
            font=FS, bg=BADGE_BG, fg=BADGE_FG, padx=6, pady=2)
        self.lbl_fases.pack(side="left", padx=(10, 0))

        self.lbl_manuales = tk.Label(
            stats_f, text="  + 0 agregados manualmente  ",
            font=FS, bg=BG, fg=MUTED, padx=6, pady=2)
        self.lbl_manuales.pack(side="left", padx=(10, 0))

        # -- Fila 2: botones de acción --
        btns_f = tk.Frame(stats_outer, bg=BG)
        btns_f.pack(fill="x")

        make_btn(btns_f, "+ Agregar manual",
                self._sel_agregar_manual, bg="#6366F1").pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Importar dudas",
                self._sel_importar_dudas, bg=WARN).pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Exportar aceptados CSV",
                self._sel_exportar_aceptados, bg=SUCCESS).pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Exportar eliminados CSV",
                self._sel_exportar_eliminados, bg="#0F172A").pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Guardar avance",
                self._sel_guardar_avance, bg=TEAL).pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Ocultar/mostrar eliminados",
                self._sel_toggle_ocultar_eliminados, bg="#475569").pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Fase anterior",
                self._sel_retroceder_fase, bg="#64748B").pack(side="left", padx=(0, 6))
        make_btn(btns_f, "Avanzar fase",
                self._sel_avanzar_fase, bg=PURPLE).pack(side="left", padx=(0, 0))
        make_btn(btns_f, "Exportar dudas CSV",
         self._sel_exportar_dudas, bg="#B45309").pack(side="left", padx=(0, 6))
        # ---- Tabla scrolleable ----
        tabla_outer = tk.Frame(p, bg=CARD,
                               highlightthickness=1, highlightbackground=BORDER)
        tabla_outer.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        tabla_outer.grid_columnconfigure(0, weight=1)
        tabla_outer.grid_rowconfigure(0, weight=1)

        self.sel_canvas = tk.Canvas(tabla_outer, bg=CARD, highlightthickness=0)
        self.sel_canvas.grid(row=0, column=0, sticky="nsew")

        sb_v = tk.Scrollbar(tabla_outer, orient="vertical",
                             command=self.sel_canvas.yview)
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h = tk.Scrollbar(tabla_outer, orient="horizontal",
                             command=self.sel_canvas.xview)
        sb_h.grid(row=1, column=0, sticky="ew")
        self.sel_canvas.configure(yscrollcommand=sb_v.set,
                                  xscrollcommand=sb_h.set)

        self.sel_frame_inner = tk.Frame(self.sel_canvas, bg=CARD)
        self._sel_canvas_window = self.sel_canvas.create_window(
            (0, 0), window=self.sel_frame_inner, anchor="nw")

        self.sel_frame_inner.bind(
            "<Configure>",
            lambda e: self.sel_canvas.configure(
                scrollregion=self.sel_canvas.bbox("all")))
        self.sel_canvas.bind(
            "<Configure>",
            lambda e: self.sel_canvas.itemconfig(
                self._sel_canvas_window, width=e.width))
        self.sel_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._sel_mostrar_bienvenida()

    def _on_mousewheel(self, event):
        if self.nb.index(self.nb.select()) == 1:
            self.sel_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _sel_mostrar_bienvenida(self):
        for w in self.sel_frame_inner.winfo_children():
            w.destroy()
        msg = tk.Frame(self.sel_frame_inner, bg=CARD)
        msg.pack(expand=True, fill="both", padx=40, pady=60)
        tk.Label(msg, text="Seleccion de Estudios",
                 font=("Segoe UI", 16, "bold"), bg=CARD, fg=PURPLE).pack(pady=(0, 8))
        tk.Label(msg,
                 text="1. Haz clic en «Configurar motor / fase / avance» para elegir motor y fase PRISMA.\n"
                      "2. Carga un archivo CSV, RIS o BIB con los estudios de la cadena.\n"
                      "3. Marca los estudios que deseas ELIMINAR y elige el motivo.\n"
                      "4. Si tienes DUDA sobre un estudio, marca el checkbox de duda y escribe el motivo.\n"
                      "5. Usa «+ Agregar manual» para incluir estudios que no esten en el CSV.\n"
                      "6. Guarda el avance (JSON) y exporta CSVs de eliminados o aceptados cuando termines.\n"
                      "7. Usa «Importar dudas» para cargar estudios en duda desde otro avance JSON.",
                 font=FS, bg=CARD, fg=MUTED, justify="left").pack()

    # ------------------------------------------------------------------ CONFIG

    def _sel_actualizar_label_fase(self):
        fase_texto = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
        self.lbl_fase_sel.config(
            text=fase_texto[:55] + "..." if len(fase_texto) > 55 else fase_texto,
            fg=PURPLE
        )


    def _sel_sincronizar_estado_actual(self):
        """Pasa los valores de los widgets Tk al diccionario de cada estudio."""
        for idx, est in enumerate(self._sel_estudios):
            est["_eliminado"] = bool(self._sel_checkvars[idx].get()) \
                if idx < len(self._sel_checkvars) else False

            est["_motivo"] = self._sel_motivovars[idx].get() \
                if idx < len(self._sel_motivovars) else ""

            est["_duda"] = bool(self._sel_dudavars[idx].get()) \
                if idx < len(self._sel_dudavars) else False

            est["_nota_duda"] = self._sel_notadudavars[idx].get() \
                if idx < len(self._sel_notadudavars) else ""

            est["_fases"] = {
                "ci3": bool(self._sel_fasesvars[idx]["ci3"].get()),
                "ci4": bool(self._sel_fasesvars[idx]["ci4"].get()),
                "ci5": bool(self._sel_fasesvars[idx]["ci5"].get()),
            } if idx < len(self._sel_fasesvars) else {
                "ci3": False,
                "ci4": False,
                "ci5": False
            }


    def _sel_guardar_snapshot_fase_actual(self):
        """Guarda cómo está la fase actual, incluyendo eliminados."""
        if not self._sel_estudios:
            return

        self._sel_sincronizar_estado_actual()
        self._sel_fases_data[self._sel_fase_actual] = copy.deepcopy(self._sel_estudios)


    def _sel_limpiar_estado_para_nueva_fase(self, estudios):
        """
        Crea los estudios que pasan a la siguiente fase.
        Se copian los datos bibliográficos, pero se limpian marcas de eliminación.
        """
        salida = []

        for est in estudios:
            nuevo = copy.deepcopy(est)

            nuevo["_eliminado"] = False
            nuevo["_motivo"] = ""
            nuevo["_duda"] = False
            nuevo["_nota_duda"] = ""
            nuevo["_fases"] = {"ci3": False, "ci4": False, "ci5": False}

            salida.append(nuevo)

        return salida


    def _sel_ir_a_fase(self, fase_destino, guardar_actual=True):
        """
        Cambia de fase.
        Si la fase ya existe, la carga como estaba.
        Si no existe, la crea desde los aceptados de la fase anterior.
        """
        if fase_destino not in FASES:
            return

        if guardar_actual:
            self._sel_guardar_snapshot_fase_actual()

        if fase_destino in self._sel_fases_data:
            self._sel_estudios = copy.deepcopy(self._sel_fases_data[fase_destino])
        else:
            idx = ORDEN_FASES.index(fase_destino)

            if idx > 0:
                fase_anterior = ORDEN_FASES[idx - 1]
                base = self._sel_fases_data.get(fase_anterior, [])
                aceptados = [e for e in base if not e.get("_eliminado")]
                self._sel_estudios = self._sel_limpiar_estado_para_nueva_fase(aceptados)
            else:
                self._sel_estudios = []

            self._sel_fases_data[fase_destino] = copy.deepcopy(self._sel_estudios)

        self._sel_fase_actual = fase_destino
        self._sel_actualizar_label_fase()
        self._sel_renderizar_tabla()
        self._actualizar_stats_sel()

        self._set_status(
            f"Fase activa: {FASES.get(self._sel_fase_actual, self._sel_fase_actual)}"
        )


    def _sel_avanzar_fase(self):
        """
        Avanza a la siguiente fase usando únicamente los estudios aceptados.
        Los eliminados quedan guardados en la fase anterior.
        """
        if not self._sel_estudios:
            messagebox.showwarning("Sin datos", "No hay estudios cargados.")
            return

        self._sel_guardar_snapshot_fase_actual()

        idx = ORDEN_FASES.index(self._sel_fase_actual)

        if idx >= len(ORDEN_FASES) - 1:
            messagebox.showinfo("Última fase", "Ya estás en la última fase.")
            return

        fase_siguiente = ORDEN_FASES[idx + 1]
        estudios_actuales = self._sel_fases_data.get(self._sel_fase_actual, [])

        aceptados = [e for e in estudios_actuales if not e.get("_eliminado")]

        if not aceptados:
            messagebox.showwarning(
                "Sin aceptados",
                "Todos los estudios están eliminados en esta fase."
            )
            return

        if fase_siguiente in self._sel_fases_data:
            ok = messagebox.askyesno(
                "Sobrescribir fase siguiente",
                f"La {FASES[fase_siguiente]} ya existe.\n\n"
                "Si continúas, se volverá a generar únicamente con los aceptados "
                "de la fase actual.\n\n¿Deseas sobrescribirla?"
            )
            if not ok:
                return

        self._sel_fases_data[fase_siguiente] = self._sel_limpiar_estado_para_nueva_fase(aceptados)

        self._sel_estudios = copy.deepcopy(self._sel_fases_data[fase_siguiente])
        self._sel_fase_actual = fase_siguiente

        self._sel_actualizar_label_fase()
        self._sel_renderizar_tabla()
        self._actualizar_stats_sel()

        self._set_status(
            f"Avanzaste a {FASES[fase_siguiente]} con {len(aceptados)} estudios aceptados."
        )


    def _sel_configurar(self):
        dlg = DialogMotor(self.ventana, self._sel_dir, self._sel_fase_actual)
        self.ventana.wait_window(dlg)

        if not dlg.result_motor:
            return

        self._sel_motor = dlg.result_motor
        fase_elegida = dlg.result_fase

        self.lbl_motor_sel.config(text=self._sel_motor, fg=ACCENT)

        if dlg.result_accion == "continuar":
            self._sel_dir = dlg.result_directorio
            self._sel_cargar_avance_json(fase_elegida=fase_elegida)
        else:
            if self._sel_estudios:
                self._sel_ir_a_fase(fase_elegida)
            else:
                self._sel_fase_actual = fase_elegida
                self._sel_actualizar_label_fase()

            fase_texto = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
            self._set_status(
                f"Motor: {self._sel_motor} | Fase: {fase_texto}. Listo para cargar CSV."
        )

    def _sel_cargar_avance_json(self, fase_elegida=None):
        if not self._sel_motor or not self._sel_dir:
            return
        nombre_json = os.path.join(
            self._sel_dir,
            f"avance_{self._sel_motor.replace(' ', '_')}.json")

        if not os.path.exists(nombre_json):
            messagebox.showinfo("Sin avance",
                                f"No se encontro avance para {self._sel_motor}.\n"
                                f"Inicia cargando el CSV de la cadena.")
            return

        try:
            with open(nombre_json, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._sel_campos   = data.get("campos", [])
            self._sel_csv_path = data.get("csv_path", "")
            self._sel_manuales = data.get("manuales", 0)

            fase_guardada = data.get("fase_actual", "fase1")
            fase_objetivo = fase_elegida or fase_guardada

            # ── Cargar estudios planos (compatibilidad con avances viejos) ──
            estudios_planos = data.get("estudios", [])

            # ── Cargar fases_data si existe (avances nuevos) ──
            fases_data_guardado = data.get("fases_data", {})

            if fases_data_guardado:
                self._sel_fases_data = fases_data_guardado
            else:
                # Avance viejo: construir fases_data desde estudios planos
                self._sel_fases_data = {fase_guardada: estudios_planos}

            # Cargar la fase objetivo
            if fase_objetivo in self._sel_fases_data:
                self._sel_estudios = copy.deepcopy(self._sel_fases_data[fase_objetivo])
                self._sel_fase_actual = fase_objetivo
            else:
                self._sel_fase_actual = fase_guardada
                self._sel_estudios = copy.deepcopy(
                    self._sel_fases_data.get(fase_guardada, estudios_planos))

            # ── Migrar formato viejo → nuevo (_estado_fases) ──
            # Debe hacerse ANTES de renderizar
            self._sel_migrar_avance_viejo(self._sel_fase_actual)

            self._sel_actualizar_label_fase()

            self.lbl_sel_archivo.config(
                text=os.path.basename(self._sel_csv_path) if self._sel_csv_path
                    else "avance cargado",
                fg=SUCCESS)

            self._sel_renderizar_tabla()
            self._actualizar_stats_sel()

            total = len(self._sel_estudios)
            self._set_status(f"Avance cargado: {total} estudios.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el avance:\n{e}")

    # ------------------------------------------------------------------ CARGAR

    def _sel_cargar_archivo(self):
        if not self._sel_motor:
            messagebox.showwarning(
                "Motor no configurado",
                "Primero haz clic en «Configurar motor / fase / avance».")
            return

        ruta = filedialog.askopenfilename(
            title="Cargar archivo de estudios",
            filetypes=[("CSV/RIS/BIB", "*.csv *.ris *.bib"),
                       ("CSV", "*.csv"), ("RIS", "*.ris"), ("BIB", "*.bib")],
            initialdir=".")
        if not ruta:
            return

        ext = os.path.splitext(ruta)[1].lower()
        if ext == ".ris":
            ruta = self._convertir_ris_temp(ruta)
            if not ruta:
                return
        elif ext == ".bib":
            ruta = self._convertir_bib_temp(ruta)
            if not ruta:
                return

        if not self._sel_dir:
            dlg = DialogGuardar(self.ventana)
            self.ventana.wait_window(dlg)
            if not dlg.result:
                messagebox.showwarning("Cancelado",
                                       "Debes seleccionar una carpeta para guardar avances.")
                return
            self._sel_dir = dlg.result

        self._sel_csv_path = ruta
        self.lbl_sel_archivo.config(text=os.path.basename(ruta), fg=SUCCESS)

        try:
            self._sel_estudios = []
            self._sel_campos   = []
            with open(ruta, "r", encoding="utf-8", newline="") as f:
                rdr = cs.DictReader(f)
                self._sel_campos = list(rdr.fieldnames or [])
                for row in rdr:
                    self._sel_estudios.append(dict(row))

            dois_elim = {e.get("DOI", e.get("doi", "")).strip().lower()
                         for e in self._sel_eliminados}
            for est in self._sel_estudios:
                doi_e = est.get("DOI", est.get("doi", "")).strip().lower()
                est["_eliminado"] = doi_e in dois_elim
                if doi_e in dois_elim:
                    match = next(
                        (x for x in self._sel_eliminados
                         if x.get("DOI", x.get("doi", "")).strip().lower() == doi_e), None)
                    est["_motivo"] = match.get("Motivo", "") if match else ""
                else:
                    est["_eliminado"] = False
                    est["_motivo"]    = ""
                if "_duda"      not in est: est["_duda"]      = False
                if "_nota_duda" not in est: est["_nota_duda"] = ""
                if "_fases"     not in est:
                    est["_fases"] = {"ci3": False, "ci4": False, "ci5": False}

            self._sel_fases_data = {
                self._sel_fase_actual: copy.deepcopy(self._sel_estudios)
            }
            self._sel_renderizar_tabla()
            self._actualizar_stats_sel()
            self._set_status(
                f"Cargados {len(self._sel_estudios)} estudios desde {os.path.basename(ruta)}.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")

    def _convertir_ris_temp(self, ruta):
        try:
            nombre = os.path.basename(ruta)
            with open(ruta, 'r', encoding='utf-8') as ar:
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
            csv_ruta = os.path.join(os.path.dirname(ruta), f"{nombre[:-4]}_temp.csv")
            with open(csv_ruta, 'w', encoding='utf-8', newline='') as out:
                w = cs.DictWriter(out, fieldnames=ordenCampos)
                w.writeheader()
                for ref in referencias:
                    w.writerow({c: ' ; '.join(ref.get(c, [])) for c in ordenCampos})
            return csv_ruta
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo convertir RIS:\n{e}")
            return None

    def _convertir_bib_temp(self, ruta):
        try:
            nombre = os.path.basename(ruta)
            with open(ruta, 'r', encoding='utf-8') as ar:
                bib = bibtexparser.load(ar)
            if not bib.entries:
                messagebox.showwarning("Archivo vacio", "No hay entradas BIB.")
                return None
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
            csv_ruta = os.path.join(os.path.dirname(ruta), f"{nombre[:-4]}_temp.csv")
            with open(csv_ruta, 'w', encoding='utf-8', newline='') as out:
                w = cs.DictWriter(out, fieldnames=orden)
                w.writeheader()
                for e in bib.entries:
                    w.writerow(e)
            return csv_ruta
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo convertir BIB:\n{e}")
            return None

    # ------------------------------------------------------------------ TABLA

    def _actualizar_label_fase(self):
        fase_texto = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
        self.lbl_fase_sel.config(
            text=fase_texto[:55] + "..." if len(fase_texto) > 55 else fase_texto,
            fg=PURPLE
        )
    
    def _bool_legacy(self, valor):
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, int):
            return valor == 1
        if isinstance(valor, str):
            return valor.strip().lower() in ("1", "true", "si", "sí", "yes")
        return False

    def _sel_migrar_avance_viejo(self, fase_origen="fase1"):
        if fase_origen not in ORDEN_FASES:
            fase_origen = "fase1"

        for est in self._sel_estudios:
            estado_existente = est.get("_estado_fases")
            if isinstance(estado_existente, dict) and estado_existente:
                continue  # Ya tiene formato nuevo

            fases_legacy = est.get("_fases", {"ci3": False, "ci4": False, "ci5": False})
            if not isinstance(fases_legacy, dict):
                fases_legacy = {"ci3": False, "ci4": False, "ci5": False}

            est["_estado_fases"] = {
                fase_origen: {
                    "eliminado":  self._bool_legacy(est.get("_eliminado", False)),
                    "motivo":     est.get("_motivo", ""),
                    "duda":       self._bool_legacy(est.get("_duda", False)),
                    "nota_duda":  est.get("_nota_duda", ""),
                    "fases": {
                        "ci3": self._bool_legacy(fases_legacy.get("ci3", False)),
                        "ci4": self._bool_legacy(fases_legacy.get("ci4", False)),
                        "ci5": self._bool_legacy(fases_legacy.get("ci5", False)),
                    },
                }
            }

        # ── NUEVO: sincronizar fases_data con la migración ──
        self._sel_fases_data[fase_origen] = copy.deepcopy(self._sel_estudios)
    def _sel_estado_fase(self, est, fase=None):
        fase = fase or self._sel_fase_actual

        if "_estado_fases" not in est or not isinstance(est.get("_estado_fases"), dict):
            est["_estado_fases"] = {}

        if fase not in est["_estado_fases"]:
            est["_estado_fases"][fase] = {
                "eliminado": False,
                "motivo": "",
                "duda": False,
                "nota_duda": "",
                "fases": {"ci3": False, "ci4": False, "ci5": False},
            }

        return est["_estado_fases"][fase]


    def _sel_aceptado_hasta_fase_anterior(self, est):
        pos = ORDEN_FASES.index(self._sel_fase_actual)

        for fase in ORDEN_FASES[:pos]:
            estado = self._sel_estado_fase(est, fase)
            if estado.get("eliminado"):
                return False

        return True


    def _sel_indices_visibles(self):
        indices = []

        for idx, est in enumerate(self._sel_estudios):
            if not self._sel_aceptado_hasta_fase_anterior(est):
                continue

            estado_actual = self._sel_estado_fase(est)

            if self._sel_ocultar_eliminados and estado_actual.get("eliminado"):
                continue

            indices.append(idx)

        return indices


    def _sel_sincronizar_fase_actual(self):
        for idx, est in enumerate(self._sel_estudios):
            if idx >= len(self._sel_checkvars):
                continue

            if self._sel_checkvars[idx] is None:
                continue

            estado = self._sel_estado_fase(est)

            estado["eliminado"] = bool(self._sel_checkvars[idx].get())
            estado["motivo"] = self._sel_motivovars[idx].get()
            estado["duda"] = bool(self._sel_dudavars[idx].get())
            estado["nota_duda"] = self._sel_notadudavars[idx].get()
            estado["fases"] = {
                "ci3": bool(self._sel_fasesvars[idx]["ci3"].get()),
                "ci4": bool(self._sel_fasesvars[idx]["ci4"].get()),
                "ci5": bool(self._sel_fasesvars[idx]["ci5"].get()),
            }

            # Compatibilidad con tu código viejo
            est["_eliminado"] = estado["eliminado"]
            est["_motivo"] = estado["motivo"]
            est["_duda"] = estado["duda"]
            est["_nota_duda"] = estado["nota_duda"]
            est["_fases"] = estado["fases"]


    def _sel_toggle_ocultar_eliminados(self):
        self._sel_sincronizar_fase_actual()
        self._sel_ocultar_eliminados = not self._sel_ocultar_eliminados
        self._sel_renderizar_tabla()
        self._actualizar_stats_sel()




    def _sel_retroceder_fase(self):
        if not self._sel_estudios:
            messagebox.showwarning("Sin datos", "No hay estudios cargados.")
            return

        self._sel_sincronizar_fase_actual()

        pos = ORDEN_FASES.index(self._sel_fase_actual)

        if pos <= 0:
            messagebox.showinfo("Primera fase", "Ya estás en la primera fase.")
            return

        self._sel_fase_actual = ORDEN_FASES[pos - 1]
        self._sel_ocultar_eliminados = False

        self._actualizar_label_fase()
        self._sel_renderizar_tabla()
        self._actualizar_stats_sel()

        self._set_status(f"Regresaste a {FASES.get(self._sel_fase_actual)}.")
        
        
    
    def _sel_renderizar_tabla(self):
        for w in self.sel_frame_inner.winfo_children():
            w.destroy()

        n = len(self._sel_estudios)

        self._sel_checkvars    = [None] * n
        self._sel_motivovars   = [None] * n
        self._sel_dudavars     = [None] * n
        self._sel_notadudavars = [None] * n
        self._sel_fasesvars    = [None] * n
        self._sel_fase_btns    = [None] * n
        
        if not self._sel_estudios:
            tk.Label(self.sel_frame_inner,
                     text="No hay estudios cargados.", font=FS,
                     bg=CARD, fg=MUTED).pack(pady=30)
            return

        # -- Encabezado de la tabla --
        hdr = tk.Frame(self.sel_frame_inner, bg=ACCENT2)
        hdr.pack(fill="x", padx=0, pady=(0, 2))

        tk.Label(hdr, text="Elim.", font=FLB, bg=ACCENT2, fg="white",
                 width=6, anchor="center").pack(side="left", padx=(6, 0))
        tk.Label(hdr, text="Motivo de exclusion", font=FLB,
                 bg=ACCENT2, fg="white", width=36, anchor="w").pack(side="left", padx=4)
        tk.Label(hdr, text="?", font=FLB, bg=ACCENT2, fg="#FDE68A",
                 width=4, anchor="center").pack(side="left", padx=(4, 0))
        tk.Label(hdr, text="Motivo de duda", font=FLB,
                 bg=ACCENT2, fg="#FDE68A", width=30, anchor="w").pack(side="left", padx=4)
        tk.Label(hdr, text="Fases CI", font=FLB,
                 bg=ACCENT2, fg="#86EFAC", width=10, anchor="center").pack(side="left", padx=4)
        tk.Label(hdr, text="Datos del estudio", font=FLB,
                 bg=ACCENT2, fg="white", anchor="w").pack(side="left", padx=4, fill="x", expand=True)

        campos_mostrar = [c for c in self._sel_campos
                          if c not in ("_eliminado", "_motivo", "_duda", "_nota_duda")]

        titulo_campo = next(
            (c for c in campos_mostrar
             if c.lower() in ("document title", "title", "ti", "t1")),
            campos_mostrar[0] if campos_mostrar else None)
        doi_campo = _hallar_campo_doi(campos_mostrar)

        indices_visibles = self._sel_indices_visibles()

        for fila_num, idx in enumerate(indices_visibles):
            estudio = self._sel_estudios[idx]
            estado_fase = self._sel_estado_fase(estudio)
            
            ya_elim     = estado_fase.get("eliminado", False)
            motivo_prev = estado_fase.get("motivo", "")
            ya_duda     = estado_fase.get("duda", False)
            nota_duda   = estado_fase.get("nota_duda", "")
            fases_prev  = estado_fase.get("fases", {"ci3": False, "ci4": False, "ci5": False})

            chk_var  = tk.IntVar(value=1 if ya_elim else 0)
            criterio_default = CRITERIO_DEFAULT_POR_FASE.get(self._sel_fase_actual, "CI-1")

            mot_var = tk.StringVar(
                value=motivo_prev if motivo_prev else CRITERIOS[criterio_default]
            )
            duda_var = tk.IntVar(value=1 if ya_duda else 0)
            nota_var = tk.StringVar(value=nota_duda)
            fases_d  = {
                "ci3": tk.IntVar(value=1 if fases_prev.get("ci3") else 0),
                "ci4": tk.IntVar(value=1 if fases_prev.get("ci4") else 0),
                "ci5": tk.IntVar(value=1 if fases_prev.get("ci5") else 0),
            }

            self._sel_checkvars[idx] = chk_var
            self._sel_motivovars[idx] = mot_var
            self._sel_dudavars[idx] = duda_var
            self._sel_notadudavars[idx] = nota_var
            self._sel_fasesvars[idx] = fases_d

            if ya_elim:
                bg_row = "#FFF1F2"
            elif ya_duda:
                bg_row = DUDA_BG
            else:
                bg_row = CARD if fila_num % 2 == 0 else "#F8FAFC"

            fila = tk.Frame(self.sel_frame_inner, bg=bg_row,
                            highlightthickness=1, highlightbackground=BORDER)
            fila.pack(fill="x", padx=0, pady=1)

            chk = tk.Checkbutton(
                fila, variable=chk_var, bg=bg_row, activebackground=bg_row,
                command=lambda i=idx, f=fila: self._sel_toggle_fila(i, f))
            chk.pack(side="left", padx=(8, 2), pady=4)

            cb = ttk.Combobox(fila, textvariable=mot_var,
                              values=list(CRITERIOS.values()),
                              state="readonly", width=34, font=FS)
            cb.pack(side="left", padx=4, pady=4)
            if not chk_var.get():
                cb.config(state="disabled")
            fila._cb = cb

            chk_duda = tk.Checkbutton(
                fila, variable=duda_var, bg=bg_row, activebackground=bg_row,
                command=lambda i=idx, f=fila: self._sel_toggle_duda(i, f))
            chk_duda.pack(side="left", padx=(6, 2), pady=4)
            fila._chk_duda = chk_duda

            entry_duda = tk.Entry(
                fila, textvariable=nota_var,
                font=FS, width=28, relief=tk.FLAT, bd=1,
                bg="#FEF9C3" if ya_duda else "#F1F5F9", fg=TEXT,
                highlightthickness=1,
                highlightbackground=WARN if ya_duda else BORDER,
                highlightcolor=WARN)
            entry_duda.pack(side="left", padx=(0, 6), pady=4, ipady=3)
            if not duda_var.get():
                entry_duda.config(state="disabled", bg="#F1F5F9",
                                  highlightbackground=BORDER)
            fila._entry_duda = entry_duda

            n_fases = sum(v.get() for v in fases_d.values())
            if n_fases == 3:
                fase_bg, fase_fg, fase_txt = SUCCESS, "white", "✓ 3/3"
            elif n_fases > 0:
                fase_bg, fase_fg = WARN, "white"
                fase_txt = f"◑ {n_fases}/3"
            else:
                fase_bg, fase_fg, fase_txt = "#E2E8F0", TEXT, "Fases"

            btn_fases = tk.Button(
                fila, text=fase_txt,
                command=lambda i=idx: self._sel_abrir_fases(i),
                bg=fase_bg, fg=fase_fg, relief=tk.FLAT,
                font=("Segoe UI", 8, "bold"), cursor="hand2",
                padx=6, pady=3,
                activebackground=ACCENT2, activeforeground="white", width=7)
            btn_fases.pack(side="left", padx=(0, 4), pady=4)
            fila._btn_fases = btn_fases
            self._sel_fase_btns[idx] = btn_fases

            datos_f = tk.Frame(fila, bg=bg_row)
            datos_f.pack(side="left", fill="both", expand=True, padx=4, pady=4)

            tit_val = (estudio.get(titulo_campo, "Sin titulo") if titulo_campo else "Sin titulo")
            tit_txt = tit_val[:120] + "..." if len(tit_val) > 120 else tit_val
            tk.Label(datos_f, text=tit_txt,
                     font=("Segoe UI", 9, "bold"),
                     bg=bg_row, fg=TEXT, anchor="w",
                     wraplength=400, justify="left").pack(anchor="w")

            extra_parts = []
            if doi_campo and doi_campo in estudio:
                extra_parts.append(f"DOI: {estudio[doi_campo][:60]}")
            otros = [c for c in campos_mostrar
                     if c != titulo_campo and c != doi_campo][:3]
            for c in otros:
                val = estudio.get(c, "")
                if val:
                    extra_parts.append(f"{c}: {str(val)[:40]}")
            if extra_parts:
                tk.Label(datos_f, text="  |  ".join(extra_parts),
                         font=FS, bg=bg_row, fg=MUTED,
                         anchor="w", wraplength=400, justify="left").pack(anchor="w")

            # Badge de origen manual
            if estudio.get("_origen") == "manual":
                tk.Label(datos_f, text=" MANUAL ", font=("Segoe UI", 7, "bold"),
                         bg="#EDE9FE", fg=PURPLE, padx=4).pack(anchor="w")

            tk.Button(fila, text="▶",
                      command=lambda i=idx: self._sel_ver_detalle(i),
                      bg="#E2E8F0", fg=TEXT, relief=tk.FLAT,
                      font=FLB, cursor="hand2",
                      activebackground=BORDER).pack(side="right", padx=(0, 6), pady=4)

            fila._chk_var  = chk_var
            fila._duda_var = duda_var
            fila._idx      = idx

    # ------------------------------------------------------------------ TOGGLE FILA

    def _sel_toggle_fila(self, idx, fila):
        chk_val = self._sel_checkvars[idx].get()
        cb = fila._cb
        if chk_val:
            cb.config(state="readonly")
            fila.config(bg="#FFF1F2", highlightbackground="#FCA5A5")
            for w in fila.winfo_children():
                try:
                    if not isinstance(w, (ttk.Combobox, tk.Entry)):
                        w.config(bg="#FFF1F2")
                except Exception:
                    pass
        else:
            cb.config(state="disabled")
            duda_on = self._sel_dudavars[idx].get() if idx < len(self._sel_dudavars) else 0
            bg = DUDA_BG if duda_on else (CARD if idx % 2 == 0 else "#F8FAFC")
            fila.config(bg=bg, highlightbackground=BORDER)
            for w in fila.winfo_children():
                try:
                    if not isinstance(w, (ttk.Combobox, tk.Entry)):
                        w.config(bg=bg)
                except Exception:
                    pass
        self._actualizar_stats_sel()

    # ------------------------------------------------------------------ TOGGLE DUDA

    def _sel_toggle_duda(self, idx, fila):
        duda_on = self._sel_dudavars[idx].get()
        entry   = fila._entry_duda
        elim_on = self._sel_checkvars[idx].get()
        if duda_on:
            entry.config(state="normal", bg="#FEF9C3", highlightbackground=WARN)
            if not elim_on:
                bg = DUDA_BG
                fila.config(bg=bg, highlightbackground="#FDE68A")
                for w in fila.winfo_children():
                    try:
                        if not isinstance(w, (ttk.Combobox, tk.Entry)):
                            w.config(bg=bg)
                    except Exception:
                        pass
        else:
            entry.config(state="disabled", bg="#F1F5F9", highlightbackground=BORDER)
            if not elim_on:
                bg = CARD if idx % 2 == 0 else "#F8FAFC"
                fila.config(bg=bg, highlightbackground=BORDER)
                for w in fila.winfo_children():
                    try:
                        if not isinstance(w, (ttk.Combobox, tk.Entry)):
                            w.config(bg=bg)
                    except Exception:
                        pass
        self._actualizar_stats_sel()

    # ------------------------------------------------------------------ FASES CI

    def _sel_abrir_fases(self, idx):
        if idx >= len(self._sel_fasesvars):
            return

        dlg = tk.Toplevel(self.ventana)
        dlg.title(f"Fases / Criterios CI - Estudio #{idx + 1}")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()

        w, h = 520, 300
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Label(dlg, text=f"Marcar fases que cumple el estudio #{idx + 1}",
                 font=FT, bg=BG, fg=PURPLE).pack(padx=18, pady=(16, 6), anchor="w")
        tk.Label(dlg, text="Selecciona los criterios de inclusion alcanzados:",
                 font=FS, bg=BG, fg=MUTED).pack(padx=18, anchor="w")

        body = tk.Frame(dlg, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        body.pack(fill="x", padx=18, pady=12)

        for key, texto in [("ci3", CRITERIOS["CI-3"]),
                            ("ci4", CRITERIOS["CI-4"]),
                            ("ci5", CRITERIOS["CI-5"])]:
            tk.Checkbutton(body, text=texto,
                           variable=self._sel_fasesvars[idx][key],
                           bg=CARD, fg=TEXT, font=FS,
                           activebackground=CARD, selectcolor=BADGE_BG,
                           anchor="w").pack(fill="x", padx=14, pady=6, anchor="w")

        bf = tk.Frame(dlg, bg=BG)
        bf.pack(fill="x", padx=18, pady=(0, 14))

        def guardar():
            self._actualizar_boton_fases(idx)
            self._actualizar_stats_sel()
            dlg.destroy()

        make_btn(bf, "Guardar", guardar, bg=SUCCESS).pack(side="right")
        make_btn(bf, "Cancelar", dlg.destroy, bg="#94A3B8", fg=TEXT).pack(
            side="right", padx=(0, 8))

    def _actualizar_boton_fases(self, idx):
        if idx >= len(self._sel_fasesvars) or idx >= len(self._sel_fase_btns):
            return
        fases_d = self._sel_fasesvars[idx]
        n_fases = sum(v.get() for v in fases_d.values())
        btn = self._sel_fase_btns[idx]
        if n_fases == 3:
            btn.config(text="✓ 3/3", bg=SUCCESS, fg="white")
        elif n_fases > 0:
            btn.config(text=f"◑ {n_fases}/3", bg=WARN, fg="white")
        else:
            btn.config(text="Fases", bg="#E2E8F0", fg=TEXT)

    # ------------------------------------------------------------------ DETALLE

    def _sel_ver_detalle(self, idx):
        est = self._sel_estudios[idx]
        dlg = tk.Toplevel(self.ventana)
        dlg.title(f"Detalle estudio #{idx+1}")
        dlg.configure(bg=BG)
        dlg.grab_set()

        w, h = 680, 520
        sw = dlg.winfo_screenwidth()
        sh = dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        tk.Label(dlg, text=f"Estudio #{idx+1}",
                 font=FT, bg=BG, fg=PURPLE).pack(pady=(12, 4), padx=16, anchor="w")

        # Estado de la fase PRISMA actual
        tk.Label(dlg,
                 text=f"Fase PRISMA: {FASES.get(self._sel_fase_actual, '—')}",
                 font=("Segoe UI", 9, "bold"), bg=BADGE_BG, fg=BADGE_FG,
                 padx=10, pady=4, anchor="w").pack(fill="x", padx=16, pady=(0, 2))

        # Estado aceptado / eliminado
        if idx < len(self._sel_checkvars):
            if self._sel_checkvars[idx].get():
                motivo = self._sel_motivovars[idx].get() if idx < len(self._sel_motivovars) else ""
                tk.Label(dlg,
                         text=f"✗ ELIMINADO: {motivo}",
                         font=("Segoe UI", 9, "bold"), bg="#FFF1F2", fg=DANGER,
                         padx=10, pady=4, anchor="w").pack(fill="x", padx=16, pady=(0, 2))
            else:
                fases_d    = self._sel_fasesvars[idx] if idx < len(self._sel_fasesvars) else {}
                n_fases    = sum(v.get() for v in fases_d.values()) if fases_d else 0
                color_ac   = SUCCESS if n_fases == 3 else TEAL
                fases_txt  = f"CI aprobados: {n_fases}/3"
                tk.Label(dlg,
                         text=f"✓ ACEPTADO  —  {fases_txt}",
                         font=("Segoe UI", 9, "bold"), bg="#F0FDF4", fg=color_ac,
                         padx=10, pady=4, anchor="w").pack(fill="x", padx=16, pady=(0, 2))

        if idx < len(self._sel_dudavars) and self._sel_dudavars[idx].get():
            nota = self._sel_notadudavars[idx].get() if idx < len(self._sel_notadudavars) else ""
            tk.Label(dlg,
                     text=f"⚠ En duda: {nota if nota else '(sin nota)'}",
                     font=("Segoe UI", 9, "bold"), bg=DUDA_BG, fg="#92400E",
                     padx=10, pady=4, anchor="w").pack(fill="x", padx=16, pady=(0, 4))

        fr, txt = make_scrolled_text(dlg, height=24, font=FM, bg=CARD, fg=TEXT)
        fr.pack(fill="both", expand=True, padx=16, pady=4)
        txt.tag_config("campo", font=("Segoe UI", 9, "bold"), foreground=ACCENT2)
        txt.tag_config("val",   font=FM, foreground=TEXT)

        for campo in self._sel_campos:
            if campo.startswith("_"):
                continue
            val = est.get(campo, "")
            if val:
                txt.insert(tk.END, f"{campo}:\n", "campo")
                txt.insert(tk.END, f"  {val}\n\n", "val")
        txt.config(state=tk.DISABLED)
        make_btn(dlg, "Cerrar", dlg.destroy, bg="#94A3B8", fg=TEXT).pack(pady=8)

    # ------------------------------------------------------------------ STATS

    def _actualizar_stats_sel(self):
        indices = self._sel_indices_visibles()

        total = len(indices)
        marcados = 0
        dudas = 0
        ci3 = 0
        ci4 = 0
        ci5 = 0

        for idx in indices:
            est = self._sel_estudios[idx]
            estado = self._sel_estado_fase(est)

            if idx < len(self._sel_checkvars) and self._sel_checkvars[idx] is not None:
                eliminado = bool(self._sel_checkvars[idx].get())
                duda = bool(self._sel_dudavars[idx].get())
                fases = self._sel_fasesvars[idx]

                f_ci3 = bool(fases["ci3"].get())
                f_ci4 = bool(fases["ci4"].get())
                f_ci5 = bool(fases["ci5"].get())
            else:
                eliminado = estado.get("eliminado", False)
                duda = estado.get("duda", False)
                fases = estado.get("fases", {})

                f_ci3 = fases.get("ci3", False)
                f_ci4 = fases.get("ci4", False)
                f_ci5 = fases.get("ci5", False)

            if eliminado:
                marcados += 1
            if duda:
                dudas += 1
            if f_ci3:
                ci3 += 1
            if f_ci4:
                ci4 += 1
            if f_ci5:
                ci5 += 1

        self.lbl_sel_stats.config(
            text=(f"Fase actual: {FASES.get(self._sel_fase_actual)}  |  "
                f"Total visible: {total}  |  Marcados para eliminar: {marcados}"
                f"  |  Incluidos: {total - marcados}"
                f"  |  En duda: {dudas}"),
            fg=TEXT
        )

        self.lbl_fases.config(
            text=f"  CI-3: {ci3}  |  CI-4: {ci4}  |  CI-5: {ci5}  "
        )

        self.lbl_manuales.config(
            text=f"  + {self._sel_manuales} agregado{'s' if self._sel_manuales != 1 else ''} manualmente  ",
            fg=SUCCESS if self._sel_manuales > 0 else MUTED,
            bg="#F0FDF4" if self._sel_manuales > 0 else BG
        )
    # ------------------------------------------------------------------ AGREGAR MANUAL

    def _sel_agregar_manual(self):
        dlg = DialogAgregarEstudio(self.ventana)
        self.ventana.wait_window(dlg)
        if not dlg.result:
            return

        datos = dlg.result
        campos_nuevos = ["Document Title", "DOI", "Publication Year",
                         "Authors", "Source", "Abstract", "_origen"]
        for c in campos_nuevos:
            if c not in self._sel_campos:
                self._sel_campos.append(c)

        estudio = {c: "" for c in self._sel_campos}
        estudio.update({
            "Document Title":   datos["titulo"],
            "DOI":              datos["doi"],
            "Publication Year": datos["anio"],
            "Authors":          datos["autores"],
            "Source":           datos["fuente"],
            "Abstract":         datos["abstract"],
            "_origen":          "manual",
            "_eliminado":       False,
            "_motivo":          "",
            "_duda":            False,
            "_nota_duda":       "",
            "_fases": {"ci3": False, "ci4": False, "ci5": False},
        })

        self._sel_estudios.append(estudio)
        self._sel_manuales += 1
        self._sel_renderizar_tabla()
        self._actualizar_stats_sel()
        self.sel_canvas.update_idletasks()
        self.sel_canvas.yview_moveto(1.0)
        self._set_status(
            f"Estudio agregado manualmente: {datos['titulo'][:60] or '(sin titulo)'}")

    # ------------------------------------------------------------------ GUARDAR AVANCE (JSON + CSV)

    def _sel_guardar_avance(self):
        if not self._sel_estudios:
            messagebox.showwarning("Sin datos", "No hay estudios cargados.")
            return
        if not self._sel_dir:
            dlg = DialogGuardar(self.ventana)
            self.ventana.wait_window(dlg)
            if not dlg.result:
                return
            self._sel_dir = dlg.result

        # Sincronizar estado actual de las variables Tk → diccionarios
        self._sel_guardar_snapshot_fase_actual()

        nombre    = f"avance_{self._sel_motor.replace(' ', '_')}.json"
        ruta_json = os.path.join(self._sel_dir, nombre)

        data = {
            "motor":       self._sel_motor,
            "fase_actual": self._sel_fase_actual,           # NUEVO: fase guardada
            "csv_path":    self._sel_csv_path or "",
            "campos":      self._sel_campos,
            "estudios":    self._sel_estudios,
            "fases_data":  self._sel_fases_data,
            "manuales":    self._sel_manuales,
        }
        try:
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar JSON:\n{e}")
            return

        # Guardar también CSV de avance completo
        self._sel_guardar_csv_avance()

        self._set_status(f"Avance guardado: {nombre}")
        messagebox.showinfo("Guardado",
                            f"Avance guardado en:\n{ruta_json}\n\n"
                            f"CSV de avance también guardado en la misma carpeta.")

    def _sel_guardar_csv_avance(self):
        """Guarda todos los estudios (con estado) como CSV en la carpeta de avance."""
        if not self._sel_dir or not self._sel_estudios:
            return
        nombre_csv = f"avance_{self._sel_motor.replace(' ', '_')}.csv"
        ruta_csv   = os.path.join(self._sel_dir, nombre_csv)

        campos_base = [c for c in self._sel_campos if not c.startswith("_")]
        campos_extra = ["_Estado", "_Motivo", "_Duda", "_Nota_Duda",
                        "_CI3_Titulo", "_CI4_Abstract", "_CI5_Lectura",
                        "_Origen", "_Fase_PRISMA"]
        campos_out = campos_base + campos_extra

        try:
            with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
                w = cs.DictWriter(f, fieldnames=campos_out, extrasaction="ignore")
                w.writeheader()
                for est in self._sel_estudios:
                    fases_v = est.get("_fases", {})
                    fila = {c: est.get(c, "") for c in campos_base}
                    fila["_Estado"]      = "Eliminado" if est.get("_eliminado") else "Aceptado"
                    fila["_Motivo"]      = est.get("_motivo", "")
                    fila["_Duda"]        = "Si" if est.get("_duda") else "No"
                    fila["_Nota_Duda"]   = est.get("_nota_duda", "")
                    fila["_CI3_Titulo"]  = "Si" if fases_v.get("ci3") else "No"
                    fila["_CI4_Abstract"]= "Si" if fases_v.get("ci4") else "No"
                    fila["_CI5_Lectura"] = "Si" if fases_v.get("ci5") else "No"
                    fila["_Origen"]      = est.get("_origen", "csv")
                    fila["_Fase_PRISMA"] = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
                    w.writerow(fila)
        except Exception as e:
            messagebox.showwarning("Aviso CSV", f"No se pudo guardar CSV de avance:\n{e}")

    # ------------------------------------------------------------------ IMPORTAR DUDAS

    def _sel_importar_dudas(self):
        """Importa estudios marcados como duda desde otro (o el mismo) avance JSON."""
        ruta_json = filedialog.askopenfilename(
            title="Seleccionar avance JSON con dudas",
            filetypes=[("JSON", "*.json")],
            initialdir=self._sel_dir or ".")
        if not ruta_json:
            return

        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el JSON:\n{e}")
            return

        estudios_fuente = data.get("estudios", [])
        dudas = [e for e in estudios_fuente if e.get("_duda")]

        if not dudas:
            messagebox.showinfo("Sin dudas",
                                "El archivo seleccionado no contiene estudios marcados como duda.")
            return

        # Asegurar que los campos del CSV incluyan los del archivo importado
        campos_fuente = data.get("campos", [])
        for c in campos_fuente:
            if c not in self._sel_campos:
                self._sel_campos.append(c)

        # Calcular DOIs ya presentes para evitar duplicados
        doi_campo = _hallar_campo_doi(self._sel_campos)
        dois_presentes = set()
        for est in self._sel_estudios:
            if doi_campo:
                v = est.get(doi_campo, "").strip().lower()
                if v:
                    dois_presentes.add(v)

        agregados  = 0
        ignorados  = 0
        for est in dudas:
            doi_e = ""
            if doi_campo:
                doi_e = est.get(doi_campo, est.get("DOI", est.get("doi", ""))).strip().lower()

            if doi_e and doi_e in dois_presentes:
                ignorados += 1
                continue

            est_nuevo = {c: "" for c in self._sel_campos}
            est_nuevo.update(est)
            # Asegurar campos internos
            est_nuevo.setdefault("_eliminado",  False)
            est_nuevo.setdefault("_motivo",     "")
            est_nuevo.setdefault("_duda",       True)
            est_nuevo.setdefault("_nota_duda",  est.get("_nota_duda", ""))
            est_nuevo.setdefault("_fases",      {"ci3": False, "ci4": False, "ci5": False})
            est_nuevo["_origen"] = f"importado_duda:{os.path.basename(ruta_json)}"

            self._sel_estudios.append(est_nuevo)
            if doi_e:
                dois_presentes.add(doi_e)
            agregados += 1

        if agregados == 0:
            messagebox.showinfo("Sin novedades",
                                f"Todos los estudios con duda ({ignorados}) ya estaban presentes.")
            return

        self._sel_renderizar_tabla()
        self._actualizar_stats_sel()
        self.sel_canvas.update_idletasks()
        self.sel_canvas.yview_moveto(1.0)
        msg = f"{agregados} estudio(s) en duda importado(s)."
        if ignorados:
            msg += f"\n{ignorados} ignorado(s) por DOI duplicado."
        messagebox.showinfo("Importacion completada", msg)
        self._set_status(msg)

    # ------------------------------------------------------------------ EXPORTAR ELIMINADOS

    def _sel_exportar_eliminados(self):
        if not self._sel_estudios:
            messagebox.showwarning("Sin datos", "No hay estudios cargados.")
            return

        eliminados = []
        for idx, est in enumerate(self._sel_estudios):
            if idx < len(self._sel_checkvars) and self._sel_checkvars[idx].get():
                motivo_codigo = self._sel_motivovars[idx].get() \
                    if idx < len(self._sel_motivovars) else ""
                cod       = motivo_codigo.split(":")[0].strip() if ":" in motivo_codigo else motivo_codigo
                duda_val  = bool(self._sel_dudavars[idx].get()) if idx < len(self._sel_dudavars) else False
                nota_duda = self._sel_notadudavars[idx].get() if idx < len(self._sel_notadudavars) else ""
                fases_val = self._sel_fasesvars[idx] if idx < len(self._sel_fasesvars) else None
                fila = {c: est.get(c, "") for c in self._sel_campos if not c.startswith("_")}
                fila["Motivo"]               = motivo_codigo
                fila["Codigo_Criterio"]      = cod
                fila["Duda"]                 = "Si" if duda_val else "No"
                fila["Nota_Duda"]            = nota_duda
                fila["CI_3_Titulo"]          = "Si" if fases_val and fases_val["ci3"].get() else "No"
                fila["CI_4_Abstract"]        = "Si" if fases_val and fases_val["ci4"].get() else "No"
                fila["CI_5_Lectura_Completa"]= "Si" if fases_val and fases_val["ci5"].get() else "No"
                fila["Fase_PRISMA"]          = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
                eliminados.append(fila)

        if not eliminados:
            messagebox.showinfo("Sin eliminados",
                                "No hay estudios marcados para eliminar.")
            return

        nombre_def = f"eliminados_{self._sel_motor.replace(' ', '_')}.csv"
        out = filedialog.asksaveasfilename(
            title="Guardar CSV de eliminados",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=nombre_def,
            initialdir=self._sel_dir or ".")
        if not out:
            return

        campos_out = [c for c in self._sel_campos if not c.startswith("_")]
        campos_out += ["Motivo", "Codigo_Criterio", "Duda", "Nota_Duda",
                       "CI_3_Titulo", "CI_4_Abstract", "CI_5_Lectura_Completa", "Fase_PRISMA"]
        try:
            with open(out, "w", encoding="utf-8", newline="") as f:
                w = cs.DictWriter(f, fieldnames=campos_out, extrasaction="ignore")
                w.writeheader()
                w.writerows(eliminados)
            messagebox.showinfo("Exportado",
                                f"{len(eliminados)} estudios eliminados guardados en:\n{out}")
            self._set_status(f"Eliminados exportados: {os.path.basename(out)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    # ------------------------------------------------------------------ EXPORTAR ACEPTADOS (NUEVO)

    def _sel_exportar_aceptados(self):
        """Exporta los estudios NO eliminados (aceptados) a un CSV."""
        if not self._sel_estudios:
            messagebox.showwarning("Sin datos", "No hay estudios cargados.")
            return

        aceptados = []
        for idx, est in enumerate(self._sel_estudios):
            if idx < len(self._sel_checkvars) and self._sel_checkvars[idx].get():
                continue  # Es eliminado, saltar
            duda_val  = bool(self._sel_dudavars[idx].get()) if idx < len(self._sel_dudavars) else False
            nota_duda = self._sel_notadudavars[idx].get() if idx < len(self._sel_notadudavars) else ""
            fases_val = self._sel_fasesvars[idx] if idx < len(self._sel_fasesvars) else None
            ci3 = fases_val["ci3"].get() if fases_val else False
            ci4 = fases_val["ci4"].get() if fases_val else False
            ci5 = fases_val["ci5"].get() if fases_val else False
            n_ci = int(ci3) + int(ci4) + int(ci5)

            fila = {c: est.get(c, "") for c in self._sel_campos if not c.startswith("_")}
            fila["Estado"]               = "Aceptado"
            fila["Duda"]                 = "Si" if duda_val else "No"
            fila["Nota_Duda"]            = nota_duda
            fila["CI_3_Titulo"]          = "Si" if ci3 else "No"
            fila["CI_4_Abstract"]        = "Si" if ci4 else "No"
            fila["CI_5_Lectura_Completa"]= "Si" if ci5 else "No"
            fila["CI_Aprobados"]         = f"{n_ci}/3"
            fila["Origen"]               = est.get("_origen", "csv")
            fila["Fase_PRISMA"]          = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
            aceptados.append(fila)

        if not aceptados:
            messagebox.showinfo("Sin aceptados",
                                "No hay estudios aceptados (todos están marcados para eliminar).")
            return

        nombre_def = f"aceptados_{self._sel_motor.replace(' ', '_')}.csv"
        out = filedialog.asksaveasfilename(
            title="Guardar CSV de aceptados",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=nombre_def,
            initialdir=self._sel_dir or ".")
        if not out:
            return

        campos_out = [c for c in self._sel_campos if not c.startswith("_")]
        campos_out += ["Estado", "Duda", "Nota_Duda",
                       "CI_3_Titulo", "CI_4_Abstract", "CI_5_Lectura_Completa",
                       "CI_Aprobados", "Origen", "Fase_PRISMA"]
        try:
            with open(out, "w", encoding="utf-8", newline="") as f:
                w = cs.DictWriter(f, fieldnames=campos_out, extrasaction="ignore")
                w.writeheader()
                w.writerows(aceptados)
            messagebox.showinfo("Exportado",
                                f"{len(aceptados)} estudios aceptados guardados en:\n{out}")
            self._set_status(f"Aceptados exportados: {os.path.basename(out)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")
            
    # =================================================================== Exportar dudas
    
    def _sel_exportar_dudas(self):
        """Exporta los estudios marcados como duda a un CSV."""
        if not self._sel_estudios:
            messagebox.showwarning("Sin datos", "No hay estudios cargados.")
            return

        dudas = []
        for idx, est in enumerate(self._sel_estudios):
            # Leer desde widgets si están disponibles, si no desde el dict
            if idx < len(self._sel_dudavars) and self._sel_dudavars[idx] is not None:
                es_duda   = bool(self._sel_dudavars[idx].get())
                nota_duda = self._sel_notadudavars[idx].get() if idx < len(self._sel_notadudavars) else ""
                eliminado = bool(self._sel_checkvars[idx].get()) if idx < len(self._sel_checkvars) else False
                motivo    = self._sel_motivovars[idx].get() if idx < len(self._sel_motivovars) else ""
                fases_val = self._sel_fasesvars[idx] if idx < len(self._sel_fasesvars) else None
                ci3 = bool(fases_val["ci3"].get()) if fases_val else False
                ci4 = bool(fases_val["ci4"].get()) if fases_val else False
                ci5 = bool(fases_val["ci5"].get()) if fases_val else False
            else:
                estado    = self._sel_estado_fase(est)
                es_duda   = estado.get("duda", False)
                nota_duda = estado.get("nota_duda", "")
                eliminado = estado.get("eliminado", False)
                motivo    = estado.get("motivo", "")
                fases_v   = estado.get("fases", {})
                ci3 = fases_v.get("ci3", False)
                ci4 = fases_v.get("ci4", False)
                ci5 = fases_v.get("ci5", False)

            if not es_duda:
                continue

            fila = {c: est.get(c, "") for c in self._sel_campos if not c.startswith("_")}
            fila["Nota_Duda"]             = nota_duda
            fila["Estado"]                = "Eliminado" if eliminado else "Aceptado"
            fila["Motivo_Exclusion"]      = motivo
            fila["CI_3_Titulo"]           = "Si" if ci3 else "No"
            fila["CI_4_Abstract"]         = "Si" if ci4 else "No"
            fila["CI_5_Lectura_Completa"] = "Si" if ci5 else "No"
            fila["Origen"]                = est.get("_origen", "csv")
            fila["Fase_PRISMA"]           = FASES.get(self._sel_fase_actual, self._sel_fase_actual)
            dudas.append(fila)

        if not dudas:
            messagebox.showinfo("Sin dudas",
                                "No hay estudios marcados como duda en esta fase.")
            return

        nombre_def = f"dudas_{self._sel_motor.replace(' ', '_')}.csv"
        out = filedialog.asksaveasfilename(
            title="Guardar CSV de dudas",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=nombre_def,
            initialdir=self._sel_dir or ".")
        if not out:
            return

        campos_base = [c for c in self._sel_campos if not c.startswith("_")]
        campos_out  = campos_base + [
            "Nota_Duda", "Estado", "Motivo_Exclusion",
            "CI_3_Titulo", "CI_4_Abstract", "CI_5_Lectura_Completa",
            "Origen", "Fase_PRISMA"
        ]

        try:
            with open(out, "w", encoding="utf-8", newline="") as f:
                w = cs.DictWriter(f, fieldnames=campos_out, extrasaction="ignore")
                w.writeheader()
                w.writerows(dudas)
            messagebox.showinfo("Exportado",
                                f"{len(dudas)} estudio(s) en duda guardados en:\n{out}")
            self._set_status(f"Dudas exportadas: {os.path.basename(out)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    # ================================================================== BUILD TAB ANALIZADOR

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=ACCENT)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        tk.Label(hdr,
                 text="  Analizador de Resultados de Busqueda de Articulos",
                 font=("Segoe UI", 13, "bold"), fg="white", bg=ACCENT,
                 anchor="w", pady=10).grid(row=0, column=0, sticky="ew", padx=12)

    def _build_archivos(self, parent):
        ca = make_card(parent, row=1, pady=(12, 4))
        ca.grid_columnconfigure(1, weight=1)

        tk.Label(ca, text="Archivos CSV", font=FT,
                 bg=CARD, fg=TEXT).grid(row=0, column=0, columnspan=4,
                                        sticky="w", padx=14, pady=(10, 4))
        self.btnSelec = make_btn(ca, "Agregar CSV(s)", self.seleccionArchivo)
        self.btnSelec.grid(row=1, column=0, padx=(14, 6), pady=6, sticky="w")
        self.btnRIS = make_btn(ca, "Convertir RIS a CSV",
                               self.convertidorRI, bg="#6366F1")
        self.btnRIS.grid(row=1, column=1, padx=6, pady=6, sticky="w")
        self.btnBIB = make_btn(ca, "Convertir BIB a CSV",
                               self.convertidorBIB, bg="#8B5CF6")
        self.btnBIB.grid(row=1, column=2, padx=6, pady=6, sticky="w")
        make_btn(ca, "Limpiar todo", self.limpiarSeleccion,
                 bg="#94A3B8", fg=TEXT).grid(row=1, column=3, padx=(6, 14), pady=6, sticky="e")

        tk.Label(ca, text="Puedes seleccionar varios archivos a la vez (Ctrl/Shift+clic).",
                 font=FS, bg=CARD, fg=MUTED, anchor="w").grid(
            row=2, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 2))
        self.lblArchivos = tk.Label(ca, text="Sin archivos seleccionados",
                                    font=FS, bg=CARD, fg=MUTED, anchor="w")
        self.lblArchivos.grid(row=3, column=0, columnspan=4,
                              sticky="ew", padx=14, pady=(0, 2))

        fl = tk.Frame(ca, bg=CARD)
        fl.grid(row=4, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 4))
        fl.grid_columnconfigure(0, weight=1)
        self.listaArchivos = tk.Listbox(fl, height=3, bg="#F8FAFC", fg=TEXT, font=FS,
                                        relief=tk.FLAT, highlightthickness=1,
                                        highlightbackground=BORDER,
                                        selectbackground=ACCENT, selectforeground="white", bd=0)
        self.listaArchivos.grid(row=0, column=0, sticky="ew")
        sb = tk.Scrollbar(fl, orient="vertical", command=self.listaArchivos.yview)
        self.listaArchivos.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")

        tk.Label(ca, text="Clic derecho sobre un archivo para eliminarlo de la lista.",
                 font=FS, bg=CARD, fg=MUTED).grid(
            row=5, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 8))

        self._menu_arch = tk.Menu(self.ventana, tearoff=0)
        self._menu_arch.add_command(label="Eliminar archivo seleccionado",
                                    command=self._eliminar_archivo_seleccionado)
        self.listaArchivos.bind("<Button-3>", lambda e: self._mostrar_menu_arch(e))

    def _build_analizar(self, parent):
        make_sep(parent, 2)
        bf = tk.Frame(parent, bg=BG)
        bf.grid(row=3, column=0, sticky="ew", padx=16, pady=6)
        bf.grid_columnconfigure(0, weight=1)
        make_btn(bf, "Analizar archivos", self.Buscador, bg=SUCCESS).grid(
            row=0, column=0, sticky="ew")
        tk.Label(bf,
                 text="El formato se detecta automaticamente  (IEEE  /  Science Direct  /  ACM Digital)",
                 font=FS, bg=BG, fg=MUTED).grid(row=1, column=0, pady=(2, 0))

    def _build_buscador_doi(self, parent):
        make_sep(parent, 4)
        cd = make_card(parent, row=5, pady=(4, 4))
        cd.grid_columnconfigure(1, weight=1)

        th = tk.Frame(cd, bg=CARD)
        th.grid(row=0, column=0, columnspan=4, sticky="ew", padx=14, pady=(10, 6))
        tk.Label(th, text="Buscar DOI especifico", font=FT, bg=CARD, fg=TEXT).pack(side="left")
        self.badge = tk.Label(th, text="  0 busquedas  ", font=FS,
                              bg=BADGE_BG, fg=BADGE_FG, padx=6, pady=2)
        self.badge.pack(side="left", padx=(10, 0))
        self.badge_encontrados = tk.Label(th, text="  0 agregados a resultados  ",
                                          font=FS, bg="#F0FDF4", fg=TEAL, padx=6, pady=2)
        self.badge_encontrados.pack(side="left", padx=(6, 0))

        tk.Label(cd, text="DOI:", font=FLB, bg=CARD, fg=TEXT).grid(
            row=1, column=0, padx=(14, 6), pady=6, sticky="w")
        self.entradaDoi = ttk.Combobox(cd, font=FM, values=[])
        self.entradaDoi.grid(row=1, column=1, padx=6, pady=6, sticky="ew", ipady=4)
        self.entradaDoi.bind('<Return>', lambda _: self.buscarDoiEspecifico())
        make_btn(cd, "Buscar", self.buscarDoiEspecifico).grid(
            row=1, column=2, padx=6, pady=6, sticky="e")
        self.btnCopiarDoi = make_btn(cd, "Copiar resultado",
                                     self._copiar_resultado_doi, bg="#64748B")
        self.btnCopiarDoi.grid(row=1, column=3, padx=(0, 14), pady=6, sticky="e")
        self.btnCopiarDoi.config(state=tk.DISABLED)

        self.panelDoi = tk.Frame(cd, bg="#F8FAFC",
                                 highlightthickness=1, highlightbackground=BORDER)
        self.panelDoi.grid(row=2, column=0, columnspan=4,
                           sticky="ew", padx=14, pady=(0, 10))
        self.panelDoi.grid_columnconfigure(0, weight=1)
        fr_doi, self.txtDoi = make_scrolled_text(self.panelDoi, height=5,
                                                 font=FM, bg="#F8FAFC", fg=TEXT)
        fr_doi.grid(row=0, column=0, sticky="ew")
        self.txtDoi.config(state=tk.DISABLED)

    def _build_resultados(self, parent):
        make_sep(parent, 6)
        rh = tk.Frame(parent, bg=BG)
        rh.grid(row=7, column=0, sticky="ew", padx=16, pady=(4, 0))
        rh.grid_columnconfigure(0, weight=1)
        tk.Label(rh, text="Resultados del analisis",
                 font=FT, bg=BG, fg=TEXT).pack(side="left")
        self.lblStats = tk.Label(rh, text="", font=FS, bg=BG, fg=MUTED)
        self.lblStats.pack(side="right")

        cr = make_card(parent, row=8, pady=(4, 4))
        cr.grid_columnconfigure(0, weight=1)
        cr.grid_rowconfigure(0, weight=1)
        fr_res, self.resultadosTexto = make_scrolled_text(cr, height=14,
                                                          font=FM, bg=CARD, fg=TEXT)
        fr_res.grid(row=0, column=0, sticky="nsew")
        self.resultadosTexto.config(state=tk.DISABLED)

        T = self.resultadosTexto
        T.tag_config("sec",    font=("Segoe UI", 10, "bold"), foreground=ACCENT)
        T.tag_config("sec_ok", font=("Segoe UI", 10, "bold"), foreground=TEAL)
        T.tag_config("doi",    foreground=PURPLE, font=FM)
        T.tag_config("tit",    foreground=TEXT)
        T.tag_config("arc",    foreground=MUTED, font=FS)
        T.tag_config("warn",   foreground=WARN, font=("Segoe UI", 9, "bold"))
        T.tag_config("num",    foreground=ACCENT2, font=("Segoe UI", 9, "bold"))
        T.tag_config("num_ok", foreground=TEAL, font=("Segoe UI", 9, "bold"))

    def _build_acumulado(self, parent):
        make_sep(parent, 9)
        ah = tk.Frame(parent, bg=BG)
        ah.grid(row=10, column=0, sticky="ew", padx=16, pady=(4, 0))
        ah.grid_columnconfigure(0, weight=1)
        tk.Label(ah, text="Acumulado de DOIs unicos en la sesion",
                 font=FT, bg=BG, fg=TEXT).pack(side="left")
        self.lblAcumStats = tk.Label(ah, text="0 DOIs", font=FS, bg=BG, fg=MUTED)
        self.lblAcumStats.pack(side="right")
        make_btn(ah, "Limpiar acumulado", self._limpiar_acumulado,
                 bg="#94A3B8", fg=TEXT).pack(side="right", padx=(0, 12))

        ca = make_card(parent, row=11, pady=(4, 4))
        ca.grid_columnconfigure(0, weight=1)
        ca.grid_rowconfigure(0, weight=1)
        fr_ac, self.txtAcumulado = make_scrolled_text(ca, height=8,
                                                      font=FM, bg=CARD, fg=TEXT)
        fr_ac.grid(row=0, column=0, sticky="nsew")
        self.txtAcumulado.config(state=tk.DISABLED)

        A = self.txtAcumulado
        A.tag_config("doi", foreground=PURPLE, font=FM)
        A.tag_config("tit", foreground=TEXT)
        A.tag_config("arc", foreground=MUTED, font=FS)
        A.tag_config("num", foreground=ACCENT2, font=("Segoe UI", 9, "bold"))
        A.tag_config("new", foreground=SUCCESS, font=("Segoe UI", 9, "bold"))

    def _build_exportar(self, parent):
        make_sep(parent, 12)
        ef = tk.Frame(parent, bg=BG)
        ef.grid(row=13, column=0, sticky="ew", padx=16, pady=(4, 12))
        ef.grid_columnconfigure(0, weight=1)
        ef.grid_columnconfigure(1, weight=1)
        self.btnExportar = make_btn(ef, "Exportar resultados del analisis",
                                    self.exportarResultados, bg="#0F172A")
        self.btnExportar.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btnExportar.config(state=tk.DISABLED)
        self.btnExportarAcum = make_btn(ef, "Exportar acumulado de DOIs",
                                        self._exportar_acumulado, bg="#334155")
        self.btnExportarAcum.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.btnExportarAcum.config(state=tk.DISABLED)

    def _build_statusbar(self):
        self.statusbar = tk.Label(self.ventana, text="Listo.",
                                  font=FS, bg=STATUS_BG, fg="#94A3B8",
                                  anchor="w", padx=12, pady=4)
        self.statusbar.pack(side="bottom", fill="x")

    # ================================================================== ESTADO

    def _set_status(self, msg):
        self.statusbar.config(text=msg)

    def _doi_color(self, modo):
        paleta = {"ok": ("#F0FDF4", "#BBF7D0"),
                  "warn": ("#FFFBEB", "#FDE68A"),
                  "empty": ("#F8FAFC", BORDER)}
        bg, br = paleta.get(modo, paleta["empty"])
        self.panelDoi.config(bg=bg, highlightbackground=br)
        self.txtDoi.config(bg=bg)

    def _upd_badge(self):
        n = self._n_busq_doi
        self.badge.config(text=f"  {n} busqueda{'s' if n != 1 else ''}  ")

    def _upd_badge_encontrados(self):
        n = self._n_encontrados
        self.badge_encontrados.config(
            text=f"  {n} agregado{'s' if n != 1 else ''} a resultados  ")

    # ================================================================== ARCHIVOS

    def seleccionArchivo(self, _=None):
        rutas = filedialog.askopenfilenames(
            title="Seleccionar CSV(s)", filetypes=[("CSV", "*.csv")], initialdir=".")
        if not rutas:
            return
        nuevos = 0
        for ruta in rutas:
            if ruta not in self.archivoRuta:
                self.archivoRuta.append(ruta)
                nuevos += 1
        if nuevos:
            self._upd_lista()
            self._bloquear("CSV")
            self._set_status(f"{nuevos} archivo(s) CSV agregado(s).")

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
        self._dois_buscados = {}
        self._n_encontrados = 0
        self._upd_badge_encontrados()
        self._set_status("Seleccion limpiada.")

    def _upd_lista(self):
        self.listaArchivos.delete(0, tk.END)
        n = len(self.archivoRuta)
        if n == 0:
            self.lblArchivos.config(text="Sin archivos seleccionados", fg=MUTED)
        else:
            self.lblArchivos.config(
                text=f"{n} archivo{'s' if n != 1 else ''} seleccionado{'s' if n != 1 else ''}",
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
        rutas = filedialog.askopenfilenames(
            title="Seleccionar RIS(s)", filetypes=[("RIS", "*.ris")], initialdir=".")
        if not rutas:
            return
        convertidos = []
        for f in rutas:
            nombre = os.path.basename(f)
            try:
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
                        w.writerow({c: ' ; '.join(ref.get(c, [])) for c in ordenCampos})
                if csv_ruta not in self.archivoRuta:
                    self.archivoRuta.append(csv_ruta)
                convertidos.append(csv_nombre)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo convertir {nombre}:\n{e}")
        if convertidos:
            self._upd_lista()
            self._bloquear("RIS")
            messagebox.showinfo("Conversion lista",
                                "Archivos CSV creados:\n\n" + "\n".join(convertidos))
            self._set_status(f"{len(convertidos)} archivo(s) RIS convertido(s).")

    def convertidorBIB(self):
        rutas = filedialog.askopenfilenames(
            title="Seleccionar BIB(s)", filetypes=[("BIB", "*.bib")], initialdir=".")
        if not rutas:
            return
        convertidos = []
        for f in rutas:
            nombre   = os.path.basename(f)
            csv_ruta = os.path.join(os.path.dirname(f), f"{nombre[:-4]}.csv")
            try:
                with open(f, 'r', encoding='utf-8') as ar:
                    bib = bibtexparser.load(ar)
                if not bib.entries:
                    messagebox.showwarning("Archivo vacio", f"No hay entradas en:\n{nombre}")
                    continue
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
                if csv_ruta not in self.archivoRuta:
                    self.archivoRuta.append(csv_ruta)
                convertidos.append(f"{nombre[:-4]}.csv")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo convertir {nombre}:\n{e}")
        if convertidos:
            self._upd_lista()
            self._bloquear("BIB")
            messagebox.showinfo("Conversion lista",
                                "Archivos CSV creados:\n\n" + "\n".join(convertidos))
            self._set_status(f"{len(convertidos)} archivo(s) BIB convertido(s).")

    # ================================================================== ANALISIS

    def _detectar_motor(self, ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                campos = [c.strip().lower() for c in (cs.DictReader(f).fieldnames or [])]
            if "document title" in campos or "publication title" in campos:
                return "IEEE"
            if ("entrytype" in campos
                    or ("abstract" in campos and "title" in campos and "doi" in campos)):
                return "ACM"
            if "ti" in campos or "t1" in campos or "source title" in campos:
                return "SD"
            return "IEEE"
        except Exception:
            return "IEEE"

    def Buscador(self):
        if not self.archivoRuta:
            messagebox.showwarning("Sin archivos", "Selecciona al menos un archivo CSV.")
            return
        motor = self._detectar_motor(self.archivoRuta[0])
        campos_titulo = {
            "IEEE": ["Document Title", "Title", "title"],
            "SD":   ["TI", "T1", "Title", "title", "Source Title"],
            "ACM":  ["title", "Title"],
        }.get(motor, ["title", "Title", "Document Title"])
        self._set_status(f"Analizando con perfil: {motor} ...")
        self._analizarMultiple(self.archivoRuta, campos_titulo)

    def _analizarMultiple(self, archivos, poCampos):
        self.doi_repetidos = {}
        self.doi_unicos    = {}
        agrupado = defaultdict(lambda: {"titulos": [], "archivos": []})
        archivos_sin_doi   = []

        for ruta in archivos:
            nombre = os.path.basename(ruta)
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    leer     = cs.DictReader(f)
                    campos   = leer.fieldnames or []
                    campoDoi = _hallar_campo_doi(campos)
                    if not campoDoi:
                        archivos_sin_doi.append(nombre)
                        continue
                    campoTit = None
                    for cand in poCampos:
                        campoTit = next(
                            (c for c in campos if cand.lower() in c.strip().lower()), None)
                        if campoTit:
                            break
                    if not campoTit:
                        campoTit = campos[0] if campos else None
                    for fila in leer:
                        doi = fila.get(campoDoi, '').strip()
                        tit = fila.get(campoTit, '').strip() if campoTit else 'Sin titulo'
                        if _es_doi_valido(doi):
                            agrupado[doi]["titulos"].append(tit)
                            agrupado[doi]["archivos"].append(nombre)
            except Exception as e:
                messagebox.showerror("Error de lectura", f"No se pudo leer {nombre}:\n{e}")

        if archivos_sin_doi:
            messagebox.showwarning(
                "Campo DOI no encontrado",
                "Los siguientes archivos no tienen una columna DOI reconocible "
                "y fueron omitidos:\n\n" + "\n".join(archivos_sin_doi))

        for doi, d in agrupado.items():
            if len(d["titulos"]) > 1:
                self.doi_repetidos[doi] = d
            else:
                self.doi_unicos[doi] = {"titulo": d["titulos"][0], "archivo": d["archivos"][0]}

        self._mostrarResultados()
        self._actualizar_acumulado()
        self.btnExportar.config(state=tk.NORMAL)
        self._set_status(
            f"Analisis completo: {len(self.doi_unicos)} unicos, {len(self.doi_repetidos)} repetidos.")

    # ================================================================== MOSTRAR

    def _mostrarResultados(self):
        T = self.resultadosTexto
        T.config(state=tk.NORMAL)
        T.delete(1.0, tk.END)

        if not self.doi_repetidos and not self.doi_unicos and not self._dois_buscados:
            T.insert(tk.END, "No se encontraron articulos.\n")
            T.config(state=tk.DISABLED)
            return

        total = len(self.doi_repetidos) + len(self.doi_unicos)
        extra = len(self._dois_buscados)
        self.lblStats.config(
            text=(f"{total} DOIs analizados  /  {len(self.doi_repetidos)} repetidos"
                  f"  /  {len(self.doi_unicos)} unicos"
                  + (f"  /  {extra} via buscador" if extra else "")))

        T.insert(tk.END, f"DOIs REPETIDOS ({len(self.doi_repetidos)})\n", "sec")
        T.insert(tk.END, "-" * 64 + "\n")
        if not self.doi_repetidos:
            T.insert(tk.END, "  Ninguno\n\n")
        else:
            for doi, d in self.doi_repetidos.items():
                T.insert(tk.END, "  DOI: ", "arc")
                T.insert(tk.END, f"{doi}\n", "doi")
                T.insert(tk.END, f"  AVISO: aparece en {len(d['titulos'])} archivos:\n", "warn")
                for t in d["titulos"]:
                    T.insert(tk.END, f"    - {t}\n", "tit")
                T.insert(tk.END, "\n")

        T.insert(tk.END, f"DOIs UNICOS ({len(self.doi_unicos)})\n", "sec")
        T.insert(tk.END, "-" * 64 + "\n")
        if not self.doi_unicos:
            T.insert(tk.END, "  Ninguno\n\n")
        else:
            for i, (doi, d) in enumerate(self.doi_unicos.items(), 1):
                T.insert(tk.END, f"  {i:>4}. ", "num")
                T.insert(tk.END, f"{d['titulo']}\n", "tit")
                T.insert(tk.END, "         DOI: ", "arc")
                T.insert(tk.END, f"{doi}\n", "doi")
                T.insert(tk.END, f"         Archivo: {d['archivo']}\n\n", "arc")

        T.insert(tk.END,
                 f"ENCONTRADOS POR BUSQUEDA DOI ({len(self._dois_buscados)})\n", "sec_ok")
        T.insert(tk.END, "-" * 64 + "\n")
        if not self._dois_buscados:
            T.insert(tk.END,
                     "  Ninguno todavia. Usa el buscador DOI para agregar articulos aqui.\n")
        else:
            for i, (doi, d) in enumerate(self._dois_buscados.items(), 1):
                T.insert(tk.END, f"  {i:>4}. ", "num_ok")
                T.insert(tk.END, f"{d['titulo']}\n", "tit")
                T.insert(tk.END, "         DOI: ", "arc")
                T.insert(tk.END, f"{doi}\n", "doi")
                T.insert(tk.END, f"         Archivo: {d['archivo']}\n\n", "arc")

        T.config(state=tk.DISABLED)

    # ================================================================== ACUMULADO

    def _actualizar_acumulado(self):
        nuevos = 0
        for doi, d in self.doi_unicos.items():
            if doi not in self.acumulado_dois:
                self.acumulado_dois[doi] = d
                nuevos += 1
        self._renderizar_acumulado(nuevos_dois=nuevos)
        total = len(self.acumulado_dois)
        self.lblAcumStats.config(
            text=f"{total} DOI{'s' if total != 1 else ''}  (+{nuevos} nuevos en este analisis)")
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
        claves = list(self.acumulado_dois.keys())
        umbral = len(claves) - nuevos_dois
        for i, doi in enumerate(claves, 1):
            d        = self.acumulado_dois[doi]
            es_nuevo = (i - 1) >= umbral and nuevos_dois > 0
            A.insert(tk.END, f"  {i:>4}. ", "new" if es_nuevo else "num")
            if es_nuevo:
                A.insert(tk.END, "[NUEVO] ", "new")
            A.insert(tk.END, f"{d['titulo']}\n", "tit")
            A.insert(tk.END, "         DOI: ", "arc")
            A.insert(tk.END, f"{doi}\n", "doi")
            A.insert(tk.END, f"         Archivo: {d['archivo']}\n\n", "arc")
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
            messagebox.showwarning("Campo vacio", "Introduce un DOI para buscar.")
            return
        if not self.archivoRuta:
            messagebox.showwarning("Sin archivos", "Selecciona archivos primero.")
            return

        doi_n      = doi_q.lower()
        resultados = []
        for ruta in self.archivoRuta:
            nombre = os.path.basename(ruta)
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    leer     = cs.DictReader(f)
                    campos   = leer.fieldnames or []
                    campoDoi = _hallar_campo_doi(campos)
                    if not campoDoi:
                        continue
                    campoTit = None
                    for posible in ["Title", "title", "Document Title", "TI", "T1"]:
                        campoTit = next(
                            (c for c in campos if posible.lower() in c.lower()), None)
                        if campoTit:
                            break
                    if not campoTit and campos:
                        campoTit = campos[0]
                    for fila in leer:
                        df = fila.get(campoDoi, '').strip()
                        if _es_doi_valido(df):
                            if doi_n in df.lower() or df.lower() in doi_n:
                                resultados.append({
                                    "archivo": nombre, "doi": df,
                                    "titulo": (fila.get(campoTit, 'Sin titulo')
                                               if campoTit else 'Sin titulo'),
                                })
            except Exception as e:
                print(f"Error leyendo {nombre}: {e}")

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
            R.insert(tk.END, f"No se encontro el DOI en los archivos cargados.\nBuscado: {doi_q}\n")
            self.btnCopiarDoi.config(state=tk.DISABLED)
        elif len(resultados) > 1:
            self._doi_color("warn")
            R.insert(tk.END, f"DOI REPETIDO -- encontrado en {len(resultados)} ubicaciones\n\n")
            for i, r in enumerate(resultados, 1):
                R.insert(tk.END, f"  {i}. {r['titulo']}\n")
                R.insert(tk.END, f"     DOI:     {r['doi']}\n")
                R.insert(tk.END, f"     Archivo: {r['archivo']}\n\n")
            self.btnCopiarDoi.config(state=tk.NORMAL)
            self._registrar_doi_buscado(resultados[0])
        else:
            self._doi_color("ok")
            r = resultados[0]
            R.insert(tk.END, "DOI encontrado\n\n")
            R.insert(tk.END, f"  Titulo:  {r['titulo']}\n")
            R.insert(tk.END, f"  DOI:     {r['doi']}\n")
            R.insert(tk.END, f"  Archivo: {r['archivo']}\n")
            self.btnCopiarDoi.config(state=tk.NORMAL)
            self._registrar_doi_buscado(r)
        R.config(state=tk.DISABLED)
        self._set_status(
            f"Busqueda '{doi_q}': {len(resultados)} resultado{'s' if len(resultados) != 1 else ''}.")

    def _registrar_doi_buscado(self, resultado):
        doi = resultado["doi"]
        if doi not in self._dois_buscados:
            self._dois_buscados[doi] = {"titulo": resultado["titulo"], "archivo": resultado["archivo"]}
            self._n_encontrados += 1
            self._upd_badge_encontrados()
        self._mostrarResultados()
        self.btnExportar.config(state=tk.NORMAL)

    def _copiar_resultado_doi(self):
        contenido = self.txtDoi.get("1.0", tk.END).strip()
        if contenido:
            self.ventana.clipboard_clear()
            self.ventana.clipboard_append(contenido)
            self._set_status("Resultado DOI copiado al portapapeles.")

    # ================================================================== EXPORTAR

    def exportarResultados(self):
        if not self.doi_unicos and not self.doi_repetidos and not self._dois_buscados:
            messagebox.showwarning("Sin datos", "No hay resultados para exportar.")
            return
        out = filedialog.asksaveasfilename(
            title="Guardar resultados", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], initialdir=".")
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
            for i, (doi, d) in enumerate(self._dois_buscados.items(), 1):
                w.writerow([i, d["titulo"], doi, d["archivo"], "Encontrado por busqueda"])
        messagebox.showinfo("Exportado", f"Resultados guardados en:\n\n{out}")
        self._set_status(f"Exportado: {os.path.basename(out)}")

    def _exportar_acumulado(self):
        if not self.acumulado_dois:
            messagebox.showwarning("Sin datos", "El acumulado esta vacio.")
            return
        out = filedialog.asksaveasfilename(
            title="Guardar acumulado", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], initialdir=".")
        if not out:
            return
        with open(out, 'w', encoding='utf-8', newline='') as f:
            w = cs.writer(f)
            w.writerow(["#", "Titulo", "DOI", "Archivo"])
            for i, (doi, d) in enumerate(self.acumulado_dois.items(), 1):
                w.writerow([i, d["titulo"], doi, d["archivo"]])
        messagebox.showinfo("Exportado", f"Acumulado guardado en:\n\n{out}")
        self._set_status(f"Acumulado exportado: {os.path.basename(out)}")

    # ================================================================== BLOQUEO

    def _bloquear(self, origen):
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