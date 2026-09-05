"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import PublicHeader from "@/components/layout/PublicHeader";
import { requestPhoneOtp, signIn, verifyPhoneOtp } from "@/lib/auth";
import {
  getRememberSessionPreference,
  setRememberSession,
} from "@/lib/supabase/client";
import { toast } from "react-hot-toast";
import {
  ArrowLeft,
  ArrowRight,
  Lock,
  Mail,
  Phone,
  ShieldCheck,
} from "lucide-react";
import { motion } from "framer-motion";
import AuthBrandPanel from "@/components/auth/AuthBrandPanel";
import { trackEvent } from "@/lib/analytics";

const inputCls =
  "block w-full rounded-xl border border-neutral-200 bg-white py-3.5 pl-11 pr-4 text-sm font-medium text-neutral-900 outline-none transition-all placeholder:text-neutral-400 focus:border-brand-turquoise-500 focus:ring-2 focus:ring-brand-turquoise-500/20";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"phone" | "legacy">("phone");
  const [step, setStep] = useState<"phone" | "verify">("phone");
  const [phone, setPhone] = useState("");
  const [normalizedPhone, setNormalizedPhone] = useState("");
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => setRememberMe(getRememberSessionPreference()), []);

  const finishLogin = () => {
    void trackEvent({
      event_name: "login_completed",
      path: "/auth/login",
      metadata: { method: mode === "phone" ? "phone_otp" : "email_password" },
    });
    toast.success("Logged in successfully!");
    router.push("/dashboard");
  };

  const sendCode = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      void trackEvent({
        event_name: "login_started",
        path: "/auth/login",
        metadata: { method: "phone_otp" },
      });
      const result = await requestPhoneOtp({ phone, shouldCreateUser: false });
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
      setRememberSession(rememberMe);
      const result = await verifyPhoneOtp(normalizedPhone, code);
      if (!result.session)
        throw new Error("Phone verified, but no session was created.");
      finishLogin();
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

  const legacyLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      void trackEvent({
        event_name: "login_started",
        path: "/auth/login",
        metadata: { method: "email_password" },
      });
      await signIn({ email, password, remember: rememberMe });
      finishLogin();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to sign in.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vh-auth">
      <PublicHeader />
      <main id="main-content" className="vh-auth-body">
        <AuthBrandPanel variant="login" />
        <div className="vh-auth-form">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto w-full max-w-[440px]"
          >
            <h1 className="text-3xl font-bold tracking-tight text-neutral-900">
              {step === "verify" ? "Enter your code" : "Welcome back"}
            </h1>
            <p className="mt-2 text-neutral-500">
              {mode === "legacy"
                ? "Sign in to your existing email account."
                : step === "verify"
                  ? `We sent a code to ${normalizedPhone}.`
                  : "Use your verified phone number. No password needed."}
            </p>

            {mode === "phone" && step === "phone" && (
              <form
                method="post"
                className="mt-8 space-y-5"
                onSubmit={sendCode}
              >
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
                </div>
                <RememberField checked={rememberMe} onChange={setRememberMe} />
                <button
                  type="submit"
                  disabled={loading || !phone.trim()}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-turquoise-500/20 transition-all hover:bg-brand-turquoise-700 disabled:opacity-60"
                >
                  {loading ? "Sending code…" : "Send verification code"}{" "}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
              </form>
            )}

            {mode === "phone" && step === "verify" && (
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
                  {loading ? "Verifying…" : "Verify and sign in"}{" "}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    setStep("phone");
                    setCode("");
                  }}
                  className="inline-flex w-full items-center justify-center gap-2 py-2 text-sm font-semibold text-neutral-500 hover:text-neutral-800"
                >
                  <ArrowLeft className="h-4 w-4" /> Change phone number
                </button>
              </form>
            )}

            {mode === "legacy" && (
              <form
                method="post"
                className="mt-8 space-y-5"
                onSubmit={legacyLogin}
              >
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
                      placeholder="you@email.com"
                      autoComplete="email"
                    />
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="password"
                    className="mb-1.5 block text-sm font-medium text-neutral-700"
                  >
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
                    <input
                      id="password"
                      name="password"
                      type="password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className={inputCls}
                      autoComplete="current-password"
                    />
                  </div>
                </div>
                <RememberField checked={rememberMe} onChange={setRememberMe} />
                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-turquoise-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-brand-turquoise-500/20 transition-all hover:bg-brand-turquoise-700 disabled:opacity-60"
                >
                  {loading ? "Signing in…" : "Sign in"}{" "}
                  {!loading && <ArrowRight className="h-4 w-4" />}
                </button>
              </form>
            )}

            {step === "phone" && (
              <button
                type="button"
                onClick={() => setMode(mode === "phone" ? "legacy" : "phone")}
                className="mt-5 w-full text-center text-sm font-semibold text-neutral-500 hover:text-neutral-800"
              >
                {mode === "phone"
                  ? "Use an existing email account"
                  : "Sign in with phone instead"}
              </button>
            )}

            <div className="mt-8 flex items-center justify-between border-t border-neutral-200 pt-6 text-sm text-neutral-500">
              <span>
                New here?{" "}
                <Link
                  href="/auth/signup"
                  className="font-semibold text-brand-turquoise-700 hover:text-brand-turquoise-800"
                >
                  Create a free account
                </Link>
              </span>
              <Link
                href="/jobs"
                className="transition-colors hover:text-neutral-800"
              >
                Browse jobs →
              </Link>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}

function RememberField({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-neutral-600">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 cursor-pointer rounded border-neutral-300 text-brand-turquoise-600 focus:ring-brand-turquoise-500"
      />{" "}
      Stay logged in
    </label>
  );
}
