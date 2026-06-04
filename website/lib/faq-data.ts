export interface FAQ {
    q: string;
    a: string;
}

export interface FAQSection {
    id: string;
    title: string;
    items: FAQ[];
}

export const FAQ_DATA: FAQSection[] = [

    {
        id: "getting-started",
        title: "Getting started",
        items: [
            {
                q: "How is Kyros different from other Indian telemedicine platforms?",
                a: "Most Indian telemedicine today is built around pharmacy logistics — the goal is to get medicine to your door. Kyros is built around the doctor. The same specialist sees you across consultations and follow-ups. Your dashboard tracks lab trends, dosage history, and treatment over time. Treatment is prescribed only when clinically appropriate, never as the default.",
            },
            {
                q: "How long does the whole process take, from filling the form to seeing a doctor?",
                a: "Our care coordinator will call you within 24 hours. From there, we typically schedule your video consultation within 1 to 2 days, depending on your specialist's availability.",
            },
            {
                q: "Do I have to know which specialist I need before signing up?",
                a: "No. That is what our care coordinator is for. Tell us your symptoms in the intake form, and we will match you with the correct specialist during your initial call.",
            },
            {
                q: "Can my parents, partner, or child use my Kyros account?",
                a: "No. Because your dashboard acts as your personal, longitudinal health record, every adult must have their own individual account to ensure clinical safety and data privacy.",
            },
        ],
    },
    {
        id: "about-doctor",
        title: "About your doctor",
        items: [
            {
                q: "Are Kyros doctors actually qualified, or are they recent graduates?",
                a: "Every doctor on Kyros is registered with the NMC or their State Medical Council, has at least 5 years of post-MBBS clinical practice, and is specialty-qualified for the conditions they treat.",
            },
            {
                q: "Will I see the same doctor every time?",
                a: "That is the intention. After your first consultation, follow-ups are scheduled with the same specialist. In the rare case of unavailability, your full case notes are seamlessly passed to a covering specialist.",
            },
            {
                q: "What if I want to change my doctor?",
                a: "You can request a change through your care coordinator at any time. Your longitudinal dashboard moves with you, so you never have to start your story over from scratch.",
            },
            {
                q: "Can my doctor see my previous medical records from outside Kyros?",
                a: "Yes. You can securely upload previous lab results, prescriptions, and scans to your dashboard before your consultation for your doctor to review.",
            },
            {
                q: "What if my doctor recommends I see someone in person?",
                a: "If your condition requires physical examination or acute care, your doctor will explicitly refer you to an in-person clinic. We prioritize your health and safety over keeping you on the platform.",
            },
        ],
    },
    {
        id: "conditions",
        title: "Conditions we treat",
        items: [
            {
                q: "Does Kyros treat low testosterone (Low T)?",
                a: "Yes. Our specialists evaluate symptoms, medical history, and laboratory results to identify potential causes of low testosterone and recommend evidence-based treatment when clinically appropriate.",
            },
            {
                q: "Does Kyros treat thyroid disorders?",
                a: "Yes. We help patients with hypothyroidism, hyperthyroidism, Hashimoto's thyroiditis, thyroid-related symptoms, and long-term thyroid medication management.",
            },
            {
                q: "Can Kyros help with PCOS?",
                a: "Yes. Our specialists provide comprehensive PCOS care including symptom assessment, hormone evaluation, weight management, fertility-related guidance, and long-term monitoring.",
            },
            {
                q: "Does Kyros treat hair loss?",
                a: "Yes. We evaluate medical causes of hair loss including hormonal conditions, nutritional deficiencies, thyroid disorders, and genetic factors before recommending treatment.",
            },
            {
                q: "Can Kyros help with weight loss?",
                a: "Yes. We provide medically supervised weight-management programs that may include lifestyle interventions, laboratory evaluation, and prescription medications when clinically appropriate.",
            },
            {
                q: "Do you treat erectile dysfunction?",
                a: "Yes. Our doctors evaluate underlying causes such as hormonal issues, cardiovascular risk factors, medication effects, and psychological contributors before recommending treatment.",
            }
        ]
    },
    {
        id: "telemedicine",
        title: "Telemedicine and prescriptions",
        items: [
            {
                q: "Are online prescriptions legal in India?",
                a: "Yes. Registered medical practitioners can issue digital prescriptions in accordance with applicable Indian telemedicine guidelines.",
            },
            {
                q: "Can I use my prescription at any pharmacy?",
                a: "Yes. Your prescription belongs to you and can generally be used at any licensed pharmacy that accepts valid digital prescriptions.",
            },
            {
                q: "Do I need to visit a clinic in person?",
                a: "Most consultations can be completed remotely. However, if your doctor determines that a physical examination is necessary, you will be advised to seek in-person care.",
            },
            {
                q: "Can I get a second opinion through Kyros?",
                a: "Yes. You may upload previous medical records, laboratory results, and prescriptions for specialist review.",
            }
        ]
    },
    {
        id: "privacy",
        title: "Privacy and your data",
        items: [
            {
                q: "Where does my health data live? Who can see it?",
                a: "Your data is stored on secure Indian servers and processed strictly under the Digital Personal Data Protection Act, 2023. Only you and your assigned clinical team can access your records.",
            },
            {
                q: "Will my family see my prescription package?",
                a: "No. We use completely discreet packaging. There is no Kyros branding and absolutely no condition-specific labeling on the outside of the delivery box.",
            },
            {
                q: "Can I delete my account and all my data?",
                a: "Yes. You retain full control over your data. You can request access, correction, or complete deletion from your profile settings at any time.",
            },
            {
                q: "Is my data shared with insurance companies, employers, or third parties?",
                a: "Never. We do not sell, rent, or share your personal health data with any third parties, employers, or insurance providers.",
            },
        ],
    },
    {
        id: "payments",
        title: "Payments and pricing",
        items: [
            {
                q: "When do I pay? Before or after the consultation?",
                a: "You pay only when confirming your scheduled consultation slot after speaking with our care coordinator. There is no fee to fill out the intake form or receive the initial triage call.",
            },
            {
                q: "Can I get a refund if I'm not satisfied?",
                a: "If a technical failure prevents your consultation from happening, we provide a full refund. Clinical disagreements are handled on a case-by-case basis through our grievance officer.",
            },
            {
                q: "Do you accept insurance?",
                a: "We do not process insurance directly at this time. However, we provide detailed invoices that you can submit to your insurance provider for reimbursement if your policy covers teleconsultations.",
            },
            {
                q: "Is there a way to use Kyros if I can't afford the full consultation fee?",
                a: "We are currently exploring accessibility programs, but at this stage, our standard specialist consultation fees apply to all patients.",
            },
        ],
    },
    {
        id: "clinical",
        title: "Clinical questions",
        items: [
            {
                q: "What conditions can Kyros actually treat?",
                a: "We focus on chronic and complex conditions that require ongoing care: thyroid health, weight management, PCOS, skin and hair, intimate health, hormones, and longevity and preventive care.",
            },
            {
                q: "What conditions does Kyros not treat?",
                a: "We do not handle medical emergencies, acute trauma, severe psychiatric crises, conditions requiring physical examination, or the prescription of controlled substances.",
            },
            {
                q: "If I'm prescribed medication, do I have to buy from Kyros's pharmacy partner?",
                a: "No. Your prescription is yours. You can use our discreet delivery partner for convenience, or download the IMC-formatted prescription to fulfill at any local pharmacy.",
            },
            {
                q: "What happens if I have a medical emergency between consultations?",
                a: "Kyros is not an emergency service. If you experience acute or worsening symptoms, please visit your nearest hospital casualty ward or call 112 immediately.",
            },
            {
                q: "Can I get lab tests done without a consultation?",
                a: "No. Lab tests on Kyros are specifically ordered by your specialist after an initial consultation to ensure they are clinically relevant to your unique case.",
            },
        ],
    },
];