# azotea

Pipeline Python de reducción de datos para [AZOTEA](https://guaix.ucm.es/AZOTEA) (Astronomía Zenital desde el hOgar en Tiempos de Extremo Aislamiento).

Esta es una herramienta de línea de comandos.


# Instalación y actualización

Instalar primero ***Python 3*** y su herramienta `pip`. Esta suele venir incluida en Linux y MacOS pero no así en Windows. Una vez que tenemos esto, se instala AZOTEA como sigue:

```bash
pip install --user azotea
```

Para actualizar a la última versión de AZOTEA, teclear:

```bash
pip install --user -U azotea
```


Comprobar la version instalada

```bash
~$ azotea --version
```

```
azotea 0.3.0
```


## Compatibilidad con Python 2

AZOTEA *No es compatible con Python 2*

# Configuracion

## Configuración global

Antes de poder operar con AZOTEA hay que crear un fichero de configuración para el observador.
La primera vez que se vaya a usar azotea, se puede hacer lo siguiente:

```bash
~$ azotea init
```


La inicialización creará un fichero `azotea.ini` en el directorio `$HOME/azotea/config` de cada usuario.
Editar el fichero con un block de notas o similar. Los campos son descriptivos y no debería haber ningin problema al rellenarlos.


## Camaras soportadas

AZOTEA se irá actualizando a medida que soporte más cámaras.

Los modelos de camara soportados hasta el momento se pueden ver listando el fichero de configuracion interno

```bash
azotea config camera --list
```

***Uso Avanzado, no recomendado***: Si hay necesidad de crar una entrada más a este fichero, se puede hacer una copia de él y luego editarlo de manera análoga a la configuración global. Este fichero no es para todo el mundo, sólo los que entienden cómo funciona el software deben hacerlo.


```bash
azotea config camera --create
```

```
2020-04-01 19:25:12,998 [INFO] Created /home/rafa/azotea/config/camera.ini file
```

Para probar la cámara comn este nuevo fichero en todos los comandos `azotea` posteriores hay que especificarlo como opción global antes de los comandos. Ejemplo:


```bash
azotea --camera mycamera.ini stats compute
```

# Operativa

## ***La version corta***

Para observadores impacientes que quieren reducir la observación una noche en un directorio.

1. Configurado el fichero `azotea.ini`, que debe residir en `$HOME/azotea/azotea.ini`

2. Volcar *todas* las imagenes de la cámara de una misma noche a un directorio de trabajo (p.e. `/home/rafa/demo/test`)

3. Si hay tomas *dark*, renombrar dichas tomas a `dark_<nombre original>`

4. ¡Por fin! ejecutar en una linea de comandos:

```bash
azotea image reduce --work-dir <directorio donde están las imágenes>
```

Si se desea detalle del proceso, ejecutar en su lugar

```bash
azotea --verbose image reduce --work-dir <directorio donde están las imágenes>
```

## Ejemplo de sesion de reducción

1. Primera inicializacion

```bash
~$ azotea init
```

```
2020-04-08 10:58:20,949 [INFO] Creating /home/rafa/azotea directory
2020-04-08 10:58:20,951 [INFO] Creating /home/rafa/azotea/config directory
2020-04-08 10:58:20,951 [INFO] Creating /home/rafa/azotea/dbase directory
2020-04-08 10:58:20,951 [INFO] Creating /home/rafa/azotea/backup directory
2020-04-08 10:58:20,951 [INFO] Creating /home/rafa/azotea/log directory
2020-04-08 10:58:20,951 [INFO] Created /home/rafa/azotea/config/azotea.ini file, please review it
2020-04-08 10:58:20,951 [INFO] Created database file /home/rafa/azotea/dbase/azotea.db
2020-04-08 10:58:21,451 [INFO] Created data model from schema.sql
2020-04-08 10:58:21,452 [INFO] Populating data model from auxiliar.sql
```

2. Reorganizacion de un lote de observaciones de varias noches

```bash
 ~$ azotea reorganize images --input-dir mis_observaciones --output-dir zamorano
```

```
2020-04-08 11:53:43,826 [INFO] read 6 images
2020-04-08 11:53:43,826 [INFO] creating 2 output directories
2020-04-08 11:53:43,826 [INFO] copying images to output directories
2020-04-08 11:53:43,885 [INFO] copied 6 images
```

3. Reducción separada de cada noche

***Noche del 25 al 26 de Marzo de 2020***

```bash
~$ azotea image reduce --work-dir zamorano/2020-03-25
```

```
2020-04-08 11:57:19,807 [INFO] Opening configuration file /home/rafa/azotea/config/azotea.ini
2020-04-08 11:57:19,807 [INFO] Found 3 candidate images
2020-04-08 11:57:19,867 [INFO] 2020_03_2523_59_139999.CR2 from Canon EOS 450D being registered in database
2020-04-08 11:57:19,922 [INFO] 2020_03_2522_50_529999.CR2 from Canon EOS 450D being registered in database
2020-04-08 11:57:19,992 [INFO] 2020_03_2519_07_239999.CR2 from Canon EOS 450D being registered in database
2020-04-08 11:57:20,064 [INFO] 3 new images registered in database
2020-04-08 11:57:20,489 [INFO] 2020_03_2523_59_139999.CR2: ROI = [828:1328,519:919], μ = [1082.4, 1105.8, 1104.8, 1067.0], σ = [41.3, 55.5, 59.4, 27.6] 
2020-04-08 11:57:20,875 [INFO] 2020_03_2522_50_529999.CR2: ROI = [828:1328,519:919], μ = [1119.1, 1147.3, 1146.4, 1079.2], σ = [42.9, 53.3, 57.5, 22.0] 
2020-04-08 11:57:21,306 [INFO] 2020_03_2519_07_239999.CR2: ROI = [828:1328,519:919], μ = [3688.1, 10030.8, 10050.6, 13061.8], σ = [496.2, 1303.5, 1298.6, 1311.0] 
2020-04-08 11:57:21,398 [INFO] 2020_03_2523_59_139999.CR2 is type LIGHT
2020-04-08 11:57:21,398 [INFO] 2020_03_2522_50_529999.CR2 is type LIGHT
2020-04-08 11:57:21,398 [INFO] 2020_03_2519_07_239999.CR2 is type LIGHT
2020-04-08 11:57:21,466 [INFO] Saved data to session  CSV file /home/rafa/azotea/session-2020-03-25.csv
```

***Noche del 25 al 26 de Marzo de 2020***

```bash
~$ azotea image reduce --work-dir zamorano/2020-03-26
```

```
2020-04-08 11:57:41,103 [INFO] Opening configuration file /home/rafa/azotea/config/azotea.ini
2020-04-08 11:57:41,103 [INFO] Found 3 candidate images
2020-04-08 11:57:41,163 [INFO] 2020_03_2600_00_199999.CR2 from Canon EOS 450D being registered in database
2020-04-08 11:57:41,219 [INFO] 2020_03_2602_45_139999.CR2 from Canon EOS 450D being registered in database
2020-04-08 11:57:41,274 [INFO] 2020_03_2604_31_319999.CR2 from Canon EOS 450D being registered in database
2020-04-08 11:57:41,343 [INFO] 3 new images registered in database
2020-04-08 11:57:41,756 [INFO] 2020_03_2600_00_199999.CR2: ROI = [828:1328,519:919], μ = [1082.5, 1106.0, 1105.0, 1067.2], σ = [41.5, 55.3, 59.5, 27.7] 
2020-04-08 11:57:42,141 [INFO] 2020_03_2602_45_139999.CR2: ROI = [828:1328,519:919], μ = [1085.3, 1110.0, 1109.3, 1068.6], σ = [37.6, 51.8, 55.8, 23.9] 
2020-04-08 11:57:42,524 [INFO] 2020_03_2604_31_319999.CR2: ROI = [828:1328,519:919], μ = [1087.0, 1117.6, 1116.7, 1077.4], σ = [43.6, 86.3, 88.5, 64.9] 
2020-04-08 11:57:42,599 [INFO] 2020_03_2600_00_199999.CR2 is type LIGHT
2020-04-08 11:57:42,599 [INFO] 2020_03_2602_45_139999.CR2 is type LIGHT
2020-04-08 11:57:42,600 [INFO] 2020_03_2604_31_319999.CR2 is type LIGHT
2020-04-08 11:57:42,667 [INFO] Saved data to session  CSV file /home/rafa/azotea/session-2020-03-26.csv
```

La observacion de la noches se deja en los ficheros CSV `$HOME/azotea/session-2020-03-25.csv` y `$HOME/azotea/session-2020-03-26.csv` respectivamente

4. Obtencion de un fichero global CSV con todas las mediciones de todas las sesiones de reduccion de datos

```bash
~$ azotea image export --all
```

```
2020-04-08 11:58:33,750 [INFO] Saved data to global CSV file /home/rafa/azotea/azotea.csv
```


5. Volver a reprocesar un directorio 

Si hemos cambiado la region de interes en el fichero config.ini, 
debemos reprocesar los directorios que nos interese, especificando la opcion --reset.


```bash
~$ azotea image reduce --reset --work-dir zamorano/2020-03-26
```


## Por si todo va mal ...


```bash
~$ azotea database clear
```

```
2020-04-08 11:49:57,045 [INFO] Cleared data from database azotea.db
```

Y a empezar el proceso desde el punto 3.

# Procesado para varios observadores

## Fichero de camaras

Para ir añadiendo camaras no conocidas hasta la fecha a un fichero:

```bash
azotea config camera --create
emacs ~$/azotea/config/camera.ini
```

## Por cada observador:

1. Preparar su fichero exclusivo de configuracion global y colocarlo en $HOME/azotea/config/

```bash
cp $HOME/azotea/config/azotea.ini $HOME/azotea/config/jizquierdo.ini
emacs $HOME/azotea/config/jizquierdo.ini
```

2. Recolectar las imágenes de los observadores cada una en un direcorio distinto

```bash
mkdir contribuciones/jizquierdo
```

3. Reorganizar las imagenes por noche de observacion

```bash
azotea reorganize images --input-dir contribuciones/jizquierdo --output-dir clasificadas/jizquierdo
ls clasificadas/jizquierdo
```

4. Reducir las imágenes usuando su fichero de configuración

```
azotea --config ~/azotea/config/jizquierdo.ini --camera ~/azotea/config/camera.ini image reduce --work-dir clasificadas/jizquierdo/<directorio de fecha>

## Cuando hemos terminado

1. Exportar el fichero global que incluye las contribuciones de todos los observadores


```bash
~$ azotea image export --all
```


## La version larga

### Pîpeline de reducción de datos

AZOTEA es un programa que lleva una pequeña base de datos incorporada para recordar los valores medidos y el estado de procesamiento de las imagenes. El usuario nunca trata con la base de datos directamente sino que actua con comandos. Las imagenes nunca se modifican ni se cambian de lugar y tipicamente se genera una sesion de procesado con el lote de imágenes del directorio de trabajo. Lo habitual sería un directorio por día lleno de imagenes.

Los datos de interés se guardan en la base de datos y a partir de ellos se generan ficheros para publicar o compartir. 

Si la base de datos se corrompe o se borra, para recuperar su contenido habría que correr el pipeline de reduccióm de imágenes con todos los directorios que se hayan generado, cosa no siempre posible. Por ello se incluyen comandos de backup de la base de datos.

El pipeline de AZOTEA consta de los siguientes pasos en secuencia:

* Registro de las imágenes en la base de datos
* Calculo de estadístcas en la región de interés (ROI) (media y varianza)
* Clasificacion de las imagenes den LIGHT y DARK para la sustracción de cuadro oscuro
* Elaboración de un DARK maestro por cada directorio de trabajo si es que hay imágenes de tipo DARK y sustracción del nivel de oscuro a las tomas de tipo LIGHT.
* Exportación de los resultados de la sesion de reducción. En la actualidad sólo se soporta un solo formato de tipo CSV

Todos estos pasos se efectuan secuencialmente con `azotea image reduce`
Opcionalmente se puede invocar `azotea image export --all` sin especificar directorio de trabajo para exportar en un sencillo CSV todas las seisones de reducción.

### Otros comandos

AZOTEA tiene otros comandos para
1. efectuar y listar backups de la base de datos
2. limpiar o recrear la base de datos desde cero.

# Ficheros CSV de salida

El pipeline de reducción genera dos ficheros CSV:

* Un fichero global CSV donde se van acumulando todos los datos de todos los lotes procesados hasta el momento: `azotea.csv`

* Un fichero CSV con los resultados de la reducción del último lote. Si el lote solo abarca un directorio de trabajo, el nombre será `session-<directorio de trabajo>.csv`. Si el lote comprende varios directorios de trabajo, el fichero incluye el identificador del lote, no el directorio de trabajo `session-YYYYMMDDHHMMSS.csv` (Ejemplo: `session-20200402103223.csv`)


Ambos ficheros se situan en la el directorio raiz (`$HOME`) de cada usuario.

El fichero CSV tiene una cabecera con los nombres de las columnas, a saber:


|    Columna      |  Descripcion                                           |
|:---------------:|:-------------------------------------------------------|
| session         | Id. de sesion de reducción de datos (YYYYMMDDHHMMSS).  |
| observer        | Nombre del observador.                                 |
| organization    | Organizacion a la que pertenece el observador.         |
| location        | Localidad desde donde ha sido tomada la imagen.        |
| type            | Tipo de imagen (LIGHT/DARK)                            |
| tstamp          | Fecha y hora de la imagen, formato ISO 8601            |
| name            | Nombre de la imagen (=nombre del fichero sin la ruta.) |
| model           | Modelo de cámara.                                      |
| ISO             | Sensibilidad ISO de la toma.                           |
| roi             | Region de interés [x1:x2, y1:y2]                       |
| dark_roi        | Region de interes para medida oscura [x1:x2, y1:y2]    |
| exptime         | Tiempo de exposicion                                   |
| mean_signal_R1  | Promedio de señal canal R.                             |
| stdev_signal_R1 | Desviación tipica señal del canal R.                   |
| mean_signal_G2  | Promedio de señal en un canal G.                       |
| stdev_signal_G2 | Desviación tipica de señal en un canal G.              |
| mean_signal_G3  | Promedio de señal en el otro canal G.                  |
| stdev_signal_G3 | Desviación tipica de señal en el otro canal G.         |
| mean_signal_B4  | Promedio de señal del canal B.                         |
| stdev_signal_B4 | Desviación tipica señal del canal B.                   |

# Referencia de comandos

1. Version del programa

```bash 
azotea --version
```

2. Comandos

La lista de comandos soportados por AZOTEA puede ir cambiando con las versiones. Aún así siempre se podrán averiguar todos con la opcion --help en cada nivel.


La invocación de AZOTEA tiene la forma general de:

```
azotea [--opcion1, --opcion2, ...] <comando>  <subcomando> [--opcion3, --opcion4, ...]
```

Cada comando y subcomando dentro del comando tienen su propia ayuda:

```bash
azotea --help
azotea <comando> --help
azotea <comando> <subcomando> --help
```

Ejemplos:

```bash
azotea --help
azotea image --help
azotea image list --help
```

