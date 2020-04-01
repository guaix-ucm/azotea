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

# Ejemplos

1. Mostrar metadatos de una sola imagen o un directorio de trabajo

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

2. Calcular estadistca de una serie de imagenes en un directorio y guardarlas en un fichero

```bash
python -m azotea stats compute  --work-dir demo/test --csv-file azotea.csv
```

```
2020-04-01 12:56:44,361 [INFO] CSV file is /home/rafa/repos/azotea/azotea.csv
2020-04-01 12:56:44,751 [INFO] 2020_03_2600_17_409999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dk. ROI = [400:550,200:350]
2020-04-01 12:56:45,144 [INFO] 2020_03_2600_18_459999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dk. ROI = [400:550,200:350]
2020-04-01 12:56:45,487 [INFO] 2020_03_2605_30_079999.CR2: Canon EOS 450D, ROI = [828:1328,519:919], Dk. ROI = [400:550,200:350]
2020-04-01 12:56:45,491 [INFO] Saved all to CSV file /home/rafa/repos/azotea/azotea.csv
```

Se puede especificar una anchura central region de iluminación a medida con `--fg-region ancho,alto`

Se puede especificar una zona rectangular para medir el nivel de oscuro con `--bg-region x1,x2,y1,y2`

# Fichewro CSV de salida

El comando `stats compute` genera un fichero CSV tanto si es una sola imagen como si es un directorio de ellas. Para incluir los metadatos de observador, su organización y su localización, se debe organizar el directorio de imágenes así:

	`<organización>/<observador>/<loacalización>/`

Ejemplo:

	`'GUAIX-UCM/Jaime Zamorano/Villaverde del Ducado'`

El fichero CSV tiene una cabecera con los nombres de las columnas, a saber:


|    Columna      |  Descripcion                                           |
|:---------------:|:-------------------------------------------------------|
| observer        | Nombre del observador.                                 |
| organization    | Organizacion a la que pertenece el observador.         |
| location        | Localidad desde donde ha sido tomada la imagen.        |
| name            | Nombre de la imagen (=nombre del fichero sin la ruta.) |
| model           | Modelo de cámara.                                      |
| ISO             | Sensibilidad ISO de la toma.                           |
| exposure        | Tiempo de exposicion                                   |
| roi             | Region de interés [x1:x2, y1:y2]                       |
| dk_roi          | Region de interes para medida oscura [x1:x2, y1:y2]    |
| mean_signal_R1  | Promedio de señal canal R.                             |
| stdev_signal_R1 | Desviación tipica señal del canal R.                   |
| mean_dark_R1    | Promedio de zona oscura en el canal R.                 |
| stdev_dark_R1   | Desviación tipica zona oscura en el canal R.           |
| mean_signal_G2  | Promedio de señal en un canal G.                       |
| stdev_signal_G2 | Desviación tipica de señal en un canal G.              |
| mean_dark_G2    | Promedio de zona oscura en un canal G.                 |
| stdev_dark_G2   | Desviación tipica zona oscura en un canal G.           |
| mean_signal_G3  | Promedio de señal en el otro canal G.                  |
| stdev_signal_G3 | Desviación tipica de señal en el otro canal G.         |
| mean_dark_G3    | Promedio de zona oscura en el otro canal G.            |
| stdev_dark_G3   | Desviación tipica zona oscura en el otro canal G.      |
| mean_signal_B4  | Promedio de señal del canal B.                         |
| stdev_signal_B4 | Desviación tipica señal del canal B.                   |
| mean_dark_B4    | Promedio de zona oscura en el canal B.                 |
| stdev_dark_B4   | Desviación tipica zona oscura en canal B.              |
