import axios from "axios";

const api = axios.create({
  baseURL: "https://smartloan-ai-8pxd.onrender.com",
  timeout: 60000,
});

export const createApplication = (data) =>
  api.post("/applications", data);

export const getApplications = (status) =>
  api.get("/applications", {
    params: status ? { status } : {},
  });

export const getApplication = (applicationId) =>
  api.get(`/applications/${applicationId}`);

export const getApplicationSummary = (applicationId) =>
  api.get(`/applications/${applicationId}/summary`);

export const getDatasetSamples = (params = {}) =>
  api.get("/dataset/samples", {
    params,
  });

export const uploadDocument = (
  applicationId,
  file,
  documentType
) => {
  const formData = new FormData();

  formData.append("file", file);

  if (documentType) {
    formData.append("document_type", documentType);
  }

  return api.post(
    `/applications/${applicationId}/documents`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
};

export const generateDummyDocs = (
  applicationId,
  mode = "clean",
  skipTax = false
) =>
  api.post(
    `/applications/${applicationId}/generate-dummy-docs`,
    {
      mode,
      skip_tax: skipTax,
    }
  );

export const validateDocument = (documentId) =>
  api.post(`/documents/${documentId}/validate`);

export const processAllDocuments = (applicationId) =>
  api.post(`/applications/${applicationId}/process-all`);

export const checkEligibility = (applicationId) =>
  api.post(
    `/applications/${applicationId}/eligibility`
  );

export const submitOfficerReview = (
  applicationId,
  decision,
  notes,
  reviewedBy
) =>
  api.post(
    `/applications/${applicationId}/officer-review`,
    {
      decision,
      notes,
      reviewed_by: reviewedBy || "Loan Officer",
    }
  );

export const getDocumentDownloadUrl = (documentId) =>
  `${api.defaults.baseURL}/documents/${documentId}/download`;

export const getDocumentsZipUrl = (applicationId) =>
  `${api.defaults.baseURL}/applications/${applicationId}/documents/zip`;

export const getApplicationDocuments = (applicationId) =>
  api.get(
    `/applications/${applicationId}/documents`
  );

export default api;