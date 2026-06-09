export interface ConditionFaq {
  question: string;
  answer: string;
}

export type ConditionAudience = 'all' | 'women' | 'men';

export interface ConditionData {
  slug: string;
  sort: number;
  name: string;
  shortDescription: string;
  image: string;
  ogImage: string;
  audience: ConditionAudience;
  hook: string;
  reflectiveClose: string;
  heroSubline: string;
  symptoms: string[];
  whatWeOffer: string[];
  stats: Array<{ numeral: string; caption: string }>;
  faqs: ConditionFaq[];
  schemaName: string;
  schemaDescription: string;
  sensitiveCategory: boolean;
}

export const CONDITIONS: ConditionData[] = [
  {
    slug: "thyroid",
    sort:3,
    name: "Thyroid",
    image: "/treatments/Thyroid.webp",
    ogImage: "/treatments/Thyroid.png",
    audience: "all",
    shortDescription: "Hypothyroidism, Hashimoto's, and thyroid hormone balance.",
    hook: "She thought she was just tired. For three years.",
    reflectiveClose: "Three years is a long time to feel like a stranger to yourself.",
    heroSubline:
      "Fatigue, weight changes, hair thinning, brain fog — thyroid dysfunction presents differently in every patient. A doctor who reads the full picture, not just the TSH.",
    symptoms: [
      "Persistent fatigue despite adequate sleep",
      "Unexplained weight changes",
      "Hair thinning or excessive hair loss",
      "Brain fog and difficulty concentrating",
      "Cold intolerance",
      "Irregular or heavy menstrual cycles",
      "Dry skin and brittle nails",
      "Mood changes, including depression",
    ],
    whatWeOffer: [
      "Complete thyroid panel including TSH, free T3, free T4, and anti-TPO",
      "Diagnosis of hypothyroidism, hyperthyroidism, and Hashimoto's thyroiditis",
      "Levothyroxine titration with 6-week rechecks",
      "Longitudinal biomarker tracking across every consultation",
      "Doctor's commentary on every new lab report",
    ],
    stats: [
      { numeral: "10.95%", caption: "adult prevalence in India" },
      { numeral: "6 weeks", caption: "typical levothyroxine recheck interval" },
      { numeral: "1 doctor", caption: "who stays with you throughout" },
    ],
    faqs: [
      {
        question: "What is the difference between TSH normal range and feeling normal?",
        answer:
          "TSH measures the pituitary's signal to the thyroid, not thyroid function directly. A TSH within laboratory reference range does not guarantee optimal thyroid hormone conversion. Symptoms, free T3, free T4, and anti-TPO together give a more complete picture.",
      },
      {
        question: "Do I need to test for Hashimoto's separately?",
        answer:
          "Yes. Hashimoto's thyroiditis is an autoimmune condition where anti-TPO and anti-thyroglobulin antibodies attack the thyroid. Standard TSH testing does not diagnose it. Your Kyros doctor will determine whether antibody testing is indicated based on your symptom history.",
      },
      {
        question: "How long does it take to feel better on levothyroxine?",
        answer:
          "Most patients notice improvement within 4 to 8 weeks of starting an effective dose. Because levothyroxine has a narrow therapeutic window, dose titration continues until TSH and symptoms stabilise — this typically takes 3 to 6 months of supervised adjustment.",
      },
      {
        question: "Can I consult a Kyros doctor if I am already on thyroid medication?",
        answer:
          "Yes. Many patients come to Kyros having been on levothyroxine for years without a recent panel review. We review your current medication, order a complete panel, and adjust if indicated.",
      },
    ],
    schemaName: "Hypothyroidism",
    schemaDescription:
      "A condition where the thyroid gland does not produce enough thyroid hormone, causing fatigue, weight gain, and other systemic symptoms.",
    sensitiveCategory: false,
  },
  {
    slug: "weight-management",
    sort:1,
    name: "Weight Management",
    image: "/treatments/WeightManagement.webp",
    ogImage: "/treatments/WeightManagement.png",
    audience: "all",
    shortDescription: "Doctor-supervised weight management, including GLP-1 therapy where indicated.",
    hook: "You've tried five things. None of them worked. That isn't a character flaw.",
    reflectiveClose:
      "The first honest conversation about your weight should be with someone who measures, not someone who sells.",
    heroSubline:
      "Weight is a metabolic and hormonal story before it is a lifestyle story. A Kyros doctor evaluates the whole picture — insulin resistance, cortisol, thyroid function — and builds a plan that is medical, not motivational.",
    symptoms: [
      "Difficulty losing weight despite dietary changes",
      "Fatigue that does not improve with rest",
      "Insulin resistance or pre-diabetes",
      "PCOS-related weight gain",
      "Unexplained weight gain over 6 to 12 months",
      "Metabolic syndrome markers",
    ],
    whatWeOffer: [
      "Metabolic workup: fasting insulin, HbA1c, lipid panel, thyroid panel, cortisol",
      "Doctor-supervised GLP-1 therapy (tirzepatide, semaglutide) where clinically indicated",
      "Personalised diet and activity guidance alongside medical management",
      "Regular follow-up with dose titration and side-effect management",
      "Longitudinal weight and biomarker tracking",
    ],
    stats: [
      { numeral: "₹1,250", caption: "approximate monthly cost of generic semaglutide" },
      { numeral: "3 months", caption: "typical programme before meaningful biomarker response" },
      { numeral: "7", caption: "metabolic conditions that can drive weight resistance" },
    ],
    faqs: [
      {
        question: "Is GLP-1 therapy right for me?",
        answer:
          "GLP-1 receptor agonists (tirzepatide, semaglutide) are medically indicated for patients with a BMI above 27 with metabolic comorbidities, or BMI above 30. Your Kyros doctor will evaluate your clinical profile before prescribing. These medications are not prescribed on demand.",
      },
      {
        question: "What metabolic tests should I have before starting a weight management programme?",
        answer:
          "At minimum: fasting blood glucose, HbA1c, fasting insulin, HOMA-IR, lipid panel (with ApoB if available), thyroid panel (TSH, free T3), liver function, and uric acid. Your doctor may add other panels based on your history.",
      },
      {
        question: "Is Kyros a diet programme?",
        answer:
          "No. Kyros is a doctor-first medical programme. Dietary guidance is one part of a clinical plan that begins with laboratory evaluation and medical assessment. We do not sell meal plans or supplements.",
      },
    ],
    schemaName: "Obesity",
    schemaDescription:
      "A complex metabolic condition involving excess body fat, insulin resistance, and associated hormonal dysregulation, managed through medically supervised interventions.",
    sensitiveCategory: false,
  },
  {
    slug: "pcos",
    sort:4,
    name: "PCOS",
    image: "/treatments/PCOS.webp",
    ogImage: "/treatments/PCOS.png",
    audience: "women",
    shortDescription: "Polycystic ovary syndrome — hormonal, metabolic, and reproductive care.",
    hook: "Your cycle has been a question mark for years. It doesn't have to stay one.",
    reflectiveClose: "Some answers are quiet. They're still answers.",
    heroSubline:
      "PCOS is an insulin problem that looks like a hormone problem that looks like a period problem. A Kyros doctor evaluates all three dimensions and builds a plan that is specific to your phenotype.",
    symptoms: [
      "Irregular or absent menstrual cycles",
      "Excess facial or body hair (hirsutism)",
      "Acne, especially along the jaw and chin",
      "Hair thinning or loss on the scalp",
      "Difficulty losing weight",
      "Mood changes and fatigue",
      "Difficulty conceiving",
      "Darkening of skin in body folds (acanthosis nigricans)",
    ],
    whatWeOffer: [
      "Complete PCOS workup: LH, FSH, AMH, DHEAS, prolactin, fasting insulin, HbA1c, androgens",
      "PCOS phenotype classification (A, B, C, or D per Rotterdam criteria)",
      "Insulin-sensitising therapy including metformin where indicated",
      "Inositol supplementation guidance with evidence-based dosing",
      "Fertility-supportive consultation for patients trying to conceive",
      "Skin and hair management alongside hormonal treatment",
    ],
    stats: [
      { numeral: "19.6%", caption: "prevalence in Indian women (Ganie 2024)" },
      { numeral: "4", caption: "PCOS phenotypes requiring different clinical approaches" },
      { numeral: "12M+", caption: "Indian women potentially affected" },
    ],
    faqs: [
      {
        question: "What is the difference between PCOS and PCOD?",
        answer:
          "PCOS (polycystic ovary syndrome) is a recognised endocrine disorder characterised by hormonal imbalance, metabolic dysfunction, and often polycystic ovaries. PCOD (polycystic ovarian disease) is a colloquial term used in India that often refers to the radiological finding of multiple follicles without the full diagnostic criteria. Your Kyros doctor will use the internationally recognised Rotterdam criteria to assess your specific presentation.",
      },
      {
        question: "Do I need to lose weight before PCOS treatment?",
        answer:
          "No. The instruction to 'lose 5 kg and come back' is medically incomplete. While weight loss can improve insulin sensitivity and hormonal balance, many patients require insulin-sensitising medication, hormonal support, or targeted supplementation regardless of weight. Treatment is based on phenotype, not weight alone.",
      },
      {
        question: "Can PCOS affect fertility?",
        answer:
          "Yes, though most women with PCOS can conceive with appropriate management. Ovulation induction with medication (clomiphene, letrozole) is effective for many patients. Your Kyros doctor will discuss fertility planning as part of your overall care.",
      },
    ],
    schemaName: "Polycystic Ovary Syndrome",
    schemaDescription:
      "A hormonal disorder characterised by irregular ovulation, elevated androgens, and often polycystic ovaries, affecting metabolic and reproductive health.",
    sensitiveCategory: false,
  },
  {
    slug: "skin-and-hair",
    sort:5,
    name: "Skin & Hair",
    image: "/treatments/Skin&Hair.webp",
    ogImage: "/treatments/Skin&Hair.png",
    audience: "all",
    shortDescription: "AGA, adult acne, melasma, and other dermatological conditions.",
    hook: "The mirror has been telling you something for a while.",
    reflectiveClose: "Skin keeps a record. A doctor reads it.",
    heroSubline:
      "Hair loss, adult acne, and melasma are often systemic signals — hormonal, nutritional, or immunological — before they are cosmetic concerns. A Kyros doctor evaluates the cause, not just the surface.",
    symptoms: [
      "Diffuse hair thinning or hairline recession",
      "Adult acne, especially hormonal pattern along jawline and chin",
      "Melasma or pigmentation changes",
      "Scalp inflammation or dandruff",
      "Brittle nails alongside hair changes",
      "Facial hair in women",
    ],
    whatWeOffer: [
      "Hormonal workup for hair loss: androgens, DHEAS, thyroid panel, ferritin, zinc",
      "AGA (androgenetic alopecia) diagnosis and supervised minoxidil/finasteride management",
      "Adult acne evaluation and treatment: topical retinoids, hormonal agents where indicated",
      "Melasma management with sun protection and evidence-based topicals",
      "Longitudinal photographic tracking of treatment response",
    ],
    stats: [
      { numeral: "58%", caption: "AGA prevalence in Indian men aged 30–50" },
      { numeral: "25–35%", caption: "adult acne prevalence in 25–35 age cohort" },
      { numeral: "1 doctor", caption: "who tracks your skin alongside your labs" },
    ],
    faqs: [
      {
        question: "Is hair loss always hormonal?",
        answer:
          "Not always, but hormonal factors — particularly androgens, thyroid dysfunction, and iron deficiency — are among the most common and most treatable causes in Indian patients. Before starting any hair loss treatment, a complete workup including ferritin, DHEAS, and thyroid panel is appropriate.",
      },
      {
        question: "Is finasteride safe for women?",
        answer:
          "Finasteride is not approved for use in premenopausal women who may become pregnant, due to teratogenicity risk. In postmenopausal women or women with reliable contraception, it is used off-label under close medical supervision. Your Kyros doctor will assess your specific situation.",
      },
      {
        question: "Can Kyros manage melasma?",
        answer:
          "Yes. Melasma management involves a combination of broad-spectrum photoprotection, topical agents (hydroquinone, azelaic acid, tranexamic acid), and in some cases, systemic tranexamic acid under supervision. Kyros doctors do not prescribe or manage in-clinic procedures (peels, lasers).",
      },
    ],
    schemaName: "Androgenetic Alopecia",
    schemaDescription:
      "A pattern of hair loss driven by androgenic hormones, often with underlying metabolic or nutritional factors requiring clinical evaluation and management.",
    sensitiveCategory: false,
  },
  {
    slug: "mens-intimate-health",
    sort:6,
    name: "Men's Intimate Health",
    image: "/treatments/Wellness.webp",
    ogImage: "/treatments/Wellness.png",
    audience: "men",
    shortDescription: "ED, premature ejaculation, and related sexual health evaluation.",
    hook: "Most Indian men carry this in silence for years. The silence is the worst part.",
    reflectiveClose: "There's no version of waiting that helps.",
    heroSubline:
      "Erectile dysfunction and related conditions are often the first sign of a metabolic or hormonal story. A Kyros doctor evaluates the underlying cause — cardiovascular, hormonal, psychological — and builds a clinical plan.",
    symptoms: [
      "Difficulty achieving or maintaining an erection",
      "Reduced sexual desire",
      "Premature ejaculation",
      "Fatigue and low energy",
      "Mood changes",
      "Reduced morning erections",
    ],
    whatWeOffer: [
      "Clinical evaluation of erectile dysfunction including cardiovascular and hormonal workup",
      "Assessment of testosterone, prolactin, and metabolic markers",
      "Evidence-based pharmacological management where clinically indicated",
      "Lifestyle and metabolic intervention alongside medical management",
      "Private, stigma-free consultation with specialist doctors",
    ],
    stats: [
      { numeral: "30–40%", caption: "prevalence of ED in urban Indian men aged 40+" },
      { numeral: "1 consultation", caption: "is all it takes to begin an honest evaluation" },
      { numeral: "100%", caption: "private — no condition names in notifications" },
    ],
    faqs: [
      {
        question: "Is erectile dysfunction always a psychological problem?",
        answer:
          "No. While psychological factors (stress, anxiety, relationship issues) can contribute, most ED in men over 40 has a vascular, hormonal, or metabolic component. A proper evaluation distinguishes between organic and psychogenic causes, which determines the most effective treatment.",
      },
      {
        question: "Will my family know what condition I am consulting for?",
        answer:
          "No. Kyros uses generic notification language ('Your consultation is confirmed') and never includes condition names in any push notification, SMS, or WhatsApp message. You can also set an app passcode for additional device-level privacy.",
      },
      {
        question: "Do I need to see a urologist instead?",
        answer:
          "Not initially. Most men presenting with ED benefit from an initial medical evaluation to identify contributing factors. If a specialist urological or surgical intervention is indicated, your Kyros doctor will refer you with a clear clinical summary.",
      },
    ],
    schemaName: "Erectile Dysfunction",
    schemaDescription:
      "A condition involving the inability to achieve or maintain an erection sufficient for sexual intercourse, often related to vascular, hormonal, or metabolic factors.",
    sensitiveCategory: true,
  },
  {
    slug: "hormones-trt",
    sort:7,
    name: "Hormones & TRT",
    image: "/treatments/TRT.webp",
    ogImage: "/treatments/TRT.png",
    audience: "men",
    shortDescription: "Low testosterone, hormonal imbalance, and supervised TRT.",
    hook: "You don't recognise the man in the photographs anymore.",
    reflectiveClose: "Slowing down is universal. Disappearing isn't.",
    heroSubline:
      "Low testosterone in Indian men is common, underdiagnosed, and routinely misattributed to stress or age. A Kyros doctor evaluates free testosterone, SHBG, and the full hormonal picture before any treatment decision.",
    symptoms: [
      "Persistent fatigue and low energy",
      "Reduced muscle mass despite regular exercise",
      "Mood changes, irritability, or low motivation",
      "Reduced libido",
      "Difficulty concentrating",
      "Increased body fat, especially abdominal",
      "Poor sleep quality",
    ],
    whatWeOffer: [
      "Complete hormonal panel: total testosterone, free testosterone, SHBG, LH, FSH, prolactin, oestradiol",
      "Diagnosis of testosterone deficiency syndrome (TDS) by clinical criteria",
      "Supervised testosterone replacement therapy (TRT) where indicated",
      "Monitoring for TRT side effects: haematocrit, PSA, lipids",
      "Fertility preservation counselling before starting TRT",
    ],
    stats: [
      { numeral: "48.18%", caption: "symptomatic TDS in Indian men ≥40 (Yadav 2019)" },
      { numeral: "Free T", caption: "the measure that matters most, not total testosterone" },
      { numeral: "1 doctor", caption: "who tracks your hormonal panel over time" },
    ],
    faqs: [
      {
        question: "My total testosterone is in the normal range. Can I still have low testosterone?",
        answer:
          "Yes. Total testosterone does not account for the bioavailable fraction. Free testosterone and SHBG (sex hormone-binding globulin) determine how much testosterone is actually available to tissues. Many symptomatic patients have normal total testosterone but low free testosterone.",
      },
      {
        question: "Does TRT cause infertility?",
        answer:
          "Exogenous testosterone suppresses the HPG axis, reducing sperm production. Men who wish to preserve fertility should discuss this with their Kyros doctor before starting TRT. Alternatives that maintain fertility (clomiphene, hCG) may be appropriate.",
      },
      {
        question: "How long does TRT take to work?",
        answer:
          "Most patients notice improvement in energy and mood within 3 to 6 weeks. Improvements in muscle mass and body composition take 3 to 6 months. Full response assessment requires a 6-month evaluation with regular bloodwork.",
      },
    ],
    schemaName: "Male Hypogonadism",
    schemaDescription:
      "A condition characterised by insufficient testosterone production, causing fatigue, reduced libido, mood changes, and metabolic effects in men.",
    sensitiveCategory: true,
  },
  {
    slug: "longevity",
    sort:8,
    name: "Longevity",
    image: "/treatments/Longevity.webp",
    ogImage: "/treatments/Longevity.png",
    audience: "all",
    shortDescription: "Cardiometabolic panels, biomarker monitoring, and preventive care.",
    hook: "Your body has been keeping score. You can read it.",
    reflectiveClose: "The best time to read the chart is before it tells a story.",
    heroSubline:
      "Longevity medicine is not about age reversal. It is about reading the data early — ApoB, Lp(a), fasting insulin, VO2 max — and acting on what the numbers say before they become diagnoses.",
    symptoms: [
      "Interest in comprehensive preventive health evaluation",
      "Family history of cardiovascular disease or metabolic conditions",
      "Curiosity about advanced biomarkers beyond a standard annual check-up",
      "Wearable data (heart rate variability, VO2 max) without clinical interpretation",
      "Fatigue and cognitive changes unexplained by routine tests",
    ],
    whatWeOffer: [
      "Cardiometabolic panel: ApoB, Lp(a), hs-CRP, fasting insulin, HOMA-IR, HbA1c",
      "Comprehensive thyroid and hormonal assessment",
      "VO2 max estimation and cardiovascular fitness evaluation",
      "Longitudinal biomarker tracking with doctor commentary at every retest",
      "Evidence-based preventive interventions: statin therapy, lifestyle modifications",
    ],
    stats: [
      { numeral: "ApoB", caption: "predicts cardiovascular risk better than LDL alone" },
      { numeral: "Lp(a)", caption: "inherited risk factor present in 20% of the population" },
      { numeral: "10+ years", caption: "biomarker changes precede cardiovascular events" },
    ],
    faqs: [
      {
        question: "Why is ApoB more important than LDL for cardiovascular risk?",
        answer:
          "LDL-C measures the cholesterol content of LDL particles. ApoB measures the number of atherogenic particles — each LDL, VLDL, and IDL particle carries one ApoB molecule. Particle number is a stronger predictor of cardiovascular risk than cholesterol mass. Many patients with 'normal' LDL have elevated ApoB.",
      },
      {
        question: "What is Lp(a) and why should I test for it?",
        answer:
          "Lipoprotein(a) is a genetically determined atherogenic particle that standard lipid panels do not measure. Elevated Lp(a) is present in approximately 1 in 5 people and significantly increases cardiovascular risk. It is tested once — it is largely inherited and does not change with lifestyle.",
      },
      {
        question: "Is Kyros's longevity programme just for older patients?",
        answer:
          "No. Preventive biomarker evaluation is most valuable in the 30s and 40s, when intervention options are broadest and the risk timeline is longest. The longevity programme at Kyros is designed for patients who want to understand their data now, not after an event.",
      },
    ],
    schemaName: "Preventive Care",
    schemaDescription:
      "Comprehensive preventive health evaluation using advanced cardiometabolic, hormonal, and metabolic biomarkers to identify and address risk factors before they become clinical conditions.",
    sensitiveCategory: false,
  },
  {
    slug: "diabetes",
    sort:1,
    name: "Diabetes",
    image: "/treatments/Diabetes.webp",
    ogImage: "/treatments/Diabetes.png",
    audience: "all",
    shortDescription: "Prediabetes, type 2 diabetes, and ongoing blood sugar management.",
    hook: "A borderline reading. A doctor who said 'keep an eye on it.' Nobody followed up.",
    reflectiveClose: "Watching a number isn't a plan. Reading it with someone who stays is.",
    heroSubline:
      "Fasting glucose, post-meal spikes, HbA1c — a single number rarely tells the full story, and 'keep an eye on it' isn't a plan. A Kyros doctor reads your metabolic picture in full and stays with you as it changes.",
    symptoms: [
      "Increased thirst and frequent urination",
      "Persistent fatigue or low energy",
      "Unexplained weight changes",
      "Blurred vision",
      "Slow-healing cuts, wounds, or frequent infections",
      "Tingling, numbness, or a burning sensation in the hands or feet",
      "Increased hunger alongside weight loss",
      "A borderline or elevated reading on a routine blood test",
    ],
    whatWeOffer: [
      "Complete metabolic workup: fasting glucose, post-meal glucose, HbA1c, fasting insulin, and lipid panel",
      "Evaluation and staging of prediabetes and type 2 diabetes against standard diagnostic criteria",
      "Doctor-supervised glucose-lowering therapy, including metformin where indicated, reviewed and adjusted at every consultation",
      "Personalised nutrition and activity guidance alongside medical management",
      "Coordination with related metabolic evaluation — weight, thyroid, and cardiometabolic risk — where indicated",
      "Longitudinal blood sugar and biomarker tracking with doctor commentary across every consultation",
    ],
    stats: [
      { numeral: "101M+", caption: "Indians estimated to be living with diabetes (Anjana et al., ICMR-INDIAB, 2023)" },
      { numeral: "136M+", caption: "Indians estimated to have prediabetes (Anjana et al., ICMR-INDIAB, 2023)" },
      { numeral: "1 doctor", caption: "who reads your glucose trend over time, not just one report" },
    ],
    faqs: [
      {
        question: "What is the difference between prediabetes and type 2 diabetes?",
        answer:
          "Prediabetes means blood sugar levels are higher than the typical reference range but not yet at the threshold used to diagnose diabetes. It is a meaningful window — many people at this stage benefit from early medical guidance and structured lifestyle changes. Type 2 diabetes is identified using specific fasting glucose, post-meal glucose, or HbA1c thresholds. Your Kyros doctor will determine where you stand and what it means for your care plan.",
      },
      {
        question: "Can lifestyle changes alone manage blood sugar?",
        answer:
          "For some people with prediabetes or early type 2 diabetes, structured nutrition and activity changes — guided by a doctor and tracked against lab values — can meaningfully support blood sugar management. For others, medical therapy alongside lifestyle change is necessary. Which applies to you depends on your specific labs, history, and your doctor's evaluation, not a one-size-fits-all answer.",
      },
      {
        question: "Is metformin the only medication used for blood sugar management?",
        answer:
          "No. Metformin is one of several glucose-lowering options a doctor may consider, depending on your overall profile, other health conditions, and how your body responds over time. Your Kyros doctor reviews your complete picture before recommending any therapy and adjusts the plan based on your follow-up labs.",
      },
      {
        question: "Can I consult a Kyros doctor if I'm already on medication for diabetes?",
        answer:
          "Yes. Many patients come to Kyros already on glucose-lowering medication without a recent comprehensive review. We assess your current plan, order updated labs, and work with you on adjustments where indicated — with the same doctor following your trend over time.",
      },
    ],
    schemaName: "Type 2 Diabetes Mellitus",
    schemaDescription:
      "A chronic metabolic condition in which the body is unable to regulate blood glucose effectively, requiring ongoing monitoring, lifestyle management, and medical supervision to reduce long-term health risks.",
    sensitiveCategory: false,
  },
];
CONDITIONS.sort((a, b) => a.sort - b.sort);
export function getCondition(slug: string): ConditionData | undefined {
  return CONDITIONS.find((c) => c.slug === slug);
}

export const CONDITION_SLUGS = CONDITIONS.map((c) => c.slug);
