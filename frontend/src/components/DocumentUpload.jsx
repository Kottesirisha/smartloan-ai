import { useState } from "react";
import {
  uploadDocument,
  generateDummyDocs,
  processAllDocuments,
} from "../services/api";
import VerificationTimeline from "./VerificationTimeline";

const DOC_SLOTS = [
  { type: "Payslip", label: "Payslip", hint: "Salary / earnings PDF" },
  { type: "Bank Statement", label: "Bank Statement", hint: "Account statement PDF" },
  { type: "Tax Return", label: "Tax Return", hint: "ITR / Form 16 PDF" },
  { type: "KYC Document", label: "KYC Document", hint: "Aadhaar / Passport PDF" },
];

const emptySlots = () =>
  Object.fromEntries(
    DOC_SLOTS.map((slot) => [
      slot.type,
      { file: null, status: "empty", documentId: null, preview: null },
    ])
  );

export default function DocumentUpload({ applicationId, onCompleted }) {
  const [slots, setSlots] = useState(emptySlots);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const updateSlot = (type, patch) => {
    setSlots((prev) => ({
      ...prev,
      [type]: { ...prev[type], ...patch },
    }));
  };

  const handleFileChange = (type, event) => {
    const selected = event.target.files?.[0] || null;
    setError("");
    if (!selected) return;

    const isPdf =
      selected.type === "application/pdf" ||
      selected.name.toLowerCase().endsWith(".pdf");

    if (!isPdf) {
      setError("Please select PDF files only.");
      return;
    }

    updateSlot(type, { file: selected, status: "selected", preview: null });
  };

  const runDummyGeneration = async (mode) => {
    if (!applicationId) {
      setError("Create an application first.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage(
      mode === "clean"
        ? "Generating clean matching documents..."
        : "Generating anomaly documents (income/name mismatch)..."
    );
    setStage(1);

    try {
      const response = await generateDummyDocs(
        applicationId,
        mode,
        mode === "anomaly"
      );
      const docs = response.data.documents || [];

      const next = emptySlots();
      docs.forEach((doc) => {
        if (next[doc.document_type]) {
          next[doc.document_type] = {
            file: { name: doc.filename },
            status: "uploaded",
            documentId: doc.document_id,
            preview: null,
          };
        }
      });
      setSlots(next);
      setStage(2);
      setMessage(
        `${docs.length} demo documents attached. Running full AI verification...`
      );

      await runProcessAll();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Dummy document generation failed."
      );
      setMessage("");
    } finally {
      setLoading(false);
    }
  };

  const runProcessAll = async () => {
    setStage(3);
    setMessage("Classifying documents & extracting fields...");
    const response = await processAllDocuments(applicationId);
    setStage(8);
    setMessage("Verification complete.");

    const processed = response.data.processed_documents || [];
    setSlots((prev) => {
      const next = { ...prev };
      processed.forEach((item) => {
        if (!item.document_type || !next[item.document_type]) return;
        next[item.document_type] = {
          ...next[item.document_type],
          status: item.validation_result?.is_valid ? "validated" : "review",
          preview:
            item.extraction?.fields ||
            item.validation_result?.extracted_details,
          documentId: item.document_id,
        };
      });
      return next;
    });

    onCompleted?.(response.data);
  };

  const handleUploadAndProcess = async () => {
    if (!applicationId) {
      setError("Application ID is missing.");
      return;
    }

    const selected = DOC_SLOTS.filter((slot) => slots[slot.type].file);
    if (selected.length === 0) {
      setError("Upload at least one document or generate demo documents.");
      return;
    }

    setLoading(true);
    setError("");
    setStage(1);

    try {
      for (const slot of selected) {
        const current = slots[slot.type];
        if (current.documentId && !current.file?.size) {
          continue;
        }
        if (!current.file?.size && current.documentId) {
          continue;
        }
        if (!current.file?.size) continue;

        setMessage(`Uploading ${slot.label}...`);
        updateSlot(slot.type, { status: "uploading" });
        const uploadResponse = await uploadDocument(
          applicationId,
          current.file,
          slot.type
        );
        updateSlot(slot.type, {
          status: "uploaded",
          documentId: uploadResponse.data.document_id,
        });
      }

      setStage(2);
      setMessage("Running multi-document AI verification...");
      await runProcessAll();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : err.message || "Processing failed."
      );
      setMessage("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel document-upload-panel">
      <div className="section-heading">
        <span>STEP 2</span>
        <h2>Document verification suite</h2>
        <p>
          Upload Payslip, Bank Statement, Tax Return, and KYC — or auto-generate
          demo PDFs for clean and anomaly testing.
        </p>
      </div>

      <VerificationTimeline currentStage={stage} />

      <div className="demo-actions">
        <button
          type="button"
          className="primary-button"
          disabled={loading}
          onClick={() => runDummyGeneration("clean")}
        >
          Auto-Generate Clean Documents
        </button>
        <button
          type="button"
          className="outline-button"
          disabled={loading}
          onClick={() => runDummyGeneration("anomaly")}
        >
          Auto-Generate Anomaly Documents
        </button>
      </div>

      <div className="doc-slot-grid">
        {DOC_SLOTS.map((slot) => {
          const state = slots[slot.type];
          return (
            <div className={`doc-slot status-${state.status}`} key={slot.type}>
              <h3>{slot.label}</h3>
              <p>{slot.hint}</p>
              <input
                type="file"
                accept=".pdf,application/pdf"
                disabled={loading}
                onChange={(event) => handleFileChange(slot.type, event)}
              />
              <span className="slot-status">{state.status}</span>
              {state.file?.name && (
                <small className="file-name">{state.file.name}</small>
              )}
              {state.preview && (
                <div className="field-chips">
                  {Object.entries(state.preview)
                    .slice(0, 4)
                    .map(([key, value]) =>
                      value != null ? (
                        <span className="chip" key={key}>
                          {key}: {String(value)}
                        </span>
                      ) : null
                    )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      <button
        type="button"
        className="primary-button full-width"
        onClick={handleUploadAndProcess}
        disabled={loading || !applicationId}
      >
        {loading ? "Processing..." : "Upload & Run Full AI Verification"}
      </button>
    </section>
  );
}
