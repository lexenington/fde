"use client";

import { useState } from "react";
import LabRunner from "@/components/LabRunner";
import SavannaDocs from "@/components/SavannaDocs";

export default function SavannaTabs({ world }: { world: React.ReactNode }) {
  const [tab, setTab] = useState<"world" | "docs" | "uat">("world");
  const T = ({ id, children }: { id: typeof tab; children: React.ReactNode }) => (
    <button className={tab === id ? "on" : ""} onClick={() => setTab(id)}>{children}</button>
  );
  return (
    <>
      <div className="tabs"><T id="world">The world</T><T id="docs">Documents, officers &amp; try it</T><T id="uat">Acceptance test</T></div>
      {tab === "world" && world}
      {tab === "docs" && <SavannaDocs />}
      {tab === "uat" && <LabRunner lab="savanna" />}
    </>
  );
}
