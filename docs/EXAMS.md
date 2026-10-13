# Exams, report cards, transfer certificates and reports (Phase 5)

## Exams and report cards

Marks are still entered test by test, as in Phase 3 (My classes > Marks). Phase 5 adds **exam terms** that collect
tests into one report card.

1. **Principal: add the terms** (Exams > New exam term), e.g. *Half-yearly* (1 Apr to 30 Sep) and *Annual*
   (1 Oct to 31 Mar). The dates decide which attendance days the report card counts.
2. **Teachers: link each test to a term** with "Counts towards" when creating it, or later on the test's marks page.
   A term can hold several tests per subject (e.g. Unit Test 1 + Half-yearly exam); they are added together.
3. **Class teacher: open the results** (Exams > choose the class > Results and report cards). The sheet shows each
   student's grade per subject, overall percentage and grade, result, and attendance for the term. The class teacher
   writes a remark and the co-scholastic grades (Art and craft, Music and dance, Games and sports, Discipline,
   Cleanliness: A, B or C) and saves.
4. **Print**: "Print all report cards" gives one PDF with a page per student; "PDF" on a row gives one student's.
5. **Principal: publish** the term. Every test in the term must be published first. Publishing shows the report card
   in the parent portal (child > Report cards) and sends each family one WhatsApp message. "Withdraw from parents"
   hides it again for a correction; publishing again does not message families twice.

How the numbers are worked out:

- Subject % = marks obtained in that subject's tests ÷ their maximum marks. Absent counts as 0. A test with no
  marks entered for that student is left out.
- Overall % = all marks obtained ÷ all maximum marks (so a 100-mark exam weighs more than a 20-mark unit test).
- Grade from the grade scale (Exams > Grade scale; the principal can edit it). Result is **Pass** when the overall
  grade and every subject grade are passing grades, otherwise **Needs improvement** (with the subjects named).
- No class rank or position is printed.

## Transfer certificates (TCs)

Menu: **TCs** (admin, principal and office).

1. The office records the parent's request: student, date asked, last day at school, reason, result of the last
   exam, conduct and remarks.
2. The principal issues it. Unpaid fees block the TC; the principal can still issue it by typing a reason, which is
   printed on the TC and kept in the audit log.
3. Issuing gives the next number (`TC/2026-27/0001`, never reused or skipped), freezes the student's details as
   printed, marks the student "TC issued" and their class place "Left", and sends the family a WhatsApp message.
4. Print gives the PDF. A wrongly issued TC can be withdrawn by the principal: the student goes back to studying and
   the number stays in the register as cancelled.

## Reports

Menu: **Reports** (admin and principal). Each report shows on screen and downloads as a CSV file that opens in Excel.

| Report | Choose |
| --- | --- |
| Student strength by class, gender and category (General, OBC, MBC, SC, ST, EWS) | session |
| Attendance by class: days marked, present %, students below 75% | month |
| Students below 75% attendance | month |
| Exam results by class: passed, needs improvement, average and highest %, grade counts | exam term |
| Fees billed, concessions, collected and outstanding by class | session |
| Admission applications by class and status | session |
| Transfer certificate register | session |

The daily fee collection and fee defaulter lists stay under Fees > Reports. The dashboard also warns the principal
when the nightly backup has not run (see `BACKUPS.md`).

## Placeholders

The report card layout, the TC layout, the grade scale, the co-scholastic areas and the 75% attendance line are
placeholders. `BOARD_CHECKS.md` lists what the school needs to confirm.
