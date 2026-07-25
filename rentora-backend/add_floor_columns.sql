-- Run this once against your Rentora MySQL database to add the new
-- optional "floors", "total rooms" and "room number" fields. All columns
-- are nullable, so this is safe - it won't touch or delete any existing
-- data. If you already ran an earlier version of this file, MySQL will
-- error on any ALTER below whose column already exists - just skip that
-- line and run the rest.

ALTER TABLE properties ADD COLUMN total_floors INT NULL;
ALTER TABLE properties ADD COLUMN total_rooms INT NULL;
ALTER TABLE rooms ADD COLUMN floor_number INT NULL;
ALTER TABLE rooms ADD COLUMN room_number VARCHAR(20) NULL;
