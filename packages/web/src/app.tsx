import { signal } from "@preact/signals";
import type { PipelineStage } from "@visit-monitor/contracts";

import { appShell, card, label, title, value } from "./app.css";

const pipelineStage = signal<PipelineStage>("idle");

export function App() {
  return (
    <main class={appShell}>
      <section class={card}>
        <p class={label}>Visit Monitor</p>
        <h1 class={title}>Frontend scaffold</h1>
        <p class={value}>Current pipeline stage: {pipelineStage.value}</p>
      </section>
    </main>
  );
}
