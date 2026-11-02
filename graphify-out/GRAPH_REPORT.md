# Graph Report - landing-page-background-photo-52719e  (2026-11-02)

## Corpus Check
- 450 files · ~176,593 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: (none) 5, .service 4, .example 3)

## Summary
- 3445 nodes · 8803 edges · 167 communities (120 shown, 23 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 745 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0031a38e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- lib/types.ts
- whatsapp.service.ts
- GradeBand
- cn
- utils.ts
- AcademicSession
- app.ts
- exams/views.py
- django_db
- certificates/services.py
- admissions/views.py
- frontend/package.json
- setup_school.py
- core/backup.py
- assessments/views.py
- dependencies
- admissions/tests.py
- react
- labels.ts
- InvoiceDetail.tsx
- setup_wizard.py
- chatbot.controller.ts
- env.ts
- server/package.json
- users/views.py
- portal/views.py
- Invoice
- academics/views.py
- bulk_import.py
- formatDate
- AdmissionApplication
- SchoolProfile
- fees/views.py
- campaign.service.ts
- as_api_errors
- sidebar.tsx
- App.tsx
- auth.controller.ts
- Enrollment
- chat.service.ts
- ISafeModeStore
- AuditLog
- dependencies
- fees/services.py
- openai-assistant.service.ts
- PrivateStorage
- OutgoingMessage
- toast.tsx
- form.tsx
- RedisSafeModeStore
- lucide-react
- as_user
- message.service.ts
- pagination.tsx
- reminder.service.ts
- Student
- devDependencies
- MemorySafeModeStore
- AttendanceRecord
- core/models.py
- attendance/tests.py
- messaging/views.py
- HeroScene.tsx
- safemode/index.ts
- conftest.py
- compilerOptions
- compilerOptions
- templates.py
- portal/tests.py
- command.tsx
- api.ts
- send.controller.ts
- fees/admin.py
- apikey.controller.ts
- outbox.py
- devDependencies
- ExamTermViewSet
- components.json
- compilerOptions
- report.py
- Message.ts
- whatsapp.py
- carousel.tsx
- captcha.py
- whatsapp-report.service.ts
- test_setup_wizard.py
- parent_login.py
- whatsapp-builder.service.ts
- test_captcha.py
- admissions/models.py
- chart.tsx
- compilerOptions
- Blastup WhatsApp server (kalpintelligence/Blastup)
- VPS deployment guide (Ubuntu 24.04)
- students/tests.py
- SchoolProfileSerializer
- StudentImportView
- widget.js
- AuditLogAdmin
- LKMS school management system
- UPI QR payment with staff verification
- Invoice and receipt numbering
- navigation-menu.tsx
- sheet.tsx
- WhatsApp alerts
- Admission workflow (submitted to admitted)
- scripts
- campaign.controller.ts
- breadcrumb.tsx
- Board/school format checklist
- scripts
- drawer.tsx
- send_whatsapp.py
- certificates/tests.py
- _FakeBlastup
- Setup wizard (deploy/setup_wizard.py)
- settings.py
- manage.py
- messaging/admin.py
- wa
- RandomPath
- AcademicsConfig
- AdmissionsConfig
- AssessmentsConfig
- AttendanceConfig
- CertificatesConfig
- CoreConfig
- ExamsConfig
- FeesConfig
- MessagingConfig
- NoticesConfig
- PortalConfig
- StudentsConfig
- UsersConfig
- Lotus Kids School Fee UPI QR Code (example)
- asgi.py
- wsgi.py
- 0004_school_branding_and_payments.py
- update.sh
- Command
- lkms-backend
- scroll-area.tsx
- CLAUDE.md

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
- `Admission workflow (submitted to admitted)` --semantically_similar_to--> `Multi-School Admission Workflow`  [INFERRED] [semantically similar]
  docs/ADMISSIONS.md → docs/ACHARYA_README.md
- `robots.txt disallow all` --conceptually_related_to--> `whatsapp service (Blastup server)`  [INFERRED]
  whatsapp-server/server/public/robots.txt → docker-compose.yml
- `test_form_filled_by_a_bot_is_refused()` --uses--> `AdmissionApplication`  [INFERRED]
  backend/admissions/tests.py → backend/admissions/models.py
- `AttendanceDaySerializer` --uses--> `AttendanceRecord`  [INFERRED]
  backend/portal/serializers.py → backend/attendance/models.py
- `test_every_report_runs()` --uses--> `AttendanceRecord`  [INFERRED]
  backend/portal/test_tables.py → backend/attendance/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **New school onboarding** — docs_new_school_answers_file, docs_new_school_setup_wizard, docs_new_school_setup_school_command, docs_student_import_bulk_import, docs_board_checks_board_format_checklist [EXTRACTED 1.00]
- **Scheduled server jobs (backup, fee reminders, WhatsApp sender)** — docs_backups_lkms_backup_timer, docs_deploy_lkms_fee_reminders_timer, docs_deploy_lkms_whatsapp_sender, docs_deploy_vps_deployment [EXTRACTED 1.00]
- **Invoice to UPI payment to staff-verified receipt** — docs_fees_invoice, docs_fees_pay_link, docs_fees_upi_qr_payment, docs_fees_send_fee_reminders, docs_whatsapp_whatsapp_alerts [EXTRACTED 1.00]

## Communities (167 total, 23 thin omitted)

### Community 0 - "lib/types.ts"
Cohesion: 0.05
Nodes (41): ATTENDANCE_LABELS, useChildren(), ApplicationListItem, AttendanceMonthRow, AttendanceSheet, AttendanceStatus, BackupStatus, Child (+33 more)

### Community 1 - "whatsapp.service.ts"
Cohesion: 0.07
Nodes (38): pino, qrcode, chatbotRuleSchema, chatbotSchema, IChatbot, IChatbotFlowNode, IChatbotRule, InstanceStatus (+30 more)

### Community 2 - "GradeBand"
Cohesion: 0.11
Nodes (15): ExamTerm, GradeBand, Meta, One row of the grading scale: a percentage of at least `min_percent` earns…, What the class teacher adds to a student's report card for a term., A reporting period that groups tests into one report card, e.g. Half-yearly or…, ReportCardEntry, ExamTermSerializer (+7 more)

### Community 3 - "cn"
Cohesion: 0.05
Nodes (58): navClass(), navClass(), Avatar, AvatarFallback, AvatarImage, Card, CardContent, CardDescription (+50 more)

### Community 4 - "utils.ts"
Cohesion: 0.08
Nodes (25): App(), PhotoReel(), PublicLayout(), SchoolName(), StaffLayout(), apiUrl(), applyColour(), applyRememberedBranding() (+17 more)

### Community 5 - "AcademicSession"
Cohesion: 0.06
Nodes (44): AcademicSessionAdmin, EnrollmentAdmin, register, SchoolClassAdmin, SectionAdmin, TeachingAssignmentAdmin, TimetableEntryAdmin, AcademicSession (+36 more)

### Community 6 - "app.ts"
Cohesion: 0.06
Nodes (39): compression, cookie-parser, express, express-rate-limit, swagger-jsdoc, swagger-ui-express, getMessages(), authenticate() (+31 more)

### Community 7 - "exams/views.py"
Cohesion: 0.05
Nodes (30): Sections the user teaches in (as class teacher or subject teacher), current…, teacher_sections(), BackupFileSerializer, Can(), has_permission(), has_capability(), BasePermission, The roles holding a capability, including the school's own choices in its… (+22 more)

### Community 8 - "django_db"
Cohesion: 0.03
Nodes (39): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+31 more)

### Community 9 - "certificates/services.py"
Cohesion: 0.06
Nodes (34): register, TransferCertificateAdmin, Meta, A school leaving / transfer certificate. Requested by the office, issued by the…, Status, TransferCertificate, CancelSerializer, IssueSerializer (+26 more)

### Community 10 - "admissions/views.py"
Cohesion: 0.06
Nodes (46): AdmissionApplicationAdmin, DocumentInline, DocumentTypeAdmin, HistoryInline, register, Read-mostly: decisions go through the API so they are checked and audited., ApplicationDocument, ApplicationStatusChange (+38 more)

### Community 11 - "frontend/package.json"
Cohesion: 0.04
Nodes (45): eslint, @types/node, typescript, zod, name, private, type, version (+37 more)

### Community 12 - "setup_school.py"
Cohesion: 0.09
Nodes (35): current_session_dates(), Answers, ask(), ask_yes(), bell_times(), check_amount(), check_colour(), check_date() (+27 more)

### Community 13 - "core/backup.py"
Cohesion: 0.06
Nodes (49): backup_dir(), BackupError, check(), copy_offsite(), create_backup(), _db(), _dump_database(), _last_migrations() (+41 more)

### Community 14 - "assessments/views.py"
Cohesion: 0.11
Nodes (23): Who teaches which subject in which section. Gives the teacher marks entry for…, TeachingAssignment, can_enter_marks(), can_take_attendance(), Which sections a staff member may work with. Admin and principal may work with…, sees_all(), AssessmentSerializer, MarkRowSerializer (+15 more)

### Community 15 - "dependencies"
Cohesion: 0.04
Nodes (53): dependencies, axios, class-variance-authority, clsx, cmdk, date-fns, embla-carousel-react, fflate (+45 more)

### Community 16 - "admissions/tests.py"
Cohesion: 0.15
Nodes (26): apply(), approved_application(), test_aadhaar_is_masked_for_office_staff(), test_admit_checks_section_class_and_capacity(), test_admit_creates_student_guardians_and_enrollment(), test_application_numbers_are_sequential(), test_approval_waits_for_verified_documents(), test_decided_application_cannot_be_edited_or_receive_documents() (+18 more)

### Community 17 - "react"
Cohesion: 0.08
Nodes (50): CaptchaGate(), Challenge, Field(), FieldProps, OneTimeSecret(), Panel(), Alert, AlertDescription (+42 more)

### Community 18 - "labels.ts"
Cohesion: 0.05
Nodes (50): ACCEPT, DocumentUploader(), Props, UploadedState, INVOICE_STYLE, STATUS_STYLE, StatusBadge(), VERIFICATION_ICON (+42 more)

### Community 19 - "InvoiceDetail.tsx"
Cohesion: 0.11
Nodes (34): NativeSelect(), ErrorNote(), InvoiceBadge(), Table, TableBody, TableCell, TableFooter, TableHead (+26 more)

### Community 20 - "setup_wizard.py"
Cohesion: 0.08
Nodes (43): ask(), ask_settings(), ask_yes(), backend_values(), check_absolute(), check_db_name(), check_domain(), check_email() (+35 more)

### Community 21 - "chatbot.controller.ts"
Cohesion: 0.07
Nodes (33): handleWidgetMessage(), replyToLead(), updateChatbot(), testKnowledgeQuery(), Chatbot, ChatbotKnowledge, chatbotKnowledgeSchema, IChatbotKnowledge (+25 more)

### Community 22 - "env.ts"
Cohesion: 0.10
Nodes (35): mongoose, socket.io, winston, createApp(), attemptConnection(), connectDatabase(), disconnectDatabase(), Env (+27 more)

### Community 23 - "server/package.json"
Cohesion: 0.04
Nodes (45): bcryptjs, cors, dotenv, express-mongo-sanitize, express-validator, helmet, hpp, ioredis (+37 more)

### Community 24 - "users/views.py"
Cohesion: 0.06
Nodes (35): ChangePasswordSerializer, IssuedCodeSerializer, LoginSerializer, MeSerializer, Meta, _mobile(), ParentCodeRequestSerializer, ParentCodeVerifySerializer (+27 more)

### Community 25 - "portal/views.py"
Cohesion: 0.11
Nodes (37): pdf_download(), Mode, Payment, pdf_response(), AlertsPreferenceSerializer, parent_notices(), Published notices a parent with children in `sections` should see., AttendanceDaySerializer (+29 more)

### Community 26 - "Invoice"
Cohesion: 0.11
Nodes (35): FeeHead, Invoice, What one student owes for one installment., A kind of charge, e.g. Tuition fee, Admission fee, Annual charges., class1(), frontend_url(), generate(), invoice() (+27 more)

### Community 27 - "academics/views.py"
Cohesion: 0.09
Nodes (32): TimetableEntry, Weekday, AcademicSessionSerializer, EnrollmentSerializer, Meta, PeriodSlotSerializer, SchoolClassSerializer, SectionSerializer (+24 more)

### Community 28 - "bulk_import.py"
Cohesion: 0.08
Nodes (39): _aadhaar(), attach_photos(), check(), fail(), take(), _choice(), _class_lookup(), Column (+31 more)

### Community 29 - "formatDate"
Cohesion: 0.09
Nodes (35): formatDate(), formatMoney(), todayISO(), UPI_QR_URL, Dashboard, PayPage, PublicInvoice, AttendanceTab() (+27 more)

### Community 30 - "AdmissionApplication"
Cohesion: 0.13
Nodes (20): AdmissionApplication, hash_token(), Allocate the next application number for a session, e.g. LK-2026-27-00001., Status, add_document(), admit(), age_on(), approve() (+12 more)

### Community 31 - "SchoolProfile"
Cohesion: 0.15
Nodes (12): The single school this installation serves. Only one row is allowed., Take the next number from the admission register. Call inside a transaction., SchoolProfile, _base_url(), _class_range(), _head(), page(), What search engines and link previews see: the React app's index.html with the… (+4 more)

### Community 32 - "fees/views.py"
Cohesion: 0.09
Nodes (37): client_ip(), Installment, A point in the session when fees fall due, e.g. Quarter 1 due 10 April., ConcessionSerializer, DecisionSerializer, FeeAmountBulkSerializer, FeeAmountRowSerializer, FeeAmountSerializer (+29 more)

### Community 33 - "campaign.service.ts"
Cohesion: 0.14
Nodes (15): getCampaign(), Campaign, campaignSchema, ICampaign, ICampaignButton, ICampaignSliderItem, CampaignLog, campaignLogSchema (+7 more)

### Community 34 - "as_api_errors"
Cohesion: 0.11
Nodes (16): as_api_errors(), Turn validation errors raised by the services into 400 responses., ApproveUpiSerializer, ReasonSerializer, UpiSubmissionSerializer, ConcessionViewSet, PaymentViewSet, action (+8 more)

### Community 35 - "sidebar.tsx"
Cohesion: 0.07
Nodes (32): Separator, Sidebar, SidebarContent, SidebarContext, SidebarFooter, SidebarGroup, SidebarGroupAction, SidebarGroupContent (+24 more)

### Community 36 - "App.tsx"
Cohesion: 0.06
Nodes (49): queryClient, StaffHome(), TimetableGrid(), TabsContent, TabsList, TabsTrigger, ALL, sectionLabel() (+41 more)

### Community 37 - "auth.controller.ts"
Cohesion: 0.09
Nodes (22): jsonwebtoken, changePassword(), COOKIE_OPTIONS, getAICreditStatus(), login(), logout(), register(), updateAISettings() (+14 more)

### Community 38 - "Enrollment"
Cohesion: 0.09
Nodes (31): Enrollment, A student's place in a section for one session., Status, _backups(), dashboard(), DashboardSerializer, api_view, extend_schema (+23 more)

### Community 39 - "chat.service.ts"
Cohesion: 0.09
Nodes (27): deleteMessage(), getChat(), getChats(), markRead(), listLeads(), deleteContact(), getContact(), getContacts() (+19 more)

### Community 40 - "ISafeModeStore"
Cohesion: 0.12
Nodes (4): SafeModeManager, ISafeModeStore, wrapBaileysSocket(), main()

### Community 41 - "AuditLog"
Cohesion: 0.09
Nodes (26): AuditLog, GalleryPhoto, Meta, A photo of school life, shown to everyone on the website's gallery., Append-only record of who did what to student data., AuditLogSerializer, GalleryPhotoSerializer, Meta (+18 more)

### Community 42 - "dependencies"
Cohesion: 0.07
Nodes (30): dependencies, bcryptjs, compression, cookie-parser, cors, dotenv, express, express-mongo-sanitize (+22 more)

### Community 43 - "fees/services.py"
Cohesion: 0.08
Nodes (41): Write an audit entry for `obj`. `request` may be None for system actions., record(), Remind parents about fees due soon or overdue. Run daily, e.g. from cron: 0 9 *…, Concession, InvoiceLine, Kind, Meta, A parent's report that they paid by scanning the school's UPI QR code. Nothing… (+33 more)

### Community 44 - "openai-assistant.service.ts"
Cohesion: 0.21
Nodes (15): AITrainingMessage, schema, aiConversationMemory, AIRoute, checkOpenAICreditAvailability(), CloudProvider, generateChatReply(), getChatReplyMode() (+7 more)

### Community 45 - "PrivateStorage"
Cohesion: 0.33
Nodes (3): PrivateStorage, Reads PRIVATE_MEDIA_ROOT on every use, so it always follows the current…, FileSystemStorage

### Community 46 - "OutgoingMessage"
Cohesion: 0.14
Nodes (30): Kind, Meta, OutgoingMessage, One WhatsApp message: queued by `core.notify`, sent by the `send_whatsapp`…, Status, Send what is due, within the per-minute limit. Returns how many were sent., send_due(), _alerts() (+22 more)

### Community 47 - "toast.tsx"
Cohesion: 0.22
Nodes (12): Toast, ToastAction, ToastActionElement, ToastClose, ToastDescription, ToastProps, ToastTitle, toastVariants (+4 more)

### Community 48 - "form.tsx"
Cohesion: 0.17
Nodes (14): FormControl, FormDescription, FormFieldContext, FormFieldContextValue, FormItem, FormItemContext, FormItemContextValue, FormLabel (+6 more)

### Community 50 - "lucide-react"
Cohesion: 0.09
Nodes (18): AccordionContent, AccordionItem, AccordionTrigger, Checkbox, InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot (+10 more)

### Community 51 - "as_user"
Cohesion: 0.12
Nodes (19): create_test(), test_marks_above_maximum_are_refused(), test_subject_teacher_enters_and_publishes_marks(), test_teacher_cannot_create_tests_for_subjects_they_do_not_teach(), test_teachers_only_see_their_own_subjects(), as_user(), test_class_result_sheet(), test_class_teacher_writes_remarks_but_subject_teacher_cannot() (+11 more)

### Community 52 - "message.service.ts"
Cohesion: 0.15
Nodes (24): @whiskeysockets/baileys, Chat, chatSchema, IChat, contactSchema, IContact, fetchBuffer(), getConnectedSocket() (+16 more)

### Community 53 - "pagination.tsx"
Cohesion: 0.09
Nodes (22): AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter(), AlertDialogHeader(), AlertDialogOverlay, AlertDialogTitle (+14 more)

### Community 54 - "reminder.service.ts"
Cohesion: 0.18
Nodes (22): createReminderFromMessage(), createSendMessage(), deliveryJid(), directPhoneContact(), findContacts(), flexibleSend(), handleReminderCommand(), isDuplicateSourceMessage() (+14 more)

### Community 55 - "Student"
Cohesion: 0.21
Nodes (19): Status, Student, admin(), jpeg(), photo_zip(), fixture, row(), sheet() (+11 more)

### Community 56 - "devDependencies"
Cohesion: 0.08
Nodes (24): devDependencies, eslint, jest, prettier, ts-jest, ts-node, ts-node-dev, @types/bcryptjs (+16 more)

### Community 58 - "AttendanceRecord"
Cohesion: 0.12
Nodes (20): AttendanceRecordAdmin, register, AttendanceRecord, Meta, One student's attendance for one school day, marked by the class teacher., Status, AttendanceMarkSerializer, AttendanceRowSerializer (+12 more)

### Community 59 - "core/models.py"
Cohesion: 0.14
Nodes (19): _d(), Transfer certificate PDF. PLACEHOLDER layout until the school gives its…, tc_pdf(), A CAPTCHA challenge or pass that has been used, so it cannot be used again., UsedCaptcha, draw_logo(), draw_report_card(), grid_row() (+11 more)

### Community 60 - "attendance/tests.py"
Cohesion: 0.53
Nodes (8): payload(), school_day(), test_class_teacher_marks_and_corrects_attendance(), test_future_dates_and_old_dates_are_refused_for_teachers(), test_month_summary(), test_students_from_other_sections_are_refused(), test_subject_teacher_can_view_but_not_mark(), test_teacher_of_another_class_cannot_see_the_register()

### Community 61 - "messaging/views.py"
Cohesion: 0.16
Nodes (11): OptOut, A number that asked not to get WhatsApp alerts. Sign-in codes the parent asks…, Meta, OptOutSerializer, OutgoingMessageSerializer, QrSerializer, WhatsAppStatusSerializer, OptOutViewSet (+3 more)

### Community 62 - "HeroScene.tsx"
Cohesion: 0.16
Nodes (18): canRun3D(), Hero3D(), HeroFallback(), HeroScene, apple(), beachBall(), blockFace(), book() (+10 more)

### Community 63 - "safemode/index.ts"
Cohesion: 0.17
Nodes (20): createSafeModeRouter(), safeModeErrorHandler(), SafeModeErrorCode, defaultState(), PhoneState, todayUtc(), computeNextTier(), getTierConfig() (+12 more)

### Community 64 - "conftest.py"
Cohesion: 0.13
Nodes (19): AbstractUser, application_data(), client_for(), _client(), _isolated(), make_user(), public(), fixture (+11 more)

### Community 65 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+12 more)

### Community 66 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, declaration, declarationMap, emitDecoratorMetadata, esModuleInterop, experimentalDecorators, forceConsistentCasingInFileNames, lib (+12 more)

### Community 67 - "templates.py"
Cohesion: 0.21
Nodes (19): _about(), admission_status_changed(), admission_submitted(), attendance_absent(), _date(), fee_payment_received(), fee_reminder(), fee_upi_rejected() (+11 more)

### Community 68 - "portal/tests.py"
Cohesion: 0.10
Nodes (22): AssessmentAdmin, MarkInline, register, Assessment, Mark, Meta, A test or exam in one subject for one section, e.g. Unit Test 1 in Class 3 A…, marked() (+14 more)

### Community 69 - "command.tsx"
Cohesion: 0.11
Nodes (17): Command, CommandDialogProps, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator (+9 more)

### Community 70 - "api.ts"
Cohesion: 0.08
Nodes (25): describeError(), onSignedOut(), readRefresh(), refreshAccess(), request(), RequestOptions, send(), tokens (+17 more)

### Community 71 - "send.controller.ts"
Cohesion: 0.15
Nodes (19): multer, uuid, fileFilter(), sendAudio(), sendButton(), sendDocument(), sendImage(), sendSlider() (+11 more)

### Community 72 - "fees/admin.py"
Cohesion: 0.16
Nodes (13): ConcessionAdmin, FeeAmountInline, FeeHeadAdmin, InstallmentAdmin, InvoiceAdmin, LineInline, PaymentAdmin, PaymentInline (+5 more)

### Community 73 - "apikey.controller.ts"
Cohesion: 0.13
Nodes (15): @hapi/boom, createApiKey(), deleteApiKey(), deleteSession(), logout(), reconnect(), ApiKey, apiKeySchema (+7 more)

### Community 74 - "outbox.py"
Cohesion: 0.15
Nodes (17): due_messages(), expire_stale(), _failed(), in_quiet_hours(), queue(), Queue and send WhatsApp messages. `queue()` is called by `core.notify` inside…, Staff asked to send a failed message again., Turn a notify() event into queued messages. Returns the rows created. (+9 more)

### Community 75 - "devDependencies"
Cohesion: 0.11
Nodes (18): devDependencies, autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, postcss (+10 more)

### Community 76 - "ExamTermViewSet"
Cohesion: 0.18
Nodes (11): ResultSheetSerializer, SaveRemarksSerializer, can_edit_remarks(), ExamTermViewSet, action, extend_schema, The class teacher saves remarks and co-scholastic grades., Report cards as one PDF: the whole section, or one student with ?student=. (+3 more)

### Community 77 - "components.json"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, rsc, $schema (+8 more)

### Community 78 - "compilerOptions"
Cohesion: 0.12
Nodes (15): compilerOptions, allowImportingTsExtensions, isolatedModules, lib, module, moduleDetection, moduleResolution, noEmit (+7 more)

### Community 79 - "report.py"
Cohesion: 0.18
Nodes (16): bands(), grade_for(), percent(), The grading scale and co-scholastic areas. The setup wizard lets a school pick…, Return (grade, is_pass) for a percentage, or ("", None) when there is nothing…, build(), enrollment_for(), _guardian_names() (+8 more)

### Community 80 - "Message.ts"
Cohesion: 0.20
Nodes (13): IMessage, Message, messageSchema, MessageStatus, MessageType, basicReply(), generateLocalLearnedReply(), normalize() (+5 more)

### Community 81 - "whatsapp.py"
Cohesion: 0.15
Nodes (19): summary(), test_http_client_talks_to_the_blastup_api(), api_view, extend_schema, permission_classes, qr_view(), Is the school's WhatsApp number connected, and how is the queue doing., QR code to link the school's phone (WhatsApp > Linked devices). (+11 more)

### Community 82 - "carousel.tsx"
Cohesion: 0.17
Nodes (14): Carousel, CarouselApi, CarouselContent, CarouselContext, CarouselContextProps, CarouselItem, CarouselNext, CarouselOptions (+6 more)

### Community 83 - "captcha.py"
Cohesion: 0.26
Nodes (11): _answer_hash(), enabled(), new_challenge(), _picture(), A self-hosted picture CAPTCHA for the public forms. No outside service, no…, True the first time a nonce is seen; False on a replay., Checks the typed letters. Returns a pass token, or None. A challenge can be…, Call at the top of a public form's POST. Raises a 400 unless the form carries a… (+3 more)

### Community 84 - "whatsapp-report.service.ts"
Cohesion: 0.18
Nodes (15): DeliveryStatus, historyEntrySchema, IReminder, Reminder, ReminderActionType, reminderSchema, ReminderStatus, campaignReport() (+7 more)

### Community 85 - "test_setup_wizard.py"
Cohesion: 0.23
Nodes (10): answer(), fixture, deploy/setup_wizard.py, the server settings wizard (plain Python, loaded from…, repo(), test_dry_run_as_root_only_shows_commands(), test_first_run_writes_settings(), test_not_saving_changes_nothing(), test_running_again_keeps_secrets_and_other_settings() (+2 more)

### Community 86 - "parent_login.py"
Cohesion: 0.14
Nodes (19): register, UserAdmin, LoginCode, Meta, A one-time 6-digit code for a parent to sign in with their mobile number. Only…, Source, children_for_phone(), has_children() (+11 more)

### Community 87 - "whatsapp-builder.service.ts"
Cohesion: 0.27
Nodes (12): createCampaign(), CampaignDraft, campaigns, FlowDraft, flows, handleCampaign(), handleFlow(), handleWhatsAppBuilderCommand() (+4 more)

### Community 88 - "test_captcha.py"
Cohesion: 0.18
Nodes (6): fixture, Pictures come back as their plain letters, so the test can 'read' them., readable(), solve(), test_application_needs_a_pass_used_once(), test_switching_it_off()

### Community 89 - "admissions/models.py"
Cohesion: 0.09
Nodes (25): Migration, get_private_storage(), Private file storage for student documents and photos. Files live under…, GuardianAdmin, register, StudentAdmin, StudentGuardianInline, An .xlsx sample with this school's classes: a Students sheet, Instructions and… (+17 more)

### Community 90 - "chart.tsx"
Cohesion: 0.23
Nodes (10): ChartConfig, ChartContainer, ChartContext, ChartContextProps, ChartLegendContent, ChartTooltipContent, getPayloadConfigFromPayload(), THEMES (+2 more)

### Community 91 - "compilerOptions"
Cohesion: 0.17
Nodes (11): compilerOptions, allowJs, baseUrl, noImplicitAny, noUnusedLocals, noUnusedParameters, paths, skipLibCheck (+3 more)

### Community 92 - "Blastup WhatsApp server (kalpintelligence/Blastup)"
Cohesion: 0.22
Nodes (11): mongo service (mongo:7), redis service (redis:7-alpine), whatsapp service (Blastup server), lkms-whatsapp-sender service, Baileys unofficial WhatsApp Web ban risk, Django messaging module with queue (adapter), WhatsApp opt-outs, WhatsApp safety limits (rate, quiet hours, daily cap) (+3 more)

### Community 93 - "VPS deployment guide (Ubuntu 24.04)"
Cohesion: 0.22
Nodes (11): Private document storage, manage.py backup, lkms-backup.timer (nightly 02:30), Encrypted off-site copy (rclone crypt), manage.py restore_backup, Backup retention (daily/weekly/monthly), Read-only GitHub deploy key, Gunicorn lkms-web service (+3 more)

### Community 94 - "students/tests.py"
Cohesion: 0.17
Nodes (3): fixture, student(), test_viewing_a_student_is_audited_and_aadhaar_masked()

### Community 95 - "SchoolProfileSerializer"
Cohesion: 0.25
Nodes (3): The school's settings. Pictures are sent as files; `remove_logo` /…, SchoolProfileSerializer, SchoolProfileView

### Community 96 - "StudentImportView"
Cohesion: 0.20
Nodes (7): _json_list(), APIView, Photos for students already in LKMS, named by admission number (0101.jpg).…, The browser sends the names of the photos it holds as a JSON list., Bulk import from the sample sheet. POST with commit=false checks only;…, StudentImportView, StudentPhotoImportView

### Community 97 - "widget.js"
Cohesion: 0.24
Nodes (3): addMessage(), buildLeadForm(), setOpen()

### Community 98 - "AuditLogAdmin"
Cohesion: 0.25
Nodes (3): AuditLogAdmin, register, SchoolProfileAdmin

### Community 99 - "LKMS school management system"
Cohesion: 0.28
Nodes (9): postgres service (postgres:16), LKMS build plan (5 phases), Session-Class-Section-Enrollment data model, Per-school isolated installation, Frontend SPA HTML shell (root + main.tsx), acharya base repository (frankmathewsajan/acharya), Django + DRF backend, LKMS school management system (+1 more)

### Community 100 - "UPI QR payment with staff verification"
Cohesion: 0.22
Nodes (9): Acharya Multi-School Management System, Category-Based Fee Management, Multi-School Admission Workflow, Role-Based Dashboards, lkms-fee-reminders.timer (10:00 daily), Signed pay link (/pay/<token>), send_fee_reminders command, UPI QR payment with staff verification (+1 more)

### Community 101 - "Invoice and receipt numbering"
Cohesion: 0.22
Nodes (9): TC number format, Transfer certificate (TC), Concession, Fee head, Installment, Invoice and receipt numbering, Role permissions (core/permissions.py), Principal/admin dashboard (+1 more)

### Community 102 - "navigation-menu.tsx"
Cohesion: 0.13
Nodes (16): NavigationMenu, NavigationMenuContent, NavigationMenuIndicator, NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle, NavigationMenuViewport, ToggleGroup (+8 more)

### Community 103 - "sheet.tsx"
Cohesion: 0.25
Nodes (8): SheetContent, SheetContentProps, SheetDescription, SheetFooter(), SheetHeader(), SheetOverlay, SheetTitle, sheetVariants

### Community 104 - "WhatsApp alerts"
Cohesion: 0.29
Nodes (8): JWT Authentication, School-wide CSV reports, Daily attendance register, Notices, Parent mobile OTP sign-in, Teacher portal (My classes), Timetable and bell times, WhatsApp alerts

### Community 105 - "Admission workflow (submitted to admitted)"
Cohesion: 0.32
Nodes (8): Aadhaar masking, Admission (S.R.) number, Admission workflow (submitted to admitted), Audit log, Hidden website honeypot field, Public admissions API (apply/track/documents), Bulk student import (import_students), Sample .xlsx template

### Community 106 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, format, lint, seed, start, test

### Community 107 - "campaign.controller.ts"
Cohesion: 0.67
Nodes (5): createCampaign(), deleteCampaign(), getCampaignLogs(), listCampaigns(), reCampaign()

### Community 108 - "breadcrumb.tsx"
Cohesion: 0.22
Nodes (8): Breadcrumb, BreadcrumbEllipsis(), BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator(), @radix-ui/react-slot

### Community 109 - "Board/school format checklist"
Cohesion: 0.38
Nodes (7): Board/school format checklist, Co-scholastic areas (CO_SCHOLASTIC_AREAS), Grade scale placeholder, RBSE / Shala Darpan (Rajasthan board), Exam term, Report card, Tests and marks

### Community 110 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, build:dev, dev, lint, preview, typecheck

### Community 111 - "drawer.tsx"
Cohesion: 0.22
Nodes (7): DrawerContent, DrawerDescription, DrawerFooter(), DrawerHeader(), DrawerOverlay, DrawerTitle, vaul

### Community 112 - "send_whatsapp.py"
Cohesion: 0.33
Nodes (3): Command, BaseCommand, Deliver queued WhatsApp messages. Run it as a service on the server: python…

### Community 113 - "certificates/tests.py"
Cohesion: 0.48
Nodes (6): request_tc(), test_office_can_withdraw_a_request_but_not_an_issued_tc(), test_office_requests_and_principal_issues(), test_one_tc_per_student_and_cancelling_restores_the_student(), test_teachers_and_accountants_cannot_see_tcs(), test_unpaid_fees_block_the_tc_unless_the_principal_gives_a_reason()

### Community 115 - "Setup wizard (deploy/setup_wizard.py)"
Cohesion: 0.70
Nodes (5): Answers file (school.json), manage.py setup_school, Setup wizard (deploy/setup_wizard.py), Green Valley sample CBSE school answers, Lotus Kids School answers

### Community 117 - "manage.py"
Cohesion: 0.50
Nodes (3): main(), Django's command-line utility for administrative tasks., Run administrative tasks.

### Community 118 - "messaging/admin.py"
Cohesion: 0.67
Nodes (3): OptOutAdmin, OutgoingMessageAdmin, register

### Community 119 - "wa"
Cohesion: 0.50
Nodes (3): fixture, WhatsApp switched on, with a fake sender that records what it was asked to send., wa()

### Community 120 - "RandomPath"
Cohesion: 0.33
Nodes (3): RandomPath, upload_to callable that keeps only a random name and the detected extension., deconstructible

### Community 134 - "Lotus Kids School Fee UPI QR Code (example)"
Cohesion: 1.00
Nodes (3): Lotus Kids School Fee UPI QR Code (example), Lotus Kids Education Society (UPI merchant), UPI Scan & Pay Fee Payment

### Community 137 - "0004_school_branding_and_payments.py"
Cohesion: 0.50
Nodes (3): carry_over(), Migration, Installs made before this version: keep the board and the UPI account from…

### Community 165 - "scroll-area.tsx"
Cohesion: 0.50
Nodes (3): ScrollArea, ScrollBar, @radix-ui/react-scroll-area

## Knowledge Gaps
- **533 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Status` (+528 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1153 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SchoolProfile` connect `SchoolProfile` to `AcademicSession`, `exams/views.py`, `django_db`, `Command`, `setup_school.py`, `users/views.py`, `Invoice`, `bulk_import.py`, `AdmissionApplication`, `fees/views.py`, `AuditLog`, `fees/services.py`, `Student`, `core/models.py`, `templates.py`, `captcha.py`, `test_captcha.py`, `admissions/models.py`, `students/tests.py`, `SchoolProfileSerializer`, `AuditLogAdmin`, `RandomPath`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `Student` connect `Student` to `conftest.py`, `AcademicSession`, `exams/views.py`, `certificates/services.py`, `setup_school.py`, `ExamTermViewSet`, `assessments/views.py`, `admissions/tests.py`, `certificates/tests.py`, `parent_login.py`, `RandomPath`, `admissions/models.py`, `Invoice`, `core/models.py`, `bulk_import.py`, `AdmissionApplication`, `SchoolProfile`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `WhatsApp alerts` connect `WhatsApp alerts` to `templates.py`, `UPI QR payment with staff verification`, `Invoice and receipt numbering`, `LKMS school management system`, `Board/school format checklist`, `Blastup WhatsApp server (kalpintelligence/Blastup)`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Are the 40 inferred relationships involving `SchoolProfile` (e.g. with `AdmissionApplication` and `admit()`) actually correct?**
  _`SchoolProfile` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `Enrollment` (e.g. with `EnrollmentSerializer` and `my_sections()`) actually correct?**
  _`Enrollment` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Migration`, `Migration`, `Migration` to the rest of the system?**
  _533 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `lib/types.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.05357142857142857 - nodes in this community are weakly interconnected._