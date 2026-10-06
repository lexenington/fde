"use client";

import { useState } from "react";
import LabRunner from "@/components/LabRunner";
import LakesideDb from "@/components/LakesideDb";
import PatientPhone from "@/components/PatientPhone";

export default function LakesideTabs({ world }: { world: React.ReactNode }) {
  const [tab, setTab] = useState<"world" | "phone" | "db" | "uat">("world");
  const T = ({ id, children }: { id: typeof tab; children: React.ReactNode }) => (
    <button className={tab === id ? "on" : ""} onClick={() => setTab(id)}>{children}</button>
  );
  return (
    <>
      <div className="tabs">
        <T id="world">The world</T><T id="phone">Patient phone</T><T id="db">Database &amp; chaos</T><T id="uat">Acceptance test</T>
      </div>
      {tab === "world" && world}
      {tab === "phone" && <PatientPhone />}
      {tab === "db" && <LakesideDb />}
      {tab === "uat" && <LabRunner lab="lakeside" />}
    </>
  );
}
