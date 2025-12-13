'''
Programa con interfaz grafica para analizar resultados de busqueda de distintas bases de articulos para faciltar
la seleccion de papers relevantes devolviendo el DOI de estos articulos.
'''
import tkinter as tk # libreria para interfaz grafica
from tkinter import filedialog, messagebox # libreria para dialogos de archivos y mensajes
import csv as cs # libreria para manejo de archivos csv
import os # libreria para manejo de archivos y rutas
import re # libreria para expresiones regulares
from collections import defaultdict # libreria para diccionarios con listas por defecto
import bibtexparser # libreria para manejo de archivos bibtex




class AnalizadorApp:
    # constructor de la clase
    def __init__(self):
        #-------------------------------------------
        # configuracion de la ventana principal
        self.ventana = tk.Tk() # creacion de la ventana principal
        
        self.ventana.title("Resultados Interesantes") # titulo de la ventana
        
        # centrar la ventana en la pantalla
        ancho = self.ventana.winfo_screenwidth() # obtener ancho de la pantalla
        alto = self.ventana.winfo_screenheight() # obtener alto de la pantalla
        #calculo de posicion
        pos_x = (ancho // 2) - (800 // 2) # calcular posicion en x. divide ancho de pantalla entre 2 y resta la mitad del ancho de la ventana
        pos_y = (alto // 2) - (700 // 2) # calcular posicion en y. divide alto de pantalla entre 2 y resta la mitad del alto de la ventana
        self.ventana.geometry(f"1000x900+{pos_x}+{pos_y}") # tamano y posicion inicial de la ventana sintaxis: "ANCHOxALTO+POS_X+POS_Y"
        
        #configuracion de cuadricula
        for col in range(3):
            self.ventana.grid_columnconfigure(col, weight=1) # configurar columnas de la cuadricula para que se expandan proporcionalmente
            
        self.ventana.grid_rowconfigure(10, weight=1) # configurar fila 10 para que se expanda proporcionalmente
        #-------------------------------------------
        #almacen
        self.archivoRuta = None # ruta del archivo seleccionado
        # almacen para analisis de DOI
        self.doi_repetidos = {}
        self.doi_unicos = {}    
        
        # configuracion de los elementos de la ventana
        # etiqueta con instrucciones para subir archivo
        self.textoInstrucciones = tk.Label(self.ventana, text="Analizador de Resultados de Busqueda de Articulos\nSeleccione el archivo .csv a analizar:") # etiqueta con instrucciones
        self.textoInstrucciones.config(font=("Arial", 12)) # configurar fuente de la etiqueta
        self.textoInstrucciones.config(fg="#333333") # configurar color de la fuente de la etiqueta
        self.textoInstrucciones.config(bg="#f0f0f0") # configurar color de fondo de la etiqueta
        self.textoInstrucciones.config(justify="left") # alinear texto a la izquierda
        self.textoInstrucciones.config(wraplength=480) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.textoInstrucciones.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,5), sticky="w") # posicionar la etiqueta en la ventana
        
        #mostrar archivo seleccionado
        self.textoSelec = tk.Label(self.ventana, text="Ningun archivo seleccionado") # etiqueta para mostrar archivo seleccionado
        self.textoSelec.config(font=("Arial", 10)) # configurar fuente de la etiqueta
        self.textoSelec.config(fg="#555555") # configurar color de la fuente de la etiqueta
        self.textoSelec.config(bg="#f0f0f0") # configurar color
        self.textoSelec.config(justify="left") # alinear texto a la izquierda
        self.textoSelec.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="w") # posicionar la etiqueta en la ventana
                
        # boton para seleccionar archivo
        self.botonSeleccionar = tk.Button(self.ventana, text="Seleccionar Archivo", command= self.seleccionArchivo) # boton para seleccionar archivo
        self.botonSeleccionar.grid(row=1, column=0, padx=10, pady=5, sticky="w") # posicionar el boton en la ventana
        
        #etiqueta con informacion sobre el convertidor ris a csv
        self.InformacionRis = tk.Label(self.ventana, text="Convertidor de archivos RIS a CSV para Science Direct") # etiqueta con instrucciones
        self.InformacionRis.config(font=("Arial", 10)) # configurar fuente de la etiqueta
        self.InformacionRis.config(fg="#333333") # configurar color de la fuente de la etiqueta
        self.InformacionRis.config(bg="#f0f0f0") # configurar color de fondo de la etiqueta
        self.InformacionRis.config(justify="left") # alinear texto a la izquierda
        self.InformacionRis.config(wraplength=260) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.InformacionRis.grid(row=1, column=2, padx=10, pady=5, sticky="w") # posicionar la etiqueta en la ventana
        
        #boton para convertir ris a csv
        self.botonConvertirRI = tk.Button(self.ventana, text="Convertir RIS a CSV", command= self.convertidorRI) # boton para convertir ris a csv
        self.botonConvertirRI.grid(row=1, column=2, padx=10, pady=5, sticky="e") # posicionar el boton en la ventana
        
        #etica con informacion sobre el convertidor bib a csv
        self.InformacionBib = tk.Label(self.ventana, text="Convertidor de archivos BIB a CSV para ACM Digital") # etiqueta con instrucciones
        self.InformacionBib.config(font=("Arial", 10)) # configurar fuente de la etiqueta
        self.InformacionBib.config(fg="#333333") # configurar color de la fuente de la etiqueta
        self.InformacionBib.config(bg="#f0f0f0") # configurar color
        self.InformacionBib.config(justify="left") # alinear texto a la izquierda
        self.InformacionBib.config(wraplength=260) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.InformacionBib.grid(row=2, column=2, padx=10, pady=5, sticky="w") # posicionar la etiqueta en la ventana
        
        #boton para convertir bib a csv
        self.botonConvertirBub = tk.Button(self.ventana, text="Convertir BIB a CSV", command= self.convertidorBIB) # boton para convertir bib a csv
        self.botonConvertirBub.grid(row=2, column=2, padx=10, pady=5, sticky="e") # posicionar el boton en la ventana
        
        #-------------------------------------------
        
        #boton para seleccionar el motor de busqueda del que fue extraido el archivo
        self.textoInfoInst = tk.Label(self.ventana, text="Seleccione el motor de busqueda del que fue extraido el archivo:") # etiqueta con instrucciones
        self.textoInfoInst.config(font=("Arial", 12)) # configurar fuente de la etiqueta
        self.textoInfoInst.config(fg="#333333") # configurar color de la fuente
        self.textoInfoInst.config(bg="#f0f0f0") # configurar color de fondo de la etiqueta
        self.textoInfoInst.config(justify="left") # alinear texto a la izquierda
        self.textoInfoInst.config(wraplength=480) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.textoInfoInst.grid(row=5, column=0, columnspan=3, padx=10, pady=(15,5), sticky="w") # posicionar la etiqueta en la ventana
        
        #botones de radio para seleccionar el motor de busqueda
        self.MotorVar = tk.StringVar() # variable para almacenar el motor seleccionado
        self.MotorVar.set("NULL") # valor por defecto
        self.MotorBoton = tk.Radiobutton(self.ventana, text="IEEE", value="IEEE", variable=self.MotorVar) # boton de radio para IEEE
        self.MotorBoton.grid(row=6, column=0, padx=10, pady=5, sticky="w") # posicionar el boton de radio en la ventana
        self.MotorBoton2 = tk.Radiobutton(self.ventana, text= "Science Direct", value="SD", variable=self.MotorVar) # boton de radio para Science Direct
        self.MotorBoton2.grid(row=6, column=1, padx=10, pady=5, sticky="w") # posicionar el boton de radio en la ventana
        self.MotorBoton3 = tk.Radiobutton(self.ventana, text= "ACM Digital", value="ACM", variable=self.MotorVar) # boton de radio para ACM Digital
        self.MotorBoton3.grid(row=6, column=2, padx=10, pady=5, sticky="w") # posicionar el boton de radio en la ventana
        
        
        #boton para iniciar analisis
        self.botonBusqueda = tk.Button(self.ventana, text="Escoger", command= self.Buscador) # boton para buscar articulos relevantes
        self.botonBusqueda.grid(row=7, column=0, columnspan=3, padx=10, pady=10, sticky="nsew") # posicionar el boton en la ventana
        
        #cuadro de texto para mostrar resultados
        self.resultadosTexto = tk.Text(self.ventana, height=10, width=60) # cuadro de texto para mostrar resultados
        self.resultadosTexto.grid(row=8, column=0, columnspan=3, padx=10, pady=10, sticky="nsew") # posicionar el cuadro de texto en la ventana
        self.resultadosTexto.config(state=tk.DISABLED) # deshabilitar el cuadro de texto para evitar edicion manual
        #-------------------------------------------
        
    '''
    ---------------------------------------------------
    FUNCIONES DE LA APLICACION
    ---------------------------------------------------
    '''
              
    #funcion para convertir ris a csv
    '''
    Esta funcion es para convertir archivos *.ris a *.csv, porque science direct no tiene opcion de exportar a csv directamente
    y la opcion que encontre en linea nunca lo convertio o no servia la pagina en el momento de la consulta y las otras 
    paginas tenia que crear cuenta.
    .|. science direct
    '''
    def convertidorRI(self):
        archivoRIS = filedialog.askopenfilename(title="Archivo RIS", filetypes=[("Archivos RIS","*.ris")], initialdir=".") # abrir cuadro de dialogo para seleccionar archivo ris
        
        #verifica si se selecciono un archivo
        if not archivoRIS:
            print("No se selecciono ningun archivo RIS.") # imprimir mensaje si no se selecciono ningun archivo
            return
        print(f"Archivo RIS seleccionado: {archivoRIS}") # imprimir ruta del archivo ris seleccionado
        
        nombreArchivo = os.path.basename(archivoRIS)# obtener nombre del archivo ris 
        
        with open(archivoRIS, 'r', encoding='utf-8') as ar: # abrir archivo ris
            leer = ar.read() # leer archivo ris
            
            #leer registros
            registros = re.split(r'\n(?=TY\s+-)', leer) # dividir registros por salto de linea seguido de TY  -
            
            #leer referencias
            referencias = []
            todoCam = set()
            for registro in registros:
                #omitir registros vacios
                if not registro.strip():
                    continue
                
                ref = defaultdict(list) # diccionario para almacenar campos de la referencia
                lineas = registro.strip().split('\n') # dividir registro en lineas
                
                for linea in lineas:
                    match = re.match(r'^([A-Z0-9]{2})\s+-\s+(.+)$', linea)
                    if match:
                        campo_actual, valor = match.groups()
                        ref[campo_actual].append(valor)
                        todoCam.add(campo_actual)
                    elif campo_actual and linea.strip():
                        ref[campo_actual][-1] += ' ' + linea.strip()
                
                if ref:
                    referencias.append(ref)
        
        #ordenar campos
        ordenCampos = sorted(todoCam)
        
        #crear archivo csv
        nomArchiCSV= f"{nombreArchivo[:-4]}.csv" # nombre del archivo csv
        rutaSalida = os.path.join(os.path.dirname(archivoRIS), nomArchiCSV) # ruta de salida del archivo csv
        
        with open(rutaSalida, 'w', encoding='utf-8', newline='') as archivoCSV: # abrir archivo csv para escritura
            escritor = cs.DictWriter(archivoCSV, fieldnames=ordenCampos) # crear escritor de csv
            escritor.writeheader() # escribir encabezado
            
            for ref in referencias:
                row = {campo: ' ; '.join(ref.get(campo, [])) for campo in ordenCampos} # unir valores de campos multiples con ;
                escritor.writerow(row) # escribir fila en el archivo csv
        
        
        
        #guardar archivo csv
        self.archivoRuta = rutaSalida # almacenar la ruta del archivo csv generado
        self.textoSelec.config(text=f"Archivo seleccionado: {rutaSalida}") # actualizar etiqueta con la ruta del archivo seleccionado
        #mensaje de exito
        messagebox.showinfo("Salio bien", f"Archivo CSV creado:\n\n{nomArchiCSV}")
        print(f"Archivo CSV creado: {rutaSalida}") # ver si funciona
        self.bloqueoboton("RIS") # bloquear botones de conversion
    
    #funcion para convertir bib a csv
    '''
    Esta funcion es para convertir archivos *.bib a *.csv porque tambien acm digital no tiene opcion de exportar a csv directamente
    .|. acm digital
    '''
    
    def convertidorBIB(self):
        archivoBib = filedialog.askopenfilename(title="Archivo BIB", filetypes=[("Archivos BIB","*.bib")], initialdir=".") # abrir cuadro de dialogo para seleccionar archivo bib
        
        #verifica si se selecciono un archivo
        if not archivoBib:
            print("No se selecciono ningun archivo BIB.") # imprimir mensaje si no se selecciono ningun archivo
            return
        print(f"Archivo BIB seleccionado: {archivoBib}") # imprimir ruta del archivo bib seleccionado
        
        nombreArchivo = os.path.basename(archivoBib)# obtener nombre del archivo bib
        rutaArchivo = os.path.dirname(archivoBib) # obtener ruta del archivo bib
        rutaCsv = os.path.join(rutaArchivo, f"{nombreArchivo[:-4]}.csv") # ruta del archivo csv de salida
        
        with open(archivoBib, 'r', encoding='utf-8') as ar: # abrir archivo bib
            bibLei = bibtexparser.load(ar) # leer archivo bib
            
            #verificar si hay entradas
            if not bibLei.entries:
                print("No se encontraron entradas en el archivo BIB.") # imprimir mensaje si no se encontraron entradas
                return
            
            #recoler campos
            todoCam = set()
            for entrada in bibLei.entries:
                todoCam.update(entrada.keys())
            
            campos = list(todoCam) # lista de campos
            camposOrdenados = []
            
            #ordenar campos
            for fijo in ["ID", "ENTRYTYPE"]:
                if fijo in campos:
                    camposOrdenados.append(fijo)
                    campos.remove(fijo)
            camposOrdenados.extend(sorted(campos)) # agregar campos restantes en orden alfabetico
            
        #crear archivo csv
        with open(rutaCsv, "w", encoding='utf-8') as esc:
            escrito = cs.DictWriter(esc, fieldnames=camposOrdenados) # crear escritor de csv
            escrito.writeheader() # escribir encabezado
            for entrada in bibLei.entries:
                escrito.writerow(entrada) # escribir fila en el archivo csv
        
        #guardar archivo csv
        self.archivoRuta = rutaCsv
        self.textoSelec.config(text=f"Archivo seleccionado: {rutaCsv}")
        #mensaje de exito
        messagebox.showinfo("Salio bien", f"Archivo CSV creado:\n\n{nombreArchivo[:-4]}.csv")
        print(f"Archivo CSV creado: {rutaCsv}") # ver si funciona
        self.bloqueoboton("BIB") # bloquear botones de conversion
        
            
            
            
    
    #funcion para seleccionar archivo CSV
    def seleccionArchivo(self, evento=None):
        archivoRuta = filedialog.askopenfilename(title="Archivo CSV", filetypes=[("Archivos CSV","*.csv")], initialdir=".") # abrir cuadro de dialogo para seleccionar archivo
        if archivoRuta:
            self.archivoRuta = archivoRuta # almacenar la ruta del archivo seleccionado
            print(f"Archivo seleccionado: {archivoRuta}") # imprimir ruta del archivo seleccionado
            self.bloqueoboton("CSV") # bloquear botones de conversion
            
    
        
    # funcion para buscar articulos relevantes
    def Buscador(self):
        #validaciones
        
        # verificar que se haya seleccionado un archivo
        if not self.archivoRuta:
            print("Error: No se ha seleccionado un archivo.") # imprimir mensaje de error
            return

        
        # obtener el motor de busqueda seleccionado
        motorBusqueda = self.MotorVar.get()
        if motorBusqueda == "NULL":
            print("Error: No se ha seleccionado un motor de busqueda.") # imprimir mensaje de error
            return
        

        #chequeo
        print("Buscando :)") # imprimir mensaje de busqueda (ver si jala el boton)
        print(f"Motor de busqueda seleccionado: {motorBusqueda}") # imprimir motor de busqueda seleccionado (ver si jala el boton)
        print(f"Archivo a analizar: {self.archivoRuta}") # imprimir archivo a analizar (ver si jala el boton)
        
        #llamar a la funcion para analizar el archivo
        self.analizarArchivo(self.archivoRuta, motorBusqueda)
        
        
    #funcion para analizar el archivo seleccionado
    def analizarArchivo(self, archivoRuta, motorBusqueda):
        match motorBusqueda:
            case "IEEE":
                self.analizarIEEE(archivoRuta)
            case "SD":
                self.analizarSD(archivoRuta)
                
            case "ACM":
                self.analizarACM(archivoRuta)
            case _:
                print("Error: Motor de busqueda no reconocido.") # imprimir mensaje de error
                return

    
    def analizisDoi(self, archivoRuta,poCampos= None):
        if poCampos is None:
            poCampos = []
            
        self.doi_repetidos = {}
        self.doi_unicos = {}
        
        # leer archivo csv
        with open(archivoRuta, 'r', encoding='utf-8') as archivoCSV: # abrir archivo csv
            leer = cs.DictReader(archivoCSV) # leer archivo csv como diccionario
            campos = leer.fieldnames or [] # obtener nombres de los campos
            
            campoDoi = None
           
            for c in campos:
                c_limpio = c.strip().lower()
                if c_limpio == 'doi' or c_limpio == 'do' or 'doi' in c_limpio:
                    campoDoi = c
                    break
            if not campoDoi:
                messagebox.showerror("Error", "No se encontro un campo DOI en el archivo CSV.")
                return
            
            campoTitulo = None
            for candidato in poCampos:
                for c in campos:
                    c_limpio = c.strip()
                    if c_limpio.lower() == candidato.lower() or candidato.lower() in c_limpio.lower():
                        campoTitulo = c
                        break
                if campoTitulo:
                    break
            
            #campo titulo por defecto
            if not campoTitulo:
                campoTitulo = campos[0] if campos else None
            
            agrupado = defaultdict(list)
            
            #leer filas y agrupar por doi
            for fila in leer:
                doi = fila.get(campoDoi, '').strip()
                titulo = fila.get(campoTitulo, '').strip() if campoTitulo else 'Titulo Desconocido'
                
                if doi:
                    agrupado[doi].append(titulo)
        
        #separar doi unicos y repetidos
        self.doi_repetidos = {doi: titulos for doi, titulos in agrupado.items() if len(titulos) > 1}
        self.doi_unicos = {doi: titulos[0] for doi, titulos in agrupado.items() if len(titulos) == 1}
        
        self.articulosRelevantes = []
        for doi, titulo in self.doi_unicos.items():
            self.articulosRelevantes.append({
                'titulo': titulo,
                'doi': doi
            })
            
        self.mostrarResultados()
    #archivo de IEEE
    def analizarIEEE(self, archivoRuta):
        
        self.analizisDoi(archivoRuta, poCampos=["Title", "Document Title", "title"])
        
        
    #archivo de science direct
    def analizarSD(self, archivoRuta):
        self.analizisDoi(archivoRuta, poCampos=["TI", "T1", "Title", "title"])
        
    #archivo de acm digital
    def analizarACM(self, archivoRuta):
       self.analizisDoi(archivoRuta, poCampos=["Title", "Document Title", "title"])
        
    #funcion para mostrar resultados en la interfaz grafica
    def mostrarResultados(self):
        self.resultadosTexto.config(state=tk.NORMAL) # habilitar el cuadro de texto para edicion
        self.resultadosTexto.delete(1.0, tk.END) # limpiar el cuadro de texto
        
        if not self.doi_repetidos and not self.doi_unicos:
            self.resultadosTexto.insert(tk.END, "No se encontraron articulos en el archivo seleccionado.\n")
            self.resultadosTexto.config(state=tk.DISABLED) # deshabilitar el cuadro de texto para evitar edicion manual
            return
        
        #mostrar articulos repetidos
        self.resultadosTexto.insert(tk.END, "Articulos con DOI Repetidos:\n")
        if not self.doi_repetidos:
            self.resultadosTexto.insert(tk.END, "  Ninguno\n")
        else:
            for doi, titulos in self.doi_repetidos.items():
                self.resultadosTexto.insert(tk.END, f"  DOI: {doi}\n")
                for titulo in titulos:
                    self.resultadosTexto.insert(tk.END, f"    Titulo: {titulo}\n")
                self.resultadosTexto.insert(tk.END, "\n")
        
        #mostrar articulos unicos
        self.resultadosTexto.insert(tk.END, "Articulos con DOI Unicos:\n")
        if not self.doi_unicos:
            self.resultadosTexto.insert(tk.END, "  Ninguno\n")
        else:
            for doi, titulo in self.doi_unicos.items():
                self.resultadosTexto.insert(tk.END, f"  Titulo: {titulo}\n")
                self.resultadosTexto.insert(tk.END, f"    DOI: {doi}\n\n")

    
    def bloqueoboton (self,origen):
        match origen:
            case "CSV":
                self.botonConvertirRI.config(state=tk.DISABLED)
                self.botonConvertirBub.config(state=tk.DISABLED)
            case "RIS":
                self.botonSeleccionar.config(state=tk.DISABLED)
                self.botonConvertirBub.config(state=tk.DISABLED)
                
            case "BIB":
                self.botonSeleccionar.config(state=tk.DISABLED)
                self.botonConvertirRI.config(state=tk.DISABLED)
            case _:
                print("Error: Opcion no valida para bloquear/desbloquear boton.") # imprimir mensaje de error
                return
    
#main del programa
if __name__ == "__main__":
    app = AnalizadorApp()
    app.ventana.mainloop() # iniciar el bucle principal de la interfaz grafica
