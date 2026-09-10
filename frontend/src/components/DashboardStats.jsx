export default function DashboardStats({ applications }) {
  const stats = [
    {
      label: "Total Applications",
      value: applications.length,
    },
    {
      label: "Eligible / Approved",
      value: applications.filter(
        (item) =>
          item.status === "Eligible" || item.status === "Approved"
      ).length,
    },
    {
      label: "Manual Review",
      value: applications.filter(
        (item) => item.status === "Manual Review"
      ).length,
    },
    {
      label: "Rejected / Pending",
      value: applications.filter((item) =>
        ["Not Eligible", "Rejected", "Document Pending", "Document Uploaded"].includes(
          item.status
        )
      ).length,
    },
  ];

  return (
    <div className="stats-grid">
      {stats.map((stat) => (
        <div className="stat-card" key={stat.label}>
          <p>{stat.label}</p>
          <h3>{stat.value}</h3>
        </div>
      ))}
    </div>
  );
}
