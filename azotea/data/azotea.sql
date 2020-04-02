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
    dark_roi            TEXT,             -- dark region of interest: [x1:x2,y1:y2]
    mean_signal_R1      REAL,
    stdev_signal_R1,    REAL,
    mean_signal_G2      REAL,
    stdev_signal_G2     REAL,
    mean_signal_G3      REAL,
    stdev_signal_G3     REAL,
    mean_signal_B4      REAL,
    stdev_signal_B4     REAL,
    -- Processing state columns
    file_path           TEXT  NOT NULL,    -- original absolute file path
    session             TEXT  NOT NULL,    -- Session id
    type                TEXT,              -- LIGHT or DARK
    state               TEXT,              -- NULL = UNPROCESSED, "RAW STATS", DARK SUBSTRACTED"
    PRIMARY KEY(name)
);
