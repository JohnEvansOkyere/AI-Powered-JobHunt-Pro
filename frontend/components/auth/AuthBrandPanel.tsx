import Image from "next/image";

export default function AuthBrandPanel({
  variant,
}: {
  variant: "signup" | "login";
}) {
  return (
    <aside className="vh-auth-story">
      <p className="vh-eyebrow">YOUR NEXT CHAPTER</p>
      <h2>
        {variant === "login"
          ? "Pick up where you left off."
          : "Make room for what comes next."}
      </h2>
      <p>
        {variant === "login"
          ? "Your shortlist, your applications, and your next opportunity. All in one place."
          : "Bring your experience. Find work that fits. Build an application that feels like you."}
      </p>
      <div className="vh-auth-photo">
        <Image
          src="/landing/candidate-at-work.jpg"
          alt="A professional working at her laptop"
          width={1200}
          height={675}
          sizes="(max-width: 760px) 1px, 440px"
        />
      </div>
      <p className="vh-auth-caption">
        Local opportunities and remote possibilities. Always your choice.
      </p>
    </aside>
  );
}
