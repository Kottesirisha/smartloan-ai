import { useEffect, useState } from "react";
import { createApplication, getDatasetSamples } from "../services/api";

const emptyForm = {
  applicant_name: "",
  email: "",
  phone: "",
  annual_income: "",
  loan_amount: "",
  loan_id: "",
  cibil_score: "",
  loan_term: "",
  education: "",
  self_employed: "",
  no_of_dependents: "",
  residential_assets_value: "",
  commercial_assets_value: "",
  luxury_assets_value: "",
  bank_asset_value: "",
};

export default function ApplicationForm({ onCreated }) {
  const [formData, setFormData] = useState(emptyForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showDataset, setShowDataset] = useState(false);
  const [samples, setSamples] = useState([]);
  const [sampleFilter, setSampleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loadingSamples, setLoadingSamples] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const loadSamples = async () => {
    setLoadingSamples(true);
    try {
      const response = await getDatasetSamples({
        q: sampleFilter || undefined,
        status: statusFilter || undefined,
        limit: 20,
      });
      setSamples(response.data.records || []);
    } catch {
      setError("Unable to load Kaggle dataset samples.");
    } finally {
      setLoadingSamples(false);
    }
  };

  useEffect(() => {
    if (showDataset) {
      loadSamples();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showDataset, statusFilter]);

  const applySample = (record) => {
    setFormData((prev) => ({
      ...prev,
      applicant_name: prev.applicant_name || `Applicant ${record.loan_id}`,
      email: prev.email || `applicant${record.loan_id}@smartloan.test`,
      phone: prev.phone || "9876543210",
      annual_income: String(record.income_annum),
      loan_amount: String(record.loan_amount),
      loan_id: String(record.loan_id),
      cibil_score: String(record.cibil_score),
      loan_term: String(record.loan_term),
      education: record.education,
      self_employed: record.self_employed,
      no_of_dependents: String(record.no_of_dependents),
      residential_assets_value: String(record.residential_assets_value),
      commercial_assets_value: String(record.commercial_assets_value),
      luxury_assets_value: String(record.luxury_assets_value),
      bank_asset_value: String(record.bank_asset_value),
    }));
    setShowDataset(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (
      !formData.applicant_name ||
      !formData.email ||
      !formData.phone ||
      !formData.annual_income ||
      !formData.loan_amount
    ) {
      setError("Please fill in the required applicant and loan fields.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        applicant_name: formData.applicant_name,
        email: formData.email,
        phone: formData.phone,
        annual_income: Number(formData.annual_income),
        loan_amount: Number(formData.loan_amount),
        loan_id: formData.loan_id ? Number(formData.loan_id) : null,
        cibil_score: formData.cibil_score ? Number(formData.cibil_score) : null,
        loan_term: formData.loan_term ? Number(formData.loan_term) : null,
        education: formData.education || null,
        self_employed: formData.self_employed || null,
        no_of_dependents: formData.no_of_dependents
          ? Number(formData.no_of_dependents)
          : null,
        residential_assets_value: formData.residential_assets_value
          ? Number(formData.residential_assets_value)
          : null,
        commercial_assets_value: formData.commercial_assets_value
          ? Number(formData.commercial_assets_value)
          : null,
        luxury_assets_value: formData.luxury_assets_value
          ? Number(formData.luxury_assets_value)
          : null,
        bank_asset_value: formData.bank_asset_value
          ? Number(formData.bank_asset_value)
          : null,
      };

      const response = await createApplication(payload);
      onCreated?.(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to create the application."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel application-panel">
      <div className="section-heading">
        <span>STEP 1</span>
        <h2>Loan application</h2>
        <p>
          Enter details or autofill from the Kaggle Loan Approval Prediction
          dataset.
        </p>
      </div>

      <div className="action-row">
        <button
          type="button"
          className="outline-button"
          onClick={() => setShowDataset(true)}
        >
          Browse Kaggle records
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <input
            type="text"
            name="applicant_name"
            placeholder="Applicant name *"
            value={formData.applicant_name}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="email"
            name="email"
            placeholder="Email address *"
            value={formData.email}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="tel"
            name="phone"
            placeholder="Phone number *"
            value={formData.phone}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="annual_income"
            placeholder="Annual income *"
            value={formData.annual_income}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="loan_amount"
            placeholder="Loan amount *"
            value={formData.loan_amount}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="loan_id"
            placeholder="Kaggle Loan ID"
            value={formData.loan_id}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="cibil_score"
            placeholder="CIBIL score"
            value={formData.cibil_score}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="loan_term"
            placeholder="Loan term (months)"
            value={formData.loan_term}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="text"
            name="education"
            placeholder="Education"
            value={formData.education}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="text"
            name="self_employed"
            placeholder="Self employed (Yes/No)"
            value={formData.self_employed}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="no_of_dependents"
            placeholder="Dependents"
            value={formData.no_of_dependents}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="residential_assets_value"
            placeholder="Residential assets"
            value={formData.residential_assets_value}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="commercial_assets_value"
            placeholder="Commercial assets"
            value={formData.commercial_assets_value}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="luxury_assets_value"
            placeholder="Luxury assets"
            value={formData.luxury_assets_value}
            onChange={handleChange}
            disabled={loading}
          />
          <input
            type="number"
            name="bank_asset_value"
            placeholder="Bank asset value"
            value={formData.bank_asset_value}
            onChange={handleChange}
            disabled={loading}
          />
        </div>

        {error && <div className="error-message">{error}</div>}

        <button
          type="submit"
          className="primary-button full-width"
          disabled={loading}
        >
          {loading ? "Creating..." : "Create Application"}
        </button>
      </form>

      {showDataset && (
        <div className="modal-backdrop" onClick={() => setShowDataset(false)}>
          <div
            className="modal-panel dataset-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="section-heading">
              <h2>Kaggle dataset selector</h2>
              <p>Pick an Approved or Rejected profile to autofill the form.</p>
            </div>

            <div className="filter-row">
              <input
                type="text"
                placeholder="Search loan ID / education"
                value={sampleFilter}
                onChange={(e) => setSampleFilter(e.target.value)}
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All statuses</option>
                <option value="Approved">Approved</option>
                <option value="Rejected">Rejected</option>
              </select>
              <button
                type="button"
                className="outline-button"
                onClick={loadSamples}
              >
                Search
              </button>
            </div>

            {loadingSamples ? (
              <p>Loading records...</p>
            ) : (
              <div className="sample-list">
                {samples.map((record) => (
                  <button
                    type="button"
                    key={record.loan_id}
                    className="sample-card"
                    onClick={() => applySample(record)}
                  >
                    <strong>Loan #{record.loan_id}</strong>
                    <span
                      className={`status-badge ${
                        record.loan_status === "Approved"
                          ? "status-eligible"
                          : "status-review"
                      }`}
                    >
                      {record.loan_status}
                    </span>
                    <small>
                      Income ₹{Number(record.income_annum).toLocaleString("en-IN")} ·
                      Loan ₹{Number(record.loan_amount).toLocaleString("en-IN")} ·
                      CIBIL {record.cibil_score}
                    </small>
                  </button>
                ))}
              </div>
            )}

            <button
              type="button"
              className="outline-button full-width"
              onClick={() => setShowDataset(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
