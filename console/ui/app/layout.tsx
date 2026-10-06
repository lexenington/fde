import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "FDE Field Console", description: "The customer's world, on your machine" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="side">
            <div className="brand">FDE Field Console</div>
            <div className="brand-sub">The customer&apos;s world, on your machine</div>
            <nav className="nav">
              <Link href="/">Dashboard</Link>
              <div className="nav-h">Labs</div>
              <a className="soon" title="CLI today: python check.py">01 Messy data</a>
              <Link href="/labs/integration">02 Enterprise integration</Link>
              <a className="soon" title="CLI today: python eval.py">03 AI engineering</a>
              <a className="soon">04 Deploy anywhere</a>
              <a className="soon">05 Unfamiliar territory</a>
              <div className="nav-h">Customer: Adom Logistics</div>
              <Link href="/systems/crm">CRM</Link>
              <Link href="/systems/identity">Identity (IdP)</Link>
              <div className="nav-h">Engagements</div>
              <Link href="/engagements/lakeside">1 Lakeside Clinics</Link>
              <a className="soon">2 Savanna Microfinance</a>
              <div className="nav-h">Practice</div>
              <Link href="/stakeholders">Stakeholder calls</Link>
              <Link href="/injects">Inject cards</Link>
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
