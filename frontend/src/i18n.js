import { createContext, createElement, useContext } from "react";

const HindiContext = createContext("en");

// Keep UI chrome translations deterministic and offline. Agreement wording and generated
// explanations are translated by the backend translation service, not by this static dictionary.
const HI = {
  'Home purchase agreement': 'घर खरीद समझौता',
  Dashboard: "डैशबोर्ड",
  "Analyze agreement": "समझौते का विश्लेषण",
  "Analyze an agreement": "समझौते का विश्लेषण करें",
  "My documents": "मेरे दस्तावेज़",
  "Risk reports": "जोखिम रिपोर्ट",
  "Saved analyses": "सहेजे गए विश्लेषण",
  "Help & support": "सहायता और समर्थन",
  "Privacy & security": "गोपनीयता और सुरक्षा",
  WORKSPACE: "कार्यस्थल",
  LIBRARY: "लाइब्रेरी",
  "Local workspace": "स्थानीय कार्यस्थल",
  "Private by default": "डिफ़ॉल्ट रूप से निजी",
  "New analysis": "नया विश्लेषण",
  Workspace: "कार्यस्थल",
  "Analysis report": "विश्लेषण रिपोर्ट",
  "Search documents, clauses…": "दस्तावेज़ और धाराएँ खोजें…",
  "Search documents": "दस्तावेज़ खोजें",
  DOCUMENTS: "दस्तावेज़",
  "No matching documents found.": "कोई मेल खाता दस्तावेज़ नहीं मिला।",
  "View all documents": "सभी दस्तावेज़ देखें",
  "You're all caught up": "अभी कोई नया अपडेट नहीं है",
  "New analysis updates will appear here.":
    "विश्लेषण के नए अपडेट यहाँ दिखाई देंगे।",
  Dismiss: "बंद करें",
  "YOUR LEGAL WORKSPACE": "आपका कानूनी कार्यस्थल",
  "Agreement clarity starts here.": "समझौते को समझने की शुरुआत यहाँ से करें।",
  "Review the fine print, surface terms worth questioning, and make more informed decisions before you sign.":
    "हस्ताक्षर करने से पहले बारीक शर्तें समझें, संदिग्ध नियम पहचानें और बेहतर निर्णय लें।",
  "CLAUSELENS WORKSPACE": "क्लॉज़लेंस कार्यस्थल",
  "Know what you’re": "समझें कि आप किस बात पर",
  "signing up for.": "हस्ताक्षर कर रहे हैं।",
  "Turn complex agreements into clear, structured insights — one clause at a time.":
    "जटिल समझौतों की धाराओं को स्पष्ट और व्यवस्थित जानकारी में बदलें।",
  "Explore a sample": "नमूना देखें",
  "AGREEMENT REVIEW": "समझौते की समीक्षा",
  "ClauseLens analysis": "क्लॉज़लेंस विश्लेषण",
  "Clause flagged for review": "समीक्षा के लिए चिह्नित धारा",
  "Financial terms · Section 4.2": "वित्तीय शर्तें · अनुभाग 4.2",
  "Privacy-first": "गोपनीयता प्राथमिकता",
  "Local analysis workflow": "स्थानीय विश्लेषण प्रक्रिया",
  "Documents reviewed": "समीक्षित दस्तावेज़",
  "Total saved analyses": "कुल सहेजे गए विश्लेषण",
  "High-risk reports": "उच्च-जोखिम रिपोर्ट",
  "Review these first": "पहले इनकी समीक्षा करें",
  "No high-risk reports yet": "अभी कोई उच्च-जोखिम रिपोर्ट नहीं",
  "Needs a closer look": "अधिक ध्यान से समीक्षा करें",
  "Medium-risk reports": "मध्यम-जोखिम रिपोर्ट",
  "Lower-risk reports": "कम-जोखिम रिपोर्ट",
  "Still review key terms": "मुख्य शर्तों की फिर भी समीक्षा करें",
  "Recent documents": "हाल के दस्तावेज़",
  "Your most recently analyzed agreements": "हाल ही में विश्लेषित समझौते",
  "View all": "सभी देखें",
  "Your library is ready": "आपकी लाइब्रेरी तैयार है",
  "Start with a rental agreement or an employment offer.":
    "किराया समझौते या नौकरी के प्रस्ताव से शुरुआत करें।",
  "Start a review": "समीक्षा शुरू करें",
  "Choose a document to get started.": "शुरू करने के लिए दस्तावेज़ चुनें।",
  "Upload an agreement": "समझौता अपलोड करें",
  "Try a sample agreement": "नमूना समझौता आज़माएँ",
  "Explore how the analysis works": "देखें कि विश्लेषण कैसे काम करता है",
  "Your report history stays in your local workspace. Review the privacy notes before uploading sensitive documents.":
    "आपकी रिपोर्ट का इतिहास स्थानीय कार्यस्थल में रहता है। संवेदनशील दस्तावेज़ अपलोड करने से पहले गोपनीयता सूचना पढ़ें।",
  "Important:": "महत्वपूर्ण:",
  "ClauseLens is an awareness and document-review aid, not a legal verdict. Risk flags are indicators and should be reviewed with a qualified legal professional.":
    "क्लॉज़लेंस जानकारी और दस्तावेज़ समीक्षा में मदद करता है, कानूनी निर्णय नहीं देता। जोखिम संकेतों की योग्य कानूनी पेशेवर से समीक्षा करवाएँ।",
  "ANALYSIS WORKSPACE": "विश्लेषण कार्यस्थल",
  "Analyze an agreement": "समझौते का विश्लेषण करें",
  "Upload a document or paste the relevant text. ClauseLens will organize clauses and flag terms that may need closer review.":
    "दस्तावेज़ अपलोड करें या उसका पाठ चिपकाएँ। क्लॉज़लेंस धाराओं को व्यवस्थित करके संभावित जोखिम चिह्नित करेगा।",
  "STEP 1 OF 2": "चरण 1 / 2",
  "Choose your agreement": "अपना समझौता चुनें",
  "Start with a file or paste the contract text below.":
    "फ़ाइल चुनें या नीचे अनुबंध का पाठ चिपकाएँ।",
  "Local workflow": "स्थानीय प्रक्रिया",
  "Upload file": "फ़ाइल अपलोड करें",
  "Paste text": "पाठ चिपकाएँ",
  "Agreement text": "समझौते का पाठ",
  "Paste the rental agreement, leave and license agreement, job offer, or service bond text here…":
    "किराया समझौते, लीव एंड लाइसेंस, नौकरी के प्रस्ताव या सेवा-बॉन्ड का पाठ यहाँ चिपकाएँ…",
  "Clear text": "पाठ साफ़ करें",
  "STEP 2 OF 2": "चरण 2 / 2",
  "Configure the review": "समीक्षा सेट करें",
  "Choose the document language and the language for explanations.":
    "दस्तावेज़ की भाषा और स्पष्टीकरण की भाषा चुनें।",
  "Sample agreement type": "नमूना समझौते का प्रकार",
  "Rental / Leave & License": "किराया / लीव एंड लाइसेंस",
  "Employment offer / service bond": "नौकरी का प्रस्ताव / सेवा-बॉन्ड",
  "Used for sample documents. For your own file, ClauseLens infers the agreement type from its text.":
    "यह नमूना दस्तावेज़ों के लिए है। आपकी फ़ाइल का प्रकार पाठ के आधार पर पहचाना जाएगा।",
  "Document language": "दस्तावेज़ की भाषा",
  "Auto-detect language": "भाषा अपने आप पहचानें",
  "Auto-detect works on extracted text. For scanned PDFs, choose the language manually and install its Tesseract language pack.":
    "स्वचालित पहचान निकाले गए पाठ पर काम करती है। स्कैन किए गए PDF के लिए भाषा चुनें और उसका Tesseract भाषा पैक इंस्टॉल करें।",
  "Explanation language": "स्पष्टीकरण की भाषा",
  "Non-English review uses a configured LibreTranslate service. Original wording is preserved for comparison.":
    "अंग्रेज़ी के अलावा अन्य भाषाओं के लिए LibreTranslate सेवा आवश्यक है। तुलना के लिए मूल शब्द सुरक्षित रखे जाते हैं।",
  "Save this analysis in my history": "इस विश्लेषण को इतिहास में सहेजें",
  "Uncheck this if you do not want the report saved to your local document history.":
    "रिपोर्ट को स्थानीय इतिहास में सहेजना नहीं चाहते, तो इसे अनचेक करें।",
  "Analyzing agreement…": "समझौते का विश्लेषण हो रहा है…",
  Reset: "रीसेट करें",
  "Use a sample": "नमूना इस्तेमाल करें",
  "Extracting text, reviewing clauses and preparing a risk summary. Longer agreements can take a little more time.":
    "पाठ निकाला जा रहा है, धाराओं की समीक्षा और जोखिम सारांश तैयार हो रहा है। बड़े समझौतों में अधिक समय लग सकता है।",
  "What you'll get": "आपको क्या मिलेगा",
  "Risk overview": "जोखिम सारांश",
  "A high-level view of clauses flagged for closer attention.":
    "अधिक ध्यान देने योग्य चिह्नित धाराओं का सारांश।",
  "Plain-language explanations": "सरल भाषा में स्पष्टीकरण",
  "Clause-by-clause explanations to help you understand the wording.":
    "हर धारा का स्पष्टीकरण ताकि शर्तें समझने में आसानी हो।",
  "Key terms & missing items": "मुख्य शर्तें और अनुपस्थित जानकारी",
  "Important amounts, timelines and a checklist of potential gaps.":
    "महत्वपूर्ण राशि, समय-सीमा और संभावित कमियों की सूची।",
  "Handle documents carefully": "दस्तावेज़ सावधानी से संभालें",
  "Personal identifiers such as certain account numbers and contact details are masked before analysis. Names and addresses may remain in the text.":
    "विश्लेषण से पहले कुछ खाता नंबर और संपर्क विवरण छिपाए जाते हैं। नाम और पते पाठ में रह सकते हैं।",
  "Privacy details": "गोपनीयता विवरण",
  "ClauseLens is an awareness tool, not a replacement for legal advice. Risk flags are heuristics.":
    "क्लॉज़लेंस जानकारी देने वाला टूल है, कानूनी सलाह का विकल्प नहीं। जोखिम संकेत अनुमान-आधारित हैं।",
  Documents: "दस्तावेज़",
  TYPE: "प्रकार",
  "RISK LEVEL": "जोखिम स्तर",
  ANALYZED: "विश्लेषण तिथि",
  ACTIONS: "कार्रवाई",
  DOCUMENT: "दस्तावेज़",
  "View report": "रिपोर्ट देखें",
  "Delete report": "रिपोर्ट हटाएँ",
  "No documents yet": "अभी कोई दस्तावेज़ नहीं",
  "Analyze an agreement to build your private document library.":
    "अपनी निजी दस्तावेज़ लाइब्रेरी बनाने के लिए किसी समझौते का विश्लेषण करें।",
  "No documents match your search": "आपकी खोज से कोई दस्तावेज़ मेल नहीं खाता",
  "Try a different title or clear the search field.":
    "दूसरा शीर्षक आज़माएँ या खोज फ़ील्ड साफ़ करें।",
  "Loading your workspace…": "आपका कार्यस्थल लोड हो रहा है…",
  "Saved documents": "सहेजे गए दस्तावेज़",
  "No saved documents": "कोई सहेजा गया दस्तावेज़ नहीं",
  "Your analyzed agreements will appear here when saved.":
    "सहेजे जाने के बाद आपके विश्लेषित समझौते यहाँ दिखाई देंगे।",
  "YOUR SHORTLIST": "आपकी चुनी हुई रिपोर्टें",
  "DOCUMENT LIBRARY": "दस्तावेज़ लाइब्रेरी",
  "RISK MONITORING": "जोखिम निगरानी",
  "Browse completed reports and open the findings that need your attention.":
    "पूरी हुई रिपोर्टें देखें और ध्यान देने योग्य निष्कर्ष खोलें।",
  "Your locally saved agreement analyses, organized in one place.":
    "आपके स्थानीय रूप से सहेजे गए समझौतों के विश्लेषण, एक ही जगह पर।",
  "Analysis complete": "विश्लेषण पूरा हुआ",
  "Back to documents": "दस्तावेज़ों पर वापस जाएँ",
  "ANALYSIS REPORT": "विश्लेषण रिपोर्ट",
  "segments detected": "खंड पहचाने गए",
  "Download PDF": "PDF डाउनलोड करें",
  "Save analysis": "विश्लेषण सहेजें",
  Saved: "सहेजा गया",
  "New review": "नई समीक्षा",
  "More report options": "रिपोर्ट के अन्य विकल्प",
  "OVERALL RISK SCORE": "कुल जोखिम स्कोर",
  "High risk": "उच्च जोखिम",
  "Medium risk": "मध्यम जोखिम",
  "Low risk": "कम जोखिम",
  "Several clauses may deserve careful review before you proceed.":
    "आगे बढ़ने से पहले कई धाराओं की सावधानी से समीक्षा करनी चाहिए।",
  "Some clauses could benefit from clarification or negotiation.":
    "कुछ धाराओं पर स्पष्टीकरण या बातचीत की आवश्यकता हो सकती है।",
  "No high-severity flags were identified by the current rules.":
    "मौजूदा नियमों ने कोई गंभीर जोखिम संकेत नहीं पाया।",
  "A screening indicator, not a legal judgment.":
    "यह प्रारंभिक संकेत है, कानूनी निर्णय नहीं।",
  "High-risk clauses": "उच्च-जोखिम धाराएँ",
  "Prioritize these first": "इनकी पहले समीक्षा करें",
  "Medium-risk clauses": "मध्यम-जोखिम धाराएँ",
  "Clarify before signing": "हस्ताक्षर से पहले स्पष्ट करें",
  "Key terms extracted": "निकाली गई मुख्य शर्तें",
  "Amounts, dates and periods": "राशियाँ, तिथियाँ और अवधि",
  Summary: "सारांश",
  "Clause explorer": "धारा एक्सप्लोरर",
  "Ask this agreement": "समझौते से पूछें",
  "Clause risk distribution": "धाराओं का जोखिम वितरण",
  "Risk levels across assessed clauses": "समीक्षित धाराओं में जोखिम स्तर",
  assessed: "समीक्षित",
  "Key findings to review": "समीक्षा योग्य मुख्य निष्कर्ष",
  "Clauses with the highest assigned risk levels":
    "सबसे अधिक जोखिम स्तर वाली धाराएँ",
  "Explore clauses": "धाराएँ देखें",
  "No clauses received a risk classification in this report.":
    "इस रिपोर्ट में किसी धारा को जोखिम वर्ग नहीं मिला।",
  "Key terms found": "मिली मुख्य शर्तें",
  "Details extracted directly from the agreement text":
    "समझौते के पाठ से निकाले गए विवरण",
  items: "आइटम",
  "View clause": "धारा देखें",
  "No financial amounts or time periods were extracted from this agreement.":
    "इस समझौते से कोई वित्तीय राशि या समयावधि नहीं निकाली गई।",
  "Potentially missing terms": "संभावित रूप से अनुपस्थित शर्तें",
  "These items weren't clearly identified by the current review. Confirm whether they apply to your agreement.":
    "वर्तमान समीक्षा में ये बातें स्पष्ट रूप से नहीं मिलीं। पुष्टि करें कि वे आपके समझौते पर लागू होती हैं या नहीं।",
  "Review all": "सभी की समीक्षा करें",
  "No likely gaps were detected by the current checklist.":
    "वर्तमान चेकलिस्ट में कोई स्पष्ट कमी नहीं मिली।",
  "Ask your agreement": "अपने समझौते से पूछें",
  "Find a clause that answers your question.":
    "अपने प्रश्न का उत्तर देने वाली धारा खोजें।",
  "Ask a question about this agreement": "इस समझौते के बारे में प्रश्न पूछें",
  "Ask question": "प्रश्न पूछें",
  "Answer from the agreement": "समझौते से मिला उत्तर",
  "No clear answer found": "स्पष्ट उत्तर नहीं मिला",
  "Your question": "आपका प्रश्न",
  "Response language": "उत्तर की भाषा",
  "Find answer": "उत्तर खोजें",
  "Relevant wording found": "संबंधित शब्दावली मिली",
  "Source clauses": "स्रोत धाराएँ",
  "Original agreement text": "समझौते का मूल पाठ",
  "Plain-language explanation": "सरल भाषा में स्पष्टीकरण",
  "Risk indicators": "जोखिम संकेत",
  "Copy explanation": "स्पष्टीकरण कॉपी करें",
  Copied: "कॉपी किया गया",
  "Ask about this clause": "इस धारा के बारे में पूछें",
  "Select a clause": "एक धारा चुनें",
  "Choose an item from the clause list to inspect the original wording and its explanation.":
    "मूल शब्दावली और उसका स्पष्टीकरण देखने के लिए धारा सूची से आइटम चुनें।",
  "Answers are retrieved from the analyzed agreement text and show source clauses when a match is found.":
    "उत्तर विश्लेषित समझौते से निकाले जाते हैं और मेल मिलने पर स्रोत धाराएँ दिखाई जाती हैं।",
  "Try asking": "ये पूछकर देखें",
  "When is the security deposit refunded?":
    "सिक्योरिटी डिपॉज़िट कब वापस मिलेगा?",
  "What is the notice period?": "नोटिस अवधि कितनी है?",
  "What happens if I leave early?":
    "अगर मैं समय से पहले छोड़ दूँ तो क्या होगा?",
  "Print / save as PDF": "प्रिंट / PDF के रूप में सहेजें",
  "YOUR DATA": "आपका डेटा",
  "SUPPORT CENTRE": "सहायता केंद्र",
  PREFERENCES: "प्राथमिकताएँ",
  "Saved items are managed in your local browser session. Open a report and use your browser print dialog to save a copy as PDF.":
    "सहेजे गए आइटम आपके स्थानीय ब्राउज़र में प्रबंधित होते हैं। रिपोर्ट खोलें और PDF के रूप में सहेजने के लिए प्रिंट विकल्प इस्तेमाल करें।",
  "Workspace settings": "कार्यस्थल सेटिंग्स",
  "Manage the way ClauseLens behaves on this device.":
    "इस डिवाइस पर क्लॉज़लेंस का व्यवहार प्रबंधित करें।",
  "Language and save-history preferences are available during each new analysis. This local workspace does not currently use user accounts or cloud sync.":
    "हर नए विश्लेषण में भाषा और इतिहास सहेजने के विकल्प उपलब्ध हैं। यह स्थानीय कार्यस्थल यूज़र अकाउंट या क्लाउड सिंक इस्तेमाल नहीं करता।",
  "How can we help?": "हम कैसे मदद कर सकते हैं?",
  "Get familiar with the main ClauseLens workflow.":
    "क्लॉज़लेंस की मुख्य प्रक्रिया समझें।",
  "Upload a PDF, DOCX or TXT agreement, select the document and explanation languages, then run the analysis. Review risk flags alongside the original text and discuss important concerns with a qualified legal professional.":
    "PDF, DOCX या TXT समझौता अपलोड करें, दस्तावेज़ और स्पष्टीकरण की भाषा चुनें, फिर विश्लेषण चलाएँ। जोखिम संकेतों की मूल पाठ के साथ समीक्षा करें और महत्वपूर्ण चिंताओं पर योग्य कानूनी पेशेवर से चर्चा करें।",
  "Privacy & security": "गोपनीयता और सुरक्षा",
  "Understand how documents are processed by this local application.":
    "समझें कि इस स्थानीय ऐप में दस्तावेज़ कैसे संसाधित होते हैं।",
  "The provided backend masks several structured identifiers before analysis, but names and addresses may remain. Saved reports are stored in the local SQLite database. Uncheck “Save this analysis in my history” if you do not want a report saved.":
    "बैकएंड विश्लेषण से पहले कई पहचान-संबंधी नंबर छिपाता है, लेकिन नाम और पते रह सकते हैं। रिपोर्ट स्थानीय SQLite डेटाबेस में सहेजी जाती हैं। रिपोर्ट सहेजना नहीं चाहते तो “इतिहास में सहेजें” विकल्प हटाएँ।",
  "Good to know": "जानने योग्य बातें",
  "Risk flags are screening indicators": "जोखिम संकेत प्रारंभिक संकेत हैं",
  "They help identify wording that may deserve closer review; they do not determine legal enforceability.":
    "ये उन शर्तों की पहचान में मदद करते हैं जिनकी समीक्षा ज़रूरी हो सकती है; ये कानूनी वैधता तय नहीं करते।",
  "Check the original wording": "मूल शब्दावली जाँचें",
  "Always compare explanations with the clause in your actual agreement.":
    "स्पष्टीकरण की तुलना अपने वास्तविक समझौते की धारा से हमेशा करें।",
  "Review privacy before upload": "अपलोड से पहले गोपनीयता जाँचें",
  "Avoid uploading documents you are not permitted to share or process on this device.":
    "ऐसे दस्तावेज़ अपलोड न करें जिन्हें साझा करने या इस डिवाइस पर संसाधित करने की अनुमति नहीं है।",
  "Not legal advice": "कानूनी सलाह नहीं",
  "Local-first agreement review": "स्थानीय समझौता समीक्षा",
  "Backend connection not detected. Start the FastAPI server and refresh this page.":
    "बैकएंड कनेक्शन नहीं मिला। FastAPI सर्वर शुरू करके पेज रीफ़्रेश करें।",
  Retry: "फिर कोशिश करें",
  "Interface language": "इंटरफ़ेस भाषा",
  "Report language": "रिपोर्ट की भाषा",
  "Legal AI workspace": "कानूनी AI कार्यस्थल",
  characters: "अक्षर",
  "Please choose a PDF, DOCX, TXT or MD file.":
    "कृपया PDF, DOCX, TXT या MD फ़ाइल चुनें।",
  "Ready to analyze": "विश्लेषण के लिए तैयार",
  "Replace file": "फ़ाइल बदलें",
  Remove: "हटाएँ",
  "Drop your agreement here": "अपना समझौता यहाँ छोड़ें",
  "or select a file from your device": "या अपने डिवाइस से फ़ाइल चुनें",
  "Browse files": "फ़ाइलें ब्राउज़ करें",
  "PDF, DOCX, TXT or MD · up to 5 MB": "PDF, DOCX, TXT या MD · अधिकतम 5 MB",
  "Upload file": "फ़ाइल अपलोड करें",
  "Paste text": "पाठ चिपकाएँ",
  "Local translation is available at": "स्थानीय अनुवाद सेवा यहाँ उपलब्ध है",
  "A remote translation service is configured at":
    "रिमोट अनुवाद सेवा यहाँ कॉन्फ़िगर है",
  "English analysis works without translation. For Hindi or other-language documents/reports, start a local LibreTranslate service at http://127.0.0.1:5000. ClauseLens does not silently upload legal documents to a remote translator.":
    "अंग्रेज़ी विश्लेषण अनुवाद के बिना काम करता है। हिंदी या अन्य भाषाओं के दस्तावेज़/रिपोर्ट के लिए http://127.0.0.1:5000 पर स्थानीय LibreTranslate सेवा शुरू करें। ClauseLens कानूनी दस्तावेज़ों को चुपचाप किसी बाहरी अनुवादक को नहीं भेजता।",
  "Supported language pairs depend on the installed models.":
    "समर्थित भाषा-जोड़े इंस्टॉल किए गए मॉडल पर निर्भर करते हैं।",
  "Sample agreement type": "नमूना समझौते का प्रकार",
  "Used for sample documents. For your own file, ClauseLens infers the agreement type from its text.":
    "यह नमूना दस्तावेज़ों के लिए है। आपकी फ़ाइल का प्रकार पाठ के आधार पर पहचाना जाएगा।",
  "Select an agreement file": "समझौते की फ़ाइल चुनें",
  "Save analysis": "विश्लेषण सहेजें",
  Saved: "सहेजा गया",
  "New review": "नई समीक्षा",
  Summary: "सारांश",
  "Clause explorer": "धारा एक्सप्लोरर",
  "Ask this agreement": "इस समझौते से पूछें",
  "High risk": "उच्च जोखिम",
  "Medium risk": "मध्यम जोखिम",
  "Low risk": "कम जोखिम",
  "All documents": "सभी दस्तावेज़",
  "High risk": "उच्च जोखिम",
  "Medium risk": "मध्यम जोखिम",
  "Low risk": "कम जोखिम",
  "Select a clause": "एक धारा चुनें",
  "agreement segments": "समझौते के खंड",
  "Select an item": "एक आइटम चुनें",
  "ORIGINAL AGREEMENT TEXT": "समझौते का मूल पाठ",
  "PLAIN-LANGUAGE EXPLANATION": "सरल भाषा में स्पष्टीकरण",
  "No plain-language explanation was generated for this segment. Review the wording carefully.":
    "इस खंड के लिए सरल भाषा में स्पष्टीकरण नहीं बनाया गया। शब्दों की सावधानी से समीक्षा करें।",
  "No clauses received a risk classification in this report.":
    "इस रिपोर्ट में किसी धारा को जोखिम वर्ग नहीं दिया गया।",
  "REPAIRS AND MAINTENANCE": "मरम्मत और रखरखाव",
  "Please wait while the report is translated.":
    "रिपोर्ट का अनुवाद होने तक प्रतीक्षा करें।",
  "The translation service is unavailable.": "अनुवाद सेवा उपलब्ध नहीं है।",
  "Translation may miss legal nuance. Compare the translated explanation with the original agreement wording.":
    "अनुवाद में कानूनी बारीकियाँ छूट सकती हैं। अनुवादित स्पष्टीकरण की मूल समझौते की भाषा से तुलना करें।",

  "Close navigation": "नेविगेशन बंद करें",
  "Open navigation": "नेविगेशन खोलें",
  "Main navigation": "मुख्य नेविगेशन",
  Notifications: "सूचनाएँ",
  "Dismiss notification": "सूचना हटाएँ",
  Help: "सहायता",
  "English interface": "अंग्रेज़ी इंटरफ़ेस",
  "Hindi interface": "हिंदी इंटरफ़ेस",
  "Filter documents": "दस्तावेज़ फ़िल्टर करें",
  "model unavailable": "मॉडल उपलब्ध नहीं",
  "Local translation is available at": "स्थानीय अनुवाद सेवा यहाँ उपलब्ध है",
  "A remote translation service is configured at":
    "रिमोट अनुवाद सेवा यहाँ कॉन्फ़िगर है",
  "Supported language pairs depend on the installed models.":
    "उपलब्ध भाषा-जोड़े इंस्टॉल किए गए मॉडल पर निर्भर करते हैं।",
  "English analysis works without translation. For Hindi or other-language documents/reports, start a local LibreTranslate service at http://127.0.0.1:5000. ClauseLens does not silently upload legal documents to a remote translator.":
    "अंग्रेज़ी विश्लेषण अनुवाद के बिना भी काम करता है। हिंदी या अन्य भाषा के दस्तावेज़ और रिपोर्ट के लिए http://127.0.0.1:5000 पर स्थानीय LibreTranslate सेवा शुरू करें। ClauseLens आपकी जानकारी के बिना कानूनी दस्तावेज़ किसी बाहरी अनुवाद सेवा पर नहीं भेजता।",
  "Report translation failed. The original report is still displayed.":
    "रिपोर्ट का अनुवाद नहीं हो सका। मूल रिपोर्ट दिखाई जा रही है।",
  "Could not translate this report:": "इस रिपोर्ट का अनुवाद नहीं हो सका:",
  "Translation is unavailable.": "अनुवाद उपलब्ध नहीं है।",
  "Translation is not running.": "अनुवाद सेवा चालू नहीं है।",
  "Hinglish is available for new analyses using built-in templates.":
    "नई समीक्षा के लिए पहले से उपलब्ध Hinglish टेम्पलेट इस्तेमाल किए जा सकते हैं।",
  "The interface is in Hindi, but this report remains in English because the translation service is not running. Start local LibreTranslate to translate report explanations.":
    "इंटरफ़ेस हिंदी में है, लेकिन अनुवाद सेवा चालू नहीं होने के कारण यह रिपोर्ट अंग्रेज़ी में है। रिपोर्ट के स्पष्टीकरणों का अनुवाद करने के लिए स्थानीय LibreTranslate शुरू करें।",
  "Explanation language": "स्पष्टीकरण की भाषा",
  "Document language": "दस्तावेज़ की भाषा",
  Clause: "धारा",
  "Agreement clause": "समझौते की धारा",
  "View source": "स्रोत देखें",
  "Open full question workspace": "प्रश्नों का पूरा कार्यक्षेत्र खोलें",
  "Key terms:": "मुख्य शर्तें:",
  "These items weren't clearly identified by the current review. Confirm whether they apply to your agreement.":
    "वर्तमान समीक्षा में ये बातें स्पष्ट रूप से नहीं मिलीं। पुष्टि करें कि वे आपके समझौते पर लागू होती हैं या नहीं।",
  "Review all": "सभी की समीक्षा करें",
  "Filter documents": "दस्तावेज़ फ़िल्टर करें",
  "PDF, DOCX, TXT or MD": "PDF, DOCX, TXT या MD",
  "Know what you’re": "समझें कि आप किस बात पर",
  "signing up for.": "सहमति दे रहे हैं।",
  "Turn complex agreements into clear, structured insights — one clause at a time.":
    "जटिल समझौतों को हर धारा के स्पष्ट और व्यवस्थित विश्लेषण में बदलें।",
  "Explore a sample": "नमूना देखें",
  "Security deposit": "सुरक्षा जमा",
  "Rent increase": "किराये में वृद्धि",
  "Lock-in period": "लॉक-इन अवधि",
  Termination: "समाप्ति",
  "Notice period": "नोटिस अवधि",
  "Service bond": "सेवा बॉन्ड",
  "Training cost recovery": "प्रशिक्षण लागत की वसूली",
  "Salary deductions": "वेतन से कटौती",
  Confidentiality: "गोपनीयता",
  "Landlord access": "मकान मालिक का प्रवेश",
  "Repairs & maintenance": "मरम्मत और रखरखाव",
  "Utilities & charges": "उपयोगिता और अन्य शुल्क",
  "Guests & subletting": "मेहमान और उप-किरायेदारी",
  "Document retention": "दस्तावेज़ रोककर रखना",
  "Payment terms": "भुगतान की शर्तें",
  "Dispute resolution": "विवाद समाधान",
  "Governing law": "लागू कानून",
  "Default & eviction": "चूक और बेदखली",
  "Tenant verification": "किरायेदार सत्यापन",
  "Handover & inventory": "कब्ज़ा सौंपना और सूची",
  "Non-compete": "प्रतिस्पर्धा-निषेध",
  "Other clause": "अन्य धारा",
  "Rental agreement": "किराया समझौता",
  "Employment offer & bond": "नौकरी का प्रस्ताव और बॉन्ड",
  "Employment offer and service bond": "नौकरी का प्रस्ताव और सेवा बॉन्ड",
  Agreement: "समझौता",
  "Date unavailable": "तिथि उपलब्ध नहीं",
  Recently: "हाल ही में",
  Today: "आज",
  Yesterday: "कल",
  "A translated explanation is not the original legal wording. Always verify it against the source clause.":
    "अनुवादित स्पष्टीकरण मूल कानूनी शब्दावली नहीं है। हमेशा इसकी मूल धारा से तुलना करें।",
  "Translation may miss legal nuance. Compare the translated explanation with the original agreement wording.":
    "अनुवाद में कानूनी बारीकियाँ छूट सकती हैं। अनुवादित स्पष्टीकरण की मूल समझौते की भाषा से तुलना करें।",

  "Ask about the security deposit, notice period, penalties, responsibilities, or another clause…":
    "सुरक्षा जमा, नोटिस अवधि, जुर्माने, ज़िम्मेदारियों या किसी अन्य धारा के बारे में पूछें…",
  "ClauseLens is an awareness tool, not legal advice. Risk labels are indicators, not a legal verdict. Have important clauses reviewed by a qualified advocate.":
    "ClauseLens जानकारी और दस्तावेज़ समीक्षा में मदद करता है, यह कानूनी सलाह या कानूनी निर्णय नहीं है। महत्वपूर्ण धाराओं की योग्य वकील से समीक्षा करवाएँ।",
  "Clear filter": "फ़िल्टर साफ़ करें",
  "These items weren't clearly identified by the current review. Confirm whether they apply to your agreement.":
    "वर्तमान समीक्षा में ये बातें स्पष्ट रूप से नहीं मिलीं। पुष्टि करें कि वे आपके समझौते पर लागू होती हैं या नहीं।",
  "What you'll get": "आपको क्या मिलेगा",
  "You're all caught up": "अभी कोई नया अपडेट नहीं है",
  "Report language is Hindi, but translation is unavailable. Start the local translation service to translate the report text.":
    "रिपोर्ट की भाषा हिंदी चुनी गई है, लेकिन अनुवाद उपलब्ध नहीं है। रिपोर्ट का अनुवाद करने के लिए स्थानीय अनुवाद सेवा शुरू करें।",
  "Analysis failed. Check the document and try again.":
    "विश्लेषण विफल हुआ। दस्तावेज़ जाँचकर दोबारा प्रयास करें।",
  "Analysis complete. Compare translated findings with the original clauses.":
    "विश्लेषण पूरा हुआ। अनुवादित निष्कर्षों की मूल धाराओं से तुलना करें।",
  "Sample agreement loaded. Review the text before analyzing.":
    "नमूना समझौता लोड हो गया। विश्लेषण से पहले पाठ की समीक्षा करें।",
  "Could not load document history": "दस्तावेज़ इतिहास लोड नहीं हो सका",
  "Local analysis workflow": "स्थानीय विश्लेषण प्रक्रिया",
  "Total saved analyses": "कुल सहेजे गए विश्लेषण",
  "PDF, DOCX, TXT or MD": "PDF, DOCX, TXT या MD",
  "Full agreement analysis report": "समझौते की पूरी विश्लेषण रिपोर्ट",
  "Report ID": "रिपोर्ट आईडी",
  "Analyzed on": "विश्लेषण की तारीख",
  "Source document language": "मूल दस्तावेज़ की भाषा",
  "Lower-risk clauses": "कम जोखिम वाली धाराएँ",
  "Executive summary": "कार्यकारी सारांश",
  "This report is a screening aid. It does not determine whether a clause is enforceable.":
    "यह रिपोर्ट प्रारंभिक जाँच के लिए है। यह तय नहीं करती कि कोई धारा कानूनी रूप से लागू की जा सकती है या नहीं।",
  "Key terms and amounts": "मुख्य शर्तें और राशियाँ",
  "Priority findings": "प्राथमिक निष्कर्ष",
  "No high or medium risk clauses were flagged by the current rules.":
    "मौजूदा नियमों ने कोई उच्च या मध्यम जोखिम वाली धारा चिह्नित नहीं की।",
  "Full clause-by-clause review": "हर धारा की पूरी समीक्षा",
  "Every extracted segment is included below, regardless of which report tab was open when PDF export was selected.":
    "PDF बनाते समय रिपोर्ट का कोई भी टैब खुला हो, नीचे सभी निकाले गए खंड शामिल हैं।",
  "Original agreement wording": "समझौते की मूल शब्दावली",
  "Original wording was not separately matched.":
    "मूल शब्दावली का अलग से मिलान नहीं हो सका।",
  "Why this matters": "यह क्यों महत्वपूर्ण है",
  "Suggested next steps": "सुझाए गए अगले कदम",
  "No clause segments were detected in this report.":
    "इस रिपोर्ट में कोई धारा नहीं मिली।",
  "Legal disclaimer": "कानूनी अस्वीकरण",
  "Important: Translation may miss legal nuance. Verify all translated explanations against the original agreement.":
    "महत्वपूर्ण: अनुवाद में कानूनी बारीकियाँ छूट सकती हैं। सभी अनुवादित स्पष्टीकरणों की मूल समझौते से तुलना करें।",
  "Original wording could not be matched confidently":
    "मूल शब्दावली का विश्वसनीय मिलान नहीं हो सका",
  "The system could not confidently map this translated finding back to an exact source-language segment.":
    "सिस्टम इस अनुवादित निष्कर्ष को मूल भाषा के किसी सटीक खंड से विश्वसनीय रूप से नहीं जोड़ सका।",
  "Text used for classification (English translation)":
    "वर्गीकरण के लिए इस्तेमाल किया गया पाठ (अंग्रेज़ी अनुवाद)",
  "No text available.": "पाठ उपलब्ध नहीं है।",
  "TEXT USED FOR CLASSIFICATION (ENGLISH TRANSLATION)":
    "वर्गीकरण के लिए इस्तेमाल किया गया पाठ (अंग्रेज़ी अनुवाद)",
  "The system could not confidently match this finding to the exact original clause. The wording below is the English translation used for classification.":
    "सिस्टम इस निष्कर्ष को मूल धारा से विश्वसनीय रूप से नहीं जोड़ सका। नीचे दिया गया पाठ वर्गीकरण के लिए इस्तेमाल किया गया अंग्रेज़ी अनुवाद है।",
  "Original wording was not separately matched.":
    "मूल शब्दावली का अलग से मिलान नहीं हो सका।",
  "Question and answer": "प्रश्न और उत्तर",
  Question: "प्रश्न",
  Answer: "उत्तर",
  "Review the clauses below alongside the original agreement wording.":
    "नीचे दी गई धाराओं की मूल समझौते की शब्दावली से तुलना करें।",
  "No financial amounts or time periods were extracted from this agreement.":
    "इस समझौते से कोई वित्तीय राशि या समयावधि नहीं निकाली गई।",
};

export function translateUiText(value, language = "en") {
  if (typeof value !== "string" || language !== "hi") return value;
  return HI[value] || value;
}

export function I18nProvider({ language = "en", children }) {
  return createElement(HindiContext.Provider, { value: language }, children);
}

export function useT() {
  const language = useContext(HindiContext);
  return (value) => translateUiText(value, language);
}

export const UI_TEXT_HI = HI;
