"use client";

import { useEffect, useState } from "react";

type Application = {
  id: number;
  company: string;
  role: string;
  current_status: string;
};

const statuses = [
  "Application Received",
  "Under Review",
  "Assessment Invite",
  "Interview Scheduled",
  "Offer",
  "Rejected",
  "Action Required",
];

export default function DashboardPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [currentStatus, setCurrentStatus] = useState("Application Received");
  const [errorMessage, setErrorMessage] = useState("");

  async function fetchApplications() {
    const response = await fetch("http://127.0.0.1:8000/applications");

    if (!response.ok) {
      throw new Error("Failed to fetch applications");
    }

    const data = await response.json();
    setApplications(data);
  }

  useEffect(() => {
    fetchApplications();
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!company.trim() || !role.trim()) {
      setErrorMessage("Company and role are required.");
      return;
    }

    setErrorMessage("");

    const response = await fetch("http://127.0.0.1:8000/applications", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        company: company.trim(),
        role: role.trim(),
        current_status: currentStatus,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to create application");
    }

    setCompany("");
    setRole("");
    setCurrentStatus("Application Received");

    await fetchApplications();
  }

  async function updateStatus(applicationId: number, newStatus: string) {
    const response = await fetch(
      `http://127.0.0.1:8000/applications/${applicationId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_status: newStatus,
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Failed to update application status");
    }

    await fetchApplications();
  }

  async function deleteApplication(applicationId: number) {
    const response = await fetch(
      `http://127.0.0.1:8000/applications/${applicationId}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      throw new Error("Failed to delete application");
    }

    await fetchApplications();
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#050816",
        color: "white",
        padding: "48px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <section
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
        }}
      >
        <div style={{ marginBottom: "40px" }}>
          <p
            style={{
              color: "#8b9bb4",
              fontSize: "14px",
              marginBottom: "8px",
              textTransform: "uppercase",
              letterSpacing: "1px",
            }}
          >
            FlowState
          </p>

          <h1
            style={{
              fontSize: "42px",
              margin: "0 0 12px 0",
            }}
          >
            Job Application Dashboard
          </h1>

          <p
            style={{
              color: "#aab4c4",
              fontSize: "18px",
              margin: 0,
            }}
          >
            Add, track, update, and delete your job applications in one place.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "360px 1fr",
            gap: "32px",
            alignItems: "start",
          }}
        >
          <form
            onSubmit={handleSubmit}
            style={{
              background: "#0f172a",
              border: "1px solid #253047",
              borderRadius: "16px",
              padding: "24px",
              boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
            }}
          >
            <h2
              style={{
                fontSize: "24px",
                marginTop: 0,
                marginBottom: "20px",
              }}
            >
              Add Application
            </h2>

            {errorMessage && (
              <p
                style={{
                  background: "#3b1111",
                  border: "1px solid #ef4444",
                  color: "#fecaca",
                  padding: "10px",
                  borderRadius: "8px",
                  marginBottom: "16px",
                }}
              >
                {errorMessage}
              </p>
            )}

            <div style={{ marginBottom: "16px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "6px",
                  color: "#cbd5e1",
                  fontSize: "14px",
                }}
              >
                Company
              </label>

              <input
                required
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                placeholder="Deloitte"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px",
                  borderRadius: "10px",
                  border: "1px solid #334155",
                  background: "#020617",
                  color: "white",
                  fontSize: "15px",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "6px",
                  color: "#cbd5e1",
                  fontSize: "14px",
                }}
              >
                Role
              </label>

              <input
                required
                value={role}
                onChange={(event) => setRole(event.target.value)}
                placeholder="Infrastructure Engineering Intern"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px",
                  borderRadius: "10px",
                  border: "1px solid #334155",
                  background: "#020617",
                  color: "white",
                  fontSize: "15px",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ marginBottom: "20px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "6px",
                  color: "#cbd5e1",
                  fontSize: "14px",
                }}
              >
                Status
              </label>

              <select
                value={currentStatus}
                onChange={(event) => setCurrentStatus(event.target.value)}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px",
                  borderRadius: "10px",
                  border: "1px solid #334155",
                  background: "#020617",
                  color: "white",
                  fontSize: "15px",
                  outline: "none",
                }}
              >
                {statuses.map((status) => (
                  <option key={status}>{status}</option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              style={{
                width: "100%",
                padding: "12px 16px",
                borderRadius: "10px",
                border: "none",
                background: "white",
                color: "#020617",
                fontWeight: "bold",
                fontSize: "15px",
                cursor: "pointer",
              }}
            >
              Add Application
            </button>
          </form>

          <section>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              <div>
                <h2
                  style={{
                    fontSize: "26px",
                    margin: 0,
                  }}
                >
                  Applications
                </h2>

                <p
                  style={{
                    color: "#94a3b8",
                    marginTop: "6px",
                  }}
                >
                  {applications.length} application
                  {applications.length === 1 ? "" : "s"} tracked
                </p>
              </div>
            </div>

            {applications.length === 0 ? (
              <div
                style={{
                  background: "#0f172a",
                  border: "1px dashed #334155",
                  borderRadius: "16px",
                  padding: "40px",
                  textAlign: "center",
                  color: "#94a3b8",
                }}
              >
                <h3 style={{ color: "white", marginTop: 0 }}>
                  No applications yet
                </h3>
                <p>
                  Add your first application using the form on the left.
                </p>
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gap: "16px",
                }}
              >
                {applications.map((application) => (
                  <div
                    key={application.id}
                    style={{
                      background: "#0f172a",
                      border: "1px solid #253047",
                      borderRadius: "16px",
                      padding: "22px",
                      boxShadow: "0 16px 30px rgba(0,0,0,0.2)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "16px",
                        alignItems: "start",
                      }}
                    >
                      <div>
                        <h3
                          style={{
                            fontSize: "22px",
                            margin: "0 0 8px 0",
                          }}
                        >
                          {application.company}
                        </h3>

                        <p
                          style={{
                            color: "#cbd5e1",
                            margin: "0 0 16px 0",
                            fontSize: "16px",
                          }}
                        >
                          {application.role}
                        </p>
                      </div>

                      <button
                        onClick={() => deleteApplication(application.id)}
                        style={{
                          background: "#2a0f16",
                          color: "#fca5a5",
                          border: "1px solid #7f1d1d",
                          borderRadius: "8px",
                          padding: "8px 10px",
                          cursor: "pointer",
                        }}
                      >
                        Delete
                      </button>
                    </div>

                    <div>
                      <label
                        style={{
                          display: "block",
                          marginBottom: "6px",
                          color: "#94a3b8",
                          fontSize: "14px",
                        }}
                      >
                        Current Status
                      </label>

                      <select
                        value={application.current_status}
                        onChange={(event) =>
                          updateStatus(application.id, event.target.value)
                        }
                        style={{
                          width: "260px",
                          padding: "10px",
                          borderRadius: "10px",
                          border: "1px solid #334155",
                          background: "#020617",
                          color: "white",
                          fontSize: "14px",
                          outline: "none",
                        }}
                      >
                        {statuses.map((status) => (
                          <option key={status}>{status}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}