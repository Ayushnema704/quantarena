"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function CodeUploadWizard() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"idle" | "uploading" | "building" | "testing" | "done">("idle");
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [duration, setDuration] = useState<number>(30);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUploadAndTest = async () => {
    if (!file) {
      setError("Please select a ZIP file containing your trading engine code.");
      return;
    }
    if (!file.name.endsWith(".zip")) {
      setError("Only .zip files are accepted.");
      return;
    }

    setUploading(true);
    setError(null);
    setStep("uploading");

    try {
      // Step 1: Upload code
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/submission", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to upload and start sandboxing");
      }

      const uploadResult = await res.json();
      const subId = uploadResult.submission_id;
      setSubmissionId(subId);
      setStep("building");

      // Wait 3 seconds for deployment to settle
      await new Promise((resolve) => setTimeout(resolve, 3000));

      // Step 2: Trigger load testing
      setStep("testing");
      const testRes = await fetch(`/api/submission/${subId}?duration=${duration}`, {
        method: "POST",
      });

      if (!testRes.ok) {
        const data = await testRes.json();
        throw new Error(data.error || "Failed to trigger load test");
      }

      setStep("done");
      // Go to submission detail page to view real-time charts and scoring
      router.push(`/submission/${subId}`);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
      setStep("idle");
      setUploading(false);
    }
  };

  return (
    <section className="wizard-card">
      <div className="wizard-header">
        <h2>Submit Trading Engine for Benchmarking</h2>
        <p>Complete Pipeline: Code Upload ➔ Sandbox Deploy ➔ Load Testing ➔ Real-Time Scoring</p>
      </div>

      {step === "idle" && (
        <div className="wizard-body">
          <div className="dropzone">
            <input type="file" accept=".zip" onChange={handleFileChange} id="zip-file" />
            <label htmlFor="zip-file" className="dropzone-label">
              <span className="icon">📁</span>
              {file ? (
                <span className="file-name">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
              ) : (
                <span>Drag & drop or click to choose a trading server .zip file</span>
              )}
            </label>
          </div>

          <div className="settings-row">
            <div className="form-group">
              <label htmlFor="duration-select">Test Duration:</label>
              <select
                id="duration-select"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              >
                <option value={10}>10 Seconds (Quick check)</option>
                <option value={30}>30 Seconds (Standard benchmark)</option>
                <option value={60}>60 Seconds (Full load test)</option>
              </select>
            </div>

            <button className="btn-primary" onClick={handleUploadAndTest} disabled={!file}>
              Deploy & Benchmark
            </button>
          </div>

          {error && <div className="error-message">{error}</div>}
        </div>
      )}

      {step !== "idle" && (
        <div className="wizard-progress">
          <div className="pipeline-steps">
            <div className={`step-item ${step === "uploading" ? "active" : "completed"}`}>
              <div className="step-num">1</div>
              <div className="step-name">Uploading</div>
            </div>
            <div className={`step-item ${step === "building" ? "active" : (step === "testing" || step === "done") ? "completed" : ""}`}>
              <div className="step-num">2</div>
              <div className="step-name">Sandboxed Deploy</div>
            </div>
            <div className={`step-item ${step === "testing" ? "active" : step === "done" ? "completed" : ""}`}>
              <div className="step-num">3</div>
              <div className="step-name">Distributed Load Test</div>
            </div>
            <div className={`step-item ${step === "done" ? "active" : ""}`}>
              <div className="step-num">4</div>
              <div className="step-name">Live Scoring Dashboard</div>
            </div>
          </div>

          <div className="progress-status">
            <div className="loader-pulse"></div>
            {step === "uploading" && <p>Uploading zip to platform...</p>}
            {step === "building" && <p>Building docker image & sandboxing container...</p>}
            {step === "testing" && <p>Launching load bots! Generating coordinate-omission-aware load...</p>}
            {step === "done" && <p>Ready! Redirecting to real-time scoring dashboard...</p>}
          </div>
        </div>
      )}
    </section>
  );
}
