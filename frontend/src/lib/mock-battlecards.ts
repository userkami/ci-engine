/**
 * Pre-rendered sample battlecards for the interactive gallery so visitors
 * can explore the UI without spending a credit (BUILD_GUIDE Phase 5).
 * Data below mirrors the shape produced by the LangGraph synthesizer.
 */
import type { BattlecardOutput } from "@/types";

export interface SampleCard {
  slug: string;
  label: string;
  target: string;
  competitor: string;
  description: string;
  card: BattlecardOutput;
}

export const SAMPLE_CARDS: SampleCard[] = [
  {
    slug: "linear-vs-jira",
    label: "Linear vs Jira",
    target: "Linear",
    competitor: "Jira",
    description: "Pricing teardown and churn quotes for Jira Software",
    card: {
      executive_summary:
        "Jira Software undercuts Linear on list price for small teams but layers on per-agent/per-user billing, add-on costs, and aggressive seat minimums that erase the apparent discount by ~25 seats. Atlassian's own review platforms surface recurring complaints about performance lag, slow support, and painful migrations. Lead with total-cost-of-ownership math and Jira's operational drag in the discovery call.",
      swot: {
        strengths: [
          "Deep ecosystem: 3,000+ marketplace apps",
          "Familiar workflows and certification base",
          "Enterprise governance (SCIM, SSO, audit) mature",
        ],
        weaknesses: [
          "Older architecture; sluggish on large boards",
          "Per-user pricing compounds quickly",
          "Complex admin; steep learning curve",
        ],
        opportunities: [
          "Teams over 25 agents feel the pricing pain first",
          "Migrating teams are actively searching for simpler tools",
          "AI features are add-ons, not core — Linear ships them free",
        ],
        threats: [
          "Enterprise procurement inertia and security reviews",
          "Atlassian bundles can be discounted at renewal",
        ],
      },
      pricing: [
        {
          name: "Free",
          price: "$0 (up to 10 users)",
          limitations: [
            "2 GB storage",
            "No advanced roadmaps",
            "No automation rules beyond basic",
          ],
          source_url: "https://www.atlassian.com/software/jira/pricing",
        },
        {
          name: "Standard",
          price: "$7.16/user/mo (billed annually)",
          limitations: [
            "Minimum purchase of ~10 users",
            "No goal feature",
            "Local + cloud storage only",
          ],
          source_url: "https://www.atlassian.com/software/jira/pricing",
        },
        {
          name: "Premium",
          price: "$14.06/user/mo (billed annually)",
          limitations: [
            "Per-user price hits hard past 25 users",
            "Advanced roadmap & sandbox are the only true additions",
          ],
          source_url: "https://www.atlassian.com/software/jira/pricing",
        },
      ],
      churn_drivers: [
        {
          pain_point: "Slowness and performance degradation on large projects",
          exact_quote:
            "After we crossed 30k issues Jira became unusable — board loads took 10+ seconds and we burned hours every week.",
          source_platform: "Reddit r/softwareengineering",
          source_url:
            "https://www.reddit.com/r/softwareengineering/comments/example",
          objection_rebuttal:
            '"At thousands of issues, Jira can feel heavy. Linear was built for that scale — boards, filters and search stay fast because issues are local-first."',
        },
        {
          pain_point: "Per-user pricing makes seats the de-facto tax on growth",
          exact_quote:
            "Atlassian's pricing creep is real. Every new hire costs another $14/mo before you add apps, and managers hate budgeting seats.",
          source_platform: "G2",
          source_url: "https://www.g2.com/products/jira/reviews/example",
          objection_rebuttal:
            '"With Linear you pay a flat per-editor price that includes AI, automations and roadmaps — your cost per user drops as the team grows."',
        },
      ],
      landmine_questions: [
        "What is your all-in seat cost including Marketplace apps today?",
        "How many workflow schemes does your Jira admin currently maintain?",
        "What is your average board load time over 10k issues?",
        "Which AI features did you buy as add-ons vs get included?",
      ],
    },
  },
  {
    slug: "supabase-vs-firebase",
    label: "Supabase vs Firebase",
    target: "Supabase",
    competitor: "Firebase",
    description: "Pricing teardown and churn quotes for Firebase",
    card: {
      executive_summary:
        "Firebase's free Spark plan disappears the moment you exceed 50k MAUs or enable paid features, and the Blaze plan silently bills per-document reads via the pricing calculator. Developers repeatedly cite unpredictable billing, vendor lock-in on proprietary APIs, and painful migrations off Firestore. Lead with migration path, realtime/Postgres wins, and predictable pricing.",
      swot: {
        strengths: [
          "Zero-config SDKs and first-party Auth/Security rules",
          "Generous free tier for prototypes",
          "Strong mobile + iOS/Android integration",
        ],
        weaknesses: [
          "Proprietary Firestore — hard to migrate off",
          "Pricing calculator obscures real cost",
          "Query model limits (no joins, composite filters)",
        ],
        opportunities: [
          "Postgres-backend teams can adopt SQL + realtime",
          "Self-host & region flexibility stage-0 desire",
          "Predictable per-project pricing room",
        ],
        threats: [
          "Google product roadmap risk and deprecated APIs",
          "BigQuery/other Google services extend lock-in",
        ],
      },
      pricing: [
        {
          name: "Spark (Free)",
          price: "$0 — up to 50k MAUs / 1 GiB stored",
          limitations: [
            "No team collaboration",
            "Billing / advanced security require upgrade",
            "Abrupt metering above 50k MAUs",
          ],
          source_url: "https://firebase.google.com/pricing",
        },
        {
          name: "Blaze (Pay as you go)",
          price: "$25/month + usage (per-document reads)",
          limitations: [
            "Cost grows with every read — hard to forecast",
            "50k MAU threshold still caps the free Spark layer",
            "Storage billed per GiB with overage tiers",
          ],
          source_url: "https://firebase.google.com/pricing",
        },
      ],
      churn_drivers: [
        {
          pain_point: "Predictability — the billing calculator hides real costs",
          exact_quote:
            "Our Firestore bill tripled after a feature went viral. Nobody on the team could explain whether the new cost was reads, writes, or storage.",
          source_platform: "Reddit r/Firebase",
          source_url: "https://www.reddit.com/r/Firebase/comments/example",
          objection_rebuttal:
            '"Supabase bills a flat per-project price plus metered compute with clear dashboards — no surprise per-read line items."',
        },
        {
          pain_point: "Vendor lock-in: Firestore is proprietary",
          exact_quote:
            "We wanted to leave GCP for a European host but Firestore's API and rules language make migration a full rewrite, not a port.",
          source_platform: "G2",
          source_url: "https://www.g2.com/products/firebase/reviews/example",
          objection_rebuttal:
            '"Supabase runs on Postgres — you keep SQL access, can self-host, and your data model is portable from day one."',
        },
      ],
      landmine_questions: [
        "What is your projected Firestore read volume per month next quarter?",
        "Which Firebase APIs would you need to keep if you switched?",
        "How many GCP regions currently serve your user base?",
        "Have you already hit the 50k MAU free-tier threshold?",
      ],
    },
  },
];

export function getSampleCard(slug: string): SampleCard | undefined {
  return SAMPLE_CARDS.find((sample) => sample.slug === slug);
}