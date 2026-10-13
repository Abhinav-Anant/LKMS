# Things to confirm with the school and the Rajasthan board

LKMS works now with placeholder formats. Before the school relies on these for official documents, someone at
Lotus Kids should check each item below against what the school actually uses and what the Rajasthan education
department (RBSE / Shala Darpan / district education office) requires. Each item says where to change it.

## Needs the school's own format (please send a sample)

| Item | What LKMS does now | To change |
| --- | --- | --- |
| **Transfer certificate layout** | A4 page of numbered fields: name, father's and mother's names, nationality, category, date of birth in figures and words, date of first admission and class, last class, last exam result, working days and days present, dues, conduct, dates of application, leaving and issue, reason, remarks; signatures of preparer, checker and principal | `backend/certificates/pdf.py` |
| **TC number format** | `TC/2026-27/0001`, restarting at 1 each session | `tc_number` in `backend/certificates/services.py` |
| **Report card layout** | A4 page per student: subject × test marks, total, %, grade; overall result; attendance; co-scholastic grades; remark; three signatures; grade key | `backend/exams/pdf.py` |
| **Admission register (S.R.) number** | prefix + running number set in School setup | Django admin, School profile |

## Needs the board's rules checked

| Item | Placeholder in LKMS | Check |
| --- | --- | --- |
| Grade scale | A+ 90%, A 75%, B 60%, C 45%, D 33%, E below 33% (fail) | The scale the school / RBSE uses for Classes 1 to 8. Editable in Exams > Grade scale, no code change |
| Pass mark | 33% in each subject and overall | Whether a pass/fail result may be shown at all for these classes (the RTE Act's no-detention rules and the rules Rajasthan currently applies to them) |
| Co-scholastic areas and grades | 5 areas, grades A/B/C | The areas and grading Rajasthan prescribes. `CO_SCHOLASTIC_AREAS` in `backend/exams/grading.py` |
| Nursery to UKG report cards | same marks-based card as other classes | Pre-primary usually uses descriptive progress reports instead of marks |
| Fields required on a TC | as listed above | Whether the TC must also show the student's PEN / Shala Darpan ID / Aadhaar, the school's UDISE+ code (printed when set in the school profile), and the counter-signature of the district education officer for some transfers |
| Low attendance line | 75% | The minimum attendance the school uses for its warnings |
| Records kept | backups kept for 12 months | How long the school must keep admission registers, TCs and results (the database itself keeps them all; this only affects old backups) |

## Already done, but worth a look

- Student category list: General, OBC, MBC, SC, ST, EWS (`backend/students/choices.py`).
- All WhatsApp messages are in English. Hindi wording can be added later in `backend/messaging/templates.py`.
- Fee amounts, classes and documents are still the placeholders from Phases 1 and 2 (see `FEES.md`, `ADMISSIONS.md`).
