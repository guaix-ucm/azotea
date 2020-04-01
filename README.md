# azotea

Pipeline Python de reducción de datos para [AZOTEA](https://guaix.ucm.es/AZOTEA) (Astronomía Zenital desde el hOgar en Tiempos de Extremo Aislamiento).

Esta es una herramienta de línea de comandos.



# Comandos

1. Version del programa

```bash 
python -m azotea --version```
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
python -m azotea stats compute  --work-dir demo/test
```

```
2020-03-31 23:21:58,510 [INFO] CSV file is test.csv
2020-03-31 23:21:58,557 [INFO] 2020_03_2600_17_409999.CR2: Loading RAW data from Canon EOS 450D
2020-03-31 23:21:58,917 [INFO] 2020_03_2600_17_409999.CR2: Background  region of interest is [(x=400,y=200) - (x=550,y=350)]
2020-03-31 23:21:58,917 [INFO] 2020_03_2600_17_409999.CR2: Illuminated region of interest is [(x=828,y=519) - (x=1328,y=919)]
2020-03-31 23:21:58,969 [INFO] 2020_03_2600_18_459999.CR2: Loading RAW data from Canon EOS 450D
2020-03-31 23:21:59,326 [INFO] 2020_03_2600_18_459999.CR2: Background  region of interest is [(x=400,y=200) - (x=550,y=350)]
2020-03-31 23:21:59,327 [INFO] 2020_03_2600_18_459999.CR2: Illuminated region of interest is [(x=828,y=519) - (x=1328,y=919)]
2020-03-31 23:21:59,377 [INFO] 2020_03_2605_30_079999.CR2: Loading RAW data from Canon EOS 450D
2020-03-31 23:21:59,689 [INFO] 2020_03_2605_30_079999.CR2: Background  region of interest is [(x=400,y=200) - (x=550,y=350)]
2020-03-31 23:21:59,689 [INFO] 2020_03_2605_30_079999.CR2: Illuminated region of interest is [(x=828,y=519) - (x=1328,y=919)]
2020-03-31 23:21:59,693 [INFO] Saved all to CSV file test.csv
```

Se puede especificar una anchura central region de iluminación a medida con `--fg-region ancho,alto`

Se puede especificar una zona rectangular para medir el nivel de oscuro con `--bg-region x1,x2,y1,y2`