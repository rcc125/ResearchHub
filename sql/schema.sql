-- MySQL 8.0+; run on an empty database named researchhub.
CREATE DATABASE IF NOT EXISTS researchhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE researchhub;
CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  openid VARCHAR(128) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS subjects (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL UNIQUE,
  subject_code VARCHAR(32) NOT NULL UNIQUE,
  name VARCHAR(80),
  gender VARCHAR(24) NOT NULL,
  birth_date DATE NOT NULL,
  height_cm DECIMAL(5,1) NOT NULL,
  weight_kg DECIMAL(5,1) NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_subject_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS projects (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_code VARCHAR(32) NOT NULL UNIQUE,
  title VARCHAR(120) NOT NULL,
  description VARCHAR(500) NOT NULL,
  form_schema JSON NOT NULL,
  leader_name VARCHAR(80) NOT NULL DEFAULT '待设置',
  workdays JSON NOT NULL,
  workday_start TIME NOT NULL DEFAULT '09:00:00',
  workday_end TIME NOT NULL DEFAULT '17:00:00'
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS enrollments (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  subject_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_project_subject UNIQUE (project_id,subject_id),
  CONSTRAINT fk_enroll_subject FOREIGN KEY (subject_id) REFERENCES subjects(id),
  CONSTRAINT fk_enroll_project FOREIGN KEY (project_id) REFERENCES projects(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS form_responses (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  enrollment_id BIGINT NOT NULL UNIQUE,
  answers JSON NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_form_enrollment FOREIGN KEY (enrollment_id) REFERENCES enrollments(id)
) ENGINE=InnoDB;

-- V0.2 new tables; safe to run on existing V0.1 database (no DROP).
CREATE TABLE IF NOT EXISTS project_members (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, project_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
 member_role VARCHAR(24) NOT NULL DEFAULT 'researcher',
 CONSTRAINT uq_member_project_user UNIQUE(project_id,user_id),
 FOREIGN KEY(project_id) REFERENCES projects(id), FOREIGN KEY(user_id) REFERENCES users(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS collections (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, enrollment_id BIGINT NOT NULL,
 attempt_no INTEGER NOT NULL, collection_code VARCHAR(48) NOT NULL UNIQUE,
 status VARCHAR(20) NOT NULL, failure_reason VARCHAR(300), data_reference VARCHAR(120),
 collected_at DATETIME NOT NULL, created_by BIGINT NOT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT uq_collection_attempt UNIQUE(enrollment_id, attempt_no),
 FOREIGN KEY(enrollment_id) REFERENCES enrollments(id), FOREIGN KEY(created_by) REFERENCES users(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS appointments (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, enrollment_id BIGINT NOT NULL, previous_collection_id BIGINT NOT NULL,
 requested_at DATETIME NOT NULL, confirmed_at DATETIME, status VARCHAR(20) NOT NULL DEFAULT 'pending',
 note VARCHAR(300) NOT NULL DEFAULT '', admin_note VARCHAR(300) NOT NULL DEFAULT '',
 created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(enrollment_id) REFERENCES enrollments(id), FOREIGN KEY(previous_collection_id) REFERENCES collections(id)
) ENGINE=InnoDB;
