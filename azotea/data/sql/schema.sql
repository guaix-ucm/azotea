-------------------------------
-- Auxiliar database DATA Model
-------------------------------

CREATE TABLE IF NOT EXISTS image_t
(
    -- Observer metadata
    observer            TEXT,             -- Observer full name (family name + surname)
    obs_family_name     TEXT,             -- Observer family name (used only for dataset Zenodo publication)
    obs_surnane         TEXT,             -- Observer family name (used only for dataset Zenodo publication)
    organization        TEXT,             -- Observer organization
    email               TEXT,             -- Observer email
    -- Location metadata
    location            TEXT,             -- location name
    -- Camera metadata
    model               TEXT,             -- Camera Model from EXIF
    focal_length        REAL,             -- Either from config file or EXIF
    f_number            REAL,             -- Either from config file or EXIF
    -- Image metadata
    name                TEXT  NOT NULL,   -- Image name without the path
    hash                BLOB,             -- Image hash
    tstamp              TEXT,             -- ISO 8601 timestamp from EXIF
    night               TEXT,             -- YYYY-MM-DD night where it belongs (as a grouping attribute)
    iso                 TEXT,             -- ISO sensivity from EXIF
    exptime             REAL,             -- exposure time in seconds from EXIF      
    roi                 TEXT,             -- region of interest: [x1:x2,y1:y2]
    dark_roi            TEXT,             -- dark region of interest: [x1:x2,y1:y2], NULL if not used
    bias                INTEGER DEFAULT 0, -- Common BIAS level for all channels
    scale               REAL,             -- image scale in arcsec/pixel

    -- Image Measurements
    aver_signal_R1      REAL,             -- R1 raw signal mean without dark substraction
    vari_signal_R1      REAL,             -- R1 raw signal variance without dark substraction
    aver_dark_R1        REAL DEFAULT 0.0, -- R1 dark level R1 either from master dark or dark_roi
    vari_dark_R1        REAL DEFAULT 0.0, -- R1 dark variance either from master dark or dark_roi

    aver_signal_G2      REAL,             -- G2 raw signal mean without dark substraction
    vari_signal_G2      REAL,             -- G2 raw signal variance without dark substraction
    aver_dark_G2        REAL DEFAULT 0.0, -- G2 dark level either from master dark or dark_roi
    vari_dark_G2        REAL DEFAULT 0.0, -- G2 dark variance either from master dark or dark_roi

    aver_signal_G3      REAL,             -- G3 raw signal mean without dark substraction
    vari_signal_G3      REAL,             -- G3 raw signal variance without dark substraction
    aver_dark_G3        REAL DEFAULT 0.0, -- G3 dark level either from master dark or dark_roi
    vari_dark_G3        REAL DEFAULT 0.0, -- G3 dark variance either from master dark or dark_roi

    aver_signal_B4      REAL,             -- B4 raw signal mean without dark substraction
    vari_signal_B4      REAL,             -- B4 raw signal variance without dark substraction
    aver_dark_B4        REAL DEFAULT 0.0, -- B4 dark level either master dark or dark_roi
    vari_dark_B4        REAL DEFAULT 0.0, -- B4 dark variance either master dark or dark_roi
    -- Processing state columns
    session             INTEGER NOT NULL, -- session identifier
    type                TEXT    NOT NULL, -- LIGHT or DARK
    state               INTEGER NOT NULL REFERENCES state_t(state),
    meta_changes        INTEGER NOT NULL REFERENCES changes_t(flags),         
    PRIMARY KEY(hash)
);

CREATE INDEX IF NOT EXISTS image_i1 ON image_t(name);

CREATE TABLE IF NOT EXISTS state_t (
    state              INTEGER,
    label              TEXT,
    PRIMARY KEY(state)
);

CREATE TABLE IF NOT EXISTS changes_t (
    flags              INTEGER,
    label              TEXT,
    PRIMARY KEY(flags)
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
    f_number            ,                 -- Either from config file or EXIF
    -- Image metadata
    name                ,                 -- Image name without the path
    hash                ,                 -- Image hash
    tstamp              ,                 -- ISO 8601 timestamp
    iso                 ,                 -- ISO sensivity
    exptime             ,                 -- exposure time in seconds       
    roi                 ,                 -- region of interest: [x1:x2,y1:y2]
    dark_roi            ,                 -- dark region of interest: [x1:x2,y1:y2], NULL if not used
    bias                ,                 -- common bias for all channels 
    scale               ,                 -- image scale in arcsec/pixel
    -- Image Measurements
    -- (aver_signal_R1 - bias - aver_dark_R1) AS aver_signal_R1, -- R1 dark substracted signal
    (aver_signal_R1 - aver_dark_R1) AS aver_signal_R1, -- R1 dark substracted signal
    (vari_signal_R1 + vari_dark_R1) AS vari_signal_R1, -- R1 dark substracted signal variance
    aver_dark_R1        ,                 -- R1 dark level R1 either from master dark or dark_roi
    vari_dark_R1        ,                 -- R1 dark variance either from master dark or dark_roi

    -- (aver_signal_G2 - bias - aver_dark_G2) AS aver_signal_G2, -- G2 dark substracted signal
    (aver_signal_G2 - aver_dark_G2) AS aver_signal_G2, -- G2 dark substracted signal
    (vari_signal_G2 + vari_dark_G2) AS vari_signal_G2, -- G2 dark substracted signal variance
    aver_dark_G2        ,                  -- G2 dark level either from master dark or dark_roi
    vari_dark_G2        ,                  -- G2 dark variance either from master dark or dark_roi

    -- (aver_signal_G3 - bias - aver_dark_G3) AS aver_signal_G3, -- G3 dark substracted signal
    (aver_signal_G3 - aver_dark_G3) AS aver_signal_G3, -- G3 dark substracted signal
    (vari_signal_G3 + vari_dark_G3) AS vari_signal_G3, -- G3 dark substracted signal variance
    aver_dark_G3        ,                 -- G3 dark level either from master dark or dark_roi
    vari_dark_G3        ,                 -- G3 dark variance either from master dark or dark_roi

    -- (aver_signal_B4 - bias - aver_dark_B4) AS aver_signal_B4, -- B4 dark substracted signal
    (aver_signal_B4 - aver_dark_B4) AS aver_signal_B4, -- B4 dark substracted signal
    (vari_signal_B4 + vari_dark_B4) AS vari_signal_B4, -- B4 dark substracted signal variance
    aver_dark_B4        ,                 -- B4 dark level either master dark or dark_roi
    vari_dark_B4        ,                 -- B4 dark variance either master dark or dark_roi
    -- Processing state columns
    session             ,                -- session identifier
    type                ,                -- LIGHT or DARK
    state               ,                -- See table state_t
    meta_changes                         -- See table changes_t
FROM image_t;



CREATE TABLE IF NOT EXISTS master_dark_t
(
    session             INTEGER,             -- session id
    aver_R1             REAL    NOT NULL,    -- Red mean dark level
    vari_R1             REAL    NOT NULL,    -- Red dark vari
    aver_G2             REAL    NOT NULL,    -- Green 1 mean dark level
    vari_G2             REAL    NOT NULL,    -- Green 1 dark variance
    aver_G3             REAL    NOT NULL,    -- Green 2 mean dark level
    vari_G3             REAL    NOT NULL,    -- Green 2 dark variance
    aver_B4             REAL    NOT NULL,    -- Blue mean dark level
    vari_B4             REAL    NOT NULL,    -- Blue dark variance
    min_exptime         REAL    NOT NULL,    -- Minimun session exposure time
    max_exptime         REAL    NOT NULL,    -- Maximun session exposure time
    roi                 TEXT    NOT NULL,    -- region of interest: [x1:x2,y1:y2]
    N                   INTEGER NOT NULL,    -- number of darks used to average
    PRIMARY KEY(session)
);