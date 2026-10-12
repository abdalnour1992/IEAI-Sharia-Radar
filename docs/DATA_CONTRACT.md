# عقود البيانات وإتاحة المعلومات

تحتوي حزمة ZIP على CSV وmanifest.json في الجذر مباشرة، دون مجلدات داخلية، بحد أقصى 40 MiB. جميع التواريخ YYYY-MM-DD، والقيم العددية بوحدات موحدة، والعملة TRY. الحقول المنطقية true/false أو 1/0. الملفات المطلوبة: prices.csv وeligibility.csv وshares.csv وmanifest.json؛ financials.csv مطلوب لملف research_30. يمكن حذف الملفات الاختيارية غير المعبأة؛ القوالب الاختيارية الفارغة تُعامل كمفقودة.

`available_at` هو أول **تاريخ قرار يومي** تكون فيه المعلومة متاحة للعامة. تتخذ القرارات بعد إغلاق اليوم وتُنفذ في إغلاق اليوم التالي. يجب تحويل الإفصاحات والإجراءات إلى هذا الاصطلاح وتوثيق أوقات الإتاحة الأصلية في المصدر. لا يُستبدل تاريخ الإتاحة بنهاية الفترة المالية. يستخدم الإصدار الحالي تواريخ يومية؛ التحليل داخل الجلسة يحتاج دقة timestamps إضافية.

| الملف | الحقول |
|---|---|
| prices.csv | date, symbol, close, total_return_close, volume, value_traded_try, is_tradable |
| eligibility.csv | symbol, available_at, effective_from, effective_to, eligible, rule_set, source_url |
| shares.csv | symbol, available_at, shares_outstanding, source_url |
| financials.csv | symbol, available_at, period_end, total_assets, interest_bearing_debt, interest_bearing_assets, total_revenue, noncompliant_revenue, activity_pass, other_criteria_pass, source_url |
| benchmarks.csv | date, benchmark, level, kind, currency |
| factors.csv | date, market_excess, smb, hml, rmw, cma, rf |
| cpi.csv | date, cpi |

## دلالات مهمة

- close وأسهم الشركة وحجم التداول يجب أن تكون وحداتها متوافقة بعد التجزئات وزيادات رأس المال. لا يثبت اسم الحقل صحتها.
- total_return_close سلسلة موجبة للعائد الكلي تراعي التوزيعات والإجراءات الرأسمالية، وليست مجرد سعر اسمّي. يتطلب استخدامها مراجعة المزود.
- لا تُملأ الأسعار أو القيم أو الأهلية الناقصة للأمام. ينبغي توفير تقييم ومعالجة موثقة للتعليق والشطب؛ إذا كان الأصل محتفظًا به ولم تتوفر معلومات تنفيذ/تقييم كافية تتوقف المحاكاة.
- وجود عضو في BIST 100 لا يعني عدم توافقه شرعيًا، ووجود السهم في القطاع التقليدي بالاسم ليس فحصًا. eligibility.csv يعلن العضوية/الأهلية بحسب المصدر الموثق.
- تكون intervals للأهلية شاملة لتاريخ effective_to. لا يبدأ التطبيق قبل available_at أو effective_from. إذا حدثت تحديثات تختار آخر معلومة متاحة ضمن فترة سريانها.
- الأسهم القائمة تؤخذ من آخر معلومة متاحة. اكتمال السلسلة والتجزئات والتحويلات مسؤولية مراجعة البيانات.
- نسب الدين والأصول المخالفة تؤخذ من مبالغ المصدر، لا إجمالي ديون عشوائي أو نسبة متوقعة. لا تستبدل unknown بـ0 أو تصريح activity_pass غير موثق.
- benchmark أحد BIST_100 أو BIST_PARTICIPATION_100؛ kind هو price أو total_return. لا يختلط النوع داخل السلسلة، ولا تُستبدل gaps بأسعار مصطنعة.
- عوامل Fama-French هي عوائد عشرية يومية بالليرة وبنفس فترة المحفظة. rf مرجع تحليل؛ لا يمثل توجيهًا للاستثمار في أداة بعينها.
- CPI يستخدم لتقييم قيمة حقيقية بعد انتهاء التجربة، لا للتنبؤ. يشرح البيان هل التاريخ تاريخ شهر القياس أو تاريخ النشر.

## بيان المصادر

```json
{
  "dataset_id": "versioned-dataset-identifier",
  "dataset_kind": "real",
  "audit_status": "unreviewed",
  "currency": "TRY",
  "universe": "Historical BIST Participation 100 universe as of each decision",
  "price_convention": "Document total-return and raw price/share conventions",
  "sources": [
    {"file": "prices.csv", "provider": "Documented provider", "url": "https://source.example/record", "retrieved_at": "2026-10-12T00:00:00Z"}
  ],
  "sha256": {"prices.csv": "actual-file-sha256"}
}
```

تُكرر sources لكل ملف موجود. إذا أُضيفت sha256 يجب أن تطابق البصمة؛ لا تكتب المثال كأنه بصمة حقيقية. `reviewed` تصريح من معد البيانات، وليس شهادة يصدرها البرنامج. يجب الاحتفاظ بإثبات مراجعة مستقل للعضوية والتوقيت والوحدات والمصادر. لن تغير البرمجية هذا الحقل تلقائيًا.
