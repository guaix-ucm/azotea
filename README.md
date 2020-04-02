# azotea

Pipeline Python de reducción de datos para [AZOTEA](https://guaix.ucm.es/AZOTEA) (Astronomía Zenital desde el hOgar en Tiempos de Extremo Aislamiento).

Esta es una herramienta de línea de comandos.

# Comandos

1. Version del programa

```bash 
python -m azotea --version
```

2. Comandos

```bash
python -m azotea --help
```

```
usage: azotea [-h] [--version] [-v | -q] {metadata,stats} ...

AZOTEA analysis tool

positional arguments:
  {metadata,stats}
    metadata        metadata commands
    stats           stats commands

optional arguments:
  -h, --help        show this help message and exit
  --version         show program's version number and exit
  -v, --verbose     Verbose output.
  -q, --quiet       Quiet output.
  ```


La invocación de AZOTEA tiene la forma general de:

```
python -m azotea <comando> <subcomando> [--opcion1, --opcion2, ...]
```

Cada comando y subcomando dentro del comando tiene su propia ayuda:

```bash
python -m azotea <comando> --help
python -m azotea <comando> <subcomando> --help
```

# Configuracion

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


Los modelos de camara soportados se pueden ver listando el fichero de configuracion interno

```bash
python -m azotea config camera --list
```

Si hay necesidad de crar una entrada más a este fichero, se puede hacer una copia de él y luego editarlo
de manera análoga a la configuración global. Este fichero no es para todo el mundo, sólo los que entienden
cómo funciona el software deben hacerlo.


```bash
python -m azotea config camera --create
```

```
2020-04-01 19:25:12,998 [INFO] Created /home/rafa/camera.ini file
```


# Operativa

Si nos interesa antes, se pueden mostrar los metadatos de una sola imagen o un directorio de trabajo.
Por ejemplo:

```bash
python -m azotea metadata display --input-file demo/test/2020_03_2600_17_409999.CR2
python -m azotea metadata display --work-dir demo/test
```

```
2020-03-31 23:20:43,272 [INFO] azotea.metadata: Scanning a list of 3 entries using filter *.CR2
+----------------------------+---------------------+------------------------+---------------------+----------------+
| File Name                  | EXIF ExposureTime   | EXIF ISOSpeedRatings   | Image DateTime      | Image Model    |
+============================+=====================+========================+=====================+================+
| 2020_03_2600_17_409999.CR2 | 60                  | 800                    | 2020:03:26 00:17:40 | Canon EOS 450D |
+----------------------------+---------------------+------------------------+---------------------+----------------+
| 2020_03_2600_18_459999.CR2 | 60                  | 800                    | 2020:03:26 00:18:45 | Canon EOS 450D |
+----------------------------+---------------------+------------------------+---------------------+----------------+
| 2020_03_2605_30_079999.CR2 | 60                  | 800                    | 2020:03:26 05:30:07 | Canon EOS 450D |
+----------------------------+---------------------+------------------------+---------------------+----------------+
```

A contnuación, calcularemos la estadistica de cada imagen. Podemos hacer una ejecución "en seco" (*dry run*) que no va actualizar ningín fichero CSV de resultados:

```bash
python -m azotea stats compute  --work-dir demo/test --dry-run
```

```
22020-04-02 12:16:53,561 [INFO] Opening configuration file /home/rafa/azotea.ini
2020-04-02 12:16:53,561 [INFO] Analyzing 3 files
2020-04-02 12:16:53,960 [INFO] 2020_03_2600_17_409999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dark ROI = None
2020-04-02 12:16:54,356 [INFO] 2020_03_2600_18_459999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dark ROI = None
2020-04-02 12:16:54,701 [INFO] 2020_03_2605_30_079999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dark ROI = None
2020-04-02 12:16:54,701 [INFO] Dry run, do not generate/update CSV files
```

Si no queremos calcular la estadistica de todas las imagenes del directorio de trabajo, se puede especificar un filtro:


```bash
python -m azotea stats compute  --work-dir demo/test --filter *2600*.CR2 --dry-run
```
`
2020-04-02 12:29:56,277 [INFO] Opening configuration file /home/rafa/azotea.ini
2020-04-02 12:29:56,277 [INFO] Analyzing 2 files
2020-04-02 12:29:56,693 [INFO] 2020_03_2600_17_409999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dark ROI = None
2020-04-02 12:29:57,104 [INFO] 2020_03_2600_18_459999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dark ROI = None
2020-04-02 12:29:57,105 [INFO] Dry run, do not generate/update CSV files
`


```bash
python -m azotea stats compute  --work-dir demo/test
```

Es importante señalar que tras
# Ficheros CSV de salida

El comando `stats compute` genera dos ficheros CSV:

* Un fichero CSV con los resultados de la sesion `YYYYMMDDHHMMSS`.csv
* Un fichero global CSV donde se van acumulando todos los datos de todas las sesiones `azotea.csv`

Ambos ficheros se situan en la el directorio raiz (`$HOME`) de cada usuario.

El fichero CSV tiene una cabecera con los nombres de las columnas, a saber:


|    Columna      |  Descripcion                                           |
|:---------------:|:-------------------------------------------------------|
| session         | Identificacion de la sesion de reducción de datos.     |
| observer        | Nombre del observador.                                 |
| organization    | Organizacion a la que pertenece el observador.         |
| location        | Localidad desde donde ha sido tomada la imagen.        |
| name            | Nombre de la imagen (=nombre del fichero sin la ruta.) |
| model           | Modelo de cámara.                                      |
| ISO             | Sensibilidad ISO de la toma.                           |
| exposure        | Tiempo de exposicion                                   |
| roi             | Region de interés [x1:x2, y1:y2]                       |
| darkk_roi       | Region de interes para medida oscura [x1:x2, y1:y2]    |
| mean_signal_R1  | Promedio de señal canal R.                             |
| stdev_signal_R1 | Desviación tipica señal del canal R.                   |
| mean_signal_G2  | Promedio de señal en un canal G.                       |
| stdev_signal_G2 | Desviación tipica de señal en un canal G.              |
| mean_signal_G3  | Promedio de señal en el otro canal G.                  |
| stdev_signal_G3 | Desviación tipica de señal en el otro canal G.         |
| mean_signal_B4  | Promedio de señal del canal B.                         |
| stdev_signal_B4 | Desviación tipica señal del canal B.                   |

