'use client';

import React, { useState } from 'react';
import { cn } from '../../lib/utils';
import { FAQ_DATA, type FAQ, type FAQSection } from '../../lib/faq-data';
import {CTASection} from "../../components/marketing/CTASection";

const faqData: FAQSection[] = FAQ_DATA;

function FaqItem({
                     item,
                     isFirst,
                     isLast,
                 }: {
    item: FAQ;
    isFirst: boolean;
    isLast: boolean;
}) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div
            className={cn(
                'border-b-[0.5px] border-forest/20 transition-all duration-200',
                isFirst && 'rounded-t-lg',
                isLast && 'rounded-b-lg',
                !isFirst && '-mt-[0.5px]'
            )}
        >
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex justify-between items-center px-6 py-4.5 text-left"
            >
        <span className="clinic-body pr-4 text-ink font-medium">
          {item.q}
        </span>

                <span className="clinic-body text-stone transition-all duration-200 ease-in-out">
          {isOpen ? '−' : '+'}
        </span>
            </button>

            <div
                className={cn(
                    'overflow-hidden clinic-small transition-all duration-300',
                    isOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                )}
            >
                <div className="px-6 pb-5 text-ink leading-[1.7]">
                    {item.a}
                </div>
            </div>
        </div>
    );
}

export default function FaqClient() {
    const [activeSection, setActiveSection] = useState(faqData[0].id);

    const activeData = faqData.find(
        (section) => section.id === activeSection
    );

    return (
        <div className="transition-all duration-300 ease-linear">
            {/* Hero */}
            <div className="pt-16 md:pt-20 px-5 md:px-8 pb-10 max-w-[944px] mx-auto">
                <div className="text-[11px] tracking-[0.08em] uppercase text-stone mb-4.5">
                    Frequently Asked Questions
                </div>

                <h1 className="font-serif text-[clamp(36px,4vw,48px)] text-ink mb-5.5">
                    Things people ask before they start.
                </h1>

                <p className="text-[16px] text-stone leading-[1.7] max-w-[660px]">
                    Questions about consultations, privacy, prescriptions,
                    pricing, and how Kyros works. If something isn't here,
                    write to us at care@kyrosclinic.com.
                </p>
            </div>

            {/* Category Tabs */}
            <div className="px-5 md:px-8 pb-10 max-w-[944px] mx-auto">
                <div className="flex gap-2 flex-wrap">
                    {faqData.map((section) => (
                        <button
                            key={section.id}
                            onClick={() => setActiveSection(section.id)}
                            className={cn(
                                'px-3.5 py-2 rounded-full border cursor-pointer text-[11px] transition',
                                activeSection === section.id
                                    ? 'bg-forest text-white border-forest'
                                    : 'border-forest/40 text-stone hover:text-ink'
                            )}
                        >
                            {section.title}
                        </button>
                    ))}
                </div>
            </div>

            {/* Active FAQ Section */}
            <div className="px-5 md:px-8 max-w-[944px] mx-auto pb-12">
                <h2 className="font-serif text-[22px] text-ink mb-5">
                    {activeData?.title}
                </h2>

                <div className="flex flex-col">
                    {activeData?.items.map((item, index) => (
                        <FaqItem
                            key={item.q}
                            item={item}
                            isFirst={index === 0}
                            isLast={index === activeData.items.length - 1}
                        />
                    ))}
                </div>
            </div>

            {/* CTA */}
            <CTASection

                headline="Still have questions?"

                subline="Our care team is available from 9 AM to 9 PM, Monday to Saturday."

                primaryCta={{ label: 'Contact us', href: '/contact' }}

                secondaryCta={{ label: 'Book a consultation', href: '/book' }}

                variant="ivory"

            />
        </div>
    );
}