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
export type PaymentMode = "cash" | "cheque" | "bank_transfer" | "upi" | "online";
export type OrderStatus = "created" | "paid" | "failed" | "expired" | "mismatch";

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

export interface OnlineOrder {
  id: number;
  order_id: string;
  amount: Money;
  status: OrderStatus;
  status_note: string;
  payment_group: string;
  cf_payment_id: string;
  created_at: string;
  paid_at: string | null;
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
  online_orders: OnlineOrder[];
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

export interface PaymentIssue {
  id: number;
  kind: string;
  kind_label: string;
  order_id: string;
  invoice: number | null;
  detail: string;
  resolved: boolean;
  resolved_note: string;
  created_at: string;
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
