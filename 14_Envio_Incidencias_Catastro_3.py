"""
Model Script: Preparar envío Catastro

1. UNR + 9000
2. Merge colindantes
3. Cálculo de solapes con superficie mínima definida por el usuario
4. Cálculo de huecos con superficie mínima definida por el usuario
5. Merge final Solapes + Huecos
6. Exportación automática de PDF´s por incidencia usando plantilla QPT

Name : dlh
Group : Catastro
With QGIS : 3.44
"""

# =====================================================
# CARGAS / IMPORTACIONES
# =====================================================

import os                                           # IMPORTA os PARA TRABAJAR CON RUTAS, CARPETAS Y ARCHIVOS
import math                                         # IMPORTA math PARA HACER CÁLCULOS MATEMÁTICOS

from qgis.PyQt.QtCore import QVariant               # IMPORTA QVariant PARA DEFINIR TIPOS DE CAMPOS
from qgis.PyQt.QtXml import QDomDocument            # IMPORTA QDomDocument PARA LEER ARCHIVOS XML/QPT

from qgis.core import (
    QgsProcessing,                                  # CONSTANTES DE QGIS PROCESSING
    QgsProcessingAlgorithm,                         # CLASE BASE PARA CREAR UN ALGORITMO DE PROCESSING
    QgsProcessingParameterFolderDestination,        # PARÁMETRO PARA PEDIR UNA CARPETA
    QgsProcessingParameterFeatureSource,            # PARÁMETRO PARA PEDIR UNA CAPA O TABLA
    QgsProcessingParameterFile,                     # PARÁMETRO PARA PEDIR UN ARCHIVO
    QgsProcessingParameterNumber,                   # PARÁMETRO PARA PEDIR UN NÚMERO AL USUARIO
    QgsProcessingException,                         # PERMITE LANZAR ERRORES CONTROLADOS
    QgsVectorLayer,                                 # PERMITE CARGAR CAPAS VECTORIALES
    QgsVectorFileWriter,                            # PERMITE CREAR/GUARDAR ARCHIVOS VECTORIALES
    QgsFields,                                      # PERMITE CREAR UNA ESTRUCTURA DE CAMPOS
    QgsField,                                       # PERMITE CREAR UN CAMPO
    QgsFeature,                                     # PERMITE CREAR UNA ENTIDAD/FEATURE
    QgsProject,                                     # ACCESO AL PROYECTO ACTUAL DE QGIS
    QgsPrintLayout,                                 # PERMITE CREAR/CARGAR COMPOSICIONES DE IMPRESIÓN
    QgsLayoutItemScaleBar,                          # PERMITE MANEJAR BARRAS DE ESCALA
    QgsLayoutItemLegend,                            # PERMITE MANEJAR LEYENDAS
    QgsLayoutExporter,                              # PERMITE EXPORTAR LAYOUTS A PDF
    QgsPalLayerSettings,                            # CONFIGURACIÓN DE ETIQUETAS
    QgsVectorLayerSimpleLabeling,                   # APLICA ETIQUETADO SIMPLE A UNA CAPA
    QgsTextFormat,                                  # FORMATO DEL TEXTO DE ETIQUETAS
    QgsTextBufferSettings,                          # HALO/BUFFER DE LAS ETIQUETAS
    QgsFillSymbol,                                  # SIMBOLOGÍA DE RELLENO DE POLÍGONOS
    QgsReadWriteContext,                            # CONTEXTO DE LECTURA/ESCRITURA PARA QPT
    QgsRectangle,                                   # RECTÁNGULO PARA EXTENSIONES DE MAPA
    QgsUnitTypes                                    # TIPOS DE UNIDADES: METROS, KILÓMETROS, ETC.
)

from qgis import processing                         # IMPORTA processing PARA EJECUTAR HERRAMIENTAS DE QGIS


# =====================================================
# SCRIPT PRINCIPAL
# =====================================================

class EnvioIncCatastro4(QgsProcessingAlgorithm):   # CREA LA CLASE DEL ALGORITMO DE PROCESSING

    # =====================================================
    # PARÁMETROS INTERNOS
    # =====================================================

    BASE_SHP = "BASE_SHP"                           # NOMBRE INTERNO DEL PARÁMETRO CARPETA SHP
    COLINDANCIAS = "COLINDANCIAS"                   # NOMBRE INTERNO DE LA TABLA DE COLINDANCIAS
    TABLA_TRABAJO = "TABLA_TRABAJO"                 # NOMBRE INTERNO DE LA TABLA DE MUNICIPIOS DE TRABAJO
    MUNICIPIOS_UNR = "MUNICIPIOS_UNR"               # NOMBRE INTERNO DE LA TABLA DE MUNICIPIOS CON UNR
    OUTPUT_FOLDER = "OUTPUT_FOLDER"                 # NOMBRE INTERNO DE LA CARPETA DE SALIDA
    PLANTILLA_MAPAS = "PLANTILLA_MAPAS"             # NOMBRE INTERNO DE LA PLANTILLA QPT
    SUPERFICIE_MINIMA = "SUPERFICIE_MINIMA"         # NOMBRE INTERNO DE LA SUPERFICIE MÍNIMA

    # =====================================================
    # CONFIGURACIÓN PDF / PLANTILLA
    # =====================================================

    ID_MAPA = "mapa"                                # ID DEL ELEMENTO MAPA EN LA PLANTILLA QPT
    ID_TITULO = "titulo"                            # ID DEL ELEMENTO TÍTULO EN LA PLANTILLA QPT
    ID_CAJETIN = "cajetin"                          # ID DEL ELEMENTO CAJETÍN EN LA PLANTILLA QPT
    ID_ESCALA = "escala"                            # ID DE LA BARRA DE ESCALA
    ID_CUADRO_ESCALA = "cuadro_escala"              # ID DEL RECTÁNGULO DONDE DEBE CABER LA ESCALA
    ID_LEYENDA = "leyenda"                          # ID DE LA LEYENDA
    ID_CUADRO_LEYENDA = "cuadro_leyenda"            # ID DEL RECTÁNGULO DONDE DEBE CABER LA LEYENDA

    FACTOR_MARGEN = 1.20                            # AUMENTA LA EXTENSIÓN DEL MAPA UN 20 %
    TAMANO_MINIMO = 20                              # TAMAÑO MÍNIMO DEL MAPA EN METROS
    FACTOR_ANCHO_ESCALA = 0.85                      # USA SOLO EL 85 % DEL CUADRO DE ESCALA

    # =====================================================
    # IDENTIFICADOR DEL SCRIPT
    # =====================================================

    def createInstance(self):                       # FUNCIÓN OBLIGATORIA PARA QUE QGIS CREE EL ALGORITMO
        return EnvioIncCatastro4()                  # DEVUELVE UNA NUEVA INSTANCIA DEL ALGORITMO

    def name(self):                                 # NOMBRE INTERNO DEL ALGORITMO
        return "envio_incidencias_catastro_4"       # ESTE ES EL NOMBRE QUE USA QGIS INTERNAMENTE

    def displayName(self):                          # NOMBRE VISIBLE EN LA CAJA DE HERRAMIENTAS
        return "Envio incidencias Catastro 4"       # TEXTO QUE VE EL USUARIO EN QGIS

    def group(self):                                # GRUPO VISIBLE EN PROCESSING
        return "Catastro"                           # CARPETA DONDE APARECE EL SCRIPT

    def groupId(self):                              # ID INTERNO DEL GRUPO
        return "catastro"                           # IDENTIFICADOR DEL GRUPO

    # =====================================================
    # ENTRADAS DEL TRABAJO
    # =====================================================

    def initAlgorithm(self, config=None):           # DEFINE LOS PARÁMETROS QUE APARECEN EN LA VENTANA DEL SCRIPT

        self.addParameter(QgsProcessingParameterFile(
            self.BASE_SHP,                          # PARÁMETRO INTERNO
            "Carpeta SHP base",                      # TEXTO QUE VE EL USUARIO
            behavior=QgsProcessingParameterFile.Folder #CARPETA DE ENTRADA DE ARCHIVOS SHP
        ))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.COLINDANCIAS,                      # PARÁMETRO INTERNO
            "Tabla colindancias"                    # TABLA CON MUNICIPIOS COLINDANTES
        ))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.TABLA_TRABAJO,                     # PARÁMETRO INTERNO
            "Tabla trabajo"                         # TABLA DE MUNICIPIOS A PROCESAR
        ))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.MUNICIPIOS_UNR,                    # PARÁMETRO INTERNO
            "Tabla UNR"                             # TABLA DE MUNICIPIOS QUE TIENEN UNR
        ))

        self.addParameter(QgsProcessingParameterFolderDestination(
            self.OUTPUT_FOLDER,                     # PARÁMETRO INTERNO
            "Carpeta salida FINAL"                  # CARPETA DONDE SE GUARDAN LOS RESULTADOS
        ))

        self.addParameter(QgsProcessingParameterFile(
            self.PLANTILLA_MAPAS,                   # PARÁMETRO INTERNO
            "Plantilla mapas QPT",                  # ARCHIVO QPT QUE SE USARÁ PARA LOS PDF
            behavior=QgsProcessingParameterFile.File, # INDICA QUE SE PIDE UN ARCHIVO
            extension="qpt"                         # SOLO ADMITE EXTENSIÓN QPT
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.SUPERFICIE_MINIMA,                 # PARÁMETRO INTERNO
            "Superficie mínima huecos/solapes (m²)", # TEXTO QUE VE EL USUARIO
            QgsProcessingParameterNumber.Double,    # PERMITE DECIMALES
            defaultValue=20,                        # VALOR POR DEFECTO 20 m²
            minValue=0                              # NO PERMITE VALORES NEGATIVOS
        ))

    # =====================================================
    # LIMPIAR ARCHIVO
    # INPUT: ruta de archivo
    # OUTPUT: archivo eliminado si existía
    # =====================================================

    def borrar_si_existe(self, path):               # FUNCIÓN AUXILIAR PARA BORRAR ARCHIVOS

        if os.path.exists(path):                    # COMPRUEBA SI EL ARCHIVO EXISTE
            try:                                    # INTENTA BORRARLO
                os.remove(path)                     # BORRA EL ARCHIVO
            except Exception:                       # SI NO PUEDE BORRARLO
                pass                                # CONTINÚA SIN PARAR EL SCRIPT

    # =====================================================
    # GUARDADO LIMPIO DE SOLAPES
    # INPUT: capa filtrada de solapes
    # OUTPUT: Solapes_XX_XXX.gpkg sin conservar fid duplicados
    # =====================================================

    def guardar_solapes_limpio(self, layer, output_path, context): # GUARDA SOLAPES SIN COPIAR fid DUPLICADOS

        self.borrar_si_existe(output_path)          # BORRA EL ARCHIVO DE SALIDA SI YA EXISTE

        fields = QgsFields()                        # CREA UNA ESTRUCTURA VACÍA DE CAMPOS
        nombres = set()                             # CREA UN CONJUNTO PARA CONTROLAR CAMPOS REPETIDOS

        for field in layer.fields():                # RECORRE TODOS LOS CAMPOS DE LA CAPA DE SOLAPES

            nombre = field.name()                   # OBTIENE EL NOMBRE DEL CAMPO

            if nombre.lower() in ("fid", "fid_2", "ogc_fid", "objectid"): # COMPRUEBA CAMPOS PROBLEMÁTICOS
                continue                            # LOS SALTA PARA NO COPIARLOS

            if nombre.lower() in nombres:           # COMPRUEBA SI EL CAMPO YA EXISTE
                continue                            # SI ESTÁ REPETIDO, LO SALTA

            fields.append(QgsField(field))          # COPIA EL CAMPO A LA NUEVA ESTRUCTURA
            nombres.add(nombre.lower())             # GUARDA EL NOMBRE PARA EVITAR REPETIDOS

        options = QgsVectorFileWriter.SaveVectorOptions() # CREA OPCIONES DE GUARDADO
        options.driverName = "GPKG"                 # FORMATO DE SALIDA GeoPackage
        options.fileEncoding = "UTF-8"              # CODIFICACIÓN DEL ARCHIVO
        options.layerName = os.path.splitext(os.path.basename(output_path))[0] # NOMBRE INTERNO DE LA CAPA
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile # SOBRESCRIBE SI EXISTE

        writer = QgsVectorFileWriter.create(        # CREA EL ESCRITOR DEL ARCHIVO
            output_path,                            # RUTA DE SALIDA
            fields,                                 # CAMPOS LIMPIOS
            layer.wkbType(),                        # TIPO DE GEOMETRÍA
            layer.sourceCrs(),                      # SISTEMA DE COORDENADAS
            context.transformContext(),             # CONTEXTO DE TRANSFORMACIÓN
            options                                 # OPCIONES DE GUARDADO
        )

        if writer.hasError() != QgsVectorFileWriter.NoError: # COMPRUEBA SI HUBO ERROR AL CREAR EL ARCHIVO
            raise QgsProcessingException(           # LANZA ERROR CONTROLADO
                f"Error creando salida de solapes: {writer.errorMessage()}"
            )

        for f in layer.getFeatures():               # RECORRE CADA SOLAPE FILTRADO

            new_f = QgsFeature(fields)              # CREA UNA ENTIDAD NUEVA CON LOS CAMPOS LIMPIOS
            new_f.setGeometry(f.geometry())         # COPIA LA GEOMETRÍA DEL SOLAPE

            attrs = []                              # CREA LISTA VACÍA DE ATRIBUTOS

            for field in fields:                    # RECORRE LOS CAMPOS DE SALIDA
                nombre = field.name()               # OBTIENE EL NOMBRE DEL CAMPO
                idx = f.fields().indexFromName(nombre) # BUSCA EL CAMPO EN LA CAPA ORIGINAL

                if idx >= 0:                        # SI EL CAMPO EXISTE
                    attrs.append(f[nombre])         # COPIA SU VALOR
                else:                               # SI NO EXISTE
                    attrs.append(None)              # PONE VALOR VACÍO

            new_f.setAttributes(attrs)              # ASIGNA LOS ATRIBUTOS A LA NUEVA ENTIDAD

            if not writer.addFeature(new_f):        # INTENTA ESCRIBIR LA ENTIDAD EN EL GPKG
                raise QgsProcessingException(       # SI FALLA, LANZA ERROR
                    f"No se pudo escribir una entidad en {output_path}"
                )

        del writer                                  # CIERRA EL ARCHIVO Y GUARDA CAMBIOS

    # =====================================================
    # GUARDADO LIMPIO DE HUECOS
    # INPUT: capa huecos_final
    # OUTPUT: Huecos_XX_XXX.gpkg
    # =====================================================

    def guardar_huecos_limpio(self, layer, output_path, context): # GUARDA HUECOS CON SOLO CAMPO area_m2

        self.borrar_si_existe(output_path)          # BORRA EL ARCHIVO DE HUECOS SI YA EXISTE

        fields = QgsFields()                        # CREA ESTRUCTURA DE CAMPOS VACÍA
        fields.append(QgsField("area_m2", QVariant.Double, "double", 20, 2)) # CREA CAMPO area_m2 DECIMAL

        options = QgsVectorFileWriter.SaveVectorOptions() # CREA OPCIONES DE GUARDADO
        options.driverName = "GPKG"                 # FORMATO GEOPACKAGE
        options.fileEncoding = "UTF-8"              # CODIFICACIÓN
        options.layerName = os.path.splitext(os.path.basename(output_path))[0] # NOMBRE DE CAPA
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile # SOBRESCRIBE ARCHIVO

        writer = QgsVectorFileWriter.create(        # CREA ARCHIVO DE SALIDA
            output_path,                            # RUTA DE SALIDA
            fields,                                 # CAMPOS
            layer.wkbType(),                        # TIPO DE GEOMETRÍA
            layer.sourceCrs(),                      # CRS
            context.transformContext(),             # CONTEXTO
            options                                 # OPCIONES
        )

        if writer.hasError() != QgsVectorFileWriter.NoError: # COMPRUEBA ERRORES
            raise QgsProcessingException(           # LANZA ERROR SI NO PUEDE CREAR
                f"Error creando salida de huecos: {writer.errorMessage()}"
            )

        for f in layer.getFeatures():               # RECORRE CADA HUECO
            geom = f.geometry()                     # OBTIENE SU GEOMETRÍA
            new_f = QgsFeature(fields)              # CREA NUEVA ENTIDAD
            new_f.setGeometry(geom)                 # ASIGNA GEOMETRÍA
            new_f["area_m2"] = geom.area()          # CALCULA Y ASIGNA EL ÁREA
            writer.addFeature(new_f)                # ESCRIBE LA ENTIDAD

        del writer                                  # CIERRA Y GUARDA EL ARCHIVO

    # =====================================================
    # FILTRAR FINAL_OUTPUT A 500 m DEL MUNICIPIO DE TRABAJO
    # INPUT:
    #   final_output = municipio + colindantes
    #   temp_gpkg = municipio base sin colindantes
    # OUTPUT: final_output
    # =====================================================

    def filtrar_final_output_500m(self, final_output, temp_gpkg, context, feedback): # FILTRA PARCELAS DISTANTES

        feedback.pushInfo("→ Filtrando parcelas a menos de 500 m del municipio de trabajo") # MENSAJE EN LOG

        final_layer = QgsVectorLayer(final_output, "final_output", "ogr") # CARGA MUNICIPIO + COLINDANTES
        temp_layer = QgsVectorLayer(temp_gpkg, "municipio_trabajo", "ogr") # CARGA MUNICIPIO BASE SIN COLINDANTES

        if not final_layer.isValid():                # COMPRUEBA SI final_output CARGA BIEN
            feedback.pushInfo(f"final_output no válido: {final_output}") # AVISA SI NO ES VÁLIDO
            return final_output                      # DEVUELVE LA MISMA RUTA SIN MODIFICAR

        if not temp_layer.isValid():                 # COMPRUEBA SI temp_gpkg CARGA BIEN
            feedback.pushInfo(f"temp_gpkg no válido: {temp_gpkg}") # AVISA SI NO ES VÁLIDO
            return final_output                      # DEVUELVE LA MISMA RUTA SIN MODIFICAR

        buffer_500 = processing.run(                 # EJECUTA HERRAMIENTA BUFFER
            "native:buffer",                         # ALGORITMO BUFFER DE QGIS
            {
                "INPUT": temp_layer,                 # CAPA DE ENTRADA: MUNICIPIO BASE
                "DISTANCE": 500,                     # DISTANCIA DEL BUFFER EN METROS
                "SEGMENTS": 10,                      # SEGMENTOS PARA REDONDEAR EL BUFFER
                "DISSOLVE": True,                    # DISUELVE EL BUFFER EN UNA SOLA GEOMETRÍA
                "OUTPUT": "TEMPORARY_OUTPUT"         # CREA SALIDA TEMPORAL
            },
            context=context,                         # CONTEXTO DE EJECUCIÓN
            feedback=feedback                        # MENSAJES DE PROCESO
        )["OUTPUT"]                                  # GUARDA LA CAPA RESULTADO

        filtrado_500 = processing.run(               # EXTRAE PARCELAS POR LOCALIZACIÓN
            "native:extractbylocation",              # ALGORITMO EXTRAER POR LOCALIZACIÓN
            {
                "INPUT": final_layer,                # ENTRADA: MUNICIPIO + COLINDANTES
                "PREDICATE": [0],                    # 0 = INTERSECTA
                "INTERSECT": buffer_500,             # CAPA DE INTERSECCIÓN: BUFFER 500 m
                "OUTPUT": "TEMPORARY_OUTPUT"         # SALIDA TEMPORAL
            },
            context=context,                         # CONTEXTO
            feedback=feedback                        # MENSAJES
        )["OUTPUT"]                                  # GUARDA CAPA FILTRADA

        temp_filtrado = final_output.replace(".gpkg", "_filtrado_500m_tmp.gpkg") # CREA RUTA TEMPORAL

        self.borrar_si_existe(temp_filtrado)         # BORRA TEMPORAL SI EXISTE

        processing.run(                              # GUARDA LA CAPA FILTRADA EN LA TEMPORAL 
            "native:savefeatures",                   # ALGORITMO GUARDAR ENTIDADES
            {
                "INPUT": filtrado_500,               # ENTRADA: CAPA FILTRADA
                "OUTPUT": temp_filtrado              # SALIDA: ARCHIVO TEMPORAL
            },
            context=context,                         # CONTEXTO
            feedback=feedback                        # MENSAJES
        )

        final_layer = None                           # LIBERA LA CAPA final_output
        temp_layer = None                            # LIBERA LA CAPA temp_gpkg

        self.borrar_si_existe(final_output)          # BORRA EL GPKG FINAL ORIGINAL, PORQUE SE VA A SUSTITUIR POR EL FILTRADO

        os.replace(temp_filtrado, final_output)      # RENOMBRA EL ARCHIVO TEMPORAL FILTRADO CON EL MISMO NOMBRE QUE TENÍA final_output

        feedback.pushInfo(f"final_output filtrado a 500 m: {final_output}") # MENSAJE FINAL

        return final_output                          # DEVUELVE LA MISMA RUTA, PERO AHORA EL ARCHIVO YA ESTÁ FILTRADO A 500 m

    # =====================================================
    # CALCULO SOLAPES
    # INPUT:
    #   XX_XXX.gpkg
    #   superficie_minima definida por el usuario
    # OUTPUT:
    #   Solapes_XX_XXX.gpkg si hay solapes válidos
    # =====================================================

    def ejecutar_solapes(self, gpkg_path, output_path, superficie_minima, context, feedback): # FUNCIÓN PARA CALCULAR SOLAPES

        layer = QgsVectorLayer(gpkg_path, "input", "ogr") # CARGA EL GPKG FINAL

        if not layer.isValid():                      # COMPRUEBA SI LA CAPA ES VÁLIDA
            feedback.pushInfo("GPKG inválido para solapes") # AVISA SI NO ES VÁLIDA
            return None                              # SALE SIN GENERAR SOLAPES

        feedback.pushInfo("→ Calculando solapes")    # MENSAJE EN LOG

        # =====================================================
        # 1. IDENTIFICAR MUNICIPIO DE TRABAJO
        # INPUT: primera entidad del GPKG final
        # OUTPUT: prov / municipio del municipio base
        # El GPKG final se crea poniendo primero el municipio de trabajo
        # y después los colindantes.
        # =====================================================

        prov = None                                  # INICIALIZA PROVINCIA
        municipio = None                             # INICIALIZA MUNICIPIO
        
        #ITERADOR
        
        for f in layer.getFeatures():                # LEE LA PRIMERA ENTIDAD DEL GPKG
            prov = f["PROVINCIA"]                    # GUARDA PROVINCIA DEL MUNICIPIO BASE
            municipio = f["MUNICIPIO"]               # GUARDA MUNICIPIO DEL MUNICIPIO BASE
            break                                    # SALE DEL BUCLE TRAS EL PRIMER REGISTRO

        if municipio is None:                        # SI NO HAY DATOS
            feedback.pushInfo("Sin datos para calcular solapes") # AVISA
            return None                              # SALE

        feedback.pushInfo(f"Municipio de trabajo para filtrar solapes: {prov}-{municipio}") # LOG

        # =====================================================
        # 2. INTERSECCIÓN DE LA CAPA CONSIGO MISMA
        # INPUT: municipio + colindantes
        # OVERLAY: municipio + colindantes
        # OUTPUT: geometrías de intersección entre parcelas
        # =====================================================

        inter = processing.run(                      # EJECUTA INTERSECCIÓN
            "native:intersection",                   # ALGORITMO INTERSECCIÓN
            {
                "INPUT": layer,                      # CAPA ENTRADA
                "OVERLAY": layer,                    # CAPA CONTRA SÍ MISMA
                "OUTPUT": "TEMPORARY_OUTPUT"         # SALIDA TEMPORAL
            },
            context=context,                         # CONTEXTO
            feedback=feedback                        # MENSAJES
        )["OUTPUT"]                                  # CAPA RESULTADO

        # =====================================================
        # 3. ELIMINAR DUPLICADOS Y AUTO-INTERSECCIONES
        # INPUT: intersección
        # OUTPUT: solo pares únicos A-B
        # =====================================================

        no_self = processing.run(                    # FILTRA DUPLICADOS
            "native:extractbyexpression",            # ALGORITMO EXTRAER POR EXPRESIÓN
            {
                "INPUT": inter,                      # ENTRADA: INTERSECCIÓN
                "EXPRESSION": '"SE_ROW_ID" < "SE_ROW_ID_2"', # EVITA A-A Y DUPLICADOS A-B/B-A
                "OUTPUT": "TEMPORARY_OUTPUT"         # SALIDA TEMPORAL
            },
            context=context,                         # CONTEXTO
            feedback=feedback                        # MENSAJES
        )["OUTPUT"]                                  # CAPA RESULTADO

        # =====================================================
        # 4. FILTRAR SOLO SOLAPES DEL MUNICIPIO DE TRABAJO
        # INPUT: solapes sin duplicados
        # OUTPUT: solapes donde participa el municipio base
        # =====================================================

        expr_municipio_trabajo = (                   # CREA EXPRESIÓN PARA QUEDARSE SOLO CON EL MUNICIPIO BASE
            f'("PROVINCIA" = {prov} AND "MUNICIPIO" = {municipio}) '
            f'OR '
            f'("PROVINCIA_2" = {prov} AND "MUNICIPIO_2" = {municipio})'
        )

        solapes_municipio = processing.run(          # FILTRA SOLAPES DEL MUNICIPIO DE TRABAJO
            "native:extractbyexpression",            # ALGORITMO FILTRAR POR EXPRESIÓN
            {
                "INPUT": no_self,                    # ENTRADA: SOLAPES SIN DUPLICADOS
                "EXPRESSION": expr_municipio_trabajo, # EXPRESIÓN MUNICIPIO BASE
                "OUTPUT": "TEMPORARY_OUTPUT"         # SALIDA TEMPORAL
            },
            context=context,                         # CONTEXTO
            feedback=feedback                        # MENSAJES
        )["OUTPUT"]                                  # CAPA RESULTADO

        if solapes_municipio.featureCount() == 0:    # COMPRUEBA SI HAY SOLAPES
            feedback.pushInfo("No hay solapes del municipio de trabajo") # AVISA
            return None                              # SALE

        # =====================================================
        # 5. CALCULAR ÁREA DEL SOLAPE
        # INPUT: solapes del municipio de trabajo
        # OUTPUT: capa con campo area_m2
        # =====================================================

        areas = processing.run(                     # CALCULA ÁREA
            "native:fieldcalculator",               # ALGORITMO CALCULADORA DE CAMPOS
            {
                "INPUT": solapes_municipio,         # ENTRADA: SOLAPES DEL MUNICIPIO
                "FIELD_NAME": "area_m2",            # NOMBRE DEL CAMPO NUEVO
                "FIELD_TYPE": 0,                    # TIPO DECIMAL
                "FIELD_LENGTH": 20,                 # LONGITUD
                "FIELD_PRECISION": 2,               # DECIMALES
                "FORMULA": "$area",                 # FÓRMULA ÁREA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # CAPA RESULTADO

        # =====================================================
        # 6. FILTRAR SOLAPES POR SUPERFICIE MÍNIMA
        # INPUT: capa con area_m2
        # OUTPUT: solapes mayores que superficie_minima
        # =====================================================

        filtrado = processing.run(                  # FILTRA POR SUPERFICIE MÍNIMA
            "native:extractbyexpression",           # ALGORITMO FILTRAR
            {
                "INPUT": areas,                     # ENTRADA: SOLAPES CON ÁREA
                "EXPRESSION": f'"area_m2" > {superficie_minima}', # ÁREA MAYOR QUE LA INDICADA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # CAPA FILTRADA

        if filtrado.featureCount() == 0:            # SI NO HAY SOLAPES TRAS FILTRAR
            feedback.pushInfo(f"No hay solapes válidos > {superficie_minima} m²") # AVISA
            return None                             # SALE

        solapes_output = os.path.join(              # CREA RUTA DE SALIDA
            output_path,                            # CARPETA DE SALIDA
            "Solapes_" + os.path.basename(gpkg_path) # NOMBRE Solapes_XX_XXX.gpkg
        )

        # =====================================================
        # 7. GUARDAR SOLAPES DE FORMA LIMPIA
        # INPUT: solapes filtrados
        # OUTPUT: Solapes_XX_XXX.gpkg
        # =====================================================

        self.guardar_solapes_limpio(                # GUARDA SOLAPES SIN fid DUPLICADOS
            filtrado,                               # CAPA FILTRADA
            solapes_output,                         # RUTA DE SALIDA
            context                                 # CONTEXTO
        )

        feedback.pushInfo(f"Solapes generados: {solapes_output}") # MENSAJE

        return solapes_output                       # DEVUELVE RUTA DE SOLAPES

    # =====================================================
    # CALCULO HUECOS
    # =====================================================

    def ejecutar_huecos(self, gpkg_path, temp_gpkg_path, output_path, superficie_minima, context, feedback): # FUNCIÓN HUECOS

        feedback.pushInfo("→ Calculando huecos")    # MENSAJE EN LOG

        # =====================================================
        # 1. CARGAR CAPA BASE DE HUECOS
        # INPUT: XX_XXX.gpkg
        # OUTPUT: layer = municipio + colindantes
        # =====================================================

        layer = QgsVectorLayer(gpkg_path, "input_huecos", "ogr") # CARGA MUNICIPIO + COLINDANTES

        if not layer.isValid():                     # COMPRUEBA CAPA
            feedback.pushInfo("GPKG inválido para huecos") # AVISA
            return None                             # SALE

        # =====================================================
        # 2. DISOLVER CAPA COMPLETA
        # INPUT: layer = municipio + colindantes
        # OUTPUT: dissolved = geometría disuelta
        # =====================================================

        dissolved = processing.run(                 # DISUELVE PARCELAS
            "native:dissolve",                      # ALGORITMO DISOLVER
            {
                "INPUT": layer,                     # ENTRADA
                "FIELD": [],                        # SIN CAMPO: DISUELVE TODO
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # CAPA DISUELTA

        # =====================================================
        # 3. CONVERTIR POLÍGONOS A LÍNEAS
        # INPUT: dissolved = geometría disuelta
        # OUTPUT: dissolved_lines = líneas del contorno parcelario
        # =====================================================

        dissolved_lines = processing.run(           # CONVIERTE POLÍGONOS A LÍNEAS
            "native:polygonstolines",               # ALGORITMO POLÍGONOS A LÍNEAS
            {
                "INPUT": dissolved,                 # ENTRADA DISUELTA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # CAPA DE LÍNEAS

        # =====================================================
        # 4. POLIGONIZAR LAS LÍNEAS
        # INPUT: dissolved_lines = líneas del contorno
        # OUTPUT: polygonized = polígonos generados a partir de las líneas
        # =====================================================

        polygonized = processing.run(               # POLIGONIZA LAS LÍNEAS
            "native:polygonize",                    # ALGORITMO POLIGONIZAR
            {
                "INPUT": dissolved_lines,           # ENTRADA LÍNEAS
                "KEEP_FIELDS": False,               # NO CONSERVA CAMPOS
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # CAPA POLIGONIZADA

        # =====================================================
        # 5. SELECCIONAR GEOMETRIAS CONTENIDOS EN PARCELAS
        # INPUT:
        #   polygonized = polígonos creados por polygonize
        #   layer = parcelario original
        # OUTPUT: polygonized con seleccionados los polígonos que contienen parcelas
        # =====================================================

        polygonized.removeSelection()               # LIMPIA SELECCIÓN PREVIA

        processing.run(                             # SELECCIONA GEOMETRIAS CONTENIDAS PARCELAS
            "native:selectbylocation",              # SELECCIÓN POR LOCALIZACIÓN
            {
                "INPUT": polygonized,               # CAPA POLIGONIZADA
                "PREDICATE": [1],                   # 1 = CONTIENE
                "INTERSECT": layer,                 # CAPA PARCELARIA
                "METHOD": 0                         # NUEVA SELECCIÓN
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )

        polygonized.invertSelection()               # INVIERTE SELECCIÓN PARA QUEDARSE CON POSIBLES HUECOS

        # =====================================================
        # 6. GUARDAR POSIBLES HUECOS
        # INPUT: polygonized con selección invertida
        # OUTPUT: huecos_raw = posibles huecos sin filtrar
        # =====================================================

        huecos_raw = processing.run(                # GUARDA SELECCIÓN INVERTIDA
            "native:saveselectedfeatures",          # GUARDAR ENTIDADES SELECCIONADAS
            {
                "INPUT": polygonized,               # ENTRADA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # HUECOS BRUTOS

        # =====================================================
        # 7. CALCULAR ÁREA DE LOS HUECOS
        # INPUT: huecos_raw = posibles huecos
        # OUTPUT: huecos_area = huecos con campo area_m2
        # =====================================================

        polygonized.removeSelection()               # LIMPIA SELECCIÓN

        huecos_area = processing.run(               # CALCULA ÁREA DE HUECOS
            "native:fieldcalculator",               # CALCULADORA DE CAMPOS
            {
                "INPUT": huecos_raw,                # ENTRADA HUECOS
                "FIELD_NAME": "area_m2",            # CAMPO NUEVO
                "FIELD_TYPE": 0,                    # DECIMAL
                "FIELD_LENGTH": 20,                 # LONGITUD
                "FIELD_PRECISION": 2,               # DECIMALES
                "FORMULA": "$area",                 # ÁREA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # HUECOS CON ÁREA

        # =====================================================
        # 8. FILTRAR HUECOS POR SUPERFICIE MÍNIMA
        # INPUT: 
        #   huecos_area = huecos con area_m2
        #   superficie_minima = valor elegido por el usuario
        # OUTPUT: filtered = huecos mayores que superficie_minima
        # =====================================================

        filtered = processing.run(                  # FILTRA HUECOS POR ÁREA
            "native:extractbyexpression",           # EXTRAER POR EXPRESIÓN
            {
                "INPUT": huecos_area,               # ENTRADA
                "EXPRESSION": f'"area_m2" > {superficie_minima}', # MAYOR QUE SUPERFICIE MÍNIMA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # HUECOS FILTRADOS

        # =====================================================
        # 9. FILTRAR HUECOS PRÓXIMOS AL MUNICIPIO BASE
        # INPUT: filtered = huecos mayores que superficie_minima
        # OUTPUT: huecos_final = huecos válidos próximos al municipio de trabajo
        # =====================================================

        temp_layer = QgsVectorLayer(temp_gpkg_path, "municipio_trabajo", "ogr") # CARGA MUNICIPIO BASE

        if not temp_layer.isValid():                # COMPRUEBA SI ES VÁLIDO
            feedback.pushInfo("GPKG temporal inválido para filtro de huecos") # AVISA
            return None                             # SALE

        #  CREAR BUFFER DE 1 m DEL MUNICIPIO BASE

        buffer_temp_1m = processing.run(            # CREA BUFFER 1 m DEL MUNICIPIO BASE
            "native:buffer",                        # ALGORITMO BUFFER
            {
                "INPUT": temp_layer,                # ENTRADA MUNICIPIO BASE
                "DISTANCE": 1,                      # DISTANCIA 1 METRO
                "SEGMENTS": 10,                     # SEGMENTOS
                "DISSOLVE": True,                   # DISUELVE
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # BUFFER 1 m

        # FILTRAR HUECOS PRÓXIMOS AL MUNICIPIO BASE (1 m)

        huecos_final = processing.run(              # FILTRA HUECOS PRÓXIMOS AL MUNICIPIO BASE
            "native:extractbylocation",             # EXTRAER POR LOCALIZACIÓN
            {
                "INPUT": filtered,                  # HUECOS FILTRADOS POR ÁREA
                "INTERSECT": buffer_temp_1m,        # BUFFER 1 m MUNICIPIO BASE
                "PREDICATE": [0],                   # INTERSECTA
                "OUTPUT": "TEMPORARY_OUTPUT"        # SALIDA TEMPORAL
            },
            context=context,                        # CONTEXTO
            feedback=feedback                       # MENSAJES
        )["OUTPUT"]                                 # HUECOS FINALES

        if huecos_final.featureCount() == 0:        # SI NO HAY HUECOS
            feedback.pushInfo(f"No hay huecos válidos > {superficie_minima} m²") # AVISA
            return None                             # SALE

        huecos_output = os.path.join(               # CREA RUTA HUECOS
            output_path,                            # CARPETA SALIDA
            "Huecos_" + os.path.basename(gpkg_path) # NOMBRE Huecos_XX_XXX.gpkg
        )

        self.guardar_huecos_limpio(huecos_final, huecos_output, context) # GUARDA HUECOS LIMPIOS

        feedback.pushInfo(f"Huecos generados: {huecos_output}") # MENSAJE

        return huecos_output                        # DEVUELVE RUTA DE HUECOS
        
    # =====================================================
    # MERGE FINAL SOLAPES + HUECOS
    # INPUT:
    #   solapes_path = Solapes_XX_XXX.gpkg SI EXISTE
    #   huecos_path = Huecos_XX_XXX.gpkg SI EXISTE
    #   output_folder = CARPETA PRINCIPAL DE SALIDA
    #   code = CÓDIGO DEL MUNICIPIO XX_XXX
    # OUTPUT:
    #   Envio/Incidencias_XXXXX.gpkg
    # =====================================================

    def ejecutar_merge_incidencias(self, solapes_path, huecos_path, output_folder, code, context, feedback): # UNE SOLAPES Y HUECOS EN UNA CAPA FINAL

        codigo_sin_barra = code.replace("_", "")    # QUITA EL GUION BAJO DEL CÓDIGO, POR EJEMPLO 46_011 PASA A 46011

        carpeta_salida = os.path.join(output_folder, "Envio") # CREA LA RUTA DE LA CARPETA Envio DENTRO DE LA CARPETA DE SALIDA
        os.makedirs(carpeta_salida, exist_ok=True)  # CREA LA CARPETA Envio SI NO EXISTE

        layers = []                                 # CREA UNA LISTA VACÍA DONDE SE AÑADIRÁN LAS CAPAS DE SOLAPES Y/O HUECOS

        if solapes_path and os.path.exists(solapes_path): # COMPRUEBA SI EXISTE RUTA DE SOLAPES Y SI EL ARCHIVO EXISTE
            solapes_layer = QgsVectorLayer(solapes_path, "solapes", "ogr") # CARGA Solapes_XX_XXX.gpkg COMO CAPA VECTORIAL
            if solapes_layer.isValid():             # COMPRUEBA SI LA CAPA DE SOLAPES ES VÁLIDA
                layers.append(solapes_layer)        # AÑADE LA CAPA DE SOLAPES A LA LISTA DE CAPAS A UNIR

        if huecos_path and os.path.exists(huecos_path): # COMPRUEBA SI EXISTE RUTA DE HUECOS Y SI EL ARCHIVO EXISTE
            huecos_layer = QgsVectorLayer(huecos_path, "huecos", "ogr") # CARGA Huecos_XX_XXX.gpkg COMO CAPA VECTORIAL
            if huecos_layer.isValid():              # COMPRUEBA SI LA CAPA DE HUECOS ES VÁLIDA
                layers.append(huecos_layer)         # AÑADE LA CAPA DE HUECOS A LA LISTA DE CAPAS A UNIR

        if not layers:                              # COMPRUEBA SI LA LISTA ESTÁ VACÍA, ES DECIR, NO HAY NI SOLAPES NI HUECOS
            feedback.pushInfo("No hay capas para unir en incidencias") # AVISA EN EL LOG DE QUE NO HAY INCIDENCIAS
            return None                             # SALE DE LA FUNCIÓN SIN CREAR ARCHIVO DE INCIDENCIAS

        output_merge = os.path.join(                # CREA LA RUTA FINAL DEL ARCHIVO DE INCIDENCIAS
            carpeta_salida,                         # CARPETA Envio
            f"Incidencias_{codigo_sin_barra}.gpkg"  # NOMBRE DEL ARCHIVO: Incidencias_XXXXX.gpkg
        )

        self.borrar_si_existe(output_merge)         # BORRA Incidencias_XXXXX.gpkg SI YA EXISTÍA

        processing.run(                             # EJECUTA LA HERRAMIENTA DE MERGE DE CAPAS VECTORIALES
            "native:mergevectorlayers",             # ALGORITMO MERGE VECTOR LAYERS
            {
                "LAYERS": layers,                   # CAPAS A UNIR: SOLAPES, HUECOS O AMBAS
                "OUTPUT": output_merge              # ARCHIVO FINAL DE SALIDA
            },
            context=context,                        # CONTEXTO DE EJECUCIÓN DE QGIS
            feedback=feedback                       # MENSAJES DE PROCESO
        )

        feedback.pushInfo(f"Incidencias generadas: {output_merge}") # MUESTRA EN EL LOG LA RUTA DEL ARCHIVO GENERADO

        return output_merge                         # DEVUELVE LA RUTA DE Incidencias_XXXXX.gpkg PARA USARLA EN LOS PDF


    # =====================================================
    # CREAR CAPA TRABAJO
    # INPUT:
    #   parameters = PARÁMETROS QUE INTRODUCE EL USUARIO EN LA VENTANA DEL SCRIPT
    #   context = CONTEXTO DE EJECUCIÓN DE QGIS
    #   feedback = MENSAJES Y BARRA DE PROGRESO
    # OUTPUT:
    #   EJECUTA TODO EL PROCESO MUNICIPIO A MUNICIPIO
    # =====================================================

    def processAlgorithm(self, parameters, context, feedback): # FUNCIÓN PRINCIPAL DEL SCRIPT, AQUÍ EMPIEZA LA EJECUCIÓN

        # =====================================================
        # 1. LEER PARAMETROS DE ENTRADA
        # =====================================================

        base_shp = self.parameterAsString(parameters, self.BASE_SHP, context) # LEE LA CARPETA BASE DONDE ESTÁN LOS SHP
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context) # LEE LA CARPETA DONDE SE GUARDARÁN LOS RESULTADOS
        plantilla_path = self.parameterAsFile(parameters, self.PLANTILLA_MAPAS, context) # LEE LA RUTA DEL ARCHIVO DE PLANTILLA QPT

        superficie_minima = self.parameterAsDouble(parameters, self.SUPERFICIE_MINIMA, context) # LEE LA SUPERFICIE MÍNIMA INTRODUCIDA POR EL USUARIO

        if not plantilla_path or not os.path.exists(plantilla_path): # COMPRUEBA SI NO HAY PLANTILLA O SI LA RUTA NO EXISTE
            raise QgsProcessingException(          # LANZA UN ERROR CONTROLADO Y DETIENE EL SCRIPT
                f"No existe la plantilla de mapas QPT: {plantilla_path}" # MENSAJE DEL ERROR
            )

        temp_gpkg_folder = os.path.join(output_folder, "_TEMP_GPKG") # CREA LA RUTA DE LA CARPETA INTERMEDIA _TEMP_GPKG
        envio_folder = os.path.join(output_folder, "Envio") # CREA LA RUTA DE LA CARPETA FINAL Envio

        os.makedirs(temp_gpkg_folder, exist_ok=True) # CREA LA CARPETA _TEMP_GPKG SI NO EXISTE
        os.makedirs(output_folder, exist_ok=True)    # CREA LA CARPETA PRINCIPAL DE SALIDA SI NO EXISTE
        os.makedirs(envio_folder, exist_ok=True)     # CREA LA CARPETA Envio SI NO EXISTE

        tabla = self.parameterAsSource(parameters, self.TABLA_TRABAJO, context) # LEE LA TABLA DE MUNICIPIOS DE TRABAJO
        unr = self.parameterAsSource(parameters, self.MUNICIPIOS_UNR, context) # LEE LA TABLA DE MUNICIPIOS CON UNR
        colindancias = self.parameterAsSource(parameters, self.COLINDANCIAS, context) # LEE LA TABLA DE MUNICIPIOS COLINDANTES

        unr_list = list(unr.getFeatures())           # CONVIERTE LA TABLA UNR EN LISTA PARA BUSCAR MÁS RÁPIDO
        col_cache = list(colindancias.getFeatures()) # CONVIERTE LA TABLA DE COLINDANCIAS EN LISTA PARA BUSCAR MÁS RÁPIDO

        total = tabla.featureCount()                 # CUENTA CUÁNTOS MUNICIPIOS HAY EN LA TABLA DE TRABAJO

        # =====================================================
        #ITERADOR
        # =====================================================

        for i, t in enumerate(tabla.getFeatures()):  # RECORRE CADA REGISTRO DE LA TABLA DE TRABAJO, i ES EL ÍNDICE Y t EL REGISTRO

            # =====================================================
            # 2. IDENTIFICAR MUNICIPIO DE TRABAJO
            # INPUT: registro de TABLA_TRABAJO
            # OUTPUT: code = XX_XXX
            # =====================================================

            prov = int(t["PROVINCIA_A"])             # ASIGNA EL VALOR PROVINCIA_A DEL REGISTRO A LA VARIABLE prov COMO ENTERO
            mun = int(t["MUNICIPIO_A"])              # ASIGNA EL VALOR MUNICIPIO_A DEL REGISTRO A LA VARIABLE mun COMO ENTERO

            code = f"{str(prov).zfill(2)}_{str(mun).zfill(3)}" # CREA EL CÓDIGO XX_XXX, PROVINCIA CON 2 DÍGITOS Y MUNICIPIO CON 3 (zfill(2) rellena con 0 hasta 2)

            feedback.pushInfo(f"\n→ Municipio {code}") # ESCRIBE EN EL LOG EL MUNICIPIO ACTUAL, \n HACE SALTO DE LÍNEA
            feedback.pushInfo(f"Superficie mínima aplicada: {superficie_minima} m²") # ESCRIBE EN EL LOG LA SUPERFICIE MÍNIMA

            # =====================================================
            # 3. CREAR RUTAS SHP DEL MUNICIPIO ("os path join")
            # INPUT: BASE_SHP + code
            # OUTPUT: PARCCAT.shp / PARCATUN.shp
            # =====================================================

            shp_parccat = os.path.join(base_shp, code, "PARCCAT.shp") # CREA LA RUTA DEL PARCCAT.shp DEL MUNICIPIO
            shp_parcatun = os.path.join(base_shp, code, "PARCATUN.shp") # CREA LA RUTA DEL PARCATUN.shp DEL MUNICIPIO

            if not os.path.exists(shp_parccat):      # COMPRUEBA SI NO EXISTE PARCCAT.shp
                feedback.pushInfo(f"No existe PARCCAT: {shp_parccat}") # AVISA EN EL LOG DE QUE NO EXISTE PARCCAT
                continue                             # SALTA AL SIGUIENTE MUNICIPIO

            # =====================================================
            # 4. CARGAR PARCCAT
            # INPUT: PARCCAT.shp
            # OUTPUT: parccat
            # =====================================================

            parccat = QgsVectorLayer(shp_parccat, "parccat", "ogr") # CARGA PARCCAT.shp COMO CAPA VECTORIAL

            if not parccat.isValid():                # COMPRUEBA SI LA CAPA PARCCAT NO ES VÁLIDA
                feedback.pushInfo(f"PARCCAT no válido: {shp_parccat}") # AVISA EN EL LOG DE QUE PARCCAT NO ES VÁLIDO
                continue                             # SALTA AL SIGUIENTE MUNICIPIO

            # =====================================================
            # 5. COMPROBAR SI EL MUNICIPIO ITERADO TIENE UNR
            # INPUT: MUNICIPIOS_UNR
            # OUTPUT: in_unr True/False
            # =====================================================

            in_unr = any(                            # COMPRUEBA SI ALGÚN REGISTRO DE LA TABLA UNR COINCIDE CON EL MUNICIPIO ACTUAL
                int(u["PROVINCIA"]) == prov and int(u["MUNICIPIO"]) == mun # COMPARA PROVINCIA Y MUNICIPIO
                for u in unr_list                    # RECORRE TODOS LOS REGISTROS DE LA LISTA UNR
            )

            # =====================================================
            # 6. ARCHIVO INTERMEDIO DEL MUNICIPIO SIN COLINDANTES
            # OUTPUT: _TEMP_GPKG/XX_XXX.gpkg
            # Este archivo será luego BACKGROUND para los PDFs
            # =====================================================

            temp_gpkg = os.path.join(temp_gpkg_folder, f"{code}.gpkg") # CREA LA RUTA DEL GPKG INTERMEDIO DEL MUNICIPIO BASE

            if os.path.exists(temp_gpkg):            # COMPRUEBA SI YA EXISTE EL GPKG INTERMEDIO
                os.remove(temp_gpkg)                 # BORRA EL GPKG INTERMEDIO PARA CREARLO LIMPIO

            # =====================================================
            # UNR + 9000
            # =====================================================

            if in_unr and os.path.exists(shp_parcatun): # SI EL MUNICIPIO ESTÁ EN UNR Y EXISTE PARCATUN.shp, APLICA PROCESO UNR

                # =====================================================
                # 7. CARGAR PARCATUN
                # INPUT: PARCATUN.shp
                # OUTPUT: parcatun
                # =====================================================

                parcatun = QgsVectorLayer(shp_parcatun, "parcatun", "ogr") # CARGA PARCATUN.shp COMO CAPA VECTORIAL

                if not parcatun.isValid():           # COMPRUEBA SI PARCATUN NO ES VÁLIDO
                    feedback.pushInfo(f"PARCATUN no válido: {shp_parcatun}") # AVISA EN EL LOG
                    continue                         # SALTA AL SIGUIENTE MUNICIPIO

                # =====================================================
                # 8. SELECCIONAR PARCELAS 9000
                # INPUT: parccat
                # OUTPUT: p9000
                # =====================================================

                p9000 = processing.run(              # EJECUTA EXTRACCIÓN DE PARCELA 9000
                    "native:extractbyexpression",    # ALGORITMO EXTRAER POR EXPRESIÓN
                    {
                        "INPUT": parccat,            # CAPA DE ENTRADA: PARCCAT
                        "EXPRESSION": '"PARCELA" = 9000', # FILTRA SOLO PARCELA 9000
                        "OUTPUT": "TEMPORARY_OUTPUT" # CREA SALIDA TEMPORAL
                    },
                    context=context,                 # CONTEXTO DE QGIS
                    feedback=feedback                # MENSAJES
                )["OUTPUT"]                          # GUARDA RESULTADO EN p9000

                # =====================================================
                # 9. SELECCIONAR RESTO DE PARCELAS
                # INPUT: parccat
                # OUTPUT: resto
                # =====================================================

                resto = processing.run(              # EJECUTA EXTRACCIÓN DEL RESTO DE PARCELAS
                    "native:extractbyexpression",    # ALGORITMO EXTRAER POR EXPRESIÓN
                    {
                        "INPUT": parccat,            # CAPA DE ENTRADA: PARCCAT
                        "EXPRESSION": '"PARCELA" <> 9000', # FILTRA TODAS LAS PARCELAS DISTINTAS DE 9000
                        "OUTPUT": "TEMPORARY_OUTPUT" # CREA SALIDA TEMPORAL
                    },
                    context=context,                 # CONTEXTO
                    feedback=feedback                # MENSAJES
                )["OUTPUT"]                          # GUARDA RESULTADO EN resto

                # =====================================================
                # 10. RECORTAR PARCELA 9000 CON UNR
                # INPUT: p9000
                # OVERLAY: parcatun
                # OUTPUT: p9000 recortada
                # =====================================================

                p9000 = processing.run(              # EJECUTA DIFERENCIA ENTRE PARCELA 9000 Y PARCATUN
                    "native:difference",             # ALGORITMO DIFERENCIA
                    {
                        "INPUT": p9000,              # ENTRADA: PARCELA 9000
                        "OVERLAY": parcatun,         # CAPA QUE SE RESTA: PARCATUN
                        "OUTPUT": "TEMPORARY_OUTPUT" # SALIDA TEMPORAL
                    },
                    context=context,                 # CONTEXTO
                    feedback=feedback                # MENSAJES
                )["OUTPUT"]                          # GUARDA LA 9000 RECORTADA EN p9000

                # =====================================================
                # 11. CREAR MUNICIPIO TEMPORAL SIN COLINDANTES
                # INPUT: resto + p9000 + parcatun
                # OUTPUT: _TEMP_GPKG/XX_XXX.gpkg
                # =====================================================

                processing.run(                      # EJECUTA MERGE DEL MUNICIPIO MODIFICADO
                    "native:mergevectorlayers",      # ALGORITMO UNIR CAPAS VECTORIALES
                    {
                        "LAYERS": [resto, p9000, parcatun], # UNE RESTO + 9000 RECORTADA + PARCATUN
                        "OUTPUT": temp_gpkg          # GUARDA EN _TEMP_GPKG/XX_XXX.gpkg
                    },
                    context=context,                 # CONTEXTO
                    feedback=feedback                # MENSAJES
                )

            else:                                    # SI NO TIENE UNR O NO EXISTE PARCATUN

                # =====================================================
                # 12. GUARDAR MUNICIPIO SIN UNR
                # INPUT: parccat
                # OUTPUT: _TEMP_GPKG/XX_XXX.gpkg
                # =====================================================

                processing.run(                      # GUARDA PARCCAT DIRECTAMENTE
                    "native:savefeatures",           # ALGORITMO GUARDAR ENTIDADES
                    {
                        "INPUT": parccat,            # ENTRADA: PARCCAT
                        "OUTPUT": temp_gpkg          # SALIDA: _TEMP_GPKG/XX_XXX.gpkg
                    },
                    context=context,                 # CONTEXTO
                    feedback=feedback                # MENSAJES
                )

            # =====================================================
            # UNIR COLINDANTES
            # =====================================================

            # =====================================================
            # 13. CAPA BASE PARA MERGE
            # INPUT: _TEMP_GPKG/XX_XXX.gpkg
            # OUTPUT: layers[0]
            # =====================================================

            layers = [QgsVectorLayer(temp_gpkg, code, "ogr")] # CREA LISTA DE CAPAS A UNIR, EMPEZANDO POR EL MUNICIPIO BASE

            # =====================================================
            # 14. BUSCAR COLINDANTES
            # INPUT: tabla colindancias
            # OUTPUT: vecinos
            # =====================================================

            vecinos = [                              # CREA LISTA DE VECINOS DEL MUNICIPIO ACTUAL
                f for f in col_cache                 # RECORRE LA LISTA DE COLINDANCIAS
                if int(f["PROVINCIA_A"]) == prov and int(f["MUNICIPIO_A"]) == mun # FILTRA SOLO LOS VECINOS DEL MUNICIPIO ACTUAL
            ]

            # =====================================================
            # 15. AÑADIR PARCCAT DE COLINDANTES
            # INPUT: PARCCAT.shp de cada vecino
            # OUTPUT: layers
            # =====================================================

            for v in vecinos:                        # RECORRE CADA VECINO ENCONTRADO

                code_b = f"{str(v['PROVINCIA_B']).zfill(2)}_{str(v['MUNICIPIO_B']).zfill(3)}" # CREA CÓDIGO XX_XXX DEL COLINDANTE
                shp_b = os.path.join(base_shp, code_b, "PARCCAT.shp") # CREA RUTA DEL PARCCAT.shp DEL COLINDANTE

                if os.path.exists(shp_b):            # COMPRUEBA SI EXISTE EL PARCCAT DEL COLINDANTE
                    layer_b = QgsVectorLayer(shp_b, code_b, "ogr") # CARGA EL COLINDANTE COMO CAPA VECTORIAL
                    if layer_b.isValid():            # COMPRUEBA SI EL COLINDANTE ES VÁLIDO
                        layers.append(layer_b)       # AÑADE EL COLINDANTE A LA LISTA DE CAPAS

            # =====================================================
            # 16. CREAR ARCHIVO FINAL MUNICIPIO + COLINDANTES
            # INPUT: layers
            # OUTPUT: FINAL:OUTPUT/XX_XXX.gpkg
            # =====================================================

            final_output = os.path.join(output_folder, f"{code}.gpkg") # CREA RUTA DEL GPKG FINAL MUNICIPIO + COLINDANTES

            if os.path.exists(final_output):         # COMPRUEBA SI YA EXISTE EL GPKG FINAL
                os.remove(final_output)              # BORRA EL GPKG FINAL PARA CREARLO LIMPIO

            processing.run(                          # EJECUTA MERGE MUNICIPIO BASE + COLINDANTES
                "native:mergevectorlayers",          # ALGORITMO UNIR CAPAS VECTORIALES
                {
                    "LAYERS": layers,                # LISTA DE CAPAS: MUNICIPIO BASE + COLINDANTES
                    "OUTPUT": final_output           # SALIDA: OUTPUT_FOLDER/XX_XXX.gpkg
                },
                context=context,                     # CONTEXTO
                feedback=feedback                    # MENSAJES
            )

            final_output = self.filtrar_final_output_500m( # FILTRA EL GPKG FINAL A 500 m DEL MUNICIPIO BASE
                final_output,                        # ENTRADA: MUNICIPIO + COLINDANTES
                temp_gpkg,                           # ENTRADA: MUNICIPIO BASE SIN COLINDANTES
                context,                             # CONTEXTO
                feedback                             # MENSAJES
            )

            feedback.pushInfo(f"Municipio generado: {final_output}") # AVISA QUE EL MUNICIPIO FINAL SE HA GENERADO

            # =====================================================
            # 17. GENERAR SOLAPES
            # INPUT: FINAL:OUTPUT/XX_XXX.gpkg
            # OUTPUT: OUTPUT_FOLDER/Solapes_XX_XXX.gpkg o None
            # =====================================================

            solapes_path = self.ejecutar_solapes(    # LLAMA A LA FUNCIÓN QUE CALCULA SOLAPES
                final_output,                        # ENTRADA: GPKG FINAL FILTRADO
                output_folder,                       # CARPETA DE SALIDA
                superficie_minima,                   # SUPERFICIE MÍNIMA
                context,                             # CONTEXTO
                feedback                             # MENSAJES
            )

            # =====================================================
            # 18. CALCULAR HUECOS
            # INPUT 1: 
            #   FINAL:OUTPUT/XX_XXX.gpkg
            #   _TEMP_GPKG/XX_XXX.gpkg
            # OUTPUT: OUTPUT_FOLDER/Huecos_XX_XXX.gpkg o None
            # =====================================================

            huecos_path = self.ejecutar_huecos(      # LLAMA A LA FUNCIÓN QUE CALCULA HUECOS
                final_output,                        # ENTRADA: GPKG FINAL FILTRADO
                temp_gpkg,                           # ENTRADA: MUNICIPIO BASE
                output_folder,                       # CARPETA DE SALIDA
                superficie_minima,                   # SUPERFICIE MÍNIMA
                context,                             # CONTEXTO
                feedback                             # MENSAJES
            )

            # =====================================================
            # 19. MERGE FINAL DE INCIDENCIAS
            # INPUT:
            #   Solapes_XX_XXX.gpkg si existe
            #   Huecos_XX_XXX.gpkg si existe
            # OUTPUT:
            #   envio/Incidencias_XXXXX.gpkg
            # =====================================================

            incidencias_path = self.ejecutar_merge_incidencias( # UNE SOLAPES Y HUECOS
                solapes_path,                         # ENTRADA: RUTA DE SOLAPES O None
                huecos_path,                          # ENTRADA: RUTA DE HUECOS O None
                output_folder,                        # CARPETA DE SALIDA
                code,                                 # CÓDIGO XX_XXX
                context,                              # CONTEXTO
                feedback                              # MENSAJES
            )

            # =====================================================
            # 20. EXPORTAR PDFs DE INCIDENCIAS
            # INPUT:
            #   INPUT = envio/Incidencias_XXXXX.gpkg
            #   BACKGROUND = _TEMP_GPKG/XX_XXX.gpkg
            #   OUTPUT_FOLDER = envio/PDF_XXXXX
            #   PLANTILLA_MAPAS = archivo QPT elegido en la entrada
            # OUTPUT:
            #   envio/PDF_XXXXX/INC_0001.pdf
            #   envio/PDF_XXXXX/INC_0002.pdf
            #   ...
            # =====================================================

            if incidencias_path and os.path.exists(incidencias_path): # COMPRUEBA SI SE HA CREADO EL GPKG DE INCIDENCIAS

                codigo_sin_barra = code.replace("_", "") # QUITA "_" DEL CÓDIGO PARA USARLO EN NOMBRES

                pdf_folder = os.path.join(            # CREA RUTA DE CARPETA PDF
                    envio_folder,                     # CARPETA Envio
                    f"PDF_{codigo_sin_barra}"         # NOMBRE PDF_XXXXX
                )

                self.exportar_pdfs_incidencias(       # GENERA UN PDF POR INCIDENCIA
                    incidencias_path,                 # ENTRADA: CAPA DE INCIDENCIAS
                    temp_gpkg,                        # ENTRADA: CAPA DE FONDO
                    pdf_folder,                       # CARPETA DE SALIDA DE PDF
                    code,                             # CÓDIGO XX_XXX
                    plantilla_path,                   # PLANTILLA QPT
                    context,                          # CONTEXTO
                    feedback                          # MENSAJES
                )

            else:                                      # SI NO HAY INCIDENCIAS

                feedback.pushInfo(                    # ESCRIBE MENSAJE EN EL LOG
                    f"No se generan PDFs para {code} porque no hay Incidencias" # AVISA QUE NO SE CREAN PDF
                )

            if total > 0:                              # COMPRUEBA QUE EXISTE AL MENOS UN MUNICIPIO
                feedback.setProgress(int(((i + 1) / total) * 100)) # ACTUALIZA LA BARRA DE PROGRESO

        feedback.pushInfo("Proceso completo terminado") # MENSAJE FINAL CUANDO TERMINA TODO

        return {}                                      # FINALIZA EL ALGORITMO SIN DEVOLVER UNA CAPA DE SALIDA DIRECTA

# =====================================================
# CREAR MAPAS CATASTRO
# =====================================================

    # =====================================================
    # 1. APLICAR ESTILO AL FONDO
    # INPUT:
    #   background = _TEMP_GPKG/XX_XXX.gpkg
    #   capa del municipio base sin colindantes
    # OUTPUT:
    #   background con relleno transparente y borde negro
    # =====================================================
    def aplicar_estilo_fondo(self, background):     # FUNCIÓN PARA DAR ESTILO A LA CAPA DE FONDO DEL PDF

        symbol = QgsFillSymbol.createSimple({       # CREA UN SÍMBOLO SIMPLE DE RELLENO PARA POLÍGONOS
            "color": "0,0,0,0",                     # RELLENO TRANSPARENTE, NO PINTA EL INTERIOR DE LAS PARCELAS
            "outline_color": "0,0,0",               # BORDE NEGRO
            "outline_width": "0.25"                 # GROSOR DEL BORDE 0.25
        })

        background.renderer().setSymbol(symbol)     # APLICA EL SÍMBOLO A LA CAPA background
        background.triggerRepaint()                 # FUERZA A QGIS A REDIBUJAR LA CAPA CON EL NUEVO ESTILO

    # =====================================================
    # 2. ETIQUETAR CAPA DE FONDO
    # INPUT:
    #   background = _TEMP_GPKG/XX_XXX.gpkg
    #   capa del municipio base sin colindantes
    # OUTPUT:
    #   background etiquetado con POLIGONO:PARCELA
    # =====================================================
    def activar_etiquetas_fondo(self, background):  # FUNCIÓN PARA ACTIVAR ETIQUETAS EN LA CAPA DE FONDO

        label_settings = QgsPalLayerSettings()      # CREA LA CONFIGURACIÓN DE ETIQUETADO

        label_settings.fieldName = '"POLIGONO" || \':\' || "PARCELA"' # DEFINE EL TEXTO DE LA ETIQUETA COMO POLIGONO:PARCELA
        label_settings.isExpression = True          # INDICA QUE fieldName ES UNA EXPRESIÓN, NO UN CAMPO SIMPLE
        label_settings.enabled = True               # ACTIVA EL ETIQUETADO

        text_format = QgsTextFormat()               # CREA EL FORMATO DEL TEXTO
        text_format.setSize(7)                      # TAMAÑO DE TEXTO 7

        buffer = QgsTextBufferSettings()            # CREA CONFIGURACIÓN DEL HALO DE TEXTO
        buffer.setEnabled(True)                     # ACTIVA EL HALO
        buffer.setSize(0.8)                         # TAMAÑO DEL HALO 0.8

        text_format.setBuffer(buffer)               # APLICA EL HALO AL FORMATO DE TEXTO
        label_settings.setFormat(text_format)       # APLICA EL FORMATO A LAS ETIQUETAS

        background.setLabelsEnabled(True)           # ACTIVA ETIQUETAS EN LA CAPA
        background.setLabeling(QgsVectorLayerSimpleLabeling(label_settings)) # ASIGNA EL ETIQUETADO SIMPLE A LA CAPA
        background.triggerRepaint()                 # REDIBUJA LA CAPA CON LAS ETIQUETAS

    # =====================================================
    # 3. ETIQUETAR CAPA DE INCIDENCIAS
    # INPUT:
    #   layer = Envio/Incidencias_XXXXX.gpkg
    # OUTPUT:
    #   layer etiquetado como INC: @id
    # =====================================================
    def activar_etiquetas_incidencias(self, layer): # FUNCIÓN PARA ACTIVAR ETIQUETAS EN LA CAPA DE INCIDENCIAS

        label_settings = QgsPalLayerSettings()      # CREA CONFIGURACIÓN DE ETIQUETADO

        label_settings.fieldName = "'INC: ' || @id" # TEXTO DE ETIQUETA: INC: + ID INTERNO DE LA ENTIDAD
        label_settings.isExpression = True          # INDICA QUE ES UNA EXPRESIÓN
        label_settings.enabled = True               # ACTIVA ETIQUETADO

        text_format = QgsTextFormat()               # CREA FORMATO DE TEXTO
        text_format.setSize(9)                      # TAMAÑO DE TEXTO 9

        buffer = QgsTextBufferSettings()            # CREA CONFIGURACIÓN DEL HALO
        buffer.setEnabled(True)                     # ACTIVA EL HALO
        buffer.setSize(1.0)                         # TAMAÑO DEL HALO 1.0

        text_format.setBuffer(buffer)               # APLICA HALO AL TEXTO
        label_settings.setFormat(text_format)       # ASIGNA FORMATO A LAS ETIQUETAS

        layer.setLabelsEnabled(True)                # ACTIVA ETIQUETAS EN LA CAPA DE INCIDENCIAS
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings)) # ASIGNA ETIQUETADO SIMPLE
        layer.triggerRepaint()                      # REDIBUJA LA CAPA

    # =====================================================
    # 4. CARGAR PLANTILLA QPT
    # INPUT:
    #   project = proyecto QGIS actual
    #   plantilla_path = ruta del archivo Plantilla_script.qpt
    # OUTPUT:
    #   layout = composición cargada desde la plantilla QPT
    # =====================================================
    def cargar_layout_desde_plantilla(self, project, plantilla_path): # FUNCIÓN PARA CARGAR UNA PLANTILLA QPT

        if not os.path.exists(plantilla_path):      # COMPRUEBA SI EXISTE EL ARCHIVO QPT
            raise QgsProcessingException(           # SI NO EXISTE, LANZA ERROR
                f"No existe la plantilla QPT: {plantilla_path}"
            )

        doc = QDomDocument()                        # CREA DOCUMENTO VACÍO PARA CARGAR EL QPT

        with open(plantilla_path, "r", encoding="utf-8") as file: # ABRE LA PLANTILLA QPT COMO TEXTO UTF-8
            contenido = file.read()                 # LEE TODO EL CONTENIDO DEL ARCHIVO QPT

        if not doc.setContent(contenido):           # INTENTA CARGAR EL TEXTO QPT COMO XML
            raise QgsProcessingException(           # SI NO PUEDE LEER EL XML, LANZA ERROR
                f"No se pudo leer la plantilla QPT: {plantilla_path}"
            )

        layout = QgsPrintLayout(project)            # CREA UN NUEVO LAYOUT DE IMPRESIÓN EN EL PROYECTO
        layout.initializeDefaults()                 # INICIALIZA VALORES POR DEFECTO DEL LAYOUT

        items, ok = layout.loadFromTemplate(        # CARGA LOS ELEMENTOS DEL QPT EN EL LAYOUT
            doc,                                    # DOCUMENTO XML DE LA PLANTILLA
            QgsReadWriteContext()                   # CONTEXTO DE LECTURA/ESCRITURA
        )

        if not ok:                                  # COMPRUEBA SI LA PLANTILLA SE CARGÓ CORRECTAMENTE
            raise QgsProcessingException(           # SI FALLÓ, LANZA ERROR
                f"No se pudo cargar la plantilla QPT: {plantilla_path}"
            )

        return layout                               # DEVUELVE EL LAYOUT YA CARGADO


    # =====================================================
    # 5. OBTENER ELEMENTOS DE PLANTILLA
    # INPUT:
    #   layout = composición cargada desde plantilla
    # OUTPUT:
    #   map_item = elemento mapa
    #   titulo = elemento texto título
    #   cajetin = elemento texto cajetín
    # =====================================================
    def obtener_elementos_plantilla(self, layout):  # FUNCIÓN PARA BUSCAR ELEMENTOS NECESARIOS EN LA PLANTILLA

        map_item = layout.itemById(self.ID_MAPA)    # BUSCA EN EL LAYOUT EL ELEMENTO CON ID "mapa"
        titulo = layout.itemById(self.ID_TITULO)    # BUSCA EN EL LAYOUT EL ELEMENTO CON ID "titulo"
        cajetin = layout.itemById(self.ID_CAJETIN)  # BUSCA EN EL LAYOUT EL ELEMENTO CON ID "cajetin"

        if map_item is None:                        # COMPRUEBA SI NO EXISTE EL MAPA
            raise QgsProcessingException(           # LANZA ERROR SI FALTA EL ELEMENTO
                f"La plantilla no tiene un elemento con ID '{self.ID_MAPA}'"
            )

        if titulo is None:                          # COMPRUEBA SI NO EXISTE EL TÍTULO
            raise QgsProcessingException(           # LANZA ERROR SI FALTA EL ELEMENTO
                f"La plantilla no tiene un elemento con ID '{self.ID_TITULO}'"
            )

        if cajetin is None:                         # COMPRUEBA SI NO EXISTE EL CAJETÍN
            raise QgsProcessingException(           # LANZA ERROR SI FALTA EL ELEMENTO
                f"La plantilla no tiene un elemento con ID '{self.ID_CAJETIN}'"
            )

        return map_item, titulo, cajetin            # DEVUELVE LOS TRES ELEMENTOS LOCALIZADOS

    # =====================================================
    # 6. CONFIGURAR LEYENDA DEL PDF
    # INPUT:
    #   layout = composición QPT cargada
    #   map_item = elemento mapa
    #   background = _TEMP_GPKG/XX_XXX.gpkg
    #   incidencias = Envio/Incidencias_XXXXX.gpkg
    # OUTPUT:
    #   leyenda configurada con INCIDENCIAS + PARCELARIO CATASTRAL
    # =====================================================
    def configurar_leyenda(self, layout, map_item, background, incidencias, feedback): # FUNCIÓN PARA CONFIGURAR LA LEYENDA

        leyenda = layout.itemById(self.ID_LEYENDA) # BUSCA EL ELEMENTO CON ID "leyenda"
        cuadro = layout.itemById(self.ID_CUADRO_LEYENDA) # BUSCA EL RECTÁNGULO CONTENEDOR "cuadro_leyenda"

        if leyenda is None:                        # SI NO EXISTE LA LEYENDA
            feedback.pushInfo("Aviso: no existe elemento de leyenda con ID 'leyenda'") # AVISA
            return                                  # SALE SIN PARAR EL SCRIPT

        if not isinstance(leyenda, QgsLayoutItemLegend): # COMPRUEBA SI EL ELEMENTO ES REALMENTE UNA LEYENDA
            feedback.pushInfo("Aviso: el elemento con ID 'leyenda' no es una leyenda de QGIS") # AVISA
            return                                  # SALE SIN CONFIGURAR LA LEYENDA

        incidencias.setName("INCIDENCIAS")         # CAMBIA EL NOMBRE VISIBLE DE LA CAPA DE INCIDENCIAS EN LA LEYENDA
        background.setName("PARCELARIO CATASTRAL") # CAMBIA EL NOMBRE VISIBLE DE LA CAPA DE FONDO EN LA LEYENDA

        if cuadro is not None:                      # SI EXISTE EL RECTÁNGULO cuadro_leyenda
            try:                                    # INTENTA MOVER Y REDIMENSIONAR LA LEYENDA
                leyenda.attemptMove(cuadro.positionWithUnits()) # MUEVE LA LEYENDA A LA POSICIÓN DEL CUADRO
                leyenda.attemptResize(cuadro.sizeWithUnits()) # REDIMENSIONA LA LEYENDA AL TAMAÑO DEL CUADRO
            except Exception:                       # SI FALLA EL AJUSTE
                pass                                # CONTINÚA SIN PARAR EL SCRIPT
        else:                                       # SI NO EXISTE EL CUADRO
            feedback.pushInfo("Aviso: no existe rectángulo contenedor con ID 'cuadro_leyenda'") # AVISA

        leyenda.setLinkedMap(map_item)              # VINCULA LA LEYENDA AL MAPA DEL LAYOUT
        leyenda.setAutoUpdateModel(False)           # DESACTIVA ACTUALIZACIÓN AUTOMÁTICA PARA CONTROLAR CAPAS MANUALMENTE

        root = leyenda.model().rootGroup()          # OBTIENE EL GRUPO RAÍZ DE LA LEYENDA
        root.clear()                                # LIMPIA LAS CAPAS EXISTENTES DE LA LEYENDA

        root.addLayer(incidencias)                  # AÑADE LA CAPA INCIDENCIAS A LA LEYENDA
        root.addLayer(background)                   # AÑADE LA CAPA PARCELARIO CATASTRAL A LA LEYENDA

        try:                                        # INTENTA PONER TÍTULO A LA LEYENDA
            leyenda.setTitle("LEYENDA")             # ESTABLECE EL TÍTULO "LEYENDA"
        except Exception:                           # SI NO PUEDE
            pass                                    # CONTINÚA SIN PARAR

        leyenda.adjustBoxSize()                     # AJUSTA EL TAMAÑO DE LA CAJA AL CONTENIDO
        leyenda.update()                            # ACTUALIZA LA LEYENDA
        leyenda.refresh()                           # REFRESCA LA LEYENDA


    # =====================================================
    # 7. CALCULAR EXTENSIÓN AJUSTADA AL MARCO DEL MAPA
    # INPUT:
    #   geom = geometría de una incidencia
    #   map_item = elemento mapa de la plantilla
    # OUTPUT:
    #   QgsRectangle = extensión centrada y ajustada al formato del mapa
    # =====================================================
    def calcular_extension_ajustada(self, geom, map_item): # FUNCIÓN PARA CALCULAR LA EXTENSIÓN DEL MAPA EN CADA PDF

        bbox = geom.boundingBox()                   # OBTIENE EL RECTÁNGULO MÍNIMO QUE ENVUELVE LA INCIDENCIA

        centro_x = bbox.center().x()                # OBTIENE COORDENADA X DEL CENTRO DE LA INCIDENCIA
        centro_y = bbox.center().y()                # OBTIENE COORDENADA Y DEL CENTRO DE LA INCIDENCIA

        ancho_geom = bbox.width()                   # OBTIENE ANCHO DE LA INCIDENCIA
        alto_geom = bbox.height()                   # OBTIENE ALTO DE LA INCIDENCIA

        if ancho_geom <= 0:                         # SI EL ANCHO ES <= 0
            ancho_geom = self.TAMANO_MINIMO         # USA TAMAÑO MÍNIMO

        if alto_geom <= 0:                          # SI EL ALTO ES <= 0
            alto_geom = self.TAMANO_MINIMO          # USA TAMAÑO MÍNIMO

        ancho_geom *= self.FACTOR_MARGEN            # APLICA MARGEN AL ANCHO
        alto_geom *= self.FACTOR_MARGEN             # APLICA MARGEN AL ALTO

        if ancho_geom < self.TAMANO_MINIMO:         # SI EL ANCHO QUEDA MENOR QUE EL MÍNIMO
            ancho_geom = self.TAMANO_MINIMO         # LO SUBE AL MÍNIMO

        if alto_geom < self.TAMANO_MINIMO:          # SI EL ALTO QUEDA MENOR QUE EL MÍNIMO
            alto_geom = self.TAMANO_MINIMO          # LO SUBE AL MÍNIMO

        rect_mapa = map_item.rect()                 # OBTIENE EL RECTÁNGULO DEL MAPA EN LA PLANTILLA
        ancho_mapa = rect_mapa.width()              # OBTIENE ANCHO DEL MAPA EN LA PLANTILLA
        alto_mapa = rect_mapa.height()              # OBTIENE ALTO DEL MAPA EN LA PLANTILLA

        if alto_mapa == 0:                          # COMPRUEBA QUE EL ALTO DEL MAPA NO SEA 0
            raise QgsProcessingException(           # SI ES 0, LANZA ERROR
                "El elemento mapa de la plantilla tiene altura 0"
            )

        proporcion_mapa = ancho_mapa / alto_mapa    # CALCULA PROPORCIÓN ANCHO/ALTO DEL MAPA
        proporcion_geom = ancho_geom / alto_geom    # CALCULA PROPORCIÓN ANCHO/ALTO DE LA INCIDENCIA

        if proporcion_geom > proporcion_mapa:       # SI LA INCIDENCIA ES MÁS ANCHA QUE EL MAPA
            ancho_final = ancho_geom                # MANDA EL ANCHO DE LA INCIDENCIA
            alto_final = ancho_final / proporcion_mapa # CALCULA ALTO NECESARIO PARA RESPETAR PROPORCIÓN DEL MAPA
        else:                                       # SI LA INCIDENCIA ES MÁS ALTA O MÁS ESTRECHA
            alto_final = alto_geom                  # MANDA EL ALTO DE LA INCIDENCIA
            ancho_final = alto_final * proporcion_mapa # CALCULA ANCHO NECESARIO PARA RESPETAR PROPORCIÓN DEL MAPA

        xmin = centro_x - ancho_final / 2           # CALCULA X MÍNIMA DE LA EXTENSIÓN
        xmax = centro_x + ancho_final / 2           # CALCULA X MÁXIMA DE LA EXTENSIÓN
        ymin = centro_y - alto_final / 2            # CALCULA Y MÍNIMA DE LA EXTENSIÓN
        ymax = centro_y + alto_final / 2            # CALCULA Y MÁXIMA DE LA EXTENSIÓN

        return QgsRectangle(xmin, ymin, xmax, ymax) # DEVUELVE LA EXTENSIÓN FINAL PARA EL MAPA
        
    # =====================================================
    # 8. NÚMERO REDONDEADO PARA ESCALA
    # INPUT:
    #   valor = distancia máxima calculada para la barra de escala
    # OUTPUT:
    #   número redondeado tipo 1, 2, 5, 10, 20, 50, 100...
    # =====================================================
    def numero_bonito_inferior(self, valor):        # FUNCIÓN PARA REDONDEAR DISTANCIAS DE ESCALA

        if valor <= 0:                              # SI EL VALOR ES 0 O NEGATIVO
            return 1                                # DEVUELVE 1 COMO VALOR SEGURO

        exponente = math.floor(math.log10(valor))   # CALCULA EL EXPONENTE BASE 10 DEL VALOR
        base = 10 ** exponente                      # CREA LA BASE 10, 100, 1000, ETC.
        fraccion = valor / base                     # CALCULA LA FRACCIÓN ENTRE 1 Y 10

        if fraccion >= 5:                           # SI LA FRACCIÓN ES 5 O MÁS
            bonito = 5                              # USA 5 COMO NÚMERO REDONDO
        elif fraccion >= 2:                         # SI LA FRACCIÓN ES 2 O MÁS
            bonito = 2                              # USA 2 COMO NÚMERO REDONDO
        else:                                       # SI ES MENOR QUE 2
            bonito = 1                              # USA 1 COMO NÚMERO REDONDO

        return bonito * base                        # DEVUELVE EL NÚMERO REDONDO FINAL

    # =====================================================
    # 9. OBTENER BARRAS DE ESCALA
    # INPUT:
    #   layout = composición cargada desde QPT
    # OUTPUT:
    #   barras = lista de barras de escala encontradas
    # =====================================================
    def obtener_barras_escala(self, layout):        # BUSCA TODAS LAS BARRAS DE ESCALA DEL LAYOUT

        barras = []                                 # CREA LISTA VACÍA DE BARRAS DE ESCALA

        escala_id = layout.itemById(self.ID_ESCALA) # BUSCA ELEMENTO CON ID "escala"

        if escala_id is not None and isinstance(escala_id, QgsLayoutItemScaleBar): # SI EXISTE Y ES BARRA DE ESCALA
            barras.append(escala_id)                # LA AÑADE A LA LISTA

        for item in layout.items():                 # RECORRE TODOS LOS ELEMENTOS DEL LAYOUT
            if isinstance(item, QgsLayoutItemScaleBar): # SI EL ELEMENTO ES UNA BARRA DE ESCALA
                if item not in barras:              # SI NO ESTÁ YA EN LA LISTA
                    barras.append(item)             # LA AÑADE

        return barras                               # DEVUELVE LISTA DE BARRAS DE ESCALA


    # =====================================================
    # 10. OBTENER ANCHO DEL CUADRO DE ESCALA
    # INPUT:
    #   layout = composición QPT
    #   scalebar = barra de escala
    # OUTPUT:
    #   ancho disponible en mm para que no se salga del cuadro
    # =====================================================
    def obtener_ancho_cuadro_escala(self, layout, scalebar): # CALCULA ANCHO MÁXIMO DISPONIBLE PARA LA ESCALA

        cuadro = layout.itemById(self.ID_CUADRO_ESCALA) # BUSCA EL RECTÁNGULO "cuadro_escala"

        if cuadro is not None:                       # SI EXISTE EL CUADRO
            ancho = cuadro.rect().width()            # OBTIENE SU ANCHO

            if ancho > 0:                            # SI EL ANCHO ES VÁLIDO
                return ancho * self.FACTOR_ANCHO_ESCALA # DEVUELVE EL 85 % DEL ANCHO PARA DEJAR MARGEN

        ancho_barra = scalebar.rect().width()        # SI NO HAY CUADRO, USA EL ANCHO DE LA BARRA

        if ancho_barra > 0:                          # SI LA BARRA TIENE ANCHO VÁLIDO
            return ancho_barra * self.FACTOR_ANCHO_ESCALA # DEVUELVE EL 85 %

        return 35                                    # SI NO HAY NINGÚN DATO VÁLIDO, USA 35 mm POR DEFECTO

    # =====================================================
    # 11. AJUSTAR BARRA DE ESCALA AL RECTÁNGULO cuadro_escala
    # INPUT:
    #   layout = composición QPT
    #   map_item = elemento mapa
    #   extent = extensión actual del mapa
    # OUTPUT:
    #   barra de escala ajustada al ancho permitido
    # =====================================================
    def ajustar_barras_escala(self, layout, map_item, extent): # AJUSTA LA BARRA DE ESCALA PARA QUE NO SE SALGA DEL CUADRO

        barras = self.obtener_barras_escala(layout) # OBTIENE TODAS LAS BARRAS DE ESCALA DEL LAYOUT

        if not barras:                              # SI NO HAY BARRAS DE ESCALA
            return                                  # SALE SIN HACER NADA

        ancho_mapa_mm = map_item.rect().width()     # OBTIENE EL ANCHO DEL MAPA EN MILÍMETROS EN EL LAYOUT
        ancho_terreno_m = extent.width()            # OBTIENE EL ANCHO REAL DEL TERRENO EN METROS

        if ancho_mapa_mm <= 0 or ancho_terreno_m <= 0: # SI ALGÚN ANCHO NO ES VÁLIDO
            return                                  # SALE SIN AJUSTAR

        for scalebar in barras:                     # RECORRE CADA BARRA DE ESCALA

            scalebar.setLinkedMap(map_item)         # VINCULA LA BARRA AL MAPA

            ancho_max_barra_mm = self.obtener_ancho_cuadro_escala( # CALCULA ANCHO MÁXIMO PERMITIDO
                layout,                             # LAYOUT
                scalebar                            # BARRA DE ESCALA
            )

            distancia_max_m = ancho_terreno_m * (   # CALCULA CUÁNTOS METROS CABEN EN EL ANCHO DISPONIBLE
                ancho_max_barra_mm / ancho_mapa_mm  # RELACIÓN ENTRE ANCHO DE BARRA Y ANCHO DE MAPA
            )

            segmentos = 4                           # EMPIEZA CON 4 SEGMENTOS

            distancia_segmento_m = self.numero_bonito_inferior( # CALCULA DISTANCIA BONITA POR SEGMENTO
                distancia_max_m / segmentos         # DISTANCIA MÁXIMA DIVIDIDA ENTRE SEGMENTOS
            )

            if distancia_segmento_m <= 0:           # SI LA DISTANCIA NO ES VÁLIDA
                distancia_segmento_m = 1            # USA 1 METRO

            distancia_total_m = distancia_segmento_m * segmentos # CALCULA DISTANCIA TOTAL DE LA BARRA

            while segmentos > 1:                    # MIENTRAS HAYA MÁS DE 1 SEGMENTO

                ancho_estimado_mm = (               # CALCULA ANCHO ESTIMADO DE LA BARRA EN MM
                    distancia_total_m / ancho_terreno_m # RELACIÓN ENTRE DISTANCIA BARRA Y ANCHO TERRENO
                ) * ancho_mapa_mm                   # CONVIERTE ESA RELACIÓN A MILÍMETROS

                if ancho_estimado_mm <= ancho_max_barra_mm: # SI LA BARRA CABE EN EL CUADRO
                    break                           # SALE DEL BUCLE

                segmentos -= 1                      # SI NO CABE, REDUCE UN SEGMENTO
                distancia_total_m = distancia_segmento_m * segmentos # RECALCULA DISTANCIA TOTAL

            if segmentos <= 1:                      # SI SOLO QUEDA 1 SEGMENTO
                segmentos = 1                       # FIJA 1 SEGMENTO
                distancia_segmento_m = self.numero_bonito_inferior( # RECALCULA DISTANCIA BONITA
                    distancia_max_m                 # USA LA DISTANCIA MÁXIMA DISPONIBLE
                )

            if distancia_segmento_m >= 1000:        # SI EL SEGMENTO ES DE 1000 m O MÁS
                scalebar.setUnits(QgsUnitTypes.DistanceKilometers) # USA KILÓMETROS
                scalebar.setUnitsPerSegment(distancia_segmento_m / 1000) # CONVIERTE METROS A KM
                scalebar.setUnitLabel("km")         # ETIQUETA DE UNIDAD km
            else:                                   # SI ES MENOR DE 1000 m
                scalebar.setUnits(QgsUnitTypes.DistanceMeters) # USA METROS
                scalebar.setUnitsPerSegment(distancia_segmento_m) # METROS POR SEGMENTO
                scalebar.setUnitLabel("m")          # ETIQUETA DE UNIDAD m

            scalebar.setNumberOfSegments(segmentos) # ASIGNA NÚMERO DE SEGMENTOS A LA DERECHA
            scalebar.setNumberOfSegmentsLeft(0)     # NO USA SEGMENTOS A LA IZQUIERDA

            try:                                    # INTENTA FIJAR ANCHO MÁXIMO
                scalebar.setMaximumBarWidth(ancho_max_barra_mm) # ANCHO MÁXIMO DE LA BARRA
            except Exception:                       # SI NO SE PUEDE
                pass                                # CONTINÚA

            try:                                    # INTENTA FIJAR ANCHO MÍNIMO
                scalebar.setMinimumBarWidth(ancho_max_barra_mm * 0.25) # ANCHO MÍNIMO 25 %
            except Exception:                       # SI NO SE PUEDE
                pass                                # CONTINÚA

            scalebar.update()                       # ACTUALIZA LA BARRA DE ESCALA
            scalebar.refresh()                      # REFRESCA LA BARRA DE ESCALA
 
    # =====================================================
    # 12. EXPORTAR PDF DE INCIDENCIAS DE UN MUNICIPIO
    # INPUT:
    #   incidencias_path = Envio/Incidencias_XXXXX.gpkg
    #   background_path = _TEMP_GPKG/XX_XXX.gpkg
    #   output_pdf_folder = Envio/PDF_XXXXX
    #   code = código municipio XX_XXX
    #   plantilla_path = archivo QPT seleccionado
    # OUTPUT:
    #   INC_0001.pdf, INC_0002.pdf, INC_0003.pdf...
    # =====================================================
    def exportar_pdfs_incidencias(
        self,
        incidencias_path,                           # RUTA DE LA CAPA FINAL DE INCIDENCIAS
        background_path,                            # RUTA DE LA CAPA DE FONDO DEL MUNICIPIO
        output_pdf_folder,                          # CARPETA DONDE SE GUARDARÁN LOS PDF
        code,                                       # CÓDIGO DEL MUNICIPIO EN FORMATO XX_XXX
        plantilla_path,                             # RUTA DE LA PLANTILLA QPT
        context,                                    # CONTEXTO DE EJECUCIÓN DE QGIS
        feedback                                    # MENSAJES Y PROGRESO DEL PROCESO
    ):

        if not incidencias_path or not os.path.exists(incidencias_path): # COMPRUEBA SI EXISTE LA CAPA DE INCIDENCIAS
            feedback.pushInfo("No existe capa de incidencias para generar PDFs") # AVISA SI NO EXISTE
            return                                  # SALE DE LA FUNCIÓN SIN GENERAR PDF

        if not background_path or not os.path.exists(background_path): # COMPRUEBA SI EXISTE LA CAPA DE FONDO
            feedback.pushInfo("No existe capa de fondo para generar PDFs") # AVISA SI NO EXISTE
            return                                  # SALE DE LA FUNCIÓN SIN GENERAR PDF

        if not plantilla_path or not os.path.exists(plantilla_path): # COMPRUEBA SI EXISTE LA PLANTILLA QPT
            raise QgsProcessingException(           # SI NO EXISTE, LANZA ERROR Y DETIENE EL PROCESO
                f"No existe la plantilla de mapas QPT: {plantilla_path}" # MENSAJE DE ERROR
            )

        os.makedirs(output_pdf_folder, exist_ok=True) # CREA LA CARPETA DE PDF SI NO EXISTE

        codigo_sin_barra = code.replace("_", "")   # QUITA EL "_" DEL CÓDIGO, XX_XXX PASA A XXXXX

        layer = QgsVectorLayer(                     # CARGA LA CAPA DE INCIDENCIAS
            incidencias_path,                       # RUTA DEL GPKG DE INCIDENCIAS
            f"Incidencias_{codigo_sin_barra}",      # NOMBRE INTERNO DE LA CAPA EN QGIS
            "ogr"                                   # PROVEEDOR OGR PARA LEER GPKG/SHP
        )

        if layer is None or not layer.isValid():    # COMPRUEBA SI LA CAPA DE INCIDENCIAS NO SE HA CARGADO BIEN
            feedback.pushInfo(f"Capa de incidencias no válida: {incidencias_path}") # AVISA EN EL LOG
            return                                  # SALE SIN GENERAR PDF

        background = QgsVectorLayer(                # CARGA LA CAPA DE FONDO DEL MUNICIPIO
            background_path,                        # RUTA DEL GPKG TEMPORAL DEL MUNICIPIO BASE
            f"Fondo_{code}",                        # NOMBRE INTERNO DE LA CAPA
            "ogr"                                   # PROVEEDOR OGR
        )

        if background is None or not background.isValid(): # COMPRUEBA SI LA CAPA DE FONDO NO ES VÁLIDA
            feedback.pushInfo(f"Capa de fondo no válida: {background_path}") # AVISA EN EL LOG
            return                                  # SALE SIN GENERAR PDF

        project = QgsProject.instance()             # OBTIENE EL PROYECTO ACTUAL DE QGIS

        if project.mapLayer(background.id()) is None: # COMPRUEBA SI LA CAPA DE FONDO NO ESTÁ YA EN EL PROYECTO
            project.addMapLayer(background, False)  # AÑADE LA CAPA AL PROYECTO SIN MOSTRARLA EN EL PANEL DE CAPAS

        if project.mapLayer(layer.id()) is None:    # COMPRUEBA SI LA CAPA DE INCIDENCIAS NO ESTÁ YA EN EL PROYECTO
            project.addMapLayer(layer, False)       # AÑADE LA CAPA AL PROYECTO SIN MOSTRARLA EN EL PANEL DE CAPAS

        self.aplicar_estilo_fondo(background)       # APLICA ESTILO TRANSPARENTE Y BORDE NEGRO A LA CAPA DE FONDO
        self.activar_etiquetas_fondo(background)    # ACTIVA ETIQUETAS POLIGONO:PARCELA EN LA CAPA DE FONDO
        self.activar_etiquetas_incidencias(layer)   # ACTIVA ETIQUETAS INC: @id EN LA CAPA DE INCIDENCIAS

        total = layer.featureCount()                # CUENTA CUÁNTAS INCIDENCIAS TIENE LA CAPA

        if total == 0:                              # SI LA CAPA NO TIENE INCIDENCIAS
            feedback.pushInfo("La capa de incidencias no tiene entidades") # AVISA EN EL LOG
            return                                  # SALE SIN GENERAR PDF

        feedback.pushInfo(                          # ESCRIBE MENSAJE DE INICIO EN EL LOG
            f"→ Generando PDFs de incidencias para municipio {code}"
        )

        for index, feature in enumerate(layer.getFeatures()): # RECORRE CADA INCIDENCIA DE LA CAPA

            geom = feature.geometry()               # OBTIENE LA GEOMETRÍA DE LA INCIDENCIA ACTUAL

            if geom is None or geom.isEmpty():      # COMPRUEBA SI LA GEOMETRÍA ESTÁ VACÍA O NO EXISTE
                continue                            # SI ESTÁ VACÍA, PASA A LA SIGUIENTE INCIDENCIA

            numero = index + 1                      # CREA NÚMERO DE INCIDENCIA EMPEZANDO EN 1
            texto_inc = f"INC: {feature.id()}"      # CREA TEXTO DE ETIQUETA USANDO EL ID DE LA ENTIDAD

            feedback.pushInfo(f"Generando PDF: {code} - {texto_inc}") # MUESTRA EN EL LOG QUÉ PDF SE ESTÁ GENERANDO

            layout = self.cargar_layout_desde_plantilla( # CARGA LA PLANTILLA QPT COMO LAYOUT
                project,                             # PROYECTO QGIS ACTUAL
                plantilla_path                       # RUTA DEL QPT
            )

            layout.setName(f"Mapa_{code}_INC_{numero:04d}") # ASIGNA NOMBRE AL LAYOUT, EJEMPLO Mapa_46_011_INC_0001

            map_item, titulo, cajetin = self.obtener_elementos_plantilla(layout) # OBTIENE MAPA, TÍTULO Y CAJETÍN DEL QPT

            extent_ajustado = self.calcular_extension_ajustada( # CALCULA LA EXTENSIÓN DEL MAPA CENTRADA EN LA INCIDENCIA
                geom,                                # GEOMETRÍA DE LA INCIDENCIA
                map_item                             # ELEMENTO MAPA DE LA PLANTILLA
            )

            map_item.setLayers([background, layer])  # ASIGNA AL MAPA LAS CAPAS QUE SE VAN A DIBUJAR: FONDO + INCIDENCIAS
            map_item.setExtent(extent_ajustado)      # APLICA LA EXTENSIÓN CALCULADA AL MAPA
            map_item.refresh()                       # REFRESCA EL MAPA PARA ACTUALIZAR SU CONTENIDO

            self.configurar_leyenda(                 # CONFIGURA LA LEYENDA DEL PDF
                layout,                              # LAYOUT ACTUAL
                map_item,                            # MAPA DEL LAYOUT
                background,                          # CAPA DE FONDO
                layer,                               # CAPA DE INCIDENCIAS
                feedback                             # MENSAJES
            )

            self.ajustar_barras_escala(              # AJUSTA LA BARRA DE ESCALA AL CUADRO DE ESCALA
                layout,                              # LAYOUT ACTUAL
                map_item,                            # MAPA DEL LAYOUT
                extent_ajustado                      # EXTENSIÓN DEL MAPA
            )

            titulo.setText(f"{texto_inc} - Incidencias_{codigo_sin_barra}") # ESCRIBE EL TÍTULO DEL PDF
            titulo.adjustSizeToText()                # AJUSTA EL TAMAÑO DEL ELEMENTO TÍTULO AL TEXTO

            area = geom.area()                       # CALCULA EL ÁREA DE LA INCIDENCIA

            cajetin_texto = (                        # CREA EL TEXTO DEL CAJETÍN
                "DATOS DE LA INCIDENCIA\n"           # LÍNEA 1 DEL CAJETÍN
                f"Municipio: {code}\n"               # CÓDIGO DEL MUNICIPIO
                f"Nº incidencia: {numero:04d}\n"     # NÚMERO DE INCIDENCIA CON 4 DÍGITOS
                f"Etiqueta: {texto_inc}\n"           # ETIQUETA INC
                f"Área: {area:.2f} m²\n"             # ÁREA DE LA INCIDENCIA CON 2 DECIMALES
                f"Capa incidencias: INCIDENCIAS\n"   # NOMBRE DE LA CAPA DE INCIDENCIAS
                f"Capa fondo: PARCELARIO CATASTRAL"  # NOMBRE DE LA CAPA DE FONDO
            )

            cajetin.setText(cajetin_texto)           # ESCRIBE EL TEXTO EN EL ELEMENTO CAJETÍN
            cajetin.adjustSizeToText()               # AJUSTA EL TAMAÑO DEL CAJETÍN AL TEXTO

            for item in layout.items():              # RECORRE TODOS LOS ELEMENTOS DEL LAYOUT
                if hasattr(item, "setLinkedMap"):    # COMPRUEBA SI EL ELEMENTO PUEDE VINCULARSE AL MAPA
                    try:                             # INTENTA VINCULARLO
                        item.setLinkedMap(map_item)  # VINCULA EL ELEMENTO AL MAPA ACTUAL
                        item.refresh()               # REFRESCA EL ELEMENTO
                    except Exception:                # SI ALGÚN ELEMENTO FALLA
                        pass                         # CONTINÚA SIN PARAR EL SCRIPT

            nombre_pdf = f"INC_{numero:04d}.pdf"     # CREA EL NOMBRE DEL PDF, EJEMPLO INC_0001.pdf
            pdf_path = os.path.join(output_pdf_folder, nombre_pdf) # CREA LA RUTA COMPLETA DEL PDF

            self.borrar_si_existe(pdf_path)          # BORRA EL PDF SI YA EXISTÍA

            exporter = QgsLayoutExporter(layout)     # CREA EL EXPORTADOR DEL LAYOUT A PDF

            result = exporter.exportToPdf(           # EXPORTA EL LAYOUT A PDF
                pdf_path,                            # RUTA DEL PDF DE SALIDA
                QgsLayoutExporter.PdfExportSettings() # CONFIGURACIÓN DE EXPORTACIÓN PDF POR DEFECTO
            )

            if result != QgsLayoutExporter.Success:  # COMPRUEBA SI LA EXPORTACIÓN FALLÓ
                feedback.pushInfo(f"Error exportando PDF: {pdf_path}") # AVISA EN EL LOG
            else:                                    # SI LA EXPORTACIÓN FUE CORRECTA
                feedback.pushInfo(f"PDF generado: {pdf_path}") # AVISA EN EL LOG

        feedback.pushInfo(f"PDFs terminados para municipio {code}") # MENSAJE FINAL AL TERMINAR TODOS LOS PDF DEL MUNICIPIO
