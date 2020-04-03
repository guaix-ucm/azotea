-------------------------------
-- Auxiliar database DATA Model
-------------------------------

CREATE TABLE IF NOT EXISTS image_t
(
	-- Image metadata
    name                TEXT  NOT NULL,   -- Image name without the path
    hash                BLOB  UNIQUE,     -- Image hash
    observer            TEXT  NOT NULL,   -- Observer name
    organization        TEXT,             -- Observer organization
    location            TEXT  NOT NULL,   -- location name
    scale               REAL,             -- image scale in arcsec/pixel
    model               TEXT  NOT NULL,   -- Camera Model
    tstamp              TEXT  NOT NULL,   -- ISO 8601 timestamp
    iso                 TEXT  NOT NULL,   -- ISO sensivity
    exposure            REAL  NOT NULL,   -- exposure time in seconds       
    -- Measurements
    roi                 TEXT,             -- region of interest: [x1:x2,y1:y2]
    dark_roi            TEXT,             -- dark region of interest: [x1:x2,y1:y2], NULL if not used
    
    mean_raw_signal_R1  REAL,             -- R1 raw signal mean without dark substraction
    vari_raw_signal_R1  REAL,             -- R1 raw signal variance without dark substraction
    mean_dark_R1        REAL DEFAULT 0.0, -- R1 dark level R1 either from master dark or dark_roi
    vari_dark_R1        REAL DEFAULT 0.0, -- R1 dark variance either from master dark or dark_roi

    mean_raw_signal_G2  REAL,             -- G2 raw signal mean without dark substraction
    vari_raw_signal_G2  REAL,             -- G2 raw signal variance without dark substraction
    mean_dark_G2        REAL DEFAULT 0.0, -- G2 dark level either from master dark or dark_roi
    vari_dark_G2        REAL DEFAULT 0.0, -- G2 dark variance either from master dark or dark_roi

    mean_raw_signal_G3  REAL,             -- G3 raw signal mean without dark substraction
    vari_raw_signal_G3  REAL,             -- G3 raw signal variance without dark substraction
    mean_dark_G3        REAL DEFAULT 0.0, -- G3 dark level either from master dark or dark_roi
    vari_dark_G3        REAL DEFAULT 0.0, -- G3 dark variance either from master dark or dark_roi

    mean_raw_signal_B4  REAL,             -- B4 raw signal mean without dark substraction
    vari_raw_signal_B4  REAL,             -- B4 raw signal variance without dark substraction
    mean_dark_B4        REAL DEFAULT 0.0, -- B4 dark level either master dark or dark_roi
    vari_dark_B4        REAL DEFAULT 0.0, -- B4 dark variance either master dark or dark_roi
    -- Processing state columns
    file_path           TEXT  NOT NULL,   -- original absolute file path
    batch               TEXT  NOT NULL,   -- batch identifier
    type                TEXT,             -- LIGHT or DARK
    state               TEXT,             -- NULL = UNPROCESSED, "RAW STATS", DARK SUBSTRACTED"
    PRIMARY KEY(name)
);

------------------------------------------------------------------------------------------------
-- This View exists to automatically substract the dark levels and calculate resulting variances
-- From the raw data without actually modifyng the underlying data
------------------------------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS image_v AS
SELECT
    -- Image metadata
    name                ,                 -- Image name without the path
    hash                ,                 -- Image hash
    observer            ,                 -- Observer name
    organization        ,                 -- Observer organization
    location            ,                 -- location name
    scale               ,                 -- image scale in arcsec/pixel
    model               ,                 -- Camera Model
    tstamp              ,                 -- ISO 8601 timestamp
    iso                 ,                 -- ISO sensivity
    exposure            ,                 -- exposure time in seconds       
    -- Measurements
    roi                 ,                 -- region of interest: [x1:x2,y1:y2]
    dark_roi            ,                 -- dark region of interest: [x1:x2,y1:y2], NULL if not used
    
    (mean_raw_signal_R1 - mean_dark_R1) AS mean_signal_R1, -- R1 dark substracted signal
    (vari_raw_signal_R1 + vari_dark_R1) AS vari_signal_R1, -- R1 dark substracted signal variance
    mean_dark_R1        ,                 -- R1 dark level R1 either from master dark or dark_roi
    vari_dark_R1        ,                 -- R1 dark variance either from master dark or dark_roi

    (mean_raw_signal_G2 - mean_dark_G2) AS mean_signal_G2, -- G2 dark substracted signal
    (vari_raw_signal_G2 + vari_dark_G1) AS vari_signal_G2, -- G2 dark substracted signal variance
    mean_dark_G2        ,                 -- G2 dark level either from master dark or dark_roi
    vari_dark_G2        ,                 -- G2 dark variance either from master dark or dark_roi

    (mean_raw_signal_G3 - mean_dark_G3) AS mean_signal_G3, -- G3 dark substracted signal
    (vari_raw_signal_G3 + vari_dark_G3) AS vari_signal_G3, -- G3 dark substracted signal variance
    mean_dark_G3        ,                 -- G3 dark level either from master dark or dark_roi
    vari_raw_signal_G3  ,                 -- G3 dark variance either from master dark or dark_roi

    (mean_raw_signal_B4 - mean_dark_B4) AS mean_signal_B4, -- B4 dark substracted signal
    (vari_raw_signal_B4 + vari_dark_G3) AS vari_signal_B4, -- B4 dark substracted signal variance
    mean_dark_B4        ,                                  -- B4 dark level either master dark or dark_roi
    vari_dark_B4        ,                                  -- B4 dark variance either master dark or dark_roi
    -- Processing state columns
    file_path           ,                -- original absolute file path
    batch               ,                -- batch identifier
    type                ,                -- LIGHT or DARK
    state                                -- NULL = UNPROCESSED, "RAW STATS", DARK SUBSTRACTED"
FROM image_t AS i;



CREATE TABLE IF NOT EXISTS master_dark_t
(
    batch               TEXT    NOT NULL,    -- batch id
    mean_R1             REAL    NOT NULL,    -- Red mean dark level in Red
    vari_R1             REAL    NOT NULL,    -- Red dark vari
    mean_G2             REAL    NOT NULL,    -- Green 1 mean dark level
    vari_G2             REAL    NOT NULL,    -- Green 1 dark variance
    mean_G3             REAL    NOT NULL,    -- Green 2 mean dark level
    vari_G3             REAL    NOT NULL,    -- Green 2 dark variance
    mean_B4             REAL    NOT NULL,    -- Blue mean dark level in Blue
    vari_B4             REAL    NOT NULL,    -- Blue dark variance
    roi                 TEXT    NOT NULL,    -- region of interest: [x1:x2,y1:y2]
    N                   INTEGER NOT NULL,    -- number of darks used to average
    PRIMARY KEY(batch)
);