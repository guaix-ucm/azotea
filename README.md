# azotea

Pipeline Python de reducción de datos para [AZOTEA](https://guaix.ucm.es/AZOTEA) (Astronomía Zenital desde el hOgar en Tiempos de Extremo Aislamiento).

Esta es una herramienta de línea de comandos.

## Introducción

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
Opcionalmente se puede invocar `azotea image export ` sin especificar directorio de trabajo para exportar en un sencillo CSV todas las seisones de reducción.

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


## Version de Python

AZOTEA necesita Python 3.6 o superior.
AZOTEA *No es compatible con Python 2*


# Configuracion

## Configuración global

Antes de poder operar con AZOTEA hay que crear un fichero de configuración para el observador.
La primera vez que se vaya a usar azotea, se puede hacer lo siguiente:

```bash
~$ azotea init
```


La inicialización creará:
* Un directorio  `$HOME/azotea/` donde se irán colocando ficheros de configuración, logs, informes CSV, etc.
* un fichero `azotea.ini` en el directorio `$HOME/azotea/config` de cada usuario.

***IMPORTANTE***: Editar el fichero con un block de notas o similar. Los campos son descriptivos y no debería haber ningin problema al rellenarlos.


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
azotea --camera /home/rafa/azotea/config/camera.ini image reduce --work-dir <directorio>
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
2020-04-16 11:02:38,937 [INFO] Creating /home/rafa/azotea directory
2020-04-16 11:02:38,939 [INFO] Creating /home/rafa/azotea/config directory
2020-04-16 11:02:38,939 [INFO] Creating /home/rafa/azotea/dbase directory
2020-04-16 11:02:38,939 [INFO] Creating /home/rafa/azotea/backup directory
2020-04-16 11:02:38,940 [INFO] Creating /home/rafa/azotea/log directory
2020-04-16 11:02:38,940 [INFO] Created /home/rafa/azotea/config/azotea.ini file, please review it
2020-04-16 11:02:38,940 [INFO] Created database file /home/rafa/azotea/dbase/azotea.db
2020-04-16 11:02:39,375 [INFO] Created data model from schema.sql
2020-04-16 11:02:39,376 [INFO] Populating data model from auxiliar.sql
```

2. Reorganizacion de un lote de observaciones de varias noches

```bash
 ~$ azotea reorganize images --input-dir todas_mis_observaciones --output-dir zamorano
```

```
2020-04-08 11:53:43,826 [INFO] Read 6 images
2020-04-08 11:53:43,826 [INFO] Creating 2 output directories
2020-04-08 11:53:43,826 [INFO] Copying images to output directories
2020-04-08 11:53:43,885 [INFO] Copied 6 images
```

3. Reducción separada de una noche

***Noche del 25 al 26 de Marzo de 2020***

```bash
~$ azotea image reduce --work-dir zamorano/2020-03-25
```

```
2020-04-16 11:15:45,112 [INFO] Created data model from schema.sql
2020-04-16 11:15:45,113 [INFO] Populating data model from auxiliar.sql
2020-04-16 11:15:45,313 [INFO] Opening configuration file /home/rafa/azotea/config/azotea.ini
2020-04-16 11:15:45,315 [INFO] Found 3 candidates matching filter *.*
2020-04-16 11:15:45,316 [INFO] ==> Start reduction session, id = 20200416091545
2020-04-16 11:15:45,449 [INFO] Registered 3 images in database
2020-04-16 11:15:45,579 [INFO] 3 new images registered in database
2020-04-16 11:15:45,579 [INFO] 0 images deleted from database
2020-04-16 11:15:45,579 [INFO] Computing image statistics
2020-04-16 11:15:46,757 [INFO] Statistics for 3 images done
2020-04-16 11:15:46,846 [INFO] Classifying images
2020-04-16 11:15:46,901 [INFO] Classified 3 images
2020-04-16 11:15:46,902 [INFO] No dark frame found for current working directory
2020-04-16 11:15:46,903 [INFO] Saved data to session CSV file /home/rafa/azotea/csv/-session-2020-03-25.csv
```

La observacion de la noches se deja bajo la carpeta `$HOME/azotea/csv/` en el fichero CSV `session-2020-03-25.csv`. Se puede especificar en la línea de comandos una ruta distinta para este fichero.


4. Obtencion de un fichero global CSV con todas las mediciones de todas las sesiones de reduccion de datos

```bash
~$ azotea image export
```

```
2020-04-08 11:58:33,750 [INFO] Saved data to global CSV file /home/rafa/azotea/csv/azotea.csv
```


5. Volver a reprocesar un directorio 

Si hemos cambiado la region de interes en el fichero config.ini, 
debemos reprocesar los directorios que nos interese, especificando la opcion --reset.


```bash
~$ azotea image reduce --reset --work-dir zamorano/2020-03-25
```

# Reducción de varias noches de observación

Si tenemos todas las imagenes de varias noches en un mismo directorio, es *MUY RECOMENDABLE* organizarlas en subdirectorios con las imagenes de una misma noche en cada subdirectorio. Esto puede haberse hecho de origen por el programa de adqusisción de la cámara, pero si no es así, AZOTEA puede hacerlo mirando la fecha de exposición de los datos EXIF de cada imagen.

```bash
~$ azotea reorganize images --input-dir zamorano/toidas_mis_observaciones --output-dir zamorano/clasificadas
~$ ls zamorano/clasificadas
```

Ahora podemos reducir todas las noches de observación con una orden simple

```bash
~$ azotea image reduce --work-dir zamorano/clasificadas
```

Se generará un fichero CSV por noche de observación


# Fichero de camaras

AZOTEA viene información de cómo decodificar los canales RGB de cámaras conocidas hasta la fecha. 
AZOTEA se irá actualizando a medida que se van probando más cámaras.
Sin embargo, para ir añadiendo camaras no conocidas hasta la fecha a un fichero, se puede crear un fichero.

```bash
azotea config camera --create
emacs ~$/azotea/config/camera.ini
```

# Trazas (log)

Por defecto AZOTEA saca unas trazas por consola con breve información de lo que va haciendo. Si se desea más detalle se puede especificar la opción `--verbose` (abreviado `-v`). Por el contrario, se puede tambien omitir las trazas (excepto las de error y aviso) con la opción `--quiet` (abreviado `-q`)

```bash
azotea --verbose <comando> <subcomando>
```

Las trazas de consola reducción de datos puede además capturarse a un fichero

```bash
azotea image reduce --log-file <ruta del fichero de log> [otras opciones del subcomando reduce]
```

Para la ejecución automatizada bajo un trabajo planificado (ej. cron de Linux), se pueden deshabilitar las trazas de consola y habilitar las de fichero

```bash
azotea image reduce --multiuser --no-console --log-file <ruta fichero log>  --work-dir <ruta dir>
```

# Procesado para varios observadores (multiusuario)

Para una reducción automatizada de todas las observaciones de todos los usuarios hay que hacer un trabajo organizativo previo por cada observador.

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

Es ***requisito*** que el nombre del directorio sea ***igual*** al del fichero de configuracion, sin el sufijo `.ini`


3. Reorganizar las imagenes de cada observacion por noche de observacion

Puede que ya las tengamos separadas en directporios de observacion de origen, peor si no es así, se puede ejecutar lo siguiente:

```bash
azotea reorganize images --input-dir contribuciones/jizquierdo --output-dir clasificadas/jizquierdo
ls clasificadas/jizquierdo
```

Una vez finalizados estos pasos, ya se puede proceder a la reduccipn automatizada.

## Reduccion 

Reducir las imágenes de todos los observadores

```
azotea image reduce --multiuser --work-dir clasificadas
```

Con el indicador `--multiuser` AZOTEA ira navegando por los subdirectorios de directorio de trabajo especificado (`clasificadas`) y tomara dischos nombres de subdirectorio como nombres de fichero .ini a cargar
Y efectuará uan reducción de varias noches de observación por cada usuario


# Otros comandos

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

