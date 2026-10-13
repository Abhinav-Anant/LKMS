export type Role = "admin" | "principal" | "office" | "accountant" | "teacher" | "parent" | "student";

export interface Me {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  role: Role;
  must_change_password: boolean;
  capabilities: string[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AcademicSession {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  admissions_open: boolean;
  age_cutoff_date: string | null;
}

export interface SchoolClass {
  id: number;
  name: string;
  code: string;
  order: number;
  min_age_years: number | null;
  max_age_years: number | null;
  is_active: boolean;
}

export interface Section {
  id: number;
  session: number;
  session_name: string;
  school_class: number;
  class_name: string;
  name: string;
  capacity: number;
  class_teacher: number | null;
  strength: number;
}

export interface DocumentType {
  id: number;
  code: string;
  name: string;
  description: string;
  is_required: boolean;
  allowed_formats: string[];
}

export type ApplicationStatus =
  | "submitted"
  | "under_review"
  | "documents_requested"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "admitted";

export type Verification = "pending" | "verified" | "rejected";

export interface ApplicationDocument {
  id: number;
  document_type: number;
  document_type_name: string;
  content_type: string;
  size: number;
  is_current: boolean;
  verification: Verification;
  verification_note: string;
  verified_by: string | null;
  verified_at: string | null;
  uploaded_at: string;
}

export interface StatusChange {
  from_status: string;
  to_status: ApplicationStatus;
  changed_by: string | null;
  message: string;
  created_at: string;
}

export interface ApplicationListItem {
  id: number;
  application_number: string;
  child_name: string;
  date_of_birth: string;
  class_name: string;
  session_name: string;
  primary_phone: string;
  status: ApplicationStatus;
  submitted_at: string;
}

export interface ApplicationForm {
  session: number | "";
  class_applied: number | "";
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: "M" | "F" | "O" | "";
  category: string;
  religion: string;
  mother_tongue: string;
  nationality: string;
  blood_group: string;
  aadhaar_number: string;
  previous_school: string;
  previous_class: string;
  sibling_admission_number: string;
  address_line: string;
  city: string;
  district: string;
  state: string;
  pincode: string;
  father_name: string;
  father_phone: string;
  father_email: string;
  father_occupation: string;
  father_qualification: string;
  father_annual_income: string;
  mother_name: string;
  mother_phone: string;
  mother_email: string;
  mother_occupation: string;
  mother_qualification: string;
  mother_annual_income: string;
  guardian_name: string;
  guardian_relationship: string;
  guardian_phone: string;
  guardian_email: string;
  guardian_occupation: string;
  primary_contact: "father" | "mother" | "guardian";
  declaration_accepted: boolean;
}

export interface ApplicationDetail extends Omit<ApplicationForm, "session" | "class_applied"> {
  id: number;
  application_number: string;
  session: number;
  class_applied: number;
  class_name: string;
  session_name: string;
  status: ApplicationStatus;
  status_message: string;
  internal_notes: string;
  reviewed_by: string | null;
  submitted_at: string;
  updated_at: string;
  decided_at: string | null;
  consent_given_at: string | null;
  documents: ApplicationDocument[];
  required_documents: DocumentType[];
  missing_documents: string[];
  history: StatusChange[];
  student_id: number | null;
}

export interface TrackResult {
  application_number: string;
  child_first_name: string;
  class_applied: string;
  session: string;
  status: ApplicationStatus;
  status_label: string;
  message: string;
  documents: { document_type: number; document_type_name: string; verification: Verification; verification_note: string; uploaded_at: string }[];
  documents_still_needed: string[];
  submitted_at: string;
}

export interface StudentListItem {
  id: number;
  admission_number: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  status: string;
  class_name: string | null;
  section_name: string | null;
}

export interface Guardian {
  id: number;
  full_name: string;
  phone: string;
  alternate_phone: string;
  email: string;
  occupation: string;
  qualification: string;
  annual_income: string | null;
  address: string;
}

export interface StudentDetail {
  id: number;
  admission_number: string;
  admission_date: string;
  admitted_in_class_name: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  category: string;
  religion: string;
  mother_tongue: string;
  nationality: string;
  blood_group: string;
  aadhaar_number: string;
  address_line: string;
  city: string;
  district: string;
  state: string;
  pincode: string;
  previous_school: string;
  status: string;
  has_photo: boolean;
  application: number | null;
  guardians: { id: number; relationship: string; relationship_detail: string; is_primary_contact: boolean; guardian: Guardian }[];
  enrollments: { id: number; session_name: string; class_name: string; section_name: string; roll_number: number | null; status: string; enrolled_on: string }[];
}

// ----- fees -----

export type InvoiceStatus = "unpaid" | "partly_paid" | "paid" | "cancelled";
export type PaymentMode = "cash" | "cheque" | "bank_transfer" | "upi";
export type UpiStatus = "pending" | "approved" | "rejected";

/** Money comes from the API as a decimal string, e.g. "7000.00". */
export type Money = string;

export interface FeeHead {
  id: number;
  code: string;
  name: string;
  new_students_only: boolean;
  order: number;
  is_active: boolean;
}

export interface Installment {
  id: number;
  session: number;
  session_name: string;
  name: string;
  due_date: string;
  order: number;
}

export interface FeeAmount {
  id: number;
  installment: number;
  school_class: number;
  fee_head: number;
  amount: Money;
}

export interface InvoiceLine {
  id: number;
  fee_head: number;
  fee_head_name: string;
  amount: Money;
  concession: Money;
  net: Money;
}

export interface FeePayment {
  id: number;
  receipt_number: string;
  invoice: number;
  invoice_number: string;
  student_name: string;
  admission_number: string;
  amount: Money;
  mode: PaymentMode;
  mode_label: string;
  reference: string;
  paid_on: string;
  status: "completed" | "reversed";
  received_by: string | null;
  created_at: string;
  reversal_reason: string;
  reversed_at: string | null;
}

export interface UpiSubmission {
  id: number;
  invoice: number;
  invoice_number: string;
  student: number;
  student_name: string;
  admission_number: string;
  class_name: string;
  invoice_balance: Money;
  amount: Money;
  utr: string;
  paid_on: string;
  payer_name: string;
  screenshot_type: string;
  status: UpiStatus;
  submitted_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  reject_reason: string;
  receipt_number: string | null;
  payment_id: number | null;
}

export interface InvoiceListItem {
  id: number;
  number: string;
  student: number;
  student_name: string;
  admission_number: string;
  class_name: string;
  installment_name: string;
  due_date: string;
  gross_amount: Money;
  concession_amount: Money;
  net_amount: Money;
  amount_paid: Money;
  balance: Money;
  status: InvoiceStatus;
}

export interface InvoiceDetail extends InvoiceListItem {
  session: number;
  session_name: string;
  cancel_reason: string;
  created_at: string;
  lines: InvoiceLine[];
  payments: FeePayment[];
  upi_submissions: UpiSubmission[];
}

export interface Concession {
  id: number;
  student: number;
  student_name: string;
  admission_number: string;
  session: number;
  session_name: string;
  fee_head: number | null;
  fee_head_name: string;
  kind: "percent" | "fixed";
  value: Money;
  reason: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  requested_by: string | null;
  requested_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string;
}

export interface DailyCollection {
  date: string;
  total: Money;
  by_mode: { mode: PaymentMode; label: string; count: number; total: Money }[];
  payments: FeePayment[];
}

export interface PublicInvoice {
  number: string;
  student_name: string;
  class_name: string;
  session_name: string;
  installment_name: string;
  due_date: string;
  lines: InvoiceLine[];
  gross_amount: Money;
  concession_amount: Money;
  net_amount: Money;
  amount_paid: Money;
  balance: Money;
  status: InvoiceStatus;
}

export interface PublicSubmission {
  amount: Money;
  utr: string;
  paid_on: string;
  status: UpiStatus;
  status_label: string;
  reject_reason: string;
  submitted_at: string;
  receipt_number: string | null;
}

export interface PayPage {
  invoice: PublicInvoice;
  school_name: string;
  upi_id: string;
  payee_name: string;
  pending_amount: Money;
  submissions: PublicSubmission[];
  receipts: { receipt_number: string; amount: Money; paid_on: string }[];
}

// Phase 3: portals

export interface SectionDetail extends Section {
  class_teacher_name: string;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  order: number;
  is_active: boolean;
}

export interface TeachingAssignment {
  id: number;
  teacher: number;
  teacher_name: string;
  section: number;
  section_label: string;
  subject: number;
  subject_name: string;
}

export interface PeriodSlot {
  id: number;
  number: number;
  start_time: string;
  end_time: string;
  label: string;
}

export interface TimetableEntry {
  id: number;
  section: number;
  section_label: string;
  weekday: number;
  period: number;
  period_number: number;
  start_time: string;
  end_time: string;
  subject: number;
  subject_name: string;
  teacher: number | null;
  teacher_name: string;
}

export interface MySection {
  id: number;
  label: string;
  class_name: string;
  name: string;
  is_class_teacher: boolean;
  subjects: { id: number; name: string }[];
  strength: number;
}

export type AttendanceStatus = "present" | "absent" | "late" | "leave";

export interface AttendanceSheet {
  section: number;
  section_label: string;
  date: string;
  can_edit: boolean;
  marked: boolean;
  marked_by: string | null;
  rows: {
    student: number;
    roll_number: number | null;
    name: string;
    admission_number: string;
    status: AttendanceStatus | null;
    note: string;
  }[];
}

export interface AttendanceMonthRow {
  student: number;
  roll_number: number | null;
  name: string;
  present: number;
  absent: number;
  late: number;
  leave: number;
  marked_days: number;
  percentage: number | null;
}

export interface Assessment {
  id: number;
  section: number;
  section_label: string;
  subject: number;
  subject_name: string;
  term: number | null;
  term_name: string | null;
  name: string;
  date: string;
  max_marks: string;
  is_published: boolean;
  published_at: string | null;
  marks_entered: number;
}

export interface MarkSheet {
  assessment: Assessment;
  can_edit: boolean;
  rows: {
    student: number;
    roll_number: number | null;
    name: string;
    admission_number: string;
    marks: string | null;
    is_absent: boolean;
    remark: string;
  }[];
}

export type NoticeAudience = "everyone" | "staff" | "parents";

export interface Notice {
  id: number;
  title: string;
  body: string;
  audience: NoticeAudience;
  audience_label: string;
  sections: number[];
  section_labels: string[];
  is_published: boolean;
  send_whatsapp: boolean;
  whatsapp_queued_at: string | null;
  published_at: string | null;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
}

export interface StaffUser {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string;
  role: Role;
  role_label: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login: string | null;
  date_joined: string;
}

export interface TemporaryPassword {
  username: string;
  temporary_password: string;
}

export interface PermissionMatrix {
  roles: { value: Role; label: string }[];
  capabilities: { key: string; roles: Role[] }[];
}

export interface Dashboard {
  session: string | null;
  date: string;
  students_total: number;
  students_by_class: { name: string; students: number }[];
  attendance_today: {
    present: number;
    absent: number;
    leave: number;
    sections_marked: number;
    sections_total: number;
    sections_not_marked: string[];
  };
  fees: { billed: string; collected: string; outstanding: string; collected_this_month: string; overdue_invoices: number };
  pending: { admissions: number; upi_payments: number; concessions: number };
  backups: { healthy: boolean; latest_at: string | null; max_age_hours: number };
}

export interface IssuedCode {
  phone: string;
  code: string;
  expires_at: string;
  children: string[];
}

export interface Child {
  id: number;
  full_name: string;
  admission_number: string;
  class_label: string | null;
  roll_number: number | null;
  class_teacher: string | null;
}

export interface ChildAttendance {
  month: string;
  present: number;
  absent: number;
  late: number;
  leave: number;
  percentage: number | null;
  days: { date: string; status: AttendanceStatus; note: string }[];
}

export interface ChildFees {
  invoices: {
    id: number;
    number: string;
    installment_name: string;
    due_date: string;
    net_amount: string;
    amount_paid: string;
    balance: string;
    status: string;
    status_label: string;
    pay_link: string | null;
  }[];
  payments: { id: number; receipt_number: string; invoice_number: string; amount: string; mode: string; mode_label: string; paid_on: string }[];
  total_due: string;
}

export interface ChildMark {
  assessment: number;
  name: string;
  subject: string;
  date: string;
  max_marks: string;
  marks: string | null;
  is_absent: boolean;
  remark: string;
}

export interface ParentNotice {
  id: number;
  title: string;
  body: string;
  published_at: string | null;
}

// Phase 4: WhatsApp

export interface WhatsAppStatus {
  enabled: boolean;
  reachable: boolean;
  state: "off" | "unreachable" | "connected" | "connecting" | "disconnected" | "qr_ready" | "error";
  phone: string | null;
  error: string;
  queued: number;
  sent_24h: number;
  failed_24h: number;
  skipped_24h: number;
  opted_out: number;
  oldest_queued: string | null;
  quiet_hours: string;
  rate_per_minute: number;
}

export interface OutgoingMessage {
  id: number;
  event: string;
  kind: "login" | "alert";
  phone: string;
  text: string;
  status: "queued" | "sending" | "sent" | "failed" | "skipped";
  status_label: string;
  skip_reason: string;
  attempts: number;
  next_attempt_at: string;
  last_error: string;
  student: number | null;
  student_name: string | null;
  created_at: string;
  sent_at: string | null;
}

export interface OptOut {
  id: number;
  phone: string;
  note: string;
  created_by_name: string | null;
  created_at: string;
}

export interface ExamTerm {
  id: number;
  session: number;
  session_name: string;
  name: string;
  order: number;
  start_date: string;
  end_date: string;
  is_published: boolean;
  published_at: string | null;
  assessments: number;
  unpublished_assessments: number;
}

export interface GradeBand {
  id: number;
  grade: string;
  min_percent: string;
  description: string;
  is_pass: boolean;
}

export interface ResultRow {
  student: number;
  roll_number: number | null;
  name: string;
  admission_number: string;
  subjects: { subject: string; percent: string | null; grade: string }[];
  obtained: string;
  maximum: string;
  percent: string | null;
  grade: string;
  result: string;
  attendance_present: number;
  attendance_marked: number;
  remark: string;
  co_scholastic: Record<string, string>;
}

export interface ResultSheet {
  term: ExamTerm;
  section: number;
  section_label: string;
  can_edit_remarks: boolean;
  co_scholastic_areas: string[];
  co_scholastic_grades: string[];
  rows: ResultRow[];
}

export interface ParentReportCard {
  term: number;
  name: string;
  session: string;
  published_at: string;
}

export type TcStatus = "requested" | "issued" | "cancelled";

export interface TransferCertificate {
  id: number;
  student: number;
  student_name: string;
  admission_number: string;
  class_label: string;
  status: TcStatus;
  number: string | null;
  application_date: string;
  leaving_date: string;
  reason: string;
  last_exam_result: string;
  conduct: string;
  remarks: string;
  fees_due: string;
  current_fees_due: string;
  dues_waived_reason: string;
  requested_at: string;
  issued_on: string | null;
  issued_by_name: string;
  cancelled_at: string | null;
  cancel_reason: string;
}

export interface ReportInfo {
  name: string;
  title: string;
  params: ("session" | "month" | "term")[];
}

export interface ReportTable {
  name: string;
  title: string;
  columns: { key: string; label: string }[];
  rows: Record<string, string | number | null>[];
}

export interface BackupStatus {
  directory: string;
  latest_at: string | null;
  healthy: boolean;
  max_age_hours: number;
  offsite_copy: boolean;
  retention: { daily: number; weekly: number; monthly: number };
  backups: { name: string; size: number; taken_at: string }[];
}
