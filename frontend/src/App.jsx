import React, { useState } from "react";

const App = () => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle, uploading, processing, complete, error
  const [downloadUrl, setDownloadUrl] = useState(null);

  const API_URL = "http://localhost:8000/convert"; // Change this for Prod

  const handleFileChange = e => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus("idle");
      setDownloadUrl(null);
    }
  };

  const processFile = async () => {
    if (!file) return;

    setStatus("uploading");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Conversion failed");

      // Handle Blob response
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      setDownloadUrl(url);
      setStatus("complete");
    } catch (err) {
      console.error(err);
      setStatus("error");
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-900/30 text-blue-400 mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
              ></path>
            </svg>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            Night Mode PDF
          </h1>
          <p className="text-gray-500 mt-2 text-sm">AI-Enhanced Vector Rewriting</p>
        </div>

        {/* Upload Zone */}
        <div className="relative group">
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
            disabled={status === "uploading"}
          />
          <div
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
              file
                ? "border-blue-500 bg-blue-900/10"
                : "border-gray-700 hover:border-gray-500 hover:bg-gray-800"
            }`}
          >
            {file ? (
              <div className="flex items-center justify-center gap-2 text-blue-300">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  ></path>
                </svg>
                <span className="truncate max-w-[200px]">{file.name}</span>
              </div>
            ) : (
              <span className="text-gray-400">Drop PDF or Click to Browse</span>
            )}
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={processFile}
          disabled={!file || status === "uploading" || status === "complete"}
          className={`w-full mt-6 py-3 rounded-lg font-semibold transition-all shadow-lg ${
            !file
              ? "bg-gray-800 text-gray-500 cursor-not-allowed"
              : status === "complete"
              ? "bg-green-600 text-white hover:bg-green-500"
              : "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-900/50"
          }`}
        >
          {status === "idle" && "Convert to Night Mode"}
          {status === "uploading" && "Processing..."}
          {status === "complete" && "Ready!"}
          {status === "error" && "Failed - Try Again"}
        </button>

        {/* Download Link */}
        {status === "complete" && downloadUrl && (
          <div className="mt-6 animate-fade-in">
            <a
              href={downloadUrl}
              download={`night_${file.name}`}
              className="block w-full py-3 text-center rounded-lg border border-green-500/50 text-green-400 hover:bg-green-900/20 transition-colors"
            >
              Download Converted PDF
            </a>
            <p className="text-xs text-center text-gray-500 mt-3">
              Works with Apple Books, Kindle & Acrobat
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
