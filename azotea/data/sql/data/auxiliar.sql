--------------------------------------------------------
-- Miscelaneous data to be inserted at database creation
--------------------------------------------------------

INSERT OR REPLACE INTO state_t(state, label) VALUES ( 0, "REGISTERED");
INSERT OR REPLACE INTO state_t(state, label) VALUES ( 1, "STATS COMPUTED");
INSERT OR REPLACE INTO state_t(state, label) VALUES ( 2, "METADATA UPDATED");
INSERT OR REPLACE INTO state_t(state, label) VALUES ( 3, "DARK SUBSTRACTED");

INSERT OR REPLACE INTO changes_t(flags, label) VALUES ( 0, "NO PENDING CHANGES");
INSERT OR REPLACE INTO changes_t(flags, label) VALUES ( 1, "CAMERA PENDING");
INSERT OR REPLACE INTO changes_t(flags, label) VALUES ( 2, "OBSERVER PENDING");
INSERT OR REPLACE INTO changes_t(flags, label) VALUES ( 3, "CAMERA & OBSERVER PENDING");
