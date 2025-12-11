'''
Programa con interfaz grafica para analizar resultados de busqueda de distintas bases de articulos para faciltar
la seleccion de papers relevantes devolviendo el DOI de estos articulos.
'''
import tkinter as tk # libreria para interfaz grafica
from tkinter import filedialog # libreria para dialogos de archivos
import csv as cs # libreria para manejo de archivos csv
import os # libreria para manejo de archivos y rutas
import re # libreria para expresiones regulares

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
        self.palabrasClave = [] # lista de palabras clave agregadas
        
        # configuracion de los elementos de la ventana
        # etiqueta con instrucciones para subir archivo
        self.textoInstrucciones = tk.Label(self.ventana, text="Analizador de Resultados de Busqueda de Articulos\nSeleccione el archivo .csv a analizar:") # etiqueta con instrucciones
        self.textoInstrucciones.config(font=("Arial", 12)) # configurar fuente de la etiqueta
        self.textoInstrucciones.config(fg="#333333") # configurar color de la fuente de la etiqueta
        self.textoInstrucciones.config(bg="#f0f0f0") # configurar color de fondo de la etiqueta
        self.textoInstrucciones.config(justify="left") # alinear texto a la izquierda
        self.textoInstrucciones.config(wraplength=480) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.textoInstrucciones.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,5), sticky="w") # posicionar la etiqueta en la ventana
                
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
        
        #-------------------------------------------
        #Seccion de agregar palabras clave a la busqueda#
        # etiqueta para palabras clave
        self.textoPalabrasClave = tk.Label(self.ventana, text="Agregar Palabras Clave para Filtrar Resultados separadas por comas:") # etiqueta para palabras clave
        self.textoPalabrasClave.config(font=("Arial", 12)) # configurar fuente de la etiqueta
        self.textoPalabrasClave.config(fg="#333333") # configurar color de la fuente de la etiqueta
        self.textoPalabrasClave.config(bg="#f0f0f0") # configurar color de
        self.textoPalabrasClave.config(justify="left") # alinear texto a la izquierda
        self.textoPalabrasClave.config(wraplength=480) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.textoPalabrasClave.grid(row=3, column=0, columnspan=3, padx=10, pady=(15,5), sticky="w") # posicionar la etiqueta en la ventana
        
        # entrada para palabras clave
        self.ingestaPa = tk.Entry(self.ventana, width=50) # entrada para palabras clave
        self.ingestaPa.grid(row=4, column=0, padx=10, pady=5, sticky="we") # posicionar la entrada en la ventana
            
        # boton para agregar palabras clave
        self.botonAgregar = tk.Button(self.ventana, text="Agregar Palabras Clave", command=self.agregarPalabrasClave) # boton para agregar palabras clave
        self.botonAgregar.grid(row=4, column=2, padx=10, pady=5, sticky="w") # posicionar el boton en la ventana
        
        #boton para seleccionar el motor de busqueda del que fue extraido el archivo
        self.textoInfoInst = tk.Label(self.ventana, text="Seleccione el motor de busqueda del que fue extraido el archivo:") # etiqueta con instrucciones
        self.textoInfoInst.config(font=("Arial", 12)) # configurar fuente de la etiqueta
        self.textoInfoInst.config(fg="#333333") # configurar color de la fuente
        self.textoInfoInst.config(bg="#f0f0f0") # configurar color de fondo de la etiqueta
        self.textoInfoInst.config(justify="left") # alinear texto a la izquierda
        self.textoInfoInst.config(wraplength=480) # establecer longitud de ajuste de texto para evitar desbordamiento
        self.textoInfoInst.grid(row=5, column=0, columnspan=3, padx=10, pady=(15,5), sticky="w") # posicionar la etiqueta en la ventana
        
        
        self.MotorVar = tk.StringVar() # variable para almacenar el motor seleccionado
        self.MotorVar.set("NULL") # valor por defecto
        self.MotorBoton = tk.Radiobutton(self.ventana, text="IEEE", value="IEEE", variable=self.MotorVar) # boton de radio para IEEE
        self.MotorBoton.grid(row=6, column=0, padx=10, pady=5, sticky="w") # posicionar el boton de radio en la ventana
        
        
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
    def convertidorRI(self):
        archivoRIS = filedialog.askopenfilename(title="Archivo RIS", filetypes=[("Archivos RIS","*.ris")], initialdir=".") # abrir cuadro de dialogo para seleccionar archivo ris
        print(f"Archivo RIS seleccionado: {archivoRIS}") # imprimir ruta del archivo ris seleccionado
        nombreArchivo = os.path.basename(archivoRIS) # obtener nombre del archivo ris
        if archivoRIS:
            with open(archivoRIS, 'r', encoding='utf-8') as ar: # abrir archivo ris
                leer = ar.read() # leer archivo ris
            
            #leer registros
            registros = re.split(r'\n(?=TY\s+-)', leer) # dividir registros por salto de linea seguido de TY  -
            
            #leer referencias
            referencias = []
            todoCam = set()
            for registro in registros:
                if not referencias.strip():
                    continue
                ref = defaultdict(list) # diccionario para almacenar campos de la referencia
                lineas = registro.split('\n')
                
                for linea in lineas:
                    match = re.match(r'^([A-Z0-9]{2})\s+-\s+(.+)$', linea)
                    if match:
                        campo, valor = match.groups()
                        ref[campo].append(valor)
                        todoCam.add(campo)
                
                if ref:
                    referencias.append(ref)
        
        #ordenar campos
        ordenCampos = sorted(todoCam)
        
        #crear archivo csv
        with open(f"{nombreArchivo[:-4]}.csv", 'w', encoding='utf-8', newline='') as archivoCSV:
            escritor = cs.DictWriter(archivoCSV, fieldnames=ordenCampos) # crear escritor de csv
            escritor.writeheader() # escribir encabezado
            
            for ref in referencias:
                row = {campo: ' ; '.join(ref.get(campo, [])) for campo in ordenCampos} # unir valores de campos multiples con ;
                escritor.writerow(row) # escribir fila en el archivo csv
                        
    #funcion para convertir ris a csv
    '''
    Esta funcion es para convertir archivos *.ris a *.csv, porque science direct no tiene opcion de exportar a csv directamente
    y la opcion que encontre en linea nunca lo convertio o no servia la pagina en el momento de la consulta y las otras 
    paginas tenia que crear cuenta.
    .|. science direct
    '''
    
    #funcion para convertir bib a csv
    '''
    Esta funcion es para convertir archivos *.bib a *.csv porque tambien acm digital no tiene opcion de exportar a csv directamente
    .|. acm digital
    '''
    
    #funcion para seleccionar archivo
    def seleccionArchivo(self, evento=None):
        archivoRuta = filedialog.askopenfilename(title="Archivo CSV", filetypes=[("Archivos CSV","*.csv")], initialdir=".") # abrir cuadro de dialogo para seleccionar archivo
        if archivoRuta:
            self.archivoRuta = archivoRuta # almacenar la ruta del archivo seleccionado
            print(f"Archivo seleccionado: {archivoRuta}") # imprimir ruta del archivo seleccionado
    
    # funcion para agregar palabras clave
    def agregarPalabrasClave(self):
        texto = self.ingestaPa.get() # obtener palabras clave ingresadas
        #separar palabras clave por comas y eliminar espacios en blanco
        self.palabras = [palabra.strip() for palabra in texto.split(",") if palabra.strip()]
        print(f"Palabras clave agregadas: {self.palabras}") # imprimir palabras clave agregadas (ver si jala el boton)
        
    # funcion para buscar articulos relevantes
    def Buscador(self):
        #validaciones
        
        # verificar que se haya seleccionado un archivo
        if not self.archivoRuta:
            print("Error: No se ha seleccionado un archivo.") # imprimir mensaje de error
            return

        # verificar que se hayan agregado palabras clave
        if not self.palabras:
            print("Error: No se han agregado palabras clave.") # imprimir mensaje de error
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
        print(f"Palabras clave a usar: {self.palabras}") # imprimir palabras clave a usar (ver si jala el boton)
        
        #llamar a la funcion para analizar el archivo
        self.analizarArchivo(self.archivoRuta, self.palabras, motorBusqueda)
        
        
    #funcion para analizar el archivo seleccionado
    def analizarArchivo(self, archivoRuta, palabrasClave, motorBusqueda):
        match motorBusqueda:
            case "IEEE":
                self.analizarIEEE(archivoRuta, palabrasClave)

    
    #archivo de IEEE
    def analizarIEEE(self, archivoRuta, palabrasClave):
        
        #nombreArchivo = os.path.basename(archivoRuta) # obtener nombre del archivo
        #print(f"Analizando archivo IEEE: {nombreArchivo}") # imprimir nombre del archivo analizado 
        
        self. articulosRelevantes = [] # lista para almacenar articulos relevantes encontrados
        # por el momento para prueba solo devuelve el nombre del articulo y el doi
        
        with open(archivoRuta, 'r', encoding='utf-8') as archivoCSV: # abrir archivo csv
            leectura = cs.DictReader(archivoCSV) # leer archivo csv como diccionario
            
            for fila in leectura: # lee las columnas por nombre de encabezado
                titulo = fila.get('Document Title', '') # obtener titulo del articulo
                doi = fila.get('DOI', '') # obtener doi del articulo
                
                #almacena el resultado
                self.articulosRelevantes.append({
                    'titulo': titulo,
                    'doi': doi
                })
        #para ver si jala
        print("Articulos Relevantes Encontrados:") # imprimir mensaje de articulos relevantes encontrados
        for articulo in self.articulosRelevantes:
            print(f"Titulo: {articulo['titulo']}, DOI: {articulo['doi']}") # imprimir titulo y doi del articulo relevante found
        #mostrar resultados en la interfaz grafica
        self.mostrarResultados()
        
    #funcion para mostrar resultados en la interfaz grafica
    def mostrarResultados(self):
        self.resultadosTexto.config(state=tk.NORMAL) # habilitar el cuadro de texto para edicion
        self.resultadosTexto.delete(1.0, tk.END) # limpiar el cuadro de texto
        
        if not self.articulosRelevantes:
            self.resultadosTexto.insert(tk.END, "No se encontraron articulos relevantes.\n") # mostrar mensaje si no se encontraron articulos relevantes
        else:
            for articulo in self.articulosRelevantes:
                self.resultadosTexto.insert(tk.END, f"Titulo: {articulo['titulo']}\nDOI: {articulo['doi']}\n\n") # mostrar titulo y doi del articulo relevante found
        
        self.resultadosTexto.config(state=tk.DISABLED) # deshabilitar el cuadro de texto para evitar edicion manual

    
    
#main del programa
if __name__ == "__main__":
    app = AnalizadorApp()
    app.ventana.mainloop() # iniciar el bucle principal de la interfaz grafica
