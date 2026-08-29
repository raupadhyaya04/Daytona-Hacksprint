import { useState } from "react";

// Renders GET /api/report's markdown as the sign-off artifact an AppSec lead
// pastes into a risk doc. Kept dependency-free — no markdown renderer pulled
// in for a hacksprint, just a monospace <pre> block that reads perfectly fine
// for a report that's mostly headings + a table.
export default function ReportPanel({ report, onGenerate, generating, error, scenario, threshold }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!report?.markdown) return;
    await navigator.clipboard.writeText(report.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function handleDownload() {
    if (!report?.markdown) return;
    const blob = new Blob([report.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `model-gate-report-${report.scenario ?? "all"}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="card report-panel">
      <div className="card-header report-panel-header">
        <h3 className="card-title">Sign-off report</h3>
        <div className="report-actions">
          <button className="btn btn-secondary" onClick={onGenerate} disabled={generating}>
            {generating ? "Generating…" : report ? "Regenerate" : "Generate report"}
          </button>
          {report && (
            <>
              <button className="btn btn-secondary" onClick={handleCopy}>
                {copied ? "Copied ✓" : "Copy"}
              </button>
              <button className="btn btn-primary" onClick={handleDownload}>
                Download .md
              </button>
            </>
          )}
        </div>
      </div>
      <div className="card-content">
        {error && <p className="error-text report-error">{error}</p>}

        {!report ? (
          <p className="empty-state">
            Generate a sign-off report for the current scenario/threshold — the artifact a
            security lead pastes into a risk doc.
          </p>
        ) : (
          <>
            <div className="report-meta">
              <span>Scenario: {report.scenario ?? "all"}</span>
              <span>Threshold: {report.threshold}</span>
              <span>Generated: {new Date(report.generated_at).toLocaleString()}</span>
            </div>
            <pre className="report-markdown">{report.markdown}</pre>
          </>
        )}
      </div>
    </div>
  );
}