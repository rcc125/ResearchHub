-- ResearchHub V0.2 -> V0.3 manual migration reference.
-- The FastAPI startup runs additive migrations automatically for local development.
-- Do NOT run this file if startup has already applied these changes. Back up first.
ALTER TABLE subjects ADD COLUMN name VARCHAR(80) NULL;
ALTER TABLE projects ADD COLUMN leader_name VARCHAR(80) NOT NULL DEFAULT '待设置';
ALTER TABLE projects ADD COLUMN workdays JSON NULL;
ALTER TABLE projects ADD COLUMN workday_start TIME NOT NULL DEFAULT '09:00:00';
ALTER TABLE projects ADD COLUMN workday_end TIME NOT NULL DEFAULT '17:00:00';
UPDATE projects SET workdays=JSON_ARRAY(1,2,3,4,5) WHERE workdays IS NULL;
ALTER TABLE appointments MODIFY previous_collection_id INT NULL;
ALTER TABLE appointments ADD COLUMN appointment_type VARCHAR(20) NOT NULL DEFAULT 'reschedule';
