## Patient Features — Mobile (Expo) + Backend (FastAPI)

### 1. Authentication
| Mobile Screen | Backend Endpoint |
|---|---|
| `(auth)/signup.tsx` | `POST /v1/auth/signup` |
| `(auth)/login.tsx` | `POST /v1/auth/login` |
| `(auth)/verify-otp.tsx` | `POST /v1/auth/send-otp`, `POST /v1/auth/verify-otp` |
| `(auth)/forgot-password.tsx` | `POST /v1/auth/forgot-password` |
| `(auth)/reset-password.tsx` | `POST /v1/auth/reset-password` |
| — | `POST /v1/auth/refresh` (token refresh) |
| — | `POST /v1/auth/google` (Google sign-in) |
| — | `GET /v1/auth/config` (auth config flags) |

### 2. Onboarding
| Mobile Screen | Backend Endpoint |
|---|---|
| `(onboarding)/welcome.tsx` | — (local) |
| `(onboarding)/conditions.tsx` | — (health condition selection) |
| `(onboarding)/intake-form.tsx` | — (medical intake questionnaire) |
| `(onboarding)/consent.tsx` | `POST /v1/users/me/consent` |
| `(onboarding)/health-sync.tsx` | HealthKit/Health Connect permissions |
| `(onboarding)/abha-link.tsx` | `POST /v1/clinic/patient/abha/link`, `/abha/create/init`, `/abha/create/confirm` |

### 3. Home Dashboard
| Mobile Screen | Backend Endpoint |
|---|---|
| `(tabs)/home.tsx` | `GET /v1/users/me`, `GET /v1/clinic/patient/notes` |
| Quick actions: Consult, Reminders, Reports, Notes | — (navigation only) |

### 4. Consultations & Video
| Mobile Screen | Backend Endpoint |
|---|---|
| `(tabs)/consultations.tsx` | `GET /v1/clinic/patient/consultations` (list, filter by status/upcoming) |
| `consultations/[id].tsx` | `GET /v1/clinic/patient/consultations/{id}` |
| `consultations/book.tsx` | `GET /v1/clinic/patient/consultations/slots`, `GET /v1/clinic/patient/doctors/available`, `POST /v1/clinic/patient/consultations` |
| — | `POST /v1/clinic/patient/consultations/{id}/confirm-payment` |
| — | `POST /v1/clinic/patient/consultations/{id}/cancel` |
| `consultations/join/[id].tsx` | `GET /v1/clinic/patient/consultations/{id}/join` (100ms video token) |
| — | `POST /v1/clinic/patient/consultations/{id}/record-consent` |
| `consultations/pre-consult-report.tsx` | `GET /v1/clinic/patient/consultations/{id}/pre-consult-report` |

### 5. Payments
| Mobile Screen | Backend Endpoint |
|---|---|
| Embedded in booking flow | `POST /v1/payments/order` (Razorpay order) |
| — | `POST /v1/payments/verify` (verify + capture) |
| — | `GET /v1/payments/{id}` |

### 6. Lab Reports & OCR
| Mobile Screen | Backend Endpoint |
|---|---|
| `(tabs)/reports.tsx` | `GET /v1/clinic/patient/lab-reports` (paginated list) |
| `reports/[id].tsx` | `GET /v1/clinic/patient/lab-reports/{id}` |
| `reports/upload.tsx` | `POST /v1/clinic/patient/lab-reports/initiate-upload` → S3 direct upload → `POST /v1/clinic/patient/lab-reports/{id}/finalize` |
| — | `PATCH /v1/clinic/patient/lab-reports/{id}` (OCR correction) |
| — | `GET /v1/clinic/patient/lab-reports/{id}/download` (presigned URL) |

### 7. Biomarker Trends
| Mobile Screen | Backend Endpoint |
|---|---|
| `biomarkers/[name].tsx` | `GET /v1/clinic/patient/biomarker-trends/{biomarker}` (trend data with time range) |
| `biomarkers/[name].web.tsx` | `GET /v1/clinic/patient/biomarkers` (list all tracked biomarkers) |
| `insights.tsx` | Aggregates biomarker summaries |

### 8. Prescriptions
| Mobile Screen | Backend Endpoint |
|---|---|
| `prescriptions/index.tsx` | `GET /v1/clinic/patient/prescriptions` (signed/dispensed only) |
| `prescriptions/[id].tsx` | `GET /v1/clinic/patient/prescriptions/{id}` |
| — | `GET /v1/clinic/patient/prescriptions/{id}/pdf` (presigned PDF URL) |

### 9. Health Reminders & Adherence
| Mobile Screen | Backend Endpoint |
|---|---|
| `(tabs)/reminders.tsx` | `GET /v1/wellness/reminders` (with adherence rates) |
| — | `POST /v1/wellness/reminders` (create) |
| — | `PATCH /v1/wellness/reminders/{id}` (update) |
| — | `DELETE /v1/wellness/reminders/{id}` |
| — | `POST /v1/wellness/reminders/{id}/log` (taken/skipped/snoozed) |

### 10. Health Data Sync
| Mobile Screen | Backend Endpoint |
|---|---|
| `(onboarding)/health-sync.tsx` | `POST /v1/wellness/health-sync` (HealthKit/Health Connect → backend) |
| Background sync every 4h | Same endpoint, idempotent on source record ID |

### 11. Patient Notes
| Mobile Screen | Backend Endpoint |
|---|---|
| `notes/index.tsx` | `GET /v1/clinic/patient/notes` (paginated) |
| — | `POST /v1/clinic/patient/notes` (create) |
| — | `PATCH /v1/clinic/patient/notes/{id}` (edit) |
| — | `DELETE /v1/clinic/patient/notes/{id}` (soft-delete) |

### 12. Education Content
| Mobile Screen | Backend Endpoint |
|---|---|
| `education/index.tsx` | `GET /v1/clinic/patient/education` (assignments + library) |
| `education/[id].tsx` | `GET /v1/clinic/patient/education/{id}` |
| — | `POST /v1/clinic/patient/education/{id}/read` (mark read) |

### 13. Notifications
| Mobile Screen | Backend Endpoint |
|---|---|
| `(tabs)/notifications.tsx` | `GET /v1/users/notifications` (paginated, unread filter) |
| — | `PATCH /v1/users/notifications/{id}/read` |
| — | `POST /v1/users/notifications/read-all` |
| `notification-preferences.tsx` | `GET /v1/users/notification-preferences` |
| — | `PATCH /v1/users/notification-preferences` (push/email/WhatsApp toggles) |

### 14. Profile & Account
| Mobile Screen | Backend Endpoint |
|---|---|
| `(tabs)/profile.tsx` | `GET /v1/users/me` |
| — | `PUT /v1/users/me/push-token` (Expo push registration) |
| — | `GET /v1/users/me/consents` (consent history) |
| `privacy-security.tsx` | — (settings UI) |
| `download-data.tsx` | `POST /v1/users/me/data-export` (DSAR) |
| `delete-account.tsx` | `POST /v1/users/me/delete` (30-day legal hold) |

### 15. ABHA Digital Health ID
| Mobile Screen | Backend Endpoint |
|---|---|
| `abha-settings.tsx` | `GET /v1/clinic/patient/abha` (status check) |
| — | `POST /v1/clinic/patient/abha/link` |
| — | `POST /v1/clinic/patient/abha/create/init` (Aadhaar OTP) |
| — | `POST /v1/clinic/patient/abha/create/confirm` |

---

### Summary: 6 tabs, 15 feature modules, 55 backend endpoints

**Tab bar:** Home | Consultations | Reports | Reminders | Notifications | Profile

**Shared UI components:** GlassCard, GlassTabBar, AmbientBackground, HapticPressable, AnimatedPressable, Skeleton, EmptyState, ErrorBoundary, OfflineBanner, PrivacyShield, CaptureGuard, GoogleSignInButton, DragDropUpload (web), PrintButton (web), WebSidebar (web)




---

## Planned Patient Features — Gap Analysis

### Build Now (Priority 1)

#### 1. Appointment Rescheduling
Already in `build-spec.md` as a planned endpoint — never implemented.
```http
POST /v1/clinic/patient/consultations/{id}/reschedule
```
Screen: update `consultations/[id].tsx` with reschedule action.

#### 5. Refund Tracking
Razorpay `initiate_refund()` already exists in backend. Patient needs visibility.
```http
GET /v1/payments/refunds
GET /v1/payments/refunds/{id}
```

#### 6. Device Session Management
Security rule #18 (refresh token rotation with reuse detection) exists but no patient UI to view/revoke.
```http
GET  /v1/users/me/sessions
DELETE /v1/users/me/sessions/{id}
```

#### 14. Consent Withdrawal
DPDP Act requires withdrawal capability. `consent.py` has no withdraw function — compliance gap.
```http
POST /v1/users/me/consent/withdraw
```

#### 15. Data Export Status
Currently fire-and-forget. Celery task and S3 key logic exist but patient can't check progress.
```http
GET /v1/users/me/data-exports
GET /v1/users/me/data-exports/{id}
```

### Build Next (Priority 2)

#### 7. Emergency Contact
Already exists as JSONB column on `kc_patients`. Just needs API endpoints — no migration needed.
```http
GET   /v1/users/me/emergency-contacts
POST  /v1/users/me/emergency-contacts
PATCH /v1/users/me/emergency-contacts/{id}
```

#### 9. Vitals Logging (Manual Entry)
Overlaps with Health Data Sync. Route through `wn_health_datapoints` with `source='manual'`.
```http
GET  /v1/wellness/vitals
POST /v1/wellness/vitals
```
Covers: weight, blood pressure, blood glucose, waist circumference.

#### 11. Care Plans (Patient Read-Only)
Doctor assigns medication/exercise/diet plans. Patient views only. Needs doctor-side endpoints too.
```http
GET /v1/clinic/patient/care-plans
GET /v1/clinic/patient/care-plans/{id}
```

#### 13. Audit History Visibility
Filter `ad_audit_log` for patient's own actions. Read-only, PHI stripped from metadata.
```http
GET /v1/users/me/activity
```

### Evaluate / Phase 2

#### 2. Consultation Chat
Big feature — needs WebSocket/polling, message storage, attachments, moderation. Consider starting with consultation-linked patient notes visible to doctor. Full chat is Phase 2+.
```http
GET  /v1/clinic/patient/consultations/{id}/messages
POST /v1/clinic/patient/consultations/{id}/messages
POST /v1/clinic/patient/consultations/{id}/attachments
```
Screen: `consultations/chat/[id].tsx`

#### 4. Medical Documents Vault
Lab report upload already handles PDFs/images. Could reuse infra with `document_type` discriminator instead of new module.
```http
GET  /v1/clinic/patient/documents
POST /v1/clinic/patient/documents
```

#### 8. Symptom Tracker
Relevant for PCOS/thyroid but needs clinical validation on symptoms/scales. Build after care plans.
```http
GET  /v1/wellness/symptoms
POST /v1/wellness/symptoms
```
Examples: fatigue, headache, sleep quality, mood, bloating.

#### 10. Goal Tracking
Low clinical value unless tied to care plans and doctor review.
```http
GET  /v1/wellness/goals
POST /v1/wellness/goals
```

#### 12. Offline Support
Client-side architecture (TanStack Query persistence, queue-and-sync). Not a backend feature. Scope separately as mobile infrastructure task.



Here's what's been completed across the previous session — 8 patient features, all committed on dev:

┌─────┬─────────────────┬──────────────────────────────────────────────────┬──────────────────────────────────┬─────────┐
│  #  │     Feature     │                     Backend                      │              Mobile              │ Commit  │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│     │ Appointment     │ POST /consultations/{id}/reschedule + service    │ Reschedule panel in              │         │
│ 1   │ rescheduling    │ with 24h window, same-doctor constraint, slot    │ consultations/[id].tsx with slot │ 472e3bf │
│     │                 │ swap                                             │  picker                          │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│ 2   │ Refund tracking │ kc_refunds table (migration 0004), GET /refunds  │ payments.tsx — refund list with  │ 472e3bf │
│     │                 │ + GET /refunds/{id}, Razorpay data capture       │ status pills                     │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│ 3   │ Device session  │ GET/DELETE /me/sessions, session family collapse │ sessions.tsx — list + revoke     │ 8f92435 │
│     │ management      │                                                  │                                  │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│     │ Consent         │                                                  │ Withdraw button on               │         │
│ 4   │ withdrawal      │ POST /me/consent/withdraw                        │ privacy-security.tsx             │ 2c1b4ce │
│     │ (DPDP)          │                                                  │                                  │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│ 5   │ Data export     │ GET /me/data-exports + GET /me/data-exports/{id} │ "Your requests" section in       │ b1e3045 │
│     │ status          │                                                  │ download-data.tsx                │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│ 6   │ Emergency       │ GET/PUT /me/emergency-contact                    │ emergency-contact.tsx — form     │ 36b0413 │
│     │ contact         │                                                  │ with NeumorphInput               │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│ 7   │ Manual vitals   │ POST/GET /v1/wellness/vitals, reuses             │ vitals.tsx — log form + recent   │ cc6b30c │
│     │ logging         │ wn_health_datapoints                             │ readings                         │         │
├─────┼─────────────────┼──────────────────────────────────────────────────┼──────────────────────────────────┼─────────┤
│     │ Account         │                                                  │ activity.tsx — feed with         │         │
│ 8   │ activity        │ GET /me/activity with friendly descriptions      │ green/red dots                   │ 44f53dd │
│     │ history         │                                                  │                                  │         │
└─────┴─────────────────┴──────────────────────────────────────────────────┴──────────────────────────────────┴─────────┘

Each feature includes: tests, RBAC matrix entries, cross-user 404, audit logging. All byte-compile and tsc clean.

Still pending:
- Feature 11 — Care Plans (full vertical: table + migration + doctor API + patient API + doctor-portal UI + mobile UI) — you chose this as the next one to build
- Running all migrations (make migrate)
- Running tests (make test)

Want me to continue with Care Plans?



Both follow-ups are complete and consistent. Summary:

1) Admin patient typeahead search (replaced the 200-row dropdown)

- admin_repo.search_patients(query, ...) — matches patient name or Kyros ID substring (capped at 20).
- GET /admin/consultations/patient-search t (admin/_patient_options.html).
- The on-demand form's patient field is now an HTMX typeahead (hx-trigger="input changed delay:300ms") that
populates the select. The old list_patient

2) Staff "Join" support seats

- livekit_video.generate_staff_token(room_th a visible role identity("coordinator"/"admin"), publish+subscribe but no moderation/recording rights (only doctors get those).
- Coordinator GET /coord/scheduling/{id}/j patients (miss → audited 404, noenumeration), ensures the room is provisioned, mints the token.
- Admin GET /admin/consultations/{id}/join ensures the room.
- Join pages coord/video_room.html + admin/video_room.html (separate per the no-shared-template rule) load the LiveKit web SDK and connect.
- "Join" buttons added to both upcoming-consultations lists, shown only for CONFIRMED/IN_PROGRESS; not_joinable
alert bars added.
- Test for the staff-token identity; dev-to-prod row added for the SDK.

Two things you should weigh

- Compliance (flagged, not assumed): a coordinator/admin in a live clinical call is the "support seat" the room
cap was designed for, and I made it visiblhe doctor as room admin sees everyparticipant). Before production use, confirm the patient/doctor are aware of/consent to a support participant, per
telemedicine norms. I deliberately did not
- SDK vendoring: the Jinja portals have no WebRTC client, so the join page needs livekit-client.umd.min.js
vendored to {admin,coord}/static/vendor/ (in-ui rule). Added to the dev-to-prodchecklist. Until it's dropped in, the join page shows "video client unavailable" — the backend (token, scoping,
audit, room provisioning) is fully wired a

Verification

Python syntax + Jinja template parsing pasn't run pytest/ruff/mypy or a browser here(no Docker) — please run make test && make ruff && make mypy, and note the JS join page itself is unverified
end-to-end (it's standard LiveKit client cit). Migrations 0010 + 0011 still needapplying before boot.

Added the LiveKit web SDK vendoring to the dev-to-prod checklist — you'll need a production value (the bundled SDK file) before go-live.