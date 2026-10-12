"""Results are produced only by the actual research engine after a user action."""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile
import pandas as pd
import streamlit as st
from ieai.config import Protocol
from ieai.data import Dataset, DataError, SCHEMAS
from ieai.experiment import run_experiment, result_zip
from ieai.learning import TrainingUnavailable

st.set_page_config(page_title="IEAI Research Laboratory", layout="wide")
TEXT = {
    "ar": ["العربية", "مختبر حفظ المال والاختبار الرجعي", "نموذج بحثي يومي وفق مقترح الماجستير",
           "ارفع حزمة البيانات الموثقة ZIP", "تشغيل التجربة", "النتائج", "الأهلية والمؤشرات", "سجل التدريب والتنفيذ", "التقرير والمخرجات",
           "لا توجد نتائج قبل توفير البيانات وتشغيل التجربة. لا تُفترض الأهلية من أسماء الأسهم.",
           "تنزيل قوالب المدخلات", "إعدادات البروتوكول", "الأهلية الموثقة فقط", "الأهلية الموثقة مع حد ديون بحثي 30%",
           "تاريخ بدء التقييم", "بداية الاختبار النهائي المجمد", "نهاية الدراسة", "نسبة الخسارة المستهدفة", "أفق الخسارة بالجلسات",
           "أقصى وزن للسهم", "عمولة بالنقاط الأساسية", "انزلاق سعري بالنقاط الأساسية", "تنزيل حزمة النتائج",
           "جميع القيم ناتجة من البيانات والحسابات. تكاليف التنفيذ وإعدادات المخاطر افتراضات معلنة.",
           "سجل الأحداث الفعلية", "حدث", "المدخلات غير مكتملة أو غير صالحة", "بيانات اختبار مصطنعة لا تصلح دليلًا بحثيًا",
           "لم تُراجع المصادر استقلالًا وفق بيان المدخلات", "الأوزان", "الصفقات", "لا تمثل الدرجة حكمًا شرعيًا أو ضمانًا لحفظ المال",
           "اختيار اللغة", "تعرض يتكيف مع متوسط الدرجة", "تعرض كامل مع حدود التركيز", "سياسة التعرض",
           "تم حساب التجربة", "تاريخ بداية الدراسة", "قيمة رأس المال بالليرة التركية"],
    "en": ["English", "Wealth Preservation Research Laboratory", "Daily research engine for the master's proposal",
           "Upload documented dataset ZIP", "Run experiment", "Results", "Eligibility and features", "Training and execution audit", "Report and exports",
           "No results before data and an actual run. Eligibility is never inferred from ticker names.",
           "Download input templates", "Protocol settings", "Historical attestation only", "Attestation plus research 30% debt limit",
           "Evaluation start", "Frozen final holdout start", "Study end", "Target loss threshold", "Loss horizon in sessions",
           "Maximum stock weight", "Commission in bps", "Slippage in bps", "Download results package",
           "Values come from input observations and calculations. Costs and risk settings are disclosed assumptions.",
           "Actual processing events", "Event", "Incomplete or invalid inputs", "Synthetic software-test data is not empirical evidence",
           "Sources have not been independently reviewed according to input metadata", "Positions", "Trades", "The score is not a religious verdict or a capital guarantee",
           "Language", "Exposure follows mean score", "Full exposure with concentration caps", "Exposure policy",
           "Experiment calculated", "Study start", "Initial capital in TRY"],
    "tr": ["Türkçe", "Malın Korunması Araştırma Laboratuvarı", "Yüksek lisans önerisi için günlük araştırma motoru",
           "Belgelenmiş veri ZIP dosyasını yükleyin", "Deneyi çalıştır", "Sonuçlar", "Uygunluk ve göstergeler", "Eğitim ve işlem denetimi", "Rapor ve dışa aktarma",
           "Veri ve deney olmadan sonuç gösterilmez. Uygunluk sembol adlarından çıkarılmaz.",
           "Girdi şablonlarını indir", "Protokol ayarları", "Tarihsel uygunluk beyanı", "Beyan ve araştırma amaçlı %30 borç sınırı",
           "Değerlendirme başlangıcı", "Dondurulmuş son test başlangıcı", "Çalışma sonu", "Hedef kayıp eşiği", "Kayıp ufku seans sayısı",
           "Azami hisse ağırlığı", "Komisyon baz puan", "Kayma baz puan", "Sonuç paketini indir",
           "Değerler verilerden hesaplanır. İşlem maliyetleri ve risk ayarları açıklanan varsayımlardır.",
           "Gerçek işlem olayları", "Olay", "Eksik veya geçersiz girdiler", "Sentetik test verisi ampirik kanıt değildir",
           "Girdi beyanına göre kaynaklar bağımsız incelenmemiştir", "Pozisyonlar", "İşlemler", "Skor fetva veya sermaye garantisi değildir",
           "Dil", "Ortalama skora bağlı riskli varlık payı", "Yoğunlaşma sınırlarıyla tam yatırım", "Riskli varlık payı politikası",
           "Deney hesaplandı", "Çalışma başlangıcı", "TRY cinsinden başlangıç sermayesi"],
}
language = st.sidebar.selectbox("Language / اللغة / Dil", ["ar", "en", "tr"], format_func=lambda x: TEXT[x][0], key="language")
t = TEXT[language]
if language == "ar":
    st.markdown("<style>h1,h2,h3,p {direction:rtl;text-align:right}</style>", unsafe_allow_html=True)
st.title(t[1])
st.caption(t[2])
st.info(t[9])
st.caption(t[31])

def templates_zip():
    output = BytesIO()
    manifest = {"dataset_id": "replace-with-reviewed-dataset-id", "dataset_kind": "real", "audit_status": "unreviewed",
                "currency": "TRY", "universe": "document-historical-universe-selection", "price_convention": "document-prices-shares-and-corporate-actions",
                "sources": [{"file": "prices.csv", "provider": "REPLACE", "url": "REPLACE", "retrieved_at": "REPLACE"}]}
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, fields in SCHEMAS.items():
            archive.writestr(name, ",".join(fields) + "\n")
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return output.getvalue()

st.sidebar.download_button(t[10], templates_zip(), "input-templates.zip", "application/zip")
uploaded = st.file_uploader(t[3], type=["zip"])
default = Protocol()
with st.sidebar.form("protocol_form"):
    st.subheader(t[11])
    profile = st.selectbox(t[11], ["research_30", "attested_membership"], format_func=lambda x: t[13] if x == "research_30" else t[12])
    study_start = st.date_input(t[37], pd.Timestamp(default.study_start).date())
    evaluation_start = st.date_input(t[14], pd.Timestamp(default.evaluation_start).date())
    holdout_start = st.date_input(t[15], pd.Timestamp(default.holdout_start).date())
    study_end = st.date_input(t[16], pd.Timestamp(default.study_end).date())
    threshold = st.number_input(t[17], .01, .90, .10, .01)
    horizon = st.number_input(t[18], 2, 126, 20)
    cap = st.number_input(t[19], .01, 1.0, .10, .01)
    commission = st.number_input(t[20], 0.0, 100.0, 5.0, 1.0)
    slippage = st.number_input(t[21], 0.0, 100.0, 10.0, 1.0)
    capital = st.number_input(t[38], 1000.0, 1e10, 100000.0, 1000.0)
    exposure = st.selectbox(t[35], ["mean_score", "fully_invested"], format_func=lambda x: t[33] if x == "mean_score" else t[34])
    submitted = st.form_submit_button(t[4], disabled=uploaded is None)
if uploaded is not None:
    input_key = sha256(uploaded.getvalue()).hexdigest()
    if st.session_state.get("dataset_key") != input_key:
        st.session_state.pop("result", None)
        st.session_state["dataset_key"] = input_key
if submitted:
    try:
        protocol = replace(default, screening_profile=profile, study_start=str(study_start),
                study_end=str(study_end), evaluation_start=str(evaluation_start), holdout_start=str(holdout_start),
                loss_threshold=threshold, horizon=int(horizon), max_stock_weight=cap,
                commission_bps=commission, slippage_bps=slippage, initial_capital=capital, exposure_policy=exposure)
        dataset = Dataset.from_zip(uploaded.getvalue())
        events = []
        progress = st.empty()
        def update(stage):
            events.append(stage)
            progress.info(f"{t[25]}: {stage}")
        st.session_state["result"] = run_experiment(dataset, protocol, progress=update)
        st.session_state["events"] = events
        progress.success(t[36])
    except (DataError, TrainingUnavailable, ValueError, KeyError) as exc:
        st.session_state.pop("result", None)
        st.error(f"{t[26]}: {exc}")
if "result" in st.session_state:
    result = st.session_state["result"]
    report = result["report"]
    if report["dataset_kind"] == "synthetic":
        st.error(t[27])
    if report["audit_status"] != "reviewed":
        st.warning(t[28])
    st.caption(t[23])
    st.caption(json.dumps(report["protocol"], ensure_ascii=False))
    tabs = st.tabs([t[5], t[6], t[7], t[8]])
    with tabs[0]:
        curves = {name: test.daily.set_index("date").index_level for name, test in result["backtests"].items()}
        curves.update({name: frame.set_index("date").index_level for name, frame in result["benchmarks"].items()})
        st.line_chart(pd.DataFrame(curves))
        st.dataframe(pd.DataFrame({name: metrics["full_test"] for name, metrics in report["metrics"].items()}).T)
        st.dataframe(pd.DataFrame(report["forecast_validation"]))
        for warning in report["warnings"]:
            st.warning(warning)
    with tabs[1]:
        st.dataframe(result["eligibility"])
        st.dataframe(result["scores"].drop(columns=["target_event", "forward_loss", "label_end"], errors="ignore"))
    with tabs[2]:
        st.write(t[24])
        st.dataframe(pd.DataFrame({t[25]: st.session_state.get("events", [])}))
        st.dataframe(result["model_audit"])
        st.write(t[30])
        st.dataframe(result["backtests"]["adaptive_ml"].trades)
        st.write(t[29])
        st.dataframe(result["backtests"]["adaptive_ml"].positions)
    with tabs[3]:
        st.json(report)
        st.download_button(t[22], result_zip(result), "ieai-experiment.zip", "application/zip")
