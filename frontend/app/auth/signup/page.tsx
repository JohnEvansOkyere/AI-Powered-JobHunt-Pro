"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import PublicHeader from "@/components/layout/PublicHeader";
import { requestPhoneOtp, saveContactEmail, verifyPhoneOtp } from "@/lib/auth";
import { apiClient } from "@/lib/api/client";
import { toast } from "react-hot-toast";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Mail,
  Phone,
  ShieldCheck,
  User,
} from "lucide-react";
import { motion } from "framer-motion";
import AuthBrandPanel from "@/components/auth/AuthBrandPanel";
import { trackEvent } from "@/lib/analytics";

interface HandoffVerifyResponse {
  valid: boolean;
  email?: string | null;
  full_name?: string | null;
  phone?: string | null;
  job_id?: string | null;
}

const handoffVerifyCache = new Map<string, Promise<HandoffVerifyResponse>>();

function verifyHandoffToken(token: string) {
  const cached = handoffVerifyCache.get(token);
  if (cached) return cached;
  const request = apiClient.post<HandoffVerifyResponse>(
    "/auth/handoff/verify",
    { token },
  );
  handoffVerifyCache.set(token, request);
  return request;
}

const inputCls =
  "block w-full rounded-xl border border-neutral-200 bg-white py-3.5 pl-11 pr-4 text-sm font-medium text-neutral-900 outline-none transition-all placeholder:text-neutral-400 focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20";

function SignUpContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"details" | "verify">("details");
  const [handoffEmail, setHandoffEmail] = useState<string | null>(null);
  const [handoffJobId, setHandoffJobId] = useState<string | null>(null);
  const [handoffPrefilled, setHandoffPrefilled] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = searchParams.get("h");
    if (!token) return;
    let cancelled = false;
    verifyHandoffToken(token)
      .then((result) => {
        if (cancelled || !result.valid) return;
        if (result.full_name) setFullName(result.full_name);
        if (result.phone) setPhone(result.phone);
        if (result.email) {
          setHandoffEmail(result.email);
          setEmail(result.email);
        }
        if (result.job_id) setHandoffJobId(result.job_id);
        setHandoffPrefilled(Boolean(result.full_name || result.phone || result.email));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  const sendCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      void trackEvent({ event_name: "signup_started", path: "/auth/signup" });
      const result = await requestPhoneOtp({
        phone,
        shouldCreateUser: true,
        metadata: {
          full_name: fullName.trim(),
          contact_email: email.trim().toLowerCase(),
          handoff_email: handoffEmail || undefined,
          source: handoffPrefilled ? "veloxarecruit_apply_handoff" : undefined,
          ats_job_id: handoffJobId || undefined,
        },
      });
      setNormalizedPhone(result.phone);
      setStep("verify");
      toast.success("Verification code sent by SMS.");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Could not send the verification code.",
      );
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      toast.error("Enter the six-digit verification code.");
      return;
    }
    setLoading(true);
    try {
      const result = await verifyPhoneOtp(normalizedPhone, code);
      if (!result.session)
        throw new Error("Phone verified, but no session was created.");
      await saveContactEmail(email);
      void trackEvent({
        event_name: "signup_completed",
        path: "/auth/signup",
        metadata: { handoff: handoffPrefilled, method: "phone_otp" },
      });
      toast.success("Phone verified. Your account is ready.");
      router.push("/dashboard");
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "The code is invalid or expired.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vh-auth">
      <PublicHeader />
      <main id="main-content" className="vh-auth-body">
        <AuthBrandPanel variant="signup" />
        <div className="vh-auth-form">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto w-full max-w-[440px]"
          >
            <h1 className="text-3xl font-bold tracking-tight text-neutral-900">
              {step === "verify"
                ? "Verify your phone"
                : handoffPrefilled
                  ? "Finish your account"
                  : "Create your free account"}
            </h1>
            <p className="mt-2 text-neutral-500">
              {step === "verify"
                ? `Enter the code sent to ${normalizedPhone}.`
                : "Add your email, then verify your phone by SMS. No password to create or remember."}
            </p>

            {handoffPrefilled && step === "details" && (
              <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3.5 py-2.5 text-sm font-medium text-emerald-700">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" /> Application
                details imported from VeloxaRecruit
              </div>
            )}

            {step === "details" ? (
              <form
                method="post"
                className="mt-8 space-y-5"
                onSubmit={sendCode}
              >
                <div>
                  <label
                    htmlFor="fullName"
                    className="mb-1.5 block text-sm font-medium text-neutral-700"
                  >
                    Full name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      id="fullName"
                      name="fullName"
                      required
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className={inputCls}
                      placeholder="Ama Mensah"
                      autoComplete="name"
                    />
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="email"
                    className="mb-1.5 block text-sm font-medium text-neutral-700"
                  >
                    Email address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className={inputCls}
                      placeholder="you@example.com"
                      autoComplete="email"
                      inputMode="email"
                    />
                  </div>
                  <p className="mt-1.5 text-xs text-neutral-400">
                    We’ll use this for application updates and email alerts.
                  </p>
                </div>
                <div>
                  <label
                    htmlFor="phone"
                    className="mb-1.5 block text-sm font-medium text-neutral-700"
                  >
                    Telephone number
                  </label>
                  <div className="relative">
                    <Phone className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      id="phone"
                      name="phone"
                      type="tel"
                      required
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                      className={inputCls}
                      placeholder="024 123 4567"
                      autoComplete="tel"
                      inputMode="tel"
                    />
                  </div>
                  <p className="mt-1.5 text-xs text-neutral-400">
                    We will send a one-time verification code by SMS.
                  </p>
                </div>
                <button
                  type="submit"
                  disabled={loading || !fullName.trim() || !email.trim() || !phone.trim()}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-turquoise-500/20 transition-all hover:bg-brand-turquoise-700 disabled:opacity-60"
                >
                  {loading ? "Sending code…" : "Send verification code"}{" "}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
              </form>
            ) : (
              <form
                method="post"
                className="mt-8 space-y-5"
                onSubmit={verifyCode}
              >
                <div>
                  <label
                    htmlFor="code"
                    className="mb-1.5 block text-sm font-medium text-neutral-700"
                  >
                    Six-digit code
                  </label>
                  <div className="relative">
                    <ShieldCheck className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      id="code"
                      name="code"
                      required
                      value={code}
                      onChange={(event) =>
                        setCode(
                          event.target.value.replace(/\D/g, "").slice(0, 6),
                        )
                      }
                      className={`${inputCls} tracking-[0.35em]`}
                      placeholder="000000"
                      autoComplete="one-time-code"
                      inputMode="numeric"
                      pattern="[0-9]{6}"
                      maxLength={6}
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={loading || code.length !== 6}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-turquoise-500/20 transition-all hover:bg-brand-turquoise-700 disabled:opacity-60"
                >
                  {loading ? "Verifying…" : "Verify and continue"}{" "}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    setStep("details");
                    setCode("");
                  }}
                  className="inline-flex w-full items-center justify-center gap-2 py-2 text-sm font-semibold text-neutral-500 hover:text-neutral-800"
                >
                  <ArrowLeft className="h-4 w-4" /> Change phone number
                </button>
              </form>
            )}

            <div className="mt-8 flex items-center justify-between border-t border-neutral-200 pt-6 text-sm text-neutral-500">
              <span>
                Already a member?{" "}
                <Link
                  href="/auth/login"
                  className="font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800"
                >
                  Sign in
                </Link>
              </span>
              <Link
                href="/jobs"
                className="transition-colors hover:text-neutral-800"
              >
                Browse jobs →
              </Link>
            </div>
            <p className="mt-4 text-xs text-neutral-400">
              By creating an account you agree to our{" "}
              <Link href="/terms" className="underline hover:text-neutral-600">
                Terms
              </Link>{" "}
              and{" "}
              <Link
                href="/privacy"
                className="underline hover:text-neutral-600"
              >
                Privacy Policy
              </Link>
              .
            </p>
          </motion.div>
        </div>
      </main>
    </div>
  );
}

export default function SignUpPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-cream-50" />}>
      <SignUpContent />
    </Suspense>
  );
}
