"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "framer-motion";
import {
  ArrowRight,
  Search,
  Check,
  Plus,
  FileText,
  ArrowUpRight,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import PublicHeader, { recruiterUrl } from "@/components/layout/PublicHeader";
import PublicFooter from '@/components/layout/PublicFooter';

const categories = [
  "Engineering",
  "Finance",
  "Marketing",
  "Customer Service",
  "Operations",
  "Human Resources",
  "Sales",
  "Data Analysis",
];
const examples = [
  {
    role: "Data Analyst",
    skills: ["Excel", "SQL", "Communication"],
    location: "Accra · Hybrid",
  },
  {
    role: "Operations Coordinator",
    skills: ["Excel", "Organisation", "Communication"],
    location: "Accra · On-site",
  },
  {
    role: "Customer Success Associate",
    skills: ["Communication", "Problem solving", "Organisation"],
    location: "Remote",
  },
];
const skills = [
  "Excel",
  "SQL",
  "Communication",
  "Organisation",
  "Problem solving",
];

export default function HomePage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const hero = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: hero,
    offset: ["start start", "end start"],
  });
  const photoY = useTransform(scrollYProgress, [0, 1], [0, 45]);
  const captionY = useTransform(scrollYProgress, [0, 1], [0, -28]);
  const [selected, setSelected] = useState(["Excel", "Communication"]);
  const ranked = examples
    .map((job) => ({
      ...job,
      matched: job.skills.filter((skill) => selected.includes(skill)),
    }))
    .sort((a, b) => b.matched.length - a.matched.length);

  useEffect(() => {
    if (!loading && isAuthenticated) router.replace("/dashboard");
  }, [loading, isAuthenticated, router]);

  return (
    <div className="vh-site">
      <PublicHeader />
      <main id="main-content">
        <section ref={hero} className="vh-wrap vh-hero" data-sc-act="flow">
          <div className="vh-hero-copy">
            <p className="vh-eyebrow">YOUR NEXT CHAPTER</p>
            <h1>
              Good work.
              <br />A better fit.
            </h1>
            <p className="vh-lead">
              Explore jobs in Ghana and beyond. Use your CV and career profile
              to find opportunities that fit your experience.
            </p>
            <form action="/jobs" className="vh-hero-search" role="search">
              <label>
                <Search size={20} />
                <span className="sr-only">Job title or keyword</span>
                <input name="q" placeholder="What work are you looking for?" />
              </label>
              <button type="submit" className="vh-button">
                Browse jobs <ArrowRight size={17} />
              </button>
            </form>
            <p className="vh-hero-note">
              Free to browse. Your next step is yours to choose.
            </p>
          </div>
          <div className="vh-hero-scene">
            <div className="vh-photo-ground" aria-hidden="true" />
            <motion.div
              className="vh-hero-photo"
              style={{ y: reduce ? 0 : photoY }}
            >
              <Image
                src="/landing/candidate-at-work.jpg"
                alt="A professional exploring opportunities at her laptop"
                width={1200}
                height={675}
                priority
                sizes="(max-width: 760px) 100vw, 48vw"
              />
            </motion.div>
            <motion.div
              className="vh-photo-caption"
              style={{ y: reduce ? 0 : captionY }}
            >
              <span className="vh-caption-icon">
                <ArrowUpRight size={22} />
              </span>
              <div>
                <strong>A career that moves with you.</strong>
                <span>Local opportunities. Remote possibilities.</span>
              </div>
            </motion.div>
          </div>
        </section>

        <section className="vh-directory" data-sc-act="flow">
          <div className="vh-wrap vh-directory-grid">
            <div>
              <h2>
                Where would you
                <br />
                like to go next?
              </h2>
              <p>
                Start with the work you know.
                <br />
                Explore what comes next.
              </p>
            </div>
            <div className="vh-category-links">
              {categories.map((category) => (
                <Link
                  key={category}
                  href={"/jobs?q=" + encodeURIComponent(category)}
                >
                  {category}
                  <ArrowUpRight size={16} />
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section
          id="how-it-works"
          className="vh-wrap vh-match-section"
          data-sc-act="flow"
        >
          <div className="vh-section-intro">
            <p className="vh-eyebrow">MAKE YOUR EXPERIENCE COUNT</p>
            <h2>
              A shortlist with
              <br />a reason behind it.
            </h2>
            <p>
              Your profile helps us connect your experience to the requirements
              of each role. See what fits, then decide where to focus.
            </p>
            <Link href="/auth/signup" className="vh-text-link">
              Create account <ArrowRight size={17} />
            </Link>
          </div>
          <motion.div
            className="vh-match-demo"
            initial={reduce ? false : { clipPath: "inset(0 0 8% 0)" }}
            whileInView={{ clipPath: "inset(0 0 0% 0)" }}
            viewport={{ once: true, amount: 0.15 }}
            transition={{ duration: 0.5 }}
          >
            <div className="vh-demo-heading">
              <strong>Find the connection</strong>
              <span>Interactive example</span>
            </div>
            <p className="vh-demo-instruction">
              Choose a few skills. Watch the shortlist change.
            </p>
            <div className="vh-skill-picker" aria-label="Example skills">
              {skills.map((skill) => (
                <button
                  key={skill}
                  aria-pressed={selected.includes(skill)}
                  onClick={() =>
                    setSelected((current) =>
                      current.includes(skill)
                        ? current.filter((value) => value !== skill)
                        : [...current, skill],
                    )
                  }
                >
                  {selected.includes(skill) ? (
                    <Check size={14} />
                  ) : (
                    <Plus size={14} />
                  )}
                  {skill}
                </button>
              ))}
            </div>
            <div className="vh-demo-results" aria-live="polite">
              {ranked.map((job, index) => (
                <motion.article
                  layout={!reduce}
                  transition={{ duration: 0.22 }}
                  key={job.role}
                  className={
                    index === 0 && job.matched.length
                      ? "vh-example-job vh-example-top"
                      : "vh-example-job"
                  }
                >
                  <div className="vh-example-job-head">
                    <h3>{job.role}</h3>
                    <span>
                      {job.matched.length} of {job.skills.length} skills
                    </span>
                  </div>
                  <p>{job.location}</p>
                  <div className="vh-example-skills">
                    {job.skills.map((skill) => (
                      <span
                        key={skill}
                        className={selected.includes(skill) ? "is-matched" : ""}
                      >
                        {selected.includes(skill) && <Check size={12} />}
                        {skill}
                      </span>
                    ))}
                  </div>
                </motion.article>
              ))}
            </div>
            <div className="vh-demo-foot">
              <p>
                Illustrative roles, not live vacancies. Your actual matches also
                consider your CV and experience.
              </p>
              <Link href={"/jobs?q=" + encodeURIComponent(ranked[0].role)}>
                Search {ranked[0].role} jobs <ArrowUpRight size={15} />
              </Link>
            </div>
          </motion.div>
        </section>

        <section className="vh-preparation" data-sc-act="flow">
          <div className="vh-wrap vh-prep-grid">
            <motion.div
              initial={reduce ? false : { y: 16 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
              className="vh-prep-photo"
            >
              <Image
                src="/landing/jobseekers-smiling.jpg"
                alt="Two professionals in a shared workplace"
                width={1600}
                height={1200}
                sizes="(max-width: 760px) 100vw, 42vw"
              />
            </motion.div>
            <div>
              <FileText size={28} strokeWidth={1.4} className="vh-prep-icon" />
              <h2>
                Your experience.
                <br />
                In your own words.
              </h2>
              <p>
                When you find a role worth applying for, create a tailored CV
                from your existing one. Review it, make changes, and take a
                version you are happy to send.
              </p>
              <ul className="vh-plain-list">
                <li>
                  <Check size={17} /> An editable draft for each role
                </li>
                <li>
                  <Check size={17} /> Your original CV stays intact
                </li>
                <li>
                  <Check size={17} /> Review and download when you are ready
                </li>
              </ul>
              <Link href="/auth/signup" className="vh-text-link">
                Create account <ArrowRight size={17} />
              </Link>
            </div>
          </div>
        </section>

        <section className="vh-wrap vh-help">
          <h2>A few things to know.</h2>
          <div>
            {[
              [
                "Do I need an account to apply?",
                "No. You can browse jobs and follow the application link without an account. Create a profile for recommendations, saved jobs, and tailored CVs.",
              ],
              [
                "Where do the jobs come from?",
                "VeloxaHire brings together roles posted by recruiters and listings from external job boards. Each role links to its application destination.",
              ],
              [
                "Will you apply for me?",
                "You choose which roles to pursue. Review the job and your CV, then follow the application link to the employer or source site.",
              ],
            ].map(([question, answer]) => (
              <details key={question}>
                <summary>
                  {question}
                  <Plus size={18} />
                </summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="vh-close" data-sc-act="flow">
          <div className="vh-wrap">
            <div>
              <h2>There is more ahead of you.</h2>
              <p>Find the work you want to do next.</p>
            </div>
            <Link href="/jobs" className="vh-button">
              Browse jobs <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </main>
      <PublicFooter />
    </div>
  );
}
