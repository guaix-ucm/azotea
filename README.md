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
## Compatibilidad con Python 2

Aunque el programa en sí, puede ejecutarse en Python 2, algunas librerías empleadas en AZOTEA ya no funcionan en Python 2, por lo que se recomienda usar Python 3.

Los siguientes comandos no funcionan en Python 2:

* `azotea metadata`

# Configuracion

## Configuración global

Antes de poder operar con AZOTEA hay que crear un fichero de configuración para el observador.
Lo mejor es crearlo a partir de la plantlla interna asi:

```bash
python -m azotea config global --create
```

```
2020-04-02 11:58:33,351 [INFO] Created /home/rafa/azotea.ini file
```

Esto creará un fichero `azotea.ini` en el directorio raiz (`$HOME`) de cada usuario.
Editar el fichero con un block de notas o similar. Los campos son descriptivos y no debería haber ningin problema al rellenarlos.


## Camaras soportadas

AZOTEA se irá actualizando a medida que soporte más cámaras.

Los modelos de camara soportados hasta el momento se pueden ver listando el fichero de configuracion interno

```bash
python -m azotea config camera --list
```

***Uso Avanzado, no recomendado***: Si hay necesidad de crar una entrada más a este fichero, se puede hacer una copia de él y luego editarlo de manera análoga a la configuración global. Este fichero no es para todo el mundo, sólo los que entienden cómo funciona el software deben hacerlo.


```bash
python -m azotea config camera --create
```

```
2020-04-01 19:25:12,998 [INFO] Created /home/rafa/camera.ini file
```

Para probar la cámara comn este nuevo fichero en todos los comandos `azotea` posteriores hay que especificarlo como opción global antes de los comandos. Ejemplo:


```bash
python -m azotea --camera mycamera.ini stats compute
```

# Operativa

## ***La version corta***

1. Configurado el fichero `azotea.ini`, que debe residir en `$HOME/azotea/azotea.ini`

2. Volcar *todas* las imagenes de la cámara de una misma noche a un directorio de trabajo (p.e. `/home/rafa/demo/test`)

3. Si hay tomas *dark*, renombrar dichas tomas a `dark_<nombre original>`

4. ¡Por fin! ejecutar en una linea de comandos:

```bash
python -m azotea image reduce --new --work-dir /home/rafa/demo/test
python -m azotea image export --all
```

## La version larga

### Pîpeline de reducción de datos

AZOTEA es un programa complejo, con muchas opciones, que lleva una pequeña base de datos incorporada para recordar los valores medidos y el estado de procesamiento de las imagenes. El usuario nunca trata con la base de datos directamente sino que actua con comandos. Las imagenes nunca se modifican ni se cambian de lugar y tipicamente se genera un lote de procesado (*batch*) por cada directorio. Lo habitual sería un directorio por día lleno de imagenes.

Los datos de interés se guardan en la base de datos y a partir de ellos se generan ficheros para publicar o compartir. 

Si la base de datos se corrompe o se borra, para recuperar su contenido habría que correr el pipeline de reduccióm de imágenes con todos los directorios que se hayan generado, cosa no siempre posible. Por ello se incluyen comandos de backup de la base de datos.


El pipeline de AZOTEA consta de los siguientes pasos en secuencia:

1. Registro de las imágenes en la base de datos

```bash
python -m azotea image register --help
```

2. Clasificacion de las imagenes den LIGHT y DARK para la sustracción de cuadro oscuro

```bash
python -m azotea image classify --help
```

3. Calculo de estadístcas en la región de interés (ROI) (media y varianza)


```bash
python -m azotea image stats --help
```

4. Elaboración de un DARK maestro si es que hay imágenes de tipo DARK y sustracción del nivel de oscuro a las tomas de tipo LIGHT


```bash
python -m azotea image dark --help
```

5. Exportación de los resultados a un fichero. En la actualidad sólo se soporta un fichero CSV

```bash
python -m azotea image export --help
```

Todos estos pasos se pùeden efectuar por separado o combinadamente con `azotea image reduce`

### Otros comandos

AZOTEA tiene otros comandos para
1. efectuar y listar backups de la base de datos
2. recrear la base de datos desde cero.

# Ficheros CSV de salida

El pipeline de reducción genera dos ficheros CSV:

* Un fichero CSV con los resultados de la reducción del último lote con la forma `YYYYMMDDHHMMSS`.csv (Ejemplo: 20200402103223.csv)
* Un fichero global CSV donde se van acumulando todos los datos de todos los lotes procesados hasta el momento: `azotea.csv`

Ambos ficheros se situan en la el directorio raiz (`$HOME`) de cada usuario.

El fichero CSV tiene una cabecera con los nombres de las columnas, a saber:


|    Columna      |  Descripcion                                           |
|:---------------:|:-------------------------------------------------------|
| batch           | Identificacion del lote de reducción de datos.         |
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
| exposure        | Tiempo de exposicion                                   |
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
python -m azotea --version
```

2. Comandos

La invocación de AZOTEA tiene la forma general de:

```
python -m azotea [--opcion1, --opcion2, ...] <comando>  <subcomando> [--opcion3, --opcion4, ...]
```

Cada comando y subcomando dentro del comando tienen su propia ayuda:

```bash
python -m azotea --help
python -m azotea <comando> --help
python -m azotea <comando> <subcomando> --help
```

La lista de comandos disponible se averigua con:

```bash
python -m azotea --help
```

```
usage: azotea [-h] [--version] [-v | -q] [--camera CAMERA] [--config CONFIG]
              {metadata,stats,config} ...

AZOTEA analysis tool

positional arguments:
  {metadata,stats,config}
    metadata            metadata commands
    stats               stats commands
    config              config commands

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -v, --verbose         Verbose output.
  -q, --quiet           Quiet output.
  --camera CAMERA       Optional alternate camera configuration file
  --config CONFIG       Optional alternate global configuration file
```

Según se ver, los comandos disponibles son `metadata` `stats` y `config` y las opciones globales son
`--camera` y `--config`

Para ver las opciones del comando `stats` se teclea

```bash
python -m azotea stats --help
```

```
usage: azotea stats [-h] {compute} ...

positional arguments:
  {compute}
    compute   compute image statistics

optional arguments:
  -h, --help  show this help message and exit
```

Como se ve, el comando `stats` solo tiene el subcomando `compute`. Y para averiguar las opciones del subcomando `stats compute` se teclea:


```bash
python -m azotea stats compute --help
```

```
usage: azotea stats compute [-h] [--roi <width,height>]
                            [--global-csv-file GLOBAL_CSV_FILE] [-w WORK_DIR]
                            [-f FILTER] [-m | -d]

optional arguments:
  -h, --help            show this help message and exit
  --roi <width,height>  Optional region of interest
  --global-csv-file GLOBAL_CSV_FILE
                        Global output CSV file where all sessions are
                        accumulated
  -w WORK_DIR, --work-dir WORK_DIR
                        Input working directory
  -f FILTER, --filter FILTER
                        Optional input glob-style filter
  -m, --do-not-move     Do not move files after processing
  -d, --dry-run         Do not generate/update CSV files
```
