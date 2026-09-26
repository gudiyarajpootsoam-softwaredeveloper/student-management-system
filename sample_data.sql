USE student_management;

INSERT INTO courses (course_code, course_name, duration_years) VALUES
('MCA', 'Master of Computer Applications', 2),
('BCA', 'Bachelor of Computer Applications', 3);

INSERT INTO subjects (course_id, subject_code, subject_name, max_marks) VALUES
(1, 'MCS-211', 'Design and Analysis of Algorithms', 100),
(1, 'MCS-212', 'Discrete Mathematics', 100),
(1, 'MCS-213', 'Software Engineering', 100),
(1, 'MCS-214', 'Professional Skills and Ethics', 100),
(2, 'BCS-011', 'Computer Basics and PC Software', 100),
(2, 'BCS-012', 'Basic Mathematics', 100);

INSERT INTO students (roll_no, full_name, dob, gender, email, phone, course_id, admission_date) VALUES
('MCA2024001', 'Aarav Sharma', '2001-04-12', 'Male',   'aarav.sharma@example.com', '9876543210', 1, '2024-07-15'),
('MCA2024002', 'Priya Verma',  '2000-11-03', 'Female', 'priya.verma@example.com',  '9123456780', 1, '2024-07-15'),
('BCA2024001', 'Rohan Gupta',  '2005-01-25', 'Male',   'rohan.gupta@example.com',  '9988776655', 2, '2024-07-20');

INSERT INTO attendance (student_id, att_date, status) VALUES
(1, '2026-09-21', 'Present'), (1, '2026-09-22', 'Present'), (1, '2026-09-23', 'Absent'),
(2, '2026-09-21', 'Present'), (2, '2026-09-22', 'Leave'),   (2, '2026-09-23', 'Present'),
(3, '2026-09-21', 'Present'), (3, '2026-09-22', 'Present'), (3, '2026-09-23', 'Present');

INSERT INTO results (student_id, subject_id, exam_term, marks_obtained) VALUES
(1, 1, 'TEE-Jun-2025', 78), (1, 2, 'TEE-Jun-2025', 84), (1, 3, 'TEE-Jun-2025', 71),
(2, 1, 'TEE-Jun-2025', 88), (2, 2, 'TEE-Jun-2025', 91), (2, 3, 'TEE-Jun-2025', 79),
(3, 5, 'TEE-Jun-2025', 65), (3, 6, 'TEE-Jun-2025', 58);
