# Graph Report - project-graphification-ea56c1  (2026-11-02)

## Corpus Check
- 451 files · ~169,251 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 5, .service 4, .example 3)

## Summary
- 3442 nodes · 8801 edges · 165 communities (118 shown, 22 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 745 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Frontend Shared Lib & Panels
- WhatsApp Baileys Messaging
- Exams & Grading
- UI Primitives (Nav/Avatar)
- App Shell & Public Pages
- Academics Admin
- WhatsApp Express App & Routes
- Notices & Student Views
- DB Migrations
- Transfer Certificates
- Admission Document Types
- Frontend Build Tooling
- Setup School Command
- Backups
- Teaching Assignments & Marks Scope
- Frontend Dependencies
- Admission Applications
- Captcha & Form Fields
- Document Uploader
- Staff Tables & Fee Pages
- Deploy Setup Wizard
- WhatsApp Chatbot
- WhatsApp DB Config
- WhatsApp Server Dependencies
- Users & Passwords
- Parent Portal API
- Fee Invoices
- Academics Serializers
- Bulk Student Import
- Fee Pay Page & Formatting
- Admissions Admin
- PDFs & URL Config
- Fee Installments & Amounts
- WhatsApp Campaigns
- Fee Payment Serializers
- Sidebar UI
- Staff Academics Admin Pages
- WhatsApp Auth & API Keys
- Enrollments
- WhatsApp Contacts & Leads
- safemode cluster 40
- core cluster 41
- server cluster 42
- fees cluster 43
- services cluster 44
- core cluster 45
- messaging cluster 46
- hooks cluster 47
- ui cluster 48
- stores cluster 49
- ui cluster 50
- exams cluster 51
- fees cluster 52
- ui cluster 53
- services cluster 54
- students cluster 55
- server cluster 56
- stores cluster 57
- attendance cluster 58
- staff cluster 59
- attendance cluster 60
- messaging cluster 61
- landing cluster 62
- safemode cluster 63
- users cluster 64
- frontend cluster 65
- server cluster 66
- messaging cluster 67
- portal cluster 68
- ui cluster 69
- lib cluster 70
- controllers cluster 71
- fees cluster 72
- services cluster 73
- messaging cluster 74
- frontend cluster 75
- core cluster 76
- frontend cluster 77
- frontend cluster 78
- backend cluster 79
- fees cluster 80
- messaging cluster 81
- ui cluster 82
- core cluster 83
- users cluster 84
- core cluster 85
- users cluster 86
- students cluster 87
- core cluster 88
- students cluster 89
- ui cluster 90
- frontend cluster 91
- docs cluster 92
- docs cluster 93
- scripts cluster 94
- core cluster 95
- students cluster 96
- public cluster 97
- messaging cluster 98
- root cluster 99
- docs cluster 100
- docs cluster 101
- ui cluster 102
- ui cluster 103
- docs cluster 104
- docs cluster 105
- server cluster 106
- controllers cluster 107
- commands cluster 108
- docs cluster 109
- frontend cluster 110
- server cluster 111
- commands cluster 112
- ui cluster 113
- messaging cluster 114
- docs cluster 115
- config cluster 116
- backend cluster 117
- messaging cluster 118
- messaging cluster 119
- students cluster 120
- academics cluster 121
- admissions cluster 122
- assessments cluster 123
- attendance cluster 124
- certificates cluster 125
- core cluster 126
- exams cluster 127
- fees cluster 128
- messaging cluster 129
- notices cluster 130
- portal cluster 131
- students cluster 132
- users cluster 133
- lotus-kids cluster 134
- config cluster 135
- config cluster 136
- deploy cluster 138
- server cluster 139
- backend cluster 163

## God Nodes (most connected - your core abstractions)
1. `cn()` - 254 edges
2. `react` - 85 edges
3. `SchoolProfile` - 75 edges
4. `Enrollment` - 56 edges
5. `Invoice` - 54 edges
6. `Student` - 53 edges
7. `AcademicSession` - 52 edges
8. `AdmissionApplication` - 51 edges
9. `formatDate()` - 50 edges
10. `Section` - 49 edges

## Surprising Connections (you probably didn't know these)
- `robots.txt disallow all` --conceptually_related_to--> `whatsapp service (Blastup server)`  [INFERRED]
  whatsapp-server/server/public/robots.txt → docker-compose.yml
- `Admission workflow (submitted to admitted)` --semantically_similar_to--> `Multi-School Admission Workflow`  [INFERRED] [semantically similar]
  docs/ADMISSIONS.md → docs/ACHARYA_README.md
- `AttendanceRowSerializer` --uses--> `AttendanceRecord`  [INFERRED]
  backend/attendance/serializers.py → backend/attendance/models.py
- `SheetRowSerializer` --uses--> `AttendanceRecord`  [INFERRED]
  backend/attendance/serializers.py → backend/attendance/models.py
- `AttendanceDaySerializer` --uses--> `AttendanceRecord`  [INFERRED]
  backend/portal/serializers.py → backend/attendance/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Scheduled server jobs (backup, fee reminders, WhatsApp sender)** — docs_backups_lkms_backup_timer, docs_deploy_lkms_fee_reminders_timer, docs_deploy_lkms_whatsapp_sender, docs_deploy_vps_deployment [EXTRACTED 1.00]
- **Invoice to UPI payment to staff-verified receipt** — docs_fees_invoice, docs_fees_pay_link, docs_fees_upi_qr_payment, docs_fees_send_fee_reminders, docs_whatsapp_whatsapp_alerts [EXTRACTED 1.00]
- **New school onboarding** — docs_new_school_answers_file, docs_new_school_setup_wizard, docs_new_school_setup_school_command, docs_student_import_bulk_import, docs_board_checks_board_format_checklist [EXTRACTED 1.00]

## Communities (165 total, 22 thin omitted)

### Community 0 - "Frontend Shared Lib & Panels"
Cohesion: 0.05
Nodes (61): OneTimeSecret(), ErrorNote(), Panel(), TimetableGrid(), Badge(), BadgeProps, badgeVariants, api (+53 more)

### Community 1 - "WhatsApp Baileys Messaging"
Cohesion: 0.05
Nodes (68): @whiskeysockets/baileys, deleteMessage(), getChat(), markRead(), Chat, chatSchema, IChat, IMessage (+60 more)

### Community 2 - "Exams & Grading"
Cohesion: 0.05
Nodes (47): bands(), grade_for(), percent(), The grading scale and co-scholastic areas. The setup wizard lets a school pick…, Return (grade, is_pass) for a percentage, or ("", None) when there is nothing…, ExamTerm, GradeBand, Meta (+39 more)

### Community 3 - "UI Primitives (Nav/Avatar)"
Cohesion: 0.05
Nodes (66): navClass(), navClass(), Avatar, AvatarFallback, AvatarImage, Card, CardContent, CardDescription (+58 more)

### Community 4 - "App Shell & Public Pages"
Cohesion: 0.05
Nodes (48): App(), queryClient, PhotoReel(), PublicLayout(), SchoolName(), StaffHome(), StaffLayout(), TabsContent (+40 more)

### Community 5 - "Academics Admin"
Cohesion: 0.06
Nodes (46): AcademicSessionAdmin, EnrollmentAdmin, register, SchoolClassAdmin, SectionAdmin, TeachingAssignmentAdmin, TimetableEntryAdmin, AcademicSession (+38 more)

### Community 6 - "WhatsApp Express App & Routes"
Cohesion: 0.06
Nodes (42): express, express-rate-limit, @hapi/boom, multer, createApp(), getMessages(), authenticate(), AuthRequest (+34 more)

### Community 7 - "Notices & Student Views"
Cohesion: 0.05
Nodes (29): BackupFileSerializer, Can(), has_permission(), has_capability(), BasePermission, The roles holding a capability, including the school's own choices in its…, DRF permission class factory: permission_classes = [Can("students.view")]., Read needs `view_capability`, writes need `manage_capability` (set on the view). (+21 more)

### Community 8 - "DB Migrations"
Cohesion: 0.04
Nodes (36): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+28 more)

### Community 9 - "Transfer Certificates"
Cohesion: 0.05
Nodes (41): register, TransferCertificateAdmin, Meta, A school leaving / transfer certificate. Requested by the office, issued by the…, Status, TransferCertificate, CancelSerializer, IssueSerializer (+33 more)

### Community 10 - "Admission Document Types"
Cohesion: 0.08
Nodes (35): DocumentType, A document the school asks for, e.g. birth certificate. Configured in admin., AdmitSerializer, ApplicationDetailSerializer, ApplicationFormSerializer, ApplicationListSerializer, ApproveSerializer, DocumentSerializer (+27 more)

### Community 11 - "Frontend Build Tooling"
Cohesion: 0.04
Nodes (47): eslint, @types/node, typescript, zod, name, private, type, version (+39 more)

### Community 12 - "Setup School Command"
Cohesion: 0.09
Nodes (34): current_session_dates(), Answers, ask(), ask_yes(), bell_times(), check_amount(), check_colour(), check_date() (+26 more)

### Community 13 - "Backups"
Cohesion: 0.06
Nodes (49): backup_dir(), BackupError, check(), copy_offsite(), create_backup(), _db(), _dump_database(), _last_migrations() (+41 more)

### Community 14 - "Teaching Assignments & Marks Scope"
Cohesion: 0.08
Nodes (30): Who teaches which subject in which section. Gives the teacher marks entry for…, TeachingAssignment, can_enter_marks(), can_take_attendance(), Which sections a staff member may work with. Admin and principal may work with…, sees_all(), AssessmentAdmin, MarkInline (+22 more)

### Community 15 - "Frontend Dependencies"
Cohesion: 0.04
Nodes (53): dependencies, axios, class-variance-authority, clsx, cmdk, date-fns, embla-carousel-react, fflate (+45 more)

### Community 16 - "Admission Applications"
Cohesion: 0.08
Nodes (32): AdmissionApplication, Allocate the next application number for a session, e.g. LK-2026-27-00001., Status, apply(), approved_application(), test_aadhaar_is_masked_for_office_staff(), test_admit_checks_section_class_and_capacity(), test_admit_creates_student_guardians_and_enrollment() (+24 more)

### Community 17 - "Captcha & Form Fields"
Cohesion: 0.14
Nodes (26): CaptchaGate(), Challenge, Field(), FieldProps, Alert, AlertDescription, AlertTitle, alertVariants (+18 more)

### Community 18 - "Document Uploader"
Cohesion: 0.07
Nodes (35): ACCEPT, DocumentUploader(), Props, UploadedState, INVOICE_STYLE, InvoiceBadge(), STATUS_STYLE, StatusBadge() (+27 more)

### Community 19 - "Staff Tables & Fee Pages"
Cohesion: 0.12
Nodes (31): NativeSelect(), Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow (+23 more)

### Community 20 - "Deploy Setup Wizard"
Cohesion: 0.08
Nodes (43): ask(), ask_settings(), ask_yes(), backend_values(), check_absolute(), check_db_name(), check_domain(), check_email() (+35 more)

### Community 21 - "WhatsApp Chatbot"
Cohesion: 0.06
Nodes (32): handleWidgetMessage(), replyToLead(), updateChatbot(), Chatbot, chatbotRuleSchema, chatbotSchema, IChatbot, IChatbotFlowNode (+24 more)

### Community 22 - "WhatsApp DB Config"
Cohesion: 0.11
Nodes (29): bcryptjs, attemptConnection(), connectDatabase(), disconnectDatabase(), Env, envSchema, localEnv, parsed (+21 more)

### Community 23 - "WhatsApp Server Dependencies"
Cohesion: 0.04
Nodes (44): compression, cookie-parser, express-validator, ioredis, jest, pino, pino-pretty, prettier (+36 more)

### Community 24 - "Users & Passwords"
Cohesion: 0.08
Nodes (26): ChangePasswordSerializer, IssuedCodeSerializer, LoginSerializer, MeSerializer, Meta, _mobile(), ParentCodeRequestSerializer, ParentCodeVerifySerializer (+18 more)

### Community 25 - "Parent Portal API"
Cohesion: 0.11
Nodes (36): pdf_download(), AlertsPreferenceSerializer, Meta, ParentNoticeSerializer, parent_notices(), Published notices a parent with children in `sections` should see., AttendanceDaySerializer, AttendanceMonthSerializer (+28 more)

### Community 26 - "Fee Invoices"
Cohesion: 0.11
Nodes (35): FeeHead, Invoice, What one student owes for one installment., A kind of charge, e.g. Tuition fee, Admission fee, Annual charges., class1(), frontend_url(), generate(), invoice() (+27 more)

### Community 27 - "Academics Serializers"
Cohesion: 0.10
Nodes (30): AcademicSessionSerializer, EnrollmentSerializer, Meta, PeriodSlotSerializer, SchoolClassSerializer, SectionSerializer, SubjectSerializer, TeachingAssignmentSerializer (+22 more)

### Community 28 - "Bulk Student Import"
Cohesion: 0.11
Nodes (35): _aadhaar(), check(), fail(), take(), _choice(), _class_lookup(), Column, _date() (+27 more)

### Community 29 - "Fee Pay Page & Formatting"
Cohesion: 0.09
Nodes (35): formatDate(), formatMoney(), todayISO(), UPI_QR_URL, PayPage, PublicInvoice, AttendanceTab(), FeesTab() (+27 more)

### Community 30 - "Admissions Admin"
Cohesion: 0.10
Nodes (27): AdmissionApplicationAdmin, DocumentInline, DocumentTypeAdmin, HistoryInline, register, Read-mostly: decisions go through the API so they are checked and audited., ApplicationDocument, ApplicationStatusChange (+19 more)

### Community 31 - "PDFs & URL Config"
Cohesion: 0.09
Nodes (24): _d(), Transfer certificate PDF. PLACEHOLDER layout until the school gives its…, tc_pdf(), The single school this installation serves. Only one row is allowed., Take the next number from the admission register. Call inside a transaction., SchoolProfile, _base_url(), _class_range() (+16 more)

### Community 32 - "Fee Installments & Amounts"
Cohesion: 0.12
Nodes (30): FeeAmount, Installment, A point in the session when fees fall due, e.g. Quarter 1 due 10 April., How much a class pays for one head in one installment (the fee structure)., ApproveUpiSerializer, ConcessionSerializer, DecisionSerializer, FeeAmountBulkSerializer (+22 more)

### Community 33 - "WhatsApp Campaigns"
Cohesion: 0.10
Nodes (29): mongoose, Campaign, campaignSchema, ICampaign, ICampaignButton, ICampaignSliderItem, CampaignLog, campaignLogSchema (+21 more)

### Community 34 - "Fee Payment Serializers"
Cohesion: 0.11
Nodes (16): as_api_errors(), Turn validation errors raised by the services into 400 responses., PaymentSerializer, ReasonSerializer, ConcessionViewSet, DailyCollectionView, InvoiceViewSet, PaymentViewSet (+8 more)

### Community 35 - "Sidebar UI"
Cohesion: 0.07
Nodes (32): Separator, Sidebar, SidebarContent, SidebarContext, SidebarFooter, SidebarGroup, SidebarGroupAction, SidebarGroupContent (+24 more)

### Community 36 - "Staff Academics Admin Pages"
Cohesion: 0.11
Nodes (27): ALL, sectionLabel(), useSections(), useSessions(), formatTime(), PeriodSlot, ReportInfo, ReportTable (+19 more)

### Community 37 - "WhatsApp Auth & API Keys"
Cohesion: 0.09
Nodes (26): jsonwebtoken, createApiKey(), deleteApiKey(), changePassword(), COOKIE_OPTIONS, login(), logout(), register() (+18 more)

### Community 38 - "Enrollments"
Cohesion: 0.09
Nodes (31): Enrollment, A student's place in a section for one session., Status, _backups(), dashboard(), DashboardSerializer, api_view, extend_schema (+23 more)

### Community 39 - "WhatsApp Contacts & Leads"
Cohesion: 0.09
Nodes (26): getChats(), listLeads(), deleteContact(), getContact(), getContacts(), getGroups(), importContacts(), updateContact() (+18 more)

### Community 40 - "safemode cluster 40"
Cohesion: 0.12
Nodes (5): createSafeModeRouter(), SafeModeManager, ISafeModeStore, wrapBaileysSocket(), main()

### Community 41 - "core cluster 41"
Cohesion: 0.10
Nodes (16): AuditLogAdmin, register, SchoolProfileAdmin, AuditLog, GalleryPhoto, Meta, A photo of school life, shown to everyone on the website's gallery., Append-only record of who did what to student data. (+8 more)

### Community 42 - "server cluster 42"
Cohesion: 0.07
Nodes (30): dependencies, bcryptjs, compression, cookie-parser, cors, dotenv, express, express-mongo-sanitize (+22 more)

### Community 43 - "fees cluster 43"
Cohesion: 0.14
Nodes (27): Write an audit entry for `obj`. `request` may be None for system actions., record(), Concession, Kind, A discount for one student in one session. Takes effect only once approved., Status, apply_concessions(), approved_concessions() (+19 more)

### Community 44 - "services cluster 44"
Cohesion: 0.12
Nodes (23): getAICreditStatus(), uploadChatTraining(), AITrainingMessage, schema, basicReply(), generateLocalLearnedReply(), normalize(), safeLearnedReply() (+15 more)

### Community 45 - "core cluster 45"
Cohesion: 0.07
Nodes (16): Migration, carry_over(), Migration, Installs made before this version: keep the board and the UPI account from…, Migration, detect_type(), get_private_storage(), PrivateStorage (+8 more)

### Community 46 - "messaging cluster 46"
Cohesion: 0.18
Nodes (25): Kind, OutgoingMessage, One WhatsApp message: queued by `core.notify`, sent by the `send_whatsapp`…, Status, Send what is due, within the per-minute limit. Returns how many were sent., send_due(), _alerts(), request_code() (+17 more)

### Community 47 - "hooks cluster 47"
Cohesion: 0.11
Nodes (24): Toast, ToastAction, ToastActionElement, ToastClose, ToastDescription, ToastProps, ToastTitle, toastVariants (+16 more)

### Community 48 - "ui cluster 48"
Cohesion: 0.11
Nodes (22): FormControl, FormDescription, FormFieldContext, FormFieldContextValue, FormItem, FormItemContext, FormItemContextValue, FormLabel (+14 more)

### Community 50 - "ui cluster 50"
Cohesion: 0.08
Nodes (21): AccordionContent, AccordionItem, AccordionTrigger, Breadcrumb, BreadcrumbEllipsis(), BreadcrumbItem, BreadcrumbLink, BreadcrumbList (+13 more)

### Community 51 - "exams cluster 51"
Cohesion: 0.14
Nodes (18): create_test(), test_marks_above_maximum_are_refused(), test_subject_teacher_enters_and_publishes_marks(), test_teacher_cannot_create_tests_for_subjects_they_do_not_teach(), test_teachers_only_see_their_own_subjects(), as_user(), test_class_result_sheet(), test_class_teacher_writes_remarks_but_subject_teacher_cannot() (+10 more)

### Community 52 - "fees cluster 52"
Cohesion: 0.13
Nodes (17): Remind parents about fees due soon or overdue. Run daily, e.g. from cron: 0 9 *…, InvoiceLine, Meta, Mode, Payment, A parent's report that they paid by scanning the school's UPI QR code. Nothing…, UpiSubmission, approve() (+9 more)

### Community 53 - "ui cluster 53"
Cohesion: 0.09
Nodes (22): AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter(), AlertDialogHeader(), AlertDialogOverlay, AlertDialogTitle (+14 more)

### Community 54 - "services cluster 54"
Cohesion: 0.17
Nodes (23): IContact, createReminderFromMessage(), createSendMessage(), deliveryJid(), directPhoneContact(), findContacts(), flexibleSend(), handleReminderCommand() (+15 more)

### Community 55 - "students cluster 55"
Cohesion: 0.21
Nodes (19): Status, Student, admin(), jpeg(), photo_zip(), fixture, row(), sheet() (+11 more)

### Community 56 - "server cluster 56"
Cohesion: 0.08
Nodes (24): devDependencies, eslint, jest, prettier, ts-jest, ts-node, ts-node-dev, @types/bcryptjs (+16 more)

### Community 58 - "attendance cluster 58"
Cohesion: 0.18
Nodes (14): AttendanceMarkSerializer, AttendanceRowSerializer, MonthSummaryRowSerializer, SheetQuerySerializer, SheetRowSerializer, SheetSerializer, MonthSummaryView, parse_month() (+6 more)

### Community 59 - "staff cluster 59"
Cohesion: 0.10
Nodes (19): CONCESSION_STATUS_LABELS, formatDateTime(), WHATSAPP_EVENT_LABELS, Concession, FeeHead, OptOut, OutgoingMessage, StudentListItem (+11 more)

### Community 60 - "attendance cluster 60"
Cohesion: 0.15
Nodes (16): AttendanceRecordAdmin, register, AttendanceRecord, Meta, One student's attendance for one school day, marked by the class teacher., Status, payload(), school_day() (+8 more)

### Community 61 - "messaging cluster 61"
Cohesion: 0.15
Nodes (13): Meta, OptOut, A number that asked not to get WhatsApp alerts. Sign-in codes the parent asks…, Meta, OptOutSerializer, OutgoingMessageSerializer, QrSerializer, WhatsAppStatusSerializer (+5 more)

### Community 62 - "landing cluster 62"
Cohesion: 0.16
Nodes (18): canRun3D(), Hero3D(), HeroFallback(), HeroScene, apple(), beachBall(), blockFace(), book() (+10 more)

### Community 63 - "safemode cluster 63"
Cohesion: 0.25
Nodes (12): safeModeErrorHandler(), SafeModeError, SafeModeErrorCode, computeNextTier(), getTierConfig(), LINK_REGEX, SENDING_WINDOW_END_UTC, SENDING_WINDOW_START_UTC (+4 more)

### Community 64 - "users cluster 64"
Cohesion: 0.14
Nodes (14): AbstractUser, make_user(), register, UserAdmin, A login. Staff sign in with username and password; parents with their mobile…, Role, User, test_login_returns_tokens_and_capabilities() (+6 more)

### Community 65 - "frontend cluster 65"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+12 more)

### Community 66 - "server cluster 66"
Cohesion: 0.10
Nodes (20): compilerOptions, declaration, declarationMap, emitDecoratorMetadata, esModuleInterop, experimentalDecorators, forceConsistentCasingInFileNames, lib (+12 more)

### Community 67 - "messaging cluster 67"
Cohesion: 0.21
Nodes (19): _about(), admission_status_changed(), admission_submitted(), attendance_absent(), _date(), fee_payment_received(), fee_reminder(), fee_upi_rejected() (+11 more)

### Community 68 - "portal cluster 68"
Cohesion: 0.15
Nodes (15): code_from_log(), sign_in(), test_code_works_once_and_expires(), test_parent_accounts_cannot_use_staff_login(), test_parent_cannot_use_staff_pages_or_other_children(), test_parent_fees_show_pay_link_and_receipts(), test_parent_sees_attendance_published_marks_timetable_and_notices(), test_parent_signs_in_with_a_code_and_sees_both_children() (+7 more)

### Community 69 - "ui cluster 69"
Cohesion: 0.11
Nodes (17): Command, CommandDialogProps, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator (+9 more)

### Community 70 - "lib cluster 70"
Cohesion: 0.16
Nodes (15): describeError(), fetchFileUrl(), onSignedOut(), readRefresh(), refreshAccess(), request(), RequestOptions, send() (+7 more)

### Community 71 - "controllers cluster 71"
Cohesion: 0.16
Nodes (18): uuid, fileFilter(), sendAudio(), sendButton(), sendDocument(), sendImage(), sendSlider(), sendText() (+10 more)

### Community 72 - "fees cluster 72"
Cohesion: 0.16
Nodes (13): ConcessionAdmin, FeeAmountInline, FeeHeadAdmin, InstallmentAdmin, InvoiceAdmin, LineInline, PaymentAdmin, PaymentInline (+5 more)

### Community 73 - "services cluster 73"
Cohesion: 0.18
Nodes (18): testKnowledgeQuery(), IChatbotKnowledge, buildSuggestions(), detectIntent(), expandWithContext(), getSession(), Intent, INTENT_PATTERNS (+10 more)

### Community 74 - "messaging cluster 74"
Cohesion: 0.15
Nodes (17): due_messages(), expire_stale(), _failed(), in_quiet_hours(), queue(), Queue and send WhatsApp messages. `queue()` is called by `core.notify` inside…, Staff asked to send a failed message again., Turn a notify() event into queued messages. Returns the rows created. (+9 more)

### Community 75 - "frontend cluster 75"
Cohesion: 0.11
Nodes (18): devDependencies, autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, postcss (+10 more)

### Community 76 - "core cluster 76"
Cohesion: 0.18
Nodes (13): CaptchaView, health(), _picture_response(), public_school(), action, api_view, APIView, extend_schema (+5 more)

### Community 77 - "frontend cluster 77"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, rsc, $schema (+8 more)

### Community 78 - "frontend cluster 78"
Cohesion: 0.12
Nodes (15): compilerOptions, allowImportingTsExtensions, isolatedModules, lib, module, moduleDetection, moduleResolution, noEmit (+7 more)

### Community 79 - "backend cluster 79"
Cohesion: 0.18
Nodes (12): application_data(), client_for(), _client(), _isolated(), public(), fixture, section(), seeded() (+4 more)

### Community 80 - "fees cluster 80"
Cohesion: 0.16
Nodes (10): client_ip(), DefaultersView, pdf_response(), PublicInvoiceView, _PublicPay, PublicReceiptView, PublicUpiSubmitView, APIView (+2 more)

### Community 81 - "messaging cluster 81"
Cohesion: 0.19
Nodes (13): test_http_client_talks_to_the_blastup_api(), _call(), Exception, qr_code(), Client for the WhatsApp server in whatsapp-server/ (Blastup). It runs on the…, Sending failed. `retry` says whether trying again later may work., Send a text to a 10-digit Indian mobile number. Returns the WhatsApp message id., Connection state of the school's WhatsApp number: {'state': 'connected' |… (+5 more)

### Community 82 - "ui cluster 82"
Cohesion: 0.17
Nodes (14): Carousel, CarouselApi, CarouselContent, CarouselContext, CarouselContextProps, CarouselItem, CarouselNext, CarouselOptions (+6 more)

### Community 83 - "core cluster 83"
Cohesion: 0.22
Nodes (13): _answer_hash(), enabled(), new_challenge(), _picture(), A self-hosted picture CAPTCHA for the public forms. No outside service, no…, True the first time a nonce is seen; False on a replay., Checks the typed letters. Returns a pass token, or None. A challenge can be…, Call at the top of a public form's POST. Raises a 400 unless the form carries a… (+5 more)

### Community 84 - "users cluster 84"
Cohesion: 0.15
Nodes (9): MeView, permission_matrix(), action, api_view, extend_schema, permission_classes, Staff accounts. New accounts and resets get a temporary password that must be…, Which role may do what. Read-only: changing it is a code change. (+1 more)

### Community 85 - "core cluster 85"
Cohesion: 0.23
Nodes (10): answer(), fixture, deploy/setup_wizard.py, the server settings wizard (plain Python, loaded from…, repo(), test_dry_run_as_root_only_shows_commands(), test_first_run_writes_settings(), test_not_saving_changes_nothing(), test_running_again_keeps_secrets_and_other_settings() (+2 more)

### Community 86 - "users cluster 86"
Cohesion: 0.26
Nodes (12): children_for_phone(), has_children(), _hash(), issue_code(), _new_code(), parent_user(), Parent sign-in with mobile number and a one-time code. A parent account is…, Send a code if the number belongs to a parent. Says nothing either way, so… (+4 more)

### Community 87 - "students cluster 87"
Cohesion: 0.23
Nodes (7): _mobile(), Migration, normalise_mobile(), Strip spaces, dashes and a leading +91 / 0 so numbers compare equal., validate_aadhaar(), validate_indian_mobile(), validate_pincode()

### Community 88 - "core cluster 88"
Cohesion: 0.18
Nodes (6): fixture, Pictures come back as their plain letters, so the test can 'read' them., readable(), solve(), test_application_needs_a_pass_used_once(), test_switching_it_off()

### Community 89 - "students cluster 89"
Cohesion: 0.23
Nodes (9): GuardianAdmin, register, StudentAdmin, StudentGuardianInline, _create_student(), Guardian, Meta, A parent or guardian. One guardian can be linked to several children (siblings). (+1 more)

### Community 90 - "ui cluster 90"
Cohesion: 0.23
Nodes (10): ChartConfig, ChartContainer, ChartContext, ChartContextProps, ChartLegendContent, ChartTooltipContent, getPayloadConfigFromPayload(), THEMES (+2 more)

### Community 91 - "frontend cluster 91"
Cohesion: 0.17
Nodes (11): compilerOptions, allowJs, baseUrl, noImplicitAny, noUnusedLocals, noUnusedParameters, paths, skipLibCheck (+3 more)

### Community 92 - "docs cluster 92"
Cohesion: 0.22
Nodes (11): mongo service (mongo:7), redis service (redis:7-alpine), whatsapp service (Blastup server), lkms-whatsapp-sender service, Baileys unofficial WhatsApp Web ban risk, Django messaging module with queue (adapter), WhatsApp opt-outs, WhatsApp safety limits (rate, quiet hours, daily cap) (+3 more)

### Community 93 - "docs cluster 93"
Cohesion: 0.22
Nodes (11): Private document storage, manage.py backup, lkms-backup.timer (nightly 02:30), Encrypted off-site copy (rclone crypt), manage.py restore_backup, Backup retention (daily/weekly/monthly), Read-only GitHub deploy key, Gunicorn lkms-web service (+3 more)

### Community 94 - "scripts cluster 94"
Cohesion: 0.24
Nodes (9): dotenv, defaultState(), PhoneState, todayUtc(), SafeModeTier, IS_EXECUTE, localEnv, Recommendation (+1 more)

### Community 95 - "core cluster 95"
Cohesion: 0.29
Nodes (3): The school's settings. Pictures are sent as files; `remove_logo` /…, SchoolProfileSerializer, SchoolProfileView

### Community 96 - "students cluster 96"
Cohesion: 0.20
Nodes (7): _json_list(), APIView, Photos for students already in LKMS, named by admission number (0101.jpg).…, The browser sends the names of the photos it holds as a JSON list., Bulk import from the sample sheet. POST with commit=false checks only;…, StudentImportView, StudentPhotoImportView

### Community 97 - "public cluster 97"
Cohesion: 0.24
Nodes (3): addMessage(), buildLeadForm(), setOpen()

### Community 98 - "messaging cluster 98"
Cohesion: 0.33
Nodes (9): summary(), api_view, extend_schema, permission_classes, qr_view(), Is the school's WhatsApp number connected, and how is the queue doing., QR code to link the school's phone (WhatsApp > Linked devices)., reconnect_view() (+1 more)

### Community 99 - "root cluster 99"
Cohesion: 0.28
Nodes (9): postgres service (postgres:16), LKMS build plan (5 phases), Session-Class-Section-Enrollment data model, Per-school isolated installation, Frontend SPA HTML shell (root + main.tsx), acharya base repository (frankmathewsajan/acharya), Django + DRF backend, LKMS school management system (+1 more)

### Community 100 - "docs cluster 100"
Cohesion: 0.22
Nodes (9): Acharya Multi-School Management System, Category-Based Fee Management, Multi-School Admission Workflow, Role-Based Dashboards, lkms-fee-reminders.timer (10:00 daily), Signed pay link (/pay/<token>), send_fee_reminders command, UPI QR payment with staff verification (+1 more)

### Community 101 - "docs cluster 101"
Cohesion: 0.22
Nodes (9): TC number format, Transfer certificate (TC), Concession, Fee head, Installment, Invoice and receipt numbering, Role permissions (core/permissions.py), Principal/admin dashboard (+1 more)

### Community 102 - "ui cluster 102"
Cohesion: 0.25
Nodes (8): NavigationMenu, NavigationMenuContent, NavigationMenuIndicator, NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle, NavigationMenuViewport, @radix-ui/react-navigation-menu

### Community 103 - "ui cluster 103"
Cohesion: 0.25
Nodes (8): SheetContent, SheetContentProps, SheetDescription, SheetFooter(), SheetHeader(), SheetOverlay, SheetTitle, sheetVariants

### Community 104 - "docs cluster 104"
Cohesion: 0.29
Nodes (8): JWT Authentication, School-wide CSV reports, Daily attendance register, Notices, Parent mobile OTP sign-in, Teacher portal (My classes), Timetable and bell times, WhatsApp alerts

### Community 105 - "docs cluster 105"
Cohesion: 0.32
Nodes (8): Aadhaar masking, Admission (S.R.) number, Admission workflow (submitted to admitted), Audit log, Hidden website honeypot field, Public admissions API (apply/track/documents), Bulk student import (import_students), Sample .xlsx template

### Community 106 - "server cluster 106"
Cohesion: 0.25
Nodes (8): scripts, build, dev, format, lint, seed, start, test

### Community 107 - "controllers cluster 107"
Cohesion: 0.43
Nodes (7): createCampaign(), deleteCampaign(), getCampaign(), getCampaignLogs(), listCampaigns(), reCampaign(), getCampaignById()

### Community 108 - "commands cluster 108"
Cohesion: 0.33
Nodes (3): Command, BaseCommand, Import students from the sample sheet on the server, e.g. when the photos are…

### Community 109 - "docs cluster 109"
Cohesion: 0.38
Nodes (7): Board/school format checklist, Co-scholastic areas (CO_SCHOLASTIC_AREAS), Grade scale placeholder, RBSE / Shala Darpan (Rajasthan board), Exam term, Report card, Tests and marks

### Community 110 - "frontend cluster 110"
Cohesion: 0.29
Nodes (7): scripts, build, build:dev, dev, lint, preview, typecheck

### Community 111 - "server cluster 111"
Cohesion: 0.29
Nodes (5): cors, express-mongo-sanitize, helmet, hpp, applySecurity()

### Community 112 - "commands cluster 112"
Cohesion: 0.33
Nodes (3): Command, BaseCommand, Deliver queued WhatsApp messages. Run it as a service on the server: python…

### Community 113 - "ui cluster 113"
Cohesion: 0.33
Nodes (5): InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot, input-otp

### Community 115 - "docs cluster 115"
Cohesion: 0.70
Nodes (5): Answers file (school.json), manage.py setup_school, Setup wizard (deploy/setup_wizard.py), Green Valley sample CBSE school answers, Lotus Kids School answers

### Community 117 - "backend cluster 117"
Cohesion: 0.50
Nodes (3): main(), Django's command-line utility for administrative tasks., Run administrative tasks.

### Community 118 - "messaging cluster 118"
Cohesion: 0.67
Nodes (3): OptOutAdmin, OutgoingMessageAdmin, register

### Community 119 - "messaging cluster 119"
Cohesion: 0.50
Nodes (3): fixture, WhatsApp switched on, with a fake sender that records what it was asked to send., wa()

### Community 120 - "students cluster 120"
Cohesion: 0.50
Nodes (4): attach_photos(), prepare_photo(), Check an uploaded photo and return it as a JPEG of at most 600 px, without…, Give existing students their photos. File names are admission numbers, e.g.…

### Community 134 - "lotus-kids cluster 134"
Cohesion: 1.00
Nodes (3): Lotus Kids School Fee UPI QR Code (example), Lotus Kids Education Society (UPI merchant), UPI Scan & Pay Fee Payment

## Knowledge Gaps
- **532 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Status` (+527 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1150 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SchoolProfile` connect `PDFs & URL Config` to `Exams & Grading`, `Academics Admin`, `Notices & Student Views`, `DB Migrations`, `core cluster 137`, `Setup School Command`, `Admission Applications`, `Users & Passwords`, `Fee Invoices`, `Bulk Student Import`, `Admissions Admin`, `Fee Installments & Amounts`, `core cluster 41`, `core cluster 45`, `fees cluster 52`, `students cluster 55`, `messaging cluster 67`, `core cluster 76`, `core cluster 83`, `core cluster 88`, `students cluster 89`, `core cluster 95`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `Student` connect `students cluster 55` to `Exams & Grading`, `Academics Admin`, `Notices & Student Views`, `Transfer Certificates`, `Admission Document Types`, `Setup School Command`, `Teaching Assignments & Marks Scope`, `Admission Applications`, `Fee Invoices`, `Bulk Student Import`, `Admissions Admin`, `PDFs & URL Config`, `core cluster 41`, `core cluster 45`, `backend cluster 79`, `users cluster 86`, `students cluster 87`, `students cluster 89`, `students cluster 120`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `WhatsApp alerts` connect `docs cluster 104` to `messaging cluster 67`, `docs cluster 100`, `docs cluster 101`, `root cluster 99`, `docs cluster 109`, `docs cluster 92`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `SchoolProfile` (e.g. with `AdmissionApplication` and `admit()`) actually correct?**
  _`SchoolProfile` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `Enrollment` (e.g. with `EnrollmentSerializer` and `my_sections()`) actually correct?**
  _`Enrollment` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Migration`, `Migration`, `Migration` to the rest of the system?**
  _532 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend Shared Lib & Panels` be split into smaller, more focused modules?**
  _Cohesion score 0.05307797537619699 - nodes in this community are weakly interconnected._