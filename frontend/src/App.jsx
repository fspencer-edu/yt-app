import React, { useEffect, useState } from "react";

const API_BASE = "/api";

export default function App() {
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  async function fetchVideos() {
    try {
      const res = await fetch(`${API_BASE}/videos`);

      if (!res.ok) {
        throw new Error(`Failed to fetch videos: ${res.status}`);
      }

      const data = await res.json();
      setVideos(data);

      if (data.length === 0) {
        setSelectedVideo(null);
        return;
      }

      setSelectedVideo((current) => {
        if (!current) return data[0];
        const updated = data.find((video) => video.id === current.id);
        return updated || data[0];
      });
    } catch (err) {
      console.error("fetchVideos error:", err);
    }
  }

  useEffect(() => {
    fetchVideos();
    const timer = setInterval(fetchVideos, 5000);
    return () => clearInterval(timer);
  }, []);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;

    try {
      setLoading(true);
      setUploadProgress(0);

      const formData = new FormData();
      formData.append("title", title);
      formData.append("description", description);
      formData.append("video", file);

      await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.open("POST", `${API_BASE}/videos/upload`);

        xhr.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            setUploadProgress(percent);
          }
        });

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            setUploadProgress(100);
            resolve(xhr.responseText);
          } else {
            reject(new Error(`Upload failed: ${xhr.status} ${xhr.responseText}`));
          }
        };

        xhr.onerror = () => {
          reject(new Error("Network error during upload"));
        };

        xhr.send(formData);
      });

      setTitle("");
      setDescription("");
      setFile(null);
      await fetchVideos();
    } catch (err) {
      console.error("upload error:", err);
    } finally {
      setLoading(false);
      setTimeout(() => setUploadProgress(0), 800);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>MiniTube</h1>
        <p>Simple React + Flask video app</p>
      </header>

      <section className="upload-card">
        <h2>Upload video</h2>
        <form onSubmit={handleUpload} className="upload-form">
          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <textarea
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <input
            type="file"
            accept="video/mp4,video/*"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? "Uploading..." : "Upload"}
          </button>

          {loading && (
            <div className="progress-wrap">
              <div className="progress-label">Uploading: {uploadProgress}%</div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </form>
      </section>

      <main className="layout">
        <section className="player-panel">
          {selectedVideo ? (
            <>
              <h2>{selectedVideo.title}</h2>
              <p className="status">Status: {selectedVideo.status}</p>

              {selectedVideo.status === "ready" ? (
                <video
                  controls
                  width="100%"
                  src={selectedVideo.stream_url}
                />
              ) : (
                <div className="processing">Video is processing...</div>
              )}

              <p>{selectedVideo.description}</p>
            </>
          ) : (
            <p>No video selected.</p>
          )}
        </section>

        <aside className="sidebar">
          <h3>Videos</h3>
          {videos.map((video) => (
            <button
              key={video.id}
              className={`video-item ${selectedVideo?.id === video.id ? "active" : ""}`}
              onClick={() => setSelectedVideo(video)}
            >
              <strong>{video.title}</strong>
              <span>{video.status}</span>
            </button>
          ))}
        </aside>
      </main>
    </div>
  );
}