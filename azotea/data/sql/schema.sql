-------------------------------
-- Auxiliar database DATA Model
-------------------------------

CREATE TABLE IF NOT EXISTS image_t
(
    -- Observer metadata
    observer            TEXT  NOT NULL,   -- Observer name
    organization        TEXT,             -- Observer organization
    email               TEXT,             -- Observer email
    -- Location metadata
    location            TEXT  NOT NULL,   -- location name
    -- Camera metadata
    model               TEXT  NOT NULL,   -- Camera Model from EXIF
    focal_length        INTEGER,          -- Either from config file or EXIF
    f_ratio             INTEGER,          -- Either from config file or EXIF
    -- Image metadata
    name                TEXT  NOT NULL,   -- Image name without the path
    hash                BLOB,             -- Image hash
    tstamp              TEXT  NOT NULL,   -- ISO 8601 timestamp from EXIF
    iso                 TEXT  NOT NULL,   -- ISO sensivity from EXIF
    exptime             REAL  NOT NULL,   -- exposure time in seconds from EXIF      
    roi                 TEXT,             -- region of interest: [x1:x2,y1:y2]
    dark_roi            TEXT,             -- dark region of interest: [x1:x2,y1:y2], NULL if not used
    scale               REAL,             -- image scale in arcsec/pixel

    -- Image Measurements
    aver_raw_signal_R1  REAL,             -- R1 raw signal mean without dark substraction
    vari_raw_signal_R1  REAL,             -- R1 raw signal variance without dark substraction
    aver_dark_R1        REAL DEFAULT 0.0, -- R1 dark level R1 either from master dark or dark_roi
    vari_dark_R1        REAL DEFAULT 0.0, -- R1 dark variance either from master dark or dark_roi

    aver_raw_signal_G2  REAL,             -- G2 raw signal mean without dark substraction
    vari_raw_signal_G2  REAL,             -- G2 raw signal variance without dark substraction
    aver_dark_G2        REAL DEFAULT 0.0, -- G2 dark level either from master dark or dark_roi
    vari_dark_G2        REAL DEFAULT 0.0, -- G2 dark variance either from master dark or dark_roi

    aver_raw_signal_G3  REAL,             -- G3 raw signal mean without dark substraction
    vari_raw_signal_G3  REAL,             -- G3 raw signal variance without dark substraction
    aver_dark_G3        REAL DEFAULT 0.0, -- G3 dark level either from master dark or dark_roi
    vari_dark_G3        REAL DEFAULT 0.0, -- G3 dark variance either from master dark or dark_roi

    aver_raw_signal_B4  REAL,             -- B4 raw signal mean without dark substraction
    vari_raw_signal_B4  REAL,             -- B4 raw signal variance without dark substraction
    aver_dark_B4        REAL DEFAULT 0.0, -- B4 dark level either master dark or dark_roi
    vari_dark_B4        REAL DEFAULT 0.0, -- B4 dark variance either master dark or dark_roi
    -- Processing state columns
    file_path           TEXT    NOT NULL, -- original absolute file path
    batch               INTEGER NOT NULL, -- batch identifier
    type                TEXT,             -- LIGHT or DARK
    state               INTEGER REFERENCES state_t(state),            
    PRIMARY KEY(hash)
);

CREATE TABLE IF NOT EXISTS state_t (
    state              INTEGER,
    label              TEXT,
    PRIMARY KEY(state)
);

------------------------------------------------------------------------------------------------
-- This View exists to automatically substract the dark levels and calculate resulting variances
-- From the raw data without actually modifyng the underlying data
------------------------------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS image_v AS
SELECT
    -- Observer metadata
    observer            ,                 -- Observer name
    organization        ,                 -- Observer organization
    email               ,                 -- Observer email
    -- Location metadata
    location            ,                 -- location name
    -- Camera metadata
    model               ,                 -- Camera Model from EXIF
    focal_length        ,                 -- Either from config file or EXIF
    f_ratio             ,                 -- Either from config file or EXIF
    -- Image metadata
    name                ,                 -- Image name without the path
    hash                ,                 -- Image hash
    tstamp              ,                 -- ISO 8601 timestamp
    iso                 ,                 -- ISO sensivity
    exptime             ,                 -- exposure time in seconds       
    roi                 ,                 -- region of interest: [x1:x2,y1:y2]
    dark_roi            ,                 -- dark region of interest: [x1:x2,y1:y2], NULL if not used
    scale               ,                 -- image scale in arcsec/pixel
    -- Image Measurements
    (aver_raw_signal_R1 - aver_dark_R1) AS aver_signal_R1, -- R1 dark substracted signal
    (vari_raw_signal_R1 + vari_dark_R1) AS vari_signal_R1, -- R1 dark substracted signal variance
    aver_dark_R1        ,                 -- R1 dark level R1 either from master dark or dark_roi
    vari_dark_R1        ,                 -- R1 dark variance either from master dark or dark_roi

    (aver_raw_signal_G2 - aver_dark_G2) AS aver_signal_G2, -- G2 dark substracted signal
    (vari_raw_signal_G2 + vari_dark_G2) AS vari_signal_G2, -- G2 dark substracted signal variance
    aver_dark_G2        ,                 -- G2 dark level either from master dark or dark_roi
    vari_dark_G2        ,                 -- G2 dark variance either from master dark or dark_roi

    (aver_raw_signal_G3 - aver_dark_G3) AS aver_signal_G3, -- G3 dark substracted signal
    (vari_raw_signal_G3 + vari_dark_G3) AS vari_signal_G3, -- G3 dark substracted signal variance
    aver_dark_G3        ,                 -- G3 dark level either from master dark or dark_roi
    vari_dark_G3        ,                 -- G3 dark variance either from master dark or dark_roi

    (aver_raw_signal_B4 - aver_dark_B4) AS aver_signal_B4, -- B4 dark substracted signal
    (vari_raw_signal_B4 + vari_dark_B4) AS vari_signal_B4, -- B4 dark substracted signal variance
    aver_dark_B4        ,                                  -- B4 dark level either master dark or dark_roi
    vari_dark_B4        ,                                  -- B4 dark variance either master dark or dark_roi
    -- Processing state columns
    file_path           ,                -- original absolute file path
    batch               ,                -- batch identifier
    type                ,                -- LIGHT or DARK
    state                                -- NULL = UNPROCESSED, "RAW STATS", DARK SUBSTRACTED"
FROM image_t;



CREATE TABLE IF NOT EXISTS master_dark_t
(
    batch               INTEGER,             -- batch id
    aver_R1             REAL    NOT NULL,    -- Red mean dark level in Red
    vari_R1             REAL    NOT NULL,    -- Red dark vari
    aver_G2             REAL    NOT NULL,    -- Green 1 mean dark level
    vari_G2             REAL    NOT NULL,    -- Green 1 dark variance
    aver_G3             REAL    NOT NULL,    -- Green 2 mean dark level
    vari_G3             REAL    NOT NULL,    -- Green 2 dark variance
    aver_B4             REAL    NOT NULL,    -- Blue mean dark level in Blue
    vari_B4             REAL    NOT NULL,    -- Blue dark variance
    min_exptime         REAL    NOT NULL,    -- Minimun batch exposure time
    max_exptime         REAL    NOT NULL,    -- Maximun batch exposure time
    roi                 TEXT    NOT NULL,    -- region of interest: [x1:x2,y1:y2]
    N                   INTEGER NOT NULL,    -- number of darks used to average
    PRIMARY KEY(batch)
);