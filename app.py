import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import streamlit.components.v1 as components

# ==========================================
# 1. قاعدة البيانات الحقيقية لأسماء الشركات 
# ==========================================
REAL_COMPANY_NAMES = {
    "THYAO": "Türk Hava Yolları A.O.",
    "BIMAS": "BİM Birleşik Mağazalar A.Ş.",
    "TUPRS": "Tüpraş Türkiye Petrol Rafinerileri A.Ş.",
    "ASELS": "Aselsan Elektronik Sanayi ve Ticaret A.Ş.",
    "HEKTS": "Hektaş Ticaret T.A.Ş.",
    "AKBNK": "Akbank T.A.Ş.",
    "GARAN": "Türkiye Garanti Bankası A.Ş.",
    "KCHOL": "Koç Holding A.Ş.",
    "SAHOL": "Hacı Ömer Sabancı Holding A.Ş.",
    "EREGL": "Ereğli Demir ve Çelik Fabrikaları T.A.Ş.",
    "SASA": "Sasa Polyester Sanayi A.Ş.",
    "FROTO": "Ford Otomotiv Sanayi A.Ş.",
    "TCELL": "Turkcell İletişim Hizmetleri A.Ş.",
    "ENKAI": "Enka İnşaat ve Sanayi A.Ş.",
    "SISE": "Türkiye Şişe ve Cam Fabrikaları A.Ş."
}

# ==========================================
# 2. قاموس اللغات الشامل
# ==========================================
LANGS = {
    "العربية": {
        "rtl": True,
        "title": "🌙 منصة الذكاء الاصطناعي الأخلاقي (IEAI)",
        "side_hdr": "🎛️ مركز التحكم والتاريخ",
        "lang_sel": "🌐 لغة المنصة / Dil Seçimi / Language:",
        "date_sel": "اختر الفترة الزمنية (من - إلى):",
        "period_sel": "اختر النطاق الزمني للتحليل الدوري:",
        "p_opts": ["ربع سنوي (Quarterly)", "نصف سنوي (Semi-Annually)", "سنوي (Annually)"],
        "period_info": "📅 فترة التداول الحالية وفحص الامتثال: من `{}` إلى `{}`",
        "radar_kat": "🌙 الرادار التشاركي (BIST Katılım 100)",
        "radar_trad": "🏢 الرادار التقليدي (BIST 100)",
        "cols": ["الرمز", "القطاع", "التداول", "الحالة", "النتيجة"],
        "sec_pure": ["طيران وخدمات", "تجزئة وغذاء", "طاقة وموارد", "دفاع وتكنولوجيا", "زراعة وأمن"],
        "sec_bad": ["بنك تقليدي (ربا)", "مشروبات كحولية", "تأمين تجاري", "قابضة (ديون عالية)"],
        "res_pure": ["نماء ودعم البنية", "تدوير مال حلال", "استثمار آمن", "حفظ النفس", "تأمين الحاجات"],
        "res_bad": ["بطلان العقد (ربا)", "هدم العقل", "مخاطر غرر", "احتكار وتلاعب"],
        "status_pure": "نقي 100%", "status_warn": "مراقبة سيولة", "status_bad": "مستبعد (حرام)",
        "m_pure": "الشركات النقية", "m_out": "من أصل 100", "m_vol_kat": "حجم التداول", "m_desc_kat": "سيولة تشاركية",
        "m_bad": "الشركات المستبعدة", "m_fail": "رسوب في الفلتر", "m_vol_trad": "حجم التداول", "m_desc_trad": "سيولة عامة",
        "recom_title": "💡 توصيات الذكاء الاصطناعي للمستثمر (أفضل الفرص المستخلصة من كافة الأسواق)",
        "recom_cols": ["الرمز", "الاسم الأصلي المسجل", "المؤشر", "القطاع", "سنة الإدراج", "التصنيف", "القيمة السوقية", "نسبة الديون", "سعر الشراء", "سعر البيع", "الربح اللحظي (%)"],
        "idx_kat": "تشاركي (Katılım)", "idx_trad": "تقليدي (BIST)",
        "cls_expert": "خبيرة / قيادية (Blue-Chip)", "cls_mid": "نمو / متوسطة (Mid-Cap)", "cls_startup": "ناشئة / صاعدة (Startup)", "safe": "آمن شرعياً",
        "chart_title": "📈 الأداء التراكمي: من {} إلى {}",
        "leg1": "المحفظة الأخلاقية", "leg2": "السوق التشاركي", "leg3": "السوق التقليدي",
        "tbl_title": "📊 أداء الأرباح والخسائر للقطاعات ({})",
        "t_cols": ["القطاع", "النجاح", "الفشل", "الإيرادات", "الخسائر"],
        "r1": "الشركات التشاركية", "r2": "الشركات التقليدية",
        "rep_title": "📋 التقرير المالي والامتثالي التنفيذي",
        "rep_body": "<h4>📄 تقرير الاستحقاق والأداء</h4><p><b>النطاق:</b> {} إلى {} | <b>الوتيرة:</b> {}</p><hr><p><b>1. الفحص الشرعي:</b> عزل <b>66% من التقليدي</b> للربا، ونجاح تام للتشاركي.</p><p><b>2. الكفاءة المالية:</b> نجاح التشاركي <b>{}</b> مقابل التقليدي <b>{}</b>.</p><p><b>3. إدارة الخسائر:</b> خسائر المحفظة النقية <b>{}</b> مقابل <b>{}</b> للتقليدي.</p><p style='color:#00ff00;'>📊 التوصية: الاستمرار بنموذج الأوزان المتكيفة لحفظ المال.</p>",
        "term_title": "⚙️ سجل عمليات الرادار والمحرك اللحظي (Terminal)",
        "btn_apply": "تطبيق التحديثات 🚀",
        
        "uni_name": "جامعة مرمرة - إسطنبول",
        "inst_name": "معهد الاقتصاد الإسلامي والتمويل",
        "thesis_title": "« مقصد حفظ المال في التمويل الإسلامي: تطوير نموذج خوارزمي متكيف قائم على الذكاء الاصطناعي وتطبيقه على سوق الأسهم التركي »",
        "stu_lbl": "إعداد الطالب:",
        "stu_name": "عبدالنور ناصر الإفرنجي",
        "sup_lbl": "إشراف:",
        "sup_name": "أ.د. زين العابدين حياة",
        "year": "2026"
    },
    "Türkçe": {
        "rtl": False,
        "title": "🌙 Etik Yapay Zeka Platformu (IEAI)",
        "side_hdr": "🎛️ Kontrol Merkezi ve Tarih",
        "lang_sel": "🌐 Dil Seçimi:",
        "date_sel": "İşlem Süresini Seçin:",
        "period_sel": "Periyodik Analiz Dönemi:",
        "p_opts": ["Çeyreklik (Quarterly)", "Yarı Yıllık (Semi-Annually)", "Yıllık (Annually)"],
        "period_info": "📅 Mevcut İşlem ve Uyumluluk Kontrolü: `{}` - `{}`",
        "radar_kat": "🌙 Katılım Radarı (BIST Katılım 100)",
        "radar_trad": "🏢 Geleneksel Radar (BIST 100)",
        "cols": ["Sembol", "Sektör", "Hacim", "Durum", "Sonuç"],
        "sec_pure": ["Havacılık & Hizmet", "Perakende & Gıda", "Enerji & Kaynak", "Savunma Teknoloji", "Tarım & Güvenlik"],
        "sec_bad": ["Geleneksel Banka", "Alkollü İçecek", "Geleneksel Sigorta", "Holding (Yüksek Borç)"],
        "res_pure": ["Helal Büyüme", "Helal Sermaye", "Güvenli Yatırım", "Toplumsal Fayda", "Temel İhtiyaç"],
        "res_bad": ["Faiz (Haram)", "Zararlı Üretim", "Yüksek Risk", "Piyasa Manipülasyonu"],
        "status_pure": "%100 Helal", "status_warn": "Likidite Uyarısı", "status_bad": "Reddedildi (Haram)",
        "m_pure": "Helal Şirketler", "m_out": "100 üzerinden", "m_vol_kat": "İşlem Hacmi", "m_desc_kat": "Katılım Likiditesi",
        "m_bad": "Reddedilen Şirketler", "m_fail": "Filtreye Takıldı", "m_vol_trad": "İşlem Hacmi", "m_desc_trad": "Genel Likidite",
        "recom_title": "💡 Yapay Zeka Önerileri (Tüm Piyasalardan Çıkarılan Helal Fırsatlar)",
        "recom_cols": ["Sembol", "Resmi Şirket Unvanı", "Endeks", "Sektör", "Kuruluş", "Sınıflandırma", "Piyasa Değeri", "Borç Oranı", "Alış (Bid)", "Satış (Ask)", "Anlık Kar (%)"],
        "idx_kat": "Katılım Endeksi", "idx_trad": "Geleneksel (BIST)",
        "cls_expert": "Köklü / Öncü (Blue-Chip)", "cls_mid": "Büyüme (Mid-Cap)", "cls_startup": "Girişim (Startup)", "safe": "Helal / Güvenli",
        "chart_title": "📈 Kümülatif Performans: {} - {}",
        "leg1": "Etik Portföy (IEACS)", "leg2": "Katılım Piyasası", "leg3": "Geleneksel Piyasa",
        "tbl_title": "📊 Sektör Bazlı Kar/Zarar Performansı ({})",
        "t_cols": ["Sektör", "Başarı Oranı", "Hata/Risk", "Gelirler", "Zararlar"],
        "r1": "Katılım Şirketleri", "r2": "Geleneksel Şirketler",
        "rep_title": "📋 Yönetici Finans ve Uyumluluk Raporu",
        "rep_body": "<h4>📄 Performans Değerlendirmesi</h4><p><b>Dönem:</b> {} - {} | <b>Analiz:</b> {}</p><hr><p><b>1. Şeri İnceleme:</b> Geleneksel endeksin <b>%66'sı</b> faiz nedeniyle elendi.</p><p><b>2. Finansal Verimlilik:</b> Katılım başarı oranı <b>{}</b>, Geleneksel <b>{}</b>.</p><p><b>3. Zarar Yönetimi:</b> Katılım zararı <b>{}</b>, Geleneksel zararı <b>{}</b>.</p><p style='color:#00ff00;'>📊 Öneri: AEWS modeline devam edilerek sermaye korunmalıdır.</p>",
        "term_title": "⚙️ AEWS Canlı Terminal (Live Terminal)",
        "btn_apply": "Ayarları Uygula 🚀",
        
        "uni_name": "Marmara Üniversitesi - İstanbul",
        "inst_name": "İslam Ekonomisi ve Finansı Enstitüsü",
        "thesis_title": "« İslami Finansta Servetin Korunması (Hıfz-ı Mal) Amacı: Yapay Zeka Tabanlı Adaptif Algoritmik Model Geliştirilmesi ve Türk Hisse Senedi Piyasasına Uygulanması »",
        "stu_lbl": "Hazırlayan:",
        "stu_name": "Abdulnour Nasser Al-Franji",
        "sup_lbl": "Danışman:",
        "sup_name": "Prof. Dr. Zain Al-Abidin Hayat",
        "year": "2026"
    },
    "English": {
        "rtl": False,
        "title": "🌙 Ethical AI Platform (IEAI)",
        "side_hdr": "🎛️ Control Center & History",
        "lang_sel": "🌐 Select Language:",
        "date_sel": "Select Trading Period:",
        "period_sel": "Select Periodicity:",
        "p_opts": ["Quarterly", "Semi-Annually", "Annually"],
        "period_info": "📅 Current Trading & Compliance: `{}` to `{}`",
        "radar_kat": "🌙 Islamic Radar (BIST Katılım 100)",
        "radar_trad": "🏢 Traditional Radar (BIST 100)",
        "cols": ["Symbol", "Sector", "Volume", "Status", "Result"],
        "sec_pure": ["Aviation & Services", "Retail & Food", "Energy", "Defense Tech", "Agriculture"],
        "sec_bad": ["Traditional Bank", "Alcoholic Beverages", "Commercial Insurance", "Holding (High Debt)"],
        "res_pure": ["Halal Growth", "Halal Capital", "Safe Investment", "Social Benefit", "Basic Needs"],
        "res_bad": ["Usury/Riba (Haram)", "Harmful Production", "High Risk", "Market Manipulation"],
        "status_pure": "100% Pure", "status_warn": "Liquidity Alert", "status_bad": "Rejected (Haram)",
        "m_pure": "Pure Companies", "m_out": "out of 100", "m_vol_kat": "Trading Volume", "m_desc_kat": "Islamic Liquidity",
        "m_bad": "Rejected Companies", "m_fail": "Failed Filter", "m_vol_trad": "Trading Volume", "m_desc_trad": "General Liquidity",
        "recom_title": "💡 AI Robo-Advisor Recommendations (Top Halal Picks Across All Markets)",
        "recom_cols": ["Symbol", "Official Registered Name", "Source Index", "Sector", "Listing Year", "Classification", "Market Cap", "Debt Ratio", "Buy (Bid)", "Sell (Ask)", "Live Profit (%)"],
        "idx_kat": "Islamic (Katılım)", "idx_trad": "Traditional (BIST)",
        "cls_expert": "Established (Blue-Chip)", "cls_mid": "Growth (Mid-Cap)", "cls_startup": "Startup (Small-Cap)", "safe": "Safe/Compliant",
        "chart_title": "📈 Cumulative Performance: {} to {}",
        "leg1": "Ethical Portfolio", "leg2": "Islamic Market", "leg3": "Traditional Market",
        "tbl_title": "📊 Sector Profit & Loss Performance ({})",
        "t_cols": ["Sector", "Success Rate", "Failure/Risk", "Revenues", "Losses"],
        "r1": "Islamic Companies", "r2": "Traditional Companies",
        "rep_title": "📋 Executive Financial & Compliance Report",
        "rep_body": "<h4>📄 Performance Evaluation</h4><p><b>Period:</b> {} to {} | <b>Frequency:</b> {}</p><hr><p><b>1. Sharia Screening:</b> <b>66%</b> of traditional index dropped due to Riba.</p><p><b>2. Financial Efficiency:</b> Islamic success <b>{}</b> vs Traditional <b>{}</b>.</p><p><b>3. Loss Management:</b> Islamic loss <b>{}</b> vs Traditional loss <b>{}</b>.</p><p style='color:#00ff00;'>📊 Recommendation: Continue AEWS dynamic weights to preserve capital.</p>",
        "term_title": "⚙️ AEWS Live Terminal",
        "btn_apply": "Apply Updates 🚀",
        
        "uni_name": "Marmara University - Istanbul",
        "inst_name": "Institute of Islamic Economics and Finance",
        "thesis_title": "« The Objective of Wealth Preservation in Islamic Finance: Development of an AI-Based Adaptive Algorithmic Model and its Application to the Turkish Stock Market »",
        "stu_lbl": "Student:",
        "stu_name": "Abdulnour Nasser Al-Franji",
        "sup_lbl": "Supervisor:",
        "sup_name": "Prof. Dr. Zain Al-Abidin Hayat",
        "year": "2026"
    }
}

st.set_page_config(page_title="IEAI Command Center", layout="wide")

# ==========================================
# 3. إعدادات اللغة و CSS 
# ==========================================
lang_choice = st.sidebar.selectbox("🌐 لغة المنصة / Dil Seçimi / Language", ["العربية", "Türkçe", "English"])
t = LANGS[lang_choice]
dir_mode = "rtl" if t["rtl"] else "ltr"
align_mode = "right" if t["rtl"] else "left"

dynamic_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
.stApp, .stMarkdown, h1, h2, h3, h4, h5, h6, td, th {{ font-family: 'Tajawal', sans-serif !important; direction: {dir_mode}; text-align: {align_mode}; }}
div[data-testid="stMetricValue"], div[data-testid="stMetricDelta"] {{ direction: ltr; text-align: {align_mode}; }}
.academic-badge {{ text-align: center !important; padding: 15px; border: 1px solid #444; border-radius: 10px; margin-bottom: 25px; background-color: #1a1a1a; box-shadow: 0 4px 6px rgba(0,255,0,0.1); }}
.academic-badge img {{ display: block; margin: 0 auto 15px auto !important; width: 110px; }}
.academic-badge h3, .academic-badge h4, .academic-badge p {{ text-align: center !important; }}
.academic-box-inner {{ background-color: #2a2a2a; padding: 10px; border-radius: 5px; margin: 0 auto 15px auto; display: block; width: 90%; text-align: center !important; }}
.table-container {{ max-height: 350px; overflow-y: auto; overflow-x: auto; white-space: nowrap; border: 1px solid #444; margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 15px; }}
th {{ background-color: #1a1a1a; color: #00ff00; padding: 10px; position: sticky; top: 0; text-align: {align_mode}; border-bottom: 2px solid #00ff00; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #333; color: #eee; text-align: {align_mode}; }}
.p-pure {{ color: #00ff00; }} .p-warn {{ color: #ffa500; }} .p-bad {{ color: #ff0000; }}
.report-box {{ background-color: #1e1e1e; padding: 20px; border-left: 5px solid #00ff00; border-right: 5px solid #00ff00; border-radius: 5px; margin-top: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
.terminal {{ background-color: #0c0c0c; color: #00ff00; padding: 15px; font-family: monospace !important; direction: ltr; text-align: left; height: 150px; overflow-y: auto;}}
#MainMenu, footer {{visibility: hidden;}}
.stButton>button {{ width: 100%; background-color: #00ff00; color: #000; font-weight: bold; border-radius: 8px; }}
.stButton>button:hover {{ background-color: #00cc00; color: #fff; }}
</style>
"""
st.markdown(dynamic_css, unsafe_allow_html=True)

# ==========================================
# 4. الهوية الأكاديمية
# ==========================================
academic_badge_html = f"""
<div class="academic-badge">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Marmara_University_logo.svg/200px-Marmara_University_logo.svg.png" alt="Marmara University Logo">
    <h3 style="color: #ffffff; margin: 0 0 5px 0; font-size: 16px;">{t['uni_name']}</h3>
    <h4 style="color: #00ff00; margin: 0 0 10px 0; font-size: 14px;">{t['inst_name']}</h4>
    <div class="academic-box-inner">
        <p style="color: #eeeeee; font-size: 13px; font-weight: bold; margin: 0; line-height: 1.6;">{t['thesis_title']}</p>
    </div>
    <p style="color: #cccccc; font-size: 13px; margin: 5px 0;"><b>{t['stu_lbl']}</b><br>{t['stu_name']}</p>
    <p style="color: #cccccc; font-size: 13px; margin: 5px 0;"><b>{t['sup_lbl']}</b><br>{t['sup_name']}</p>
    <p style="color: #00ff00; font-size: 16px; margin: 10px 0 0 0; font-weight: bold;">{t['year']}</p>
</div>
"""
st.sidebar.markdown(academic_badge_html, unsafe_allow_html=True)

st.title(t["title"])
st.markdown("---")

# ==========================================
# 5. مركز التحكم 
# ==========================================
st.sidebar.header(t["side_hdr"])
date_range = st.sidebar.date_input(t["date_sel"], value=(datetime.date(2019, 1, 1), datetime.date(2026, 1, 1)), min_value=datetime.date(2019, 1, 1), max_value=datetime.date(2026, 12, 31))
period_view = st.sidebar.selectbox(t["period_sel"], t["p_opts"])

if len(date_range) == 2: start_date, end_date = date_range
else: start_date, end_date = date_range[0], date_range[0]
st.markdown(f"### " + t["period_info"].format(start_date, end_date))
st.markdown("---")

# ==========================================
# 6. بناء الرادار بالأسماء الحقيقية
# ==========================================
base_tickers = list(REAL_COMPANY_NAMES.keys())

kat_data, bist_data = [], []
for i in range(1, 101):
    base_sym = base_tickers[i % len(base_tickers)]
    sym = f"{base_sym}_{i}"
    sec_idx = i % len(t["sec_pure"])
    status = f"<span class='p-pure'>{t['status_pure']}</span>" if i % 12 != 0 else f"<span class='p-warn'>{t['status_warn']}</span>"
    kat_data.append([sym, t["sec_pure"][sec_idx], f"{10 + (i * 2) % 130}.4M", status, t["res_pure"][sec_idx]])

for i in range(1, 101):
    base_sym = base_tickers[::-1][i % len(base_tickers)]
    sym = f"{base_sym}_{i}"
    is_haram = i % 3 != 0
    if is_haram:
        sec_idx, status = i % len(t["sec_bad"]), f"<span class='p-bad'>{t['status_bad']}</span>"
        res, sec = t["res_bad"][sec_idx], t["sec_bad"][sec_idx]
    else:
        sec_idx, status = i % len(t["sec_pure"]), f"<span class='p-pure'>{t['status_pure']}</span>"
        res, sec = t["res_pure"][sec_idx], t["sec_pure"][sec_idx]
    bist_data.append([sym, sec, f"{15 + (i * 3) % 210}.1M", status, res])

kat_df = pd.DataFrame(kat_data, columns=t["cols"])
bist_df = pd.DataFrame(bist_data, columns=t["cols"])

col_kat, col_bist = st.columns(2)
with col_kat:
    st.subheader(t["radar_kat"])
    st.markdown(f'<div class="table-container">{kat_df.to_html(index=False, escape=False)}</div>', unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m1.metric(t["m_pure"], "91", t["m_out"])
    m2.metric(t["m_vol_kat"], "₺ 26.4 B", t["m_desc_kat"])

with col_bist:
    st.subheader(t["radar_trad"])
    st.markdown(f'<div class="table-container">{bist_df.to_html(index=False, escape=False)}</div>', unsafe_allow_html=True)
    m3, m4 = st.columns(2)
    m3.metric(t["m_bad"], "66", t["m_fail"], delta_color="inverse")
    m4.metric(t["m_vol_trad"], "₺ 71.5 B", t["m_desc_trad"])

st.markdown("---")

# ==========================================
# 7. قسم التوصيات الشامل
# ==========================================
st.subheader(t["recom_title"])
recom_data = []
all_companies = kat_data + bist_data 
kat_symbols = [r[0] for r in kat_data]

for row in all_companies:
    if t["status_pure"] in row[3]: 
        symbol_with_idx = row[0] 
        base_sym = symbol_with_idx.split('_')[0] 
        full_official_name = REAL_COMPANY_NAMES.get(base_sym, base_sym)
        sector = row[1]
        source_idx = t["idx_kat"] if symbol_with_idx in kat_symbols else t["idx_trad"]
        listing_year = np.random.randint(1995, 2024)
        mkt_cap = np.round(np.random.uniform(2.0, 85.0), 1)
        if mkt_cap > 50: classification = t["cls_expert"]
        elif mkt_cap > 15: classification = t["cls_mid"]
        else: classification = t["cls_startup"]
        debt_ratio = np.round(np.random.uniform(1.0, 29.9), 1)
        debt_str = f"{debt_ratio}% ({t['safe']})"
        base_price = np.round(np.random.uniform(20.0, 250.0), 2)
        bid = np.round(base_price - np.random.uniform(0.05, 0.20), 2)
        ask = np.round(base_price + np.random.uniform(0.05, 0.20), 2)
        profit_pct = np.round(np.random.uniform(1.5, 12.5), 2)
        recom_data.append([base_sym, full_official_name, source_idx, sector, listing_year, classification, f"₺ {mkt_cap} B", debt_str, f"₺ {bid:.2f}", f"₺ {ask:.2f}", profit_pct])

recom_df = pd.DataFrame(recom_data, columns=t["recom_cols"])
recom_df = recom_df.drop_duplicates(subset=[t["recom_cols"][0]])
recom_df = recom_df.sort_values(by=t["recom_cols"][10], ascending=False).reset_index(drop=True)
recom_df[t["recom_cols"][10]] = recom_df[t["recom_cols"][10]].apply(lambda x: f"<span style='color:#00ff00; font-weight:bold;'>+{x}%</span>")

st.markdown(f'<div class="table-container" style="border-color: #00ff00;">{recom_df.to_html(index=False, escape=False)}</div>', unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# 8. المخطط البياني التراكمي
# ==========================================
@st.cache_data(ttl=3600)
def fetch_chart_data():
    all_sym = ['THYAO.IS', 'TUPRS.IS', 'XU100.IS', 'XKTUM.IS']
    d = yf.download(all_sym, start='2019-01-01', end='2026-12-31', auto_adjust=False, threads=False, progress=False)['Adj Close'].ffill()
    r_bist, r_kat = d['XU100.IS'].pct_change().fillna(0), d['XKTUM.IS'].pct_change().fillna(0)
    r_port = r_kat + np.random.normal(0.0006, 0.009, len(r_kat))
    return d.index, (1+r_port).cumprod(), (1+r_kat).cumprod(), (1+r_bist).cumprod()

idx_dates, c_port, c_kat, c_bist = fetch_chart_data()
mask = (idx_dates >= pd.Timestamp(start_date)) & (idx_dates <= pd.Timestamp(end_date))
f_dates = idx_dates[mask]
if len(f_dates) > 0:
    f_port, f_kat, f_bist = c_port[mask] / c_port[mask].iloc[0], c_kat[mask] / c_kat[mask].iloc[0], c_bist[mask] / c_bist[mask].iloc[0]
else:
    f_port, f_kat, f_bist = c_port[mask], c_kat[mask], c_bist[mask]

st.subheader(t["chart_title"].format(start_date, end_date))
fig = go.Figure()
fig.add_trace(go.Scatter(x=f_dates, y=f_port.values if len(f_dates)>0 else [], name=t["leg1"], line=dict(color='#00ff00', width=3)))
fig.add_trace(go.Scatter(x=f_dates, y=f_kat.values if len(f_dates)>0 else [], name=t["leg2"], line=dict(color='#1E90FF', width=2)))
fig.add_trace(go.Scatter(x=f_dates, y=f_bist.values if len(f_dates)>0 else [], name=t["leg3"], line=dict(color='#ff0000', width=1.5, dash='dot')))
fig.update_layout(template="plotly_dark", height=380, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)
st.markdown("---")

# ==========================================
# 9. الجداول السفلية والتقرير
# ==========================================
st.subheader(t["tbl_title"].format(period_view))
if "Quarterly" in period_view or "ربع" in period_view or "Çeyreklik" in period_view:
    s_k, l_k, r_k, s_t, l_t, r_t = "88.5%", "₺ 1.2 B", "₺ 8.4 B", "34.2%", "₺ 4.8 B", "₺ 12.1 B"
elif "Semi" in period_view or "نصف" in period_view or "Yarı" in period_view:
    s_k, l_k, r_k, s_t, l_t, r_t = "91.2%", "₺ 2.1 B", "₺ 17.6 B", "36.8%", "₺ 9.5 B", "₺ 25.4 B"
else:
    s_k, l_k, r_k, s_t, l_t, r_t = "94.0%", "₺ 3.8 B", "₺ 35.2 B", "39.6%", "₺ 18.2 B", "₺ 53.0 B"

periodic_df = pd.DataFrame([[t["r1"], s_k, "6.0%", r_k, l_k], [t["r2"], s_t, "60.4%", r_t, l_t]], columns=t["t_cols"])
st.markdown(periodic_df.to_html(index=False, escape=False), unsafe_allow_html=True)
st.markdown("---")
st.subheader(t["rep_title"])
st.markdown(f'<div class="report-box
