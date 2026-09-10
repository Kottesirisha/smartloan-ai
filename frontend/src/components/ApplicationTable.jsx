export default function ApplicationTable({ applications, onSelect }) {
  return (
    <section className="panel table-panel">
      <div className="section-heading">
        <h2>Loan applications</h2>
        <p>Select a row to open the review workspace.</p>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Applicant</th>
              <th>Income</th>
              <th>Loan Amount</th>
              <th>CIBIL</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            {applications.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">
                  No applications found.
                </td>
              </tr>
            ) : (
              applications.map((application) => (
                <tr key={application.application_id}>
                  <td>
                    <strong>{application.applicant_name}</strong>
                    <small>{application.email}</small>
                  </td>
                  <td>
                    ₹
                    {Number(application.annual_income).toLocaleString("en-IN")}
                  </td>
                  <td>
                    ₹
                    {Number(application.loan_amount).toLocaleString("en-IN")}
                  </td>
                  <td>{application.cibil_score ?? "—"}</td>
                  <td>
                    <span
                      className={`status-badge ${
                        application.status === "Eligible" ||
                        application.status === "Approved"
                          ? "status-eligible"
                          : application.status === "Manual Review"
                            ? "status-review"
                            : application.status === "Rejected" ||
                                application.status === "Not Eligible"
                              ? "status-rejected"
                              : "status-pending"
                      }`}
                    >
                      {application.status}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="outline-button"
                      onClick={() => onSelect?.(application.application_id)}
                    >
                      Review
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
