-- ============================================================
--  Student Management System - MySQL schema (3NF)
-- ============================================================
--  courses    1 ──< students
--  courses    1 ──< subjects
--  students   1 ──< attendance
--  students   1 ──< results >── 1 subjects
-- ============================================================

CREATE DATABASE IF NOT EXISTS student_management
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_management;

CREATE TABLE IF NOT EXISTS courses (
    course_id      INT AUTO_INCREMENT PRIMARY KEY,
    course_code    VARCHAR(20)  NOT NULL UNIQUE,
    course_name    VARCHAR(100) NOT NULL,
    duration_years TINYINT      NOT NULL DEFAULT 3,
    CHECK (duration_years BETWEEN 1 AND 6)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS students (
    student_id     INT AUTO_INCREMENT PRIMARY KEY,
    roll_no        VARCHAR(20)  NOT NULL UNIQUE,
    full_name      VARCHAR(100) NOT NULL,
    dob            DATE         NOT NULL,
    gender         ENUM('Male','Female','Other') NOT NULL,
    email          VARCHAR(120) UNIQUE,
    phone          VARCHAR(15),
    course_id      INT          NOT NULL,
    admission_date DATE         NOT NULL,
    INDEX idx_students_name (full_name),
    CONSTRAINT fk_student_course FOREIGN KEY (course_id)
        REFERENCES courses(course_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subjects (
    subject_id   INT AUTO_INCREMENT PRIMARY KEY,
    course_id    INT          NOT NULL,
    subject_code VARCHAR(20)  NOT NULL UNIQUE,
    subject_name VARCHAR(100) NOT NULL,
    max_marks    SMALLINT     NOT NULL DEFAULT 100,
    CONSTRAINT fk_subject_course FOREIGN KEY (course_id)
        REFERENCES courses(course_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id    INT  NOT NULL,
    att_date      DATE NOT NULL,
    status        ENUM('Present','Absent','Leave') NOT NULL,
    CONSTRAINT uq_attendance UNIQUE (student_id, att_date),
    INDEX idx_attendance_date (att_date),
    CONSTRAINT fk_att_student FOREIGN KEY (student_id)
        REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS results (
    result_id      INT AUTO_INCREMENT PRIMARY KEY,
    student_id     INT          NOT NULL,
    subject_id     INT          NOT NULL,
    exam_term      VARCHAR(20)  NOT NULL,
    marks_obtained DECIMAL(5,2) NOT NULL,
    CONSTRAINT uq_result UNIQUE (student_id, subject_id, exam_term),
    CONSTRAINT fk_res_student FOREIGN KEY (student_id)
        REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_res_subject FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id) ON DELETE CASCADE
) ENGINE=InnoDB;
