# Mobile API Documentation

**Base URL (local):** `http://localhost:8000`
**Interactive docs (Swagger UI):** `http://localhost:8000/docs`
**OpenAPI schema:** `http://localhost:8000/openapi.json`

هذا الـ API طبقة HTTP رقيقة فوق نفس الـ features الموجودة في المشروع
(`question_bank`, `knowledge_graph`, `rag`, `assessment`) — بيغطي سيناريوهين:

1. **Admin flow**: رفع كتاب PDF مع `grade`/`subject` → يشتغل تلقائيًا Knowledge Graph
   ثم RAG indexing ثم توليد أسئلة لكل الـ topics، ويتخزن الكتاب في مكتبة الكتب
   المُعالَجة (`content_hash` هو المفتاح).
2. **Student flow**: بدء امتحان لكتاب مُعالَج، الإجابة سؤال-سؤال، ومتابعة/استرجاع
   النتيجة النهائية والتقرير.

---

## Table of Contents

| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | `POST` | [`/books`](#1-post-books) | رفع كتاب جديد → يبدأ المعالجة كـ background job |
| 2 | `GET`  | [`/books/jobs/{job_id}`](#2-get-booksjobsjob_id) | متابعة حالة job المعالجة |
| 3 | `GET`  | [`/books`](#3-get-books) | قائمة الكتب المُعالَجة (للـ picker) |
| 4 | `GET`  | [`/books/{content_hash}/topics`](#4-get-bookscontent_hashtopics) | الـ topics المتاحة لكتاب معين |
| 5 | `POST` | [`/exams`](#5-post-exams) | بدء امتحان جديد |
| 6 | `GET`  | [`/exams/{exam_id}`](#6-get-examsexam_id) | حالة الامتحان الحالية (read-only، بدون تأثير) |
| 7 | `POST` | [`/exams/{exam_id}/answers`](#7-post-examsexam_idanswers) | إرسال إجابة → السؤال الجاي أو النتيجة النهائية |
| 8 | `GET`  | [`/exams/{exam_id}/report`](#8-get-examsexam_idreport) | تقرير الـ LLM النهائي |

---

## Conventions

- كل الـ responses بصيغة JSON.
- الأخطاء بترجع بالشكل: `{"detail": "<error message>"}` (أو array تفصيلي من FastAPI
  في حالة الـ `422 Validation Error`).
- الـ endpoints دي معمولها CORS مفتوح (`allow_origins=["*"]`) — يُنصح بتضييقه في الإنتاج.
- مفيش authentication حاليًا على الـ API — أي حد يقدر يستدعي أي endpoint (بما فيها
  رفع كتاب جديد). لازم يتضاف قبل الإنتاج.

---

## 1. `POST /books`

رفع كتاب PDF جديد ومعالجته بالكامل: **Knowledge Graph → RAG indexing → Question
generation**. الـ pipeline ده بياخد عادة **5-8 دقايق**، فالـ endpoint ده **لا
يستنى النتيجة النهائية** — بيحفظ الملف، يرمي الشغل في background thread، ويرجع
فورًا بـ `job_id`. الـ client لازم يتابع بعدها على
[`GET /books/jobs/{job_id}`](#2-get-booksjobsjob_id).

### Request

`multipart/form-data`

| Field     | Type          | Required | Description |
|-----------|---------------|----------|--------------|
| `file`    | file (`.pdf`) | ✅ | ملف الكتاب PDF. |
| `grade`   | string (form) | ✅ | مثال: `"Grade 5"`. |
| `subject` | string (form) | ✅ | مثال: `"Mathematics"`. |

**مثال (curl):**

```bash
curl -X POST http://localhost:8000/books \
  -F "file=@math_book.pdf" \
  -F "grade=Grade 5" \
  -F "subject=Mathematics"
```

### Response — `202 Accepted`

نفس الـ shape بتاع [`BookJobResponse`](#bookjobresponse-shape) لكن دايمًا في حالة
`queued` أو `generating_kg` وقت الاستجابة (لأن الـ job بيتحرك على thread تاني فورًا):

```json
{
  "job_id": "576d349b9a334300b94b3409a39ea5d2",
  "status": "generating_kg",
  "stage_detail": "Building the Knowledge Graph from the PDF",
  "filename": "math_book.pdf",
  "grade": "Grade 5",
  "subject": "Mathematics",
  "content_hash": null,
  "result": null,
  "error": null
}
```

### Errors

| Status | متى يحصل |
|--------|----------|
| `415`  | امتداد الملف مش `.pdf`. |
| `422`  | `grade` أو `subject` فاضيين، أو الحقول ناقصة أصلًا من الـ form. |
| `413`  | حجم الملف أكبر من 100MB. |
| `500`  | `OPENROUTER_API_KEY` مش موجود في الـ `.env`، أو فشل حفظ الملف على الديسك. |

### ملاحظة عن الـ deduplication

لو نفس محتوى الملف (بالـ `content_hash`، بغض النظر عن اسم الملف) اتعالج قبل كده،
الـ job بيوصل لحالة `done` بسرعة جدًا لإنه بيرجّع نفس الـ entry القديمة بدل ما
يعيد كل الـ pipeline من الأول.

---

## 2. `GET /books/jobs/{job_id}`

متابعة (polling) حالة job معالجة كتاب اتبعت في `POST /books`.

### Path Parameters

| Param    | Type   | Description |
|----------|--------|--------------|
| `job_id` | string | القيمة المُرجعة من `POST /books`. |

### `BookJobResponse` shape

| Field           | Type                  | Description |
|-----------------|-----------------------|--------------|
| `job_id`        | string                | معرّف الـ job. |
| `status`        | enum (انظر تحت)       | الحالة الحالية. |
| `stage_detail`  | string \| null        | وصف نصي مفهوم للمرحلة الحالية. |
| `filename`      | string                | اسم الملف الأصلي اللي اترفع. |
| `grade`         | string                | نفس القيمة المرسلة في `POST /books`. |
| `subject`       | string                | نفس القيمة المرسلة في `POST /books`. |
| `content_hash`  | string \| null        | بيظهر بمجرد ما مرحلة الـ Knowledge Graph تخلص (أول مرحلة). `null` قبل كده. |
| `result`        | [`BookSummary`](#booksummary-shape) \| null | بيتملى بس لما `status == "done"`. |
| `error`         | string \| null        | بيتملى بس لما `status == "failed"`. |

### Status state machine

```
queued → generating_kg → indexing → generating_questions → done
                                                          ↘ failed   (ممكن تحصل من أي مرحلة)
```

| Status                  | المعنى |
|--------------------------|--------|
| `queued`                | الـ job في الانتظار لسه ماخدش worker. |
| `generating_kg`          | بيتبني الـ Knowledge Graph من الـ PDF. |
| `indexing`               | بيتفهرس الكتاب في الـ RAG (chunking, embedding, vector store). |
| `generating_questions`   | بيتولّد أسئلة لكل topic في الـ Knowledge Graph. |
| `done`                   | خلص بنجاح. `result` فيه ملخص الكتاب المُعالَج. |
| `failed`                 | فشل في أي مرحلة. `error` فيه سبب الفشل. |

### Response — `200 OK`

**مثال (حالة `done`):**

```json
{
  "job_id": "576d349b9a334300b94b3409a39ea5d2",
  "status": "done",
  "stage_detail": "Book processed end-to-end",
  "filename": "math_book.pdf",
  "grade": "Grade 5",
  "subject": "Mathematics",
  "content_hash": "9f2a1e...c3b7",
  "result": {
    "content_hash": "9f2a1e...c3b7",
    "filename": "math_book.pdf",
    "grade": "Grade 5",
    "subject": "Mathematics",
    "processed_at": "2026-08-30T10:15:42.123456+00:00",
    "rag_file_reference_id": "a1b2c3d4e5f6",
    "indexed_chunks": 842,
    "entity_count": 37,
    "topics_generated": 37
  },
  "error": null
}
```

**مثال (حالة `failed`):**

```json
{
  "job_id": "576d349b9a334300b94b3409a39ea5d2",
  "status": "failed",
  "stage_detail": null,
  "filename": "math_book.pdf",
  "grade": "Grade 5",
  "subject": "Mathematics",
  "content_hash": null,
  "result": null,
  "error": "RAG indexing completed without returning file_reference_id."
}
```

### Errors

| Status | متى يحصل |
|--------|----------|
| `404`  | `job_id` مش موجود (غلط أو الـ process اتعمله restart، لأن الـ jobs مخزنة in-memory). |

---

## 3. `GET /books`

قائمة كل الكتب اللي اتعالجت بالكامل قبل كده — ده اللي بيغذي الـ **book picker**
في تطبيق الموبايل بدل ما يضطر المستخدم يرفع نفس الكتاب تاني.

### Request

مفيش parameters.

### Response — `200 OK`

```json
{
  "books": [
    {
      "content_hash": "9f2a1e...c3b7",
      "filename": "math_book.pdf",
      "grade": "Grade 5",
      "subject": "Mathematics",
      "processed_at": "2026-08-30T10:15:42.123456+00:00",
      "rag_file_reference_id": "a1b2c3d4e5f6",
      "indexed_chunks": 842,
      "entity_count": 37,
      "topics_generated": 37
    }
  ]
}
```

الترتيب: الأحدث معالجة أولًا (`processed_at` تنازليًا). القائمة بترجع فاضية
(`{"books": []}`) لو مفيش كتب اتعالجت لسه.

> **ملاحظة:** الـ response ده **مايحمّلش** الـ Knowledge Graph الكامل (ممكن يبقى
> كبير جدًا) — لو محتاج تفاصيل الـ topics لكتاب معين استخدم endpoint رقم 4.

---

## 4. `GET /books/{content_hash}/topics`

الـ topics المتاحة لكتاب معين، مأخوذة من الـ Knowledge Graph بتاعه.

### Path Parameters

| Param          | Type   | Description |
|----------------|--------|--------------|
| `content_hash` | string | القيمة اللي جاية من `GET /books` أو من نتيجة `POST /books`. |

### Response — `200 OK`

```json
{
  "content_hash": "9f2a1e...c3b7",
  "filename": "math_book.pdf",
  "grade": "Grade 5",
  "subject": "Mathematics",
  "topics": [
    {
      "id": "entity_12",
      "name": "الكسور العادية",
      "type": "concept",
      "has_questions": true
    },
    {
      "id": "entity_13",
      "name": "جمع الكسور",
      "type": "concept",
      "has_questions": true
    }
  ]
}
```

| Field               | Description |
|---------------------|--------------|
| `topics[].id`       | معرّف الـ entity في الـ Knowledge Graph. |
| `topics[].name`      | اسم الـ topic (مأخوذ من `entity.text`). |
| `topics[].type`      | نوع الـ entity في الـ graph (اختياري، ممكن يكون `null`). |
| `topics[].has_questions` | هل الـ topic ده عنده أسئلة محفوظة فعليًا في الـ Question Bank. عمليًا دايمًا `true` لكتاب راجع من `GET /books`، لأن `POST /books` بيولّد أسئلة لكل topic في الـ graph تلقائيًا — الحقل موجود للاستخدام المستقبلي (مثلاً لو الـ graph اتوسّع بعدين). |

### Errors

| Status | متى يحصل |
|--------|----------|
| `404`  | `content_hash` مش موجود — راجع `GET /books`. |

---

## 5. `POST /exams`

بدء امتحان جديد لطالب على كتاب مُعالَج. بيرجّع أول سؤال فورًا.

### Request Body

```json
{
  "student_id": "S1",
  "grade": "Grade 5",
  "subject": "Mathematics",
  "content_hash": "9f2a1e...c3b7"
}
```

| Field          | Type   | Required | Description |
|----------------|--------|----------|--------------|
| `student_id`   | string | ✅ | معرّف الطالب. |
| `grade`        | string | ✅ | لازم يطابق (case-insensitive) الـ `grade` اللي اتعالج بيه الكتاب. |
| `subject`      | string | ✅ | لازم يطابق (case-insensitive) الـ `subject` اللي اتعالج بيه الكتاب. |
| `content_hash` | string | ✅ | من `GET /books`. |

### Response — `200 OK`

```json
{
  "exam_id": "8f14e45f-ceea-4e...",
  "question": {
    "question_id": "q_ab12cd34...",
    "topic_name": "الكسور العادية",
    "difficulty_level": "L1",
    "question_type": "MCQ",
    "question": {
      "text": "أي الكسور التالية يساوي نصف؟",
      "options": {
        "A": "1/4",
        "B": "2/4",
        "C": "1/3",
        "D": "3/4"
      }
    }
  },
  "question_timeout_seconds": 60
}
```

> **ملاحظة:** الـ `question` object **مايحتويش** على الإجابة الصحيحة — الفحص
> بيحصل server-side فقط عند إرسال إجابة.

### Errors

| Status | متى يحصل |
|--------|----------|
| `400`  | `grade`/`subject` المُرسلين مايطابقوش اللي الكتاب اتعالج بيهم، أو مفيش أي topic عنده أسئلة محفوظة للـ grade/subject دول. |
| `404`  | `content_hash` مش موجود — راجع `GET /books`. |

---

## 6. `GET /exams/{exam_id}`

استرجاع حالة الامتحان الحالية **بدون أي تأثير جانبي** — مفيدة لو الطالب قفل
التطبيق نص الامتحان وفتحه تاني، أو أي client عايز يعمل polling للحالة من غير
ما يبعت إجابة.

### Path Parameters

| Param     | Type   | Description |
|-----------|--------|--------------|
| `exam_id` | string | من `POST /exams`. |

### Response — `200 OK`

**لو الامتحان لسه شغال (`in_progress`):**

```json
{
  "status": "in_progress",
  "exam_id": "8f14e45f-ceea-4e...",
  "question": { "...": "نفس شكل question في POST /exams" },
  "question_timeout_seconds": 60
}
```

بيرجّع بالظبط نفس السؤال اللي الطالب واقف عنده حاليًا — مفيش تقدّم في الامتحان
بسبب الاستدعاء ده.

**لو الامتحان خلص (`exam_ended`):** نفس شكل الـ response بتاع
[`POST /exams/{exam_id}/answers`](#7-post-examsexam_idanswers) لما يرجع
`exam_ended` (شوف مثال هناك).

### Errors

| Status | متى يحصل |
|--------|----------|
| `404`  | `exam_id` مش موجود (غلط، أو الـ process اتعمله restart لأن sessions مخزنة in-memory). |

---

## 7. `POST /exams/{exam_id}/answers`

إرسال إجابة الطالب على السؤال الحالي. بيرجّع إما السؤال الجاي أو، لو خلص كل
الـ topics، النتيجة النهائية.

### Path Parameters

| Param     | Type   | Description |
|-----------|--------|--------------|
| `exam_id` | string | من `POST /exams`. |

### Request Body

```json
{
  "question_id": "q_ab12cd34...",
  "answer": "B"
}
```

| Field         | Type                          | Required | Description |
|---------------|-------------------------------|----------|--------------|
| `question_id` | string                        | ✅ | `question_id` بتاع السؤال الحالي (من آخر response). |
| `answer`      | string \| string[] \| null    | ❌ | مفتاح الخيار الواحد لـ **MCQ** (مثال: `"B"`)، أو array من المفاتيح لـ **MSQ** (مثال: `["A", "C"]`)، أو `null` في حالة انتهاء الوقت/تخطي السؤال (بيتحسب غلط تلقائيًا). |

### Response — `200 OK`

**لو فيه سؤال جاي في نفس الـ topic (`next_question`):**

```json
{
  "status": "next_question",
  "exam_id": "8f14e45f-ceea-4e...",
  "question": { "...": "السؤال الجاي" },
  "question_timeout_seconds": 60
}
```

**لو خلص الـ topic الحالي وانتقل لـ topic جديد (`next_topic_first_question`):**

```json
{
  "status": "next_topic_first_question",
  "exam_id": "8f14e45f-ceea-4e...",
  "topic": "جمع الكسور",
  "question": { "...": "أول سؤال في الـ topic الجديد" },
  "question_timeout_seconds": 60
}
```

**لو الامتحان خلص خالص (`exam_ended`):**

```json
{
  "status": "exam_ended",
  "exam_id": "8f14e45f-ceea-4e...",
  "results": [
    {
      "topic_name": "الكسور العادية",
      "confirmed_level": "L3",
      "answers": [
        {
          "question_id": "q_ab12cd34...",
          "difficulty": "L1",
          "question_text": "أي الكسور التالية يساوي نصف؟",
          "options": { "A": "1/4", "B": "2/4", "C": "1/3", "D": "3/4" },
          "question_type": "MCQ",
          "student_answer": "B",
          "correct_answer": "B",
          "is_correct": true
        }
      ]
    },
    {
      "topic_name": "جمع الكسور",
      "confirmed_level": "not_assessed",
      "answers": []
    }
  ]
}
```

`confirmed_level` لكل topic بتكون واحدة من:
`below_L1` | `L1` | `L2` | `L3` | `not_assessed` (الامتحان خلص قبل ما يوصلها).

> **ملاحظة:** بعد ما تستلم `status: "exam_ended"`، استخدم
> [`GET /exams/{exam_id}/report`](#8-get-examsexam_idreport) لو محتاج تقرير
> نصي مفصّل بدل الأرقام الخام دي.

### Errors

| Status | متى يحصل |
|--------|----------|
| `404`  | `exam_id` أو `question_id` مش موجودين. |

---

## 8. `GET /exams/{exam_id}/report`

توليد (أو استرجاع، لو اتولّد قبل كده) تقرير نصي بصياغة الـ LLM، مفهوم للطالب
وولي الأمر، عن نتيجة الامتحان كامل.

### Path Parameters

| Param     | Type   | Description |
|-----------|--------|--------------|
| `exam_id` | string | من `POST /exams`. لازم يكون الامتحان خلص (`exam_ended`) قبل ما تستدعي الـ endpoint ده. |

### Response — `200 OK`

```json
{
  "exam_id": "8f14e45f-ceea-4e...",
  "report": "# تقرير الامتحان\n\n**الطالب:** S1 — **المادة:** Mathematics ..."
}
```

`report` نص Markdown طويل. أول مرة بتتولّد بيتم تخزينها (cached) جوه الـ exam
session، فأي استدعاء تاني لنفس الـ `exam_id` بيرجّع نفس النص فورًا من غير ما
يعمل استدعاء تاني للـ LLM.

### Errors

| Status | متى يحصل |
|--------|----------|
| `404`  | `exam_id` مش موجود. |
| `409`  | الامتحان لسه شغال ومخلصش (`is_finished == false`) — استنى `status: "exam_ended"` من endpoint رقم 6 أو 7 الأول. |

---

## Typical mobile app flow (end-to-end)

```
Admin:
  POST /books  (file + grade + subject)
        │
        ▼
  GET /books/jobs/{job_id}   ← poll كل كام ثانية
        │
        ▼ status == "done"
  GET /books                 ← content_hash بقى متاح للطلبة

Student:
  POST /exams  (student_id + grade + subject + content_hash)
        │
        ▼
  question #1 راجعة في الـ response
        │
        ▼ (لو الطالب قفل التطبيق فجأة)
  GET /exams/{exam_id}        ← يرجّع نفس السؤال الحالي
        │
        ▼
  POST /exams/{exam_id}/answers  (تكرار لحد ما status == "exam_ended")
        │
        ▼
  GET /exams/{exam_id}/report     ← اختياري، لو الطالب/ولي الأمر عايز تقرير
```
